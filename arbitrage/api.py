"""
Enhanced Django Ninja API endpoints for multi-exchange arbitrage operations.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from decimal import Decimal
from typing import List, Optional
from uuid import UUID

from django.db import models, transaction
from django.shortcuts import get_object_or_404
from ninja import Router
from ninja.pagination import paginate
from ninja.security import django_auth

from arbitrage.engine import MultiExchangeArbitrageEngine
from arbitrage.models import (
    ArbitrageAlert,
    ArbitrageConfig,
    ArbitrageExecution,
    ArbitrageOpportunity,
    MultiExchangeArbitrageStrategy,
    MultiExchangeExecution,
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
    ExecuteMultiStrategySchema,
    MultiExchangeExecutionSchema,
    MultiExchangeStrategySchema,
)
from arbitrage.tasks import (
    execute_arbitrage_opportunity,
    execute_multi_exchange_strategy,
)
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
    List simple arbitrage opportunities with optional filters.
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


@router.get("/strategies", response=List[MultiExchangeStrategySchema])
@paginate
def list_multi_strategies(
    request,
    status: Optional[str] = None,
    strategy_type: Optional[str] = None,
    min_profit: Optional[float] = None,
):
    """
    List multi-exchange arbitrage strategies.
    """
    queryset = MultiExchangeArbitrageStrategy.objects.select_related(
        "trading_pair",
        "trading_pair__base_currency",
        "trading_pair__quote_currency",
    )
    
    # Apply filters
    if status:
        queryset = queryset.filter(status=status)
    else:
        # Default to active strategies
        queryset = queryset.filter(
            status="detected",
            expires_at__gt=datetime.now()
        )
    
    if strategy_type:
        queryset = queryset.filter(strategy_type=strategy_type)
    
    if min_profit:
        queryset = queryset.filter(profit_percentage__gte=min_profit)
    
    # Apply user config filters if authenticated
    if request.user.is_authenticated:
        try:
            config = request.user.arbitrage_config
            if not config.enable_multi_exchange:
                return queryset.none()
            
            queryset = queryset.filter(
                profit_percentage__gte=config.min_profit_percentage
            )
            
            if config.enabled_pairs.exists():
                queryset = queryset.filter(
                    trading_pair__in=config.enabled_pairs.all()
                )
        except ArbitrageConfig.DoesNotExist:
            pass
    
    return queryset.order_by("-profit_percentage", "-created_at")


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


@router.get("/strategies/{strategy_id}", response=MultiExchangeStrategySchema)
def get_multi_strategy(request, strategy_id: UUID):
    """
    Get details of a specific multi-exchange strategy.
    """
    strategy = get_object_or_404(
        MultiExchangeArbitrageStrategy.objects.select_related(
            "trading_pair"
        ).prefetch_related("executions"),
        id=strategy_id
    )
    return strategy


@router.post("/opportunities/scan", response=ArbitrageScanResultSchema)
async def scan_opportunities(request, scan_request: ArbitrageScanRequestSchema):
    """
    Manually trigger an enhanced arbitrage scan for both simple and multi-exchange strategies.
    """
    start_time = datetime.now()
    engine = MultiExchangeArbitrageEngine()
    
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
        all_strategies = await engine.scan_all_opportunities(
            user_config=user_config,
            enabled_exchanges=exchanges,
            enabled_pairs=pairs
        )
        
        simple_opportunities = [s for s in all_strategies if isinstance(s, ArbitrageOpportunity)]
        multi_strategies = [s for s in all_strategies if isinstance(s, MultiExchangeArbitrageStrategy)]
        
        # Save opportunities to database
        saved_simple = []
        saved_multi = []
        
        with transaction.atomic():
            for opp in simple_opportunities:
                opp.save()
                saved_simple.append(opp)
            
            for strategy in multi_strategies:
                strategy.save()
                saved_multi.append(strategy)
        
        scan_duration = (datetime.now() - start_time).total_seconds()
        
        return {
            "simple_opportunities_found": len(saved_simple),
            "multi_strategies_found": len(saved_multi),
            "total_found": len(saved_simple) + len(saved_multi),
            "scan_duration": scan_duration,
            "simple_opportunities": saved_simple,
            "multi_strategies": saved_multi,
            "errors": []
        }
        
    except Exception as e:
        logger.error(f"Error scanning opportunities: {e}")
        return {
            "simple_opportunities_found": 0,
            "multi_strategies_found": 0,
            "total_found": 0,
            "scan_duration": 0,
            "simple_opportunities": [],
            "multi_strategies": [],
            "errors": [str(e)]
        }


@router.post("/opportunities/{opportunity_id}/execute", 
            auth=django_auth,
            response=ArbitrageExecutionSchema)
def execute_opportunity(request, opportunity_id: UUID, data: ExecuteArbitrageSchema):
    """
    Execute a simple arbitrage opportunity.
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
        request.user.id,
        float(amount),
        use_market_orders
    )
    
    return execution


@router.post("/strategies/{strategy_id}/execute", 
            auth=django_auth,
            response=MultiExchangeStrategySchema)
def execute_multi_strategy(request, strategy_id: UUID, data: ExecuteMultiStrategySchema):
    """
    Execute a multi-exchange arbitrage strategy.
    """
    strategy = get_object_or_404(
        MultiExchangeArbitrageStrategy,
        id=strategy_id,
        status="detected"
    )
    
    # Check if strategy is still valid
    if strategy.expires_at < datetime.now():
        return {"error": "Strategy has expired"}
    
    # Get user config
    try:
        config = request.user.arbitrage_config
        if not config.is_active:
            return {"error": "Arbitrage trading is disabled for your account"}
        if not config.enable_multi_exchange:
            return {"error": "Multi-exchange arbitrage is disabled for your account"}
    except ArbitrageConfig.DoesNotExist:
        return {"error": "Please configure your arbitrage settings first"}
    
    # Check if user has required API credentials for all exchanges
    required_exchanges = set()
    for action in strategy.buy_actions + strategy.sell_actions:
        exchange = Exchange.objects.filter(code=action['exchange']).first()
        if exchange:
            required_exchanges.add(exchange)
    
    user_exchanges = set(request.user.api_credentials.filter(
        is_active=True
    ).values_list('exchange', flat=True))
    
    missing_exchanges = required_exchanges - set(Exchange.objects.filter(id__in=user_exchanges))
    if missing_exchanges:
        missing_names = [ex.name for ex in missing_exchanges]
        return {"error": f"Missing API credentials for exchanges: {', '.join(missing_names)}"}
    
    # Trigger async execution
    execute_multi_exchange_strategy.delay(
        strategy.id,
        request.user.id
    )
    
    # Update strategy status
    strategy.status = "validating"
    strategy.save()
    
    return strategy


@router.get("/executions", auth=django_auth, response=List[ArbitrageExecutionSchema])
@paginate
def list_executions(request, status: Optional[str] = None):
    """
    List user's simple arbitrage executions.
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


@router.get("/executions/multi", auth=django_auth, response=List[MultiExchangeExecutionSchema])
@paginate
def list_multi_executions(request, strategy_id: Optional[UUID] = None, status: Optional[str] = None):
    """
    List user's multi-exchange executions.
    """
    queryset = MultiExchangeExecution.objects.filter(
        strategy__executions__strategy__user=request.user  # Get user through strategy
    ).select_related(
        "strategy",
        "exchange",
        "strategy__trading_pair"
    ).distinct()
    
    if strategy_id:
        queryset = queryset.filter(strategy_id=strategy_id)
    
    if status:
        queryset = queryset.filter(status=status)
    
    return queryset.order_by("-created_at")


@router.get("/executions/{execution_id}", 
           auth=django_auth, 
           response=ArbitrageExecutionSchema)
def get_execution(request, execution_id: UUID):
    """
    Get details of a specific simple execution.
    """
    execution = get_object_or_404(
        ArbitrageExecution,
        id=execution_id,
        user=request.user
    )
    return execution


@router.get("/executions/multi/{execution_id}", 
           auth=django_auth, 
           response=MultiExchangeExecutionSchema)
def get_multi_execution(request, execution_id: UUID):
    """
    Get details of a specific multi-exchange execution.
    """
    execution = get_object_or_404(
        MultiExchangeExecution.objects.select_related(
            "strategy", "exchange"
        ),
        id=execution_id,
        strategy__executions__strategy__user=request.user
    )
    return execution


@router.get("/config", auth=django_auth, response=ArbitrageConfigSchema)
def get_config(request):
    """
    Get user's enhanced arbitrage configuration.
    """
    config, created = ArbitrageConfig.objects.get_or_create(
        user=request.user,
        defaults={
            "min_profit_percentage": Decimal("0.5"),
            "min_profit_amount": Decimal("10"),
            "max_exposure_percentage": Decimal("10"),
            "stop_loss_percentage": Decimal("2"),
            "enable_multi_exchange": True,
            "max_exchanges_per_strategy": 3,
            "min_profit_per_exchange": Decimal("0.3"),
            "allocation_strategy": "risk_adjusted",
            "max_allocation_per_exchange": Decimal("50.0"),
            "require_simultaneous_execution": True,
            "max_execution_time": 30,
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
        # Multi-exchange specific fields
        "enable_multi_exchange": config.enable_multi_exchange,
        "max_exchanges_per_strategy": config.max_exchanges_per_strategy,
        "min_profit_per_exchange": config.min_profit_per_exchange,
        "allocation_strategy": config.allocation_strategy,
        "max_allocation_per_exchange": config.max_allocation_per_exchange,
        "require_simultaneous_execution": config.require_simultaneous_execution,
        "max_execution_time": config.max_execution_time,
        "enable_triangular_arbitrage": config.enable_triangular_arbitrage,
        "min_liquidity_ratio": config.min_liquidity_ratio,
        "max_slippage_tolerance": config.max_slippage_tolerance,
        "notify_on_high_profit": config.notify_on_high_profit,
        "exchange_reliability_weights": config.exchange_reliability_weights,
        "order_timeout": config.order_timeout,
    }


@router.patch("/config", auth=django_auth, response=ArbitrageConfigSchema)
def update_config(request, data: ArbitrageConfigUpdateSchema):
    """
    Update user's enhanced arbitrage configuration.
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
def list_alerts(request, unread_only: bool = False, alert_type: Optional[str] = None):
    """
    List user's arbitrage alerts including multi-exchange alerts.
    """
    queryset = ArbitrageAlert.objects.filter(user=request.user)
    
    if unread_only:
        queryset = queryset.filter(is_read=False)
    
    if alert_type:
        queryset = queryset.filter(alert_type=alert_type)
    
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
    Get enhanced arbitrage statistics for the user including multi-exchange data.
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
    
    # Get simple executions
    executions = ArbitrageExecution.objects.filter(user=request.user)
    if start_date:
        executions = executions.filter(created_at__gte=start_date)
    
    # Calculate simple stats
    total_executions = executions.count()
    completed_executions = executions.filter(status="completed")
    
    total_profit = completed_executions.aggregate(
        total=models.Sum("final_profit")
    )["total"] or Decimal("0")
    
    avg_profit_percentage = completed_executions.aggregate(
        avg=models.Avg("profit_percentage")
    )["avg"] or Decimal("0")
    
    # Get multi-exchange strategies
    multi_strategies = MultiExchangeArbitrageStrategy.objects.filter(
        executions__strategy__user=request.user
    ).distinct()
    if start_date:
        multi_strategies = multi_strategies.filter(created_at__gte=start_date)
    
    total_multi_strategies = multi_strategies.count()
    completed_multi_strategies = multi_strategies.filter(status="completed")
    
    multi_profit = completed_multi_strategies.aggregate(
        total=models.Sum("actual_profit")
    )["total"] or Decimal("0")
    
    # Combined stats
    combined_profit = total_profit + multi_profit
    
    # Success rates
    simple_success_rate = (
        (completed_executions.count() / total_executions * 100)
        if total_executions > 0 else Decimal("0")
    )
    
    multi_success_rate = (
        (completed_multi_strategies.count() / total_multi_strategies * 100)
        if total_multi_strategies > 0 else Decimal("0")
    )
    
    # Get active opportunities
    active_simple_opportunities = ArbitrageOpportunity.objects.filter(
        status="detected",
        expires_at__gt=datetime.now()
    ).count()
    
    active_multi_strategies = MultiExchangeArbitrageStrategy.objects.filter(
        status="detected",
        expires_at__gt=datetime.now()
    ).count()
    
    # Get total opportunities (including expired)
    total_simple_opportunities = ArbitrageOpportunity.objects.count()
    total_multi_opportunities = MultiExchangeArbitrageStrategy.objects.count()
    
    if start_date:
        total_simple_opportunities = ArbitrageOpportunity.objects.filter(
            created_at__gte=start_date
        ).count()
        total_multi_opportunities = MultiExchangeArbitrageStrategy.objects.filter(
            created_at__gte=start_date
        ).count()
    
    # Get top profitable pairs (combined)
    top_pairs_simple = (
        ArbitrageOpportunity.objects
        .values("trading_pair__symbol")
        .annotate(
            count=models.Count("id"),
            avg_profit=models.Avg("net_profit_percentage")
        )
        .order_by("-avg_profit")[:3]
    )
    
    top_pairs_multi = (
        MultiExchangeArbitrageStrategy.objects
        .values("trading_pair__symbol")
        .annotate(
            count=models.Count("id"),
            avg_profit=models.Avg("profit_percentage")
        )
        .order_by("-avg_profit")[:3]
    )
    
    # Combine and deduplicate
    all_pairs = {}
    for pair in top_pairs_simple:
        symbol = pair["trading_pair__symbol"]
        all_pairs[symbol] = {
            "symbol": symbol,
            "simple_count": pair["count"],
            "multi_count": 0,
            "simple_avg_profit": pair["avg_profit"],
            "multi_avg_profit": Decimal("0")
        }
    
    for pair in top_pairs_multi:
        symbol = pair["trading_pair__symbol"]
        if symbol in all_pairs:
            all_pairs[symbol]["multi_count"] = pair["count"]
            all_pairs[symbol]["multi_avg_profit"] = pair["avg_profit"]
        else:
            all_pairs[symbol] = {
                "symbol": symbol,
                "simple_count": 0,
                "multi_count": pair["count"],
                "simple_avg_profit": Decimal("0"),
                "multi_avg_profit": pair["avg_profit"]
            }
    
    top_pairs = sorted(
        all_pairs.values(),
        key=lambda x: max(x["simple_avg_profit"], x["multi_avg_profit"]),
        reverse=True
    )[:5]
    
    return {
        # Simple arbitrage stats
        "total_simple_opportunities_detected": total_simple_opportunities,
        "total_simple_opportunities_executed": total_executions,
        "simple_profit": total_profit,
        "simple_average_profit_percentage": avg_profit_percentage,
        "simple_success_rate": simple_success_rate,
        "active_simple_opportunities": active_simple_opportunities,
        
        # Multi-exchange stats
        "total_multi_strategies_detected": total_multi_opportunities,
        "total_multi_strategies_executed": total_multi_strategies,
        "multi_profit": multi_profit,
        "multi_success_rate": multi_success_rate,
        "active_multi_strategies": active_multi_strategies,
        
        # Combined stats
        "total_opportunities_detected": total_simple_opportunities + total_multi_opportunities,
        "total_opportunities_executed": total_executions + total_multi_strategies,
        "total_profit": combined_profit,
        "active_opportunities": active_simple_opportunities + active_multi_strategies,
        "top_profitable_pairs": top_pairs,
        "time_period": period
    }


@router.post("/history/export", auth=django_auth)
def export_history(request, filters: ArbitrageHistoryFilterSchema):
    """
    Export arbitrage history to CSV/Excel including multi-exchange data.
    """
    # This would implement enhanced export functionality
    # For now, return a placeholder
    return {"message": "Enhanced export functionality to be implemented"}


@router.get("/performance/comparison")
def compare_strategies(request, period: str = "7d"):
    """
    Compare performance between simple and multi-exchange strategies.
    """
    # Parse period
    if period == "24h":
        start_date = datetime.now() - timedelta(hours=24)
    elif period == "7d":
        start_date = datetime.now() - timedelta(days=7)
    elif period == "30d":
        start_date = datetime.now() - timedelta(days=30)
    else:
        start_date = datetime.now() - timedelta(days=7)
    
    # Simple arbitrage performance
    simple_executions = ArbitrageExecution.objects.filter(
        created_at__gte=start_date,
        status="completed"
    )
    
    simple_stats = {
        "count": simple_executions.count(),
        "total_profit": simple_executions.aggregate(
            total=models.Sum("final_profit")
        )["total"] or Decimal("0"),
        "avg_profit": simple_executions.aggregate(
            avg=models.Avg("final_profit")
        )["avg"] or Decimal("0"),
        "avg_profit_percentage": simple_executions.aggregate(
            avg=models.Avg("profit_percentage")
        )["avg"] or Decimal("0"),
    }
    
    # Multi-exchange performance
    multi_strategies = MultiExchangeArbitrageStrategy.objects.filter(
        created_at__gte=start_date,
        status="completed"
    )
    
    multi_stats = {
        "count": multi_strategies.count(),
        "total_profit": multi_strategies.aggregate(
            total=models.Sum("actual_profit")
        )["total"] or Decimal("0"),
        "avg_profit": multi_strategies.aggregate(
            avg=models.Avg("actual_profit")
        )["avg"] or Decimal("0"),
        "avg_profit_percentage": multi_strategies.aggregate(
            avg=models.Avg("actual_profit_percentage")
        )["avg"] or Decimal("0"),
    }
    
    # Calculate efficiency metrics
    total_profit = simple_stats["total_profit"] + multi_stats["total_profit"]
    total_count = simple_stats["count"] + multi_stats["count"]
    
    return {
        "period": period,
        "simple_arbitrage": simple_stats,
        "multi_exchange": multi_stats,
        "summary": {
            "total_profit": total_profit,
            "total_executions": total_count,
            "simple_percentage": (simple_stats["count"] / total_count * 100) if total_count > 0 else 0,
            "multi_percentage": (multi_stats["count"] / total_count * 100) if total_count > 0 else 0,
            "profit_ratio_simple": (simple_stats["total_profit"] / total_profit * 100) if total_profit > 0 else 0,
            "profit_ratio_multi": (multi_stats["total_profit"] / total_profit * 100) if total_profit > 0 else 0,
        }
    }


@router.get("/strategies/types")
def get_strategy_types(request):
    """
    Get available multi-exchange strategy types and their descriptions.
    """
    return {
        "strategy_types": [
            {
                "code": "one_to_many",
                "name": "One-to-Many",
                "description": "Buy on one exchange, sell on multiple exchanges",
                "complexity": "Medium",
                "typical_profit": "0.5-2.0%",
                "risk_level": "Medium"
            },
            {
                "code": "many_to_one",
                "name": "Many-to-One",
                "description": "Buy on multiple exchanges, sell on one exchange",
                "complexity": "Medium",
                "typical_profit": "0.3-1.5%",
                "risk_level": "Medium"
            },
            {
                "code": "complex",
                "name": "Complex Multi-Exchange",
                "description": "Buy and sell across multiple exchanges simultaneously",
                "complexity": "High",
                "typical_profit": "0.8-3.0%",
                "risk_level": "High"
            },
            {
                "code": "triangular",
                "name": "Triangular Arbitrage",
                "description": "Three-way arbitrage using currency pairs",
                "complexity": "Very High",
                "typical_profit": "0.2-1.0%",
                "risk_level": "Very High"
            }
        ]
    }


@router.get("/market/depth/{trading_pair}")
async def get_market_depth_analysis(request, trading_pair: str):
    """
    Get detailed market depth analysis across all exchanges for a trading pair.
    """
    pair = get_object_or_404(TradingPair, symbol=trading_pair)
    
    engine = MultiExchangeArbitrageEngine()
    exchanges = list(Exchange.objects.filter(is_active=True))
    
    try:
        market_data = await engine._get_market_data(pair, exchanges)
        
        depth_analysis = {}
        for exchange, data in market_data.items():
            ticker = data.get("ticker")
            order_book = data.get("order_book")
            
            if ticker and order_book:
                # Calculate liquidity at different levels
                buy_liquidity_1pct = engine._calculate_available_liquidity(
                    order_book, "ask", ticker.ask_price * Decimal("1.01")
                )
                sell_liquidity_1pct = engine._calculate_available_liquidity(
                    order_book, "bid", ticker.bid_price * Decimal("0.99")
                )
                
                depth_analysis[exchange.name] = {
                    "ask_price": float(ticker.ask_price) if ticker.ask_price else None,
                    "bid_price": float(ticker.bid_price) if ticker.bid_price else None,
                    "spread_percentage": float(
                        (ticker.ask_price - ticker.bid_price) / ticker.bid_price * 100
                    ) if ticker.ask_price and ticker.bid_price else None,
                    "buy_liquidity_1pct": float(buy_liquidity_1pct),
                    "sell_liquidity_1pct": float(sell_liquidity_1pct),
                    "volume_24h": float(ticker.volume_24h),
                    "last_update": ticker.timestamp.isoformat()
                }
        
        return {
            "trading_pair": trading_pair,
            "exchanges": depth_analysis,
            "analysis_time": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error analyzing market depth: {e}")
        return {"error": str(e)}