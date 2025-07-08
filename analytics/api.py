import logging
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any, Dict, List

from django.db import models
from django.utils import timezone
from ninja import Router, Schema
from ninja.pagination import paginate
from ninja.security import django_auth

from analytics.models import (
    DailyArbitrageSummary,
    ExchangePerformance,
    MarketSnapshot,
    TradingPairAnalytics,
    UserPerformance,
)
from arbitrage.models import ArbitrageExecution, ArbitrageOpportunity
from core.models import Exchange, TradingPair

logger = logging.getLogger(__name__)

router = Router()


class DateRangeSchema(Schema):
    start_date: datetime
    end_date: datetime


class DailySummarySchema(Schema):
    date: str
    total_opportunities: int
    total_executions: int
    successful_executions: int
    failed_executions: int
    total_profit: Decimal
    average_profit_percentage: Decimal
    highest_profit_percentage: Decimal
    top_trading_pair: str = None
    top_route: Dict = {}
    total_volume_traded: Decimal
    market_volatility_index: Decimal = None


class ExchangePerformanceSchema(Schema):
    exchange: str
    date: str
    uptime_percentage: Decimal
    average_response_time: float
    error_count: int
    total_orders_placed: int
    successful_orders: int
    failed_orders: int
    opportunities_as_buy: int
    opportunities_as_sell: int
    total_volume: Decimal


class TradingPairAnalyticsSchema(Schema):
    trading_pair: str
    period_start: datetime
    period_end: datetime
    period_type: str
    total_opportunities: int
    average_spread_percentage: Decimal
    max_spread_percentage: Decimal
    total_executions: int
    success_rate: Decimal
    average_profit: Decimal
    total_volume: Decimal
    price_volatility: Decimal = None
    average_price: Decimal = None
    top_routes: List[Dict]


class MarketOverviewSchema(Schema):
    current_opportunities: int
    active_exchanges: int
    active_trading_pairs: int
    total_volume_24h: Decimal
    average_spread: Decimal
    max_spread: Decimal
    market_trend: str
    top_opportunities: List[Dict]


class InsightSchema(Schema):
    insight_type: str
    title: str
    description: str
    value: Any
    trend: str = None  # "up", "down", "stable"
    recommendation: str = None


@router.get("/overview", response=MarketOverviewSchema)
def get_market_overview(request):
    """
    Get current market overview.
    """
    # Get current opportunities
    current_opportunities = ArbitrageOpportunity.objects.filter(
        status="detected",
        expires_at__gt=timezone.now()
    ).count()
    
    # Get active exchanges
    active_exchanges = Exchange.objects.filter(is_active=True).count()
    
    # Get active trading pairs
    active_pairs = TradingPair.objects.filter(is_active=True).count()
    
    # Get 24h volume
    last_24h = timezone.now() - timedelta(hours=24)
    volume_24h = ArbitrageExecution.objects.filter(
        created_at__gte=last_24h,
        status="completed"
    ).aggregate(
        total=models.Sum(models.F("buy_filled_amount") * models.F("buy_average_price"))
    )["total"] or Decimal("0")
    
    # Get spread statistics
    opportunities = ArbitrageOpportunity.objects.filter(
        status="detected",
        expires_at__gt=timezone.now()
    )
    
    avg_spread = opportunities.aggregate(
        avg=models.Avg("net_profit_percentage")
    )["avg"] or Decimal("0")
    
    max_spread = opportunities.aggregate(
        max=models.Max("net_profit_percentage")
    )["max"] or Decimal("0")
    
    # Get top opportunities
    top_opps = opportunities.order_by("-net_profit_percentage")[:5]
    top_opportunities = [
        {
            "id": str(opp.id),
            "pair": opp.trading_pair.symbol,
            "buy_exchange": opp.buy_exchange.name,
            "sell_exchange": opp.sell_exchange.name,
            "profit_percentage": str(opp.net_profit_percentage),
            "optimal_amount": str(opp.optimal_amount),
        }
        for opp in top_opps
    ]
    
    # Determine market trend
    recent_snapshot = MarketSnapshot.objects.order_by("-timestamp").first()
    market_trend = recent_snapshot.market_trend if recent_snapshot else "neutral"
    
    return {
        "current_opportunities": current_opportunities,
        "active_exchanges": active_exchanges,
        "active_trading_pairs": active_pairs,
        "total_volume_24h": volume_24h,
        "average_spread": avg_spread,
        "max_spread": max_spread,
        "market_trend": market_trend,
        "top_opportunities": top_opportunities,
    }


@router.get("/daily-summaries", response=List[DailySummarySchema])
@paginate
def get_daily_summaries(request, days: int = 30):
    """
    Get daily arbitrage summaries.
    """
    start_date = timezone.now().date() - timedelta(days=days)
    summaries = DailyArbitrageSummary.objects.filter(
        date__gte=start_date
    ).select_related("top_trading_pair")
    
    return summaries


@router.get("/exchange-performance", response=List[ExchangePerformanceSchema])
def get_exchange_performance(request, exchange: str = None, days: int = 7):
    """
    Get exchange performance metrics.
    """
    start_date = timezone.now().date() - timedelta(days=days)
    
    queryset = ExchangePerformance.objects.filter(
        date__gte=start_date
    ).select_related("exchange")
    
    if exchange:
        queryset = queryset.filter(exchange__code=exchange)
    
    return queryset.order_by("-date", "exchange")


@router.get("/trading-pair/{symbol}/analytics", response=TradingPairAnalyticsSchema)
def get_trading_pair_analytics(
    request,
    symbol: str,
    period_type: str = "daily",
    periods: int = 7
):
    """
    Get analytics for a specific trading pair.
    """
    trading_pair = TradingPair.objects.filter(symbol=symbol).first()
    if not trading_pair:
        return {"error": "Trading pair not found"}
    
    # Calculate period
    if period_type == "hourly":
        start_time = timezone.now() - timedelta(hours=periods)
    elif period_type == "daily":
        start_time = timezone.now() - timedelta(days=periods)
    elif period_type == "weekly":
        start_time = timezone.now() - timedelta(weeks=periods)
    else:  # monthly
        start_time = timezone.now() - timedelta(days=periods * 30)
    
    analytics = TradingPairAnalytics.objects.filter(
        trading_pair=trading_pair,
        period_type=period_type,
        period_start__gte=start_time
    ).order_by("-period_start").first()
    
    if not analytics:
        # Generate analytics on the fly
        from analytics.tasks import generate_trading_pair_analytics
        generate_trading_pair_analytics.delay(trading_pair.id, period_type)
        
        return {
            "trading_pair": symbol,
            "period_start": start_time,
            "period_end": timezone.now(),
            "period_type": period_type,
            "total_opportunities": 0,
            "average_spread_percentage": Decimal("0"),
            "max_spread_percentage": Decimal("0"),
            "total_executions": 0,
            "success_rate": Decimal("0"),
            "average_profit": Decimal("0"),
            "total_volume": Decimal("0"),
            "top_routes": [],
        }
    
    return analytics


@router.get("/user/performance", auth=django_auth, response=List[Dict])
def get_user_performance(request, days: int = 30):
    """
    Get user's performance metrics.
    """
    start_date = timezone.now().date() - timedelta(days=days)
    
    performance = UserPerformance.objects.filter(
        user=request.user,
        date__gte=start_date
    ).order_by("-date")
    
    return [
        {
            "date": p.date.isoformat(),
            "total_executions": p.total_executions,
            "successful_executions": p.successful_executions,
            "daily_profit": str(p.daily_profit),
            "net_profit": str(p.net_profit),
            "roi_percentage": str(p.roi_percentage),
            "total_volume": str(p.total_volume_traded),
        }
        for p in performance
    ]


@router.get("/insights", response=List[InsightSchema])
def get_market_insights(request):
    """
    Get AI-generated market insights.
    """
    insights = []
    
    # Insight 1: Most profitable trading pair
    last_7_days = timezone.now() - timedelta(days=7)
    top_pair = (
        ArbitrageOpportunity.objects
        .filter(created_at__gte=last_7_days)
        .values("trading_pair__symbol")
        .annotate(
            avg_profit=models.Avg("net_profit_percentage"),
            count=models.Count("id")
        )
        .order_by("-avg_profit")
        .first()
    )
    
    if top_pair:
        insights.append({
            "insight_type": "top_pair",
            "title": "Most Profitable Trading Pair",
            "description": f"{top_pair['trading_pair__symbol']} has shown the highest average profit",
            "value": {
                "pair": top_pair["trading_pair__symbol"],
                "avg_profit": str(top_pair["avg_profit"]),
                "opportunities": top_pair["count"],
            },
            "trend": "up",
            "recommendation": f"Consider focusing on {top_pair['trading_pair__symbol']} for arbitrage",
        })
    
    # Insight 2: Best exchange route
    top_route = (
        ArbitrageOpportunity.objects
        .filter(created_at__gte=last_7_days)
        .values("buy_exchange__name", "sell_exchange__name")
        .annotate(
            avg_profit=models.Avg("net_profit_percentage"),
            count=models.Count("id")
        )
        .order_by("-avg_profit")
        .first()
    )
    
    if top_route:
        insights.append({
            "insight_type": "top_route",
            "title": "Most Profitable Route",
            "description": f"Buy on {top_route['buy_exchange__name']}, sell on {top_route['sell_exchange__name']}",
            "value": {
                "buy": top_route["buy_exchange__name"],
                "sell": top_route["sell_exchange__name"],
                "avg_profit": str(top_route["avg_profit"]),
                "opportunities": top_route["count"],
            },
            "trend": "stable",
            "recommendation": "This route consistently shows good arbitrage opportunities",
        })
    
    # Insight 3: Market volatility
    recent_opportunities = ArbitrageOpportunity.objects.filter(
        created_at__gte=timezone.now() - timedelta(hours=24)
    ).count()
    
    previous_opportunities = ArbitrageOpportunity.objects.filter(
        created_at__gte=timezone.now() - timedelta(hours=48),
        created_at__lt=timezone.now() - timedelta(hours=24)
    ).count()
    
    if previous_opportunities > 0:
        change_percentage = ((recent_opportunities - previous_opportunities) / previous_opportunities) * 100
        trend = "up" if change_percentage > 0 else "down"
        
        insights.append({
            "insight_type": "volatility",
            "title": "Market Volatility",
            "description": f"Arbitrage opportunities {'increased' if trend == 'up' else 'decreased'} by {abs(change_percentage):.1f}%",
            "value": {
                "current": recent_opportunities,
                "previous": previous_opportunities,
                "change_percentage": change_percentage,
            },
            "trend": trend,
            "recommendation": "Higher volatility typically means more arbitrage opportunities",
        })
    
    # Insight 4: Exchange reliability
    best_exchange = (
        ExchangePerformance.objects
        .filter(date__gte=timezone.now().date() - timedelta(days=7))
        .values("exchange__name")
        .annotate(
            avg_uptime=models.Avg("uptime_percentage"),
            avg_response=models.Avg("average_response_time")
        )
        .order_by("-avg_uptime", "avg_response")
        .first()
    )
    
    if best_exchange:
        insights.append({
            "insight_type": "reliability",
            "title": "Most Reliable Exchange",
            "description": f"{best_exchange['exchange__name']} has the best uptime and response time",
            "value": {
                "exchange": best_exchange["exchange__name"],
                "uptime": str(best_exchange["avg_uptime"]),
                "response_time": best_exchange["avg_response"],
            },
            "trend": "stable",
            "recommendation": "Prioritize this exchange for time-sensitive arbitrage",
        })
    
    return insights


@router.get("/reports/generate", auth=django_auth)
def generate_report(request, report_type: str, date_range: DateRangeSchema):
    """
    Generate custom analytics report.
    """
    from analytics.tasks import generate_custom_report
    
    task = generate_custom_report.delay(
        request.user.id,
        report_type,
        date_range.start_date.isoformat(),
        date_range.end_date.isoformat()
    )
    
    return {
        "success": True,
        "task_id": task.id,
        "message": f"Report generation started. Task ID: {task.id}",
    }


@router.get("/charts/profit-trend")
def get_profit_trend(request, days: int = 30):
    """
    Get profit trend data for charts.
    """
    start_date = timezone.now().date() - timedelta(days=days)
    
    daily_profits = (
        DailyArbitrageSummary.objects
        .filter(date__gte=start_date)
        .order_by("date")
        .values("date", "total_profit", "average_profit_percentage")
    )
    
    return {
        "labels": [p["date"].isoformat() for p in daily_profits],
        "datasets": [
            {
                "label": "Total Profit",
                "data": [float(p["total_profit"]) for p in daily_profits],
            },
            {
                "label": "Average Profit %",
                "data": [float(p["average_profit_percentage"]) for p in daily_profits],
            },
        ],
    }


@router.get("/charts/opportunity-distribution")
def get_opportunity_distribution(request):
    """
    Get opportunity distribution by exchange pairs.
    """
    last_7_days = timezone.now() - timedelta(days=7)
    
    distribution = (
        ArbitrageOpportunity.objects
        .filter(created_at__gte=last_7_days)
        .values("buy_exchange__name", "sell_exchange__name")
        .annotate(count=models.Count("id"))
        .order_by("-count")[:10]
    )
    
    return {
        "labels": [f"{d['buy_exchange__name']} → {d['sell_exchange__name']}" for d in distribution],
        "data": [d["count"] for d in distribution],
    }