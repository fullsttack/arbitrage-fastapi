from decimal import Decimal

from django.contrib.auth.models import User
from django.db import models

from core.models import Exchange, TimestampedModel, TradingPair, UUIDModel


class Order(UUIDModel, TimestampedModel):
    """
    Model representing a trading order.
    """

    ORDER_TYPE_CHOICES = [
        ("MARKET", "Market Order"),
        ("LIMIT", "Limit Order"),
        ("STOP", "Stop Order"),
        ("STOP_LIMIT", "Stop Limit Order"),
    ]

    ORDER_SIDE_CHOICES = [
        ("BUY", "Buy"),
        ("SELL", "Sell"),
    ]

    ORDER_STATUS_CHOICES = [
        ("PENDING", "Pending"),
        ("OPEN", "Open"),
        ("PARTIAL", "Partially Filled"),
        ("FILLED", "Filled"),
        ("CANCELLED", "Cancelled"),
        ("REJECTED", "Rejected"),
        ("EXPIRED", "Expired"),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="orders")
    exchange = models.ForeignKey(
        Exchange, on_delete=models.CASCADE, related_name="orders"
    )
    trading_pair = models.ForeignKey(
        TradingPair, on_delete=models.CASCADE, related_name="orders"
    )
    
    # Order details
    exchange_order_id = models.CharField(max_length=255, db_index=True)
    order_type = models.CharField(max_length=20, choices=ORDER_TYPE_CHOICES)
    side = models.CharField(max_length=10, choices=ORDER_SIDE_CHOICES)
    status = models.CharField(
        max_length=20, choices=ORDER_STATUS_CHOICES, default="PENDING"
    )
    
    # Amounts and prices
    amount = models.DecimalField(max_digits=20, decimal_places=8)
    price = models.DecimalField(max_digits=20, decimal_places=8, null=True, blank=True)
    stop_price = models.DecimalField(
        max_digits=20, decimal_places=8, null=True, blank=True
    )
    
    # Execution details
    filled_amount = models.DecimalField(max_digits=20, decimal_places=8, default=0)
    average_price = models.DecimalField(
        max_digits=20, decimal_places=8, null=True, blank=True
    )
    fee = models.DecimalField(max_digits=20, decimal_places=8, default=0)
    fee_currency = models.CharField(max_length=10, blank=True)
    
    # Timing
    placed_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    filled_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    
    # Metadata
    is_arbitrage = models.BooleanField(default=False)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        verbose_name = "Order"
        verbose_name_plural = "Orders"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "-created_at"]),
            models.Index(fields=["exchange", "exchange_order_id"]),
            models.Index(fields=["status", "-created_at"]),
        ]

    def __str__(self):
        return f"{self.side} {self.amount} {self.trading_pair.symbol} @ {self.exchange.name}"

    @property
    def is_buy(self):
        return self.side == "BUY"

    @property
    def is_sell(self):
        return self.side == "SELL"

    @property
    def is_open(self):
        return self.status in ["PENDING", "OPEN", "PARTIAL"]

    @property
    def is_complete(self):
        return self.status in ["FILLED", "CANCELLED", "REJECTED", "EXPIRED"]

    @property
    def remaining_amount(self):
        return self.amount - self.filled_amount

    @property
    def fill_percentage(self):
        if self.amount > 0:
            return (self.filled_amount / self.amount) * 100
        return 0

    def calculate_total_cost(self):
        """Calculate total cost/revenue including fees."""
        if self.average_price:
            base_amount = self.filled_amount * self.average_price
            if self.is_buy:
                return base_amount + self.fee
            else:
                return base_amount - self.fee
        return 0


class Trade(UUIDModel, TimestampedModel):
    """
    Model representing executed trades (fills).
    """

    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="trades")
    exchange_trade_id = models.CharField(max_length=255)
    
    # Trade details
    price = models.DecimalField(max_digits=20, decimal_places=8)
    amount = models.DecimalField(max_digits=20, decimal_places=8)
    fee = models.DecimalField(max_digits=20, decimal_places=8, default=0)
    fee_currency = models.CharField(max_length=10, blank=True)
    
    # Timing
    executed_at = models.DateTimeField()
    
    # Metadata
    is_maker = models.BooleanField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        verbose_name = "Trade"
        verbose_name_plural = "Trades"
        ordering = ["-executed_at"]
        unique_together = ["order", "exchange_trade_id"]

    def __str__(self):
        return f"{self.amount} @ {self.price} - {self.order.trading_pair.symbol}"

    @property
    def total_value(self):
        return self.amount * self.price


class TradingStrategy(TimestampedModel):
    """
    Model for automated trading strategies.
    """

    STRATEGY_TYPE_CHOICES = [
        ("ARBITRAGE", "Arbitrage"),
        ("MARKET_MAKING", "Market Making"),
        ("TREND_FOLLOWING", "Trend Following"),
        ("MEAN_REVERSION", "Mean Reversion"),
        ("DCA", "Dollar Cost Averaging"),
        ("CUSTOM", "Custom Strategy"),
    ]

    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="trading_strategies"
    )
    name = models.CharField(max_length=100)
    strategy_type = models.CharField(max_length=30, choices=STRATEGY_TYPE_CHOICES)
    description = models.TextField(blank=True)
    
    # Configuration
    is_active = models.BooleanField(default=False)
    config = models.JSONField(default=dict)
    
    # Constraints
    enabled_exchanges = models.ManyToManyField(
        Exchange, related_name="strategies", blank=True
    )
    enabled_pairs = models.ManyToManyField(
        TradingPair, related_name="strategies", blank=True
    )
    
    # Risk management
    max_position_size = models.DecimalField(
        max_digits=20, decimal_places=8, null=True, blank=True
    )
    stop_loss_percentage = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True
    )
    take_profit_percentage = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True
    )
    
    # Performance tracking
    total_trades = models.IntegerField(default=0)
    winning_trades = models.IntegerField(default=0)
    total_profit = models.DecimalField(max_digits=20, decimal_places=8, default=0)
    
    # Execution
    last_run = models.DateTimeField(null=True, blank=True)
    next_run = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Trading Strategy"
        verbose_name_plural = "Trading Strategies"
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} ({self.strategy_type})"

    @property
    def win_rate(self):
        if self.total_trades > 0:
            return (self.winning_trades / self.total_trades) * 100
        return 0

    @property
    def average_profit_per_trade(self):
        if self.total_trades > 0:
            return self.total_profit / self.total_trades
        return 0


class Position(UUIDModel, TimestampedModel):
    """
    Model for tracking open positions.
    """

    POSITION_STATUS_CHOICES = [
        ("OPEN", "Open"),
        ("CLOSED", "Closed"),
        ("LIQUIDATED", "Liquidated"),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="positions")
    exchange = models.ForeignKey(
        Exchange, on_delete=models.CASCADE, related_name="positions"
    )
    trading_pair = models.ForeignKey(
        TradingPair, on_delete=models.CASCADE, related_name="positions"
    )
    strategy = models.ForeignKey(
        TradingStrategy,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="positions",
    )
    
    # Position details
    side = models.CharField(max_length=10, choices=[("LONG", "Long"), ("SHORT", "Short")])
    status = models.CharField(
        max_length=20, choices=POSITION_STATUS_CHOICES, default="OPEN"
    )
    
    # Amounts and prices
    amount = models.DecimalField(max_digits=20, decimal_places=8)
    entry_price = models.DecimalField(max_digits=20, decimal_places=8)
    exit_price = models.DecimalField(
        max_digits=20, decimal_places=8, null=True, blank=True
    )
    
    # Risk management
    stop_loss_price = models.DecimalField(
        max_digits=20, decimal_places=8, null=True, blank=True
    )
    take_profit_price = models.DecimalField(
        max_digits=20, decimal_places=8, null=True, blank=True
    )
    
    # P&L
    unrealized_pnl = models.DecimalField(
        max_digits=20, decimal_places=8, default=0
    )
    realized_pnl = models.DecimalField(
        max_digits=20, decimal_places=8, default=0
    )
    
    # Orders
    entry_orders = models.ManyToManyField(
        Order, related_name="entry_positions", blank=True
    )
    exit_orders = models.ManyToManyField(
        Order, related_name="exit_positions", blank=True
    )
    
    # Timing
    opened_at = models.DateTimeField(auto_now_add=True)
    closed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Position"
        verbose_name_plural = "Positions"
        ordering = ["-opened_at"]
        indexes = [
            models.Index(fields=["user", "status", "-opened_at"]),
        ]

    def __str__(self):
        return f"{self.side} {self.amount} {self.trading_pair.symbol}"

    def update_unrealized_pnl(self, current_price):
        """Update unrealized P&L based on current price."""
        if self.status == "OPEN":
            if self.side == "LONG":
                self.unrealized_pnl = (current_price - self.entry_price) * self.amount
            else:  # SHORT
                self.unrealized_pnl = (self.entry_price - current_price) * self.amount
            self.save()

    def close_position(self, exit_price):
        """Close the position and calculate realized P&L."""
        self.exit_price = exit_price
        self.status = "CLOSED"
        self.closed_at = timezone.now()
        
        if self.side == "LONG":
            self.realized_pnl = (exit_price - self.entry_price) * self.amount
        else:  # SHORT
            self.realized_pnl = (self.entry_price - exit_price) * self.amount
        
        self.unrealized_pnl = 0
        self.save()


class TradingAlert(TimestampedModel):
    """
    Model for trading alerts and notifications.
    """

    ALERT_TYPE_CHOICES = [
        ("ORDER_FILLED", "Order Filled"),
        ("ORDER_CANCELLED", "Order Cancelled"),
        ("POSITION_OPENED", "Position Opened"),
        ("POSITION_CLOSED", "Position Closed"),
        ("STOP_LOSS_HIT", "Stop Loss Hit"),
        ("TAKE_PROFIT_HIT", "Take Profit Hit"),
        ("STRATEGY_ERROR", "Strategy Error"),
        ("LOW_BALANCE", "Low Balance Warning"),
    ]

    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="trading_alerts"
    )
    alert_type = models.CharField(max_length=30, choices=ALERT_TYPE_CHOICES)
    title = models.CharField(max_length=255)
    message = models.TextField()
    
    # Related objects
    order = models.ForeignKey(
        Order, on_delete=models.CASCADE, null=True, blank=True, related_name="alerts"
    )
    position = models.ForeignKey(
        Position, on_delete=models.CASCADE, null=True, blank=True, related_name="alerts"
    )
    
    # Status
    is_read = models.BooleanField(default=False)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        verbose_name = "Trading Alert"
        verbose_name_plural = "Trading Alerts"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "is_read", "-created_at"]),
        ]

    def __str__(self):
        return f"{self.alert_type} - {self.title}"