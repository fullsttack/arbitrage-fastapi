from django.contrib import admin
from django.utils.html import format_html

from unfold.admin import ModelAdmin
from unfold.decorators import display

from analytics.models import DailyArbitrageSummary, ExchangePerformance


@admin.register(DailyArbitrageSummary)
class DailyArbitrageSummaryAdmin(ModelAdmin):
    """Daily arbitrage performance tracking."""
    
    list_display = [
        'date_display', 'opportunities_summary', 'profit_summary',
        'success_metrics', 'volume_summary'
    ]
    list_filter = [('date', admin.DateFieldListFilter)]
    date_hierarchy = 'date'
    ordering = ['-date']
    
    # Unfold settings
    list_fullwidth = True
    
    @display(description="Date", ordering="date")
    def date_display(self, obj):
        return format_html(
            '<div class="font-medium">{}</div>',
            obj.date.strftime('%B %d, %Y')
        )
    
    @display(description="Opportunities")
    def opportunities_summary(self, obj):
        return format_html(
            '<div class="text-sm">'
            '<div class="font-bold text-blue-600">{}</div>'
            '<div class="text-xs text-gray-500">detected</div>'
            '<div class="font-bold text-green-600">{}</div>'
            '<div class="text-xs text-gray-500">executed</div>'
            '</div>',
            obj.total_opportunities_detected,
            obj.total_opportunities_executed
        )
    
    @display(description="Profit")
    def profit_summary(self, obj):
        return format_html(
            '<div class="text-sm">'
            '<div class="font-bold text-green-600">${:.2f}</div>'
            '<div class="text-xs text-gray-500">{:.2f}% avg</div>'
            '</div>',
            obj.total_profit, obj.average_profit_percentage
        )
    
    @display(description="Success Rate")
    def success_metrics(self, obj):
        success_rate = (obj.total_opportunities_executed / obj.total_opportunities_detected * 100) if obj.total_opportunities_detected else 0
        
        color = 'green' if success_rate > 80 else 'yellow' if success_rate > 60 else 'red'
        
        return format_html(
            '<div class="text-{}-600 font-bold">{:.1f}%</div>',
            color, success_rate
        )
    
    @display(description="Volume")
    def volume_summary(self, obj):
        return format_html(
            '<div class="text-sm font-mono">${:,.0f}</div>',
            obj.total_volume_traded
        )

@admin.register(ExchangePerformance)
class ExchangePerformanceAdmin(ModelAdmin):
    """Exchange performance tracking."""
    list_display = [field.name for field in ExchangePerformance._meta.fields]
    list_filter = ['exchange', 'date']
    search_fields = ['exchange__name']
    ordering = ['-date']
    list_fullwidth = True