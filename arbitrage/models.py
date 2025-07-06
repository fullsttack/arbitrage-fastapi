"""
Models for arbitrage opportunities and related data.
"""

from decimal import Decimal

from django.contrib.auth.models import User
from django.db import models

from core.models import Exchange, TimestampedModel, TradingPair, UUIDModel


class ArbitrageOpportunity(UUIDModel, TimestampedModel):
    """
    Model representing an arbitrage opportunity between exchanges.
    """

    STATUS_CHOICES = [
        ("detected", "Detected"),
        ("executing", "Executing"),
        ("executed", "Executed"),
        ("expired", "Expired"),
        ("failed", "Failed"),
    ]

    trading_pair = models.ForeignKey(
        TradingPair, on_delete=models.CASCADE, related_name="arbitrage_opportunities"
    )
    buy_exchange = models.ForeignKey(
        Exchange, on_delete=models.CASCADE, related_name="arbitrage_buy_opportunities"
    )
    sell_exchange = models.ForeignKey(
        Exchange, on_delete=models.CASCADE, related_name="arbitrage_sell_opportunities"
    )
    
    # Prices
    buy_price = models.DecimalField(max_digits=20, decimal_places=8)
    sell_price = models.DecimalField(max_digits=20, decimal_places=8)
    
    # Amounts
    available_buy_amount = models.DecimalField(max_digits=20, decimal_places=8)
    available_sell_amount = models.DecimalField(max_digits=20, decimal_places=8)
    optimal_amount = models.DecimalField(max_digits=20, decimal_places=8)
    
    # Profit calculations
    gross_profit_percentage = models.DecimalField(max_digits=10, decimal_places=4)
    net_profit_percentage = models.DecimalField(max_digits=10, decimal_places=4)
    estimated_profit = models.DecimalField(max_digits=20, decimal_places=8)
    
    # Fees
    buy_fee = models.DecimalField(max_digits=20, decimal_places=8)
    sell_fee = models.DecimalField(max_digits=20, decimal_places=8)
    total_fees = models.DecimalField(max_digits=20, decimal_places=8)
    
    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="detected")
    expires_at = models.DateTimeField()
    executed_at = models.DateTimeField(null=True, blank=True)
    
    # Execution details
    executed_amount = models.DecimalField(
        max_digits=20, decimal_places=8, null=True, blank=True
    )
    actual_profit = models.DecimalField(
        max_digits=20, decimal_places=8, null=True, blank=True
    )
    
    # Metadata
    detection_latency = models.FloatField(
        help_text="Time taken to detect opportunity in seconds"
    )
    market_depth = models.JSONField(default=dict, blank=True)

    class Meta:
        verbose_name = "Arbitrage Opportunity"
        verbose_name_plural = "Arbitrage Opportunities"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status", "-created_at"]),
            models.Index(fields=["trading_pair", "-created_at"]),
            models.Index(fields=["-net_profit_percentage"]),
        ]

    def __str__(self):
        return f"{self.trading_pair.symbol}: {self.buy_exchange.name} -> {self.sell_exchange.name} ({self.net_profit_percentage}%)"

    def calculate_fees(self):
        """Calculate total fees for the arbitrage."""
        buy_amount = self.optimal_amount * self.buy_price
        self.buy_fee = buy_amount * self.buy_exchange.taker_fee
        self.sell_fee = self.optimal_amount * self.sell_price * self.sell_exchange.taker_fee
        self.total_fees = self.buy_fee + self.sell_fee
        return self.total_fees

    def calculate_profit(self):
        """Calculate estimated profit."""
        buy_cost = self.optimal_amount * self.buy_price
        sell_revenue = self.optimal_amount * self.sell_price
        self.estimated_profit = sell_revenue - buy_cost - self.total_fees
        return self.estimated_profit


class ArbitrageConfig(TimestampedModel):
    """
    Model for storing arbitrage configuration per user.
    """

    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name="arbitrage_config"
    )
    
    # Trading settings
    is_active = models.BooleanField(default=True)
    auto_trade = models.BooleanField(default=False)
    
    # Thresholds
    min_profit_percentage = models.DecimalField(
        max_digits=5, decimal_places=2, default=0.5,
        help_text="Minimum profit percentage to consider"
    )
    min_profit_amount = models.DecimalField(
        max_digits=20, decimal_places=8, default=10,
        help_text="Minimum profit amount in quote currency"
    )
    
    # Trading limits
    max_trade_amount = models.JSONField(
        default=dict, help_text="Maximum trade amount per currency"
    )
    daily_trade_limit = models.JSONField(
        default=dict, help_text="Daily trade limit per currency"
    )
    
    # Risk management
    max_exposure_percentage = models.DecimalField(
        max_digits=5, decimal_places=2, default=10,
        help_text="Maximum percentage of balance to use"
    )
    stop_loss_percentage = models.DecimalField(
        max_digits=5, decimal_places=2, default=2,
        help_text="Stop loss percentage"
    )
    
    # Notifications
    enable_notifications = models.BooleanField(default=True)
    notification_channels = models.JSONField(
        default=list, help_text="List of notification channels (email, sms, etc.)"
    )
    
    # Exchange preferences
    enabled_exchanges = models.ManyToManyField(
        Exchange, related_name="arbitrage_configs", blank=True
    )
    enabled_pairs = models.ManyToManyField(
        TradingPair, related_name="arbitrage_configs", blank=True
    )
    
    # Advanced settings
    use_market_orders = models.BooleanField(
        default=False, help_text="Use market orders instead of limit orders"
    )
    slippage_tolerance = models.DecimalField(
        max_digits=5, decimal_places=2, default=0.5,
        help_text="Maximum acceptable slippage percentage"
    )

    class Meta:
        verbose_name = "Arbitrage Configuration"
        verbose_name_plural = "Arbitrage Configurations"

    def __str__(self):
        return f"{self.user.username} - Arbitrage Config"


class ArbitrageExecution(UUIDModel, TimestampedModel):
    """
    Model for tracking arbitrage execution details.
    """

    EXECUTION_STATUS = [
        ("pending", "Pending"),
        ("buy_placed", "Buy Order Placed"),
        ("buy_filled", "Buy Order Filled"),
        ("sell_placed", "Sell Order Placed"),
        ("sell_filled", "Sell Order Filled"),
        ("completed", "Completed"),
        ("failed", "Failed"),
        ("cancelled", "Cancelled"),
    ]

    opportunity = models.OneToOneField(
        ArbitrageOpportunity, on_delete=models.CASCADE, related_name="execution"
    )
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="arbitrage_executions"
    )
    
    # Execution status
    status = models.CharField(
        max_length=20, choices=EXECUTION_STATUS, default="pending"
    )
    
    # Buy order details
    buy_order_id = models.CharField(max_length=255, blank=True)
    buy_order_status = models.CharField(max_length=50, blank=True)
    buy_filled_amount = models.DecimalField(
        max_digits=20, decimal_places=8, default=0
    )
    buy_average_price = models.DecimalField(
        max_digits=20, decimal_places=8, null=True, blank=True
    )
    buy_fee_paid = models.DecimalField(
        max_digits=20, decimal_places=8, default=0
    )
    
    # Sell order details
    sell_order_id = models.CharField(max_length=255, blank=True)
    sell_order_status = models.CharField(max_length=50, blank=True)
    sell_filled_amount = models.DecimalField(
        max_digits=20, decimal_places=8, default=0
    )
    sell_average_price = models.DecimalField(
        max_digits=20, decimal_places=8, null=True, blank=True
    )
    sell_fee_paid = models.DecimalField(
        max_digits=20, decimal_places=8, default=0
    )
    
    # Timing
    buy_order_placed_at = models.DateTimeField(null=True, blank=True)
    buy_order_filled_at = models.DateTimeField(null=True, blank=True)
    sell_order_placed_at = models.DateTimeField(null=True, blank=True)
    sell_order_filled_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    # Results
    final_profit = models.DecimalField(
        max_digits=20, decimal_places=8, null=True, blank=True
    )
    profit_percentage = models.DecimalField(
        max_digits=10, decimal_places=4, null=True, blank=True
    )
    
    # Error tracking
    error_message = models.TextField(blank=True)
    retry_count = models.IntegerField(default=0)

    class Meta:
        verbose_name = "Arbitrage Execution"
        verbose_name_plural = "Arbitrage Executions"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.opportunity.trading_pair.symbol} - {self.status}"

    def calculate_final_profit(self):
        """Calculate the actual profit after execution."""
        if self.buy_average_price and self.sell_average_price:
            buy_cost = self.buy_filled_amount * self.buy_average_price + self.buy_fee_paid
            sell_revenue = self.sell_filled_amount * self.sell_average_price - self.sell_fee_paid
            self.final_profit = sell_revenue - buy_cost
            
            if buy_cost > 0:
                self.profit_percentage = (self.final_profit / buy_cost) * 100
            
            return self.final_profit
        return None


class ArbitrageAlert(TimestampedModel):
    """
    Model for arbitrage alerts and notifications.
    """

    ALERT_TYPE_CHOICES = [
        ("opportunity", "Opportunity Detected"),
        ("execution_started", "Execution Started"),
        ("execution_completed", "Execution Completed"),
        ("execution_failed", "Execution Failed"),
        ("high_profit", "High Profit Opportunity"),
        ("market_anomaly", "Market Anomaly"),
    ]

    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="arbitrage_alerts"
    )
    opportunity = models.ForeignKey(
        ArbitrageOpportunity,
        on_delete=models.CASCADE,
        related_name="alerts",
        null=True,
        blank=True,
    )
    alert_type = models.CharField(max_length=30, choices=ALERT_TYPE_CHOICES)
    title = models.CharField(max_length=255)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    sent_via = models.JSONField(default=list)  # ["email", "sms", "push"]
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        verbose_name = "Arbitrage Alert"
        verbose_name_plural = "Arbitrage Alerts"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "is_read", "-created_at"]),
        ]

    def __str__(self):
        return f"{self.user.username} - {self.alert_type} - {self.created_at}"