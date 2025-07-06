"""
Django Ninja API endpoints for exchange operations.
"""

import logging
from datetime import datetime
from typing import List, Optional

from django.shortcuts import get_object_or_404
from ninja import Router
from ninja.security import django_auth

from core.models import Exchange, ExchangeTradingPair
from exchanges.models import ExchangeBalance, ExchangeStatus, MarketTicker
from exchanges.schemas import (
    BalanceSchema,
    ExchangeBalanceSchema,
    ExchangeSchema,
    ExchangeStatusSchema,
    ExchangeTradingPairSchema,
    MarketSummarySchema,
    MarketTickerSchema,
    OrderBookSchema,
    OrderRequestSchema,
    OrderResponseSchema,
    OrderStatusSchema,
    SyncResultSchema,
)
from exchanges.services.nobitex import NobitexService
from exchanges.services.ramzinex import RamzinexService
from exchanges.services.wallex import WallexService
from exchanges.tasks import sync_exchange_markets, update_exchange_tickers

logger = logging.getLogger(__name__)

router = Router()

# Service mapping
EXCHANGE_SERVICES = {
    "nobitex": NobitexService,
    "wallex": WallexService,
    "ramzinex": RamzinexService,
}


@router.get("/", response=List[ExchangeSchema])
def list_exchanges(request):
    """
    List all available exchanges.
    """
    exchanges = Exchange.objects.filter(is_active=True)
    return exchanges


@router.get("/{exchange_code}/status", response=ExchangeStatusSchema)
def get_exchange_status(request, exchange_code: str):
    """
    Get the current status of an exchange.
    """
    exchange = get_object_or_404(Exchange, code=exchange_code)
    status = ExchangeStatus.objects.get_or_create(exchange=exchange)[0]
    
    return {
        "exchange": exchange.name,
        "is_online": status.is_online,
        "last_check": status.last_check,
        "response_time": status.response_time,
        "error_count": status.error_count,
        "last_error": status.last_error,
        "last_error_time": status.last_error_time,
    }


@router.get("/{exchange_code}/markets", response=List[ExchangeTradingPairSchema])
def list_exchange_markets(request, exchange_code: str):
    """
    List all trading pairs available on an exchange.
    """
    exchange = get_object_or_404(Exchange, code=exchange_code)
    pairs = ExchangeTradingPair.objects.filter(
        exchange=exchange, is_active=True
    ).select_related("trading_pair", "trading_pair__base_currency", 
                    "trading_pair__quote_currency")
    
    return pairs


@router.post("/{exchange_code}/sync", response=SyncResultSchema)
def sync_exchange_markets_endpoint(request, exchange_code: str):
    """
    Trigger market synchronization for an exchange.
    """
    exchange = get_object_or_404(Exchange, code=exchange_code)
    
    # Trigger async task
    task = sync_exchange_markets.delay(exchange.id)
    
    return {
        "exchange": exchange.name,
        "success": True,
        "markets_synced": 0,
        "errors": [],
        "timestamp": datetime.now(),
    }


@router.get("/{exchange_code}/ticker/{symbol}", response=MarketTickerSchema)
async def get_ticker(request, exchange_code: str, symbol: str):
    """
    Get ticker data for a specific symbol on an exchange.
    """
    exchange = get_object_or_404(Exchange, code=exchange_code)
    
    # Get the exchange trading pair
    exchange_pair = get_object_or_404(
        ExchangeTradingPair,
        exchange=exchange,
        trading_pair__symbol=symbol
    )
    
    # Get service class
    service_class = EXCHANGE_SERVICES.get(exchange_code)
    if not service_class:
        return {"error": "Exchange service not implemented"}
    
    # Get API credentials if user is authenticated
    api_key = ""
    api_secret = ""
    if request.user.is_authenticated:
        try:
            credential = request.user.api_credentials.get(exchange=exchange)
            api_key = credential.api_key
            api_secret = credential.api_secret
        except:
            pass
    
    # Get ticker data
    async with service_class(exchange, api_key, api_secret) as service:
        ticker = await service.update_ticker(exchange_pair)
    
    return {
        "exchange": exchange.name,
        "symbol": symbol,
        "last_price": ticker.last_price,
        "bid_price": ticker.bid_price,
        "ask_price": ticker.ask_price,
        "volume_24h": ticker.volume_24h,
        "high_24h": ticker.high_24h,
        "low_24h": ticker.low_24h,
        "change_24h": ticker.change_24h,
        "timestamp": ticker.timestamp,
    }


@router.get("/{exchange_code}/orderbook/{symbol}", response=OrderBookSchema)
async def get_order_book(request, exchange_code: str, symbol: str, limit: int = 20):
    """
    Get order book for a specific symbol on an exchange.
    """
    exchange = get_object_or_404(Exchange, code=exchange_code)
    
    # Get the exchange trading pair
    exchange_pair = get_object_or_404(
        ExchangeTradingPair,
        exchange=exchange,
        trading_pair__symbol=symbol
    )
    
    # Get service class
    service_class = EXCHANGE_SERVICES.get(exchange_code)
    if not service_class:
        return {"error": "Exchange service not implemented"}
    
    # Get order book data
    async with service_class(exchange) as service:
        order_book = await service.update_order_book(exchange_pair, limit)
    
    # Format response
    bids = []
    asks = []
    
    for entry in order_book.entries.filter(side="bid").order_by("-price")[:limit]:
        bids.append({
            "price": entry.price,
            "amount": entry.amount,
            "total": entry.total,
        })
    
    for entry in order_book.entries.filter(side="ask").order_by("price")[:limit]:
        asks.append({
            "price": entry.price,
            "amount": entry.amount,
            "total": entry.total,
        })
    
    return {
        "exchange": exchange.name,
        "symbol": symbol,
        "bids": bids,
        "asks": asks,
        "timestamp": order_book.timestamp,
    }


@router.get("/balance", auth=django_auth, response=List[ExchangeBalanceSchema])
async def get_balances(request):
    """
    Get user balances across all exchanges.
    """
    balances = []
    
    for exchange in Exchange.objects.filter(is_active=True):
        try:
            # Get user credentials
            credential = request.user.api_credentials.get(exchange=exchange)
            
            # Get service class
            service_class = EXCHANGE_SERVICES.get(exchange.code)
            if not service_class:
                continue
            
            # Get balances
            async with service_class(
                exchange, credential.api_key, credential.api_secret
            ) as service:
                exchange_balances = await service.get_balance()
                
                # Update database
                for currency_code, balance_data in exchange_balances.items():
                    ExchangeBalance.objects.update_or_create(
                        user=request.user,
                        exchange=exchange,
                        currency__symbol=currency_code,
                        defaults={
                            "available": balance_data["available"],
                            "locked": balance_data["locked"],
                            "total": balance_data["total"],
                        }
                    )
                
                # Format response
                formatted_balances = {}
                for currency_code, balance_data in exchange_balances.items():
                    formatted_balances[currency_code] = BalanceSchema(**balance_data)
                
                balances.append({
                    "exchange": exchange.name,
                    "balances": formatted_balances,
                    "last_updated": datetime.now(),
                })
                
        except Exception as e:
            logger.error(f"Error getting balance for {exchange.name}: {e}")
            continue
    
    return balances


@router.post("/order", auth=django_auth, response=OrderResponseSchema)
async def place_order(request, order: OrderRequestSchema):
    """
    Place an order on an exchange.
    """
    exchange = get_object_or_404(Exchange, code=order.exchange)
    
    # Get user credentials
    try:
        credential = request.user.api_credentials.get(exchange=exchange)
    except:
        return {"error": "API credentials not found for this exchange"}
    
    # Get service class
    service_class = EXCHANGE_SERVICES.get(order.exchange)
    if not service_class:
        return {"error": "Exchange service not implemented"}
    
    # Place order
    async with service_class(
        exchange, credential.api_key, credential.api_secret
    ) as service:
        result = await service.place_order(
            symbol=order.symbol,
            side=order.side,
            order_type=order.order_type,
            amount=order.amount,
            price=order.price,
        )
    
    return OrderResponseSchema(
        exchange=exchange.name,
        **result
    )


@router.delete("/order/{exchange_code}/{order_id}")
async def cancel_order(request, exchange_code: str, order_id: str):
    """
    Cancel an order on an exchange.
    """
    exchange = get_object_or_404(Exchange, code=exchange_code)
    
    # Get user credentials
    try:
        credential = request.user.api_credentials.get(exchange=exchange)
    except:
        return {"error": "API credentials not found for this exchange"}
    
    # Get service class
    service_class = EXCHANGE_SERVICES.get(exchange_code)
    if not service_class:
        return {"error": "Exchange service not implemented"}
    
    # Cancel order
    async with service_class(
        exchange, credential.api_key, credential.api_secret
    ) as service:
        success = await service.cancel_order(order_id)
    
    return {"success": success}


@router.get("/order/{exchange_code}/{order_id}", response=OrderStatusSchema)
async def get_order_status(request, exchange_code: str, order_id: str):
    """
    Get the status of an order.
    """
    exchange = get_object_or_404(Exchange, code=exchange_code)
    
    # Get user credentials
    try:
        credential = request.user.api_credentials.get(exchange=exchange)
    except:
        return {"error": "API credentials not found for this exchange"}
    
    # Get service class
    service_class = EXCHANGE_SERVICES.get(exchange_code)
    if not service_class:
        return {"error": "Exchange service not implemented"}
    
    # Get order status
    async with service_class(
        exchange, credential.api_key, credential.api_secret
    ) as service:
        status = await service.get_order_status(order_id)
    
    return OrderStatusSchema(
        exchange=exchange.name,
        symbol="",  # Would need to be stored or retrieved
        **status
    )


@router.get("/market-summary/{symbol}", response=MarketSummarySchema)
async def get_market_summary(request, symbol: str):
    """
    Get market summary for a symbol across all exchanges.
    """
    summary = {
        "symbol": symbol,
        "exchanges": [],
        "lowest_ask": {},
        "highest_bid": {},
        "volume_24h": {},
        "last_update": datetime.now(),
    }
    
    # Get latest tickers for this symbol from all exchanges
    tickers = MarketTicker.objects.filter(
        exchange_pair__trading_pair__symbol=symbol,
        exchange_pair__is_active=True,
    ).select_related("exchange_pair__exchange").order_by(
        "exchange_pair__exchange", "-timestamp"
    ).distinct("exchange_pair__exchange")
    
    for ticker in tickers:
        exchange_name = ticker.exchange_pair.exchange.name
        summary["exchanges"].append(exchange_name)
        
        if ticker.ask_price:
            if not summary["lowest_ask"] or ticker.ask_price < min(summary["lowest_ask"].values()):
                summary["lowest_ask"] = {exchange_name: ticker.ask_price}
        
        if ticker.bid_price:
            if not summary["highest_bid"] or ticker.bid_price > max(summary["highest_bid"].values()):
                summary["highest_bid"] = {exchange_name: ticker.bid_price}
        
        summary["volume_24h"][exchange_name] = ticker.volume_24h
    
    # Calculate spread
    if summary["lowest_ask"] and summary["highest_bid"]:
        lowest_ask = min(summary["lowest_ask"].values())
        highest_bid = max(summary["highest_bid"].values())
        if highest_bid > 0:
            summary["spread_percentage"] = ((lowest_ask - highest_bid) / highest_bid) * 100
    
    return summary