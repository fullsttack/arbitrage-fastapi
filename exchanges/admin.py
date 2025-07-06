from django.contrib import admin
from exchanges.models import MarketTicker, OrderBook, OrderBookEntry, ExchangeBalance, ExchangeStatus

@admin.register(MarketTicker)
class MarketTickerAdmin(admin.ModelAdmin):
    list_display = ['exchange_pair', 'last_price', 'volume_24h', 'timestamp']
    list_filter = ['exchange_pair__exchange', 'timestamp']
    ordering = ['-timestamp']

@admin.register(OrderBook)
class OrderBookAdmin(admin.ModelAdmin):
    list_display = ['exchange_pair', 'timestamp']
    list_filter = ['exchange_pair__exchange', 'timestamp']
    ordering = ['-timestamp']

@admin.register(ExchangeBalance)
class ExchangeBalanceAdmin(admin.ModelAdmin):
    list_display = ['user', 'exchange', 'currency', 'total', 'available', 'locked']
    list_filter = ['exchange', 'currency']
    search_fields = ['user__username']

@admin.register(ExchangeStatus)
class ExchangeStatusAdmin(admin.ModelAdmin):
    list_display = ['exchange', 'is_online', 'last_check', 'response_time', 'error_count']
    list_filter = ['is_online']