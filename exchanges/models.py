from decimal import Decimal

from django.db import models

from core.models import Exchange, ExchangeTradingPair, TimestampedModel, TradingPair


class OrderBook(TimestampedModel):
    """
    Model for storing order book snapshots.
    """

    exchange_pair = models.ForeignKey(
        ExchangeTradingPair, on_delete=models.CASCADE, related_name="order_books"
    )
    timestamp = models.DateTimeField(db_index=True)
    
    class Meta:
        verbose_name = "Order Book"
        verbose_name_plural = "Order Books"
        ordering = ["-timestamp"]
        indexes = [
            models.Index(fields=["exchange_pair", "-timestamp"]),
        ]

    def __str__(self):
        return f"{self.exchange_pair} - {self.timestamp}"


class OrderBookEntry(models.Model):
    """
    Model for individual order book entries (bids/asks).
    """

    SIDE_CHOICES = [
        ("bid", "Bid"),
        ("ask", "Ask"),
    ]

    order_book = models.ForeignKey(
        OrderBook, on_delete=models.CASCADE, related_name="entries"
    )
    side = models.CharField(max_length=3, choices=SIDE_CHOICES)
    price = models.DecimalField(max_digits=20, decimal_places=8)
    amount = models.DecimalField(max_digits=20, decimal_places=8)
    total = models.DecimalField(max_digits=20, decimal_places=8)
    position = models.IntegerField()  # Position in the order book

    class Meta:
        verbose_name = "Order Book Entry"
        verbose_name_plural = "Order Book Entries"
        ordering = ["position"]
        indexes = [
            models.Index(fields=["order_book", "side", "position"]),
        ]

    def save(self, *args, **kwargs):
        if not self.total:
            self.total = self.price * self.amount # type: ignore
        super().save(*args, **kwargs)


class MarketTicker(TimestampedModel):
    """
    Model for storing market ticker data.
    """

    exchange_pair = models.ForeignKey(
        ExchangeTradingPair, on_delete=models.CASCADE, related_name="tickers"
    )
    timestamp = models.DateTimeField(db_index=True)
    last_price = models.DecimalField(max_digits=20, decimal_places=8)
    bid_price = models.DecimalField(max_digits=20, decimal_places=8, null=True)
    ask_price = models.DecimalField(max_digits=20, decimal_places=8, null=True)
    volume_24h = models.DecimalField(max_digits=20, decimal_places=8)
    high_24h = models.DecimalField(max_digits=20, decimal_places=8)
    low_24h = models.DecimalField(max_digits=20, decimal_places=8)
    change_24h = models.DecimalField(max_digits=10, decimal_places=4)

    class Meta:
        verbose_name = "Market Ticker"
        verbose_name_plural = "Market Tickers"
        ordering = ["-timestamp"]
        indexes = [
            models.Index(fields=["exchange_pair", "-timestamp"]),
        ]

    def __str__(self):
        return f"{self.exchange_pair} - {self.last_price} @ {self.timestamp}"


class ExchangeBalance(TimestampedModel):
    """
    Model for storing user balances on exchanges.
    """

    user = models.ForeignKey(
        "auth.User", on_delete=models.CASCADE, related_name="exchange_balances"
    )
    exchange = models.ForeignKey(
        Exchange, on_delete=models.CASCADE, related_name="user_balances"
    )
    currency = models.ForeignKey(
        "core.Currency", on_delete=models.CASCADE, related_name="exchange_balances"
    )
    available = models.DecimalField(max_digits=20, decimal_places=8, default=0)
    locked = models.DecimalField(max_digits=20, decimal_places=8, default=0)
    total = models.DecimalField(max_digits=20, decimal_places=8, default=0)
    last_updated = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Exchange Balance"
        verbose_name_plural = "Exchange Balances"
        unique_together = ["user", "exchange", "currency"]
        ordering = ["exchange", "currency"]

    def save(self, *args, **kwargs):
        self.total = self.available + self.locked # type: ignore
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.user.username} - {self.exchange.name} - {self.currency.symbol}: {self.total}" # type: ignore


class ExchangeStatus(TimestampedModel):
    """
    Model for tracking exchange status and health.
    """

    exchange = models.OneToOneField(
        Exchange, on_delete=models.CASCADE, related_name="status"
    )
    is_online = models.BooleanField(default=True)  # type: ignore
    last_check = models.DateTimeField(auto_now=True)
    response_time = models.FloatField(null=True, help_text="Response time in seconds")
    error_count = models.IntegerField(default=0)  # type: ignore
    last_error = models.TextField(blank=True)
    last_error_time = models.DateTimeField(null=True)

    class Meta:
        verbose_name = "Exchange Status"
        verbose_name_plural = "Exchange Statuses"

    def __str__(self):
        status = "Online" if self.is_online else "Offline"
        return f"{self.exchange.name} - {status}"