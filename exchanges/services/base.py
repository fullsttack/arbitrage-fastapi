import logging
from abc import ABC, abstractmethod
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

import httpx
from django.core.cache import cache
from django.utils import timezone

from core.exceptions import ExchangeAPIError, RateLimitError
from core.models import Exchange, ExchangeTradingPair
from exchanges.models import MarketTicker, OrderBook, OrderBookEntry

logger = logging.getLogger(__name__)


class BaseExchangeService(ABC):
    """
    Abstract base class for exchange services.
    """

    def __init__(self, exchange: Exchange, api_key: str = "", api_secret: str = ""):
        self.exchange = exchange
        self.api_key = api_key
        self.api_secret = api_secret
        self.client = httpx.AsyncClient(
            base_url=exchange.api_url,
            timeout=30.0,
            limits=httpx.Limits(max_keepalive_connections=5, max_connections=10),
        )
        self.rate_limiter_key = f"rate_limit:{exchange.code}"
        
    async def __aenter__(self):
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()

    def check_rate_limit(self) -> bool:
        """
        Check if we're within rate limits.
        """
        current_count = cache.get(self.rate_limiter_key, 0)
        if current_count >= self.exchange.rate_limit:
            raise RateLimitError(f"Rate limit exceeded for {self.exchange.name}")
        
        # Increment counter
        cache.set(self.rate_limiter_key, current_count + 1, 60)  # Reset every minute
        return True

    async def make_request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict] = None,
        data: Optional[Dict] = None,
        headers: Optional[Dict] = None,
    ) -> Dict[str, Any]:
        """
        Make an HTTP request to the exchange API.
        """
        self.check_rate_limit()
        
        try:
            response = await self.client.request(
                method=method,
                url=endpoint,
                params=params,
                json=data,
                headers=headers or self.get_headers(),
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error from {self.exchange.name}: {e}")
            raise ExchangeAPIError(f"HTTP error: {e}")
        except Exception as e:
            logger.error(f"Request error from {self.exchange.name}: {e}")
            raise ExchangeAPIError(f"Request error: {e}")

    @abstractmethod
    def get_headers(self) -> Dict[str, str]:
        """
        Get headers for API requests.
        """
        pass

    @abstractmethod
    async def get_markets(self) -> List[Dict[str, Any]]:
        """
        Get all available markets from the exchange.
        """
        pass

    @abstractmethod
    async def get_ticker(self, symbol: str) -> Dict[str, Any]:
        """
        Get ticker data for a specific symbol.
        """
        pass

    @abstractmethod
    async def get_order_book(
        self, symbol: str, limit: int = 20
    ) -> Tuple[List[Tuple[Decimal, Decimal]], List[Tuple[Decimal, Decimal]]]:
        """
        Get order book for a specific symbol.
        Returns (bids, asks) where each entry is (price, amount).
        """
        pass

    @abstractmethod
    async def get_balance(self) -> Dict[str, Dict[str, Decimal]]:
        """
        Get account balances.
        Returns dict with currency as key and {available, locked, total} as value.
        """
        pass

    @abstractmethod
    async def place_order(
        self,
        symbol: str,
        side: str,
        order_type: str,
        amount: Decimal,
        price: Optional[Decimal] = None,
    ) -> Dict[str, Any]:
        """
        Place an order on the exchange.
        """
        pass

    @abstractmethod
    async def cancel_order(self, order_id: str, symbol: Optional[str] = None) -> bool:
        """
        Cancel an order.
        """
        pass

    @abstractmethod
    async def get_order_status(
        self, order_id: str, symbol: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get the status of a specific order.
        """
        pass

    async def sync_markets(self) -> None:
        """
        Sync available markets with the database.
        """
        try:
            markets = await self.get_markets()
            logger.info(f"Syncing {len(markets)} markets for {self.exchange.name}")
            
            # Process markets and update database
            # This would be implemented based on specific exchange response format
            
        except Exception as e:
            logger.error(f"Error syncing markets for {self.exchange.name}: {e}")
            raise

    async def update_ticker(self, exchange_pair: ExchangeTradingPair) -> MarketTicker:
        """
        Update ticker data for a trading pair.
        """
        try:
            ticker_data = await self.get_ticker(exchange_pair.exchange_symbol)
            
            # Create ticker record
            ticker = MarketTicker.objects.create(
                exchange_pair=exchange_pair,
                timestamp=timezone.now(),
                last_price=Decimal(str(ticker_data.get("last", 0))),
                bid_price=Decimal(str(ticker_data.get("bid", 0))),
                ask_price=Decimal(str(ticker_data.get("ask", 0))),
                volume_24h=Decimal(str(ticker_data.get("volume", 0))),
                high_24h=Decimal(str(ticker_data.get("high", 0))),
                low_24h=Decimal(str(ticker_data.get("low", 0))),
                change_24h=Decimal(str(ticker_data.get("change", 0))),
            )
            
            return ticker
            
        except Exception as e:
            logger.error(
                f"Error updating ticker for {exchange_pair} on {self.exchange.name}: {e}"
            )
            raise

    async def update_order_book(
        self, exchange_pair: ExchangeTradingPair, limit: int = 20
    ) -> OrderBook:
        """
        Update order book data for a trading pair.
        """
        try:
            bids, asks = await self.get_order_book(
                exchange_pair.exchange_symbol, limit
            )
            
            # Create order book record
            order_book = OrderBook.objects.create(
                exchange_pair=exchange_pair,
                timestamp=timezone.now(),
            )
            
            # Create bid entries
            for position, (price, amount) in enumerate(bids):
                OrderBookEntry.objects.create(
                    order_book=order_book,
                    side="bid",
                    price=price,
                    amount=amount,
                    position=position,
                )
            
            # Create ask entries
            for position, (price, amount) in enumerate(asks):
                OrderBookEntry.objects.create(
                    order_book=order_book,
                    side="ask",
                    price=price,
                    amount=amount,
                    position=position,
                )
            
            return order_book
            
        except Exception as e:
            logger.error(
                f"Error updating order book for {exchange_pair} on {self.exchange.name}: {e}"
            )
            raise

    def normalize_symbol(self, base: str, quote: str) -> str:
        """
        Normalize trading pair symbol for the exchange.
        Default implementation, can be overridden by specific exchanges.
        """
        return f"{base.upper()}{quote.upper()}"

    def parse_decimal(self, value: Any) -> Decimal:
        """
        Safely parse a value to Decimal.
        """
        if value is None:
            return Decimal("0")
        return Decimal(str(value))