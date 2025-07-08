import os
import json
import logging
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, Any, Optional

from django.conf import settings
from django.core.cache import cache
from django.utils import timezone


logger = logging.getLogger(__name__)


def get_environment_label(request=None) -> str:
    """
    Return environment label for admin interface.
    """
    if getattr(settings, 'DEBUG', False):
        return "Development"
    return "Production"


def format_currency(amount: Decimal, currency: str = "USD", decimals: int = 2) -> str:
    """
    Format currency amount with proper symbol and decimals.
    """
    symbols = {
        "USD": "$",
        "EUR": "€",
        "BTC": "₿",
        "ETH": "Ξ",
        "RLS": "﷼",
    }
    
    symbol = symbols.get(currency.upper(), currency.upper() + " ")
    return f"{symbol}{amount:,.{decimals}f}"


def format_percentage(percentage: Decimal, decimals: int = 2) -> str:
    """
    Format percentage with appropriate styling.
    """
    return f"{percentage:.{decimals}f}%"


def format_relative_time(timestamp: datetime) -> str:
    """
    Format timestamp as relative time (e.g., "2 minutes ago").
    """
    now = timezone.now()
    diff = now - timestamp
    
    seconds = int(diff.total_seconds())
    
    if seconds < 60:
        return f"{seconds}s ago"
    elif seconds < 3600:
        minutes = seconds // 60
        return f"{minutes}m ago"
    elif seconds < 86400:
        hours = seconds // 3600
        return f"{hours}h ago"
    else:
        days = seconds // 86400
        return f"{days}d ago"


def calculate_profit_class(profit_percentage: Decimal) -> str:
    """
    Return CSS class for profit percentage styling.
    """
    if profit_percentage >= 2.0:
        return "high-profit"
    elif profit_percentage >= 1.0:
        return "medium-profit"
    else:
        return "low-profit"


def get_exchange_status_color(is_online: bool, response_time: float = None) -> str:
    """
    Get color class for exchange status indicator.
    """
    if not is_online:
        return "red"
    
    if response_time:
        if response_time < 0.1:  # 100ms
            return "green"
        elif response_time < 0.5:  # 500ms
            return "yellow"
        else:
            return "orange"
    
    return "green"


def cache_market_data(key: str, data: Dict[str, Any], timeout: int = 300) -> None:
    """
    Cache market data with appropriate timeout.
    """
    try:
        cache.set(f"market_data:{key}", data, timeout)
    except Exception as e:
        logger.error(f"Failed to cache market data: {e}")


def get_cached_market_data(key: str) -> Optional[Dict[str, Any]]:
    """
    Retrieve cached market data.
    """
    try:
        return cache.get(f"market_data:{key}")
    except Exception as e:
        logger.error(f"Failed to retrieve cached market data: {e}")
        return None


def validate_trading_pair_symbol(symbol: str) -> bool:
    """
    Validate trading pair symbol format.
    """
    # Basic validation - should be improved based on requirements
    if not symbol or len(symbol) < 6:
        return False
    
    # Should contain valid characters
    if not symbol.replace("/", "").replace("-", "").replace("_", "").isalnum():
        return False
    
    return True


def calculate_arbitrage_metrics(buy_price: Decimal, sell_price: Decimal, 
                              buy_fee: Decimal, sell_fee: Decimal) -> Dict[str, Decimal]:
    """
    Calculate arbitrage opportunity metrics.
    """
    gross_profit = sell_price - buy_price
    gross_profit_percentage = (gross_profit / buy_price) * 100
    
    net_profit = gross_profit - buy_fee - sell_fee
    net_profit_percentage = (net_profit / buy_price) * 100
    
    return {
        "gross_profit": gross_profit,
        "gross_profit_percentage": gross_profit_percentage,
        "net_profit": net_profit,
        "net_profit_percentage": net_profit_percentage,
        "total_fees": buy_fee + sell_fee,
    }


def generate_dashboard_chart_data(days: int = 7) -> Dict[str, Any]:
    """
    Generate chart data for dashboard.
    """
    from arbitrage.models import ArbitrageExecution
    
    end_date = timezone.now().date()
    start_date = end_date - timedelta(days=days-1)
    
    chart_data = {
        "labels": [],
        "profit_data": [],
        "opportunity_data": [],
    }
    
    for i in range(days):
        date = start_date + timedelta(days=i)
        chart_data["labels"].append(date.strftime("%m/%d"))
        
        # Get daily profit
        daily_executions = ArbitrageExecution.objects.filter(
            completed_at__date=date,
            status='completed'
        )
        
        daily_profit = sum([
            execution.final_profit for execution in daily_executions 
            if execution.final_profit
        ]) or Decimal('0')
        
        chart_data["profit_data"].append(float(daily_profit))
        chart_data["opportunity_data"].append(daily_executions.count())
    
    return chart_data


def get_system_health_metrics() -> Dict[str, Any]:
    """
    Get comprehensive system health metrics.
    """
    from exchanges.models import ExchangeStatus
    from arbitrage.models import ArbitrageOpportunity
    
    # Exchange health
    online_exchanges = ExchangeStatus.objects.filter(is_online=True).count()
    total_exchanges = ExchangeStatus.objects.count()
    
    # Active opportunities
    active_opportunities = ArbitrageOpportunity.objects.filter(
        status='detected',
        expires_at__gt=timezone.now()
    ).count()
    
    # Database health (simple check)
    db_healthy = True
    try:
        ExchangeStatus.objects.first()
    except Exception:
        db_healthy = False
    
    # Redis health
    redis_healthy = True
    try:
        cache.set('health_check', 'ok', 1)
        redis_healthy = cache.get('health_check') == 'ok'
    except Exception:
        redis_healthy = False
    
    return {
        "exchanges": {
            "online": online_exchanges,
            "total": total_exchanges,
            "health_percentage": (online_exchanges / total_exchanges * 100) if total_exchanges else 0,
        },
        "opportunities": {
            "active": active_opportunities,
        },
        "infrastructure": {
            "database": db_healthy,
            "redis": redis_healthy,
        },
        "overall_health": all([
            online_exchanges > 0,
            db_healthy,
            redis_healthy,
        ]),
    }


def log_admin_action(user, action: str, object_repr: str, change_message: str = "") -> None:
    """
    Log admin actions for audit trail.
    """
    from django.contrib.admin.models import LogEntry, ADDITION, CHANGE, DELETION
    from django.contrib.contenttypes.models import ContentType
    
    action_map = {
        "create": ADDITION,
        "update": CHANGE,
        "delete": DELETION,
    }
    
    try:
        LogEntry.objects.log_action(
            user_id=user.id,
            content_type_id=None,
            object_id=None,
            object_repr=object_repr,
            action_flag=action_map.get(action, CHANGE),
            change_message=change_message,
        )
    except Exception as e:
        logger.error(f"Failed to log admin action: {e}")


def export_arbitrage_data(queryset, format: str = "csv") -> str:
    """
    Export arbitrage data to various formats.
    """
    import csv
    import io
    
    if format.lower() == "csv":
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Write headers
        headers = [
            "ID", "Trading Pair", "Buy Exchange", "Sell Exchange",
            "Buy Price", "Sell Price", "Profit %", "Status", "Created At"
        ]
        writer.writerow(headers)
        
        # Write data
        for opportunity in queryset:
            writer.writerow([
                str(opportunity.id),
                opportunity.trading_pair.symbol,
                opportunity.buy_exchange.name,
                opportunity.sell_exchange.name,
                str(opportunity.buy_price),
                str(opportunity.sell_price),
                str(opportunity.net_profit_percentage),
                opportunity.status,
                opportunity.created_at.strftime("%Y-%m-%d %H:%M:%S"),
            ])
        
        return output.getvalue()
    
    return ""


def validate_admin_config() -> Dict[str, bool]:
    """
    Validate admin configuration and return status.
    """
    checks = {
        "unfold_installed": "unfold" in settings.INSTALLED_APPS,
        "dashboard_callback_configured": hasattr(settings, 'UNFOLD') and 
                                       settings.UNFOLD.get('DASHBOARD_CALLBACK') is not None,
        "static_files_configured": hasattr(settings, 'STATIC_URL'),
        "redis_available": False,
        "database_accessible": False,
    }
    
    # Test Redis
    try:
        cache.set('config_test', 'ok', 1)
        checks["redis_available"] = cache.get('config_test') == 'ok'
    except Exception:
        pass
    
    # Test Database
    try:
        from django.db import connection
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        checks["database_accessible"] = True
    except Exception:
        pass
    
    return checks