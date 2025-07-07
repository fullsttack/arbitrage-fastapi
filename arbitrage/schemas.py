"""
Enhanced Pydantic schemas for multi-exchange arbitrage data validation.
"""

from datetime import datetime
from decimal import Decimal
from typing import Dict, List, Optional
from uuid import UUID

from ninja import Schema
from pydantic import Field, validator


# Existing schemas (enhanced)

class ArbitrageOpportunitySchema(Schema):
    """Schema for simple arbitrage opportunity."""
    
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
    executed_at: Optional[datetime] = None
    executed_amount: Optional[Decimal] = None
    actual_profit: Optional[Decimal] = None
    detection_latency: float
    market_depth: Optional[Dict] = None


# New multi-exchange schemas

class ExchangeActionSchema(Schema):
    """Schema for individual exchange action within a strategy."""
    
    exchange: str
    amount: Decimal = Field(..., gt=0)
    price: Decimal = Field(..., gt=0)
    profit_percentage: Optional[Decimal] = None
    liquidity: Optional[Decimal] = None


class MultiExchangeStrategySchema(Schema):
    """Schema for multi-exchange arbitrage strategy."""
    
    id: UUID
    trading_pair: str
    strategy_type: str
    status: str
    buy_actions: List[ExchangeActionSchema]
    sell_actions: List[ExchangeActionSchema]
    total_buy_amount: Decimal
    total_sell_amount: Decimal
    total_buy_cost: Decimal
    total_sell_revenue: Decimal
    estimated_profit: Decimal
    profit_percentage: Decimal
    total_fees: Decimal
    complexity_score: int
    risk_score: Decimal
    max_execution_time: int
    expires_at: datetime
    created_at: datetime
    execution_started_at: Optional[datetime] = None
    execution_completed_at: Optional[datetime] = None
    actual_profit: Optional[Decimal] = None
    actual_profit_percentage: Optional[Decimal] = None
    market_snapshot: Optional[Dict] = None
    executions: Optional[List] = []  # Will be populated with MultiExchangeExecutionSchema


class MultiExchangeExecutionSchema(Schema):
    """Schema for individual exchange execution within a multi-exchange strategy."""
    
    id: UUID
    strategy_id: UUID
    exchange: str
    action_type: str  # BUY or SELL
    target_amount: Decimal
    target_price: Decimal
    exchange_order_id: str
    order_type: str
    filled_amount: Decimal
    average_price: Optional[Decimal] = None
    total_fee: Decimal
    status: str
    error_message: str
    retry_count: int
    order_placed_at: Optional[datetime] = None
    first_fill_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    execution_latency: Optional[float] = None
    fill_latency: Optional[float] = None
    price_slippage: Optional[Decimal] = None
    remaining_amount: Decimal
    fill_percentage: Decimal
    created_at: datetime


class ArbitrageConfigSchema(Schema):
    """Enhanced schema for arbitrage configuration."""
    
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
    
    # Multi-exchange specific fields
    enable_multi_exchange: bool = True
    max_exchanges_per_strategy: int = Field(default=3, ge=2, le=10)
    min_profit_per_exchange: Decimal = Field(default=0.3, ge=0, le=100)
    allocation_strategy: str = Field(default="risk_adjusted")
    max_allocation_per_exchange: Decimal = Field(default=50.0, ge=10, le=100)
    require_simultaneous_execution: bool = True
    max_execution_time: int = Field(default=30, ge=10, le=300)
    enable_triangular_arbitrage: bool = False
    min_liquidity_ratio: Decimal = Field(default=10.0, ge=1, le=100)
    max_slippage_tolerance: Decimal = Field(default=0.5, ge=0, le=5)
    notify_on_high_profit: Decimal = Field(default=5.0, ge=0, le=100)
    exchange_reliability_weights: Dict[str, float] = {}
    order_timeout: int = Field(default=60, ge=10, le=300)
    
    @validator("allocation_strategy")
    def validate_allocation_strategy(cls, v):
        allowed = ["equal", "liquidity_weighted", "profit_weighted", "risk_adjusted"]
        if v not in allowed:
            raise ValueError(f"Allocation strategy must be one of: {allowed}")
        return v


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
    
    # Multi-exchange specific fields
    enable_multi_exchange: Optional[bool] = None
    max_exchanges_per_strategy: Optional[int] = Field(None, ge=2, le=10)
    min_profit_per_exchange: Optional[Decimal] = Field(None, ge=0, le=100)
    allocation_strategy: Optional[str] = None
    max_allocation_per_exchange: Optional[Decimal] = Field(None, ge=10, le=100)
    require_simultaneous_execution: Optional[bool] = None
    max_execution_time: Optional[int] = Field(None, ge=10, le=300)
    enable_triangular_arbitrage: Optional[bool] = None
    min_liquidity_ratio: Optional[Decimal] = Field(None, ge=1, le=100)
    max_slippage_tolerance: Optional[Decimal] = Field(None, ge=0, le=5)
    notify_on_high_profit: Optional[Decimal] = Field(None, ge=0, le=100)
    exchange_reliability_weights: Optional[Dict[str, float]] = None
    order_timeout: Optional[int] = Field(None, ge=10, le=300)
    
    @validator("allocation_strategy")
    def validate_allocation_strategy(cls, v):
        if v is not None:
            allowed = ["equal", "liquidity_weighted", "profit_weighted", "risk_adjusted"]
            if v not in allowed:
                raise ValueError(f"Allocation strategy must be one of: {allowed}")
        return v


class ArbitrageExecutionSchema(Schema):
    """Schema for simple arbitrage execution details."""
    
    id: UUID
    opportunity_id: UUID
    multi_strategy_id: Optional[UUID] = None
    status: str
    buy_order_id: str
    buy_order_status: str
    buy_filled_amount: Decimal
    buy_average_price: Optional[Decimal] = None
    buy_fee_paid: Decimal
    sell_order_id: str
    sell_order_status: str
    sell_filled_amount: Decimal
    sell_average_price: Optional[Decimal] = None
    sell_fee_paid: Decimal
    final_profit: Optional[Decimal] = None
    profit_percentage: Optional[Decimal] = None
    created_at: datetime
    buy_order_placed_at: Optional[datetime] = None
    buy_order_filled_at: Optional[datetime] = None
    sell_order_placed_at: Optional[datetime] = None
    sell_order_filled_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: str
    retry_count: int


class ExecuteArbitrageSchema(Schema):
    """Schema for executing a simple arbitrage opportunity."""
    
    amount: Optional[Decimal] = Field(None, gt=0)
    use_market_orders: Optional[bool] = None
    
    @validator("amount")
    def validate_amount(cls, v, values):
        # Additional validation can be added here
        return v


class ExecuteMultiStrategySchema(Schema):
    """Schema for executing a multi-exchange strategy."""
    
    force_execution: bool = False
    custom_amounts: Optional[Dict[str, Decimal]] = None  # Override amounts per exchange
    custom_timeout: Optional[int] = Field(None, ge=10, le=300)
    
    @validator("custom_amounts")
    def validate_custom_amounts(cls, v):
        if v:
            for exchange, amount in v.items():
                if amount <= 0:
                    raise ValueError(f"Amount for {exchange} must be positive")
        return v


class ArbitrageAlertSchema(Schema):
    """Enhanced schema for arbitrage alerts."""
    
    id: int
    alert_type: str
    title: str
    message: str
    is_read: bool
    created_at: datetime
    opportunity_id: Optional[UUID] = None
    multi_strategy_id: Optional[UUID] = None
    metadata: Dict = {}
    sent_via: List[str] = []


class ArbitrageScanRequestSchema(Schema):
    """Enhanced schema for manual arbitrage scan request."""
    
    exchanges: Optional[List[str]] = None
    trading_pairs: Optional[List[str]] = None
    min_profit_percentage: Optional[Decimal] = Field(None, ge=0, le=100)
    enable_multi_exchange: bool = True
    max_complexity: Optional[int] = Field(None, ge=2, le=10)
    strategy_types: Optional[List[str]] = None  # Filter by strategy type


class ArbitrageScanResultSchema(Schema):
    """Enhanced schema for arbitrage scan results."""
    
    simple_opportunities_found: int
    multi_strategies_found: int
    total_found: int
    scan_duration: float
    simple_opportunities: List[ArbitrageOpportunitySchema]
    multi_strategies: List[MultiExchangeStrategySchema]
    errors: List[str] = []


class ArbitrageStatsSchema(Schema):
    """Enhanced schema for arbitrage statistics."""
    
    # Simple arbitrage stats
    total_simple_opportunities_detected: int
    total_simple_opportunities_executed: int
    simple_profit: Decimal
    simple_average_profit_percentage: Decimal
    simple_success_rate: Decimal
    active_simple_opportunities: int
    
    # Multi-exchange stats
    total_multi_strategies_detected: int
    total_multi_strategies_executed: int
    multi_profit: Decimal
    multi_success_rate: Decimal
    active_multi_strategies: int
    
    # Combined stats
    total_opportunities_detected: int
    total_opportunities_executed: int
    total_profit: Decimal
    active_opportunities: int
    top_profitable_pairs: List[Dict[str, any]]
    time_period: str


class ArbitrageHistoryFilterSchema(Schema):
    """Enhanced schema for filtering arbitrage history."""
    
    # Simple arbitrage filters
    opportunity_status: Optional[str] = None
    execution_status: Optional[str] = None
    
    # Multi-exchange filters
    strategy_type: Optional[str] = None
    strategy_status: Optional[str] = None
    min_complexity: Optional[int] = Field(None, ge=1)
    max_complexity: Optional[int] = Field(None, le=20)
    
    # Common filters
    trading_pair: Optional[str] = None
    exchange: Optional[str] = None
    min_profit: Optional[Decimal] = None
    max_profit: Optional[Decimal] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    include_simple: bool = True
    include_multi: bool = True
    page: int = 1
    page_size: int = Field(default=50, le=200)


class StrategyPerformanceSchema(Schema):
    """Schema for strategy performance comparison."""
    
    strategy_type: str
    total_executions: int
    successful_executions: int
    success_rate: Decimal
    total_profit: Decimal
    average_profit: Decimal
    average_profit_percentage: Decimal
    average_execution_time: Optional[float] = None
    complexity_score: Optional[int] = None


class MarketDepthAnalysisSchema(Schema):
    """Schema for market depth analysis."""
    
    trading_pair: str
    exchanges: Dict[str, Dict]
    analysis_time: datetime
    arbitrage_potential: Optional[Dict] = None
    liquidity_score: Optional[Dict[str, float]] = None


class RiskAssessmentSchema(Schema):
    """Schema for risk assessment of strategies."""
    
    strategy_id: UUID
    strategy_type: str
    risk_score: Decimal = Field(..., ge=0, le=100)
    risk_factors: List[Dict[str, any]]
    recommended_allocation: Decimal
    max_recommended_amount: Decimal
    warning_messages: List[str] = []


class BacktestRequestSchema(Schema):
    """Schema for backtesting multi-exchange strategies."""
    
    strategy_type: str
    trading_pairs: List[str]
    exchanges: List[str]
    start_date: datetime
    end_date: datetime
    initial_balance: Decimal = Field(..., gt=0)
    config_overrides: Optional[ArbitrageConfigUpdateSchema] = None
    
    @validator("end_date")
    def validate_date_range(cls, v, values):
        if "start_date" in values and v <= values["start_date"]:
            raise ValueError("End date must be after start date")
        return v


class BacktestResultSchema(Schema):
    """Schema for backtest results."""
    
    strategy_type: str
    start_date: datetime
    end_date: datetime
    initial_balance: Decimal
    final_balance: Decimal
    total_return: Decimal
    total_return_percentage: Decimal
    
    # Execution metrics
    total_strategies_executed: int
    successful_strategies: int
    failed_strategies: int
    success_rate: Decimal
    
    # Profitability metrics
    total_profit: Decimal
    average_profit_per_strategy: Decimal
    best_strategy_profit: Decimal
    worst_strategy_profit: Decimal
    
    # Risk metrics
    max_drawdown: Decimal
    max_drawdown_percentage: Decimal
    sharpe_ratio: Optional[Decimal] = None
    volatility: Optional[Decimal] = None
    
    # Time series data
    equity_curve: List[Dict[str, any]]
    monthly_returns: List[Dict[str, any]]
    strategy_breakdown: List[StrategyPerformanceSchema]
    
    # Execution details
    execution_summary: Dict[str, any]
    risk_analysis: Dict[str, any]


class OptimizationRequestSchema(Schema):
    """Schema for strategy optimization request."""
    
    strategy_type: str
    trading_pairs: List[str]
    exchanges: List[str]
    optimization_target: str = Field(default="profit")  # profit, risk_adjusted, sharpe
    constraints: Dict[str, any] = {}
    parameter_ranges: Dict[str, Dict[str, float]] = {}
    
    @validator("optimization_target")
    def validate_target(cls, v):
        allowed = ["profit", "risk_adjusted", "sharpe", "max_drawdown"]
        if v not in allowed:
            raise ValueError(f"Optimization target must be one of: {allowed}")
        return v


class OptimizationResultSchema(Schema):
    """Schema for optimization results."""
    
    optimal_config: ArbitrageConfigSchema
    expected_performance: BacktestResultSchema
    parameter_sensitivity: Dict[str, List[Dict[str, float]]]
    optimization_summary: Dict[str, any]


class RealTimeMonitoringSchema(Schema):
    """Schema for real-time strategy monitoring."""
    
    strategy_id: UUID
    current_status: str
    execution_progress: Dict[str, any]
    current_profit: Decimal
    estimated_completion: Optional[datetime] = None
    active_orders: List[Dict[str, any]]
    risk_alerts: List[str] = []
    performance_metrics: Dict[str, any]
    last_update: datetime


class AlertRuleSchema(Schema):
    """Schema for custom alert rules."""
    
    rule_name: str
    rule_type: str  # profit_threshold, volume_threshold, spread_threshold, etc.
    conditions: Dict[str, any]
    actions: List[str]  # email, sms, webhook, auto_execute
    is_active: bool = True
    trading_pairs: Optional[List[str]] = None
    exchanges: Optional[List[str]] = None


class WebhookConfigSchema(Schema):
    """Schema for webhook configuration."""
    
    webhook_url: str
    events: List[str]  # opportunity_detected, execution_completed, etc.
    headers: Optional[Dict[str, str]] = None
    authentication: Optional[Dict[str, str]] = None
    retry_config: Optional[Dict[str, int]] = None
    is_active: bool = True