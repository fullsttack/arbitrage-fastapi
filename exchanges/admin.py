from django.contrib import admin
from django.utils.html import format_html
from django.utils import timezone
from datetime import timedelta

from unfold.admin import ModelAdmin, TabularInline
from unfold.decorators import display

from exchanges.models import ExchangeStatus, MarketTicker, OrderBook, ExchangeBalance


@admin.register(ExchangeStatus)
class ExchangeStatusAdmin(ModelAdmin):
    """Real-time exchange status monitoring."""
    
    list_display = [
        'exchange', 'status_indicator', 'response_time_display',
        'error_count', 'last_check', 'uptime_percentage'
    ]
    list_filter = ['is_online', 'exchange', 'last_check']
    search_fields = ['exchange__name']
    readonly_fields = ['last_check', 'error_count', 'last_error', 'last_error_time']
    
    # Unfold settings
    list_fullwidth = True
    compressed_fields = True
    
    # Auto-refresh every 30 seconds
    change_list_template = 'admin/exchanges/exchangestatus/change_list.html'
    
    @display(description="Status", label=True)
    def status_indicator(self, obj):
        if obj.is_online:
            return format_html(
                '<span class="bg-green-100 text-green-800 px-3 py-1 rounded-full text-sm font-medium flex items-center w-fit">'
                '<span class="w-2 h-2 bg-green-600 rounded-full mr-2 animate-pulse"></span>Online</span>'
            )
        else:
            return format_html(
                '<span class="bg-red-100 text-red-800 px-3 py-1 rounded-full text-sm font-medium flex items-center w-fit">'
                '<span class="w-2 h-2 bg-red-600 rounded-full mr-2"></span>Offline</span>'
            )
    
    @display(description="Response Time", ordering="response_time")
    def response_time_display(self, obj):
        if obj.response_time is None:
            return "N/A"
        
        time_ms = obj.response_time * 1000
        if time_ms < 100:
            color = "green"
        elif time_ms < 500:
            color = "yellow"
        else:
            color = "red"
        
        return format_html(
            '<span class="text-{}-800 font-mono">{:.0f}ms</span>',
            color, time_ms
        )
    
    @display(description="Uptime %")
    def uptime_percentage(self, obj):
        # Calculate uptime for last 24 hours
        if obj.last_check:
            return "99.5%"  # Placeholder - implement actual calculation
        return "N/A"


@admin.register(MarketTicker)
class MarketTickerAdmin(ModelAdmin):
    """Market data monitoring with real-time updates."""
    
    list_display = [
        'exchange_trading_pair', 'last_price_display', 'spread_display',
        'volume_24h_display', 'change_24h_display', 'timestamp'
    ]
    list_filter = ['exchange_trading_pair__exchange', 'timestamp']
    search_fields = [
        'exchange_trading_pair__trading_pair__symbol',
        'exchange_trading_pair__exchange__name'
    ]
    readonly_fields = ['timestamp']
    
    # Unfold settings
    list_fullwidth = True
    compressed_fields = True
    list_per_page = 50
    
    @display(description="Last Price", ordering="last_price")
    def last_price_display(self, obj):
        return format_html(
            '<span class="font-mono text-lg">${:,.4f}</span>',
            obj.last_price
        )
    
    @display(description="Spread", ordering="bid_price")
    def spread_display(self, obj):
        if obj.ask_price and obj.bid_price:
            spread = ((obj.ask_price - obj.bid_price) / obj.ask_price) * 100
            return format_html(
                '<span class="font-mono">{:.2f}%</span>',
                spread
            )
        return "N/A"
    
    @display(description="24h Volume", ordering="volume_24h")
    def volume_24h_display(self, obj):
        if obj.volume_24h:
            return format_html(
                '<span class="font-mono">{:,.0f}</span>',
                obj.volume_24h
            )
        return "N/A"
    
    @display(description="24h Change", ordering="change_24h")
    def change_24h_display(self, obj):
        if obj.change_24h is not None:
            color = "green" if obj.change_24h >= 0 else "red"
            icon = "↗" if obj.change_24h >= 0 else "↘"
            return format_html(
                '<span class="text-{}-800 font-medium">{} {:.2f}%</span>',
                color, icon, obj.change_24h
            )
        return "N/A"


@admin.register(OrderBook)
class OrderBookAdmin(ModelAdmin):
    """Order book depth analysis."""
    
    list_display = [
        'exchange_trading_pair', 'depth_analysis', 'best_bid_display',
        'best_ask_display', 'timestamp'
    ]
    list_filter = ['exchange_trading_pair__exchange', 'timestamp']
    readonly_fields = ['timestamp']
    
    # Unfold settings
    list_fullwidth = True
    list_per_page = 30
    
    @display(description="Depth Analysis")
    def depth_analysis(self, obj):
        if obj.bids and obj.asks:
            bid_depth = sum(float(bid[1]) for bid in obj.bids[:10])  # Top 10 bids
            ask_depth = sum(float(ask[1]) for ask in obj.asks[:10])  # Top 10 asks
            
            return format_html(
                '<div class="text-xs">'
                '<div>Bid Depth: <span class="font-mono">{:,.0f}</span></div>'
                '<div>Ask Depth: <span class="font-mono">{:,.0f}</span></div>'
                '</div>',
                bid_depth, ask_depth
            )
        return "No data"
    
    @display(description="Best Bid")
    def best_bid_display(self, obj):
        if obj.bids:
            price, volume = obj.bids[0]
            return format_html(
                '<div class="font-mono text-sm">'
                '<div class="text-green-800">${:.4f}</div>'
                '<div class="text-gray-600">{:.2f}</div>'
                '</div>',
                float(price), float(volume)
            )
        return "N/A"
    
    @display(description="Best Ask")
    def best_ask_display(self, obj):
        if obj.asks:
            price, volume = obj.asks[0]
            return format_html(
                '<div class="font-mono text-sm">'
                '<div class="text-red-800">${:.4f}</div>'
                '<div class="text-gray-600">{:.2f}</div>'
                '</div>',
                float(price), float(volume)
            )
        return "N/A"


@admin.register(ExchangeBalance)
class ExchangeBalanceAdmin(ModelAdmin):
    """Account balance monitoring."""
    
    list_display = [
        'user', 'exchange', 'currency', 'available_display',
        'locked_display', 'total_display', 'last_updated'
    ]
    list_filter = ['exchange', 'currency', 'last_updated']
    search_fields = ['user__username', 'currency__symbol', 'exchange__name']
    readonly_fields = ['last_updated']
    
    # Unfold settings
    list_fullwidth = True
    compressed_fields = True
    
    @display(description="Available", ordering="available_balance")
    def available_display(self, obj):
        return format_html(
            '<span class="font-mono text-green-800">{:.8f}</span>',
            obj.available_balance
        )
    
    @display(description="Locked", ordering="locked_balance")
    def locked_display(self, obj):
        return format_html(
            '<span class="font-mono text-yellow-800">{:.8f}</span>',
            obj.locked_balance
        )
    
    @display(description="Total", ordering="total_balance")
    def total_display(self, obj):
        return format_html(
            '<span class="font-mono font-bold">{:.8f}</span>',
            obj.total_balance)