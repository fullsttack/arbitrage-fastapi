"""
Base models for the Crypto Arbitrage system.
"""

import uuid
from django.db import models
from django.utils import timezone



class TimestampedModel(models.Model):
    """
    Abstract base model with created and modified timestamps.
    """

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
        ordering = ["-created_at"]


class UUIDModel(models.Model):
    """
    Abstract base model with UUID as primary key.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    class Meta:
        abstract = True


class Currency(TimestampedModel):
    """
    Model representing a cryptocurrency or fiat currency.
    """

    symbol = models.CharField(max_length=10, unique=True, db_index=True)
    name = models.CharField(max_length=100)
    is_crypto = models.BooleanField(default=True)  # type: ignore
    decimal_places = models.IntegerField(default=8)  # type: ignore
    is_active = models.BooleanField(default=True)  # type: ignore

    class Meta:
        verbose_name = "Currency"
        verbose_name_plural = "Currencies"
        ordering = ["symbol"]

    def __str__(self):
        return f"{self.symbol} - {self.name}"


class TradingPair(TimestampedModel):
    """
    Model representing a trading pair (e.g., BTC/USDT).
    """

    base_currency = models.ForeignKey(
        Currency, on_delete=models.CASCADE, related_name="base_pairs"
    )
    quote_currency = models.ForeignKey(
        Currency, on_delete=models.CASCADE, related_name="quote_pairs"
    )
    symbol = models.CharField(max_length=20, unique=True, db_index=True)
    min_order_size = models.DecimalField(max_digits=20, decimal_places=8)
    max_order_size = models.DecimalField(max_digits=20, decimal_places=8)
    is_active = models.BooleanField(default=True)  # type: ignore

    class Meta:
        verbose_name = "Trading Pair"
        verbose_name_plural = "Trading Pairs"
        unique_together = ["base_currency", "quote_currency"]
        ordering = ["symbol"]

    def __str__(self):
        return self.symbol

    def save(self, *args, **kwargs):
        if not self.symbol:
            self.symbol = f"{self.base_currency.symbol}{self.quote_currency.symbol}"  # type: ignore
        super().save(*args, **kwargs)


class Exchange(TimestampedModel):
    """
    Model representing a cryptocurrency exchange.
    """

    EXCHANGE_CHOICES = [
        ("nobitex", "Nobitex"),
        ("wallex", "Wallex"),
        ("ramzinex", "Ramzinex"),
    ]

    name = models.CharField(max_length=50, unique=True)
    code = models.CharField(max_length=20, unique=True, choices=EXCHANGE_CHOICES)
    api_url = models.URLField()
    is_active = models.BooleanField(default=True)  # type: ignore
    rate_limit = models.IntegerField(default=60, help_text="Requests per minute")  # type: ignore

    # Fee structure
    maker_fee = models.DecimalField(
        max_digits=5, decimal_places=4, default=0.002, help_text="Maker fee percentage"
    )
    taker_fee = models.DecimalField(
        max_digits=5, decimal_places=4, default=0.002, help_text="Taker fee percentage"
    )

    class Meta:
        verbose_name = "Exchange"
        verbose_name_plural = "Exchanges"
        ordering = ["name"]

    def __str__(self):
        return self.name


class ExchangeTradingPair(TimestampedModel):
    """
    Model representing trading pairs available on specific exchanges.
    """

    exchange = models.ForeignKey(
        Exchange, on_delete=models.CASCADE, related_name="trading_pairs"
    )
    trading_pair = models.ForeignKey(
        TradingPair, on_delete=models.CASCADE, related_name="exchange_pairs"
    )
    exchange_symbol = models.CharField(
        max_length=50, help_text="Symbol used by the exchange"
    )
    min_order_size = models.DecimalField(max_digits=20, decimal_places=8)
    max_order_size = models.DecimalField(max_digits=20, decimal_places=8)
    min_order_value = models.DecimalField(max_digits=20, decimal_places=8)
    price_precision = models.IntegerField(default=8)  # type: ignore
    amount_precision = models.IntegerField(default=8)  # type: ignore
    is_active = models.BooleanField(default=True)  # type: ignore
    last_sync = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Exchange Trading Pair"
        verbose_name_plural = "Exchange Trading Pairs"
        unique_together = ["exchange", "trading_pair"]
        ordering = ["exchange", "trading_pair"]

    def __str__(self):
        return f"{self.exchange.name} - {self.trading_pair.symbol}" # type: ignore


class APICredential(TimestampedModel):
    """
    Model for storing encrypted API credentials for exchanges.
    """

    user = models.ForeignKey(
        "auth.User", on_delete=models.CASCADE, related_name="api_credentials"
    )
    exchange = models.ForeignKey(
        Exchange, on_delete=models.CASCADE, related_name="credentials"
    )
    api_key = models.CharField(max_length=255)  # Should be encrypted in production
    api_secret = models.CharField(max_length=255, blank=True)  # Should be encrypted
    is_active = models.BooleanField(default=True)  # type: ignore   
    permissions = models.JSONField(default=dict, blank=True)
    ip_whitelist = models.JSONField(default=list, blank=True)
    last_used = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "API Credential"
        verbose_name_plural = "API Credentials"
        unique_together = ["user", "exchange"]

    def __str__(self):
        return f"{self.user.username} - {self.exchange.name}" # type: ignore
