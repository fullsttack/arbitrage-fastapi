
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional
from uuid import UUID

from ninja import Schema
from pydantic import Field, validator


class OrderSchema(Schema):
    """Schema for order information."""
    
    id: UUID
    exchange: str
    trading_pair: str
    exchange_order_id: str
    order_type: str
    side: str
    status: str
    amount: Decimal
    price: Optional[Decimal] = None
    stop_price: Optional[Decimal] = None
    filled_amount: Decimal
    average_price: Optional[Decimal] = None
    fee: Decimal
    fee_currency: str
    placed_at: datetime
    updated_at: datetime
    filled_at: Optional[datetime] = None
    cancelled_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    is_arbitrage: bool
    remaining_amount: Decimal
    fill_percentage: Decimal


class CreateOrderSchema(Schema):
    """Schema for creating a new order."""
    
    exchange: str
    trading_pair: str
    order_type: str = Field(..., pattern="^(MARKET|LIMIT|STOP|STOP_LIMIT)$")
    side: str = Field(..., pattern="^(BUY|SELL)$")
    amount: Decimal = Field(..., gt=0)
    price: Optional[Decimal] = Field(None, gt=0)
    stop_price: Optional[Decimal] = Field(None, gt=0)
    expires_at: Optional[datetime] = None
    
    @validator("price")
    def validate_price(cls, v, values):
        if values.get("order_type") in ["LIMIT", "STOP_LIMIT"] and v is None:
            raise ValueError("Price is required for limit orders")
        return v
    
    @validator("stop_price")
    def validate_stop_price(cls, v, values):
        if values.get("order_type") in ["STOP", "STOP_LIMIT"] and v is None:
            raise ValueError("Stop price is required for stop orders")
        return v


class CancelOrderSchema(Schema):
    """Schema for cancelling an order."""
    
    order_id: UUID
    reason: Optional[str] = None


class TradeSchema(Schema):
    """Schema for trade (fill) information."""
    
    id: UUID
    order_id: UUID
    exchange_trade_id: str
    price: Decimal
    amount: Decimal
    fee: Decimal
    fee_currency: str
    executed_at: datetime
    is_maker: Optional[bool] = None
    total_value: Decimal


class TradingStrategySchema(Schema):
    """Schema for trading strategy."""
    
    id: int
    name: str
    strategy_type: str
    description: str
    is_active: bool
    config: Dict
    enabled_exchanges: List[str]
    enabled_pairs: List[str]
    max_position_size: Optional[Decimal] = None
    stop_loss_percentage: Optional[Decimal] = None
    take_profit_percentage: Optional[Decimal] = None
    total_trades: int
    winning_trades: int
    total_profit: Decimal
    win_rate: Decimal
    average_profit_per_trade: Decimal
    last_run: Optional[datetime] = None
    next_run: Optional[datetime] = None


class CreateStrategySchema(Schema):
    """Schema for creating a trading strategy."""
    
    name: str = Field(..., min_length=1, max_length=100)
    strategy_type: str
    description: Optional[str] = ""
    config: Dict = {}
    enabled_exchanges: Optional[List[str]] = []
    enabled_pairs: Optional[List[str]] = []
    max_position_size: Optional[Decimal] = Field(None, gt=0)
    stop_loss_percentage: Optional[Decimal] = Field(None, ge=0, le=100)
    take_profit_percentage: Optional[Decimal] = Field(None, ge=0, le=100)


class UpdateStrategySchema(Schema):
    """Schema for updating a trading strategy."""
    
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None
    is_active: Optional[bool] = None
    config: Optional[Dict] = None
    enabled_exchanges: Optional[List[str]] = None
    enabled_pairs: Optional[List[str]] = None
    max_position_size: Optional[Decimal] = Field(None, gt=0)
    stop_loss_percentage: Optional[Decimal] = Field(None, ge=0, le=100)
    take_profit_percentage: Optional[Decimal] = Field(None, ge=0, le=100)


class PositionSchema(Schema):
    """Schema for position information."""
    
    id: UUID
    exchange: str
    trading_pair: str
    strategy: Optional[str] = None
    side: str
    status: str
    amount: Decimal
    entry_price: Decimal
    exit_price: Optional[Decimal] = None
    stop_loss_price: Optional[Decimal] = None
    take_profit_price: Optional[Decimal] = None
    unrealized_pnl: Decimal
    realized_pnl: Decimal
    opened_at: datetime
    closed_at: Optional[datetime] = None


class OpenPositionSchema(Schema):
    """Schema for opening a position."""
    
    exchange: str
    trading_pair: str
    side: str = Field(..., pattern="^(LONG|SHORT)$")
    amount: Decimal = Field(..., gt=0)
    entry_price: Optional[Decimal] = Field(None, gt=0)
    stop_loss_price: Optional[Decimal] = Field(None, gt=0)
    take_profit_price: Optional[Decimal] = Field(None, gt=0)
    strategy_id: Optional[int] = None


class ClosePositionSchema(Schema):
    """Schema for closing a position."""
    
    position_id: UUID
    amount: Optional[Decimal] = Field(None, gt=0)  # Partial close
    price: Optional[Decimal] = Field(None, gt=0)  # Market or limit


class TradingAlertSchema(Schema):
    """Schema for trading alerts."""
    
    id: int
    alert_type: str
    title: str
    message: str
    is_read: bool
    created_at: datetime
    order_id: Optional[UUID] = None
    position_id: Optional[UUID] = None
    metadata: Dict = {}


class OrderBookUpdateSchema(Schema):
    """Schema for order book updates."""
    
    exchange: str
    trading_pair: str
    bids: List[List[Decimal]]  # [[price, amount], ...]
    asks: List[List[Decimal]]  # [[price, amount], ...]
    timestamp: datetime


class TradingStatsSchema(Schema):
    """Schema for trading statistics."""
    
    total_orders: int
    open_orders: int
    filled_orders: int
    cancelled_orders: int
    total_trades: int
    total_volume: Decimal
    total_fees: Decimal
    open_positions: int
    total_pnl: Decimal
    win_rate: Decimal
    average_trade_size: Decimal
    most_traded_pair: Optional[str] = None
    most_used_exchange: Optional[str] = None
    time_period: str


class PortfolioSummarySchema(Schema):
    """Schema for portfolio summary."""
    
    total_value: Decimal
    total_cost: Decimal
    total_pnl: Decimal
    pnl_percentage: Decimal
    positions: List[Dict[str, Any]]
    balances: Dict[str, Dict[str, Decimal]]
    open_orders_value: Decimal
    last_updated: datetime


class TradingHistoryFilterSchema(Schema):
    """Schema for filtering trading history."""
    
    exchange: Optional[str] = None
    trading_pair: Optional[str] = None
    order_type: Optional[str] = None
    side: Optional[str] = None
    status: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    page: int = 1
    page_size: int = Field(default=50, le=200)


class BacktestRequestSchema(Schema):
    """Schema for backtest request."""
    
    strategy_id: int
    start_date: datetime
    end_date: datetime
    initial_balance: Decimal = Field(..., gt=0)
    trading_pairs: List[str]
    exchanges: List[str]
    parameters: Optional[Dict] = {}


class BacktestResultSchema(Schema):
    """Schema for backtest results."""
    
    strategy_id: int
    start_date: datetime
    end_date: datetime
    initial_balance: Decimal
    final_balance: Decimal
    total_return: Decimal
    total_return_percentage: Decimal
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: Decimal
    max_drawdown: Decimal
    sharpe_ratio: Optional[Decimal] = None
    trades: List[Dict[str, Any]]
    equity_curve: List[Dict[str, Any]]