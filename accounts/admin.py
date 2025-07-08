from django.contrib import admin
from django.utils.html import format_html

from unfold.admin import ModelAdmin, TabularInline
from unfold.decorators import display

from accounts.models import UserProfile, NotificationSetting


class NotificationSettingInline(TabularInline):
    """Inline for notification settings."""
    
    model = NotificationSetting
    extra = 0
    fields = ['notification_type', 'email_enabled', 'telegram_enabled', 'sms_enabled']


@admin.register(UserProfile)
class UserProfileAdmin(ModelAdmin):
    """Enhanced user profile management."""
    
    list_display = [
        'user', 'contact_info', 'trading_preferences', 
        'notification_status', 'timezone', 'created_at'
    ]
    list_filter = ['default_exchange', 'timezone', 'enable_email_alerts', 'enable_telegram_alerts']
    search_fields = ['user__username', 'user__email', 'phone', 'telegram_id']
    
    # Unfold settings
    list_fullwidth = True
    warn_unsaved_form = True
    
    fieldsets = [
        ("User", {"fields": ['user', 'phone', 'telegram_id']}),
        ("Preferences", {"fields": ['default_exchange', 'timezone', 'enable_email_alerts', 'enable_telegram_alerts']}),
        ("Meta", {"fields": ['created_at']}),
    ]
    readonly_fields = ['created_at']
    
    @display(description="Contact Information")
    def contact_info(self, obj):
        return format_html(
            '<div class="text-sm">'
            '<div><strong>Email:</strong> {}</div>'
            '<div><strong>Phone:</strong> {}</div>'
            '<div><strong>Telegram:</strong> {}</div>'
            '</div>',
            obj.user.email or "Not provided",
            obj.phone or "Not provided",
            obj.telegram_id or "Not provided"
        )
    
    @display(description="Trading Preferences")
    def trading_preferences(self, obj):
        return format_html(
            '<div class="text-sm">'
            '<div><strong>Exchange:</strong> {}</div>'
            '<div><strong>Currency:</strong> {}</div>'
            '<div><strong>Risk:</strong> {}</div>'
            '</div>',
            obj.default_exchange.name if obj.default_exchange else "None",
            obj.preferred_quote_currency.symbol if obj.preferred_quote_currency else "None",
            obj.get_risk_tolerance_display() if obj.risk_tolerance else "Not set"
        )
    
    @display(description="Notifications")
    def notification_status(self, obj):
        alerts = []
        if obj.enable_email_alerts:
            alerts.append('<span class="bg-blue-100 text-blue-800 px-1 py-0.5 rounded text-xs">Email</span>')
        if obj.enable_telegram_alerts:
            alerts.append('<span class="bg-green-100 text-green-800 px-1 py-0.5 rounded text-xs">Telegram</span>')
        if obj.enable_sms_alerts:
            alerts.append('<span class="bg-purple-100 text-purple-800 px-1 py-0.5 rounded text-xs">SMS</span>')
        
        if alerts:
            return format_html(' '.join(alerts))
        return format_html('<span class="text-gray-500 text-xs">Disabled</span>')


@admin.register(NotificationSetting)
class NotificationSettingAdmin(ModelAdmin):
    """Detailed notification preference management."""
    
    list_display = [
        'user', 'notification_type_display', 'channels_enabled',
        'frequency_display', 'is_active_display'
    ]
    list_filter = ['notification_type', 'email_enabled', 'telegram_enabled']
    search_fields = ['user__username', 'user__email']
    
    # Unfold settings
    list_fullwidth = True
    compressed_fields = True
    
    @display(description="Notification Type", label=True)
    def notification_type_display(self, obj):
        type_colors = {
            'arbitrage_opportunity': 'blue',
            'execution_completed': 'green',
            'execution_failed': 'red',
            'system_alert': 'orange',
            'price_alert': 'purple',
            'balance_update': 'yellow',
        }
        
        color = type_colors.get(obj.notification_type, 'gray')
        
        return format_html(
            '<span class="bg-{}-100 text-{}-800 px-2 py-1 rounded-full text-xs font-medium">{}</span>',
            color, color, obj.get_notification_type_display()
        )
    
    @display(description="Enabled Channels")
    def channels_enabled(self, obj):
        channels = []
        if obj.email_enabled:
            channels.append('<span class="bg-blue-100 text-blue-800 px-1 py-0.5 rounded text-xs">Email</span>')
        if obj.telegram_enabled:
            channels.append('<span class="bg-green-100 text-green-800 px-1 py-0.5 rounded text-xs">Telegram</span>')
        if obj.sms_enabled:
            channels.append('<span class="bg-purple-100 text-purple-800 px-1 py-0.5 rounded text-xs">SMS</span>')
        
        return format_html(' '.join(channels)) if channels else "None"
    
    @display(description="Frequency", label=True)
    def frequency_display(self, obj):
        frequency_colors = {
            'immediate': 'red',
            'hourly': 'orange',
            'daily': 'yellow',
            'weekly': 'blue',
        }
        
        color = frequency_colors.get(obj.frequency, 'gray')
        
        return format_html(
            '<span class="bg-{}-100 text-{}-800 px-2 py-1 rounded-full text-xs font-medium">{}</span>',
            color, color, obj.get_frequency_display()
        )
    
    @display(description="Active", boolean=True)
    def is_active_display(self, obj):
        return obj.email_enabled or obj.telegram_enabled or obj.sms_enabled
