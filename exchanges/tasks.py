import asyncio
import logging
from datetime import datetime, timedelta
from typing import List

from celery import shared_task
from django.core.cache import cache
from django.db import transaction
from django.utils import timezone

from core.models import Exchange, ExchangeTradingPair, TradingPair
from exchanges.models import ExchangeStatus, MarketTicker, OrderBook
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
def sync_exchange_markets(exchange_id: int):
    """
    Sync available markets for an exchange.
    """
    try:
        exchange = Exchange.objects.get(id=exchange_id)
        service_class = EXCHANGE_SERVICES.get(exchange.code)
        
        if not service_class:
            logger.error(f"Service not implemented for {exchange.name}")
            return
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            async def sync():
                async with service_class(exchange) as service:
                    await service.sync_markets()
            
            loop.run_until_complete(sync())
            
            # Update last sync time
            ExchangeTradingPair.objects.filter(
                exchange=exchange
            ).update(last_sync=timezone.now())
            
            logger.info(f"Successfully synced markets for {exchange.name}")
            
        finally:
            loop.close()
            
    except Exception as e:
        logger.error(f"Error syncing markets for exchange {exchange_id}: {e}")


@shared_task
def update_exchange_tickers():
    """
    Update tickers for all active exchange trading pairs.
    """
    logger.info("Starting ticker update...")
    
    # Get active exchanges
    exchanges = Exchange.objects.filter(is_active=True)
    
    for exchange in exchanges:
        update_exchange_ticker.delay(exchange.id)
    
    return f"Triggered ticker updates for {exchanges.count()} exchanges"


@shared_task
def update_exchange_ticker(exchange_id: int):
    """
    Update tickers for a specific exchange.
    """
    try:
        exchange = Exchange.objects.get(id=exchange_id)
        service_class = EXCHANGE_SERVICES.get(exchange.code)
        
        if not service_class:
            logger.error(f"Service not implemented for {exchange.name}")
            return
        
        # Get active trading pairs for this exchange
        exchange_pairs = ExchangeTradingPair.objects.filter(
            exchange=exchange,
            is_active=True
        ).select_related("trading_pair")
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            async def update_tickers():
                async with service_class(exchange) as service:
                    tasks = []
                    for pair in exchange_pairs:
                        task = service.update_ticker(pair)
                        tasks.append(task)
                    
                    # Run updates concurrently with rate limiting
                    results = []
                    batch_size = 10  # Process 10 at a time
                    
                    for i in range(0, len(tasks), batch_size):
                        batch = tasks[i:i + batch_size]
                        batch_results = await asyncio.gather(
                            *batch, return_exceptions=True
                        )
                        results.extend(batch_results)
                        
                        # Small delay between batches to respect rate limits
                        if i + batch_size < len(tasks):
                            await asyncio.sleep(0.5)
                    
                    return results
            
            results = loop.run_until_complete(update_tickers())
            
            success_count = sum(
                1 for r in results if not isinstance(r, Exception)
            )
            logger.info(
                f"Updated {success_count}/{len(exchange_pairs)} tickers "
                f"for {exchange.name}"
            )
            
            # Update exchange status
            update_exchange_status(exchange.id, is_online=True)
            
        finally:
            loop.close()
            
    except Exception as e:
        logger.error(f"Error updating tickers for exchange {exchange_id}: {e}")
        update_exchange_status(exchange_id, is_online=False, error=str(e))


@shared_task
def update_order_books():
    """
    Update order books for active trading pairs.
    """
    logger.info("Starting order book update...")
    
    # Get pairs that need order book updates
    # Prioritize pairs with recent arbitrage opportunities
    pairs_with_opportunities = (
        ExchangeTradingPair.objects
        .filter(
            is_active=True,
            trading_pair__arbitrage_opportunities__status="detected",
            trading_pair__arbitrage_opportunities__expires_at__gt=timezone.now()
        )
        .distinct()
        .values_list("id", flat=True)
    )
    
    # Update order books for these pairs
    for pair_id in pairs_with_opportunities:
        update_order_book.delay(pair_id)
    
    return f"Triggered order book updates for {len(pairs_with_opportunities)} pairs"


@shared_task
def update_order_book(exchange_pair_id: int):
    """
    Update order book for a specific exchange trading pair.
    """
    try:
        exchange_pair = ExchangeTradingPair.objects.select_related(
            "exchange"
        ).get(id=exchange_pair_id)
        
        service_class = EXCHANGE_SERVICES.get(exchange_pair.exchange.code)
        if not service_class:
            return
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            async def update():
                async with service_class(exchange_pair.exchange) as service:
                    return await service.update_order_book(exchange_pair)
            
            order_book = loop.run_until_complete(update())
            logger.info(f"Updated order book for {exchange_pair}")
            
        finally:
            loop.close()
            
    except Exception as e:
        logger.error(f"Error updating order book for pair {exchange_pair_id}: {e}")


@shared_task
def check_exchange_health():
    """
    Check health status of all exchanges.
    """
    exchanges = Exchange.objects.filter(is_active=True)
    
    for exchange in exchanges:
        check_exchange_status.delay(exchange.id)
    
    return f"Checking health for {exchanges.count()} exchanges"


@shared_task
def check_exchange_status(exchange_id: int):
    """
    Check if an exchange is accessible and functioning.
    """
    try:
        exchange = Exchange.objects.get(id=exchange_id)
        service_class = EXCHANGE_SERVICES.get(exchange.code)
        
        if not service_class:
            return
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            start_time = datetime.now()
            
            async def check():
                async with service_class(exchange) as service:
                    # Try to get markets as a health check
                    markets = await service.get_markets()
                    return len(markets) > 0
            
            is_healthy = loop.run_until_complete(check())
            response_time = (datetime.now() - start_time).total_seconds()
            
            if is_healthy:
                update_exchange_status(
                    exchange_id,
                    is_online=True,
                    response_time=response_time
                )
            else:
                update_exchange_status(
                    exchange_id,
                    is_online=False,
                    error="No markets returned"
                )
                
        finally:
            loop.close()
            
    except Exception as e:
        logger.error(f"Error checking status for exchange {exchange_id}: {e}")
        update_exchange_status(exchange_id, is_online=False, error=str(e))


def update_exchange_status(
    exchange_id: int,
    is_online: bool,
    response_time: float = None,
    error: str = None
):
    """
    Update exchange status in database.
    """
    try:
        exchange = Exchange.objects.get(id=exchange_id)
        status, created = ExchangeStatus.objects.get_or_create(
            exchange=exchange
        )
        
        status.is_online = is_online
        status.last_check = timezone.now()
        
        if response_time is not None:
            status.response_time = response_time
        
        if error:
            status.error_count += 1
            status.last_error = error
            status.last_error_time = timezone.now()
        elif is_online:
            # Reset error count on successful check
            status.error_count = 0
        
        status.save()
        
    except Exception as e:
        logger.error(f"Error updating exchange status: {e}")


@shared_task
def cleanup_old_market_data():
    """
    Clean up old market data to prevent database bloat.
    """
    # Keep only last 24 hours of ticker data
    ticker_cutoff = timezone.now() - timedelta(hours=24)
    deleted_tickers = MarketTicker.objects.filter(
        timestamp__lt=ticker_cutoff
    ).delete()[0]
    
    # Keep only last 6 hours of order book data
    orderbook_cutoff = timezone.now() - timedelta(hours=6)
    deleted_orderbooks = OrderBook.objects.filter(
        timestamp__lt=orderbook_cutoff
    ).delete()[0]
    
    logger.info(
        f"Cleaned up {deleted_tickers} tickers and "
        f"{deleted_orderbooks} order books"
    )
    
    return {
        "deleted_tickers": deleted_tickers,
        "deleted_orderbooks": deleted_orderbooks
    }


@shared_task
def sync_user_balances(user_id: int):
    """
    Sync user balances across all exchanges.
    """
    from django.contrib.auth.models import User
    from core.models import APICredential
    from exchanges.models import ExchangeBalance
    
    try:
        user = User.objects.get(id=user_id)
        credentials = APICredential.objects.filter(
            user=user,
            is_active=True
        ).select_related("exchange")
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            async def sync_balances():
                tasks = []
                for credential in credentials:
                    service_class = EXCHANGE_SERVICES.get(
                        credential.exchange.code
                    )
                    if service_class:
                        task = update_user_balance(
                            user, credential, service_class
                        )
                        tasks.append(task)
                
                return await asyncio.gather(*tasks, return_exceptions=True)
            
            results = loop.run_until_complete(sync_balances())
            
            success_count = sum(
                1 for r in results if not isinstance(r, Exception)
            )
            logger.info(
                f"Updated balances for {success_count}/{len(credentials)} "
                f"exchanges for user {user_id}"
            )
            
        finally:
            loop.close()
            
    except Exception as e:
        logger.error(f"Error syncing balances for user {user_id}: {e}")


async def update_user_balance(user, credential, service_class):
    """
    Update user balance for a specific exchange.
    """
    try:
        async with service_class(
            credential.exchange,
            credential.api_key,
            credential.api_secret
        ) as service:
            balances = await service.get_balance()
            
            # Update database
            with transaction.atomic():
                for currency_code, balance_data in balances.items():
                    ExchangeBalance.objects.update_or_create(
                        user=user,
                        exchange=credential.exchange,
                        currency__symbol=currency_code,
                        defaults={
                            "available": balance_data["available"],
                            "locked": balance_data["locked"],
                            "total": balance_data["total"],
                        }
                    )
            
            return True
            
    except Exception as e:
        logger.error(
            f"Error updating balance for {credential.exchange.name}: {e}"
        )
        raise


@shared_task
def generate_market_summary():
    """
    Generate daily market summary report.
    """
    # Get all active trading pairs
    trading_pairs = TradingPair.objects.filter(is_active=True)
    
    summary = {}
    
    for pair in trading_pairs:
        # Get latest tickers from all exchanges
        tickers = MarketTicker.objects.filter(
            exchange_pair__trading_pair=pair,
            timestamp__gte=timezone.now() - timedelta(hours=1)
        ).select_related("exchange_pair__exchange").order_by(
            "exchange_pair__exchange", "-timestamp"
        ).distinct("exchange_pair__exchange")
        
        if tickers:
            pair_summary = {
                "exchanges": {},
                "avg_price": 0,
                "total_volume": 0,
                "price_spread": 0,
            }
            
            prices = []
            for ticker in tickers:
                exchange_name = ticker.exchange_pair.exchange.name
                pair_summary["exchanges"][exchange_name] = {
                    "last_price": str(ticker.last_price),
                    "volume_24h": str(ticker.volume_24h),
                    "change_24h": str(ticker.change_24h),
                }
                prices.append(ticker.last_price)
                pair_summary["total_volume"] += ticker.volume_24h
            
            if prices:
                pair_summary["avg_price"] = sum(prices) / len(prices)
                pair_summary["price_spread"] = (
                    (max(prices) - min(prices)) / min(prices) * 100
                )
            
            summary[pair.symbol] = pair_summary
    
    # Cache the summary
    cache.set("market_summary", summary, 3600)  # Cache for 1 hour
    
    logger.info(f"Generated market summary for {len(summary)} pairs")
    
    return summary