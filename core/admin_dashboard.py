from datetime import datetime, timedelta
from decimal import Decimal

from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Count, Sum, Avg, Q
from django.utils import timezone

from arbitrage.models import ArbitrageOpportunity, ArbitrageExecution
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
    weekly_profit = ArbitrageExecution.objects.filter(
        completed_at__gte=week_ago,
        status='completed'
    ).aggregate(
        total=Sum('final_profit')
    )['total'] or Decimal('0')
    
    # Success rate (last 7 days)
    weekly_executions = ArbitrageExecution.objects.filter(
        created_at__gte=week_ago
    )
    success_rate = 0
    if weekly_executions.exists():
        successful = weekly_executions.filter(status='completed').count()
        total = weekly_executions.count()
        success_rate = (successful / total) * 100 if total > 0 else 0
    
    # === EXCHANGE METRICS ===
    
    # Exchange health
    online_exchanges = ExchangeStatus.objects.filter(
        is_online=True
    ).count()
    total_exchanges = Exchange.objects.filter(is_active=True).count()
    
    # Average response time
    avg_response_time = ExchangeStatus.objects.filter(
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
    
    # Top opportunities by profit
    top_opportunities = ArbitrageOpportunity.objects.filter(
        created_at__gte=week_ago
    ).select_related(
        'trading_pair', 'buy_exchange', 'sell_exchange'
    ).order_by('-net_profit_percentage')[:5]
    
    # Recent executions
    recent_executions = ArbitrageExecution.objects.filter(
        created_at__gte=week_ago
    ).select_related(
        'opportunity__trading_pair',
        'opportunity__buy_exchange',
        'opportunity__sell_exchange'
    ).order_by('-created_at')[:10]
    
    # Exchange performance chart data
    exchange_performance = []
    for exchange in Exchange.objects.filter(is_active=True):
        performance = ExchangePerformance.objects.filter(
            exchange=exchange,
            date__gte=week_ago.date()
        ).aggregate(
            avg_uptime=Avg('uptime_percentage'),
            total_volume=Sum('total_volume'),
            avg_response=Avg('average_response_time')
        )
        
        exchange_performance.append({
            'name': exchange.name,
            'uptime': round(performance['avg_uptime'] or 0, 2),
            'volume': performance['total_volume'] or 0,
            'response_time': round(performance['avg_response'] or 0, 2),
        })
    
    # Daily profit chart (last 30 days)
    daily_profits = []
    for i in range(30):
        date = today - timedelta(days=i)
        profit = ArbitrageExecution.objects.filter(
            completed_at__date=date,
            status='completed'
        ).aggregate(
            total=Sum('final_profit')
        )['total'] or 0
        
        daily_profits.append({
            'date': date.strftime('%Y-%m-%d'),
            'profit': float(profit),
        })
    
    daily_profits.reverse()  # Show oldest first
    
    # System alerts
    system_alerts = []
    
    # Check for offline exchanges
    offline_exchanges = ExchangeStatus.objects.filter(
        is_online=False
    ).select_related('exchange')
    
    for status in offline_exchanges:
        system_alerts.append({
            'level': 'error',
            'title': f'{status.exchange.name} Offline',
            'message': f'Exchange has been offline since {status.last_check}',
            'timestamp': status.last_check,
        })
    
    # Check for low success rate
    if success_rate < 70:
        system_alerts.append({
            'level': 'warning',
            'title': 'Low Success Rate',
            'message': f'Weekly success rate is {success_rate:.1f}%',
            'timestamp': now,
        })
    
    # Check for stale market data
    stale_tickers = MarketTicker.objects.filter(
        timestamp__lt=now - timedelta(minutes=10)
    ).count()
    
    if stale_tickers > 0:
        system_alerts.append({
            'level': 'warning',
            'title': 'Stale Market Data',
            'message': f'{stale_tickers} tickers have not updated in 10+ minutes',
            'timestamp': now,
        })
    
    # Update context with all dashboard data
    context.update({
        # KPI Metrics
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
        
        # Lists and Charts
        'top_opportunities': top_opportunities,
        'recent_executions': recent_executions,
        'exchange_performance': exchange_performance,
        'daily_profits': daily_profits,
        'system_alerts': system_alerts,
        
        # Metadata
        'dashboard_last_updated': now,
        'dashboard_auto_refresh': True,
    })
    
    return context