from django.contrib.auth.models import User
from django.db import models

from core.models import Exchange, TimestampedModel


class UserProfile(TimestampedModel):
    """
    Extended user profile for additional settings.
    """
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="profile"
    )
    
    # Contact information
    phone = models.CharField(max_length=20, blank=True)
    telegram_id = models.CharField(max_length=100, blank=True)
    
    # Notification preferences
    enable_email_alerts = models.BooleanField(default=True)
    enable_telegram_alerts = models.BooleanField(default=False)
    enable_push_notifications = models.BooleanField(default=False)
    
    # Trading preferences
    default_exchange = models.ForeignKey(
        Exchange,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="default_for_users"
    )
    
    # Other preferences
    timezone = models.CharField(max_length=50, default="UTC")
    language = models.CharField(max_length=10, default="en")
    
    # Account limits
    daily_trade_count = models.IntegerField(default=0)
    last_trade_reset = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        verbose_name = "User Profile"
        verbose_name_plural = "User Profiles"
    
    def __str__(self):
        return f"{self.user.username} Profile"


class NotificationSetting(TimestampedModel):
    """
    Granular notification settings per alert type.
    """
    NOTIFICATION_TYPES = [
        ("opportunity_detected", "Arbitrage Opportunity Detected"),
        ("execution_started", "Execution Started"),
        ("execution_completed", "Execution Completed"),
        ("execution_failed", "Execution Failed"),
        ("high_profit", "High Profit Opportunity"),
        ("order_filled", "Order Filled"),
        ("position_closed", "Position Closed"),
        ("stop_loss_hit", "Stop Loss Hit"),
        ("low_balance", "Low Balance Warning"),
    ]
    
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="notification_settings"
    )
    notification_type = models.CharField(
        max_length=30,
        choices=NOTIFICATION_TYPES
    )
    
    # Channels
    email_enabled = models.BooleanField(default=True)
    telegram_enabled = models.BooleanField(default=False)
    push_enabled = models.BooleanField(default=False)
    
    # Thresholds
    min_profit_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Only notify if profit % is above this"
    )
    
    class Meta:
        unique_together = ["user", "notification_type"]
        verbose_name = "Notification Setting"
        verbose_name_plural = "Notification Settings"
    
    def __str__(self):
        return f"{self.user.username} - {self.notification_type}"