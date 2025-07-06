from django.contrib import admin
from trading.models import Order, Trade, TradingStrategy, Position, TradingAlert

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ['user', 'exchange', 'trading_pair', 'side', 'order_type', 'status', 'amount', 'price']
    list_filter = ['exchange', 'status', 'side', 'order_type']
    search_fields = ['user__username', 'exchange_order_id']
    ordering = ['-created_at']

@admin.register(Trade)
class TradeAdmin(admin.ModelAdmin):
    list_display = ['order', 'price', 'amount', 'fee', 'executed_at']
    ordering = ['-executed_at']

@admin.register(TradingStrategy)
class TradingStrategyAdmin(admin.ModelAdmin):
    list_display = ['user', 'name', 'strategy_type', 'is_active', 'total_trades', 'total_profit']
    list_filter = ['strategy_type', 'is_active']
    search_fields = ['user__username', 'name']

@admin.register(Position)
class PositionAdmin(admin.ModelAdmin):
    list_display = ['user', 'exchange', 'trading_pair', 'side', 'status', 'amount', 'unrealized_pnl']
    list_filter = ['exchange', 'status', 'side']
    search_fields = ['user__username']
    ordering = ['-opened_at']

@admin.register(TradingAlert)
class TradingAlertAdmin(admin.ModelAdmin):
    list_display = ['user', 'alert_type', 'title', 'is_read', 'created_at']
    list_filter = ['alert_type', 'is_read']
    search_fields = ['user__username', 'title']
    ordering = ['-created_at']