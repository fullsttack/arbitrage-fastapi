"""
Ramzinex exchange service implementation.
"""

import hashlib
import hmac
import time
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

from exchanges.services.base import BaseExchangeService


class RamzinexService(BaseExchangeService):
    """
    Service for interacting with Ramzinex exchange API.
    """

    def __init__(self, exchange, api_key: str = "", api_secret: str = ""):
        super().__init__(exchange, api_key, api_secret)
        # Ramzinex API base URL
        self.client.base_url = "https://publicapi.ramzinex.com"

    def get_headers(self) -> Dict[str, str]:
        """
        Get headers for Ramzinex API requests.
        """
        headers = {
            "Content-Type": "application/json",
        }
        
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
            
        return headers

    def _generate_signature(self, data: str) -> str:
        """
        Generate HMAC signature for authenticated requests.
        """
        if not self.api_secret:
            return ""
        
        signature = hmac.new(
            self.api_secret.encode(),
            data.encode(),
            hashlib.sha256
        ).hexdigest()
        
        return signature

    async def get_markets(self) -> List[Dict[str, Any]]:
        """
        Get all available markets from Ramzinex.
        """
        response = await self.make_request("GET", "/exchange/api/v1.0/public/exchange/pairs")
        
        if response.get("status") != 0:
            raise Exception(f"Failed to get markets: {response.get('msg')}")
        
        markets = []
        for pair in response.get("data", []):
            markets.append({
                "symbol": f"{pair['base_currency_symbol']['en'].upper()}{pair['quote_currency_symbol']['en'].upper()}",
                "base": pair["base_currency_symbol"]["en"].upper(),
                "quote": pair["quote_currency_symbol"]["en"].upper(),
                "is_active": pair.get("active", 0) == 1,
                "last_price": self.parse_decimal(pair.get("last_price")),
                "volume_24h": self.parse_decimal(pair.get("base_volume")),
                "pair_id": pair.get("pair_id"),
                "min_amount": self.parse_decimal(pair.get("buy_min_base_amount", 0)),
                "min_price": self.parse_decimal(pair.get("buy_min_quote_amount", 0)),
            })
        
        return markets

    async def get_ticker(self, symbol: str) -> Dict[str, Any]:
        """
        Get ticker data for a specific symbol.
        """
        # Get pair ID for the symbol
        pair_id = await self._get_pair_id(symbol)
        
        response = await self.make_request(
            "GET",
            f"/exchange/api/v1.0/public/exchange/pairs/{pair_id}"
        )
        
        if response.get("status") != 0:
            raise Exception(f"Failed to get ticker: {response.get('msg')}")
        
        data = response.get("data", {})
        
        return {
            "symbol": symbol,
            "last": self.parse_decimal(data.get("last_price")),
            "bid": self.parse_decimal(data.get("buy", 0)),
            "ask": self.parse_decimal(data.get("sell", 0)),
            "volume": self.parse_decimal(data.get("base_volume")),
            "high": self.parse_decimal(data.get("high")),
            "low": self.parse_decimal(data.get("low")),
            "change": self.parse_decimal(data.get("base_volume_change")),
        }

    async def get_order_book(
        self, symbol: str, limit: int = 20
    ) -> Tuple[List[Tuple[Decimal, Decimal]], List[Tuple[Decimal, Decimal]]]:
        """
        Get order book for a specific symbol.
        """
        # Get pair ID for the symbol
        pair_id = await self._get_pair_id(symbol)
        
        response = await self.make_request(
            "GET",
            f"/exchange/api/v1.0/public/exchange/orderbooks/{pair_id}"
        )
        
        if response.get("status") != 0:
            raise Exception(f"Failed to get order book: {response.get('msg')}")
        
        data = response.get("data", {})
        
        # Parse bids
        bids = []
        for bid in data.get("buys", [])[:limit]:
            price = self.parse_decimal(bid[0])
            amount = self.parse_decimal(bid[1])
            bids.append((price, amount))
        
        # Parse asks
        asks = []
        for ask in data.get("sells", [])[:limit]:
            price = self.parse_decimal(ask[0])
            amount = self.parse_decimal(ask[1])
            asks.append((price, amount))
        
        return bids, asks

    async def get_balance(self) -> Dict[str, Dict[str, Decimal]]:
        """
        Get account balances from Ramzinex.
        """
        # This endpoint requires authentication
        timestamp = str(int(time.time()))
        signature = self._generate_signature(f"GET/exchange/users/me/funds{timestamp}")
        
        headers = self.get_headers()
        headers["X-SIGNATURE"] = signature
        headers["X-TIMESTAMP"] = timestamp
        
        response = await self.make_request(
            "GET", "/exchange/users/me/funds", headers=headers
        )
        
        if response.get("status") != 0:
            raise Exception(f"Failed to get balance: {response.get('msg')}")
        
        balances = {}
        for fund in response.get("data", {}).get("funds", []):
            currency = fund.get("currency", {}).get("symbol", {}).get("en", "").upper()
            balances[currency] = {
                "available": self.parse_decimal(fund.get("balance", 0)),
                "locked": self.parse_decimal(fund.get("locked", 0)),
                "total": self.parse_decimal(fund.get("balance", 0)) + 
                        self.parse_decimal(fund.get("locked", 0)),
            }
        
        return balances

    async def place_order(
        self,
        symbol: str,
        side: str,
        order_type: str,
        amount: Decimal,
        price: Optional[Decimal] = None,
    ) -> Dict[str, Any]:
        """
        Place an order on Ramzinex.
        """
        # Get pair ID for the symbol
        pair_id = await self._get_pair_id(symbol)
        
        order_data = {
            "pair_id": pair_id,
            "type": 1 if side.upper() == "BUY" else 2,  # 1 for buy, 2 for sell
            "amount": str(amount),
        }
        
        if order_type.upper() == "LIMIT" and price:
            order_data["price"] = str(price)
        
        timestamp = str(int(time.time()))
        data_str = f"POST/exchange/users/me/orders{timestamp}{str(order_data)}"
        signature = self._generate_signature(data_str)
        
        headers = self.get_headers()
        headers["X-SIGNATURE"] = signature
        headers["X-TIMESTAMP"] = timestamp
        
        response = await self.make_request(
            "POST", "/exchange/users/me/orders", data=order_data, headers=headers
        )
        
        if response.get("status") != 0:
            raise Exception(f"Failed to place order: {response.get('msg')}")
        
        order = response.get("data", {})
        
        return {
            "order_id": str(order.get("id")),
            "symbol": symbol,
            "side": side,
            "type": order_type,
            "price": self.parse_decimal(order.get("price")),
            "amount": self.parse_decimal(order.get("amount")),
            "status": self._normalize_order_status(order.get("status")),
            "created_at": order.get("created_at"),
        }

    async def cancel_order(self, order_id: str, symbol: Optional[str] = None) -> bool:
        """
        Cancel an order on Ramzinex.
        """
        timestamp = str(int(time.time()))
        data_str = f"DELETE/exchange/users/me/orders/{order_id}{timestamp}"
        signature = self._generate_signature(data_str)
        
        headers = self.get_headers()
        headers["X-SIGNATURE"] = signature
        headers["X-TIMESTAMP"] = timestamp
        
        response = await self.make_request(
            "DELETE", f"/exchange/users/me/orders/{order_id}", headers=headers
        )
        
        return response.get("status") == 0

    async def get_order_status(
        self, order_id: str, symbol: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get the status of a specific order.
        """
        timestamp = str(int(time.time()))
        data_str = f"GET/exchange/users/me/orders/{order_id}{timestamp}"
        signature = self._generate_signature(data_str)
        
        headers = self.get_headers()
        headers["X-SIGNATURE"] = signature
        headers["X-TIMESTAMP"] = timestamp
        
        response = await self.make_request(
            "GET", f"/exchange/users/me/orders/{order_id}", headers=headers
        )
        
        if response.get("status") != 0:
            raise Exception(f"Failed to get order status: {response.get('msg')}")
        
        order = response.get("data", {})
        
        return {
            "order_id": order_id,
            "status": self._normalize_order_status(order.get("status")),
            "filled_amount": self.parse_decimal(order.get("closed_amount", 0)),
            "remaining_amount": self.parse_decimal(order.get("amount", 0)) - 
                              self.parse_decimal(order.get("closed_amount", 0)),
            "price": self.parse_decimal(order.get("price")),
            "created_at": order.get("created_at"),
        }

    async def _get_pair_id(self, symbol: str) -> int:
        """
        Get pair ID for a given symbol.
        """
        # Cache pair IDs to avoid repeated API calls
        cache_key = f"ramzinex_pair_id:{symbol}"
        pair_id = cache.get(cache_key) # type: ignore
        
        if pair_id:
            return pair_id
        
        # Get all markets and find the pair ID
        markets = await self.get_markets()
        for market in markets:
            if market["symbol"] == symbol:
                pair_id = market["pair_id"]
                cache.set(cache_key, pair_id, 3600)  # Cache for 1 hour # type: ignore
                return pair_id
        
        raise Exception(f"Pair ID not found for symbol: {symbol}")

    def _normalize_order_status(self, status: int) -> str:
        """
        Normalize order status to standard format.
        """
        # Ramzinex status codes (assumed based on common patterns)
        status_map = {
            0: "PENDING",
            1: "OPEN",
            2: "PARTIAL",
            3: "FILLED",
            4: "CANCELLED",
            5: "REJECTED",
        }
        return status_map.get(status, "UNKNOWN")