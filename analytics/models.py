from decimal import Decimal

from django.contrib.auth.models import User
from django.db import models

from core.models import Exchange, TimestampedModel, TradingPair


class DailyArbitrageSummary(TimestampedModel):
    """
    Daily summary of arbitrage opportunities.
    """
    date = models.DateField(unique=True)
    total_opportunities = models.IntegerField(default=0)
    total_executions = models.IntegerField(default=0)
    successful_executions = models.IntegerField(default=0)
    failed_executions = models.IntegerField(default=0)
    
    # Profit metrics
    total_profit = models.DecimalField(max_digits=20, decimal_places=8, default=0)
    average_profit_percentage = models.DecimalField(
        max_digits=10,
        decimal_places=4,
        default=0
    )
    highest_profit_percentage = models.DecimalField(
        max_digits=10,
        decimal_places=4,
        default=0
    )
    
    # Top performers
    top_trading_pair = models.ForeignKey(
        TradingPair,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="daily_summaries"
    )
    top_route = models.JSONField(default=dict)  # {"buy": "exchange1", "sell": "exchange2"}
    
    # Market conditions
    total_volume_traded = models.DecimalField(
        max_digits=20,
        decimal_places=8,
        default=0
    )
    market_volatility_index = models.DecimalField(
        max_digits=10,
        decimal_places=4,
        null=True,
        blank=True
    )
    
    class Meta:
        verbose_name = "Daily Arbitrage Summary"
        verbose_name_plural = "Daily Arbitrage Summaries"
        ordering = ["-date"]
    
    def __str__(self):
        return f"Summary for {self.date}"


class ExchangePerformance(TimestampedModel):
    """
    Track exchange performance metrics.
    """
    exchange = models.ForeignKey(
        Exchange,
        on_delete=models.CASCADE,
        related_name="performance_metrics"
    )
    date = models.DateField()
    
    # Availability metrics
    uptime_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=100
    )
    average_response_time = models.FloatField(
        help_text="Average API response time in seconds"
    )
    error_count = models.IntegerField(default=0)
    
    # Trading metrics
    total_orders_placed = models.IntegerField(default=0)
    successful_orders = models.IntegerField(default=0)
    failed_orders = models.IntegerField(default=0)
    
    # Arbitrage metrics
    opportunities_as_buy = models.IntegerField(default=0)
    opportunities_as_sell = models.IntegerField(default=0)
    total_volume = models.DecimalField(max_digits=20, decimal_places=8, default=0)
    
    class Meta:
        unique_together = ["exchange", "date"]
        verbose_name = "Exchange Performance"
        verbose_name_plural = "Exchange Performances"
        ordering = ["-date", "exchange"]
    
    def __str__(self):
        return f"{self.exchange.name} - {self.date}"


class TradingPairAnalytics(TimestampedModel):
    """
    Analytics for trading pairs.
    """
    trading_pair = models.ForeignKey(
        TradingPair,
        on_delete=models.CASCADE,
        related_name="analytics"
    )
    period_start = models.DateTimeField()
    period_end = models.DateTimeField()
    period_type = models.CharField(
        max_length=20,
        choices=[
            ("hourly", "Hourly"),
            ("daily", "Daily"),
            ("weekly", "Weekly"),
            ("monthly", "Monthly"),
        ]
    )
    
    # Opportunity metrics
    total_opportunities = models.IntegerField(default=0)
    average_spread_percentage = models.DecimalField(
        max_digits=10,
        decimal_places=4,
        default=0
    )
    max_spread_percentage = models.DecimalField(
        max_digits=10,
        decimal_places=4,
        default=0
    )
    
    # Execution metrics
    total_executions = models.IntegerField(default=0)
    success_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    average_profit = models.DecimalField(max_digits=20, decimal_places=8, default=0)
    total_volume = models.DecimalField(max_digits=20, decimal_places=8, default=0)
    
    # Market metrics
    price_volatility = models.DecimalField(
        max_digits=10,
        decimal_places=4,
        null=True,
        blank=True
    )
    average_price = models.DecimalField(
        max_digits=20,
        decimal_places=8,
        null=True,
        blank=True
    )
    
    # Best performing routes
    top_routes = models.JSONField(default=list)  # List of {"buy": "ex1", "sell": "ex2", "count": n}
    
    class Meta:
        unique_together = ["trading_pair", "period_start", "period_type"]
        verbose_name = "Trading Pair Analytics"
        verbose_name_plural = "Trading Pair Analytics"
        ordering = ["-period_start"]
        indexes = [
            models.Index(fields=["trading_pair", "period_type", "-period_start"]),
        ]
    
    def __str__(self):
        return f"{self.trading_pair.symbol} - {self.period_type} - {self.period_start}"


class UserPerformance(TimestampedModel):
    """
    Track user trading performance.
    """
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="performance_metrics"
    )
    date = models.DateField()
    
    # Execution metrics
    total_executions = models.IntegerField(default=0)
    successful_executions = models.IntegerField(default=0)
    failed_executions = models.IntegerField(default=0)
    
    # Profit metrics
    daily_profit = models.DecimalField(max_digits=20, decimal_places=8, default=0)
    daily_loss = models.DecimalField(max_digits=20, decimal_places=8, default=0)
    net_profit = models.DecimalField(max_digits=20, decimal_places=8, default=0)
    roi_percentage = models.DecimalField(max_digits=10, decimal_places=4, default=0)
    
    # Volume metrics
    total_volume_traded = models.DecimalField(max_digits=20, decimal_places=8, default=0)
    total_fees_paid = models.DecimalField(max_digits=20, decimal_places=8, default=0)
    
    # Risk metrics
    max_drawdown = models.DecimalField(
        max_digits=10,
        decimal_places=4,
        null=True,
        blank=True
    )
    sharpe_ratio = models.DecimalField(
        max_digits=10,
        decimal_places=4,
        null=True,
        blank=True
    )
    
    class Meta:
        unique_together = ["user", "date"]
        verbose_name = "User Performance"
        verbose_name_plural = "User Performances"
        ordering = ["-date"]
    
    def __str__(self):
        return f"{self.user.username} - {self.date}"


class MarketSnapshot(TimestampedModel):
    """
    Periodic market snapshots for analysis.
    """
    timestamp = models.DateTimeField(unique=True)
    
    # Market overview
    total_market_volume = models.DecimalField(max_digits=20, decimal_places=8)
    active_trading_pairs = models.IntegerField()
    active_exchanges = models.IntegerField()
    
    # Arbitrage metrics
    active_opportunities = models.IntegerField()
    average_spread = models.DecimalField(max_digits=10, decimal_places=4)
    max_spread = models.DecimalField(max_digits=10, decimal_places=4)
    
    # Top opportunities
    top_opportunities = models.JSONField(
        default=list,
        help_text="List of top arbitrage opportunities at this moment"
    )
    
    # Market sentiment
    market_trend = models.CharField(
        max_length=20,
        choices=[
            ("bullish", "Bullish"),
            ("bearish", "Bearish"),
            ("neutral", "Neutral"),
            ("volatile", "Volatile"),
        ],
        default="neutral"
    )
    
    # Exchange status
    exchange_status = models.JSONField(
        default=dict,
        help_text="Status of each exchange at snapshot time"
    )
    
    class Meta:
        verbose_name = "Market Snapshot"
        verbose_name_plural = "Market Snapshots"
        ordering = ["-timestamp"]
    
    def __str__(self):
        return f"Market Snapshot - {self.timestamp}"