from django.contrib import admin
from accounts.models import UserProfile, NotificationSetting

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'phone', 'default_exchange', 'timezone']
    list_filter = ['default_exchange', 'enable_email_alerts', 'enable_telegram_alerts']
    search_fields = ['user__username', 'user__email', 'phone', 'telegram_id']

@admin.register(NotificationSetting)
class NotificationSettingAdmin(admin.ModelAdmin):
    list_display = ['user', 'notification_type', 'email_enabled', 'telegram_enabled']
    list_filter = ['notification_type', 'email_enabled', 'telegram_enabled']
    search_fields = ['user__username']