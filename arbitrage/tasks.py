
import asyncio
import logging
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Optional

from celery import shared_task
from django.core.cache import cache
from django.db import transaction
from django.utils import timezone

from arbitrage.engine import ArbitrageEngine
from arbitrage.models import (
    ArbitrageAlert,
    ArbitrageConfig,
    ArbitrageExecution,
    ArbitrageOpportunity,
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
    Periodic task to scan for arbitrage opportunities.
    """
    logger.info("Starting arbitrage scan...")
    
    # Get all active user configs
    active_configs = ArbitrageConfig.objects.filter(
        is_active=True
    ).select_related("user")
    
    # Run async scan
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        engine = ArbitrageEngine()
        
        # Scan for opportunities
        opportunities = loop.run_until_complete(
            engine.scan_all_opportunities()
        )
        
        logger.info(f"Found {len(opportunities)} opportunities")
        
        # Save opportunities
        with transaction.atomic():
            for opp in opportunities:
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
                    
                    # Check user configs for alerts
                    for config in active_configs:
                        if should_alert_user(config, opp):
                            create_opportunity_alert(config.user, opp)
                            
                            # Auto-execute if enabled
                            if config.auto_trade:
                                execute_arbitrage_opportunity.delay(
                                    opp.id,
                                    config.user.id
                                )
        
        # Mark expired opportunities
        loop.run_until_complete(engine.mark_expired_opportunities())
        
    except Exception as e:
        logger.error(f"Error in arbitrage scan: {e}")
    finally:
        loop.close()
    
    return f"Scan completed. Found {len(opportunities)} opportunities."


@shared_task
def execute_arbitrage_opportunity(
    execution_id: str,
    amount: Optional[float] = None,
    use_market_orders: bool = False
):
    """
    Execute an arbitrage opportunity.
    """
    try:
        execution = ArbitrageExecution.objects.get(id=execution_id)
        opportunity = execution.opportunity
        user = execution.user
        
        logger.info(f"Executing arbitrage opportunity {opportunity.id}")
        
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
            execution.status = "failed"
            execution.error_message = "Missing API credentials for one or both exchanges"
            execution.save()
            return
        
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
            
            # Monitor order status
            monitor_execution_status.delay(execution_id)
            
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
    Monitor the status of an arbitrage execution.
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


def create_opportunity_alert(user, opportunity):
    """
    Create an alert for a detected opportunity.
    """
    alert_type = "opportunity"
    if opportunity.net_profit_percentage > Decimal("5"):
        alert_type = "high_profit"
    
    ArbitrageAlert.objects.create(
        user=user,
        opportunity=opportunity,
        alert_type=alert_type,
        title=f"Arbitrage Opportunity: {opportunity.trading_pair.symbol}",
        message=(
            f"Profit: {opportunity.net_profit_percentage}% | "
            f"Buy: {opportunity.buy_exchange.name} @ {opportunity.buy_price} | "
            f"Sell: {opportunity.sell_exchange.name} @ {opportunity.sell_price}"
        ),
        metadata={
            "profit_percentage": str(opportunity.net_profit_percentage),
            "estimated_profit": str(opportunity.estimated_profit),
            "optimal_amount": str(opportunity.optimal_amount)
        }
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
    Clean up old arbitrage opportunities.
    """
    # Delete opportunities older than 7 days
    cutoff_date = timezone.now() - timedelta(days=7)
    
    deleted_count = ArbitrageOpportunity.objects.filter(
        created_at__lt=cutoff_date,
        status__in=["expired", "failed"]
    ).delete()[0]
    
    logger.info(f"Deleted {deleted_count} old opportunities")
    
    return deleted_count


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
    
    for user_id in users_with_activity:
        try:
            # Generate report for user
            # This would send an email or create a notification
            logger.info(f"Generated daily report for user {user_id}")
        except Exception as e:
            logger.error(f"Error generating report for user {user_id}: {e}")