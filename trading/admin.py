from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.contrib.admin import action

from unfold.admin import ModelAdmin, TabularInline
from unfold.decorators import display

from trading.models import Order, Trade, Position, TradingStrategy, TradingAlert


class TradeInline(TabularInline):
    """Inline for related trades."""
    
    model = Trade
    extra = 0
    readonly_fields = ['fee']
    fields = ['fee']


@admin.register(Order)
class OrderAdmin(ModelAdmin):
    """Enhanced order management."""
    
    list_display = [
        'order_info', 'side_indicator', 'amount_display', 
        'price_display', 'status_indicator', 'progress_bar', 'created_at'
    ]
    list_filter = ['side', 'order_type', 'status', 'exchange', 'created_at']
    search_fields = ['exchange_order_id', 'trading_pair__symbol', 'user__username']
    readonly_fields = ['exchange_order_id', 'created_at', 'updated_at']
    inlines = [TradeInline]
    
    # Unfold settings
    list_fullwidth = True
    compressed_fields = True
    
    @display(description="Order Details")
    def order_info(self, obj):
        return format_html(
            '<div>'
            '<div class="font-medium">{}</div>'
            '<div class="text-sm text-gray-600">{} on {}</div>'
            '</div>',
            obj.trading_pair.symbol,
            obj.get_order_type_display(),
            obj.exchange.name
        )
    
    @display(description="Side", label=True)
    def side_indicator(self, obj):
        if obj.side == 'buy':
            return format_html(
                '<span class="bg-green-100 text-green-800 px-2 py-1 rounded-full text-xs font-medium">BUY</span>'
            )
        else:
            return format_html(
                '<span class="bg-red-100 text-red-800 px-2 py-1 rounded-full text-xs font-medium">SELL</span>'
            )
    
    @display(description="Amount", ordering="amount")
    def amount_display(self, obj):
        return format_html(
            '<span class="font-mono">{:.6f}</span>',
            obj.amount
        )
    
    @display(description="Price", ordering="price")
    def price_display(self, obj):
        if obj.price:
            return format_html(
                '<span class="font-mono">${:.4f}</span>',
                obj.price
            )
        return "Market"
    
    @display(description="Status", label=True)
    def status_indicator(self, obj):
        status_colors = {
            'pending': 'yellow',
            'partially_filled': 'blue',
            'filled': 'green',
            'cancelled': 'gray',
            'rejected': 'red',
        }
        
        color = status_colors.get(obj.status, 'gray')
        
        return format_html(
            '<span class="bg-{}-100 text-{}-800 px-2 py-1 rounded-full text-xs font-medium">{}</span>',
            color, color, obj.get_status_display()
        )
    
    @display(description="Progress")
    def progress_bar(self, obj):
        if obj.filled_amount and obj.amount:
            percentage = (obj.filled_amount / obj.amount) * 100
            return format_html(
                '<div class="w-20 bg-gray-200 rounded-full h-2">'
                '<div class="bg-blue-600 h-2 rounded-full" style="width: {:.0f}%"></div>'
                '</div>'
                '<span class="text-xs ml-2">{:.0f}%</span>',
                percentage, percentage
            )
        return "0%"


@admin.register(Trade)
class TradeAdmin(ModelAdmin):
    """Trade execution tracking."""
    
    list_display = [
        'trade_info', 'side_indicator', 'fee_display'
    ]
    list_filter = ['order__side', 'order__exchange']
    search_fields = ['order__trading_pair__symbol', 'trade_id']
    readonly_fields = ['metadata']
    
    # Unfold settings
    list_fullwidth = True
    compressed_fields = True
    
    @display(description="Trade Details")
    def trade_info(self, obj):
        return format_html(
            '<div>'
            '<div class="font-medium">{}</div>'
            '<div class="text-sm text-gray-600">Order #{}</div>'
            '</div>',
            obj.order.trading_pair.symbol,
            obj.order.id
        )
    
    @display(description="Side", label=True)
    def side_indicator(self, obj):
        if obj.order.side == 'buy':
            return format_html(
                '<span class="bg-green-100 text-green-800 px-2 py-1 rounded-full text-xs font-medium">BUY</span>'
            )
        else:
            return format_html(
                '<span class="bg-red-100 text-red-800 px-2 py-1 rounded-full text-xs font-medium">SELL</span>'
            )
    
    @display(description="Fee", ordering="fee")
    def fee_display(self, obj):
        return format_html(
            '<span class="font-mono text-red-800">${:.4f}</span>',
            obj.fee or 0
        )


@admin.register(Position)
class PositionAdmin(ModelAdmin):
    """Portfolio position management."""
    
    list_display = [
        'position_info', 'side_indicator', 'size_display',
        'average_price_display', 'pnl_display', 'updated_at'
    ]
    list_filter = ['side', 'exchange', 'updated_at']
    search_fields = ['trading_pair__symbol', 'user__username']
    readonly_fields = ['unrealized_pnl', 'realized_pnl', 'updated_at']
    
    # Unfold settings
    list_fullwidth = True
    compressed_fields = True
    
    @display(description="Position")
    def position_info(self, obj):
        return format_html(
            '<div>'
            '<div class="font-medium">{}</div>'
            '<div class="text-sm text-gray-600">{}</div>'
            '</div>',
            obj.trading_pair.symbol,
            obj.exchange.name
        )
    
    @display(description="Side", label=True)
    def side_indicator(self, obj):
        if obj.side == 'long':
            return format_html(
                '<span class="bg-green-100 text-green-800 px-2 py-1 rounded-full text-xs font-medium">LONG</span>'
            )
        else:
            return format_html(
                '<span class="bg-red-100 text-red-800 px-2 py-1 rounded-full text-xs font-medium">SHORT</span>'
            )
    
    @display(description="Size", ordering="size")
    def size_display(self, obj):
        return format_html(
            '<span class="font-mono">{:.6f}</span>',
            obj.size
        )
    
    @display(description="Avg Price", ordering="average_price")
    def average_price_display(self, obj):
        return format_html(
            '<span class="font-mono">${:.4f}</span>',
            obj.average_price
        )
    
    @display(description="P&L")
    def pnl_display(self, obj):
        total_pnl = (obj.realized_pnl or 0) + (obj.unrealized_pnl or 0)
        color = "green" if total_pnl >= 0 else "red"
        icon = "↗" if total_pnl >= 0 else "↘"
        
        return format_html(
            '<div class="text-{}-800">'
            '<div class="font-bold">{} ${:.2f}</div>'
            '<div class="text-xs">R: ${:.2f} | U: ${:.2f}</div>'
            '</div>',
            color, icon, total_pnl, obj.realized_pnl or 0, obj.unrealized_pnl or 0
        )


@admin.register(TradingStrategy)
class TradingStrategyAdmin(ModelAdmin):
    """Trading strategy management."""
    
    list_display = [
        'name', 'strategy_type_display', 'is_active_display',
        'performance_summary', 'updated_at'
    ]
    list_filter = ['strategy_type', 'is_active', 'updated_at']
    search_fields = ['name', 'user__username']
    
    # Unfold settings
    list_fullwidth = True
    warn_unsaved_form = True
    
    @display(description="Type", label=True)
    def strategy_type_display(self, obj):
        type_colors = {
            'arbitrage': 'blue',
            'market_making': 'green',
            'momentum': 'purple',
            'mean_reversion': 'orange',
        }
        
        color = type_colors.get(obj.strategy_type, 'gray')
        
        return format_html(
            '<span class="bg-{}-100 text-{}-800 px-2 py-1 rounded-full text-xs font-medium">{}</span>',
            color, color, obj.get_strategy_type_display()
        )
    
    @display(description="Status", boolean=True)
    def is_active_display(self, obj):
        return obj.is_active
    
    @display(description="Performance")
    def performance_summary(self, obj):
        # This would be calculated from related trades/executions
        return format_html(
            '<div class="text-sm">'
            '<div class="text-green-800">+$1,234.56</div>'
            '<div class="text-gray-600">15 trades</div>'
            '</div>'
        )


@admin.register(TradingAlert)
class TradingAlertAdmin(ModelAdmin):
    """Trading alert management."""
    
    list_display = [
        'alert_type_display', 'message_preview', 'is_read_display',
        'priority_indicator', 'created_at'
    ]
    list_filter = ['alert_type', 'is_read', 'created_at']
    search_fields = ['message', 'order__trading_pair__symbol']
    actions = ['mark_as_read', 'mark_as_unread']
    
    # Unfold settings
    list_fullwidth = True
    list_per_page = 100
    
    @display(description="Type", label=True)
    def alert_type_display(self, obj):
        type_colors = {
            'order_filled': 'green',
            'order_cancelled': 'yellow',
            'order_rejected': 'red',
            'position_opened': 'blue',
            'position_closed': 'purple',
            'stop_loss_triggered': 'red',
        }
        
        color = type_colors.get(obj.alert_type, 'gray')
        
        return format_html(
            '<span class="bg-{}-100 text-{}-800 px-2 py-1 rounded-full text-xs font-medium">{}</span>',
            color, color, obj.get_alert_type_display()
        )
    
    @display(description="Message")
    def message_preview(self, obj):
        return format_html(
            '<div class="max-w-xs truncate">{}</div>',
            obj.message
        )
    
    @display(description="Read", boolean=True)
    def is_read_display(self, obj):
        return obj.is_read
    
    @display(description="Priority", label=True)
    def priority_indicator(self, obj):
        priority_colors = {
            'low': 'gray',
            'medium': 'yellow',
            'high': 'orange',
            'critical': 'red',
        }
        
        color = priority_colors.get(obj.priority, 'gray')
        
        return format_html(
            '<span class="bg-{}-100 text-{}-800 px-2 py-1 rounded-full text-xs font-medium">{}</span>',
            color, color, obj.priority.title()
        )
    
    @action(description="Mark selected alerts as read")
    def mark_as_read(self, request, queryset):
        updated = queryset.update(is_read=True)
        self.message_user(
            request,
            f"{updated} alerts marked as read."
        )
    
    @action(description="Mark selected alerts as unread")
    def mark_as_unread(self, request, queryset):
        updated = queryset.update(is_read=False)
        self.message_user(
            request,
            f"{updated} alerts marked as unread."
        )