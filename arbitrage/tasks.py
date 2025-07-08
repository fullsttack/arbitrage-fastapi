import logging
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Optional

from asgiref.sync import sync_to_async
from celery import shared_task
from django.core.cache import cache
from django.db import transaction
from django.utils import timezone

from arbitrage.engine import MultiExchangeArbitrageEngine
from arbitrage.models import (
    ArbitrageAlert,
    ArbitrageConfig,
    ArbitrageExecution,
    ArbitrageOpportunity,
    MultiExchangeArbitrageStrategy,
    MultiExchangeExecution,
)
from core.models import APICredential, Exchange, TradingPair
from exchanges.services.nobitex import NobitexService
from exchanges.services.ramzinex import RamzinexService
from exchanges.services.wallex import WallexService

logger = logging.getLogger(__name__)

# Service mapping
EXCHANGE_SERVICES = {
    "nobitex": NobitexService,
    "wallex": WallexService,
    "ramzinex": RamzinexService,
}


@shared_task
def scan_arbitrage_opportunities():
    """
    Enhanced periodic task to scan for both simple and multi-exchange arbitrage opportunities.
    
    FIXED: Proper async handling in Celery task
    """
    logger.info("Starting enhanced arbitrage scan...")
    
    # Initialize variables
    simple_opportunities = []
    multi_strategies = []
    
    try:
        # Get all active user configs (sync call)
        active_configs = list(ArbitrageConfig.objects.filter(
            is_active=True
        ).select_related("user"))
        
        # Create engine
        engine = MultiExchangeArbitrageEngine()
        
        # Run the async scan in sync context
        # FIXED: Use sync_to_async instead of event loop
        all_strategies = sync_to_async_scan(engine)
        
        # Separate simple and multi strategies
        simple_opportunities = [s for s in all_strategies if hasattr(s, 'buy_exchange')]
        multi_strategies = [s for s in all_strategies if hasattr(s, 'strategy_type')]
        
        logger.info(f"Found {len(simple_opportunities)} simple opportunities and {len(multi_strategies)} multi-exchange strategies")
        
        # Save opportunities and strategies (sync operations)
        save_opportunities_and_strategies(
            simple_opportunities, 
            multi_strategies, 
            active_configs
        )
        
    except Exception as e:
        logger.error(f"Error in enhanced arbitrage scan: {e}")
        return f"Scan failed: {str(e)}"
    
    return f"Scan completed. Found {len(simple_opportunities)} simple opportunities and {len(multi_strategies)} multi-exchange strategies."


def sync_to_async_scan(engine):
    """
    Synchronous wrapper for async scanning.
    
    FIXED: Proper async to sync conversion
    """
    import asyncio
    
    # Create new event loop for this task
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # Run the async scan
        result = loop.run_until_complete(
            engine.scan_all_opportunities()
        )
        
        return result
    finally:
        loop.close()


def save_opportunities_and_strategies(simple_opportunities, multi_strategies, active_configs):
    """
    Save opportunities and strategies to database (sync operations).
    
    FIXED: Separated from async context
    """
    with transaction.atomic():
        # Save simple opportunities
        for opp in simple_opportunities:
            # Check if similar opportunity already exists
            existing = ArbitrageOpportunity.objects.filter(
                trading_pair=opp.trading_pair,
                buy_exchange=opp.buy_exchange,
                sell_exchange=opp.sell_exchange,
                status="detected",
                expires_at__gt=timezone.now()
            ).first()
            
            if not existing:
                opp.save()
                
                # Check user configs for alerts and auto-execution
                for config in active_configs:
                    if should_alert_user(config, opp):
                        create_opportunity_alert(config.user, opp)
                        
                        # Auto-execute if enabled
                        if config.auto_trade:
                            execute_arbitrage_opportunity.delay(opp.id, config.user.id)
        
        # Save multi-exchange strategies
        for strategy in multi_strategies:
            # Check if similar strategy already exists
            existing_strategy = MultiExchangeArbitrageStrategy.objects.filter(
                trading_pair=strategy.trading_pair,
                strategy_type=strategy.strategy_type,
                status="detected",
                expires_at__gt=timezone.now()
            ).first()
            
            if not existing_strategy:
                strategy.save()
                
                # Check user configs for multi-exchange strategies
                for config in active_configs:
                    if config.enable_multi_exchange and should_alert_user_multi(config, strategy):
                        create_multi_strategy_alert(config.user, strategy)
                        
                        # Auto-execute if enabled
                        if config.auto_trade:
                            execute_multi_exchange_strategy.delay(strategy.id, config.user.id)


@shared_task
def execute_multi_exchange_strategy(strategy_id: str, user_id: int):
    """
    Execute a multi-exchange arbitrage strategy.
    """
    logger.info(f"Executing multi-exchange strategy {strategy_id} for user {user_id}")
    
    try:
        strategy = MultiExchangeArbitrageStrategy.objects.get(id=strategy_id)
        
        # Create execution record
        execution = MultiExchangeExecution.objects.create(
            strategy=strategy,
            user_id=user_id,
            status="executing",
            started_at=timezone.now()
        )
        
        # Execute strategy asynchronously
        result = sync_to_async_execute_strategy(strategy, execution)
        
        return f"Strategy execution {'completed' if result else 'failed'}"
        
    except Exception as e:
        logger.error(f"Error executing multi-exchange strategy {strategy_id}: {e}")
        return f"Execution failed: {str(e)}"


def sync_to_async_execute_strategy(strategy, execution):
    """
    Synchronous wrapper for async strategy execution.
    """
    import asyncio
    
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # Run the async execution
        engine = MultiExchangeArbitrageEngine()
        result = loop.run_until_complete(
            engine.execute_multi_strategy(strategy, execution)
        )
        
        return result
    finally:
        loop.close()


@shared_task
def execute_arbitrage_opportunity(opportunity_id: str, user_id: int):
    """
    Execute a simple arbitrage opportunity.
    
    FIXED: Proper async handling
    """
    logger.info(f"Executing arbitrage opportunity {opportunity_id} for user {user_id}")
    
    try:
        opportunity = ArbitrageOpportunity.objects.get(id=opportunity_id)
        
        # Update status
        opportunity.status = "executing"
        opportunity.save()
        
        # Create execution record
        execution = ArbitrageExecution.objects.create(
            opportunity=opportunity,
            user_id=user_id,
            status="executing",
            started_at=timezone.now()
        )
        
        # Execute trades
        result = sync_to_async_execute_trades(opportunity, execution)
        
        # Update final status
        if result:
            opportunity.status = "executed"
            execution.status = "completed"
        else:
            opportunity.status = "failed"
            execution.status = "failed"
        
        opportunity.executed_at = timezone.now()
        opportunity.save()
        execution.completed_at = timezone.now()
        execution.save()
        
        return f"Execution {'completed' if result else 'failed'}"
        
    except Exception as e:
        logger.error(f"Error executing opportunity {opportunity_id}: {e}")
        return f"Execution failed: {str(e)}"


def sync_to_async_execute_trades(opportunity, execution):
    """
    Synchronous wrapper for async trade execution.
    """
    import asyncio
    
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # Run the async execution
        engine = MultiExchangeArbitrageEngine()
        result = loop.run_until_complete(
            engine.execute_simple_opportunity(opportunity, execution)
        )
        
        return result
    finally:
        loop.close()


@shared_task
def cleanup_old_opportunities():
    """
    Clean up old arbitrage opportunities and executions.
    """
    logger.info("Cleaning up old arbitrage opportunities...")
    
    # Clean up expired opportunities
    expired_count = ArbitrageOpportunity.objects.filter(
        expires_at__lt=timezone.now(),
        status="detected"
    ).update(status="expired")
    
    # Clean up old opportunities (older than 7 days)
    old_threshold = timezone.now() - timedelta(days=7)
    old_opportunities = ArbitrageOpportunity.objects.filter(
        created_at__lt=old_threshold,
        status__in=["expired", "executed", "failed"]
    )
    old_count = old_opportunities.count()
    old_opportunities.delete()
    
    logger.info(f"Cleaned up {expired_count} expired and {old_count} old opportunities")
    return f"Cleaned up {expired_count} expired and {old_count} old opportunities"


# Helper functions
def should_alert_user(config, opportunity):
    """Check if user should be alerted about this opportunity."""
    return (
        config.is_active and
        opportunity.net_profit_percentage >= config.min_profit_percentage and
        (not config.enabled_pairs.exists() or 
         opportunity.trading_pair in config.enabled_pairs.all())
    )


def should_alert_user_multi(config, strategy):
    """Check if user should be alerted about this multi-exchange strategy."""
    return (
        config.is_active and
        config.enable_multi_exchange and
        strategy.profit_percentage >= config.min_profit_percentage and
        (not config.enabled_pairs.exists() or 
         strategy.trading_pair in config.enabled_pairs.all())
    )


def create_opportunity_alert(user, opportunity):
    """Create alert for arbitrage opportunity."""
    ArbitrageAlert.objects.create(
        user=user,
        alert_type="opportunity_detected",
        title=f"Arbitrage Opportunity: {opportunity.trading_pair.symbol}",
        message=f"Profit: {opportunity.net_profit_percentage}% | "
                f"{opportunity.buy_exchange.name} → {opportunity.sell_exchange.name}",
        related_opportunity=opportunity
    )


def create_multi_strategy_alert(user, strategy):
    """Create alert for multi-exchange strategy."""
    ArbitrageAlert.objects.create(
        user=user,
        alert_type="multi_strategy_detected",
        title=f"Multi-Exchange Strategy: {strategy.trading_pair.symbol}",
        message=f"Profit: {strategy.profit_percentage}% | "
                f"Type: {strategy.get_strategy_type_display()}",
        related_multi_strategy=strategy
    )