"""
Django Ninja API endpoints for arbitrage operations.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from decimal import Decimal
from typing import List, Optional
from uuid import UUID

from django.db import transaction
from django.shortcuts import get_object_or_404
from ninja import Router
from ninja.pagination import paginate
from ninja.security import django_auth

from arbitrage.engine import ArbitrageEngine
from arbitrage.models import (
    ArbitrageAlert,
    ArbitrageConfig,
    ArbitrageExecution,
    ArbitrageOpportunity,
)
from arbitrage.schemas import (
    ArbitrageAlertSchema,
    ArbitrageConfigSchema,
    ArbitrageConfigUpdateSchema,
    ArbitrageExecutionSchema,
    ArbitrageHistoryFilterSchema,
    ArbitrageOpportunitySchema,
    ArbitrageScanRequestSchema,
    ArbitrageScanResultSchema,
    ArbitrageStatsSchema,
    ExecuteArbitrageSchema,
)
from arbitrage.tasks import execute_arbitrage_opportunity
from core.models import Exchange, TradingPair

logger = logging.getLogger(__name__)

router = Router()


@router.get("/opportunities", response=List[ArbitrageOpportunitySchema])
@paginate
def list_opportunities(
    request,
    status: Optional[str] = None,
    min_profit: Optional[float] = None,
    exchange: Optional[str] = None,
):
    """
    List arbitrage opportunities with optional filters.
    """
    queryset = ArbitrageOpportunity.objects.select_related(
        "trading_pair",
        "trading_pair__base_currency",
        "trading_pair__quote_currency",
        "buy_exchange",
        "sell_exchange",
    )
    
    # Apply filters
    if status:
        queryset = queryset.filter(status=status)
    else:
        # Default to active opportunities
        queryset = queryset.filter(
            status="detected",
            expires_at__gt=datetime.now()
        )
    
    if min_profit:
        queryset = queryset.filter(net_profit_percentage__gte=min_profit)
    
    if exchange:
        queryset = queryset.filter(
            models.Q(buy_exchange__code=exchange) |
            models.Q(sell_exchange__code=exchange)
        )
    
    # Apply user config filters if authenticated
    if request.user.is_authenticated:
        try:
            config = request.user.arbitrage_config
            queryset = queryset.filter(
                net_profit_percentage__gte=config.min_profit_percentage
            )
            
            if config.enabled_exchanges.exists():
                queryset = queryset.filter(
                    buy_exchange__in=config.enabled_exchanges.all(),
                    sell_exchange__in=config.enabled_exchanges.all()
                )
            
            if config.enabled_pairs.exists():
                queryset = queryset.filter(
                    trading_pair__in=config.enabled_pairs.all()
                )
        except ArbitrageConfig.DoesNotExist:
            pass
    
    return queryset.order_by("-net_profit_percentage", "-created_at")


@router.get("/opportunities/{opportunity_id}", response=ArbitrageOpportunitySchema)
def get_opportunity(request, opportunity_id: UUID):
    """
    Get details of a specific arbitrage opportunity.
    """
    opportunity = get_object_or_404(
        ArbitrageOpportunity.objects.select_related(
            "trading_pair",
            "buy_exchange",
            "sell_exchange"
        ),
        id=opportunity_id
    )
    return opportunity


@router.post("/opportunities/scan", response=ArbitrageScanResultSchema)
async def scan_opportunities(request, scan_request: ArbitrageScanRequestSchema):
    """
    Manually trigger an arbitrage scan.
    """
    start_time = datetime.now()
    engine = ArbitrageEngine()
    
    # Get exchanges and pairs to scan
    exchanges = None
    pairs = None
    
    if scan_request.exchanges:
        exchanges = list(Exchange.objects.filter(
            code__in=scan_request.exchanges,
            is_active=True
        ))
    
    if scan_request.trading_pairs:
        pairs = list(TradingPair.objects.filter(
            symbol__in=scan_request.trading_pairs,
            is_active=True
        ))
    
    # Get user config if authenticated
    user_config = None
    if request.user.is_authenticated:
        try:
            user_config = request.user.arbitrage_config
            if scan_request.min_profit_percentage:
                # Override config for this scan
                user_config.min_profit_percentage = scan_request.min_profit_percentage
        except ArbitrageConfig.DoesNotExist:
            pass
    
    # Scan for opportunities
    try:
        opportunities = await engine.scan_all_opportunities(
            user_config=user_config,
            enabled_exchanges=exchanges,
            enabled_pairs=pairs
        )
        
        # Save opportunities to database
        saved_opportunities = []
        with transaction.atomic():
            for opp in opportunities:
                opp.save()
                saved_opportunities.append(opp)
        
        scan_duration = (datetime.now() - start_time).total_seconds()
        
        return {
            "opportunities_found": len(saved_opportunities),
            "scan_duration": scan_duration,
            "opportunities": saved_opportunities,
            "errors": []
        }
        
    except Exception as e:
        logger.error(f"Error scanning opportunities: {e}")
        return {
            "opportunities_found": 0,
            "scan_duration": 0,
            "opportunities": [],
            "errors": [str(e)]
        }


@router.post("/opportunities/{opportunity_id}/execute", 
            auth=django_auth,
            response=ArbitrageExecutionSchema)
def execute_opportunity(request, opportunity_id: UUID, data: ExecuteArbitrageSchema):
    """
    Execute an arbitrage opportunity.
    """
    opportunity = get_object_or_404(
        ArbitrageOpportunity,
        id=opportunity_id,
        status="detected"
    )
    
    # Check if opportunity is still valid
    if opportunity.expires_at < datetime.now():
        return {"error": "Opportunity has expired"}
    
    # Get user config
    try:
        config = request.user.arbitrage_config
        if not config.is_active:
            return {"error": "Arbitrage trading is disabled for your account"}
    except ArbitrageConfig.DoesNotExist:
        return {"error": "Please configure your arbitrage settings first"}
    
    # Create execution record
    execution = ArbitrageExecution.objects.create(
        opportunity=opportunity,
        user=request.user,
        status="pending"
    )
    
    # Update opportunity status
    opportunity.status = "executing"
    opportunity.save()
    
    # Trigger async execution
    amount = data.amount or opportunity.optimal_amount
    use_market_orders = data.use_market_orders or config.use_market_orders
    
    execute_arbitrage_opportunity.delay(
        execution.id,
        amount,
        use_market_orders
    )
    
    return execution


@router.get("/executions", auth=django_auth, response=List[ArbitrageExecutionSchema])
@paginate
def list_executions(request, status: Optional[str] = None):
    """
    List user's arbitrage executions.
    """
    queryset = ArbitrageExecution.objects.filter(
        user=request.user
    ).select_related(
        "opportunity",
        "opportunity__trading_pair",
        "opportunity__buy_exchange",
        "opportunity__sell_exchange"
    )
    
    if status:
        queryset = queryset.filter(status=status)
    
    return queryset.order_by("-created_at")


@router.get("/executions/{execution_id}", 
           auth=django_auth, 
           response=ArbitrageExecutionSchema)
def get_execution(request, execution_id: UUID):
    """
    Get details of a specific execution.
    """
    execution = get_object_or_404(
        ArbitrageExecution,
        id=execution_id,
        user=request.user
    )
    return execution


@router.get("/config", auth=django_auth, response=ArbitrageConfigSchema)
def get_config(request):
    """
    Get user's arbitrage configuration.
    """
    config, created = ArbitrageConfig.objects.get_or_create(
        user=request.user,
        defaults={
            "min_profit_percentage": Decimal("0.5"),
            "min_profit_amount": Decimal("10"),
            "max_exposure_percentage": Decimal("10"),
            "stop_loss_percentage": Decimal("2"),
        }
    )
    
    return {
        "is_active": config.is_active,
        "auto_trade": config.auto_trade,
        "min_profit_percentage": config.min_profit_percentage,
        "min_profit_amount": config.min_profit_amount,
        "max_trade_amount": config.max_trade_amount,
        "daily_trade_limit": config.daily_trade_limit,
        "max_exposure_percentage": config.max_exposure_percentage,
        "stop_loss_percentage": config.stop_loss_percentage,
        "enable_notifications": config.enable_notifications,
        "notification_channels": config.notification_channels,
        "enabled_exchanges": [e.code for e in config.enabled_exchanges.all()],
        "enabled_pairs": [p.symbol for p in config.enabled_pairs.all()],
        "use_market_orders": config.use_market_orders,
        "slippage_tolerance": config.slippage_tolerance,
    }


@router.patch("/config", auth=django_auth, response=ArbitrageConfigSchema)
def update_config(request, data: ArbitrageConfigUpdateSchema):
    """
    Update user's arbitrage configuration.
    """
    config, created = ArbitrageConfig.objects.get_or_create(user=request.user)
    
    # Update fields
    for field, value in data.dict(exclude_unset=True).items():
        if field == "enabled_exchanges" and value is not None:
            exchanges = Exchange.objects.filter(code__in=value)
            config.enabled_exchanges.set(exchanges)
        elif field == "enabled_pairs" and value is not None:
            pairs = TradingPair.objects.filter(symbol__in=value)
            config.enabled_pairs.set(pairs)
        elif value is not None:
            setattr(config, field, value)
    
    config.save()
    
    return get_config(request)


@router.get("/alerts", auth=django_auth, response=List[ArbitrageAlertSchema])
@paginate
def list_alerts(request, unread_only: bool = False):
    """
    List user's arbitrage alerts.
    """
    queryset = ArbitrageAlert.objects.filter(user=request.user)
    
    if unread_only:
        queryset = queryset.filter(is_read=False)
    
    return queryset.order_by("-created_at")


@router.post("/alerts/{alert_id}/read", auth=django_auth)
def mark_alert_read(request, alert_id: int):
    """
    Mark an alert as read.
    """
    alert = get_object_or_404(
        ArbitrageAlert,
        id=alert_id,
        user=request.user
    )
    alert.is_read = True
    alert.save()
    
    return {"success": True}


@router.post("/alerts/read-all", auth=django_auth)
def mark_all_alerts_read(request):
    """
    Mark all alerts as read.
    """
    ArbitrageAlert.objects.filter(
        user=request.user,
        is_read=False
    ).update(is_read=True)
    
    return {"success": True}


@router.get("/stats", auth=django_auth, response=ArbitrageStatsSchema)
def get_stats(request, period: str = "24h"):
    """
    Get arbitrage statistics for the user.
    """
    # Parse period
    if period == "24h":
        start_date = datetime.now() - timedelta(hours=24)
    elif period == "7d":
        start_date = datetime.now() - timedelta(days=7)
    elif period == "30d":
        start_date = datetime.now() - timedelta(days=30)
    else:
        start_date = None
    
    # Get user executions
    executions = ArbitrageExecution.objects.filter(user=request.user)
    if start_date:
        executions = executions.filter(created_at__gte=start_date)
    
    # Calculate stats
    total_executions = executions.count()
    completed_executions = executions.filter(status="completed")
    successful_executions = completed_executions.filter(final_profit__gt=0)
    
    total_profit = completed_executions.aggregate(
        total=models.Sum("final_profit")
    )["total"] or Decimal("0")
    
    avg_profit_percentage = completed_executions.aggregate(
        avg=models.Avg("profit_percentage")
    )["avg"] or Decimal("0")
    
    success_rate = (
        (successful_executions.count() / total_executions * 100)
        if total_executions > 0 else Decimal("0")
    )
    
    # Get active opportunities
    active_opportunities = ArbitrageOpportunity.objects.filter(
        status="detected",
        expires_at__gt=datetime.now()
    ).count()
    
    # Get total opportunities (including expired)
    total_opportunities = ArbitrageOpportunity.objects.count()
    if start_date:
        total_opportunities = ArbitrageOpportunity.objects.filter(
            created_at__gte=start_date
        ).count()
    
    # Get top profitable pairs
    top_pairs = (
        ArbitrageOpportunity.objects
        .values("trading_pair__symbol")
        .annotate(
            count=models.Count("id"),
            avg_profit=models.Avg("net_profit_percentage")
        )
        .order_by("-avg_profit")[:5]
    )
    
    # Get top profitable routes
    top_routes = (
        ArbitrageOpportunity.objects
        .values("buy_exchange__name", "sell_exchange__name")
        .annotate(
            count=models.Count("id"),
            avg_profit=models.Avg("net_profit_percentage")
        )
        .order_by("-avg_profit")[:5]
    )
    
    return {
        "total_opportunities_detected": total_opportunities,
        "total_opportunities_executed": total_executions,
        "total_profit": total_profit,
        "average_profit_percentage": avg_profit_percentage,
        "success_rate": success_rate,
        "active_opportunities": active_opportunities,
        "top_profitable_pairs": list(top_pairs),
        "top_profitable_routes": [
            {
                "route": f"{r['buy_exchange__name']} -> {r['sell_exchange__name']}",
                "count": r["count"],
                "avg_profit": r["avg_profit"]
            }
            for r in top_routes
        ],
        "time_period": period
    }


@router.post("/history/export", auth=django_auth)
def export_history(request, filters: ArbitrageHistoryFilterSchema):
    """
    Export arbitrage history to CSV/Excel.
    """
    # This would implement export functionality
    # For now, return a placeholder
    return {"message": "Export functionality to be implemented"}