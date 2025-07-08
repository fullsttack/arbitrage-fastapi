# Enhanced Dashboard Callback - save as core/admin_dashboard.py

import json
from datetime import datetime, timedelta
from decimal import Decimal

from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Count, Sum, Avg, Q
from django.utils import timezone

from arbitrage.models import ArbitrageOpportunity, ArbitrageExecution, MultiExchangeArbitrageStrategy
from analytics.models import DailyArbitrageSummary, ExchangePerformance
from core.models import Exchange
from exchanges.models import ExchangeStatus, MarketTicker
from trading.models import Order, Trade


def dashboard_callback(request, context):
    """
    Enhanced dashboard callback with comprehensive arbitrage metrics.
    """
    now = timezone.now()
    today = now.date()
    week_ago = now - timedelta(days=7)
    month_ago = now - timedelta(days=30)
    
    # === ARBITRAGE METRICS ===
    
    # Active opportunities
    active_opportunities = ArbitrageOpportunity.objects.filter(
        status='detected',
        expires_at__gt=now
    ).count()
    
    # Today's opportunities
    todays_opportunities = ArbitrageOpportunity.objects.filter(
        created_at__date=today
    ).count()
    
    # Weekly profit
    weekly_executions = ArbitrageExecution.objects.filter(
        completed_at__gte=week_ago,
        status='completed'
    )
    
    weekly_profit = weekly_executions.aggregate(
        total=Sum('final_profit')
    )['total'] or Decimal('0')
    
    # Success rate (last 7 days)
    weekly_all_executions = ArbitrageExecution.objects.filter(
        created_at__gte=week_ago
    )
    success_rate = 0
    if weekly_all_executions.exists():
        successful = weekly_all_executions.filter(status='completed').count()
        total = weekly_all_executions.count()
        success_rate = (successful / total) * 100 if total > 0 else 0
    
    # === EXCHANGE METRICS ===
    
    # Exchange health
    exchange_statuses = ExchangeStatus.objects.select_related('exchange').filter(
        exchange__is_active=True
    )
    
    online_exchanges = exchange_statuses.filter(is_online=True).count()
    total_exchanges = Exchange.objects.filter(is_active=True).count()
    
    # Average response time
    avg_response_time = exchange_statuses.filter(
        is_online=True
    ).aggregate(
        avg_time=Avg('response_time')
    )['avg_time'] or 0
    
    # === TRADING METRICS ===
    
    # Active orders
    active_orders = Order.objects.filter(
        status__in=['pending', 'partially_filled']
    ).count()
    
    # Today's trades
    todays_trades = Trade.objects.filter(
        executed_at__date=today
    ).count()
    
    # === MARKET METRICS ===
    
    # Active trading pairs
    active_pairs = MarketTicker.objects.filter(
        timestamp__gte=now - timedelta(minutes=5)
    ).values('exchange_pair').distinct().count()
    
    # === RECENT OPPORTUNITIES ===
    
    recent_opportunities = ArbitrageOpportunity.objects.select_related(
        'trading_pair', 'buy_exchange', 'sell_exchange'
    ).filter(
        created_at__gte=now - timedelta(hours=24)
    ).order_by('-created_at')[:10]
    
    # Add profit class for styling
    for opp in recent_opportunities:
        if opp.net_profit_percentage >= 2.0:
            opp.profit_class = 'high-profit'
        elif opp.net_profit_percentage >= 1.0:
            opp.profit_class = 'medium-profit'
        else:
            opp.profit_class = 'low-profit'
    
    # === CHART DATA ===
    
    # Profit chart data (last 7 days)
    profit_chart_data = []
    profit_chart_labels = []
    
    for i in range(7):
        date = today - timedelta(days=6-i)
        daily_profit = ArbitrageExecution.objects.filter(
            completed_at__date=date,
            status='completed'
        ).aggregate(
            total=Sum('final_profit')
        )['total'] or 0
        
        profit_chart_data.append(float(daily_profit))
        profit_chart_labels.append(date.strftime('%m/%d'))
    
    # Exchange performance chart
    exchange_chart_labels = []
    exchange_chart_data = []
    
    exchange_performance = ExchangePerformance.objects.filter(
        date=today
    ).select_related('exchange')
    
    for perf in exchange_performance:
        exchange_chart_labels.append(perf.exchange.name)
        exchange_chart_data.append(float(perf.uptime_percentage))
    
    # === MULTI-EXCHANGE STRATEGIES ===
    
    active_strategies = MultiExchangeArbitrageStrategy.objects.filter(
        status='detected'
    ).count()
    
    # === SYSTEM HEALTH INDICATORS ===
    
    # Database response time (rough estimate)
    db_start = timezone.now()
    test_query = Exchange.objects.first()
    db_response_time = (timezone.now() - db_start).total_seconds() * 1000
    
    # Redis health (if available)
    redis_healthy = True
    try:
        from django.core.cache import cache
        cache.set('health_check', 'ok', 1)
        redis_healthy = cache.get('health_check') == 'ok'
    except:
        redis_healthy = False
    
    # Celery health (check recent tasks)
    recent_tasks = 0
    try:
        from django_celery_beat.models import PeriodicTask
        recent_tasks = PeriodicTask.objects.filter(enabled=True).count()
    except:
        pass
    
    # === ALERTS AND NOTIFICATIONS ===
    
    # High profit opportunities today
    high_profit_opportunities = ArbitrageOpportunity.objects.filter(
        created_at__date=today,
        net_profit_percentage__gte=5.0
    ).count()
    
    # Failed executions today
    failed_executions = ArbitrageExecution.objects.filter(
        created_at__date=today,
        status='failed'
    ).count()
    
    # === PERFORMANCE METRICS ===
    
    # Average execution time
    avg_execution_time = ArbitrageExecution.objects.filter(
        completed_at__gte=week_ago,
        status='completed'
    ).extra(
        select={
            'execution_duration': 'EXTRACT(EPOCH FROM (completed_at - created_at))'
        }
    ).aggregate(
        avg_time=Avg('execution_duration')
    )['avg_time'] or 0
    
    # Update context with all metrics
    context.update({
        # Core metrics
        'active_opportunities': active_opportunities,
        'todays_opportunities': todays_opportunities,
        'weekly_profit': weekly_profit,
        'success_rate': success_rate,
        'online_exchanges': online_exchanges,
        'total_exchanges': total_exchanges,
        'avg_response_time': avg_response_time,
        'active_orders': active_orders,
        'todays_trades': todays_trades,
        'active_pairs': active_pairs,
        
        # Recent data
        'recent_opportunities': recent_opportunities,
        
        # Chart data
        'profit_chart_data': json.dumps(profit_chart_data),
        'profit_chart_labels': json.dumps(profit_chart_labels),
        'exchange_chart_data': json.dumps(exchange_chart_data),
        'exchange_chart_labels': json.dumps(exchange_chart_labels),
        
        # Multi-exchange
        'active_strategies': active_strategies,
        
        # System health
        'db_response_time': db_response_time,
        'redis_healthy': redis_healthy,
        'celery_tasks': recent_tasks,
        
        # Alerts
        'high_profit_opportunities': high_profit_opportunities,
        'failed_executions': failed_executions,
        
        # Performance
        'avg_execution_time': avg_execution_time,
        
        # Additional context for enhanced dashboard
        'dashboard_title': 'Crypto Arbitrage Dashboard',
        'last_updated': now.strftime('%Y-%m-%d %H:%M:%S'),
        'environment': 'Development' if context.get('DEBUG') else 'Production',
    })
    
    return context


@staff_member_required
def dashboard_stats_api(request):
    """
    API endpoint for real-time dashboard updates.
    """
    from django.http import JsonResponse
    
    now = timezone.now()
    today = now.date()
    week_ago = now - timedelta(days=7)
    
    # Get latest stats
    active_opportunities = ArbitrageOpportunity.objects.filter(
        status='detected',
        expires_at__gt=now
    ).count()
    
    weekly_profit = ArbitrageExecution.objects.filter(
        completed_at__gte=week_ago,
        status='completed'
    ).aggregate(
        total=Sum('final_profit')
    )['total'] or Decimal('0')
    
    active_orders = Order.objects.filter(
        status__in=['pending', 'partially_filled']
    ).count()
    
    online_exchanges = ExchangeStatus.objects.filter(
        is_online=True
    ).count()
    
    return JsonResponse({
        'active_opportunities': active_opportunities,
        'weekly_profit': float(weekly_profit),
        'active_orders': active_orders,
        'online_exchanges': online_exchanges,
        'timestamp': now.isoformat(),
    })


# Utility function for environment label
def get_environment_label(request=None):
    """Return environment label for admin interface."""
    from django.conf import settings
    if getattr(settings, 'DEBUG', False):
        return "Development"
    return "Production"