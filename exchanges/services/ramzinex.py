"""
Fixed Ramzinex exchange service implementation based on official documentation.
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
    FIXED according to official documentation.
    """

    def __init__(self, exchange, api_key: str = "", api_secret: str = ""):
        super().__init__(exchange, api_key, api_secret)
        # Fixed URLs according to documentation
        self.public_base_url = "https://publicapi.ramzinex.com/exchange/api/v1.0/exchange"
        self.private_base_url = "https://api.ramzinex.com/exchange/api/v1.0/exchange"
        self.client.base_url = self.public_base_url
        
        # Store authentication token
        self.access_token = None

    async def authenticate(self) -> bool:
        """
        Get authentication token using API key and secret.
        Required for private endpoints according to documentation.
        """
        if not self.api_key or not self.api_secret:
            return False
            
        auth_data = {
            "api_key": self.api_key,
            "secret": self.api_secret
        }
        
        # Use public URL for authentication
        original_base = self.client.base_url
        self.client.base_url = self.private_base_url
        
        try:
            response = await self.make_request(
                "POST", 
                "/auth/api_key/getToken",
                data=auth_data
            )
            
            if response.get("status") == 0:
                self.access_token = response.get("data", {}).get("token")
                return True
            else:
                self.logger.error(f"Ramzinex authentication failed: {response}")
                return False
                
        except Exception as e:
            self.logger.error(f"Ramzinex authentication error: {e}")
            return False
        finally:
            self.client.base_url = original_base

    def get_headers(self, private: bool = False) -> Dict[str, str]:
        """
        Get headers for Ramzinex API requests.
        Fixed according to documentation.
        """
        headers = {
            "Content-Type": "application/json",
        }
        
        if private and self.access_token:
            # Fixed header names according to documentation
            headers["Authorization2"] = f"Bearer {self.access_token}"
            headers["x-api-key"] = self.api_key
            
        return headers

    async def get_markets(self) -> List[Dict[str, Any]]:
        """
        Get all available markets from Ramzinex.
        Fixed endpoint according to documentation.
        """
        response = await self.make_request("GET", "/pairs")
        
        if response.get("status") != 0:
            raise Exception(f"Failed to get markets: {response}")
        
        markets = []
        pairs = response.get("data", {}).get("pairs", [])
        
        for pair in pairs:
            markets.append({
                "symbol": pair.get("symbol"),
                "base": pair.get("base_currency_symbol"),
                "quote": pair.get("quote_currency_symbol"),
                "pair_id": pair.get("id"),
                "is_active": pair.get("active", 1) == 1,
                "last_price": self.parse_decimal(pair.get("last_price")),
                "volume_24h": self.parse_decimal(pair.get("base_volume")),
                "min_amount": self.parse_decimal(pair.get("min_base_amount")),
                "min_value": self.parse_decimal(pair.get("min_quote_amount")),
            })
        
        return markets

    async def get_ticker(self, symbol: str) -> Dict[str, Any]:
        """
        Get ticker data for a specific symbol.
        Fixed according to documentation.
        """
        pair_id = await self._get_pair_id(symbol)
        
        response = await self.make_request("GET", f"/pairs/{pair_id}")
        
        if response.get("status") != 0:
            raise Exception(f"Failed to get ticker: {response}")
        
        pair = response.get("data", {}).get("pair", {})
        
        return {
            "symbol": symbol,
            "last": self.parse_decimal(pair.get("last_price")),
            "bid": self.parse_decimal(pair.get("buy", 0)),
            "ask": self.parse_decimal(pair.get("sell", 0)),
            "volume": self.parse_decimal(pair.get("base_volume")),
            "high": self.parse_decimal(pair.get("high")),
            "low": self.parse_decimal(pair.get("low")),
            "change": self.parse_decimal(pair.get("change_percent")),
        }

    async def get_order_book(
        self, symbol: str, limit: int = 20
    ) -> Tuple[List[Tuple[Decimal, Decimal]], List[Tuple[Decimal, Decimal]]]:
        """
        Get order book for a specific symbol.
        Fixed endpoint according to documentation.
        """
        pair_id = await self._get_pair_id(symbol)
        
        response = await self.make_request(
            "GET",
            f"/orderbooks/{pair_id}/buys_sells"
        )
        
        if response.get("status") != 0:
            raise Exception(f"Failed to get order book: {response}")
        
        data = response.get("data", {})
        
        # Parse bids (buys)
        bids = []
        for bid in data.get("buys", [])[:limit]:
            price = self.parse_decimal(bid[0])
            amount = self.parse_decimal(bid[1])
            bids.append((price, amount))
        
        # Parse asks (sells)
        asks = []
        for ask in data.get("sells", [])[:limit]:
            price = self.parse_decimal(ask[0])
            amount = self.parse_decimal(ask[1])
            asks.append((price, amount))
        
        return bids, asks

    async def get_balance(self) -> Dict[str, Dict[str, Decimal]]:
        """
        Get account balances from Ramzinex.
        Fixed endpoint and authentication according to documentation.
        """
        if not await self.authenticate():
            raise Exception("Authentication failed")
            
        # Switch to private API
        original_base = self.client.base_url
        self.client.base_url = self.private_base_url
        
        try:
            # Get wallet summary
            response = await self.make_request(
                "GET", 
                "/users/me/funds/summaryDesktop",
                headers=self.get_headers(private=True)
            )
            
            if response.get("status") != 0:
                raise Exception(f"Failed to get balance: {response}")
            
            balances = {}
            for fund in response.get("data", []):
                currency = fund.get("currency", {}).get("symbol")
                if currency:
                    balances[currency.upper()] = {
                        "available": self.parse_decimal(fund.get("balance", 0)),
                        "locked": self.parse_decimal(fund.get("locked", 0)),
                        "total": self.parse_decimal(fund.get("total", 0)),
                    }
            
            return balances
            
        finally:
            self.client.base_url = original_base

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
        Fixed according to documentation endpoints.
        """
        if not await self.authenticate():
            raise Exception("Authentication failed")
            
        pair_id = await self._get_pair_id(symbol)
        
        # Switch to private API
        original_base = self.client.base_url
        self.client.base_url = self.private_base_url
        
        try:
            if order_type.upper() == "LIMIT":
                if not price:
                    raise ValueError("Price required for limit orders")
                
                order_data = {
                    "pair_id": pair_id,
                    "amount": float(amount),
                    "price": float(price),
                    "type": side.lower()  # "buy" or "sell"
                }
                
                endpoint = "/users/me/orders/limit"
                
            elif order_type.upper() == "MARKET":
                order_data = {
                    "pair_id": pair_id,
                    "amount": float(amount),
                    "type": side.lower()  # "buy" or "sell"
                }
                
                endpoint = "/users/me/orders/market"
            else:
                raise ValueError(f"Unsupported order type: {order_type}")
            
            response = await self.make_request(
                "POST", 
                endpoint, 
                data=order_data,
                headers=self.get_headers(private=True)
            )
            
            if response.get("status") != 0:
                raise Exception(f"Failed to place order: {response}")
            
            order = response.get("data", {})
            
            return {
                "order_id": str(order.get("order_id")),
                "symbol": symbol,
                "side": side,
                "type": order_type,
                "price": self.parse_decimal(price) if price else None,
                "amount": self.parse_decimal(amount),
                "status": "NEW",
                "created_at": None,
            }
            
        finally:
            self.client.base_url = original_base

    async def cancel_order(self, order_id: str, symbol: Optional[str] = None) -> bool:
        """
        Cancel an order on Ramzinex.
        Fixed according to documentation.
        """
        if not await self.authenticate():
            raise Exception("Authentication failed")
            
        original_base = self.client.base_url
        self.client.base_url = self.private_base_url
        
        try:
            response = await self.make_request(
                "POST", 
                f"/users/me/orders/{order_id}/cancel",
                headers=self.get_headers(private=True)
            )
            
            return response.get("status") == 0
            
        finally:
            self.client.base_url = original_base

    async def get_24h_stats(self) -> Dict[str, Any]:
        """
        Get 24-hour statistics for all markets.
        Based on documentation endpoint.
        """
        response = await self.make_request("GET", "/chart/statistics-24")
        
        if response.get("status") != 0:
            raise Exception(f"Failed to get 24h stats: {response}")
        
        return response.get("data", {})

    async def _get_pair_id(self, symbol: str) -> int:
        """
        Get pair ID for a symbol from Ramzinex.
        Required for most endpoints.
        """
        markets = await self.get_markets()
        for market in markets:
            if market["symbol"] == symbol:
                return market["pair_id"]
        
        raise ValueError(f"Symbol {symbol} not found")

    def _normalize_order_status(self, status: Any) -> str:
        """
        Normalize order status according to Ramzinex documentation.
        """
        status_map = {
            1: "NEW",      # Open orders
            2: "CANCELED", # Canceled orders  
            3: "FILLED",   # Completed orders
            4: "PARTIALLY_FILLED"  # Partially completed
        }
        return status_map.get(status, "UNKNOWN")