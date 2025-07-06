from django.contrib import admin
from arbitrage.models import ArbitrageOpportunity, ArbitrageConfig, ArbitrageExecution, ArbitrageAlert

@admin.register(ArbitrageOpportunity)
class ArbitrageOpportunityAdmin(admin.ModelAdmin):
    list_display = ['trading_pair', 'buy_exchange', 'sell_exchange', 'net_profit_percentage', 'status', 'created_at']
    list_filter = ['status', 'trading_pair', 'buy_exchange', 'sell_exchange']
    ordering = ['-created_at']

@admin.register(ArbitrageConfig)
class ArbitrageConfigAdmin(admin.ModelAdmin):
    list_display = ['user', 'is_active', 'auto_trade', 'min_profit_percentage']
    list_filter = ['is_active', 'auto_trade']
    search_fields = ['user__username']

@admin.register(ArbitrageExecution)
class ArbitrageExecutionAdmin(admin.ModelAdmin):
    list_display = ['opportunity', 'user', 'status', 'final_profit', 'created_at']
    list_filter = ['status']
    search_fields = ['user__username']
    ordering = ['-created_at']

@admin.register(ArbitrageAlert)
class ArbitrageAlertAdmin(admin.ModelAdmin):
    list_display = ['user', 'alert_type', 'title', 'is_read', 'created_at']
    list_filter = ['alert_type', 'is_read']
    search_fields = ['user__username', 'title']
    ordering = ['-created_at']