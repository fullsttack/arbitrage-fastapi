from django.contrib import admin
from django.utils.html import format_html

from unfold.admin import ModelAdmin
from unfold.decorators import display

from trading.models import Order, Position, Trade, TradingStrategy, TradingAlert


@admin.register(Order)
class OrderAdmin(ModelAdmin):
    """Comprehensive order management."""
    
    list_display = [
        'order_id_display', 'user_display', 'pair_display',
        'order_details', 'status_progress', 'execution_info', 'actions_column'
    ]
    list_filter = [
        'status', 'order_type', 'side', 'exchange',
        ('created_at', admin.DateFieldListFilter)
    ]
    search_fields = [
        'user__username', 'trading_pair__symbol',
        'exchange_order_id', 'exchange__name'
    ]
    readonly_fields = [
        'exchange_order_id', 'filled_amount', 'average_price',
        'total_fee', 'created_at', 'updated_at'
    ]
    
    # Unfold settings
    list_fullwidth = True
    warn_unsaved_form = True
    
    @display(description="Order ID")
    def order_id_display(self, obj):
        return format_html(
            '<div class="font-mono text-sm">'
            '<div class="font-bold">#{}</div>'
            '<div class="text-xs text-gray-500">{}</div>'
            '</div>',
            str(obj.id)[:8], obj.created_at.strftime('%m/%d %H:%M')
        )
    
    @display(description="User")
    def user_display(self, obj):
        return obj.user.username
    
    @display(description="Pair")
    def pair_display(self, obj):
        return format_html(
            '<span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-indigo-100 text-indigo-800 font-mono">{}</span>',
            obj.trading_pair.symbol
        )
    
    @display(description="Order Details")
    def order_details(self, obj):
        side_color = 'green' if obj.side == 'BUY' else 'red'
        
        return format_html(
            '<div class="text-sm">'
            '<div class="flex items-center space-x-2">'
            '<span class="inline-flex items-center px-2 py-1 rounded text-xs font-medium bg-{}-100 text-{}-800">{}</span>'
            '<span class="text-gray-500">{}</span>'
            '</div>'
            '<div class="font-mono text-xs mt-1">'
            '<div>Amount: {:.6f}</div>'
            '<div>Price: ${:.4f}</div>'
            '</div>'
            '</div>',
            side_color, side_color, obj.side,
            obj.order_type,
            obj.amount, obj.price
        )
    
    @display(description="Status & Progress")
    def status_progress(self, obj):
        status_colors = {
            'PENDING': 'yellow',
            'PLACED': 'blue',
            'PARTIALLY_FILLED': 'orange',
            'FILLED': 'green',
            'CANCELLED': 'gray',
            'FAILED': 'red'
        }
        
        color = status_colors.get(obj.status, 'gray')
        fill_percentage = (obj.filled_amount / obj.amount * 100) if obj.amount else 0
        
        return format_html(
            '<div>'
            '<span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-{}-100 text-{}-800 mb-1">{}</span>'
            '<div class="w-full bg-gray-200 rounded-full h-1.5">'
            '<div class="bg-{}-600 h-1.5 rounded-full" style="width: {:.0f}%"></div>'
            '</div>'
            '<div class="text-xs text-gray-500 mt-1">{:.1f}% filled</div>'
            '</div>',
            color, color, obj.get_status_display(),
            color, fill_percentage, fill_percentage
        )
    
    @display(description="Execution Info")
    def execution_info(self, obj):
        if obj.filled_amount > 0:
            return format_html(
                '<div class="text-sm font-mono">'
                '<div>Filled: {:.6f}</div>'
                '<div>Avg Price: ${:.4f}</div>'
                '<div>Fee: ${:.4f}</div>'
                '</div>',
                obj.filled_amount,
                obj.average_price or 0,
                obj.total_fee
            )
        return '-'
    
    @display(description="Actions")
    def actions_column(self, obj):
        if obj.status in ['PENDING', 'PLACED', 'PARTIALLY_FILLED']:
            return format_html(
                '<a href="#" onclick="cancelOrder(\'{}\')" class="text-red-600 hover:text-red-800 text-sm">Cancel</a>',
                obj.id
            )
        return '-'


@admin.register(TradingStrategy)
class TradingStrategyAdmin(ModelAdmin):
    """Trading strategy management."""
    
    list_display = [
        'strategy_name', 'user_display', 'strategy_type_display',
        'performance_metrics', 'status_indicator', 'actions_column'
    ]
    list_filter = ['strategy_type', 'is_active', 'user']
    search_fields = ['name', 'user__username']
    
    # Unfold settings
    list_fullwidth = True
    warn_unsaved_form = True
    
    @display(description="Strategy")
    def strategy_name(self, obj):
        return format_html(
            '<div>'
            '<div class="font-medium">{}</div>'
            '<div class="text-xs text-gray-500">{}</div>'
            '</div>',
            obj.name, obj.created_at.strftime('%m/%d/%Y')
        )
    
    @display(description="User")
    def user_display(self, obj):
        return obj.user.username
    
    @display(description="Type", label=True)
    def strategy_type_display(self, obj):
        type_colors = {
            'arbitrage': 'purple',
            'market_making': 'blue',
            'momentum': 'green',
            'mean_reversion': 'orange'
        }
        
        color = type_colors.get(obj.strategy_type, 'gray')
        
        return format_html(
            '<span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-{}-100 text-{}-800">{}</span>',
            color, color, obj.strategy_type.replace('_', ' ').title()
        )
    
    @display(description="Performance")
    def performance_metrics(self, obj):
        # These would come from actual performance calculations
        return format_html(
            '<div class="text-sm">'
            '<div class="text-green-600 font-medium">+12.3%</div>'
            '<div class="text-xs text-gray-500">30d return</div>'
            '</div>'
        )
    
    @display(description="Status", boolean=True)
    def status_indicator(self, obj):
        return obj.is_active
    
    @display(description="Actions")
    def actions_column(self, obj):
        if obj.is_active:
            return format_html(
                '<a href="#" onclick="pauseStrategy(\'{}\')" class="text-yellow-600 hover:text-yellow-800 text-sm">Pause</a>',
                obj.id
            )
        else:
            return format_html(
                '<a href="#" onclick="activateStrategy(\'{}\')" class="text-green-600 hover:text-green-800 text-sm">Activate</a>',
                obj.id
            )