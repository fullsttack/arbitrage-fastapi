from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse

from unfold.admin import ModelAdmin
from unfold.decorators import display

from analytics.models import (
    DailyArbitrageSummary, ExchangePerformance, 
    TradingPairAnalytics, UserPerformance, MarketSnapshot
)


@admin.register(DailyArbitrageSummary)
class DailyArbitrageSummaryAdmin(ModelAdmin):
    """Daily performance analytics."""
    
    list_display = [
        'date', 'opportunities_summary', 'execution_summary',
        'profit_display', 'success_rate_display', 'top_pair_link'
    ]
    list_filter = ['date']
    search_fields = ['top_trading_pair__symbol']
    readonly_fields = ['date']
    ordering = ['-date']
    
    # Unfold settings
    list_fullwidth = True
    compressed_fields = True
    
    @display(description="Opportunities")
    def opportunities_summary(self, obj):
        return format_html(
            '<div class="text-sm">'
            '<div class="font-medium">{} detected</div>'
            '<div class="text-gray-600">{} executed</div>'
            '</div>',
            obj.total_opportunities, obj.total_executions
        )
    
    @display(description="Execution Results")
    def execution_summary(self, obj):
        success_color = "green" if obj.successful_executions > obj.failed_executions else "red"
        
        return format_html(
            '<div class="text-sm">'
            '<div class="text-{}-800">{} successful</div>'
            '<div class="text-red-800">{} failed</div>'
            '</div>',
            success_color, obj.successful_executions, obj.failed_executions
        )
    
    @display(description="Total Profit", ordering="total_profit")
    def profit_display(self, obj):
        color = "green" if obj.total_profit >= 0 else "red"
        icon = "↗" if obj.total_profit >= 0 else "↘"
        
        return format_html(
            '<div class="text-{}-800">'
            '<div class="font-bold text-lg">{} ${:.2f}</div>'
            '<div class="text-sm">Avg: {:.2f}%</div>'
            '</div>',
            color, icon, obj.total_profit, obj.average_profit_percentage
        )
    
    @display(description="Success Rate")
    def success_rate_display(self, obj):
        if obj.total_executions > 0:
            rate = (obj.successful_executions / obj.total_executions) * 100
            color = "green" if rate >= 80 else "yellow" if rate >= 60 else "red"
            
            return format_html(
                '<div class="flex items-center">'
                '<div class="w-16 bg-gray-200 rounded-full h-2 mr-2">'
                '<div class="bg-{}-600 h-2 rounded-full" style="width: {:.0f}%"></div>'
                '</div>'
                '<span class="text-{}-800 font-medium">{:.1f}%</span>'
                '</div>',
                color, rate, color, rate
            )
        return "N/A"
    
    @display(description="Top Pair")
    def top_pair_link(self, obj):
        if obj.top_trading_pair:
            url = reverse('admin:core_tradingpair_change', args=[obj.top_trading_pair.id])
            return format_html(
                '<a href="{}" class="text-blue-600 hover:text-blue-800">{}</a>',
                url, obj.top_trading_pair.symbol
            )
        return "N/A"


@admin.register(ExchangePerformance)
class ExchangePerformanceAdmin(ModelAdmin):
    """Exchange performance tracking."""
    
    list_display = [
        'exchange', 'date', 'uptime_display', 'response_time_display',
        'volume_display', 'order_stats', 'reliability_indicator'
    ]
    list_filter = ['exchange', 'date']
    search_fields = ['exchange__name']
    ordering = ['-date', 'exchange']
    
    # Unfold settings
    list_fullwidth = True
    compressed_fields = True
    
    @display(description="Uptime", ordering="uptime_percentage")
    def uptime_display(self, obj):
        uptime = obj.uptime_percentage
        color = "green" if uptime >= 99 else "yellow" if uptime >= 95 else "red"
        
        return format_html(
            '<div class="flex items-center">'
            '<div class="w-16 bg-gray-200 rounded-full h-2 mr-2">'
            '<div class="bg-{}-600 h-2 rounded-full" style="width: {:.0f}%"></div>'
            '</div>'
            '<span class="text-{}-800 font-medium">{:.1f}%</span>'
            '</div>',
            color, uptime, color, uptime
        )
    
    @display(description="Response Time", ordering="average_response_time")
    def response_time_display(self, obj):
        time_ms = obj.average_response_time * 1000 if obj.average_response_time else 0
        color = "green" if time_ms < 100 else "yellow" if time_ms < 500 else "red"
        
        return format_html(
            '<span class="text-{}-800 font-mono">{:.0f}ms</span>',
            color, time_ms
        )
    
    @display(description="Volume", ordering="total_volume_traded")
    def volume_display(self, obj):
        return format_html(
            '<span class="font-mono">${:,.0f}</span>',
            obj.total_volume_traded or 0
        )
    
    @display(description="Orders")
    def order_stats(self, obj):
        success_rate = 0
        if obj.total_orders_placed > 0:
            success_rate = (obj.successful_orders / obj.total_orders_placed) * 100
        
        return format_html(
            '<div class="text-sm">'
            '<div>{} placed</div>'
            '<div class="text-green-800">{:.1f}% success</div>'
            '</div>',
            obj.total_orders_placed, success_rate
        )
    
    @display(description="Reliability", label=True)
    def reliability_indicator(self, obj):
        # Simple scoring based on uptime and response time
        score = obj.uptime_percentage
        if obj.average_response_time:
            # Penalize slow response times
            if obj.average_response_time > 1.0:  # > 1 second
                score -= 10
            elif obj.average_response_time > 0.5:  # > 500ms
                score -= 5
        
        if score >= 95:
            return format_html(
                '<span class="bg-green-100 text-green-800 px-2 py-1 rounded-full text-xs font-medium">Excellent</span>'
            )
        elif score >= 90:
            return format_html(
                '<span class="bg-yellow-100 text-yellow-800 px-2 py-1 rounded-full text-xs font-medium">Good</span>'
            )
        else:
            return format_html(
                '<span class="bg-red-100 text-red-800 px-2 py-1 rounded-full text-xs font-medium">Poor</span>'
            )


@admin.register(TradingPairAnalytics)
class TradingPairAnalyticsAdmin(ModelAdmin):
    """Trading pair performance analytics."""
    
    list_display = [
        'trading_pair', 'period_display', 'opportunities_count',
        'avg_profit_display', 'volume_display', 'volatility_indicator'
    ]
    list_filter = ['period_type', 'period_start', 'trading_pair']
    search_fields = ['trading_pair__symbol']
    ordering = ['-period_start', 'trading_pair']
    
    # Unfold settings
    list_fullwidth = True
    compressed_fields = True
    
    @display(description="Period")
    def period_display(self, obj):
        return format_html(
            '<div class="text-sm">'
            '<div class="font-medium">{}</div>'
            '<div class="text-gray-600">{}</div>'
            '</div>',
            obj.get_period_type_display(),
            obj.period_start.strftime('%Y-%m-%d')
        )
    
    @display(description="Opportunities", ordering="total_opportunities")
    def opportunities_count(self, obj):
        return format_html(
            '<div class="text-center">'
            '<div class="font-bold text-lg">{}</div>'
            '<div class="text-xs text-gray-600">detected</div>'
            '</div>',
            obj.total_opportunities
        )
    
    @display(description="Avg Profit", ordering="average_profit_percentage")
    def avg_profit_display(self, obj):
        profit = obj.average_profit_percentage
        color = "green" if profit > 0 else "red"
        
        return format_html(
            '<span class="text-{}-800 font-bold">{:.2f}%</span>',
            color, profit
        )
    
    @display(description="Volume", ordering="total_volume")
    def volume_display(self, obj):
        return format_html(
            '<span class="font-mono">${:,.0f}</span>',
            obj.total_volume or 0
        )
    
    @display(description="Volatility", label=True)
    def volatility_indicator(self, obj):
        volatility = obj.price_volatility or 0
        
        if volatility > 5:
            return format_html(
                '<span class="bg-red-100 text-red-800 px-2 py-1 rounded-full text-xs font-medium">High</span>'
            )
        elif volatility > 2:
            return format_html(
                '<span class="bg-yellow-100 text-yellow-800 px-2 py-1 rounded-full text-xs font-medium">Medium</span>'
            )
        else:
            return format_html(
                '<span class="bg-green-100 text-green-800 px-2 py-1 rounded-full text-xs font-medium">Low</span>'
            )


@admin.register(UserPerformance)
class UserPerformanceAdmin(ModelAdmin):
    """User performance tracking."""
    
    list_display = [
        'user', 'date', 'execution_summary', 'profit_display',
        'win_rate_display', 'risk_score_indicator'
    ]
    list_filter = ['date']
    search_fields = ['user__username']
    ordering = ['-date', 'user']
    
    # Unfold settings
    list_fullwidth = True
    compressed_fields = True
    
    @display(description="Executions")
    def execution_summary(self, obj):
        return format_html(
            '<div class="text-center">'
            '<div class="font-bold">{}</div>'
            '<div class="text-xs text-gray-600">trades</div>'
            '</div>',
            obj.total_executions
        )
    
    @display(description="Net Profit", ordering="net_profit")
    def profit_display(self, obj):
        profit = obj.net_profit
        color = "green" if profit >= 0 else "red"
        icon = "↗" if profit >= 0 else "↘"
        
        return format_html(
            '<div class="text-{}-800">'
            '<div class="font-bold">{} ${:.2f}</div>'
            '<div class="text-sm">Gross: ${:.2f}</div>'
            '</div>',
            color, icon, profit, obj.gross_profit
        )
    
    @display(description="Win Rate")
    def win_rate_display(self, obj):
        if obj.total_executions > 0:
            # This would need to be calculated from successful vs failed executions
            win_rate = 75  # Placeholder
            color = "green" if win_rate >= 70 else "yellow" if win_rate >= 50 else "red"
            
            return format_html(
                '<div class="flex items-center">'
                '<div class="w-12 bg-gray-200 rounded-full h-2 mr-2">'
                '<div class="bg-{}-600 h-2 rounded-full" style="width: {}%"></div>'
                '</div>'
                '<span class="text-{}-800 text-sm">{}%</span>'
                '</div>',
                color, win_rate, color, win_rate
            )
        return "N/A"
    
    @display(description="Risk Score", label=True)
    def risk_score_indicator(self, obj):
        # Calculate risk score based on execution patterns
        risk_score = 60  # Placeholder calculation
        
        if risk_score >= 80:
            return format_html(
                '<span class="bg-red-100 text-red-800 px-2 py-1 rounded-full text-xs font-medium">High Risk</span>'
            )
        elif risk_score >= 60:
            return format_html(
                '<span class="bg-yellow-100 text-yellow-800 px-2 py-1 rounded-full text-xs font-medium">Medium Risk</span>'
            )
        else:
            return format_html(
                '<span class="bg-green-100 text-green-800 px-2 py-1 rounded-full text-xs font-medium">Low Risk</span>'
            )


@admin.register(MarketSnapshot)
class MarketSnapshotAdmin(ModelAdmin):
    """Market condition snapshots."""
    
    list_display = [
        'timestamp', 'active_opportunities_display', 'spread_analysis',
        'market_trend_indicator', 'volatility_display'
    ]
    list_filter = ['market_trend', 'timestamp']
    ordering = ['-timestamp']
    
    # Unfold settings
    list_fullwidth = True
    compressed_fields = True
    list_per_page = 50
    
    @display(description="Active Opportunities", ordering="active_opportunities")
    def active_opportunities_display(self, obj):
        return format_html(
            '<div class="text-center">'
            '<div class="font-bold text-lg text-blue-800">{}</div>'
            '<div class="text-xs text-gray-600">opportunities</div>'
            '</div>',
            obj.active_opportunities
        )
    
    @display(description="Spread Analysis")
    def spread_analysis(self, obj):
        avg_spread = obj.average_spread
        color = "green" if avg_spread > 1 else "yellow" if avg_spread > 0.5 else "red"
        
        return format_html(
            '<div class="text-sm">'
            '<div class="text-{}-800 font-medium">Avg: {:.2f}%</div>'
            '<div class="text-gray-600">Max: {:.2f}%</div>'
            '</div>',
            color, avg_spread, obj.max_spread
        )
    
    @display(description="Market Trend", label=True)
    def market_trend_indicator(self, obj):
        trend_colors = {
            'bullish': 'green',
            'bearish': 'red',
            'sideways': 'yellow',
            'volatile': 'purple',
        }
        
        color = trend_colors.get(obj.market_trend, 'gray')
        
        return format_html(
            '<span class="bg-{}-100 text-{}-800 px-2 py-1 rounded-full text-xs font-medium">{}</span>',
            color, color, obj.get_market_trend_display()
        )
    
    @display(description="Volatility Index")
    def volatility_display(self, obj):
        volatility = obj.volatility_index or 0
        
        if volatility > 70:
            color, label = "red", "Very High"
        elif volatility > 50:
            color, label = "orange", "High"
        elif volatility > 30:
            color, label = "yellow", "Medium"
        else:
            color, label = "green", "Low"
        
        return format_html(
            '<div class="flex items-center">'
            '<div class="w-16 bg-gray-200 rounded-full h-2 mr-2">'
            '<div class="bg-{}-600 h-2 rounded-full" style="width: {:.0f}%"></div>'
            '</div>'
            '<span class="text-{}-800 text-xs">{}</span>'
            '</div>',
            color, volatility, color, label
        )