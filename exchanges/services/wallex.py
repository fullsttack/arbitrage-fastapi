"""
Fixed Wallex exchange service implementation based on official documentation.
"""

from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

from exchanges.services.base import BaseExchangeService


class WallexService(BaseExchangeService):
    """
    Service for interacting with Wallex exchange API.
    FIXED according to official documentation.
    """

    def __init__(self, exchange, api_key: str = "", api_secret: str = ""):
        super().__init__(exchange, api_key, api_secret)
        # Fixed base URL according to documentation
        self.client.base_url = "https://api.wallex.ir"

    def get_headers(self) -> Dict[str, str]:
        """
        Get headers for Wallex API requests.
        Authentication according to documentation.
        """
        headers = {
            "Content-Type": "application/json",
        }
        
        if self.api_key:
            # Fixed header name according to documentation
            headers["X-API-Key"] = self.api_key
            
        return headers

    async def get_markets(self) -> List[Dict[str, Any]]:
        """
        Get all available markets from Wallex.
        Fixed endpoint according to documentation.
        """
        response = await self.make_request("GET", "/v1/markets")
        
        if not response.get("success"):
            raise Exception(f"Failed to get markets: {response.get('message')}")
        
        markets = []
        symbols = response.get("result", {}).get("symbols", {})
        
        for symbol, data in symbols.items():
            stats = data.get("stats", {})
            markets.append({
                "symbol": symbol,
                "base": data.get("baseAsset"),
                "quote": data.get("quoteAsset"),
                "base_precision": data.get("baseAssetPrecision"),
                "quote_precision": data.get("quotePrecision"),
                "fa_name": data.get("faName"),
                "fa_base_asset": data.get("faBaseAsset"),
                "fa_quote_asset": data.get("faQuoteAsset"),
                "step_size": data.get("stepSize"),
                "tick_size": data.get("tickSize"),
                "min_qty": self.parse_decimal(data.get("minQty")),
                "min_notional": self.parse_decimal(data.get("minNotional")),
                "max_qty": self.parse_decimal(data.get("maxQty", 0)),
                "is_active": True,  # Wallex shows only active markets
                "last_price": self.parse_decimal(stats.get("lastPrice")),
                "volume_24h": self.parse_decimal(stats.get("24h_volume")),
                "volume_24h_quote": self.parse_decimal(stats.get("24h_quoteVolume")),
                "bid": self.parse_decimal(stats.get("bidPrice")),
                "ask": self.parse_decimal(stats.get("askPrice")),
                "bid_volume": self.parse_decimal(stats.get("bidVolume")),
                "ask_volume": self.parse_decimal(stats.get("askVolume")),
                "bid_count": stats.get("bidCount"),
                "ask_count": stats.get("askCount"),
                "high_24h": self.parse_decimal(stats.get("24h_highPrice")),
                "low_24h": self.parse_decimal(stats.get("24h_lowPrice")),
                "change_24h": stats.get("24h_ch"),
                "change_7d": stats.get("7d_ch"),
                "volume_7d": self.parse_decimal(stats.get("7d_volume")),
                "last_trade_side": stats.get("lastTradeSide"),
                "direction": stats.get("direction", {}),
                "created_at": data.get("createdAt"),
            })
        
        return markets

    async def get_ticker(self, symbol: str) -> Dict[str, Any]:
        """
        Get ticker data for a specific symbol.
        Uses markets endpoint to get specific symbol data.
        """
        markets = await self.get_markets()
        
        for market in markets:
            if market["symbol"] == symbol:
                return {
                    "symbol": symbol,
                    "last": market["last_price"],
                    "bid": market["bid"],
                    "ask": market["ask"],
                    "volume": market["volume_24h"],
                    "high": market["high_24h"],
                    "low": market["low_24h"],
                    "change": market["change_24h"],
                    "change_percent": market["change_24h"],
                }
        
        raise ValueError(f"Symbol {symbol} not found")

    async def get_order_book(
        self, symbol: str, limit: int = 20
    ) -> Tuple[List[Tuple[Decimal, Decimal]], List[Tuple[Decimal, Decimal]]]:
        """
        Get order book for a specific symbol.
        Fixed endpoint according to documentation.
        """
        params = {"symbol": symbol}
        response = await self.make_request("GET", "/v1/depth", params=params)
        
        if not response.get("success"):
            raise Exception(f"Failed to get order book: {response.get('message')}")
        
        data = response.get("result", {})
        
        # Parse bids
        bids = []
        for bid in data.get("bid", [])[:limit]:
            price = self.parse_decimal(bid.get("price"))
            quantity = self.parse_decimal(bid.get("quantity"))
            bids.append((price, quantity))
        
        # Parse asks
        asks = []
        for ask in data.get("ask", [])[:limit]:
            price = self.parse_decimal(ask.get("price"))
            quantity = self.parse_decimal(ask.get("quantity"))
            asks.append((price, quantity))
        
        return bids, asks

    async def get_trades(self, symbol: str, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Get recent trades for a specific symbol.
        Fixed endpoint according to documentation.
        """
        params = {"symbol": symbol}
        response = await self.make_request("GET", "/v1/trades", params=params)
        
        if not response.get("success"):
            raise Exception(f"Failed to get trades: {response.get('message')}")
        
        trades = []
        trade_data = response.get("result", {}).get("latestTrades", [])
        
        for trade in trade_data[:limit]:
            trades.append({
                "symbol": trade.get("symbol"),
                "price": self.parse_decimal(trade.get("price")),
                "quantity": self.parse_decimal(trade.get("quantity")),
                "sum": self.parse_decimal(trade.get("sum")),
                "is_buyer": trade.get("isBuyOrder"),
                "timestamp": trade.get("timestamp"),
            })
        
        return trades

    async def get_balance(self) -> Dict[str, Dict[str, Decimal]]:
        """
        Get account balances from Wallex.
        Requires authentication.
        """
        response = await self.make_request(
            "GET", 
            "/v1/account/balances",
            headers=self.get_headers()
        )
        
        if not response.get("success"):
            raise Exception(f"Failed to get balance: {response.get('message')}")
        
        balances = {}
        balance_data = response.get("result", {}).get("balances", {})
        
        for asset, data in balance_data.items():
            balances[asset] = {
                "available": self.parse_decimal(data.get("value", 0)),
                "locked": self.parse_decimal(data.get("locked", 0)),
                "total": (
                    self.parse_decimal(data.get("value", 0)) + 
                    self.parse_decimal(data.get("locked", 0))
                ),
                "fa_name": data.get("faName"),
                "is_fiat": data.get("fiat", False),
            }
        
        return balances

    async def place_order(
        self,
        symbol: str,
        side: str,
        order_type: str,
        amount: Decimal,
        price: Optional[Decimal] = None,
        client_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Place an order on Wallex.
        Fixed according to documentation.
        """
        order_data = {
            "symbol": symbol,
            "type": order_type.upper(),  # LIMIT or MARKET
            "side": side.upper(),        # BUY or SELL
            "quantity": str(amount),
        }
        
        if order_type.upper() == "LIMIT":
            if not price:
                raise ValueError("Price required for limit orders")
            order_data["price"] = str(price)
        
        if client_id:
            order_data["client_id"] = client_id
        
        response = await self.make_request(
            "POST", 
            "/v1/account/orders",
            data=order_data,
            headers=self.get_headers()
        )
        
        if not response.get("success"):
            raise Exception(f"Failed to place order: {response.get('message')}")
        
        order = response.get("result", {})
        
        return {
            "order_id": order.get("clientOrderId"),
            "symbol": order.get("symbol"),
            "side": order.get("side"),
            "type": order.get("type"),
            "price": self.parse_decimal(order.get("price")),
            "amount": self.parse_decimal(order.get("origQty")),
            "executed_qty": self.parse_decimal(order.get("executedQty")),
            "executed_sum": self.parse_decimal(order.get("executedSum")),
            "executed_percent": order.get("executedPercent"),
            "status": order.get("status"),
            "is_active": order.get("active"),
            "created_at": order.get("created_at"),
        }

    async def cancel_order(self, order_id: str, symbol: Optional[str] = None) -> bool:
        """
        Cancel an order on Wallex.
        Fixed according to documentation.
        """
        params = {"clientOrderId": order_id}
        
        response = await self.make_request(
            "DELETE", 
            "/v1/account/orders",
            params=params,
            headers=self.get_headers()
        )
        
        return response.get("success", False)

    async def get_order_info(self, order_id: str) -> Dict[str, Any]:
        """
        Get order information by ID.
        Fixed according to documentation.
        """
        response = await self.make_request(
            "GET", 
            f"/v1/account/orders/{order_id}",
            headers=self.get_headers()
        )
        
        if not response.get("success"):
            raise Exception(f"Failed to get order info: {response.get('message')}")
        
        return response.get("result", {})

    async def get_open_orders(self, symbol: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get list of open orders.
        Fixed according to documentation.
        """
        params = {}
        if symbol:
            params["symbol"] = symbol
            
        response = await self.make_request(
            "GET", 
            "/v1/account/openOrders",
            params=params,
            headers=self.get_headers()
        )
        
        if not response.get("success"):
            raise Exception(f"Failed to get open orders: {response.get('message')}")
        
        return response.get("result", {}).get("orders", [])

    async def get_account_trades(
        self, 
        symbol: Optional[str] = None, 
        side: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get account trade history.
        Fixed according to documentation.
        """
        params = {}
        if symbol:
            params["symbol"] = symbol
        if side:
            params["side"] = side
            
        response = await self.make_request(
            "GET", 
            "/v1/account/trades",
            params=params,
            headers=self.get_headers()
        )
        
        if not response.get("success"):
            raise Exception(f"Failed to get account trades: {response.get('message')}")
        
        return response.get("result", {}).get("AccountLatestTrades", [])

    async def get_account_profile(self) -> Dict[str, Any]:
        """
        Get account profile information.
        Based on documentation.
        """
        response = await self.make_request(
            "GET", 
            "/v1/account/profile",
            headers=self.get_headers()
        )
        
        if not response.get("success"):
            raise Exception(f"Failed to get profile: {response.get('message')}")
        
        return response.get("result", {})

    async def get_account_fees(self) -> Dict[str, Any]:
        """
        Get account fee rates for all markets.
        Based on documentation.
        """
        response = await self.make_request(
            "GET", 
            "/v1/account/fee",
            headers=self.get_headers()
        )
        
        if not response.get("success"):
            raise Exception(f"Failed to get fees: {response.get('message')}")
        
        return response.get("result", {})

    # OTC Trading Methods (Instant Trading)
    
    async def get_otc_markets(self) -> List[Dict[str, Any]]:
        """
        Get OTC (instant trading) markets.
        Based on documentation.
        """
        response = await self.make_request("GET", "/v1/otc/markets")
        
        if not response.get("success"):
            raise Exception(f"Failed to get OTC markets: {response.get('message')}")
        
        otc_markets = []
        symbols = response.get("result", {}).get("symbols", {})
        
        for symbol, data in symbols.items():
            otc_markets.append({
                "symbol": symbol,
                "base": data.get("baseAsset"),
                "quote": data.get("quoteAsset"),
                "fa_name": data.get("faName"),
                "min_qty": self.parse_decimal(data.get("minQty")),
                "min_notional": self.parse_decimal(data.get("minNotional")),
                "max_notional": self.parse_decimal(data.get("maxNotional")),
                "buy_status": data.get("buyStatus"),
                "sell_status": data.get("sellStatus"),
                "stats": data.get("stats", {}),
                "created_at": data.get("createdAt"),
            })
        
        return otc_markets

    async def get_otc_price(self, symbol: str, side: str) -> Dict[str, Any]:
        """
        Get OTC price for instant trading.
        Based on documentation.
        """
        data = {
            "symbol": symbol,
            "side": side.upper()  # BUY or SELL
        }
        
        response = await self.make_request(
            "GET", 
            "/v1/account/otc/price",
            data=data,
            headers=self.get_headers()
        )
        
        if not response.get("success"):
            raise Exception(f"Failed to get OTC price: {response.get('message')}")
        
        return response.get("result", {})

    async def place_otc_order(
        self, 
        symbol: str, 
        side: str, 
        amount: Decimal
    ) -> Dict[str, Any]:
        """
        Place an instant (OTC) order.
        Based on documentation.
        """
        order_data = {
            "symbol": symbol,
            "side": side.upper(),  # BUY or SELL
            "amount": float(amount)
        }
        
        response = await self.make_request(
            "POST", 
            "/v1/account/otc/orders",
            data=order_data,
            headers=self.get_headers()
        )
        
        if not response.get("success"):
            raise Exception(f"Failed to place OTC order: {response.get('message')}")
        
        return response.get("result", {})

    async def get_crypto_currencies_stats(self) -> List[Dict[str, Any]]:
        """
        Get global cryptocurrency statistics.
        Public endpoint based on documentation.
        """
        response = await self.make_request("GET", "/v1/currencies/stats")
        
        if not response.get("success"):
            raise Exception(f"Failed to get crypto stats: {response.get('message')}")
        
        return response.get("result", [])

    async def get_candles(
        self, 
        symbol: str, 
        resolution: str, 
        from_time: int, 
        to_time: int
    ) -> Dict[str, Any]:
        """
        Get OHLC candle data.
        Based on documentation.
        """
        params = {
            "symbol": symbol,
            "resolution": resolution,  # 1, 60, 180, 360, 720, 1D
            "from": from_time,
            "to": to_time
        }
        
        response = await self.make_request("GET", "/v1/udf/history", params=params)
        
        return response  # Returns s, t, c, o, h, l, v arrays