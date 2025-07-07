from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from arbitrage.models import (
    ArbitrageOpportunity, 
    ArbitrageConfig, 
    ArbitrageExecution, 
    ArbitrageAlert,
    MultiExchangeArbitrageStrategy,
    MultiExchangeExecution
)


@admin.register(ArbitrageOpportunity)
class ArbitrageOpportunityAdmin(admin.ModelAdmin):
    list_display = [
        'trading_pair', 'buy_exchange', 'sell_exchange', 
        'formatted_profit', 'status', 'optimal_amount', 
        'created_at', 'expires_at'
    ]
    list_filter = [
        'status', 'trading_pair', 'buy_exchange', 'sell_exchange',
        'created_at'
    ]
    search_fields = [
        'trading_pair__symbol', 'buy_exchange__name', 
        'sell_exchange__name'
    ]
    ordering = ['-created_at']
    readonly_fields = [
        'id', 'detection_latency', 'estimated_profit', 
        'total_fees', 'created_at', 'updated_at'
    ]
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('id', 'trading_pair', 'status', 'created_at', 'updated_at')
        }),
        ('Exchange Details', {
            'fields': ('buy_exchange', 'sell_exchange', 'buy_price', 'sell_price')
        }),
        ('Amounts & Liquidity', {
            'fields': (
                'available_buy_amount', 'available_sell_amount', 
                'optimal_amount', 'executed_amount'
            )
        }),
        ('Profitability', {
            'fields': (
                'gross_profit_percentage', 'net_profit_percentage',
                'estimated_profit', 'actual_profit'
            )
        }),
        ('Fees & Costs', {
            'fields': ('buy_fee', 'sell_fee', 'total_fees')
        }),
        ('Timing', {
            'fields': ('expires_at', 'executed_at', 'detection_latency')
        }),
        ('Market Data', {
            'fields': ('market_depth',),
            'classes': ('collapse',)
        })
    )
    
    def formatted_profit(self, obj):
        if obj.net_profit_percentage:
            color = 'green' if obj.net_profit_percentage > 0 else 'red'
            return format_html(
                '<span style="color: {};">{:.2f}%</span>',
                color,
                obj.net_profit_percentage
            )
        return '-'
    formatted_profit.short_description = 'Net Profit %'
    formatted_profit.admin_order_field = 'net_profit_percentage'


@admin.register(MultiExchangeArbitrageStrategy)
class MultiExchangeArbitrageStrategyAdmin(admin.ModelAdmin):
    list_display = [
        'trading_pair', 'strategy_type', 'formatted_profit',
        'complexity_score', 'status', 'execution_progress',
        'created_at'
    ]
    list_filter = [
        'strategy_type', 'status', 'trading_pair', 'created_at',
        'complexity_score'
    ]
    search_fields = ['trading_pair__symbol']
    ordering = ['-created_at']
    readonly_fields = [
        'id', 'complexity_score', 'estimated_profit', 'total_fees',
        'created_at', 'updated_at', 'execution_link'
    ]
    
    fieldsets = (
        ('Strategy Overview', {
            'fields': (
                'id', 'trading_pair', 'strategy_type', 'status',
                'complexity_score', 'created_at', 'updated_at'
            )
        }),
        ('Buy Actions', {
            'fields': ('buy_actions', 'total_buy_amount', 'total_buy_cost')
        }),
        ('Sell Actions', {
            'fields': ('sell_actions', 'total_sell_amount', 'total_sell_revenue')
        }),
        ('Profitability Analysis', {
            'fields': (
                'estimated_profit', 'profit_percentage', 'total_fees',
                'actual_profit', 'actual_profit_percentage'
            )
        }),
        ('Risk Assessment', {
            'fields': ('risk_score', 'max_execution_time')
        }),
        ('Execution Timeline', {
            'fields': (
                'expires_at', 'execution_started_at', 
                'execution_completed_at'
            )
        }),
        ('Market Snapshot', {
            'fields': ('market_snapshot',),
            'classes': ('collapse',)
        }),
        ('Execution Details', {
            'fields': ('execution_link',)
        })
    )
    
    def formatted_profit(self, obj):
        if obj.profit_percentage:
            color = 'green' if obj.profit_percentage > 0 else 'red'
            return format_html(
                '<span style="color: {};">{:.2f}%</span>',
                color,
                obj.profit_percentage
            )
        return '-'
    formatted_profit.short_description = 'Profit %'
    formatted_profit.admin_order_field = 'profit_percentage'
    
    def execution_progress(self, obj):
        total_executions = obj.executions.count()
        completed_executions = obj.executions.filter(status='filled').count()
        failed_executions = obj.executions.filter(status='failed').count()
        
        if total_executions == 0:
            return "No executions"
        
        if obj.status == 'completed':
            color = 'green' if failed_executions == 0 else 'orange'
        elif obj.status == 'failed':
            color = 'red'
        else:
            color = 'blue'
        
        return format_html(
            '<span style="color: {};">{}/{} completed</span>',
            color,
            completed_executions,
            total_executions
        )
    execution_progress.short_description = 'Execution Progress'
    
    def execution_link(self, obj):
        if obj.pk:
            url = reverse('admin:arbitrage_multiexchangeexecution_changelist')
            return format_html(
                '<a href="{}?strategy__id__exact={}">View Executions ({})</a>',
                url,
                obj.pk,
                obj.executions.count()
            )
        return '-'
    execution_link.short_description = 'Related Executions'


@admin.register(MultiExchangeExecution)
class MultiExchangeExecutionAdmin(admin.ModelAdmin):
    list_display = [
        'strategy_link', 'exchange', 'action_type',
        'target_amount', 'filled_amount', 'fill_progress',
        'status', 'execution_time', 'created_at'
    ]
    list_filter = [
        'action_type', 'status', 'exchange', 'created_at'
    ]
    search_fields = [
        'strategy__trading_pair__symbol', 'exchange__name',
        'exchange_order_id'
    ]
    ordering = ['-created_at']
    readonly_fields = [
        'id', 'remaining_amount', 'fill_percentage', 'execution_latency',
        'fill_latency', 'price_slippage', 'created_at', 'updated_at'
    ]
    
    fieldsets = (
        ('Execution Overview', {
            'fields': (
                'id', 'strategy', 'exchange', 'action_type',
                'created_at', 'updated_at'
            )
        }),
        ('Order Details', {
            'fields': (
                'target_amount', 'target_price', 'order_type',
                'exchange_order_id'
            )
        }),
        ('Execution Results', {
            'fields': (
                'filled_amount', 'average_price', 'total_fee',
                'remaining_amount', 'fill_percentage'
            )
        }),
        ('Status & Timing', {
            'fields': (
                'status', 'order_placed_at', 'first_fill_at',
                'completed_at'
            )
        }),
        ('Performance Metrics', {
            'fields': (
                'execution_latency', 'fill_latency', 'price_slippage'
            )
        }),
        ('Error Information', {
            'fields': ('error_message', 'retry_count'),
            'classes': ('collapse',)
        })
    )
    
    def strategy_link(self, obj):
        if obj.strategy:
            url = reverse(
                'admin:arbitrage_multiexchangearbitragestrategy_change',
                args=[obj.strategy.pk]
            )
            return format_html(
                '<a href="{}">{} ({})</a>',
                url,
                obj.strategy.trading_pair.symbol,
                obj.strategy.strategy_type
            )
        return '-'
    strategy_link.short_description = 'Strategy'
    
    def fill_progress(self, obj):
        if obj.target_amount > 0:
            percentage = (obj.filled_amount / obj.target_amount) * 100
            color = 'green' if percentage == 100 else 'orange' if percentage > 0 else 'red'
            return format_html(
                '<span style="color: {};">{:.1f}%</span>',
                color,
                percentage
            )
        return '0%'
    fill_progress.short_description = 'Fill %'
    
    def execution_time(self, obj):
        if obj.order_placed_at and obj.completed_at:
            duration = obj.completed_at - obj.order_placed_at
            return f"{duration.total_seconds():.1f}s"
        return '-'
    execution_time.short_description = 'Duration'


@admin.register(ArbitrageConfig)
class ArbitrageConfigAdmin(admin.ModelAdmin):
    list_display = [
        'user', 'is_active', 'auto_trade', 'enable_multi_exchange',
        'min_profit_percentage', 'max_exchanges_per_strategy'
    ]
    list_filter = [
        'is_active', 'auto_trade', 'enable_multi_exchange',
        'allocation_strategy'
    ]
    search_fields = ['user__username', 'user__email']
    
    fieldsets = (
        ('User & Basic Settings', {
            'fields': ('user', 'is_active', 'auto_trade')
        }),
        ('Profit Thresholds', {
            'fields': (
                'min_profit_percentage', 'min_profit_amount',
                'min_profit_per_exchange'
            )
        }),
        ('Multi-Exchange Settings', {
            'fields': (
                'enable_multi_exchange', 'max_exchanges_per_strategy',
                'allocation_strategy', 'max_allocation_per_exchange'
            )
        }),
        ('Risk Management', {
            'fields': (
                'max_exposure_percentage', 'stop_loss_percentage',
                'max_slippage_tolerance', 'min_liquidity_ratio'
            )
        }),
        ('Trading Limits', {
            'fields': ('max_trade_amount', 'daily_trade_limit')
        }),
        ('Execution Settings', {
            'fields': (
                'use_market_orders', 'slippage_tolerance',
                'require_simultaneous_execution', 'max_execution_time',
                'order_timeout'
            )
        }),
        ('Advanced Features', {
            'fields': ('enable_triangular_arbitrage', 'exchange_reliability_weights'),
            'classes': ('collapse',)
        }),
        ('Notifications', {
            'fields': (
                'enable_notifications', 'notification_channels',
                'notify_on_high_profit'
            )
        }),
        ('Exchange & Pair Filters', {
            'fields': ('enabled_exchanges', 'enabled_pairs')
        })
    )
    
    filter_horizontal = ('enabled_exchanges', 'enabled_pairs')


@admin.register(ArbitrageExecution)
class ArbitrageExecutionAdmin(admin.ModelAdmin):
    list_display = [
        'opportunity_link', 'user', 'status', 'formatted_profit',
        'execution_duration', 'created_at'
    ]
    list_filter = ['status', 'user', 'created_at']
    search_fields = [
        'user__username', 'opportunity__trading_pair__symbol',
        'buy_order_id', 'sell_order_id'
    ]
    ordering = ['-created_at']
    readonly_fields = [
        'id', 'final_profit', 'profit_percentage',
        'created_at', 'updated_at'
    ]
    
    fieldsets = (
        ('Execution Overview', {
            'fields': (
                'id', 'opportunity', 'user', 'multi_strategy',
                'status', 'created_at', 'updated_at'
            )
        }),
        ('Buy Order', {
            'fields': (
                'buy_order_id', 'buy_order_status', 'buy_filled_amount',
                'buy_average_price', 'buy_fee_paid', 'buy_order_placed_at',
                'buy_order_filled_at'
            )
        }),
        ('Sell Order', {
            'fields': (
                'sell_order_id', 'sell_order_status', 'sell_filled_amount',
                'sell_average_price', 'sell_fee_paid', 'sell_order_placed_at',
                'sell_order_filled_at'
            )
        }),
        ('Results', {
            'fields': ('final_profit', 'profit_percentage', 'completed_at')
        }),
        ('Error Information', {
            'fields': ('error_message', 'retry_count'),
            'classes': ('collapse',)
        })
    )
    
    def opportunity_link(self, obj):
        if obj.opportunity:
            url = reverse(
                'admin:arbitrage_arbitrageopportunity_change',
                args=[obj.opportunity.pk]
            )
            return format_html(
                '<a href="{}">{}</a>',
                url,
                obj.opportunity.trading_pair.symbol
            )
        return '-'
    opportunity_link.short_description = 'Opportunity'
    
    def formatted_profit(self, obj):
        if obj.final_profit:
            color = 'green' if obj.final_profit > 0 else 'red'
            return format_html(
                '<span style="color: {};">{:.4f}</span>',
                color,
                obj.final_profit
            )
        return '-'
    formatted_profit.short_description = 'Final Profit'
    formatted_profit.admin_order_field = 'final_profit'
    
    def execution_duration(self, obj):
        if obj.buy_order_placed_at and obj.completed_at:
            duration = obj.completed_at - obj.buy_order_placed_at
            return f"{duration.total_seconds():.1f}s"
        return '-'
    execution_duration.short_description = 'Duration'


@admin.register(ArbitrageAlert)
class ArbitrageAlertAdmin(admin.ModelAdmin):
    list_display = [
        'user', 'alert_type', 'title', 'is_read',
        'opportunity_link', 'strategy_link', 'created_at'
    ]
    list_filter = [
        'alert_type', 'is_read', 'created_at'
    ]
    search_fields = [
        'user__username', 'title', 'message'
    ]
    ordering = ['-created_at']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Alert Information', {
            'fields': (
                'user', 'alert_type', 'title', 'message',
                'is_read', 'created_at', 'updated_at'
            )
        }),
        ('Related Objects', {
            'fields': ('opportunity', 'multi_strategy')
        }),
        ('Delivery', {
            'fields': ('sent_via', 'metadata')
        })
    )
    
    def opportunity_link(self, obj):
        if obj.opportunity:
            url = reverse(
                'admin:arbitrage_arbitrageopportunity_change',
                args=[obj.opportunity.pk]
            )
            return format_html(
                '<a href="{}">{}</a>',
                url,
                obj.opportunity.trading_pair.symbol
            )
        return '-'
    opportunity_link.short_description = 'Opportunity'
    
    def strategy_link(self, obj):
        if obj.multi_strategy:
            url = reverse(
                'admin:arbitrage_multiexchangearbitragestrategy_change',
                args=[obj.multi_strategy.pk]
            )
            return format_html(
                '<a href="{}">{}</a>',
                url,
                f"{obj.multi_strategy.trading_pair.symbol} ({obj.multi_strategy.strategy_type})"
            )
        return '-'
    strategy_link.short_description = 'Strategy'
    
    actions = ['mark_as_read', 'mark_as_unread']
    
    def mark_as_read(self, request, queryset):
        updated = queryset.update(is_read=True)
        self.message_user(
            request,
            f"{updated} alerts marked as read."
        )
    mark_as_read.short_description = "Mark selected alerts as read"
    
    def mark_as_unread(self, request, queryset):
        updated = queryset.update(is_read=False)
        self.message_user(
            request,
            f"{updated} alerts marked as unread."
        )
    mark_as_unread.short_description = "Mark selected alerts as unread"


# Custom admin views for analytics
class ArbitrageAnalyticsAdmin(admin.ModelAdmin):
    """Base class for arbitrage analytics views"""
    
    def has_add_permission(self, request):
        return False
    
    def has_delete_permission(self, request, obj=None):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False


# Add custom admin site configurations
admin.site.site_header = "Crypto Arbitrage Administration"
admin.site.site_title = "Arbitrage Admin"
admin.site.index_title = "Welcome to Crypto Arbitrage Administration"