
import logging
from datetime import datetime, timedelta
from decimal import Decimal
from typing import List, Optional
from uuid import UUID

from django.db import models, transaction
from django.shortcuts import get_object_or_404
from ninja import Router
from ninja.pagination import paginate
from ninja.security import django_auth

from core.models import APICredential, Exchange, TradingPair
from exchanges.services.nobitex import NobitexService
from exchanges.services.ramzinex import RamzinexService
from exchanges.services.wallex import WallexService
from trading.models import Order, Position, Trade, TradingAlert, TradingStrategy
from trading.schemas import (
    BacktestRequestSchema,
    BacktestResultSchema,
    CancelOrderSchema,
    ClosePositionSchema,
    CreateOrderSchema,
    CreateStrategySchema,
    OpenPositionSchema,
    OrderSchema,
    PortfolioSummarySchema,
    PositionSchema,
    TradeSchema,
    TradingAlertSchema,
    TradingHistoryFilterSchema,
    TradingStatsSchema,
    TradingStrategySchema,
    UpdateStrategySchema,
)
from trading.tasks import execute_order, monitor_order_status

logger = logging.getLogger(__name__)

router = Router()

# Service mapping
EXCHANGE_SERVICES = {
    "nobitex": NobitexService,
    "wallex": WallexService,
    "ramzinex": RamzinexService,
}


@router.post("/orders", auth=django_auth, response=OrderSchema)
def create_order(request, data: CreateOrderSchema):
    """
    Create a new trading order.
    """
    # Validate exchange and trading pair
    exchange = get_object_or_404(Exchange, code=data.exchange)
    trading_pair = get_object_or_404(TradingPair, symbol=data.trading_pair)
    
    # Check user has API credentials
    try:
        credential = request.user.api_credentials.get(
            exchange=exchange,
            is_active=True
        )
    except APICredential.DoesNotExist:
        return {"error": "API credentials not found for this exchange"}
    
    # Create order
    order = Order.objects.create(
        user=request.user,
        exchange=exchange,
        trading_pair=trading_pair,
        order_type=data.order_type,
        side=data.side,
        amount=data.amount,
        price=data.price,
        stop_price=data.stop_price,
        expires_at=data.expires_at,
        status="PENDING",
        exchange_order_id="",  # Will be set by exchange
    )
    
    # Execute order asynchronously
    execute_order.delay(order.id)
    
    return order


@router.get("/orders", auth=django_auth, response=List[OrderSchema])
@paginate
def list_orders(request, filters: TradingHistoryFilterSchema = None):
    """
    List user's orders with optional filters.
    """
    queryset = Order.objects.filter(user=request.user).select_related(
        "exchange", "trading_pair"
    )
    
    if filters:
        if filters.exchange:
            queryset = queryset.filter(exchange__code=filters.exchange)
        if filters.trading_pair:
            queryset = queryset.filter(trading_pair__symbol=filters.trading_pair)
        if filters.order_type:
            queryset = queryset.filter(order_type=filters.order_type)
        if filters.side:
            queryset = queryset.filter(side=filters.side)
        if filters.status:
            queryset = queryset.filter(status=filters.status)
        if filters.start_date:
            queryset = queryset.filter(created_at__gte=filters.start_date)
        if filters.end_date:
            queryset = queryset.filter(created_at__lte=filters.end_date)
    
    return queryset.order_by("-created_at")


@router.get("/orders/{order_id}", auth=django_auth, response=OrderSchema)
def get_order(request, order_id: UUID):
    """
    Get details of a specific order.
    """
    order = get_object_or_404(
        Order.objects.select_related("exchange", "trading_pair"),
        id=order_id,
        user=request.user
    )
    return order


@router.post("/orders/cancel", auth=django_auth)
def cancel_order(request, data: CancelOrderSchema):
    """
    Cancel an open order.
    """
    order = get_object_or_404(
        Order,
        id=data.order_id,
        user=request.user
    )
    
    if not order.is_open:
        return {"error": "Order is not open"}
    
    # Get API credentials
    try:
        credential = request.user.api_credentials.get(
            exchange=order.exchange,
            is_active=True
        )
    except APICredential.DoesNotExist:
        return {"error": "API credentials not found"}
    
    # Cancel order on exchange
    service_class = EXCHANGE_SERVICES.get(order.exchange.code)
    if not service_class:
        return {"error": "Exchange service not implemented"}
    
    # Execute cancellation asynchronously
    from trading.tasks import cancel_order_on_exchange
    cancel_order_on_exchange.delay(order.id, data.reason)
    
    return {"success": True, "message": "Order cancellation initiated"}


@router.get("/orders/{order_id}/trades", auth=django_auth, response=List[TradeSchema])
def get_order_trades(request, order_id: UUID):
    """
    Get trades (fills) for a specific order.
    """
    order = get_object_or_404(Order, id=order_id, user=request.user)
    trades = order.trades.all().order_by("-executed_at")
    return trades


@router.get("/positions", auth=django_auth, response=List[PositionSchema])
def list_positions(request, status: str = "OPEN"):
    """
    List user's positions.
    """
    queryset = Position.objects.filter(
        user=request.user,
        status=status.upper()
    ).select_related("exchange", "trading_pair", "strategy")
    
    return queryset.order_by("-opened_at")


@router.post("/positions", auth=django_auth, response=PositionSchema)
def open_position(request, data: OpenPositionSchema):
    """
    Open a new position.
    """
    # Validate exchange and trading pair
    exchange = get_object_or_404(Exchange, code=data.exchange)
    trading_pair = get_object_or_404(TradingPair, symbol=data.trading_pair)
    
    # Get strategy if specified
    strategy = None
    if data.strategy_id:
        strategy = get_object_or_404(
            TradingStrategy,
            id=data.strategy_id,
            user=request.user
        )
    
    # Create position
    position = Position.objects.create(
        user=request.user,
        exchange=exchange,
        trading_pair=trading_pair,
        strategy=strategy,
        side=data.side,
        amount=data.amount,
        entry_price=data.entry_price or Decimal("0"),  # Will be updated
        stop_loss_price=data.stop_loss_price,
        take_profit_price=data.take_profit_price,
    )
    
    # Create entry order
    order_side = "BUY" if data.side == "LONG" else "SELL"
    order = Order.objects.create(
        user=request.user,
        exchange=exchange,
        trading_pair=trading_pair,
        order_type="MARKET" if not data.entry_price else "LIMIT",
        side=order_side,
        amount=data.amount,
        price=data.entry_price,
        status="PENDING",
        exchange_order_id="",
        metadata={"position_id": str(position.id)}
    )
    
    position.entry_orders.add(order)
    
    # Execute order
    execute_order.delay(order.id)
    
    return position


@router.post("/positions/close", auth=django_auth)
def close_position(request, data: ClosePositionSchema):
    """
    Close a position.
    """
    position = get_object_or_404(
        Position,
        id=data.position_id,
        user=request.user,
        status="OPEN"
    )
    
    # Determine close amount
    close_amount = data.amount or position.amount
    if close_amount > position.amount:
        return {"error": "Close amount exceeds position size"}
    
    # Create exit order
    order_side = "SELL" if position.side == "LONG" else "BUY"
    order = Order.objects.create(
        user=request.user,
        exchange=position.exchange,
        trading_pair=position.trading_pair,
        order_type="MARKET" if not data.price else "LIMIT",
        side=order_side,
        amount=close_amount,
        price=data.price,
        status="PENDING",
        exchange_order_id="",
        metadata={"position_id": str(position.id), "is_close": True}
    )
    
    position.exit_orders.add(order)
    
    # Execute order
    execute_order.delay(order.id)
    
    return {"success": True, "message": "Position close initiated"}


@router.get("/strategies", auth=django_auth, response=List[TradingStrategySchema])
def list_strategies(request):
    """
    List user's trading strategies.
    """
    strategies = TradingStrategy.objects.filter(
        user=request.user
    ).prefetch_related("enabled_exchanges", "enabled_pairs")
    
    return strategies.order_by("name")


@router.post("/strategies", auth=django_auth, response=TradingStrategySchema)
def create_strategy(request, data: CreateStrategySchema):
    """
    Create a new trading strategy.
    """
    with transaction.atomic():
        strategy = TradingStrategy.objects.create(
            user=request.user,
            name=data.name,
            strategy_type=data.strategy_type,
            description=data.description,
            config=data.config,
            max_position_size=data.max_position_size,
            stop_loss_percentage=data.stop_loss_percentage,
            take_profit_percentage=data.take_profit_percentage,
        )
        
        # Set enabled exchanges
        if data.enabled_exchanges:
            exchanges = Exchange.objects.filter(code__in=data.enabled_exchanges)
            strategy.enabled_exchanges.set(exchanges)
        
        # Set enabled pairs
        if data.enabled_pairs:
            pairs = TradingPair.objects.filter(symbol__in=data.enabled_pairs)
            strategy.enabled_pairs.set(pairs)
    
    return strategy


@router.patch("/strategies/{strategy_id}", auth=django_auth, response=TradingStrategySchema)
def update_strategy(request, strategy_id: int, data: UpdateStrategySchema):
    """
    Update a trading strategy.
    """
    strategy = get_object_or_404(
        TradingStrategy,
        id=strategy_id,
        user=request.user
    )
    
    # Update fields
    for field, value in data.dict(exclude_unset=True).items():
        if field == "enabled_exchanges" and value is not None:
            exchanges = Exchange.objects.filter(code__in=value)
            strategy.enabled_exchanges.set(exchanges)
        elif field == "enabled_pairs" and value is not None:
            pairs = TradingPair.objects.filter(symbol__in=value)
            strategy.enabled_pairs.set(pairs)
        elif value is not None:
            setattr(strategy, field, value)
    
    strategy.save()
    
    return strategy


@router.delete("/strategies/{strategy_id}", auth=django_auth)
def delete_strategy(request, strategy_id: int):
    """
    Delete a trading strategy.
    """
    strategy = get_object_or_404(
        TradingStrategy,
        id=strategy_id,
        user=request.user
    )
    
    # Check if strategy has open positions
    if strategy.positions.filter(status="OPEN").exists():
        return {"error": "Cannot delete strategy with open positions"}
    
    strategy.delete()
    
    return {"success": True}


@router.post("/strategies/{strategy_id}/activate", auth=django_auth)
def activate_strategy(request, strategy_id: int):
    """
    Activate a trading strategy.
    """
    strategy = get_object_or_404(
        TradingStrategy,
        id=strategy_id,
        user=request.user
    )
    
    strategy.is_active = True
    strategy.save()
    
    # Schedule strategy execution
    from trading.tasks import run_trading_strategy
    run_trading_strategy.delay(strategy_id)
    
    return {"success": True, "message": "Strategy activated"}


@router.post("/strategies/{strategy_id}/deactivate", auth=django_auth)
def deactivate_strategy(request, strategy_id: int):
    """
    Deactivate a trading strategy.
    """
    strategy = get_object_or_404(
        TradingStrategy,
        id=strategy_id,
        user=request.user
    )
    
    strategy.is_active = False
    strategy.save()
    
    return {"success": True, "message": "Strategy deactivated"}


@router.get("/alerts", auth=django_auth, response=List[TradingAlertSchema])
@paginate
def list_alerts(request, unread_only: bool = False):
    """
    List user's trading alerts.
    """
    queryset = TradingAlert.objects.filter(user=request.user)
    
    if unread_only:
        queryset = queryset.filter(is_read=False)
    
    return queryset.order_by("-created_at")


@router.post("/alerts/{alert_id}/read", auth=django_auth)
def mark_alert_read(request, alert_id: int):
    """
    Mark an alert as read.
    """
    alert = get_object_or_404(
        TradingAlert,
        id=alert_id,
        user=request.user
    )
    alert.is_read = True
    alert.save()
    
    return {"success": True}


@router.get("/stats", auth=django_auth, response=TradingStatsSchema)
def get_trading_stats(request, period: str = "30d"):
    """
    Get user's trading statistics.
    """
    # Parse period
    if period == "24h":
        start_date = datetime.now() - timedelta(hours=24)
    elif period == "7d":
        start_date = datetime.now() - timedelta(days=7)
    elif period == "30d":
        start_date = datetime.now() - timedelta(days=30)
    else:
        start_date = None
    
    # Get orders
    orders = Order.objects.filter(user=request.user)
    if start_date:
        orders = orders.filter(created_at__gte=start_date)
    
    # Calculate stats
    total_orders = orders.count()
    open_orders = orders.filter(status__in=["PENDING", "OPEN", "PARTIAL"]).count()
    filled_orders = orders.filter(status="FILLED").count()
    cancelled_orders = orders.filter(status="CANCELLED").count()
    
    # Get trades
    trades = Trade.objects.filter(order__user=request.user)
    if start_date:
        trades = trades.filter(executed_at__gte=start_date)
    
    total_trades = trades.count()
    total_volume = trades.aggregate(
        volume=models.Sum(models.F("amount") * models.F("price"))
    )["volume"] or Decimal("0")
    total_fees = trades.aggregate(fees=models.Sum("fee"))["fees"] or Decimal("0")
    
    # Get positions
    positions = Position.objects.filter(user=request.user)
    if start_date:
        positions = positions.filter(opened_at__gte=start_date)
    
    open_positions = positions.filter(status="OPEN").count()
    total_pnl = positions.aggregate(
        pnl=models.Sum("realized_pnl")
    )["pnl"] or Decimal("0")
    
    # Calculate win rate
    winning_positions = positions.filter(
        status="CLOSED",
        realized_pnl__gt=0
    ).count()
    closed_positions = positions.filter(status="CLOSED").count()
    win_rate = (
        (winning_positions / closed_positions * 100)
        if closed_positions > 0 else Decimal("0")
    )
    
    # Average trade size
    average_trade_size = (
        total_volume / total_trades if total_trades > 0 else Decimal("0")
    )
    
    # Most traded pair
    most_traded = (
        orders.values("trading_pair__symbol")
        .annotate(count=models.Count("id"))
        .order_by("-count")
        .first()
    )
    
    # Most used exchange
    most_used = (
        orders.values("exchange__name")
        .annotate(count=models.Count("id"))
        .order_by("-count")
        .first()
    )
    
    return {
        "total_orders": total_orders,
        "open_orders": open_orders,
        "filled_orders": filled_orders,
        "cancelled_orders": cancelled_orders,
        "total_trades": total_trades,
        "total_volume": total_volume,
        "total_fees": total_fees,
        "open_positions": open_positions,
        "total_pnl": total_pnl,
        "win_rate": win_rate,
        "average_trade_size": average_trade_size,
        "most_traded_pair": most_traded["trading_pair__symbol"] if most_traded else None,
        "most_used_exchange": most_used["exchange__name"] if most_used else None,
        "time_period": period,
    }


@router.get("/portfolio", auth=django_auth, response=PortfolioSummarySchema)
def get_portfolio_summary(request):
    """
    Get user's portfolio summary.
    """
    from exchanges.models import ExchangeBalance
    
    # Get balances
    balances = ExchangeBalance.objects.filter(
        user=request.user,
        total__gt=0
    ).select_related("exchange", "currency")
    
    # Calculate total value (simplified - would need price data)
    total_value = Decimal("0")
    balance_dict = {}
    
    for balance in balances:
        exchange_name = balance.exchange.name
        if exchange_name not in balance_dict:
            balance_dict[exchange_name] = {}
        
        balance_dict[exchange_name][balance.currency.symbol] = {
            "available": balance.available,
            "locked": balance.locked,
            "total": balance.total,
        }
        
        # Add to total value (would multiply by current price)
        total_value += balance.total
    
    # Get open positions
    positions = Position.objects.filter(
        user=request.user,
        status="OPEN"
    ).select_related("exchange", "trading_pair")
    
    position_list = []
    total_unrealized_pnl = Decimal("0")
    
    for position in positions:
        position_data = {
            "id": str(position.id),
            "exchange": position.exchange.name,
            "trading_pair": position.trading_pair.symbol,
            "side": position.side,
            "amount": str(position.amount),
            "entry_price": str(position.entry_price),
            "unrealized_pnl": str(position.unrealized_pnl),
        }
        position_list.append(position_data)
        total_unrealized_pnl += position.unrealized_pnl
    
    # Get open orders value
    open_orders = Order.objects.filter(
        user=request.user,
        status__in=["PENDING", "OPEN", "PARTIAL"]
    )
    
    open_orders_value = Decimal("0")
    for order in open_orders:
        if order.price:
            open_orders_value += order.remaining_amount * order.price
    
    # Calculate P&L
    total_cost = total_value - total_unrealized_pnl  # Simplified
    total_pnl = total_unrealized_pnl
    pnl_percentage = (
        (total_pnl / total_cost * 100) if total_cost > 0 else Decimal("0")
    )
    
    return {
        "total_value": total_value,
        "total_cost": total_cost,
        "total_pnl": total_pnl,
        "pnl_percentage": pnl_percentage,
        "positions": position_list,
        "balances": balance_dict,
        "open_orders_value": open_orders_value,
        "last_updated": datetime.now(),
    }


@router.post("/backtest", auth=django_auth, response=BacktestResultSchema)
def run_backtest(request, data: BacktestRequestSchema):
    """
    Run a backtest for a trading strategy.
    """
    strategy = get_object_or_404(
        TradingStrategy,
        id=data.strategy_id,
        user=request.user
    )
    
    # Trigger backtest task
    from trading.tasks import run_strategy_backtest
    task = run_strategy_backtest.delay(
        strategy.id,
        data.start_date.isoformat(),
        data.end_date.isoformat(),
        float(data.initial_balance),
        data.trading_pairs,
        data.exchanges,
        data.parameters or {}
    )
    
    # For now, return a placeholder
    # In production, this would return a task ID and results would be fetched separately
    return {
        "strategy_id": strategy.id,
        "start_date": data.start_date,
        "end_date": data.end_date,
        "initial_balance": data.initial_balance,
        "final_balance": data.initial_balance,
        "total_return": Decimal("0"),
        "total_return_percentage": Decimal("0"),
        "total_trades": 0,
        "winning_trades": 0,
        "losing_trades": 0,
        "win_rate": Decimal("0"),
        "max_drawdown": Decimal("0"),
        "trades": [],
        "equity_curve": [],
        "task_id": task.id,
        "status": "Running backtest..."
    }