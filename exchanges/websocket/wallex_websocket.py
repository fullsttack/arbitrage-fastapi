
import asyncio
import json
import logging
from typing import Any, Callable, Dict, List, Optional
from decimal import Decimal

import socketio
from django.conf import settings
from django.utils import timezone

from core.models import Exchange, ExchangeTradingPair
from exchanges.models import OrderBook, OrderBookEntry, MarketTicker

logger = logging.getLogger(__name__)


class WallexWebSocketService:
    """
    Wallex WebSocket client using Socket.IO v2.5.0.
    
    Handles real-time data streams for:
    - Buy depth (SYMBOL@buyDepth) 
    - Sell depth (SYMBOL@sellDepth)
    - Trades (SYMBOL@trade)
    - Market data (SYMBOL@marketCap)
    """
    
    def __init__(self, exchange: Exchange):
        self.exchange = exchange
        self.sio = None
        self.is_connected = False
        self.subscriptions = {}
        self.callbacks = {}
        
        # WebSocket settings from configuration
        self.ws_settings = settings.WEBSOCKET_SETTINGS.get('wallex', {})
        
        # Wallex WebSocket URL (needs to be configured)
        self.ws_url = getattr(settings, 'WALLEX_WEBSOCKET_URL', 'wss://api.wallex.ir/socket.io/')
        
    async def connect(self):
        """Connect to Wallex WebSocket using Socket.IO."""
        try:
            logger.info(f"Connecting to Wallex WebSocket: {self.ws_url}")
            
            # Create Socket.IO client
            self.sio = socketio.AsyncClient(
                engineio_logger=False,
                socketio_logger=False,
                ssl_verify=False
            )
            
            # Register event handlers
            self._register_event_handlers()
            
            # Connect to server
            await self.sio.connect(
                self.ws_url,
                socketio_path='/socket.io',
                transports=['websocket']
            )
            
            logger.info("Successfully connected to Wallex WebSocket")
            
        except Exception as e:
            logger.error(f"Error connecting to Wallex WebSocket: {e}")
            raise
    
    async def disconnect(self):
        """Disconnect from WebSocket."""
        self.is_connected = False
        
        if self.sio and self.sio.connected:
            await self.sio.disconnect()
            
        logger.info("Disconnected from Wallex WebSocket")
    
    def _register_event_handlers(self):
        """Register Socket.IO event handlers."""
        
        @self.sio.event
        async def connect():
            """Handle connection event."""
            self.is_connected = True
            logger.info("Connected to Wallex WebSocket")
        
        @self.sio.event
        async def disconnect():
            """Handle disconnection event."""
            self.is_connected = False
            logger.info("Disconnected from Wallex WebSocket")
        
        @self.sio.event
        async def connect_error(data):
            """Handle connection error."""
            logger.error(f"Wallex WebSocket connection error: {data}")
            self.is_connected = False
        
        # Register subscription event handlers
        self._register_subscription_handlers()
    
    def _register_subscription_handlers(self):
        """Register handlers for subscribed channels."""
        
        @self.sio.event
        async def message(data):
            """Handle general messages."""
            logger.debug(f"Received message: {data}")
        
        # Buy depth handler  
        @self.sio.on('*')
        async def catch_all(event, data):
            """Catch all events and route to appropriate handlers."""
            try:
                if '@buyDepth' in event:
                    symbol = event.split('@')[0]
                    await self._handle_buy_depth_update(symbol, data)
                elif '@sellDepth' in event:
                    symbol = event.split('@')[0]
                    await self._handle_sell_depth_update(symbol, data)
                elif '@trade' in event:
                    symbol = event.split('@')[0]
                    await self._handle_trade_update(symbol, data)
                elif '@marketCap' in event:
                    symbol = event.split('@')[0]
                    await self._handle_market_data_update(symbol, data)
                else:
                    logger.debug(f"Unhandled event: {event} with data: {data}")
            except Exception as e:
                logger.error(f"Error handling event {event}: {e}")
    
    async def subscribe_orderbook(self, symbol: str, callback: Optional[Callable] = None):
        """
        Subscribe to order book updates for a trading pair.
        
        Args:
            symbol: Trading symbol (e.g., 'USDTTMN')
            callback: Optional callback function
        """
        if not self.is_connected:
            raise ConnectionError("Not connected to WebSocket")
        
        # Subscribe to both buy and sell depth
        buy_channel = f"{symbol}@buyDepth"
        sell_channel = f"{symbol}@sellDepth"
        
        # Send subscription messages
        await self.sio.emit('subscribe', {'channel': buy_channel})
        await self.sio.emit('subscribe', {'channel': sell_channel})
        
        # Store subscription info
        self.subscriptions[buy_channel] = {
            'symbol': symbol,
            'type': 'buy_depth',
            'callback': callback
        }
        self.subscriptions[sell_channel] = {
            'symbol': symbol,
            'type': 'sell_depth', 
            'callback': callback
        }
        
        logger.info(f"Subscribed to orderbook updates for {symbol}")
    
    async def subscribe_trades(self, symbol: str, callback: Optional[Callable] = None):
        """
        Subscribe to trade updates for a trading pair.
        
        Args:
            symbol: Trading symbol
            callback: Optional callback function
        """
        if not self.is_connected:
            raise ConnectionError("Not connected to WebSocket")
        
        channel = f"{symbol}@trade"
        
        await self.sio.emit('subscribe', {'channel': channel})
        
        self.subscriptions[channel] = {
            'symbol': symbol,
            'type': 'trades',
            'callback': callback
        }
        
        logger.info(f"Subscribed to trade updates for {symbol}")
    
    async def subscribe_market_data(self, symbol: str, callback: Optional[Callable] = None):
        """
        Subscribe to market data updates.
        
        Args:
            symbol: Trading symbol
            callback: Optional callback function
        """
        if not self.is_connected:
            raise ConnectionError("Not connected to WebSocket")
        
        channel = f"{symbol}@marketCap"
        
        await self.sio.emit('subscribe', {'channel': channel})
        
        self.subscriptions[channel] = {
            'symbol': symbol,
            'type': 'market_data',
            'callback': callback
        }
        
        logger.info(f"Subscribed to market data for {symbol}")
    
    async def _handle_buy_depth_update(self, symbol: str, data: Dict):
        """Handle buy depth (bid) updates."""
        try:
            # Save buy orders to database
            await self._save_depth_to_db(symbol, data, 'bid')
            
            # Call custom callback if available
            channel = f"{symbol}@buyDepth"
            if channel in self.subscriptions:
                callback = self.subscriptions[channel].get('callback')
                if callback:
                    await callback(symbol, 'buy_depth', data)
            
            logger.debug(f"Processed buy depth update for {symbol}")
            
        except Exception as e:
            logger.error(f"Error handling buy depth update for {symbol}: {e}")
    
    async def _handle_sell_depth_update(self, symbol: str, data: Dict):
        """Handle sell depth (ask) updates."""
        try:
            # Save sell orders to database
            await self._save_depth_to_db(symbol, data, 'ask')
            
            # Call custom callback if available
            channel = f"{symbol}@sellDepth"
            if channel in self.subscriptions:
                callback = self.subscriptions[channel].get('callback')
                if callback:
                    await callback(symbol, 'sell_depth', data)
            
            logger.debug(f"Processed sell depth update for {symbol}")
            
        except Exception as e:
            logger.error(f"Error handling sell depth update for {symbol}: {e}")
    
    async def _handle_trade_update(self, symbol: str, data: Dict):
        """Handle trade updates."""
        try:
            # Call custom callback if available
            channel = f"{symbol}@trade"
            if channel in self.subscriptions:
                callback = self.subscriptions[channel].get('callback')
                if callback:
                    await callback(symbol, 'trade', data)
            
            logger.debug(f"Processed trade update for {symbol}")
            
        except Exception as e:
            logger.error(f"Error handling trade update for {symbol}: {e}")
    
    async def _handle_market_data_update(self, symbol: str, data: Dict):
        """Handle market data updates."""
        try:
            # Save market ticker to database
            await self._save_ticker_to_db(symbol, data)
            
            # Call custom callback if available
            channel = f"{symbol}@marketCap"
            if channel in self.subscriptions:
                callback = self.subscriptions[channel].get('callback')
                if callback:
                    await callback(symbol, 'market_data', data)
            
            logger.debug(f"Processed market data update for {symbol}")
            
        except Exception as e:
            logger.error(f"Error handling market data update for {symbol}: {e}")
    
    async def _save_depth_to_db(self, symbol: str, data: Dict, side: str):
        """Save order book depth data to database."""
        try:
            # Find the exchange trading pair
            exchange_pair = await self._get_exchange_trading_pair(symbol)
            if not exchange_pair:
                return
            
            # Create or get order book snapshot
            order_book, created = await OrderBook.objects.aget_or_create(
                exchange_pair=exchange_pair,
                timestamp__gte=timezone.now().replace(second=0, microsecond=0),
                defaults={'timestamp': timezone.now()}
            )
            
            # Clear existing entries for this side
            await OrderBookEntry.objects.filter(
                order_book=order_book,
                side=side
            ).adelete()
            
            # Process depth data
            # Data format: {"0": {"quantity": 214.86, "price": "31695.0", "sum": 6809987.7}, ...}
            for position_str, order_data in data.items():
                try:
                    position = int(position_str)
                    price = Decimal(str(order_data['price']))
                    amount = Decimal(str(order_data['quantity']))
                    
                    await OrderBookEntry.objects.acreate(
                        order_book=order_book,
                        side=side,
                        price=price,
                        amount=amount,
                        total=price * amount,
                        position=position
                    )
                except (ValueError, KeyError, TypeError) as e:
                    logger.warning(f"Invalid order data for {symbol}: {order_data} - {e}")
                    
        except Exception as e:
            logger.error(f"Error saving depth data to database for {symbol}: {e}")
    
    async def _save_ticker_to_db(self, symbol: str, data: Dict):
        """Save market ticker data to database."""
        try:
            # Find the exchange trading pair
            exchange_pair = await self._get_exchange_trading_pair(symbol)
            if not exchange_pair:
                return
            
            # Extract ticker data
            ticker_data = {
                'exchange_pair': exchange_pair,
                'timestamp': timezone.now(),
                'last_price': Decimal(str(data.get('lastPrice', 0))),
                'bid_price': Decimal(str(data.get('bidPrice', 0))) if data.get('bidPrice') else None,
                'ask_price': Decimal(str(data.get('askPrice', 0))) if data.get('askPrice') else None,
                'volume_24h': Decimal(str(data.get('24h_volume', 0))),
                'high_24h': Decimal(str(data.get('24h_highPrice', 0))),
                'low_24h': Decimal(str(data.get('24h_lowPrice', 0))),
                'change_24h': Decimal(str(data.get('24h_ch', 0)))
            }
            
            await MarketTicker.objects.acreate(**ticker_data)
            
        except Exception as e:
            logger.error(f"Error saving ticker data for {symbol}: {e}")
    
    async def _get_exchange_trading_pair(self, symbol: str) -> Optional[ExchangeTradingPair]:
        """Get ExchangeTradingPair by Wallex symbol."""
        try:
            return await ExchangeTradingPair.objects.select_related(
                'exchange', 'trading_pair'
            ).aget(
                exchange=self.exchange,
                exchange_symbol=symbol
            )
        except ExchangeTradingPair.DoesNotExist:
            logger.warning(f"ExchangeTradingPair not found for symbol {symbol}")
            return None
        except Exception as e:
            logger.error(f"Error getting ExchangeTradingPair for {symbol}: {e}")
            return None


# Usage example:
async def main():
    """Example usage of WallexWebSocketService."""
    exchange = Exchange.objects.get(code='wallex')
    
    ws_service = WallexWebSocketService(exchange)
    
    try:
        await ws_service.connect()
        
        # Subscribe to USDT/TMN orderbook
        await ws_service.subscribe_orderbook('USDTTMN')
        
        # Subscribe to BTC/TMN trades
        await ws_service.subscribe_trades('BTCTMN')
        
        # Subscribe to market data
        await ws_service.subscribe_market_data('USDTTMN')
        
        # Keep running
        while ws_service.is_connected:
            await asyncio.sleep(1)
            
    except KeyboardInterrupt:
        logger.info("Shutting down...")
    finally:
        await ws_service.disconnect()


if __name__ == "__main__":
    asyncio.run(main())