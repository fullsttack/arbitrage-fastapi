import hashlib
import hmac
import json
import time
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

from exchanges.services.base import BaseExchangeService


class NobitexService(BaseExchangeService):
    """
    Service for interacting with Nobitex exchange API.
    """

    def get_headers(self) -> Dict[str, str]:
        """
        Get headers for Nobitex API requests.
        """
        headers = {
            "Content-Type": "application/json",
        }
        
        if self.api_key:
            headers["Authorization"] = f"Token {self.api_key}"
            
        return headers

    async def get_markets(self) -> List[Dict[str, Any]]:
        """
        Get all available markets from Nobitex.
        """
        response = await self.make_request("GET", "/market/stats")
        
        if response.get("status") != "ok":
            raise Exception(f"Failed to get markets: {response}")
        
        markets = []
        for symbol, data in response.get("stats", {}).items():
            # Parse symbol (e.g., "btc-rls" -> base: BTC, quote: RLS)
            parts = symbol.split("-")
            if len(parts) == 2:
                markets.append({
                    "symbol": symbol,
                    "base": parts[0].upper(),
                    "quote": parts[1].upper(),
                    "is_active": not data.get("isClosed", False),
                    "last_price": self.parse_decimal(data.get("latest")),
                    "volume_24h": self.parse_decimal(data.get("volumeSrc")),
                    "bid": self.parse_decimal(data.get("bestBuy")),
                    "ask": self.parse_decimal(data.get("bestSell")),
                })
        
        return markets

    async def get_ticker(self, symbol: str) -> Dict[str, Any]:
        """
        Get ticker data for a specific symbol.
        """
        # Convert symbol format (e.g., BTCUSDT -> btc-usdt)
        formatted_symbol = self._format_symbol_for_api(symbol)
        
        response = await self.make_request(
            "GET",
            "/market/stats",
            params={"srcCurrency": formatted_symbol.split("-")[0], 
                   "dstCurrency": formatted_symbol.split("-")[1]}
        )
        
        if response.get("status") != "ok":
            raise Exception(f"Failed to get ticker: {response}")
        
        data = response.get("stats", {}).get(formatted_symbol, {})
        
        return {
            "symbol": symbol,
            "last": self.parse_decimal(data.get("latest")),
            "bid": self.parse_decimal(data.get("bestBuy")),
            "ask": self.parse_decimal(data.get("bestSell")),
            "volume": self.parse_decimal(data.get("volumeSrc")),
            "high": self.parse_decimal(data.get("dayHigh")),
            "low": self.parse_decimal(data.get("dayLow")),
            "change": self.parse_decimal(data.get("dayChange")),
        }

    async def get_order_book(
        self, symbol: str, limit: int = 20
    ) -> Tuple[List[Tuple[Decimal, Decimal]], List[Tuple[Decimal, Decimal]]]:
        """
        Get order book for a specific symbol.
        """
        # Convert symbol format (e.g., BTCUSDT -> BTCIRT for Nobitex)
        formatted_symbol = self._format_symbol_for_orderbook(symbol)
        
        response = await self.make_request("GET", f"/v3/orderbook/{formatted_symbol}")
        
        if response.get("status") != "ok":
            raise Exception(f"Failed to get order book: {response}")
        
        # Parse bids and asks
        bids = []
        for bid in response.get("bids", [])[:limit]:
            price = self.parse_decimal(bid[0])
            amount = self.parse_decimal(bid[1])
            bids.append((price, amount))
        
        asks = []
        for ask in response.get("asks", [])[:limit]:
            price = self.parse_decimal(ask[0])
            amount = self.parse_decimal(ask[1])
            asks.append((price, amount))
        
        return bids, asks

    async def get_balance(self) -> Dict[str, Dict[str, Decimal]]:
        """
        Get account balances from Nobitex.
        """
        response = await self.make_request("GET", "/users/wallets/list")
        
        if response.get("status") != "ok":
            raise Exception(f"Failed to get balance: {response}")
        
        balances = {}
        for wallet in response.get("wallets", []):
            currency = wallet.get("currency", "").upper()
            balances[currency] = {
                "available": self.parse_decimal(wallet.get("activeBalance", 0)),
                "locked": self.parse_decimal(wallet.get("blockedBalance", 0)),
                "total": self.parse_decimal(wallet.get("balance", 0)),
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
        Place an order on Nobitex.
        """
        # Parse symbol to get source and destination currencies
        base, quote = self._parse_symbol(symbol)
        
        # Prepare order data
        order_data = {
            "type": side.lower(),
            "srcCurrency": base.lower(),
            "dstCurrency": quote.lower(),
            "amount": str(amount),
            "execution": "market" if order_type.upper() == "MARKET" else "limit",
        }
        
        if price and order_type.upper() != "MARKET":
            order_data["price"] = str(price)
        
        response = await self.make_request("POST", "/market/orders/add", data=order_data)
        
        if response.get("status") != "ok":
            raise Exception(f"Failed to place order: {response}")
        
        order = response.get("order", {})
        
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
        Cancel an order on Nobitex.
        """
        response = await self.make_request(
            "POST",
            "/market/orders/update-status",
            data={"order": int(order_id), "status": "canceled"},
        )
        
        return response.get("status") == "ok"

    async def get_order_status(
        self, order_id: str, symbol: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get the status of a specific order.
        """
        response = await self.make_request(
            "POST",
            "/market/orders/status",
            data={"id": int(order_id)},
        )
        
        if response.get("status") != "ok":
            raise Exception(f"Failed to get order status: {response}")
        
        order = response.get("order", {})
        
        return {
            "order_id": str(order.get("id")),
            "status": self._normalize_order_status(order.get("status")),
            "filled_amount": self.parse_decimal(order.get("matchedAmount", 0)),
            "remaining_amount": self.parse_decimal(order.get("unmatchedAmount", 0)),
            "price": self.parse_decimal(order.get("price")),
            "created_at": order.get("created_at"),
        }

    def _format_symbol_for_api(self, symbol: str) -> str:
        """
        Convert symbol from standard format to Nobitex API format.
        e.g., BTCUSDT -> btc-usdt
        """
        # Handle common conversions
        if symbol.endswith("IRT"):
            base = symbol[:-3].lower()
            return f"{base}-rls"
        elif symbol.endswith("USDT"):
            base = symbol[:-4].lower()
            return f"{base}-usdt"
        else:
            # Try to split at common points
            for quote in ["USDT", "IRT", "BTC", "ETH"]:
                if quote in symbol:
                    base = symbol.replace(quote, "").lower()
                    quote = quote.lower()
                    if quote == "irt":
                        quote = "rls"
                    return f"{base}-{quote}"
        
        return symbol.lower()

    def _format_symbol_for_orderbook(self, symbol: str) -> str:
        """
        Convert symbol for orderbook API.
        e.g., BTCUSDT -> BTCUSDT (no change for most pairs)
        """
        # Nobitex uses uppercase symbols for orderbook
        return symbol.upper()

    def _parse_symbol(self, symbol: str) -> Tuple[str, str]:
        """
        Parse symbol into base and quote currencies.
        """
        # Common patterns
        if symbol.endswith("USDT"):
            return symbol[:-4], "USDT"
        elif symbol.endswith("IRT"):
            return symbol[:-3], "RLS"
        elif symbol.endswith("RLS"):
            return symbol[:-3], "RLS"
        elif symbol.endswith("BTC"):
            return symbol[:-3], "BTC"
        elif symbol.endswith("ETH"):
            return symbol[:-3], "ETH"
        
        # Default: assume 3-letter base currency
        return symbol[:3], symbol[3:]

    def _normalize_order_status(self, status: str) -> str:
        """
        Normalize order status to standard format.
        """
        status_map = {
            "Active": "OPEN",
            "Done": "FILLED",
            "Canceled": "CANCELLED",
            "Inactive": "PENDING",
        }
        return status_map.get(status, status.upper())