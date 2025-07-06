"""
Pydantic schemas for exchange data validation.
"""

from datetime import datetime
from decimal import Decimal
from typing import Dict, List, Optional

from ninja import Schema
from pydantic import Field, validator


class ExchangeSchema(Schema):
    """Schema for exchange information."""
    
    id: int
    name: str
    code: str
    api_url: str
    is_active: bool
    rate_limit: int
    maker_fee: Decimal
    taker_fee: Decimal


class CurrencySchema(Schema):
    """Schema for currency information."""
    
    symbol: str
    name: str
    is_crypto: bool
    decimal_places: int
    is_active: bool


class TradingPairSchema(Schema):
    """Schema for trading pair information."""
    
    id: int
    symbol: str
    base_currency: CurrencySchema
    quote_currency: CurrencySchema
    min_order_size: Decimal
    max_order_size: Decimal
    is_active: bool


class ExchangeTradingPairSchema(Schema):
    """Schema for exchange-specific trading pair information."""
    
    id: int
    exchange: ExchangeSchema
    trading_pair: TradingPairSchema
    exchange_symbol: str
    min_order_size: Decimal
    max_order_size: Decimal
    min_order_value: Decimal
    price_precision: int
    amount_precision: int
    is_active: bool
    last_sync: Optional[datetime] = None


class MarketTickerSchema(Schema):
    """Schema for market ticker data."""
    
    exchange: str
    symbol: str
    last_price: Decimal
    bid_price: Optional[Decimal] = None
    ask_price: Optional[Decimal] = None
    volume_24h: Decimal
    high_24h: Decimal
    low_24h: Decimal
    change_24h: Decimal
    timestamp: datetime


class OrderBookEntrySchema(Schema):
    """Schema for order book entry."""
    
    price: Decimal
    amount: Decimal
    total: Decimal
    
    @validator("total", pre=True, always=True)
    def calculate_total(cls, v, values):
        if v is None and "price" in values and "amount" in values:
            return values["price"] * values["amount"]
        return v


class OrderBookSchema(Schema):
    """Schema for order book data."""
    
    exchange: str
    symbol: str
    bids: List[OrderBookEntrySchema]
    asks: List[OrderBookEntrySchema]
    timestamp: datetime


class BalanceSchema(Schema):
    """Schema for balance information."""
    
    currency: str
    available: Decimal
    locked: Decimal
    total: Decimal
    
    @validator("total", pre=True, always=True)
    def calculate_total(cls, v, values):
        if v is None and "available" in values and "locked" in values:
            return values["available"] + values["locked"]
        return v


class ExchangeBalanceSchema(Schema):
    """Schema for exchange balance information."""
    
    exchange: str
    balances: Dict[str, BalanceSchema]
    last_updated: datetime


class OrderRequestSchema(Schema):
    """Schema for order placement request."""
    
    exchange: str
    symbol: str
    side: str = Field(..., regex="^(buy|sell|BUY|SELL)$") # type: ignore 
    order_type: str = Field(..., regex="^(market|limit|MARKET|LIMIT)$") # type: ignore
    amount: Decimal = Field(..., gt=0)
    price: Optional[Decimal] = Field(None, gt=0)
    
    @validator("side")
    def normalize_side(cls, v):
        return v.upper()
    
    @validator("order_type")
    def normalize_order_type(cls, v):
        return v.upper()
    
    @validator("price")
    def validate_price(cls, v, values):
        if values.get("order_type") == "LIMIT" and v is None:
            raise ValueError("Price is required for limit orders")
        return v


class OrderResponseSchema(Schema):
    """Schema for order placement response."""
    
    order_id: str
    exchange: str
    symbol: str
    side: str
    type: str
    price: Optional[Decimal] = None
    amount: Decimal
    status: str
    created_at: datetime


class OrderStatusSchema(Schema):
    """Schema for order status information."""
    
    order_id: str
    exchange: str
    symbol: str
    status: str
    filled_amount: Decimal
    remaining_amount: Decimal
    price: Optional[Decimal] = None
    created_at: datetime
    updated_at: Optional[datetime] = None


class ExchangeStatusSchema(Schema):
    """Schema for exchange status."""
    
    exchange: str
    is_online: bool
    last_check: datetime
    response_time: Optional[float] = None
    error_count: int
    last_error: Optional[str] = None
    last_error_time: Optional[datetime] = None


class SyncResultSchema(Schema):
    """Schema for sync operation result."""
    
    exchange: str
    success: bool
    markets_synced: int
    errors: List[str] = []
    timestamp: datetime


class MarketSummarySchema(Schema):
    """Schema for market summary across exchanges."""
    
    symbol: str
    exchanges: List[str]
    lowest_ask: Optional[Dict[str, Decimal]] = None  # {exchange: price}
    highest_bid: Optional[Dict[str, Decimal]] = None  # {exchange: price}
    spread_percentage: Optional[Decimal] = None
    volume_24h: Dict[str, Decimal]  # {exchange: volume}
    last_update: datetime