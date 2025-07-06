import asyncio
import logging
from datetime import datetime, timedelta
from decimal import Decimal

from celery import shared_task
from django.db import transaction
from django.utils import timezone

from core.models import APICredential
from exchanges.services.nobitex import NobitexService
from exchanges.services.ramzinex import RamzinexService
from exchanges.services.wallex import WallexService
from trading.models import Order, Position, Trade, TradingAlert, TradingStrategy

logger = logging.getLogger(__name__)

# Service mapping
EXCHANGE_SERVICES = {
    "nobitex": NobitexService,
    "wallex": WallexService,
    "ramzinex": RamzinexService,
}


@shared_task
def execute_order(order_id: str):
    """
    Execute an order on the exchange.
    """
    try:
        order = Order.objects.get(id=order_id)
        user = order.user
        
        # Get API credentials
        try:
            credential = APICredential.objects.get(
                user=user,
                exchange=order.exchange,
                is_active=True
            )
        except APICredential.DoesNotExist:
            order.status = "REJECTED"
            order.save()
            create_trading_alert(
                user,
                "ORDER_CANCELLED",
                "Order Rejected",
                f"No API credentials found for {order.exchange.name}",
                order=order
            )
            return
        
        # Get service class
        service_class = EXCHANGE_SERVICES.get(order.exchange.code)
        if not service_class:
            order.status = "REJECTED"
            order.save()
            return
        
        # Execute order
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            async def place():
                async with service_class(
                    order.exchange,
                    credential.api_key,
                    credential.api_secret
                ) as service:
                    result = await service.place_order(
                        symbol=order.trading_pair.symbol,
                        side=order.side,
                        order_type=order.order_type,
                        amount=order.amount,
                        price=order.price
                    )
                    return result
            
            result = loop.run_until_complete(place())
            
            # Update order
            order.exchange_order_id = result["order_id"]
            order.status = result.get("status", "OPEN")
            order.save()
            
            # Monitor order status
            monitor_order_status.delay(order_id)
            
            # Create alert
            create_trading_alert(
                user,
                "ORDER_PLACED",
                "Order Placed",
                f"{order.side} {order.amount} {order.trading_pair.symbol} on {order.exchange.name}",
                order=order
            )
            
        finally:
            loop.close()
            
    except Exception as e:
        logger.error(f"Error executing order {order_id}: {e}")
        if 'order' in locals():
            order.status = "REJECTED"
            order.save()


@shared_task
def monitor_order_status(order_id: str):
    """
    Monitor the status of an order.
    """
    try:
        order = Order.objects.get(id=order_id)
        
        if not order.is_open:
            return
        
        # Get credentials
        credential = APICredential.objects.get(
            user=order.user,
            exchange=order.exchange,
            is_active=True
        )
        
        # Get service
        service_class = EXCHANGE_SERVICES.get(order.exchange.code)
        if not service_class:
            return
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            async def check_status():
                async with service_class(
                    order.exchange,
                    credential.api_key,
                    credential.api_secret
                ) as service:
                    return await service.get_order_status(
                        order.exchange_order_id,
                        order.trading_pair.symbol
                    )
            
            status = loop.run_until_complete(check_status())
            
            if status:
                # Update order
                old_status = order.status
                order.status = status["status"]
                order.filled_amount = status.get("filled_amount", 0)
                
                if status.get("average_price"):
                    order.average_price = status["average_price"]
                
                if order.status == "FILLED":
                    order.filled_at = timezone.now()
                    
                    # Create trade record
                    Trade.objects.create(
                        order=order,
                        exchange_trade_id=order.exchange_order_id,
                        price=order.average_price or order.price,
                        amount=order.filled_amount,
                        fee=order.fee,
                        fee_currency=order.fee_currency,
                        executed_at=order.filled_at
                    )
                    
                    # Update position if linked
                    update_position_from_order(order)
                    
                    # Create alert
                    create_trading_alert(
                        order.user,
                        "ORDER_FILLED",
                        "Order Filled",
                        f"Order {order.exchange_order_id} filled at {order.average_price}",
                        order=order
                    )
                
                elif order.status == "CANCELLED":
                    order.cancelled_at = timezone.now()
                
                order.save()
                
                # Continue monitoring if still open
                if order.is_open:
                    monitor_order_status.apply_async(
                        args=[order_id],
                        countdown=5
                    )
                    
        finally:
            loop.close()
            
    except Exception as e:
        logger.error(f"Error monitoring order {order_id}: {e}")


@shared_task
def cancel_order_on_exchange(order_id: str, reason: str = None):
    """
    Cancel an order on the exchange.
    """
    try:
        order = Order.objects.get(id=order_id)
        
        if not order.is_open:
            return
        
        # Get credentials
        credential = APICredential.objects.get(
            user=order.user,
            exchange=order.exchange,
            is_active=True
        )
        
        # Get service
        service_class = EXCHANGE_SERVICES.get(order.exchange.code)
        if not service_class:
            return
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            async def cancel():
                async with service_class(
                    order.exchange,
                    credential.api_key,
                    credential.api_secret
                ) as service:
                    return await service.cancel_order(
                        order.exchange_order_id,
                        order.trading_pair.symbol
                    )
            
            success = loop.run_until_complete(cancel())
            
            if success:
                order.status = "CANCELLED"
                order.cancelled_at = timezone.now()
                order.save()
                
                # Create alert
                create_trading_alert(
                    order.user,
                    "ORDER_CANCELLED",
                    "Order Cancelled",
                    f"Order {order.exchange_order_id} cancelled. Reason: {reason or 'User requested'}",
                    order=order
                )
                
        finally:
            loop.close()
            
    except Exception as e:
        logger.error(f"Error cancelling order {order_id}: {e}")


@shared_task
def run_trading_strategy(strategy_id: int):
    """
    Execute a trading strategy.
    """
    try:
        strategy = TradingStrategy.objects.get(id=strategy_id)
        
        if not strategy.is_active:
            return
        
        logger.info(f"Running strategy: {strategy.name}")
        
        # Update last run time
        strategy.last_run = timezone.now()
        strategy.save()
        
        # Execute based on strategy type
        if strategy.strategy_type == "ARBITRAGE":
            # This is handled by arbitrage engine
            pass
        elif strategy.strategy_type == "DCA":
            execute_dca_strategy(strategy)
        elif strategy.strategy_type == "MARKET_MAKING":
            execute_market_making_strategy(strategy)
        # Add more strategy types as needed
        
        # Schedule next run
        if strategy.is_active:
            # Default to run every 5 minutes
            next_run_delay = strategy.config.get("run_interval", 300)
            run_trading_strategy.apply_async(
                args=[strategy_id],
                countdown=next_run_delay
            )
            
    except Exception as e:
        logger.error(f"Error running strategy {strategy_id}: {e}")


def execute_dca_strategy(strategy: TradingStrategy):
    """
    Execute Dollar Cost Averaging strategy.
    """
    config = strategy.config
    amount_per_trade = Decimal(str(config.get("amount_per_trade", 100)))
    
    # Get enabled pairs and exchanges
    for pair in strategy.enabled_pairs.all():
        for exchange in strategy.enabled_exchanges.all():
            try:
                # Create buy order
                order = Order.objects.create(
                    user=strategy.user,
                    exchange=exchange,
                    trading_pair=pair,
                    order_type="MARKET",
                    side="BUY",
                    amount=amount_per_trade / pair.last_price,  # Simplified
                    status="PENDING",
                    is_arbitrage=False,
                    metadata={"strategy_id": strategy.id}
                )
                
                # Execute order
                execute_order.delay(order.id)
                
                # Update strategy stats
                strategy.total_trades += 1
                strategy.save()
                
            except Exception as e:
                logger.error(f"Error in DCA strategy for {pair.symbol}: {e}")


def execute_market_making_strategy(strategy: TradingStrategy):
    """
    Execute market making strategy.
    """
    # Simplified implementation
    # Would place limit orders on both sides of the order book
    pass


def update_position_from_order(order: Order):
    """
    Update position based on filled order.
    """
    if "position_id" not in order.metadata:
        return
    
    try:
        position = Position.objects.get(id=order.metadata["position_id"])
        
        if order.metadata.get("is_close"):
            # Closing position
            if order.filled_amount >= position.amount:
                # Fully closed
                position.exit_price = order.average_price or order.price
                position.close_position(position.exit_price)
            else:
                # Partially closed
                position.amount -= order.filled_amount
                position.save()
        else:
            # Opening/adding to position
            if position.entry_price == 0:
                position.entry_price = order.average_price or order.price
            position.save()
            
    except Position.DoesNotExist:
        logger.error(f"Position {order.metadata['position_id']} not found")


def create_trading_alert(user, alert_type, title, message, order=None, position=None):
    """
    Create a trading alert for the user.
    """
    TradingAlert.objects.create(
        user=user,
        alert_type=alert_type,
        title=title,
        message=message,
        order=order,
        position=position
    )


@shared_task
def update_position_pnl():
    """
    Update P&L for all open positions.
    """
    positions = Position.objects.filter(status="OPEN")
    
    for position in positions:
        try:
            # Get current price (simplified - would fetch from exchange)
            current_price = position.trading_pair.last_price
            
            if current_price:
                position.update_unrealized_pnl(current_price)
                
                # Check stop loss
                if position.stop_loss_price:
                    if (position.side == "LONG" and current_price <= position.stop_loss_price) or \
                       (position.side == "SHORT" and current_price >= position.stop_loss_price):
                        # Trigger stop loss
                        close_position_stop_loss.delay(position.id)
                
                # Check take profit
                if position.take_profit_price:
                    if (position.side == "LONG" and current_price >= position.take_profit_price) or \
                       (position.side == "SHORT" and current_price <= position.take_profit_price):
                        # Trigger take profit
                        close_position_take_profit.delay(position.id)
                        
        except Exception as e:
            logger.error(f"Error updating position {position.id} P&L: {e}")


@shared_task
def close_position_stop_loss(position_id: str):
    """
    Close position due to stop loss.
    """
    try:
        position = Position.objects.get(id=position_id)
        
        if position.status != "OPEN":
            return
        
        # Create market order to close
        order_side = "SELL" if position.side == "LONG" else "BUY"
        order = Order.objects.create(
            user=position.user,
            exchange=position.exchange,
            trading_pair=position.trading_pair,
            order_type="MARKET",
            side=order_side,
            amount=position.amount,
            status="PENDING",
            metadata={
                "position_id": str(position.id),
                "is_close": True,
                "reason": "stop_loss"
            }
        )
        
        position.exit_orders.add(order)
        execute_order.delay(order.id)
        
        # Create alert
        create_trading_alert(
            position.user,
            "STOP_LOSS_HIT",
            "Stop Loss Triggered",
            f"Position {position.trading_pair.symbol} closed due to stop loss",
            position=position
        )
        
    except Exception as e:
        logger.error(f"Error closing position {position_id} on stop loss: {e}")


@shared_task
def close_position_take_profit(position_id: str):
    """
    Close position due to take profit.
    """
    # Similar to stop loss but for take profit
    pass


@shared_task
def run_strategy_backtest(
    strategy_id: int,
    start_date: str,
    end_date: str,
    initial_balance: float,
    trading_pairs: List[str],
    exchanges: List[str],
    parameters: dict
):
    """
    Run backtest for a trading strategy.
    """
    # This would implement backtesting logic
    # For now, return placeholder
    return {
        "status": "completed",
        "results": {
            "total_return": 0,
            "win_rate": 0,
            "max_drawdown": 0,
        }
    }