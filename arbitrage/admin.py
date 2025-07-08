from django.contrib import admin
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


class ArbitrageExecutionInline(TabularInline):
    """Inline for viewing executions."""
    
    model = ArbitrageExecution
    extra = 0
    readonly_fields = ['executed_at', 'status', 'actual_profit']
    fields = ['status', 'executed_amount', 'actual_profit', 'executed_at']


@admin.register(ArbitrageOpportunity)
class ArbitrageOpportunityAdmin(ModelAdmin):
    """Enhanced arbitrage opportunity monitoring."""
    
    list_display = [
        'trading_pair_display', 'route_display', 'profit_display',
        'status_indicator', 'optimal_amount_display', 'expires_at'
    ]
    list_filter = ['status', 'buy_exchange', 'sell_exchange', 'expires_at']
    search_fields = ['trading_pair__symbol', 'buy_exchange__name', 'sell_exchange__name']
    readonly_fields = [
        'gross_profit_percentage', 'net_profit_percentage', 'estimated_profit',
        'total_fees', 'detection_latency', 'expires_at'
    ]
    inlines = [ArbitrageExecutionInline]
    
    # Unfold settings
    list_fullwidth = True
    compressed_fields = True
    list_per_page = 50
    
    # Custom actions
    actions = ['execute_selected_opportunities', 'mark_as_expired']
    
    fieldsets = [
        ("Opportunity Details", {
            "fields": [
                ('trading_pair', 'status'),
                ('buy_exchange', 'sell_exchange'),
                ('buy_price', 'sell_price'),
            ]
        }),
        ("Profit Analysis", {
            "fields": [
                ('gross_profit_percentage', 'net_profit_percentage'),
                ('estimated_profit', 'total_fees'),
                ('optimal_amount',),
            ]
        }),
        ("Execution Details", {
            "fields": [
                ('available_buy_amount', 'available_sell_amount'),
                ('executed_amount', 'actual_profit'),
                ('expires_at', 'executed_at'),
            ]
        }),
        ("Technical Details", {
            "fields": [
                ('detection_latency', 'market_depth'),
            ],
            "classes": ["collapse"]
        }),
    ]
    
    @display(description="Trading Pair")
    def trading_pair_display(self, obj):
        return format_html(
            '<div class="font-medium">{}</div>'
            '<div class="text-sm text-gray-600">{}/{}</div>',
            obj.trading_pair.symbol,
            obj.trading_pair.base_currency.symbol,
            obj.trading_pair.quote_currency.symbol
        )
    
    @display(description="Route")
    def route_display(self, obj):
        return format_html(
            '<div class="text-sm">'
            '<div class="text-green-800">Buy: {}</div>'
            '<div class="text-red-800">Sell: {}</div>'
            '</div>',
            obj.buy_exchange.name,
            obj.sell_exchange.name
        )
    
    @display(description="Profit", ordering="net_profit_percentage")
    def profit_display(self, obj):
        profit_pct = obj.net_profit_percentage
        color = "green" if profit_pct > 0 else "red"
        
        return format_html(
            '<div class="text-{}-800">'
            '<div class="font-bold text-lg">{:.2f}%</div>'
            '<div class="text-sm">${:.2f}</div>'
            '</div>',
            color, profit_pct, obj.estimated_profit
        )
    
    @display(description="Status", label=True)
    def status_indicator(self, obj):
        status_colors = {
            'detected': ('blue', 'New'),
            'executing': ('yellow', 'Executing'),
            'executed': ('green', 'Executed'),
            'expired': ('gray', 'Expired'),
            'failed': ('red', 'Failed'),
        }
        
        color, label = status_colors.get(obj.status, ('gray', obj.status.title()))
        
        return format_html(
            '<span class="bg-{}-100 text-{}-800 px-2 py-1 rounded-full text-xs font-medium">{}</span>',
            color, color, label
        )
    
    @display(description="Amount", ordering="optimal_amount")
    def optimal_amount_display(self, obj):
        return format_html(
            '<span class="font-mono">{:.4f}</span>',
            obj.optimal_amount
        )
    
    @action(description="Execute selected opportunities")
    def execute_selected_opportunities(self, request, queryset):
        """Custom action to execute selected opportunities."""
        count = 0
        for opportunity in queryset.filter(status='detected'):
            # Here you would trigger the execution task
            # execute_arbitrage_opportunity.delay(opportunity.id)
            count += 1
        
        self.message_user(
            request, 
            f"Triggered execution for {count} opportunities."
        )
    
    @action(description="Mark as expired")
    def mark_as_expired(self, request, queryset):
        """Mark opportunities as expired."""
        updated = queryset.update(status='expired')
        self.message_user(
            request,
            f"Marked {updated} opportunities as expired."
        )


@admin.register(MultiExchangeArbitrageStrategy)
class MultiExchangeArbitrageStrategyAdmin(ModelAdmin):
    """Multi-exchange strategy management."""
    
    list_display = [
        'strategy_name', 'trading_pairs_display', 'exchanges_count',
        'profit_display', 'complexity_indicator', 'status_display'
    ]
    list_filter = ['status', 'created_at']
    readonly_fields = ['total_profit_percentage', 'estimated_total_profit', 'complexity_score']
    
    # Unfold settings
    list_fullwidth = True
    warn_unsaved_form = True
    
    @display(description="Strategy")
    def strategy_name(self, obj):
        return f"Multi-Exchange #{obj.id}"
    
    @display(description="Trading Pairs")
    def trading_pairs_display(self, obj):
        pairs = [step.get('trading_pair', 'Unknown') for step in obj.execution_steps]
        return format_html(
            '<div class="text-sm">{}</div>',
            " → ".join(pairs[:3]) + ("..." if len(pairs) > 3 else "")
        )
    
    @display(description="Exchanges")
    def exchanges_count(self, obj):
        exchanges = set()
        for step in obj.execution_steps:
            exchanges.add(step.get('exchange', 'Unknown'))
        return f"{len(exchanges)} exchanges"
    
    @display(description="Profit", ordering="total_profit_percentage")
    def profit_display(self, obj):
        return format_html(
            '<div class="text-green-800">'
            '<div class="font-bold">{:.2f}%</div>'
            '<div class="text-sm">${:.2f}</div>'
            '</div>',
            obj.total_profit_percentage, obj.estimated_total_profit
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
            '<span class="bg-{}-100 text-{}-800 px-2 py-1 rounded-full text-xs font-medium">{}</span>',
            color, color, label
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
        }
        
        color = status_colors.get(obj.status, 'gray')
        
        return format_html(
            '<span class="bg-{}-100 text-{}-800 px-2 py-1 rounded-full text-xs font-medium">{}</span>',
            color, color, obj.status.title()
        )


@admin.register(ArbitrageExecution)
class ArbitrageExecutionAdmin(ModelAdmin):
    """Execution tracking and analysis."""
    
    list_display = [
        'opportunity_link', 'status_indicator', 'executed_amount_display',
        'profit_analysis', 'execution_time', 'executed_at'
    ]
    list_filter = ['status', 'executed_at']
    search_fields = [
        'opportunity__trading_pair__symbol',
        'opportunity__buy_exchange__name',
        'opportunity__sell_exchange__name'
    ]
    readonly_fields = ['executed_at', 'execution_metadata']
    
    # Unfold settings
    list_fullwidth = True
    compressed_fields = True
    
    @display(description="Opportunity")
    def opportunity_link(self, obj):
        url = reverse('admin:arbitrage_arbitrageopportunity_change', args=[obj.opportunity.id])
        return format_html(
            '<a href="{}" class="text-blue-600 hover:text-blue-800">{}</a>',
            url, 
            f"{obj.opportunity.trading_pair.symbol} ({obj.opportunity.buy_exchange.name} → {obj.opportunity.sell_exchange.name})"
        )
    
    @display(description="Status", label=True)
    def status_indicator(self, obj):
        status_colors = {
            'pending': 'yellow',
            'executing': 'blue',
            'completed': 'green',
            'failed': 'red',
            'cancelled': 'gray',
        }
        
        color = status_colors.get(obj.status, 'gray')
        
        return format_html(
            '<span class="bg-{}-100 text-{}-800 px-2 py-1 rounded-full text-xs font-medium">{}</span>',
            color, color, obj.status.title()
        )
    
    @display(description="Amount", ordering="executed_amount")
    def executed_amount_display(self, obj):
        if obj.executed_amount:
            return format_html(
                '<span class="font-mono">{:.6f}</span>',
                obj.executed_amount
            )
        return "N/A"
    
    @display(description="Profit Analysis")
    def profit_analysis(self, obj):
        if obj.actual_profit is not None:
            color = "green" if obj.actual_profit >= 0 else "red"
            icon = "↗" if obj.actual_profit >= 0 else "↘"
            
            return format_html(
                '<div class="text-{}-800">'
                '<div class="font-bold">{} ${:.2f}</div>'
                '<div class="text-sm">Expected: ${:.2f}</div>'
                '</div>',
                color, icon, obj.actual_profit, obj.opportunity.estimated_profit
            )
        return "Pending"
    
    @display(description="Execution Time")
    def execution_time(self, obj):
        if obj.executed_at and obj.created_at:
            duration = obj.executed_at - obj.created_at
            seconds = duration.total_seconds()
            
            if seconds < 60:
                return f"{seconds:.1f}s"
            else:
                return f"{seconds/60:.1f}m"
        return "N/A"


@admin.register(ArbitrageConfig)
class ArbitrageConfigAdmin(ModelAdmin):
    """User arbitrage configuration management."""
    
    list_display = [
        'user', 'config_summary', 'risk_level_display', 
        'is_active_display', 'updated_at'
    ]
    list_filter = ['is_active', 'max_execution_amount', 'updated_at']
    search_fields = ['user__username']
    
    # Unfold settings
    list_fullwidth = True
    warn_unsaved_form = True
    
    fieldsets = [
        ("User Settings", {
            "fields": [
                ('user', 'is_active'),
            ]
        }),
        ("Risk Management", {
            "fields": [
                ('min_profit_threshold', 'max_execution_amount'),
                ('max_daily_executions', 'stop_loss_percentage'),
            ]
        }),
        ("Execution Settings", {
            "fields": [
                ('allowed_exchanges', 'excluded_trading_pairs'),
                ('execution_delay', 'auto_execute'),
            ]
        }),
        ("Notifications", {
            "fields": [
                ('notification_settings',),
            ]
        }),
    ]
    
    @display(description="Configuration")
    def config_summary(self, obj):
        return format_html(
            '<div class="text-sm">'
            '<div>Min Profit: {:.2f}%</div>'
            '<div>Max Amount: ${:,.0f}</div>'
            '<div>Max Daily: {} executions</div>'
            '</div>',
            obj.min_profit_threshold, obj.max_execution_amount, obj.max_daily_executions
        )
    
    @display(description="Risk Level", label=True)
    def risk_level_display(self, obj):
        if obj.min_profit_threshold >= 2.0 and obj.max_execution_amount <= 1000:
            return format_html(
                '<span class="bg-green-100 text-green-800 px-2 py-1 rounded-full text-xs font-medium">Conservative</span>'
            )
        elif obj.min_profit_threshold >= 1.0:
            return format_html(
                '<span class="bg-yellow-100 text-yellow-800 px-2 py-1 rounded-full text-xs font-medium">Moderate</span>'
            )
        else:
            return format_html(
                '<span class="bg-red-100 text-red-800 px-2 py-1 rounded-full text-xs font-medium">Aggressive</span>'
            )
    
    @display(description="Status", boolean=True)
    def is_active_display(self, obj):
        return obj.is_active


@admin.register(ArbitrageAlert)
class ArbitrageAlertAdmin(ModelAdmin):
    """Alert management system."""
    
    list_display = [
        'alert_type_display', 'message_preview', 'is_read_display',
        'priority_indicator', 'created_at'
    ]
    list_filter = ['alert_type', 'is_read', 'priority', 'created_at']
    search_fields = ['message', 'opportunity__trading_pair__symbol']
    actions = ['mark_as_read', 'mark_as_unread']
    
    # Unfold settings
    list_fullwidth = True
    list_per_page = 100
    
    @display(description="Type", label=True)
    def alert_type_display(self, obj):
        type_colors = {
            'opportunity_detected': 'blue',
            'execution_started': 'yellow',
            'execution_completed': 'green',
            'execution_failed': 'red',
            'system_error': 'red',
            'exchange_offline': 'orange',
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


# Custom admin site configuration
admin.site.site_header = "Crypto Arbitrage Administration"
admin.site.site_title = "Arbitrage Admin"  
admin.site.index_title = "Welcome to Crypto Arbitrage Platform"