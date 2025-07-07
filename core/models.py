import uuid
from django.db import models
from django.utils import timezone
from django.conf import settings
from cryptography.fernet import Fernet
import logging

logger = logging.getLogger(__name__)


class TimestampedModel(models.Model):
    """
    Abstract base model with created and modified timestamps.
    """

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
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
    is_crypto = models.BooleanField(default=True, db_index=True)
    decimal_places = models.IntegerField(default=8)
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        verbose_name = "Currency"
        verbose_name_plural = "Currencies"
        ordering = ["symbol"]
        indexes = [
            models.Index(fields=["is_active", "is_crypto"]),
            models.Index(fields=["symbol", "is_active"]),
        ]

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
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        verbose_name = "Trading Pair"
        verbose_name_plural = "Trading Pairs"
        unique_together = ["base_currency", "quote_currency"]
        ordering = ["symbol"]
        indexes = [
            models.Index(fields=["is_active", "symbol"]),
            models.Index(fields=["base_currency", "quote_currency"]),
        ]

    def __str__(self):
        return self.symbol

    def save(self, *args, **kwargs):
        if not self.symbol:
            self.symbol = f"{self.base_currency.symbol}{self.quote_currency.symbol}"
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
    code = models.CharField(max_length=20, unique=True, choices=EXCHANGE_CHOICES, db_index=True)
    api_url = models.URLField()
    is_active = models.BooleanField(default=True, db_index=True)
    rate_limit = models.IntegerField(default=60, help_text="Requests per minute")
    
    # Enhanced security settings
    requires_ip_whitelist = models.BooleanField(default=False)
    max_daily_volume = models.DecimalField(max_digits=20, decimal_places=8, null=True, blank=True)
    
    # Performance settings
    connection_timeout = models.IntegerField(default=30, help_text="Connection timeout in seconds")
    read_timeout = models.IntegerField(default=30, help_text="Read timeout in seconds")

    # Fee structure
    maker_fee = models.DecimalField(
        max_digits=5, decimal_places=4, default=0.002, help_text="Maker fee percentage"
    )
    taker_fee = models.DecimalField(
        max_digits=5, decimal_places=4, default=0.002, help_text="Taker fee percentage"
    )
    
    # Reliability scoring
    reliability_score = models.DecimalField(
        max_digits=5, decimal_places=2, default=100.0, help_text="Reliability score (0-100)"
    )

    class Meta:
        verbose_name = "Exchange"
        verbose_name_plural = "Exchanges"
        ordering = ["name"]
        indexes = [
            models.Index(fields=["is_active", "code"]),
            models.Index(fields=["reliability_score", "-created_at"]),
        ]

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
    price_precision = models.IntegerField(default=8)
    amount_precision = models.IntegerField(default=8)
    is_active = models.BooleanField(default=True, db_index=True)
    last_sync = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Exchange Trading Pair"
        verbose_name_plural = "Exchange Trading Pairs"
        unique_together = ["exchange", "trading_pair"]
        ordering = ["exchange", "trading_pair"]
        indexes = [
            models.Index(fields=["exchange", "is_active"]),
            models.Index(fields=["trading_pair", "is_active"]),
            models.Index(fields=["is_active", "-last_sync"]),
        ]

    def __str__(self):
        return f"{self.exchange.name} - {self.trading_pair.symbol}"


class APICredential(TimestampedModel):
    """
    FIXED: Model for storing ENCRYPTED API credentials for exchanges.
    """

    user = models.ForeignKey(
        "auth.User", on_delete=models.CASCADE, related_name="api_credentials"
    )
    exchange = models.ForeignKey(
        Exchange, on_delete=models.CASCADE, related_name="credentials"
    )
    
    # ENCRYPTED fields
    encrypted_api_key = models.TextField(help_text="Encrypted API key")
    encrypted_api_secret = models.TextField(blank=True, help_text="Encrypted API secret")
    
    # Security settings
    is_active = models.BooleanField(default=True, db_index=True)
    permissions = models.JSONField(default=dict, blank=True)
    ip_whitelist = models.JSONField(default=list, blank=True)
    
    # Usage tracking
    last_used = models.DateTimeField(null=True, blank=True, db_index=True)
    usage_count = models.IntegerField(default=0)
    
    # Security monitoring
    failed_attempts = models.IntegerField(default=0)
    last_failed_attempt = models.DateTimeField(null=True, blank=True)
    is_locked = models.BooleanField(default=False)
    locked_until = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "API Credential"
        verbose_name_plural = "API Credentials"
        unique_together = ["user", "exchange"]
        indexes = [
            models.Index(fields=["user", "exchange", "is_active"]),
            models.Index(fields=["is_active", "-last_used"]),
            models.Index(fields=["is_locked", "locked_until"]),
        ]

    def __str__(self):
        return f"{self.user.username} - {self.exchange.name}"
    
    def _get_cipher(self):
        """Get Fernet cipher for encryption/decryption."""
        if not hasattr(settings, 'ENCRYPTION_KEY'):
            raise ValueError("ENCRYPTION_KEY not found in settings")
        return Fernet(settings.ENCRYPTION_KEY.encode() if isinstance(settings.ENCRYPTION_KEY, str) else settings.ENCRYPTION_KEY)
    
    def set_api_key(self, api_key: str):
        """Encrypt and store API key."""
        try:
            cipher = self._get_cipher()
            self.encrypted_api_key = cipher.encrypt(api_key.encode()).decode()
        except Exception as e:
            logger.error(f"Failed to encrypt API key: {e}")
            raise
    
    def get_api_key(self) -> str:
        """Decrypt and return API key."""
        try:
            if not self.encrypted_api_key:
                return ""
            cipher = self._get_cipher()
            return cipher.decrypt(self.encrypted_api_key.encode()).decode()
        except Exception as e:
            logger.error(f"Failed to decrypt API key: {e}")
            raise
    
    def set_api_secret(self, api_secret: str):
        """Encrypt and store API secret."""
        try:
            cipher = self._get_cipher()
            self.encrypted_api_secret = cipher.encrypt(api_secret.encode()).decode()
        except Exception as e:
            logger.error(f"Failed to encrypt API secret: {e}")
            raise
    
    def get_api_secret(self) -> str:
        """Decrypt and return API secret."""
        try:
            if not self.encrypted_api_secret:
                return ""
            cipher = self._get_cipher()
            return cipher.decrypt(self.encrypted_api_secret.encode()).decode()
        except Exception as e:
            logger.error(f"Failed to decrypt API secret: {e}")
            raise
    
    # Properties for backward compatibility
    @property
    def api_key(self):
        return self.get_api_key()
    
    @api_key.setter
    def api_key(self, value):
        self.set_api_key(value)
    
    @property
    def api_secret(self):
        return self.get_api_secret()
    
    @api_secret.setter
    def api_secret(self, value):
        self.set_api_secret(value)
    
    def record_usage(self):
        """Record successful API usage."""
        self.last_used = timezone.now()
        self.usage_count += 1
        self.failed_attempts = 0  # Reset failed attempts on success
        if self.is_locked:
            self.is_locked = False
            self.locked_until = None
        self.save(update_fields=['last_used', 'usage_count', 'failed_attempts', 'is_locked', 'locked_until'])
    
    def record_failed_attempt(self):
        """Record failed API attempt and potentially lock account."""
        self.failed_attempts += 1
        self.last_failed_attempt = timezone.now()
        
        # Lock after 5 failed attempts for 1 hour
        if self.failed_attempts >= 5:
            self.is_locked = True
            self.locked_until = timezone.now() + timezone.timedelta(hours=1)
        
        self.save(update_fields=['failed_attempts', 'last_failed_attempt', 'is_locked', 'locked_until'])
    
    def is_usable(self):
        """Check if credentials can be used (not locked)."""
        if not self.is_active:
            return False
        
        if self.is_locked:
            if self.locked_until and timezone.now() > self.locked_until:
                # Auto-unlock if lock period has passed
                self.is_locked = False
                self.locked_until = None
                self.failed_attempts = 0
                self.save(update_fields=['is_locked', 'locked_until', 'failed_attempts'])
                return True
            return False
        
        return True


class UserAPIKey(TimestampedModel):
    """
    NEW: Model for user API keys to access our platform.
    """
    
    user = models.ForeignKey(
        "auth.User", on_delete=models.CASCADE, related_name="platform_api_keys"
    )
    name = models.CharField(max_length=100, help_text="Human-readable name for this key")
    key_hash = models.CharField(max_length=128, unique=True, db_index=True)
    key_preview = models.CharField(max_length=12, help_text="First 8 chars for display")
    
    # Permissions
    permissions = models.JSONField(default=list, help_text="List of allowed actions")
    ip_whitelist = models.JSONField(default=list, blank=True)
    
    # Usage tracking
    is_active = models.BooleanField(default=True, db_index=True)
    last_used = models.DateTimeField(null=True, blank=True)
    usage_count = models.IntegerField(default=0)
    
    # Rate limiting
    rate_limit_per_hour = models.IntegerField(default=1000)
    
    # Security
    expires_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        verbose_name = "User API Key"
        verbose_name_plural = "User API Keys"
        indexes = [
            models.Index(fields=["user", "is_active"]),
            models.Index(fields=["key_hash", "is_active"]),
            models.Index(fields=["expires_at", "is_active"]),
        ]
    
    def __str__(self):
        return f"{self.user.username} - {self.name}"
    
    def is_valid(self):
        """Check if API key is valid and not expired."""
        if not self.is_active:
            return False
        
        if self.expires_at and timezone.now() > self.expires_at:
            return False
        
        return True