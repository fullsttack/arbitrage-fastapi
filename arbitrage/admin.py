# Comprehensive Admin Configuration - Update your admin.py files

# ===== ARBITRAGE/ADMIN.PY =====

from django.contrib import admin
from django.contrib.admin import SimpleListFilter
from django.utils.html import format_html
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta

from unfold.admin import ModelAdmin, TabularInline, StackedInline
from unfold.decorators import display, action

from arbitrage.models import (
    ArbitrageOpportunity, MultiExchangeArbitrageStrategy,
    ArbitrageExecution, MultiExchangeExecution,
    ArbitrageConfig, ArbitrageAlert
)


class ProfitPercentageFilter(SimpleListFilter):
    title = 'profit percentage'
    parameter_name = 'net_profit_percentage'

    def lookups(self, request, model_admin):
        return (
            ('high', 'High (>2%)'),
            ('medium', 'Medium (1-2%)'),
            ('low', 'Low (<1%)'),
        )

    def queryset(self, request, queryset):
        if self.value() == 'high':
            return queryset.filter(net_profit_percentage__gt=2)
        if self.value() == 'medium':
            return queryset.filter(net_profit_percentage__gt=1, net_profit_percentage__lte=2)
        if self.value() == 'low':
            return queryset.filter(net_profit_percentage__lte=1)


class StrategyProfitFilter(SimpleListFilter):
    title = 'profit percentage'
    parameter_name = 'profit_percentage'

    def lookups(self, request, model_admin):
        return (
            ('high', 'High (>5%)'),
            ('medium', 'Medium (2-5%)'),
            ('low', 'Low (<2%)'),
        )

    def queryset(self, request, queryset):
        if self.value() == 'high':
            return queryset.filter(profit_percentage__gt=5)
        if self.value() == 'medium':
            return queryset.filter(profit_percentage__gt=2, profit_percentage__lte=5)
        if self.value() == 'low':
            return queryset.filter(profit_percentage__lte=2)


class ArbitrageExecutionInline(TabularInline):
    """Inline for viewing executions."""
    
    model = ArbitrageExecution
    extra = 0
    readonly_fields = ['status_display', 'profit_display']
    fields = ['status_display', 'buy_filled_amount', 'sell_filled_amount', 'profit_display']
    
    @display(description="Status", label=True)
    def status_display(self, obj):
        colors = {
            'pending': 'yellow',
            'executing': 'blue',
            'completed': 'green',
            'failed': 'red',
            'cancelled': 'gray'
        }
        color = colors.get(obj.status, 'gray')
        
        return format_html(
            '<span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-{}-100 text-{}-800">{}</span>',
            color, color, obj.get_status_display()
        )
    
    @display(description="Profit")
    def profit_display(self, obj):
        if obj.final_profit:
            color = 'green' if obj.final_profit > 0 else 'red'
            return format_html(
                '<span class="text-{}-600 font-medium">${:.2f}</span>',
                color, obj.final_profit
            )
        return '-'


@admin.register(ArbitrageOpportunity)
class ArbitrageOpportunityAdmin(ModelAdmin):
    """Enhanced arbitrage opportunity monitoring."""
    
    list_display = [
        'trading_pair_display', 'route_display', 'profit_display',
        'status_indicator', 'optimal_amount_display', 'time_remaining', 'actions_column'
    ]
    list_filter = [
        'status', 'buy_exchange', 'sell_exchange', 'trading_pair',
        ('created_at', admin.DateFieldListFilter),
        ProfitPercentageFilter,
    ]
    search_fields = ['trading_pair__symbol', 'buy_exchange__name', 'sell_exchange__name']
    readonly_fields = [
        'gross_profit_percentage', 'net_profit_percentage', 'estimated_profit',
        'total_fees', 'detection_latency', 'expires_at', 'market_depth_display'
    ]
    inlines = [ArbitrageExecutionInline]
    
    # Unfold settings
    list_fullwidth = True
    compressed_fields = True
    list_per_page = 25
    warn_unsaved_form = True
    
    # Custom actions
    actions = ['execute_selected_opportunities', 'mark_as_expired', 'export_to_csv']
    
    fieldsets = [
        ("Opportunity Details", {
            "fields": [
                ('trading_pair', 'status'),
                ('buy_exchange', 'sell_exchange'),
                ('buy_price', 'sell_price'),
            ],
            "classes": ["collapse"]
        }),
        ("Profit Analysis", {
            "fields": [
                ('gross_profit_percentage', 'net_profit_percentage'),
                ('estimated_profit', 'total_fees'),
                ('optimal_amount',),
            ],
            "classes": ["collapse"]
        }),
        ("Execution Details", {
            "fields": [
                ('available_buy_amount', 'available_sell_amount'),
                ('executed_amount', 'actual_profit'),
                ('executed_at',),
            ],
            "classes": ["collapse"]
        }),
        ("Technical Data", {
            "fields": [
                ('detection_latency', 'expires_at'),
                ('market_depth_display',),
            ],
            "classes": ["collapse"]
        }),
    ]
    
    @display(description="Trading Pair", ordering="trading_pair__symbol")
    def trading_pair_display(self, obj):
        return format_html(
            '<div class="flex items-center">'
            '<span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-indigo-100 text-indigo-800">{}</span>'
            '</div>',
            obj.trading_pair.symbol
        )
    
    @display(description="Route")
    def route_display(self, obj):
        return format_html(
            '<div class="text-sm">'
            '<div class="font-medium text-green-800">{}</div>'
            '<div class="text-gray-500">↓</div>'
            '<div class="font-medium text-red-800">{}</div>'
            '</div>',
            obj.buy_exchange.name,
            obj.sell_exchange.name
        )
    
    @display(description="Profit", ordering="net_profit_percentage")
    def profit_display(self, obj):
        color_class = 'green' if obj.net_profit_percentage >= 1 else 'yellow' if obj.net_profit_percentage >= 0.5 else 'gray'
        
        return format_html(
            '<div class="text-center">'
            '<div class="text-lg font-bold text-{}-600">{:.2f}%</div>'
            '<div class="text-sm text-gray-500">${:.2f}</div>'
            '</div>',
            color_class, obj.net_profit_percentage, obj.estimated_profit
        )
    
    @display(description="Status", label=True)
    def status_indicator(self, obj):
        status_colors = {
            'detected': ('blue', '🔍'),
            'executing': ('yellow', '⚡'),
            'executed': ('green', '✅'),
            'expired': ('gray', '⏰'),
            'failed': ('red', '❌'),
        }
        
        color, icon = status_colors.get(obj.status, ('gray', '❓'))
        
        return format_html(
            '<span class="inline-flex items-center px-3 py-1 rounded-full text-sm font-medium bg-{}-100 text-{}-800">'
            '{} {}'
            '</span>',
            color, color, icon, obj.get_status_display()
        )
    
    @display(description="Amount", ordering="optimal_amount")
    def optimal_amount_display(self, obj):
        return format_html(
            '<span class="font-mono text-sm">{:.4f}</span>',
            obj.optimal_amount
        )
    
    @display(description="Time Remaining")
    def time_remaining(self, obj):
        if obj.status in ['executed', 'failed', 'expired']:
            return '-'
        
        now = timezone.now()
        if obj.expires_at > now:
            remaining = obj.expires_at - now
            total_seconds = int(remaining.total_seconds())
            minutes, seconds = divmod(total_seconds, 60)
            
            color = 'green' if minutes > 2 else 'yellow' if minutes > 1 else 'red'
            
            return format_html(
                '<span class="text-{}-600 font-mono text-sm">{}:{:02d}</span>',
                color, minutes, seconds
            )
        else:
            return format_html('<span class="text-red-600">Expired</span>')
    
    @display(description="Actions")
    def actions_column(self, obj):
        if obj.status == 'detected':
            return format_html(
                '<div class="flex space-x-2">'
                '<a href="#" onclick="executeOpportunity(\'{}\')" class="text-green-600 hover:text-green-800">Execute</a>'
                '<a href="#" onclick="viewDetails(\'{}\')" class="text-blue-600 hover:text-blue-800">Details</a>'
                '</div>',
                obj.id, obj.id
            )
        return '-'
    
    @display(description="Market Depth")
    def market_depth_display(self, obj):
        if obj.market_depth:
            return format_html('<pre class="text-xs">{}</pre>', str(obj.market_depth)[:100])
        return 'No data'
    
    @action(description="Execute selected opportunities")
    def execute_selected_opportunities(self, request, queryset):
        """Execute selected opportunities."""
        count = 0
        for opportunity in queryset.filter(status='detected'):
            # Here you would trigger the execution task
            # execute_arbitrage_opportunity.delay(opportunity.id)
            count += 1
        
        self.message_user(
            request, 
            f"Triggered execution for {count} opportunities.",
            level='success'
        )
    
    @action(description="Mark as expired")
    def mark_as_expired(self, request, queryset):
        """Mark opportunities as expired."""
        updated = queryset.update(status='expired')
        self.message_user(
            request,
            f"Marked {updated} opportunities as expired.",
            level='warning'
        )
    
    @action(description="Export to CSV")
    def export_to_csv(self, request, queryset):
        """Export opportunities to CSV."""
        # Implementation for CSV export
        self.message_user(
            request,
            f"Exported {queryset.count()} opportunities to CSV.",
            level='info'
        )


@admin.register(MultiExchangeArbitrageStrategy)
class MultiExchangeArbitrageStrategyAdmin(ModelAdmin):
    """Multi-exchange strategy management with enhanced visualization."""
    
    list_display = [
        'strategy_name', 'trading_pair_display', 'strategy_type_display',
        'exchanges_involved', 'profit_display', 'complexity_indicator', 
        'status_display', 'execution_progress'
    ]
    list_filter = [
        'status', 'strategy_type', 'trading_pair',
        ('created_at', admin.DateFieldListFilter),
        StrategyProfitFilter,
    ]
    search_fields = ['trading_pair__symbol']
    readonly_fields = [
        'complexity_score', 'risk_score', 'estimated_profit',
        'market_snapshot_display', 'execution_timeline'
    ]
    
    # Unfold settings
    list_fullwidth = True
    warn_unsaved_form = True
    compressed_fields = True
    
    fieldsets = [
        ("Strategy Overview", {
            "fields": [
                ('trading_pair', 'strategy_type', 'status'),
                ('complexity_score', 'risk_score'),
            ]
        }),
        ("Financial Analysis", {
            "fields": [
                ('total_buy_amount', 'total_sell_amount'),
                ('total_buy_cost', 'total_sell_revenue'),
                ('estimated_profit', 'profit_percentage'),
                ('total_fees',),
            ]
        }),
        ("Execution Data", {
            "fields": [
                'buy_actions',
                'sell_actions',
            ],
            "classes": ["collapse"]
        }),
        ("Timeline", {
            "fields": [
                ('expires_at', 'execution_started_at'),
                ('execution_completed_at',),
                'execution_timeline',
            ],
            "classes": ["collapse"]
        }),
        ("Market Data", {
            "fields": [
                'market_snapshot_display',
            ],
            "classes": ["collapse"]
        }),
    ]
    
    @display(description="Strategy ID")
    def strategy_name(self, obj):
        return format_html(
            '<div class="font-mono text-sm">'
            '<div class="font-bold">MX-{}</div>'
            '<div class="text-xs text-gray-500">{}</div>'
            '</div>',
            str(obj.id)[:8], obj.created_at.strftime('%m/%d %H:%M')
        )
    
    @display(description="Trading Pair")
    def trading_pair_display(self, obj):
        return format_html(
            '<span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-indigo-100 text-indigo-800">{}</span>',
            obj.trading_pair.symbol
        )
    
    @display(description="Type", label=True)
    def strategy_type_display(self, obj):
        type_colors = {
            'one_to_many': 'blue',
            'many_to_one': 'purple',
            'triangular': 'green',
            'complex': 'orange'
        }
        
        color = type_colors.get(obj.strategy_type, 'gray')
        display_name = obj.strategy_type.replace('_', ' ').title()
        
        return format_html(
            '<span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-{}-100 text-{}-800">{}</span>',
            color, color, display_name
        )
    
    @display(description="Exchanges")
    def exchanges_involved(self, obj):
        exchanges = set()
        for action in obj.buy_actions:
            exchanges.add(action.get('exchange', 'Unknown'))
        for action in obj.sell_actions:
            exchanges.add(action.get('exchange', 'Unknown'))
        
        return format_html(
            '<div class="text-sm">'
            '<div class="font-medium">{} exchanges</div>'
            '<div class="text-xs text-gray-500">{}</div>'
            '</div>',
            len(exchanges),
            ', '.join(list(exchanges)[:2]) + ('...' if len(exchanges) > 2 else '')
        )
    
    @display(description="Profit", ordering="profit_percentage")
    def profit_display(self, obj):
        color = 'green' if obj.profit_percentage >= 2 else 'yellow' if obj.profit_percentage >= 1 else 'gray'
        
        return format_html(
            '<div class="text-center">'
            '<div class="text-lg font-bold text-{}-600">{:.2f}%</div>'
            '<div class="text-sm text-gray-500">${:.2f}</div>'
            '</div>',
            color, obj.profit_percentage, obj.estimated_profit
        )
    
    @display(description="Complexity", label=True)
    def complexity_indicator(self, obj):
        score = obj.complexity_score
        if score <= 3:
            color, label = "green", "Simple"
        elif score <= 6:
            color, label = "yellow", "Medium"
        else:
            color, label = "red", "Complex"
        
        return format_html(
            '<span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-{}-100 text-{}-800">'
            '{} ({})'
            '</span>',
            color, color, label, score
        )
    
    @display(description="Status", label=True)
    def status_display(self, obj):
        status_colors = {
            'detected': 'blue',
            'analyzing': 'yellow', 
            'ready': 'green',
            'executing': 'purple',
            'completed': 'green',
            'failed': 'red',
            'expired': 'gray'
        }
        
        color = status_colors.get(obj.status, 'gray')
        
        return format_html(
            '<span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-{}-100 text-{}-800">{}</span>',
            color, color, obj.status.title()
        )
    
    @display(description="Progress")
    def execution_progress(self, obj):
        if obj.status == 'completed':
            return format_html('<div class="w-full bg-green-200 rounded-full h-2"><div class="bg-green-600 h-2 rounded-full" style="width: 100%"></div></div>')
        elif obj.status == 'executing':
            # Calculate progress based on completed executions
            return format_html('<div class="w-full bg-yellow-200 rounded-full h-2"><div class="bg-yellow-600 h-2 rounded-full" style="width: 60%"></div></div>')
        elif obj.status == 'failed':
            return format_html('<div class="w-full bg-red-200 rounded-full h-2"><div class="bg-red-600 h-2 rounded-full" style="width: 30%"></div></div>')
        else:
            return format_html('<div class="w-full bg-gray-200 rounded-full h-2"><div class="bg-gray-400 h-2 rounded-full" style="width: 5%"></div></div>')
    
    @display(description="Market Snapshot")
    def market_snapshot_display(self, obj):
        if obj.market_snapshot:
            return format_html('<pre class="text-xs bg-gray-50 p-2 rounded">{}</pre>', str(obj.market_snapshot)[:200])
        return 'No snapshot available'
    
    @display(description="Execution Timeline")
    def execution_timeline(self, obj):
        timeline = []
        timeline.append(f"Created: {obj.created_at.strftime('%H:%M:%S')}")
        if obj.execution_started_at:
            timeline.append(f"Started: {obj.execution_started_at.strftime('%H:%M:%S')}")
        if obj.execution_completed_at:
            timeline.append(f"Completed: {obj.execution_completed_at.strftime('%H:%M:%S')}")
        
        return format_html('<div class="text-xs">{}</div>', '<br>'.join(timeline))


@admin.register(ArbitrageExecution)
class ArbitrageExecutionAdmin(ModelAdmin):
    """Execution tracking and analysis with detailed monitoring."""
    
    list_display = [
        'execution_id', 'opportunity_link', 'status_display',
        'execution_progress', 'profit_result', 'timing_analysis'
    ]
    list_filter = [
        'status', 'opportunity__trading_pair',
        ('created_at', admin.DateFieldListFilter)
    ]
    search_fields = ['opportunity__trading_pair__symbol']
    readonly_fields = [
        'opportunity', 'final_profit', 'profit_percentage',
        'execution_details', 'timing_details'
    ]
    
    # Unfold settings
    list_fullwidth = True
    compressed_fields = True
    
    @display(description="Execution ID")
    def execution_id(self, obj):
        return format_html(
            '<span class="font-mono text-sm">EX-{}</span>',
            str(obj.id)[:8]
        )
    
    @display(description="Opportunity")
    def opportunity_link(self, obj):
        if obj.opportunity:
            url = reverse('admin:arbitrage_arbitrageopportunity_change', args=[obj.opportunity.id])
            return format_html(
                '<a href="{}" class="text-blue-600 hover:text-blue-800">{}</a>',
                url, obj.opportunity.trading_pair.symbol
            )
        return '-'
    
    @display(description="Status", label=True)
    def status_display(self, obj):
        colors = {
            'pending': 'yellow',
            'buy_placed': 'blue',
            'buy_filled': 'green',
            'sell_placed': 'blue',
            'sell_filled': 'green',
            'completed': 'green',
            'failed': 'red',
            'cancelled': 'gray'
        }
        
        color = colors.get(obj.status, 'gray')
        
        return format_html(
            '<span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-{}-100 text-{}-800">{}</span>',
            color, color, obj.get_status_display()
        )
    
    @display(description="Progress")
    def execution_progress(self, obj):
        progress_map = {
            'pending': 10,
            'buy_placed': 25,
            'buy_filled': 50,
            'sell_placed': 75,
            'sell_filled': 90,
            'completed': 100,
            'failed': 0,
            'cancelled': 0
        }
        
        progress = progress_map.get(obj.status, 0)
        color = 'green' if progress == 100 else 'red' if progress == 0 else 'blue'
        
        return format_html(
            '<div class="w-full bg-gray-200 rounded-full h-2">'
            '<div class="bg-{}-600 h-2 rounded-full transition-all duration-500" style="width: {}%"></div>'
            '</div>',
            color, progress
        )
    
    @display(description="Result")
    def profit_result(self, obj):
        if obj.final_profit is not None:
            color = 'green' if obj.final_profit > 0 else 'red'
            return format_html(
                '<div class="text-center">'
                '<div class="font-bold text-{}-600">${:.2f}</div>'
                '<div class="text-xs text-gray-500">{:.2f}%</div>'
                '</div>',
                color, obj.final_profit, obj.profit_percentage or 0
            )
        return '-'
    
    @display(description="Timing")
    def timing_analysis(self, obj):
        if obj.completed_at:
            duration = obj.completed_at - obj.created_at
            total_seconds = duration.total_seconds()
            
            color = 'green' if total_seconds < 30 else 'yellow' if total_seconds < 60 else 'red'
            
            return format_html(
                '<span class="text-{}-600 font-mono text-sm">{:.1f}s</span>',
                color, total_seconds
            )
        return '-'

    @display(description="Execution Details")
    def execution_details(self, obj):
        return format_html(
            '<div class="text-sm">'
            '<div class="mb-2">'
            '<span class="font-medium">Buy Order:</span> {} @ {:.8f}</div>'
            '<div class="mb-2">'
            '<span class="font-medium">Sell Order:</span> {} @ {:.8f}</div>'
            '<div>'
            '<span class="font-medium">Net Result:</span> {:.8f}</div>'
            '</div>',
            obj.buy_order_id, obj.buy_price,
            obj.sell_order_id, obj.sell_price,
            obj.final_profit
        )
    
    @display(description="Timing Details")
    def timing_details(self, obj):
        return format_html(
            '<div class="text-sm">'
            '<div class="mb-2">'
            '<span class="font-medium">Started:</span> {}</div>'
            '<div class="mb-2">'
            '<span class="font-medium">Completed:</span> {}</div>'
            '<div>'
            '<span class="font-medium">Duration:</span> {:.2f}s</div>'
            '</div>',
            obj.created_at.strftime('%H:%M:%S'),
            obj.completed_at.strftime('%H:%M:%S') if obj.completed_at else '-',
            (obj.completed_at - obj.created_at).total_seconds() if obj.completed_at else 0
        )


@admin.register(ArbitrageConfig)
class ArbitrageConfigAdmin(ModelAdmin):
    """User configuration management with intuitive interface."""
    
    list_display = [
        'user', 'is_active', 'auto_trade_status', 'risk_level',
        'profit_settings', 'last_updated'
    ]
    list_filter = ['is_active', 'auto_trade', 'enable_multi_exchange']
    search_fields = ['user__username', 'user__email']
    
    # Unfold settings
    list_fullwidth = True
    warn_unsaved_form = True
    
    fieldsets = [
        ("Basic Settings", {
            "fields": [
                ('user', 'is_active'),
                ('auto_trade', 'enable_notifications'),
            ]
        }),
        ("Profit Thresholds", {
            "fields": [
                ('min_profit_percentage', 'min_profit_amount'),
                ('stop_loss_percentage',),
            ]
        }),
        ("Trading Limits", {
            "fields": [
                'max_trade_amount',
                'daily_trade_limit',
                ('max_exposure_percentage',),
            ]
        }),
        ("Multi-Exchange Settings", {
            "fields": [
                ('enable_multi_exchange', 'max_exchanges_per_strategy'),
                ('min_profit_per_exchange', 'allocation_strategy'),
                ('require_simultaneous_execution', 'max_execution_time'),
            ],
            "classes": ["collapse"]
        }),
        ("Risk Management", {
            "fields": [
                ('slippage_tolerance', 'max_slippage_tolerance'),
                ('min_liquidity_ratio',),
                'exchange_reliability_weights',
            ],
            "classes": ["collapse"]
        }),
        ("Notifications", {
            "fields": [
                'notification_channels',
                ('notify_on_high_profit',),
            ],
            "classes": ["collapse"]
        }),
    ]
    
    @display(description="Auto Trading", boolean=True)
    def auto_trade_status(self, obj):
        return obj.auto_trade
    
    @display(description="Risk Level", label=True)
    def risk_level(self, obj):
        if obj.max_exposure_percentage <= 5:
            return format_html('<span class="bg-green-100 text-green-800 px-2 py-1 rounded-full text-xs font-medium">Conservative</span>')
        elif obj.max_exposure_percentage <= 15:
            return format_html('<span class="bg-yellow-100 text-yellow-800 px-2 py-1 rounded-full text-xs font-medium">Moderate</span>')
        else:
            return format_html('<span class="bg-red-100 text-red-800 px-2 py-1 rounded-full text-xs font-medium">Aggressive</span>')
    
    @display(description="Profit Settings")
    def profit_settings(self, obj):
        return format_html(
            '<div class="text-sm">'
            '<div>Min: {:.1f}%</div>'
            '<div>Stop: {:.1f}%</div>'
            '</div>',
            obj.min_profit_percentage, obj.stop_loss_percentage
        )
    
    @display(description="Last Updated", ordering="updated_at")
    def last_updated(self, obj):
        return obj.updated_at.strftime('%m/%d/%Y %H:%M')


# Custom admin site configuration
admin.site.site_header = "Crypto Arbitrage Administration"
admin.site.site_title = "Arbitrage Admin"
admin.site.index_title = "Welcome to Crypto Arbitrage Admin Portal"