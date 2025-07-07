import asyncio
import logging
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Optional

from celery import shared_task
from django.core.cache import cache
from django.db import transaction
from django.utils import timezone

from arbitrage.engine import MultiExchangeArbitrageEngine
from arbitrage.models import (
    ArbitrageAlert,
    ArbitrageConfig,
    ArbitrageExecution,
    ArbitrageOpportunity,
    MultiExchangeArbitrageStrategy,
    MultiExchangeExecution,
)
from core.models import APICredential, Exchange, TradingPair
from exchanges.services.nobitex import NobitexService
from exchanges.services.ramzinex import RamzinexService
from exchanges.services.wallex import WallexService

logger = logging.getLogger(__name__)

# Service mapping
EXCHANGE_SERVICES = {
    "nobitex": NobitexService,
    "wallex": WallexService,
    "ramzinex": RamzinexService,
}


@shared_task
def scan_arbitrage_opportunities():
    """
    Enhanced periodic task to scan for both simple and multi-exchange arbitrage opportunities.
    """
    logger.info("Starting enhanced arbitrage scan...")
    
    # Get all active user configs
    active_configs = ArbitrageConfig.objects.filter(
        is_active=True
    ).select_related("user")
    
    # Run async scan
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        engine = MultiExchangeArbitrageEngine()
        
        # Scan for opportunities
        all_strategies = loop.run_until_complete(
            engine.scan_all_opportunities()
        )
        
        simple_opportunities = [s for s in all_strategies if isinstance(s, ArbitrageOpportunity)]
        multi_strategies = [s for s in all_strategies if isinstance(s, MultiExchangeArbitrageStrategy)]
        
        logger.info(f"Found {len(simple_opportunities)} simple opportunities and {len(multi_strategies)} multi-exchange strategies")
        
        # Save opportunities and strategies
        with transaction.atomic():
            # Save simple opportunities
            for opp in simple_opportunities:
                # Check if similar opportunity already exists
                existing = ArbitrageOpportunity.objects.filter(
                    trading_pair=opp.trading_pair,
                    buy_exchange=opp.buy_exchange,
                    sell_exchange=opp.sell_exchange,
                    status="detected",
                    expires_at__gt=timezone.now()
                ).first()
                
                if not existing:
                    opp.save()
                    
                    # Check user configs for alerts and auto-execution
                    for config in active_configs:
                        if should_alert_user(config, opp):
                            create_opportunity_alert(config.user, opp)
                            
                            # Auto-execute if enabled
                            if config.auto_trade:
                                execute_arbitrage_opportunity.delay(opp.id, config.user.id)
            
            # Save multi-exchange strategies
            for strategy in multi_strategies:
                # Check if similar strategy already exists
                existing_strategy = MultiExchangeArbitrageStrategy.objects.filter(
                    trading_pair=strategy.trading_pair,
                    strategy_type=strategy.strategy_type,
                    status="detected",
                    expires_at__gt=timezone.now()
                ).first()
                
                if not existing_strategy:
                    strategy.save()
                    
                    # Check user configs for multi-exchange strategies
                    for config in active_configs:
                        if config.enable_multi_exchange and should_alert_user_multi(config, strategy):
                            create_multi_strategy_alert(config.user, strategy)
                            
                            # Auto-execute if enabled
                            if config.auto_trade:
                                execute_multi_exchange_strategy.delay(strategy.id, config.user.id)
        
        # Mark expired opportunities
        loop.run_until_complete(engine.mark_expired_opportunities())
        
    except Exception as e:
        logger.error(f"Error in enhanced arbitrage scan: {e}")
    finally:
        loop.close()
    
    return f"Scan completed. Found {len(simple_opportunities)} simple opportunities and {len(multi_strategies)} multi-exchange strategies."


@shared_task
def execute_multi_exchange_strategy(strategy_id: str, user_id: int):
    """
    Execute a multi-exchange arbitrage strategy.
    """
    try:
        strategy = MultiExchangeArbitrageStrategy.objects.get(id=strategy_id)
        from django.contrib.auth.models import User
        user = User.objects.get(id=user_id)
        
        logger.info(f"Executing multi-exchange strategy {strategy.id} for user {user.username}")
        
        # Validate strategy is still viable
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            engine = MultiExchangeArbitrageEngine()
            is_valid, validation_message = loop.run_until_complete(
                engine.validate_strategy(strategy)
            )
            
            if not is_valid:
                strategy.status = "failed"
                strategy.save()
                create_strategy_alert(
                    user, strategy, "strategy_failed",
                    f"Strategy validation failed: {validation_message}"
                )
                return
            
            # Update strategy status
            strategy.status = "executing"
            strategy.execution_started_at = timezone.now()
            strategy.save()
            
            # Create execution records for each exchange action
            execution_tasks = []
            
            # Create buy executions
            for buy_action in strategy.buy_actions:
                execution = MultiExchangeExecution.objects.create(
                    strategy=strategy,
                    exchange=Exchange.objects.get(code=buy_action['exchange']),
                    action_type="BUY",
                    target_amount=Decimal(str(buy_action['amount'])),
                    target_price=Decimal(str(buy_action['price'])),
                    status="pending"
                )
                
                task = execute_single_exchange_action.delay(execution.id, user.id)
                execution_tasks.append(task)
            
            # Create sell executions
            for sell_action in strategy.sell_actions:
                execution = MultiExchangeExecution.objects.create(
                    strategy=strategy,
                    exchange=Exchange.objects.get(code=sell_action['exchange']),
                    action_type="SELL",
                    target_amount=Decimal(str(sell_action['amount'])),
                    target_price=Decimal(str(sell_action['price'])),
                    status="pending"
                )
                
                task = execute_single_exchange_action.delay(execution.id, user.id)
                execution_tasks.append(task)
            
            # Monitor overall strategy execution
            monitor_multi_strategy_execution.delay(strategy_id)
            
            # Create alert
            create_strategy_alert(
                user, strategy, "execution_started",
                f"Multi-exchange strategy execution started with {len(execution_tasks)} actions"
            )
            
        finally:
            loop.close()
            
    except Exception as e:
        logger.error(f"Error executing multi-exchange strategy {strategy_id}: {e}")
        if 'strategy' in locals():
            strategy.status = "failed"
            strategy.save()


@shared_task
def execute_single_exchange_action(execution_id: str, user_id: int):
    """
    Execute a single buy/sell action on one exchange as part of a multi-exchange strategy.
    """
    try:
        execution = MultiExchangeExecution.objects.get(id=execution_id)
        from django.contrib.auth.models import User
        user = User.objects.get(id=user_id)
        strategy = execution.strategy
        
        logger.info(f"Executing {execution.action_type} on {execution.exchange.name} for strategy {strategy.id}")
        
        # Get API credentials
        try:
            credential = APICredential.objects.get(
                user=user,
                exchange=execution.exchange,
                is_active=True
            )
        except APICredential.DoesNotExist:
            execution.status = "failed"
            execution.error_message = f"No API credentials found for {execution.exchange.name}"
            execution.save()
            return
        
        # Get service class
        service_class = EXCHANGE_SERVICES.get(execution.exchange.code)
        if not service_class:
            execution.status = "failed"
            execution.error_message = "Exchange service not implemented"
            execution.save()
            return
        
        # Execute order
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            start_time = timezone.now()
            
            async def place_order():
                async with service_class(
                    execution.exchange,
                    credential.api_key,
                    credential.api_secret
                ) as service:
                    result = await service.place_order(
                        symbol=strategy.trading_pair.symbol,
                        side=execution.action_type,
                        order_type="LIMIT",  # Default to limit orders for better control
                        amount=execution.target_amount,
                        price=execution.target_price
                    )
                    return result
            
            result = loop.run_until_complete(place_order())
            
            # Update execution
            execution.exchange_order_id = result["order_id"]
            execution.status = "order_placed"
            execution.order_placed_at = timezone.now()
            execution.execution_latency = (execution.order_placed_at - start_time).total_seconds()
            execution.save()
            
            # Monitor this specific execution
            monitor_single_execution.delay(execution_id)
            
        finally:
            loop.close()
            
    except Exception as e:
        logger.error(f"Error executing single action {execution_id}: {e}")
        if 'execution' in locals():
            execution.status = "failed"
            execution.error_message = str(e)
            execution.save()


@shared_task
def monitor_single_execution(execution_id: str):
    """
    Monitor the status of a single exchange execution.
    """
    try:
        execution = MultiExchangeExecution.objects.get(id=execution_id)
        
        if execution.status not in ["order_placed", "partially_filled"]:
            return
        
        # Get credentials
        try:
            credential = APICredential.objects.get(
                user_id=execution.strategy.executions.first().strategy.user_id,  # Get user from strategy
                exchange=execution.exchange,
                is_active=True
            )
        except (APICredential.DoesNotExist, AttributeError):
            execution.status = "failed"
            execution.error_message = "Cannot find user credentials"
            execution.save()
            return
        
        # Get service
        service_class = EXCHANGE_SERVICES.get(execution.exchange.code)
        if not service_class:
            return
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            async def check_status():
                async with service_class(
                    execution.exchange,
                    credential.api_key,
                    credential.api_secret
                ) as service:
                    return await service.get_order_status(
                        execution.exchange_order_id,
                        execution.strategy.trading_pair.symbol
                    )
            
            status = loop.run_until_complete(check_status())
            
            if status:
                # Update execution
                old_filled = execution.filled_amount
                execution.filled_amount = status.get("filled_amount", 0)
                
                if status.get("average_price"):
                    execution.average_price = status["average_price"]
                
                # Calculate slippage
                execution.calculate_slippage()
                
                # Update status
                if status["status"] == "FILLED":
                    execution.status = "filled"
                    execution.completed_at = timezone.now()
                    
                    if execution.order_placed_at:
                        execution.fill_latency = (execution.completed_at - execution.order_placed_at).total_seconds()
                    
                    if not execution.first_fill_at:
                        execution.first_fill_at = execution.completed_at
                        
                elif status["status"] == "PARTIAL":
                    execution.status = "partially_filled"
                    if not execution.first_fill_at and execution.filled_amount > old_filled:
                        execution.first_fill_at = timezone.now()
                        
                elif status["status"] == "CANCELLED":
                    execution.status = "cancelled"
                    execution.completed_at = timezone.now()
                
                execution.save()
                
                # Continue monitoring if not completed
                if execution.status in ["order_placed", "partially_filled"]:
                    monitor_single_execution.apply_async(
                        args=[execution_id],
                        countdown=5
                    )
                    
        finally:
            loop.close()
            
    except Exception as e:
        logger.error(f"Error monitoring execution {execution_id}: {e}")


@shared_task
def monitor_multi_strategy_execution(strategy_id: str):
    """
    Monitor the overall execution of a multi-exchange strategy.
    """
    try:
        strategy = MultiExchangeArbitrageStrategy.objects.get(id=strategy_id)
        
        if strategy.status != "executing":
            return
        
        # Get all executions for this strategy
        executions = strategy.executions.all()
        
        # Check completion status
        completed_executions = executions.filter(status="filled")
        failed_executions = executions.filter(status="failed")
        active_executions = executions.filter(status__in=["pending", "order_placed", "partially_filled"])
        
        total_executions = executions.count()
        
        # Check if strategy is complete
        if completed_executions.count() + failed_executions.count() == total_executions:
            # Strategy execution finished
            if failed_executions.count() == 0:
                # All executions successful
                strategy.status = "completed"
                strategy.execution_completed_at = timezone.now()
                
                # Calculate actual profit
                calculate_strategy_actual_profit(strategy)
                
                # Create success alert
                user = strategy.executions.first().strategy.user_id  # Get user from executions
                create_strategy_alert(
                    user, strategy, "strategy_success",
                    f"Strategy completed successfully with {completed_executions.count()}/{total_executions} executions"
                )
                
            else:
                # Some executions failed
                strategy.status = "failed"
                strategy.execution_completed_at = timezone.now()
                
                # Create failure alert
                user = strategy.executions.first().strategy.user_id
                create_strategy_alert(
                    user, strategy, "strategy_failed",
                    f"Strategy failed: {failed_executions.count()}/{total_executions} executions failed"
                )
            
            strategy.save()
            
        elif active_executions.exists():
            # Check for timeout
            max_execution_time = strategy.max_execution_time or 300  # 5 minutes default
            if strategy.execution_started_at and \
               timezone.now() > strategy.execution_started_at + timedelta(seconds=max_execution_time):
                
                # Cancel remaining active orders
                for execution in active_executions:
                    cancel_single_execution.delay(execution.id)
                
                strategy.status = "failed"
                strategy.execution_completed_at = timezone.now()
                strategy.save()
                
                # Create timeout alert
                user = strategy.executions.first().strategy.user_id
                create_strategy_alert(
                    user, strategy, "strategy_failed",
                    f"Strategy timed out after {max_execution_time} seconds"
                )
            else:
                # Continue monitoring
                monitor_multi_strategy_execution.apply_async(
                    args=[strategy_id],
                    countdown=10
                )
                
    except Exception as e:
        logger.error(f"Error monitoring multi-strategy {strategy_id}: {e}")


@shared_task
def cancel_single_execution(execution_id: str):
    """
    Cancel a single execution order.
    """
    try:
        execution = MultiExchangeExecution.objects.get(id=execution_id)
        
        if not execution.exchange_order_id or execution.status in ["filled", "cancelled", "failed"]:
            return
        
        # Get credentials
        try:
            credential = APICredential.objects.get(
                user_id=execution.strategy.executions.first().strategy.user_id,
                exchange=execution.exchange,
                is_active=True
            )
        except (APICredential.DoesNotExist, AttributeError):
            return
        
        # Get service
        service_class = EXCHANGE_SERVICES.get(execution.exchange.code)
        if not service_class:
            return
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            async def cancel():
                async with service_class(
                    execution.exchange,
                    credential.api_key,
                    credential.api_secret
                ) as service:
                    return await service.cancel_order(
                        execution.exchange_order_id,
                        execution.strategy.trading_pair.symbol
                    )
            
            success = loop.run_until_complete(cancel())
            
            if success:
                execution.status = "cancelled"
                execution.completed_at = timezone.now()
                execution.save()
                
        finally:
            loop.close()
            
    except Exception as e:
        logger.error(f"Error cancelling execution {execution_id}: {e}")


def calculate_strategy_actual_profit(strategy: MultiExchangeArbitrageStrategy):
    """
    Calculate the actual profit/loss from a completed strategy.
    """
    try:
        total_buy_cost = Decimal("0")
        total_sell_revenue = Decimal("0")
        total_fees = Decimal("0")
        
        # Calculate actual costs and revenues
        for execution in strategy.executions.filter(status="filled"):
            if execution.action_type == "BUY":
                cost = execution.filled_amount * (execution.average_price or execution.target_price)
                total_buy_cost += cost
                total_fees += execution.total_fee
            else:  # SELL
                revenue = execution.filled_amount * (execution.average_price or execution.target_price)
                total_sell_revenue += revenue
                total_fees += execution.total_fee
        
        # Calculate actual profit
        strategy.actual_profit = total_sell_revenue - total_buy_cost - total_fees
        
        if total_buy_cost > 0:
            strategy.actual_profit_percentage = (strategy.actual_profit / total_buy_cost) * 100
        
        strategy.save()
        
    except Exception as e:
        logger.error(f"Error calculating actual profit for strategy {strategy.id}: {e}")


# Legacy functions for backward compatibility

@shared_task
def execute_arbitrage_opportunity(
    opportunity_id: str,
    user_id: int,
    amount: Optional[float] = None,
    use_market_orders: bool = False
):
    """
    Execute a simple arbitrage opportunity (backward compatibility).
    """
    try:
        opportunity = ArbitrageOpportunity.objects.get(id=opportunity_id)
        from django.contrib.auth.models import User
        user = User.objects.get(id=user_id)
        
        logger.info(f"Executing simple arbitrage opportunity {opportunity.id}")
        
        # Get user credentials for both exchanges
        try:
            buy_credential = APICredential.objects.get(
                user=user,
                exchange=opportunity.buy_exchange,
                is_active=True
            )
            sell_credential = APICredential.objects.get(
                user=user,
                exchange=opportunity.sell_exchange,
                is_active=True
            )
        except APICredential.DoesNotExist:
            opportunity.status = "failed"
            opportunity.save()
            create_opportunity_alert(
                user, opportunity, "execution_failed",
                "Missing API credentials for one or both exchanges"
            )
            return
        
        # Create execution record
        execution = ArbitrageExecution.objects.create(
            opportunity=opportunity,
            user=user,
            status="pending"
        )
        
        # Update opportunity status
        opportunity.status = "executing"
        opportunity.save()
        
        # Get service classes
        buy_service_class = EXCHANGE_SERVICES.get(opportunity.buy_exchange.code)
        sell_service_class = EXCHANGE_SERVICES.get(opportunity.sell_exchange.code)
        
        if not buy_service_class or not sell_service_class:
            execution.status = "failed"
            execution.error_message = "Exchange service not implemented"
            execution.save()
            return
        
        # Execute trades
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            # Place buy order
            buy_result = loop.run_until_complete(
                place_buy_order(
                    opportunity,
                    execution,
                    buy_service_class,
                    buy_credential,
                    amount or opportunity.optimal_amount,
                    use_market_orders
                )
            )
            
            if not buy_result:
                return
            
            # Place sell order
            sell_result = loop.run_until_complete(
                place_sell_order(
                    opportunity,
                    execution,
                    sell_service_class,
                    sell_credential,
                    execution.buy_filled_amount,  # Use actual filled amount
                    use_market_orders
                )
            )
            
            if not sell_result:
                # Cancel buy order if sell fails
                loop.run_until_complete(
                    cancel_order(
                        buy_service_class,
                        opportunity.buy_exchange,
                        buy_credential,
                        execution.buy_order_id,
                        opportunity.trading_pair.symbol
                    )
                )
                return
            
            # Monitor execution status
            monitor_execution_status.delay(execution.id)
            
        finally:
            loop.close()
            
    except Exception as e:
        logger.error(f"Error executing arbitrage: {e}")
        if 'execution' in locals():
            execution.status = "failed"
            execution.error_message = str(e)
            execution.save()


async def place_buy_order(
    opportunity,
    execution,
    service_class,
    credential,
    amount,
    use_market_orders
):
    """
    Place buy order on exchange.
    """
    try:
        async with service_class(
            opportunity.buy_exchange,
            credential.api_key,
            credential.api_secret
        ) as service:
            # Place order
            order_type = "MARKET" if use_market_orders else "LIMIT"
            price = None if use_market_orders else opportunity.buy_price
            
            result = await service.place_order(
                symbol=opportunity.trading_pair.symbol,
                side="BUY",
                order_type=order_type,
                amount=amount,
                price=price
            )
            
            # Update execution
            execution.buy_order_id = result["order_id"]
            execution.buy_order_status = result["status"]
            execution.buy_order_placed_at = timezone.now()
            execution.status = "buy_placed"
            execution.save()
            
            # Create alert
            create_execution_alert(
                execution.user,
                opportunity,
                "execution_started",
                f"Buy order placed on {opportunity.buy_exchange.name}"
            )
            
            return True
            
    except Exception as e:
        logger.error(f"Error placing buy order: {e}")
        execution.status = "failed"
        execution.error_message = f"Buy order failed: {str(e)}"
        execution.save()
        return False


async def place_sell_order(
    opportunity,
    execution,
    service_class,
    credential,
    amount,
    use_market_orders
):
    """
    Place sell order on exchange.
    """
    try:
        async with service_class(
            opportunity.sell_exchange,
            credential.api_key,
            credential.api_secret
        ) as service:
            # Place order
            order_type = "MARKET" if use_market_orders else "LIMIT"
            price = None if use_market_orders else opportunity.sell_price
            
            result = await service.place_order(
                symbol=opportunity.trading_pair.symbol,
                side="SELL",
                order_type=order_type,
                amount=amount,
                price=price
            )
            
            # Update execution
            execution.sell_order_id = result["order_id"]
            execution.sell_order_status = result["status"]
            execution.sell_order_placed_at = timezone.now()
            execution.status = "sell_placed"
            execution.save()
            
            return True
            
    except Exception as e:
        logger.error(f"Error placing sell order: {e}")
        execution.status = "failed"
        execution.error_message = f"Sell order failed: {str(e)}"
        execution.save()
        return False


async def cancel_order(service_class, exchange, credential, order_id, symbol):
    """
    Cancel an order.
    """
    try:
        async with service_class(
            exchange,
            credential.api_key,
            credential.api_secret
        ) as service:
            await service.cancel_order(order_id, symbol)
    except Exception as e:
        logger.error(f"Error cancelling order: {e}")


@shared_task
def monitor_execution_status(execution_id: str):
    """
    Monitor the status of an arbitrage execution (backward compatibility).
    """
    try:
        execution = ArbitrageExecution.objects.get(id=execution_id)
        opportunity = execution.opportunity
        user = execution.user
        
        # Get credentials
        buy_credential = APICredential.objects.get(
            user=user,
            exchange=opportunity.buy_exchange
        )
        sell_credential = APICredential.objects.get(
            user=user,
            exchange=opportunity.sell_exchange
        )
        
        # Get service classes
        buy_service_class = EXCHANGE_SERVICES.get(opportunity.buy_exchange.code)
        sell_service_class = EXCHANGE_SERVICES.get(opportunity.sell_exchange.code)
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            # Check buy order status
            buy_status = loop.run_until_complete(
                check_order_status(
                    buy_service_class,
                    opportunity.buy_exchange,
                    buy_credential,
                    execution.buy_order_id,
                    opportunity.trading_pair.symbol
                )
            )
            
            # Update buy order info
            if buy_status:
                execution.buy_order_status = buy_status["status"]
                execution.buy_filled_amount = buy_status["filled_amount"]
                
                if buy_status["status"] == "FILLED":
                    execution.buy_order_filled_at = timezone.now()
                    execution.buy_average_price = buy_status.get("price")
                    execution.status = "buy_filled"
            
            # Check sell order status
            if execution.sell_order_id:
                sell_status = loop.run_until_complete(
                    check_order_status(
                        sell_service_class,
                        opportunity.sell_exchange,
                        sell_credential,
                        execution.sell_order_id,
                        opportunity.trading_pair.symbol
                    )
                )
                
                if sell_status:
                    execution.sell_order_status = sell_status["status"]
                    execution.sell_filled_amount = sell_status["filled_amount"]
                    
                    if sell_status["status"] == "FILLED":
                        execution.sell_order_filled_at = timezone.now()
                        execution.sell_average_price = sell_status.get("price")
                        execution.status = "sell_filled"
            
            # Check if both orders are filled
            if (execution.buy_order_status == "FILLED" and 
                execution.sell_order_status == "FILLED"):
                execution.status = "completed"
                execution.completed_at = timezone.now()
                
                # Calculate final profit
                execution.calculate_final_profit()
                
                # Update opportunity
                opportunity.status = "executed"
                opportunity.executed_at = timezone.now()
                opportunity.executed_amount = execution.buy_filled_amount
                opportunity.actual_profit = execution.final_profit
                opportunity.save()
                
                # Create completion alert
                create_execution_alert(
                    user,
                    opportunity,
                    "execution_completed",
                    f"Arbitrage completed. Profit: {execution.final_profit}"
                )
            
            execution.save()
            
            # Continue monitoring if not completed
            if execution.status not in ["completed", "failed", "cancelled"]:
                monitor_execution_status.apply_async(
                    args=[execution_id],
                    countdown=5  # Check again in 5 seconds
                )
                
        finally:
            loop.close()
            
    except Exception as e:
        logger.error(f"Error monitoring execution: {e}")


async def check_order_status(service_class, exchange, credential, order_id, symbol):
    """
    Check the status of an order.
    """
    try:
        async with service_class(
            exchange,
            credential.api_key,
            credential.api_secret
        ) as service:
            return await service.get_order_status(order_id, symbol)
    except Exception as e:
        logger.error(f"Error checking order status: {e}")
        return None


def should_alert_user(config: ArbitrageConfig, opportunity: ArbitrageOpportunity) -> bool:
    """
    Check if user should be alerted about an opportunity.
    """
    if not config.enable_notifications:
        return False
    
    # Check profit threshold
    if opportunity.net_profit_percentage < config.min_profit_percentage:
        return False
    
    # Check enabled exchanges
    if config.enabled_exchanges.exists():
        if (opportunity.buy_exchange not in config.enabled_exchanges.all() or
            opportunity.sell_exchange not in config.enabled_exchanges.all()):
            return False
    
    # Check enabled pairs
    if config.enabled_pairs.exists():
        if opportunity.trading_pair not in config.enabled_pairs.all():
            return False
    
    # Check for recent similar alerts
    recent_alert = ArbitrageAlert.objects.filter(
        user=config.user,
        opportunity__trading_pair=opportunity.trading_pair,
        opportunity__buy_exchange=opportunity.buy_exchange,
        opportunity__sell_exchange=opportunity.sell_exchange,
        created_at__gte=timezone.now() - timedelta(minutes=5)
    ).exists()
    
    return not recent_alert


def should_alert_user_multi(config: ArbitrageConfig, strategy: MultiExchangeArbitrageStrategy) -> bool:
    """
    Check if user should be alerted about a multi-exchange strategy.
    """
    if not config.enable_notifications or not config.enable_multi_exchange:
        return False
    
    # Check profit threshold
    if strategy.profit_percentage < config.min_profit_percentage:
        return False
    
    # Check enabled pairs
    if config.enabled_pairs.exists():
        if strategy.trading_pair not in config.enabled_pairs.all():
            return False
    
    # Check enabled exchanges
    if config.enabled_exchanges.exists():
        strategy_exchanges = set()
        for action in strategy.buy_actions + strategy.sell_actions:
            exchange = Exchange.objects.filter(code=action['exchange']).first()
            if exchange:
                strategy_exchanges.add(exchange)
        
        enabled_exchanges = set(config.enabled_exchanges.all())
        if not strategy_exchanges.issubset(enabled_exchanges):
            return False
    
    return True


def create_opportunity_alert(user, opportunity, alert_type="opportunity", custom_message=None):
    """
    Create an alert for a detected opportunity.
    """
    message = custom_message or (
        f"Profit: {opportunity.net_profit_percentage}% | "
        f"Buy: {opportunity.buy_exchange.name} @ {opportunity.buy_price} | "
        f"Sell: {opportunity.sell_exchange.name} @ {opportunity.sell_price}"
    )
    
    if opportunity.net_profit_percentage > Decimal("5"):
        alert_type = "high_profit"
    
    ArbitrageAlert.objects.create(
        user=user,
        opportunity=opportunity,
        alert_type=alert_type,
        title=f"Arbitrage Opportunity: {opportunity.trading_pair.symbol}",
        message=message,
        metadata={
            "profit_percentage": str(opportunity.net_profit_percentage),
            "estimated_profit": str(opportunity.estimated_profit),
            "optimal_amount": str(opportunity.optimal_amount)
        }
    )


def create_multi_strategy_alert(user, strategy, alert_type="multi_opportunity"):
    """
    Create an alert for a multi-exchange strategy.
    """
    involved_exchanges = ", ".join(strategy.get_involved_exchanges())
    
    ArbitrageAlert.objects.create(
        user=user,
        multi_strategy=strategy,
        alert_type=alert_type,
        title=f"Multi-Exchange Strategy: {strategy.trading_pair.symbol}",
        message=(
            f"Type: {strategy.strategy_type} | "
            f"Profit: {strategy.profit_percentage}% | "
            f"Exchanges: {involved_exchanges} | "
            f"Actions: {len(strategy.buy_actions)} buy, {len(strategy.sell_actions)} sell"
        ),
        metadata={
            "profit_percentage": str(strategy.profit_percentage),
            "estimated_profit": str(strategy.estimated_profit),
            "strategy_type": strategy.strategy_type,
            "complexity_score": strategy.complexity_score
        }
    )


def create_strategy_alert(user, strategy, alert_type, message):
    """
    Create an alert for strategy execution events.
    """
    ArbitrageAlert.objects.create(
        user=user,
        multi_strategy=strategy,
        alert_type=alert_type,
        title=f"Strategy {alert_type.replace('_', ' ').title()}",
        message=message
    )


def create_execution_alert(user, opportunity, alert_type, message):
    """
    Create an alert for execution events.
    """
    ArbitrageAlert.objects.create(
        user=user,
        opportunity=opportunity,
        alert_type=alert_type,
        title=f"Arbitrage {alert_type.replace('_', ' ').title()}",
        message=message
    )


@shared_task
def cleanup_old_opportunities():
    """
    Clean up old arbitrage opportunities and strategies.
    """
    # Delete opportunities older than 7 days
    cutoff_date = timezone.now() - timedelta(days=7)
    
    deleted_opportunities = ArbitrageOpportunity.objects.filter(
        created_at__lt=cutoff_date,
        status__in=["expired", "failed"]
    ).delete()[0]
    
    deleted_strategies = MultiExchangeArbitrageStrategy.objects.filter(
        created_at__lt=cutoff_date,
        status__in=["expired", "failed"]
    ).delete()[0]
    
    logger.info(f"Deleted {deleted_opportunities} old opportunities and {deleted_strategies} old strategies")
    
    return {"opportunities": deleted_opportunities, "strategies": deleted_strategies}


@shared_task
def generate_daily_report():
    """
    Generate daily arbitrage report for active users.
    """
    # Get active users with completed executions
    users_with_activity = (
        ArbitrageExecution.objects
        .filter(
            created_at__gte=timezone.now() - timedelta(hours=24),
            status="completed"
        )
        .values_list("user", flat=True)
        .distinct()
    )
    
    # Also include users with completed multi-exchange strategies
    users_with_multi_activity = (
        MultiExchangeArbitrageStrategy.objects
        .filter(
            created_at__gte=timezone.now() - timedelta(hours=24),
            status="completed"
        )
        .values_list("executions__strategy__user", flat=True)
        .distinct()
    )
    
    all_active_users = set(users_with_activity) | set(users_with_multi_activity)
    
    for user_id in all_active_users:
        try:
            # Generate report for user
            # This would send an email or create a notification
            logger.info(f"Generated daily report for user {user_id}")
        except Exception as e:
            logger.error(f"Error generating report for user {user_id}: {e}")


# Additional tasks for enhanced multi-exchange arbitrage system
# These should be added to the existing arbitrage/tasks.py file

@shared_task
def monitor_active_multi_strategies():
    """
    Monitor all active multi-exchange strategies and check their status.
    """
    from arbitrage.models import MultiExchangeArbitrageStrategy
    
    active_strategies = MultiExchangeArbitrageStrategy.objects.filter(
        status__in=['executing', 'validating']
    )
    
    monitored_count = 0
    for strategy in active_strategies:
        try:
            # Check if strategy has timed out
            if strategy.execution_started_at:
                max_time = strategy.max_execution_time or 300
                elapsed = (timezone.now() - strategy.execution_started_at).total_seconds()
                
                if elapsed > max_time:
                    # Strategy has timed out
                    strategy.status = 'failed'
                    strategy.execution_completed_at = timezone.now()
                    strategy.save()
                    
                    # Cancel all pending executions
                    for execution in strategy.executions.filter(
                        status__in=['pending', 'order_placed', 'partially_filled']
                    ):
                        cancel_single_execution.delay(execution.id)
                    
                    # Create timeout alert
                    from django.contrib.auth.models import User
                    try:
                        user = User.objects.get(
                            id=strategy.executions.first().strategy.user_id
                        )
                        create_strategy_alert(
                            user, strategy, "strategy_failed",
                            f"Strategy timed out after {max_time} seconds"
                        )
                    except:
                        pass
            
            monitored_count += 1
            
        except Exception as e:
            logger.error(f"Error monitoring strategy {strategy.id}: {e}")
    
    return f"Monitored {monitored_count} active strategies"


@shared_task
def validate_active_strategies():
    """
    Validate that active strategies are still viable for execution.
    """
    from arbitrage.models import MultiExchangeArbitrageStrategy
    from arbitrage.engine import MultiExchangeArbitrageEngine
    
    active_strategies = MultiExchangeArbitrageStrategy.objects.filter(
        status='detected',
        expires_at__gt=timezone.now()
    )
    
    engine = MultiExchangeArbitrageEngine()
    validated_count = 0
    invalidated_count = 0
    
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        for strategy in active_strategies:
            try:
                is_valid, message = loop.run_until_complete(
                    engine.validate_strategy(strategy)
                )
                
                if not is_valid:
                    strategy.status = 'expired'
                    strategy.save()
                    invalidated_count += 1
                    logger.info(f"Invalidated strategy {strategy.id}: {message}")
                else:
                    validated_count += 1
                    
            except Exception as e:
                logger.error(f"Error validating strategy {strategy.id}: {e}")
                strategy.status = 'failed'
                strategy.save()
                invalidated_count += 1
    
    finally:
        loop.close()
    
    return f"Validated {validated_count} strategies, invalidated {invalidated_count}"


@shared_task
def calculate_strategy_risks():
    """
    Calculate risk scores for active multi-exchange strategies.
    """
    from arbitrage.models import MultiExchangeArbitrageStrategy
    from exchanges.models import ExchangeStatus
    
    active_strategies = MultiExchangeArbitrageStrategy.objects.filter(
        status='detected',
        expires_at__gt=timezone.now()
    )
    
    calculated_count = 0
    
    for strategy in active_strategies:
        try:
            risk_score = Decimal("0")
            
            # Factor 1: Complexity (more exchanges = higher risk)
            complexity_risk = min(strategy.complexity_score * 5, 30)
            risk_score += complexity_risk
            
            # Factor 2: Exchange reliability
            exchange_codes = []
            for action in strategy.buy_actions + strategy.sell_actions:
                exchange_codes.append(action['exchange'])
            
            exchange_reliability = Decimal("100")
            for code in set(exchange_codes):
                try:
                    exchange = Exchange.objects.get(code=code)
                    status = ExchangeStatus.objects.filter(exchange=exchange).first()
                    if status:
                        # Lower uptime = higher risk
                        reliability = status.uptime_percentage or 95
                        exchange_reliability = min(exchange_reliability, reliability)
                except:
                    exchange_reliability = min(exchange_reliability, Decimal("90"))
            
            reliability_risk = (100 - exchange_reliability) * 2
            risk_score += reliability_risk
            
            # Factor 3: Profit margin (lower profit = higher risk for execution)
            if strategy.profit_percentage < 1:
                profit_risk = (1 - strategy.profit_percentage) * 20
                risk_score += profit_risk
            
            # Factor 4: Market volatility (more volatile = higher risk)
            volatility_risk = 0  # This would be calculated from price history
            risk_score += volatility_risk
            
            # Factor 5: Execution time window (longer = higher risk)
            if strategy.max_execution_time > 60:
                time_risk = (strategy.max_execution_time - 60) / 10
                risk_score += time_risk
            
            # Cap risk score at 100
            strategy.risk_score = min(risk_score, Decimal("100"))
            strategy.save()
            
            calculated_count += 1
            
        except Exception as e:
            logger.error(f"Error calculating risk for strategy {strategy.id}: {e}")
    
    return f"Calculated risk scores for {calculated_count} strategies"


@shared_task
def update_exchange_reliability():
    """
    Update exchange reliability weights based on recent performance.
    """
    from exchanges.models import ExchangeStatus
    from arbitrage.models import ArbitrageConfig
    
    exchanges = Exchange.objects.filter(is_active=True)
    reliability_data = {}
    
    # Calculate reliability metrics for each exchange
    for exchange in exchanges:
        try:
            # Get recent status records (last 24 hours)
            recent_statuses = ExchangeStatus.objects.filter(
                exchange=exchange,
                last_check__gte=timezone.now() - timedelta(hours=24)
            ).order_by('-last_check')
            
            if recent_statuses.exists():
                # Calculate uptime percentage
                total_checks = recent_statuses.count()
                online_checks = recent_statuses.filter(is_online=True).count()
                uptime = (online_checks / total_checks) * 100 if total_checks > 0 else 0
                
                # Calculate average response time
                avg_response_time = recent_statuses.filter(
                    response_time__isnull=False
                ).aggregate(avg=models.Avg('response_time'))['avg'] or 0
                
                # Calculate error rate
                error_rate = recent_statuses.filter(
                    is_online=False
                ).count() / total_checks * 100 if total_checks > 0 else 0
                
                # Calculate overall reliability score (0.0 to 1.0)
                reliability_score = (
                    (uptime / 100) * 0.5 +  # 50% weight for uptime
                    (max(0, (5 - avg_response_time) / 5)) * 0.3 +  # 30% weight for response time
                    (max(0, (100 - error_rate) / 100)) * 0.2  # 20% weight for error rate
                )
                
                reliability_data[exchange.code] = max(0.1, min(1.0, reliability_score))
            else:
                # Default reliability for exchanges without recent data
                reliability_data[exchange.code] = 0.8
                
        except Exception as e:
            logger.error(f"Error calculating reliability for {exchange.name}: {e}")
            reliability_data[exchange.code] = 0.5  # Default middle value
    
    # Update all user configs with new reliability weights
    updated_configs = 0
    for config in ArbitrageConfig.objects.filter(enable_multi_exchange=True):
        try:
            config.exchange_reliability_weights = reliability_data
            config.save()
            updated_configs += 1
        except Exception as e:
            logger.error(f"Error updating config for user {config.user.id}: {e}")
    
    return f"Updated reliability weights for {len(reliability_data)} exchanges in {updated_configs} configs"


@shared_task
def optimize_allocation_strategies():
    """
    Optimize allocation strategies based on historical performance.
    """
    from arbitrage.models import ArbitrageConfig, MultiExchangeArbitrageStrategy
    
    # Analyze performance of different allocation strategies
    strategy_performance = {}
    
    # Get completed strategies from last 30 days
    recent_strategies = MultiExchangeArbitrageStrategy.objects.filter(
        status='completed',
        created_at__gte=timezone.now() - timedelta(days=30)
    )
    
    # Group by strategy characteristics and analyze performance
    for strategy in recent_strategies:
        strategy_key = f"{strategy.strategy_type}_{strategy.complexity_score}"
        
        if strategy_key not in strategy_performance:
            strategy_performance[strategy_key] = {
                'count': 0,
                'total_profit': Decimal('0'),
                'total_profit_percentage': Decimal('0'),
                'success_rate': Decimal('0'),
                'avg_execution_time': 0
            }
        
        perf = strategy_performance[strategy_key]
        perf['count'] += 1
        
        if strategy.actual_profit:
            perf['total_profit'] += strategy.actual_profit
        if strategy.actual_profit_percentage:
            perf['total_profit_percentage'] += strategy.actual_profit_percentage
        
        # Calculate execution time
        if strategy.execution_started_at and strategy.execution_completed_at:
            execution_time = (strategy.execution_completed_at - strategy.execution_started_at).total_seconds()
            perf['avg_execution_time'] = (perf['avg_execution_time'] * (perf['count'] - 1) + execution_time) / perf['count']
    
    # Calculate success rates and averages
    for key, perf in strategy_performance.items():
        if perf['count'] > 0:
            perf['avg_profit'] = perf['total_profit'] / perf['count']
            perf['avg_profit_percentage'] = perf['total_profit_percentage'] / perf['count']
    
    # Find optimal strategies
    optimal_strategies = sorted(
        strategy_performance.items(),
        key=lambda x: x[1]['avg_profit_percentage'],
        reverse=True
    )[:5]
    
    # Update configurations with optimization recommendations
    optimization_data = {
        'last_optimization': timezone.now().isoformat(),
        'optimal_strategies': dict(optimal_strategies),
        'recommendations': {
            'best_strategy_type': optimal_strategies[0][0].split('_')[0] if optimal_strategies else 'one_to_many',
            'optimal_complexity': int(optimal_strategies[0][0].split('_')[1]) if optimal_strategies else 3,
        }
    }
    
    # Store optimization results (could be in a separate model)
    from django.core.cache import cache
    cache.set('arbitrage_optimization_results', optimization_data, 86400)  # 24 hours
    
    return f"Optimized allocation strategies based on {len(recent_strategies)} historical strategies"


@shared_task
def generate_performance_comparison():
    """
    Generate detailed performance comparison between simple and multi-exchange strategies.
    """
    from arbitrage.models import ArbitrageExecution, MultiExchangeArbitrageStrategy
    from django.core.mail import send_mail
    from django.template.loader import render_to_string
    
    # Get data for last 7 days
    week_ago = timezone.now() - timedelta(days=7)
    
    # Simple arbitrage data
    simple_executions = ArbitrageExecution.objects.filter(
        created_at__gte=week_ago,
        status='completed'
    )
    
    simple_stats = {
        'count': simple_executions.count(),
        'total_profit': simple_executions.aggregate(
            total=models.Sum('final_profit')
        )['total'] or Decimal('0'),
        'avg_profit': simple_executions.aggregate(
            avg=models.Avg('final_profit')
        )['avg'] or Decimal('0'),
        'success_rate': 100,  # Only completed executions
    }
    
    # Multi-exchange data
    multi_strategies = MultiExchangeArbitrageStrategy.objects.filter(
        created_at__gte=week_ago
    )
    
    completed_multi = multi_strategies.filter(status='completed')
    failed_multi = multi_strategies.filter(status='failed')
    
    multi_stats = {
        'count': multi_strategies.count(),
        'completed': completed_multi.count(),
        'failed': failed_multi.count(),
        'total_profit': completed_multi.aggregate(
            total=models.Sum('actual_profit')
        )['total'] or Decimal('0'),
        'avg_profit': completed_multi.aggregate(
            avg=models.Avg('actual_profit')
        )['avg'] or Decimal('0'),
        'success_rate': (completed_multi.count() / multi_strategies.count() * 100) if multi_strategies.count() > 0 else 0,
    }
    
    # Generate report
    report_data = {
        'period': 'Last 7 days',
        'simple': simple_stats,
        'multi': multi_stats,
        'generated_at': timezone.now(),
        'total_profit': simple_stats['total_profit'] + multi_stats['total_profit'],
    }
    
    # Store report in cache
    cache.set('weekly_performance_report', report_data, 86400 * 7)  # 1 week
    
    # Send email to administrators (if configured)
    try:
        admin_emails = ['admin@example.com']  # Configure in settings
        if admin_emails:
            subject = f"Weekly Arbitrage Performance Report - {timezone.now().strftime('%Y-%m-%d')}"
            message = f"""
            Weekly Performance Summary:
            
            Simple Arbitrage:
            - Executions: {simple_stats['count']}
            - Total Profit: {simple_stats['total_profit']}
            - Average Profit: {simple_stats['avg_profit']}
            
            Multi-Exchange Strategies:
            - Total Strategies: {multi_stats['count']}
            - Completed: {multi_stats['completed']}
            - Success Rate: {multi_stats['success_rate']:.1f}%
            - Total Profit: {multi_stats['total_profit']}
            - Average Profit: {multi_stats['avg_profit']}
            
            Combined Total Profit: {report_data['total_profit']}
            """
            
            send_mail(
                subject,
                message,
                'noreply@arbitrage.local',
                admin_emails,
                fail_silently=True
            )
    except Exception as e:
        logger.error(f"Error sending performance report email: {e}")
    
    return f"Generated performance comparison report"


@shared_task
def cleanup_failed_executions():
    """
    Clean up failed executions and associated data.
    """
    from arbitrage.models import MultiExchangeExecution, ArbitrageExecution
    
    # Clean up old failed multi-exchange executions (older than 7 days)
    old_failed_multi = MultiExchangeExecution.objects.filter(
        status='failed',
        created_at__lt=timezone.now() - timedelta(days=7)
    )
    
    deleted_multi = old_failed_multi.count()
    old_failed_multi.delete()
    
    # Clean up old failed simple executions (older than 7 days)
    old_failed_simple = ArbitrageExecution.objects.filter(
        status='failed',
        created_at__lt=timezone.now() - timedelta(days=7)
    )
    
    deleted_simple = old_failed_simple.count()
    old_failed_simple.delete()
    
    # Clean up orphaned execution records
    orphaned_multi = MultiExchangeExecution.objects.filter(
        strategy__isnull=True
    )
    deleted_orphaned = orphaned_multi.count()
    orphaned_multi.delete()
    
    return f"Cleaned up {deleted_simple} simple and {deleted_multi} multi-exchange failed executions, {deleted_orphaned} orphaned records"


@shared_task
def backup_strategy_configs():
    """
    Backup user strategy configurations and important settings.
    """
    from arbitrage.models import ArbitrageConfig
    import json
    
    # Get all active configurations
    configs = ArbitrageConfig.objects.filter(is_active=True)
    
    backup_data = {
        'backup_date': timezone.now().isoformat(),
        'configs': []
    }
    
    for config in configs:
        config_data = {
            'user_id': config.user.id,
            'username': config.user.username,
            'settings': {
                'min_profit_percentage': str(config.min_profit_percentage),
                'enable_multi_exchange': config.enable_multi_exchange,
                'max_exchanges_per_strategy': config.max_exchanges_per_strategy,
                'allocation_strategy': config.allocation_strategy,
                'max_allocation_per_exchange': str(config.max_allocation_per_exchange),
                'auto_trade': config.auto_trade,
                'enabled_exchanges': [e.code for e in config.enabled_exchanges.all()],
                'enabled_pairs': [p.symbol for p in config.enabled_pairs.all()],
            }
        }
        backup_data['configs'].append(config_data)
    
    # Store backup in cache (in production, this should go to a file or database)
    cache.set(
        f'config_backup_{timezone.now().strftime("%Y%m%d")}',
        backup_data,
        86400 * 30  # 30 days
    )
    
    logger.info(f"Backed up {len(backup_data['configs'])} strategy configurations")
    
    return f"Backed up {len(backup_data['configs'])} configurations"


# Additional utility tasks

@shared_task
def stress_test_strategy_detection():
    """
    Stress test the strategy detection system.
    """
    from arbitrage.engine import MultiExchangeArbitrageEngine
    
    engine = MultiExchangeArbitrageEngine()
    
    # Get all active pairs for testing
    active_pairs = list(TradingPair.objects.filter(is_active=True)[:5])  # Limit for testing
    active_exchanges = list(Exchange.objects.filter(is_active=True))
    
    if not active_pairs or len(active_exchanges) < 2:
        return "Insufficient data for stress test"
    
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        start_time = timezone.now()
        
        # Run multiple scans concurrently
        tasks = []
        for _ in range(5):  # Run 5 concurrent scans
            task = engine.scan_all_opportunities(
                enabled_exchanges=active_exchanges,
                enabled_pairs=active_pairs
            )
            tasks.append(task)
        
        results = loop.run_until_complete(asyncio.gather(*tasks, return_exceptions=True))
        
        end_time = timezone.now()
        duration = (end_time - start_time).total_seconds()
        
        # Analyze results
        total_opportunities = 0
        total_strategies = 0
        errors = 0
        
        for result in results:
            if isinstance(result, Exception):
                errors += 1
            elif isinstance(result, list):
                for item in result:
                    if isinstance(item, ArbitrageOpportunity):
                        total_opportunities += 1
                    elif isinstance(item, MultiExchangeArbitrageStrategy):
                        total_strategies += 1
        
        stress_test_result = {
            'test_duration': duration,
            'concurrent_scans': 5,
            'total_opportunities': total_opportunities,
            'total_strategies': total_strategies,
            'errors': errors,
            'avg_scan_time': duration / 5,
            'performance_rating': 'Good' if duration < 30 and errors == 0 else 'Poor'
        }
        
        # Store test results
        cache.set('stress_test_results', stress_test_result, 3600)
        
        return f"Stress test completed: {total_opportunities + total_strategies} items found in {duration:.2f}s"
        
    finally:
        loop.close()


@shared_task
def generate_market_efficiency_report():
    """
    Generate a report on market efficiency and arbitrage opportunities.
    """
    from arbitrage.models import ArbitrageOpportunity, MultiExchangeArbitrageStrategy
    
    # Analyze market efficiency over different time periods
    periods = {
        '1h': timedelta(hours=1),
        '24h': timedelta(hours=24),
        '7d': timedelta(days=7),
    }
    
    efficiency_data = {}
    
    for period_name, period_delta in periods.items():
        start_time = timezone.now() - period_delta
        
        # Simple opportunities
        simple_opps = ArbitrageOpportunity.objects.filter(
            created_at__gte=start_time
        )
        
        # Multi-exchange strategies
        multi_strategies = MultiExchangeArbitrageStrategy.objects.filter(
            created_at__gte=start_time
        )
        
        # Calculate efficiency metrics
        total_opportunities = simple_opps.count() + multi_strategies.count()
        
        if total_opportunities > 0:
            avg_simple_profit = simple_opps.aggregate(
                avg=models.Avg('net_profit_percentage')
            )['avg'] or Decimal('0')
            
            avg_multi_profit = multi_strategies.aggregate(
                avg=models.Avg('profit_percentage')
            )['avg'] or Decimal('0')
            
            # Market efficiency score (lower profit margins = more efficient market)
            efficiency_score = 100 - min(100, (avg_simple_profit + avg_multi_profit) * 10)
        else:
            avg_simple_profit = Decimal('0')
            avg_multi_profit = Decimal('0')
            efficiency_score = 100  # Perfect efficiency if no opportunities
        
        efficiency_data[period_name] = {
            'total_opportunities': total_opportunities,
            'simple_opportunities': simple_opps.count(),
            'multi_strategies': multi_strategies.count(),
            'avg_simple_profit': float(avg_simple_profit),
            'avg_multi_profit': float(avg_multi_profit),
            'efficiency_score': float(efficiency_score),
            'opportunity_frequency': total_opportunities / (period_delta.total_seconds() / 3600),  # per hour
        }
    
    # Store efficiency report
    efficiency_report = {
        'generated_at': timezone.now().isoformat(),
        'periods': efficiency_data,
        'summary': {
            'trend': 'improving' if efficiency_data['1h']['efficiency_score'] > efficiency_data['24h']['efficiency_score'] else 'declining',
            'most_efficient_period': max(efficiency_data.keys(), key=lambda k: efficiency_data[k]['efficiency_score']),
        }
    }
    
    cache.set('market_efficiency_report', efficiency_report, 3600)
    
    return f"Generated market efficiency report covering {len(periods)} time periods"