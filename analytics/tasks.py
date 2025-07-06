import logging
from datetime import datetime, timedelta
from decimal import Decimal

from celery import shared_task
from django.db import models, transaction
from django.utils import timezone

from analytics.models import (
    DailyArbitrageSummary,
    ExchangePerformance,
    MarketSnapshot,
    TradingPairAnalytics,
    UserPerformance,
)
from arbitrage.models import ArbitrageExecution, ArbitrageOpportunity
from core.models import Exchange, TradingPair
from exchanges.models import ExchangeStatus, MarketTicker
from trading.models import Order, Position

logger = logging.getLogger(__name__)


@shared_task
def generate_daily_analytics():
    """
    Generate daily analytics summaries.
    """
    yesterday = timezone.now().date() - timedelta(days=1)
    
    # Generate daily arbitrage summary
    generate_daily_arbitrage_summary(yesterday)
    
    # Generate exchange performance metrics
    for exchange in Exchange.objects.filter(is_active=True):
        generate_exchange_performance(exchange.id, yesterday)
    
    # Generate user performance metrics
    from django.contrib.auth.models import User
    for user in User.objects.filter(is_active=True):
        generate_user_performance(user.id, yesterday)
    
    # Generate trading pair analytics
    for pair in TradingPair.objects.filter(is_active=True):
        generate_trading_pair_analytics.delay(pair.id, "daily")
    
    logger.info(f"Generated daily analytics for {yesterday}")


def generate_daily_arbitrage_summary(date):
    """
    Generate daily arbitrage summary.
    """
    start_time = timezone.make_aware(
        datetime.combine(date, datetime.min.time())
    )
    end_time = start_time + timedelta(days=1)
    
    # Get opportunities for the day
    opportunities = ArbitrageOpportunity.objects.filter(
        created_at__gte=start_time,
        created_at__lt=end_time
    )
    
    # Get executions for the day
    executions = ArbitrageExecution.objects.filter(
        created_at__gte=start_time,
        created_at__lt=end_time
    )
    
    # Calculate metrics
    total_opportunities = opportunities.count()
    total_executions = executions.count()
    successful_executions = executions.filter(status="completed").count()
    failed_executions = executions.filter(status="failed").count()
    
    # Profit metrics
    completed_executions = executions.filter(status="completed")
    total_profit = completed_executions.aggregate(
        total=models.Sum("final_profit")
    )["total"] or Decimal("0")
    
    avg_profit_percentage = completed_executions.aggregate(
        avg=models.Avg("profit_percentage")
    )["avg"] or Decimal("0")
    
    highest_profit = opportunities.aggregate(
        max=models.Max("net_profit_percentage")
    )["max"] or Decimal("0")
    
    # Top trading pair
    top_pair_data = (
        opportunities
        .values("trading_pair")
        .annotate(count=models.Count("id"))
        .order_by("-count")
        .first()
    )
    
    top_pair = None
    if top_pair_data:
        top_pair = TradingPair.objects.get(id=top_pair_data["trading_pair"])
    
    # Top route
    top_route_data = (
        opportunities
        .values("buy_exchange__name", "sell_exchange__name")
        .annotate(
            count=models.Count("id"),
            avg_profit=models.Avg("net_profit_percentage")
        )
        .order_by("-avg_profit")
        .first()
    )
    
    top_route = {}
    if top_route_data:
        top_route = {
            "buy": top_route_data["buy_exchange__name"],
            "sell": top_route_data["sell_exchange__name"],
            "count": top_route_data["count"],
            "avg_profit": str(top_route_data["avg_profit"])
        }
    
    # Volume traded
    total_volume = completed_executions.aggregate(
        volume=models.Sum(
            models.F("buy_filled_amount") * models.F("buy_average_price")
        )
    )["volume"] or Decimal("0")
    
    # Create or update summary
    DailyArbitrageSummary.objects.update_or_create(
        date=date,
        defaults={
            "total_opportunities": total_opportunities,
            "total_executions": total_executions,
            "successful_executions": successful_executions,
            "failed_executions": failed_executions,
            "total_profit": total_profit,
            "average_profit_percentage": avg_profit_percentage,
            "highest_profit_percentage": highest_profit,
            "top_trading_pair": top_pair,
            "top_route": top_route,
            "total_volume_traded": total_volume,
        }
    )


def generate_exchange_performance(exchange_id: int, date):
    """
    Generate exchange performance metrics.
    """
    exchange = Exchange.objects.get(id=exchange_id)
    
    start_time = timezone.make_aware(
        datetime.combine(date, datetime.min.time())
    )
    end_time = start_time + timedelta(days=1)
    
    # Get exchange status records
    status_records = ExchangeStatus.objects.filter(
        exchange=exchange,
        last_check__gte=start_time,
        last_check__lt=end_time
    )
    
    # Calculate uptime
    total_checks = status_records.count()
    online_checks = status_records.filter(is_online=True).count()
    uptime_percentage = (online_checks / total_checks * 100) if total_checks > 0 else 0
    
    # Average response time
    avg_response_time = status_records.filter(
        response_time__isnull=False
    ).aggregate(
        avg=models.Avg("response_time")
    )["avg"] or 0
    
    # Error count
    error_count = status_records.filter(is_online=False).count()
    
    # Trading metrics
    orders = Order.objects.filter(
        exchange=exchange,
        created_at__gte=start_time,
        created_at__lt=end_time
    )
    
    total_orders = orders.count()
    successful_orders = orders.filter(status="FILLED").count()
    failed_orders = orders.filter(
        status__in=["REJECTED", "EXPIRED", "FAILED"]
    ).count()
    
    # Arbitrage metrics
    opportunities_buy = ArbitrageOpportunity.objects.filter(
        buy_exchange=exchange,
        created_at__gte=start_time,
        created_at__lt=end_time
    ).count()
    
    opportunities_sell = ArbitrageOpportunity.objects.filter(
        sell_exchange=exchange,
        created_at__gte=start_time,
        created_at__lt=end_time
    ).count()
    
    # Volume
    total_volume = orders.filter(status="FILLED").aggregate(
        volume=models.Sum(models.F("filled_amount") * models.F("average_price"))
    )["volume"] or Decimal("0")
    
    # Create or update performance record
    ExchangePerformance.objects.update_or_create(
        exchange=exchange,
        date=date,
        defaults={
            "uptime_percentage": uptime_percentage,
            "average_response_time": avg_response_time,
            "error_count": error_count,
            "total_orders_placed": total_orders,
            "successful_orders": successful_orders,
            "failed_orders": failed_orders,
            "opportunities_as_buy": opportunities_buy,
            "opportunities_as_sell": opportunities_sell,
            "total_volume": total_volume,
        }
    )


def generate_user_performance(user_id: int, date):
    """
    Generate user performance metrics.
    """
    from django.contrib.auth.models import User
    user = User.objects.get(id=user_id)
    
    start_time = timezone.make_aware(
        datetime.combine(date, datetime.min.time())
    )
    end_time = start_time + timedelta(days=1)
    
    # Execution metrics
    executions = ArbitrageExecution.objects.filter(
        user=user,
        created_at__gte=start_time,
        created_at__lt=end_time
    )
    
    total_executions = executions.count()
    successful_executions = executions.filter(status="completed").count()
    failed_executions = executions.filter(status="failed").count()
    
    # Profit metrics
    daily_profit = executions.filter(
        status="completed",
        final_profit__gt=0
    ).aggregate(
        total=models.Sum("final_profit")
    )["total"] or Decimal("0")
    
    daily_loss = executions.filter(
        status="completed",
        final_profit__lt=0
    ).aggregate(
        total=models.Sum("final_profit")
    )["total"] or Decimal("0")
    
    net_profit = daily_profit + daily_loss  # loss is negative
    
    # Volume and fees
    total_volume = executions.filter(status="completed").aggregate(
        volume=models.Sum(
            models.F("buy_filled_amount") * models.F("buy_average_price")
        )
    )["volume"] or Decimal("0")
    
    total_fees = executions.filter(status="completed").aggregate(
        fees=models.Sum(models.F("buy_fee_paid") + models.F("sell_fee_paid"))
    )["fees"] or Decimal("0")
    
    # ROI calculation (simplified)
    roi_percentage = (net_profit / total_volume * 100) if total_volume > 0 else Decimal("0")
    
    # Create or update performance record
    UserPerformance.objects.update_or_create(
        user=user,
        date=date,
        defaults={
            "total_executions": total_executions,
            "successful_executions": successful_executions,
            "failed_executions": failed_executions,
            "daily_profit": daily_profit,
            "daily_loss": abs(daily_loss),
            "net_profit": net_profit,
            "roi_percentage": roi_percentage,
            "total_volume_traded": total_volume,
            "total_fees_paid": total_fees,
        }
    )


@shared_task
def generate_trading_pair_analytics(pair_id: int, period_type: str = "daily"):
    """
    Generate analytics for a trading pair.
    """
    pair = TradingPair.objects.get(id=pair_id)
    
    # Determine period
    now = timezone.now()
    if period_type == "hourly":
        period_start = now.replace(minute=0, second=0, microsecond=0)
        period_end = period_start + timedelta(hours=1)
    elif period_type == "daily":
        period_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        period_end = period_start + timedelta(days=1)
    elif period_type == "weekly":
        period_start = now - timedelta(days=now.weekday())
        period_start = period_start.replace(hour=0, minute=0, second=0, microsecond=0)
        period_end = period_start + timedelta(weeks=1)
    else:  # monthly
        period_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        if now.month == 12:
            period_end = period_start.replace(year=now.year + 1, month=1)
        else:
            period_end = period_start.replace(month=now.month + 1)
    
    # Get opportunities
    opportunities = ArbitrageOpportunity.objects.filter(
        trading_pair=pair,
        created_at__gte=period_start,
        created_at__lt=period_end
    )
    
    # Calculate metrics
    total_opportunities = opportunities.count()
    
    avg_spread = opportunities.aggregate(
        avg=models.Avg("net_profit_percentage")
    )["avg"] or Decimal("0")
    
    max_spread = opportunities.aggregate(
        max=models.Max("net_profit_percentage")
    )["max"] or Decimal("0")
    
    # Execution metrics
    executions = ArbitrageExecution.objects.filter(
        opportunity__trading_pair=pair,
        created_at__gte=period_start,
        created_at__lt=period_end
    )
    
    total_executions = executions.count()
    successful = executions.filter(status="completed").count()
    success_rate = (successful / total_executions * 100) if total_executions > 0 else Decimal("0")
    
    # Average profit
    avg_profit = executions.filter(status="completed").aggregate(
        avg=models.Avg("final_profit")
    )["avg"] or Decimal("0")
    
    # Volume
    total_volume = executions.filter(status="completed").aggregate(
        volume=models.Sum(
            models.F("buy_filled_amount") * models.F("buy_average_price")
        )
    )["volume"] or Decimal("0")
    
    # Top routes
    top_routes = (
        opportunities
        .values("buy_exchange__name", "sell_exchange__name")
        .annotate(
            count=models.Count("id"),
            avg_profit=models.Avg("net_profit_percentage")
        )
        .order_by("-count")[:5]
    )
    
    top_routes_list = [
        {
            "buy": route["buy_exchange__name"],
            "sell": route["sell_exchange__name"],
            "count": route["count"],
            "avg_profit": str(route["avg_profit"])
        }
        for route in top_routes
    ]
    
    # Create or update analytics
    TradingPairAnalytics.objects.update_or_create(
        trading_pair=pair,
        period_start=period_start,
        period_type=period_type,
        defaults={
            "period_end": period_end,
            "total_opportunities": total_opportunities,
            "average_spread_percentage": avg_spread,
            "max_spread_percentage": max_spread,
            "total_executions": total_executions,
            "success_rate": success_rate,
            "average_profit": avg_profit,
            "total_volume": total_volume,
            "top_routes": top_routes_list,
        }
    )


@shared_task
def capture_market_snapshot():
    """
    Capture current market snapshot.
    """
    now = timezone.now()
    
    # Market overview
    active_exchanges = Exchange.objects.filter(is_active=True).count()
    active_pairs = TradingPair.objects.filter(is_active=True).count()
    
    # Current opportunities
    active_opportunities = ArbitrageOpportunity.objects.filter(
        status="detected",
        expires_at__gt=now
    )
    
    opportunity_count = active_opportunities.count()
    
    avg_spread = active_opportunities.aggregate(
        avg=models.Avg("net_profit_percentage")
    )["avg"] or Decimal("0")
    
    max_spread = active_opportunities.aggregate(
        max=models.Max("net_profit_percentage")
    )["max"] or Decimal("0")
    
    # Top opportunities
    top_opps = active_opportunities.order_by("-net_profit_percentage")[:10]
    top_opportunities = [
        {
            "pair": opp.trading_pair.symbol,
            "buy": opp.buy_exchange.name,
            "sell": opp.sell_exchange.name,
            "profit": str(opp.net_profit_percentage),
            "amount": str(opp.optimal_amount)
        }
        for opp in top_opps
    ]
    
    # Total volume (last hour)
    last_hour = now - timedelta(hours=1)
    total_volume = MarketTicker.objects.filter(
        timestamp__gte=last_hour
    ).aggregate(
        volume=models.Sum("volume_24h")
    )["volume"] or Decimal("0")
    
    # Exchange status
    exchange_status = {}
    for exchange in Exchange.objects.filter(is_active=True):
        status = ExchangeStatus.objects.filter(exchange=exchange).first()
        if status:
            exchange_status[exchange.name] = {
                "online": status.is_online,
                "response_time": status.response_time,
                "last_check": status.last_check.isoformat()
            }
    
    # Determine market trend (simplified)
    if avg_spread > Decimal("2"):
        market_trend = "volatile"
    elif opportunity_count > 100:
        market_trend = "bullish"
    elif opportunity_count < 20:
        market_trend = "bearish"
    else:
        market_trend = "neutral"
    
    # Create snapshot
    MarketSnapshot.objects.create(
        timestamp=now,
        total_market_volume=total_volume,
        active_trading_pairs=active_pairs,
        active_exchanges=active_exchanges,
        active_opportunities=opportunity_count,
        average_spread=avg_spread,
        max_spread=max_spread,
        top_opportunities=top_opportunities,
        market_trend=market_trend,
        exchange_status=exchange_status
    )


@shared_task
def generate_custom_report(user_id: int, report_type: str, start_date: str, end_date: str):
    """
    Generate custom analytics report for user.
    """
    # This would generate PDF/Excel reports
    # Implementation depends on specific requirements
    logger.info(f"Generating {report_type} report for user {user_id}")
    return {"status": "Report generation completed"}


@shared_task
def test_api_credential(credential_id: int):
    """
    Test API credential validity.
    """
    from core.models import APICredential
    from exchanges.services.nobitex import NobitexService
    from exchanges.services.ramzinex import RamzinexService
    from exchanges.services.wallex import WallexService
    
    try:
        credential = APICredential.objects.get(id=credential_id)
        
        # Get service
        services = {
            "nobitex": NobitexService,
            "wallex": WallexService,
            "ramzinex": RamzinexService,
        }
        
        service_class = services.get(credential.exchange.code)
        if not service_class:
            return {"success": False, "error": "Exchange not supported"}
        
        # Test by getting balance
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            async def test():
                async with service_class(
                    credential.exchange,
                    credential.api_key,
                    credential.api_secret
                ) as service:
                    balances = await service.get_balance()
                    return len(balances) > 0
            
            success = loop.run_until_complete(test())
            
            # Update last used
            if success:
                credential.last_used = timezone.now()
                credential.save()
            
            return {"success": success}
            
        finally:
            loop.close()
            
    except Exception as e:
        logger.error(f"Error testing credential {credential_id}: {e}")
        return {"success": False, "error": str(e)}