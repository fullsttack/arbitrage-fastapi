"""
Wallex exchange service implementation.
"""

from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

from exchanges.services.base import BaseExchangeService


class WallexService(BaseExchangeService):
    """
    Service for interacting with Wallex exchange API.
    """

    def get_headers(self) -> Dict[str, str]:
        """
        Get headers for Wallex API requests.
        """
        headers = {
            "Content-Type": "application/json",
        }
        
        if self.api_key:
            headers["X-API-Key"] = self.api_key
            
        return headers

    async def get_markets(self) -> List[Dict[str, Any]]:
        """
        Get all available markets from Wallex.
        """
        response = await self.make_request("GET", "/v1/markets")
        
        if not response.get("success"):
            raise Exception(f"Failed to get markets: {response.get('message')}")
        
        markets = []
        for symbol, data in response.get("result", {}).get("symbols", {}).items():
            markets.append({
                "symbol": symbol,
                "base": data.get("baseAsset"),
                "quote": data.get("quoteAsset"),
                "is_active": True,  # Wallex doesn't provide this directly
                "last_price": self.parse_decimal(
                    data.get("stats", {}).get("lastPrice")
                ),
                "volume_24h": self.parse_decimal(
                    data.get("stats", {}).get("24h_volume")
                ),
                "bid": self.parse_decimal(data.get("stats", {}).get("bidPrice")),
                "ask": self.parse_decimal(data.get("stats", {}).get("askPrice")),
                "min_qty": self.parse_decimal(data.get("minQty")),
                "min_notional": self.parse_decimal(data.get("minNotional")),
                "step_size": data.get("stepSize"),
                "tick_size": data.get("tickSize"),
            })
        
        return markets

    async def get_ticker(self, symbol: str) -> Dict[str, Any]:
        """
        Get ticker data for a specific symbol.
        """
        response = await self.make_request("GET", "/v1/markets")
        
        if not response.get("success"):
            raise Exception(f"Failed to get ticker: {response.get('message')}")
        
        data = response.get("result", {}).get("symbols", {}).get(symbol, {})
        stats = data.get("stats", {})
        
        return {
            "symbol": symbol,
            "last": self.parse_decimal(stats.get("lastPrice")),
            "bid": self.parse_decimal(stats.get("bidPrice")),
            "ask": self.parse_decimal(stats.get("askPrice")),
            "volume": self.parse_decimal(stats.get("24h_volume")),
            "high": self.parse_decimal(stats.get("24h_highPrice")),
            "low": self.parse_decimal(stats.get("24h_lowPrice")),
            "change": self.parse_decimal(stats.get("24h_ch")),
        }

    async def get_order_book(
        self, symbol: str, limit: int = 20
    ) -> Tuple[List[Tuple[Decimal, Decimal]], List[Tuple[Decimal, Decimal]]]:
        """
        Get order book for a specific symbol.
        """
        response = await self.make_request(
            "GET", "/v1/depth", params={"symbol": symbol}
        )
        
        if not response.get("success"):
            raise Exception(f"Failed to get order book: {response.get('message')}")
        
        result = response.get("result", {})
        
        # Parse bids
        bids = []
        for bid in result.get("bid", [])[:limit]:
            price = self.parse_decimal(bid.get("price"))
            amount = self.parse_decimal(bid.get("quantity"))
            bids.append((price, amount))
        
        # Parse asks
        asks = []
        for ask in result.get("ask", [])[:limit]:
            price = self.parse_decimal(ask.get("price"))
            amount = self.parse_decimal(ask.get("quantity"))
            asks.append((price, amount))
        
        return bids, asks

    async def get_balance(self) -> Dict[str, Dict[str, Decimal]]:
        """
        Get account balances from Wallex.
        """
        response = await self.make_request("GET", "/v1/account/balances")
        
        if not response.get("success"):
            raise Exception(f"Failed to get balance: {response.get('message')}")
        
        balances = {}
        for currency, data in response.get("result", {}).get("balances", {}).items():
            balances[currency] = {
                "available": self.parse_decimal(data.get("value", 0)),
                "locked": self.parse_decimal(data.get("locked", 0)),
                "total": self.parse_decimal(data.get("value", 0)) + 
                        self.parse_decimal(data.get("locked", 0)),
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
        Place an order on Wallex.
        """
        order_data = {
            "symbol": symbol,
            "type": order_type.upper(),
            "side": side.upper(),
            "quantity": str(amount),
        }
        
        if price and order_type.upper() == "LIMIT":
            order_data["price"] = str(price)
        
        response = await self.make_request("POST", "/v1/account/orders", data=order_data)
        
        if not response.get("success"):
            raise Exception(f"Failed to place order: {response.get('message')}")
        
        order = response.get("result", {})
        
        return {
            "order_id": order.get("clientOrderId"),
            "symbol": symbol,
            "side": side,
            "type": order_type,
            "price": self.parse_decimal(order.get("price")),
            "amount": self.parse_decimal(order.get("origQty")),
            "status": self._normalize_order_status(order.get("status")),
            "created_at": order.get("created_at"),
        }

    async def cancel_order(self, order_id: str, symbol: Optional[str] = None) -> bool:
        """
        Cancel an order on Wallex.
        """
        params = {"clientOrderId": order_id}
        
        response = await self.make_request("DELETE", "/v1/account/orders", params=params)
        
        return response.get("success", False)

    async def get_order_status(
        self, order_id: str, symbol: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get the status of a specific order.
        """
        response = await self.make_request(
            "GET", f"/v1/account/orders/{order_id}"
        )
        
        if not response.get("success"):
            raise Exception(f"Failed to get order status: {response.get('message')}")
        
        order = response.get("result", {})
        
        return {
            "order_id": order_id,
            "status": self._normalize_order_status(order.get("status")),
            "filled_amount": self.parse_decimal(order.get("executedQty", 0)),
            "remaining_amount": self.parse_decimal(order.get("origQty", 0)) - 
                              self.parse_decimal(order.get("executedQty", 0)),
            "price": self.parse_decimal(order.get("price")),
            "created_at": order.get("created_at"),
        }

    async def get_trade_history(
        self, symbol: Optional[str] = None, limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get trade history from Wallex.
        """
        params = {}
        if symbol:
            params["symbol"] = symbol
        
        response = await self.make_request(
            "GET", "/v1/account/trades", params=params
        )
        
        if not response.get("success"):
            raise Exception(f"Failed to get trade history: {response.get('message')}")
        
        trades = []
        for trade in response.get("result", {}).get("AccountLatestTrades", [])[:limit]:
            trades.append({
                "symbol": trade.get("symbol"),
                "price": self.parse_decimal(trade.get("price")),
                "amount": self.parse_decimal(trade.get("quantity")),
                "side": "buy" if trade.get("isBuyer") else "sell",
                "fee": self.parse_decimal(trade.get("fee")),
                "fee_asset": trade.get("feeAsset"),
                "timestamp": trade.get("timestamp"),
            })
        
        return trades

    def _normalize_order_status(self, status: str) -> str:
        """
        Normalize order status to standard format.
        """
        status_map = {
            "NEW": "OPEN",
            "PARTIALLY_FILLED": "PARTIAL",
            "FILLED": "FILLED",
            "CANCELED": "CANCELLED",
            "REJECTED": "REJECTED",
        }
        return status_map.get(status.upper(), status.upper())