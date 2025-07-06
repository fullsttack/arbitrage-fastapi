from django.contrib import admin
from analytics.models import (
    DailyArbitrageSummary, ExchangePerformance, 
    TradingPairAnalytics, UserPerformance, MarketSnapshot
)

@admin.register(DailyArbitrageSummary)
class DailyArbitrageSummaryAdmin(admin.ModelAdmin):
    list_display = ['date', 'total_opportunities', 'total_executions', 'total_profit']
    list_filter = ['date']
    ordering = ['-date']

@admin.register(ExchangePerformance)
class ExchangePerformanceAdmin(admin.ModelAdmin):
    list_display = ['exchange', 'date', 'uptime_percentage', 'total_orders_placed']
    list_filter = ['exchange', 'date']
    ordering = ['-date', 'exchange']

@admin.register(TradingPairAnalytics)
class TradingPairAnalyticsAdmin(admin.ModelAdmin):
    list_display = ['trading_pair', 'period_type', 'period_start', 'total_opportunities']
    list_filter = ['period_type', 'trading_pair']
    ordering = ['-period_start']

@admin.register(UserPerformance)
class UserPerformanceAdmin(admin.ModelAdmin):
    list_display = ['user', 'date', 'total_executions', 'net_profit']
    list_filter = ['date']
    search_fields = ['user__username']
    ordering = ['-date']

@admin.register(MarketSnapshot)
class MarketSnapshotAdmin(admin.ModelAdmin):
    list_display = ['timestamp', 'active_opportunities', 'average_spread', 'market_trend']
    list_filter = ['market_trend']
    ordering = ['-timestamp']