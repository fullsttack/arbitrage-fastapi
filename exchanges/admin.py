from django.contrib import admin
from django.utils.html import format_html
from django.utils import timezone
from datetime import timedelta

from unfold.admin import ModelAdmin, TabularInline
from unfold.decorators import display, action

from exchanges.models import (
    MarketTicker, OrderBook, ExchangeBalance, 
    ExchangeStatus
)
from core.models import ExchangeTradingPair


class MarketTickerInline(TabularInline):
    """Inline for market tickers."""
    model = MarketTicker
    extra = 0
    readonly_fields = ['timestamp', 'last_price', 'volume_24h']
    fields = ['timestamp', 'last_price', 'bid_price', 'ask_price', 'volume_24h']


@admin.register(MarketTicker)
class MarketTickerAdmin(ModelAdmin):
    """Real-time market data monitoring."""
    
    list_display = [
        'pair_display', 'exchange_display', 'price_info',
        'spread_display', 'volume_info', 'timestamp_display'
    ]
    list_filter = [
        'exchange_pair__exchange',
        'exchange_pair__trading_pair',
        ('timestamp', admin.DateFieldListFilter)
    ]
    search_fields = [
        'exchange_pair__trading_pair__symbol',
        'exchange_pair__exchange__name'
    ]
    readonly_fields = ['timestamp']
    
    # Unfold settings
    list_fullwidth = True
    list_per_page = 100
    
    date_hierarchy = 'timestamp'
    ordering = ['-timestamp']
    
    @display(description="Trading Pair")
    def pair_display(self, obj):
        return format_html(
            '<span class="font-mono font-bold text-indigo-800">{}</span>',
            obj.exchange_pair.trading_pair.symbol
        )
    
    @display(description="Exchange")
    def exchange_display(self, obj):
        return obj.exchange_pair.exchange.name
    
    @display(description="Price Info")
    def price_info(self, obj):
        spread = obj.ask_price - obj.bid_price if obj.ask_price and obj.bid_price else 0
        spread_pct = (spread / obj.last_price * 100) if obj.last_price else 0
        
        return format_html(
            '<div class="text-sm">'
            '<div class="font-bold font-mono">${:.4f}</div>'
            '<div class="text-xs text-gray-500">Spread: {:.2f}%</div>'
            '</div>',
            obj.last_price, spread_pct
        )
    
    @display(description="Bid/Ask Spread")
    def spread_display(self, obj):
        if obj.bid_price and obj.ask_price:
            spread = obj.ask_price - obj.bid_price
            spread_pct = (spread / obj.last_price * 100) if obj.last_price else 0
            
            return format_html(
                '<div class="text-sm">'
                '<div class="font-mono">${:.4f}</div>'
                '<div class="text-xs text-gray-500">{:.2f}%</div>'
                '</div>',
                spread, spread_pct
            )
        return '-'
    
    @display(description="Volume")
    def volume_info(self, obj):
        if obj.volume_24h:
            return format_html(
                '<span class="font-mono text-sm">{:,.0f}</span>',
                obj.volume_24h
            )
        return '-'
    
    @display(description="Time", ordering="timestamp")
    def timestamp_display(self, obj):
        return obj.timestamp.strftime('%H:%M:%S')


@admin.register(ExchangeStatus)
class ExchangeStatusAdmin(ModelAdmin):
    """Exchange health monitoring."""
    
    list_display = [
        'exchange_name', 'status_indicator', 'response_time_display',
        'error_rate', 'uptime_display', 'last_check_display'
    ]
    list_filter = ['is_online', 'exchange']
    search_fields = ['exchange__name']
    readonly_fields = ['last_check']
    
    # Unfold settings
    list_fullwidth = True
    
    @display(description="Exchange")
    def exchange_name(self, obj):
        return obj.exchange.name
    
    @display(description="Status", label=True)
    def status_indicator(self, obj):
        if obj.is_online:
            return format_html(
                '<span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">'
                '<span class="w-2 h-2 bg-green-600 rounded-full mr-1"></span>Online</span>'
            )
        else:
            return format_html(
                '<span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-red-100 text-red-800">'
                '<span class="w-2 h-2 bg-red-600 rounded-full mr-1"></span>Offline</span>'
            )
    
    @display(description="Response Time", ordering="response_time")
    def response_time_display(self, obj):
        if obj.response_time:
            color = 'green' if obj.response_time < 0.5 else 'yellow' if obj.response_time < 1.0 else 'red'
            return format_html(
                '<span class="text-{}-600 font-mono">{:.2f}s</span>',
                color, obj.response_time
            )
        return '-'
    
    @display(description="Error Rate")
    def error_rate(self, obj):
        # Calculate error rate based on recent checks
        if obj.error_count is not None:
            rate = obj.error_count / 100  # Assuming 100 checks
            color = 'green' if rate < 0.05 else 'yellow' if rate < 0.1 else 'red'
            return format_html(
                '<span class="text-{}-600">{:.1%}</span>',
                color, rate
            )
        return '-'
    
    @display(description="Uptime")
    def uptime_display(self, obj):
        # Calculate uptime based on recent checks
        if obj.is_online:
            uptime = 0.98  # Example value
            color = 'green' if uptime > 0.98 else 'yellow' if uptime > 0.95 else 'red'
            return format_html(
                '<div class="flex items-center">'
                '<div class="w-16 bg-gray-200 rounded-full h-2 mr-2">'
                '<div class="bg-{}-600 h-2 rounded-full" style="width: {}%"></div>'
                '</div>'
                '<span class="text-{}-800">{:.1%}</span>'
                '</div>',
                color, uptime * 100, color, uptime
            )
        return format_html(
            '<span class="text-red-600">Down</span>'
        )
    
    @display(description="Last Check", ordering="last_check")
    def last_check_display(self, obj):
        if obj.last_check:
            return obj.last_check.strftime('%H:%M:%S')
        return '-'


@admin.register(ExchangeBalance)
class ExchangeBalanceAdmin(ModelAdmin):
    """User balance monitoring across exchanges."""
    
    list_display = [
        'user_display', 'exchange_display', 'currency_display',
        'balance_display', 'value_display', 'last_updated'
    ]
    list_filter = ['exchange', 'currency', 'user']
    search_fields = ['user__username', 'exchange__name', 'currency__symbol']
    readonly_fields = ['last_updated']
    
    # Unfold settings
    list_fullwidth = True
    
    @display(description="User")
    def user_display(self, obj):
        return obj.user.username
    
    @display(description="Exchange")
    def exchange_display(self, obj):
        return obj.exchange.name
    
    @display(description="Currency")
    def currency_display(self, obj):
        return format_html(
            '<span class="font-mono font-medium">{}</span>',
            obj.currency.symbol
        )
    
    @display(description="Balance")
    def balance_display(self, obj):
        if obj.total > 0:
            return format_html(
                '<div class="text-sm font-mono">'
                '<div>{:.8f}</div>'
                '<div class="text-xs text-gray-500">Available: {:.8f}</div>'
                '</div>',
                obj.total, obj.available
            )
        return format_html(
            '<span class="text-gray-400">No balance</span>'
        )
    
    @display(description="USD Value")
    def value_display(self, obj):
        # This would require price lookup
        return '-'
    
    @display(description="Updated", ordering="last_updated")
    def last_updated(self, obj):
        return obj.last_updated.strftime('%H:%M:%S')