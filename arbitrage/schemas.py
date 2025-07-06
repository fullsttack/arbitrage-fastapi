"""
Pydantic schemas for arbitrage data validation.
"""

from datetime import datetime
from decimal import Decimal
from typing import Dict, List, Optional
from uuid import UUID

from ninja import Schema
from pydantic import Field, validator


class ArbitrageOpportunitySchema(Schema):
    """Schema for arbitrage opportunity."""
    
    id: UUID
    trading_pair: str
    buy_exchange: str
    sell_exchange: str
    buy_price: Decimal
    sell_price: Decimal
    available_buy_amount: Decimal
    available_sell_amount: Decimal
    optimal_amount: Decimal
    gross_profit_percentage: Decimal
    net_profit_percentage: Decimal
    estimated_profit: Decimal
    buy_fee: Decimal
    sell_fee: Decimal
    total_fees: Decimal
    status: str
    expires_at: datetime
    created_at: datetime
    market_depth: Optional[Dict] = None


class ArbitrageConfigSchema(Schema):
    """Schema for arbitrage configuration."""
    
    is_active: bool = True
    auto_trade: bool = False
    min_profit_percentage: Decimal = Field(default=0.5, ge=0, le=100)
    min_profit_amount: Decimal = Field(default=10, ge=0)
    max_trade_amount: Dict[str, Decimal] = {}
    daily_trade_limit: Dict[str, Decimal] = {}
    max_exposure_percentage: Decimal = Field(default=10, ge=0, le=100)
    stop_loss_percentage: Decimal = Field(default=2, ge=0, le=100)
    enable_notifications: bool = True
    notification_channels: List[str] = []
    enabled_exchanges: List[str] = []
    enabled_pairs: List[str] = []
    use_market_orders: bool = False
    slippage_tolerance: Decimal = Field(default=0.5, ge=0, le=10)


class ArbitrageConfigUpdateSchema(Schema):
    """Schema for updating arbitrage configuration."""
    
    is_active: Optional[bool] = None
    auto_trade: Optional[bool] = None
    min_profit_percentage: Optional[Decimal] = Field(None, ge=0, le=100)
    min_profit_amount: Optional[Decimal] = Field(None, ge=0)
    max_trade_amount: Optional[Dict[str, Decimal]] = None
    daily_trade_limit: Optional[Dict[str, Decimal]] = None
    max_exposure_percentage: Optional[Decimal] = Field(None, ge=0, le=100)
    stop_loss_percentage: Optional[Decimal] = Field(None, ge=0, le=100)
    enable_notifications: Optional[bool] = None
    notification_channels: Optional[List[str]] = None
    enabled_exchanges: Optional[List[str]] = None
    enabled_pairs: Optional[List[str]] = None
    use_market_orders: Optional[bool] = None
    slippage_tolerance: Optional[Decimal] = Field(None, ge=0, le=10)


class ArbitrageExecutionSchema(Schema):
    """Schema for arbitrage execution details."""
    
    id: UUID
    opportunity_id: UUID
    status: str
    buy_order_id: Optional[str] = None
    buy_order_status: Optional[str] = None
    buy_filled_amount: Decimal
    buy_average_price: Optional[Decimal] = None
    buy_fee_paid: Decimal
    sell_order_id: Optional[str] = None
    sell_order_status: Optional[str] = None
    sell_filled_amount: Decimal
    sell_average_price: Optional[Decimal] = None
    sell_fee_paid: Decimal
    final_profit: Optional[Decimal] = None
    profit_percentage: Optional[Decimal] = None
    created_at: datetime
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None


class ExecuteArbitrageSchema(Schema):
    """Schema for executing an arbitrage opportunity."""
    
    opportunity_id: UUID
    amount: Optional[Decimal] = Field(None, gt=0)
    use_market_orders: Optional[bool] = None
    
    @validator("amount")
    def validate_amount(cls, v, values):
        # Additional validation can be added here
        return v


class ArbitrageAlertSchema(Schema):
    """Schema for arbitrage alerts."""
    
    id: int
    alert_type: str
    title: str
    message: str
    is_read: bool
    created_at: datetime
    opportunity_id: Optional[UUID] = None
    metadata: Dict = {}


class ArbitrageScanRequestSchema(Schema):
    """Schema for manual arbitrage scan request."""
    
    exchanges: Optional[List[str]] = None
    trading_pairs: Optional[List[str]] = None
    min_profit_percentage: Optional[Decimal] = Field(None, ge=0, le=100)


class ArbitrageScanResultSchema(Schema):
    """Schema for arbitrage scan results."""
    
    opportunities_found: int
    scan_duration: float
    opportunities: List[ArbitrageOpportunitySchema]
    errors: List[str] = []


class ArbitrageStatsSchema(Schema):
    """Schema for arbitrage statistics."""
    
    total_opportunities_detected: int
    total_opportunities_executed: int
    total_profit: Decimal
    average_profit_percentage: Decimal
    success_rate: Decimal
    active_opportunities: int
    top_profitable_pairs: List[Dict[str, any]]
    top_profitable_routes: List[Dict[str, any]]
    time_period: str


class ArbitrageHistoryFilterSchema(Schema):
    """Schema for filtering arbitrage history."""
    
    status: Optional[str] = None
    trading_pair: Optional[str] = None
    buy_exchange: Optional[str] = None
    sell_exchange: Optional[str] = None
    min_profit: Optional[Decimal] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    page: int = 1
    page_size: int = Field(default=50, le=200)