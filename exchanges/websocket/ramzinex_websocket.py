import asyncio
import json
import logging
import time
from typing import Any, Callable, Dict, List, Optional
from decimal import Decimal

import websockets
from django.conf import settings
from django.utils import timezone

from core.models import Exchange, ExchangeTradingPair
from exchanges.models import OrderBook, OrderBookEntry, MarketTicker

logger = logging.getLogger(__name__)


class RamzinexWebSocketService:
    """
    Ramzinex WebSocket client using Centrifugo protocol.
    
    Handles real-time data streams for:
    - Order books (orderbook:{pair_id})
    - Last trades (last-trades:{pair_id})
    """
    
    def __init__(self, exchange: Exchange):
        self.exchange = exchange
        self.websocket = None
        self.subscriptions = {}
        self.message_id = 1
        self.is_connected = False
        self.ping_task = None
        self.callbacks = {}
        
        # WebSocket settings from configuration
        self.ws_settings = settings.WEBSOCKET_SETTINGS.get('ramzinex', {})
        self.ws_url = self.ws_settings.get('url', 'wss://websocket.ramzinex.com/websocket')
        self.ping_interval = self.ws_settings.get('ping_interval', 25)
        
    async def connect(self):
        """Connect to Ramzinex WebSocket."""
        try:
            logger.info(f"Connecting to Ramzinex WebSocket: {self.ws_url}")
            
            self.websocket = await websockets.connect(
                self.ws_url,
                ping_interval=None,  # Manual ping handling
                ping_timeout=30
            )
            
            # Send initial connection message
            connect_msg = {
                'connect': {'name': 'python'},
                'id': self._get_message_id()
            }
            
            await self.websocket.send(json.dumps(connect_msg))
            
            # Wait for connection response
            response = await self.websocket.recv()
            response_data = json.loads(response)
            
            if 'connect' in response_data and response_data.get('connect', {}).get('client'):
                self.is_connected = True
                logger.info("Successfully connected to Ramzinex WebSocket")
                
                # Start ping task
                self.ping_task = asyncio.create_task(self._ping_loop())
                
                # Start message handling
                asyncio.create_task(self._message_handler())
                
            else:
                logger.error(f"Failed to connect: {response_data}")
                raise ConnectionError("WebSocket connection failed")
                
        except Exception as e:
            logger.error(f"Error connecting to Ramzinex WebSocket: {e}")
            raise
    
    async def disconnect(self):
        """Disconnect from WebSocket."""
        self.is_connected = False
        
        if self.ping_task:
            self.ping_task.cancel()
            
        if self.websocket:
            await self.websocket.close()
            
        logger.info("Disconnected from Ramzinex WebSocket")
    
    async def subscribe_orderbook(self, pair_id: int, callback: Optional[Callable] = None):
        """
        Subscribe to order book updates for a trading pair.
        
        Args:
            pair_id: Trading pair ID (e.g., 11 for USDT/TMN)
            callback: Optional callback function for custom processing
        """
        channel = f"orderbook:{pair_id}"
        
        subscribe_msg = {
            'subscribe': {
                'channel': channel,
                'recover': True,
                'delta': 'fossil'  # Enable delta updates
            },
            'id': self._get_message_id()
        }
        
        await self.websocket.send(json.dumps(subscribe_msg))
        
        self.subscriptions[channel] = {
            'pair_id': pair_id,
            'type': 'orderbook',
            'callback': callback
        }
        
        logger.info(f"Subscribed to orderbook updates for pair {pair_id}")
    
    async def subscribe_trades(self, pair_id: int, callback: Optional[Callable] = None):
        """
        Subscribe to last trades for a trading pair.
        
        Args:
            pair_id: Trading pair ID
            callback: Optional callback function
        """
        channel = f"last-trades:{pair_id}"
        
        subscribe_msg = {
            'subscribe': {
                'channel': channel,
                'recover': True,
                'delta': 'fossil'
            },
            'id': self._get_message_id()
        }
        
        await self.websocket.send(json.dumps(subscribe_msg))
        
        self.subscriptions[channel] = {
            'pair_id': pair_id,
            'type': 'trades',
            'callback': callback
        }
        
        logger.info(f"Subscribed to trade updates for pair {pair_id}")
    
    async def _message_handler(self):
        """Handle incoming WebSocket messages."""
        try:
            async for message in self.websocket:
                if not self.is_connected:
                    break
                    
                try:
                    data = json.loads(message)
                    await self._process_message(data)
                except json.JSONDecodeError:
                    logger.warning(f"Invalid JSON received: {message}")
                except Exception as e:
                    logger.error(f"Error processing message: {e}")
                    
        except websockets.exceptions.ConnectionClosed:
            logger.warning("WebSocket connection closed")
            self.is_connected = False
        except Exception as e:
            logger.error(f"Error in message handler: {e}")
            self.is_connected = False
    
    async def _process_message(self, data: Dict[str, Any]):
        """Process incoming WebSocket messages."""
        
        # Handle ping messages
        if data == {}:
            await self._handle_ping()
            return
        
        # Handle push messages (real-time data)
        if 'push' in data:
            push_data = data['push']
            channel = push_data.get('channel', '')
            pub_data = push_data.get('pub', {})
            
            if channel in self.subscriptions:
                subscription = self.subscriptions[channel]
                
                if subscription['type'] == 'orderbook':
                    await self._handle_orderbook_update(
                        subscription['pair_id'], 
                        pub_data, 
                        subscription.get('callback')
                    )
                elif subscription['type'] == 'trades':
                    await self._handle_trade_update(
                        subscription['pair_id'], 
                        pub_data, 
                        subscription.get('callback')
                    )
    
    async def _handle_orderbook_update(self, pair_id: int, data: Dict, callback: Optional[Callable]):
        """Handle order book updates."""
        try:
            # Parse the order book data
            if 'data' in data:
                orderbook_str = data['data']
                if isinstance(orderbook_str, str):
                    orderbook_data = json.loads(orderbook_str)
                else:
                    orderbook_data = orderbook_str
                
                # Save to database
                await self._save_orderbook_to_db(pair_id, orderbook_data)
                
                # Call custom callback if provided
                if callback:
                    await callback(pair_id, orderbook_data)
                    
                logger.debug(f"Processed orderbook update for pair {pair_id}")
                
        except Exception as e:
            logger.error(f"Error handling orderbook update: {e}")
    
    async def _handle_trade_update(self, pair_id: int, data: Dict, callback: Optional[Callable]):
        """Handle trade updates."""
        try:
            if 'data' in data:
                trade_data = data['data']
                
                # Call custom callback if provided
                if callback:
                    await callback(pair_id, trade_data)
                    
                logger.debug(f"Processed trade update for pair {pair_id}")
                
        except Exception as e:
            logger.error(f"Error handling trade update: {e}")
    
    async def _save_orderbook_to_db(self, pair_id: int, orderbook_data: Dict):
        """Save order book data to database."""
        try:
            # Find the exchange trading pair
            exchange_pair = await self._get_exchange_trading_pair(pair_id)
            if not exchange_pair:
                return
            
            # Create order book snapshot
            order_book = await OrderBook.objects.acreate(
                exchange_pair=exchange_pair,
                timestamp=timezone.now()
            )
            
            # Process buy orders
            if 'buys' in orderbook_data:
                for position, buy_order in enumerate(orderbook_data['buys']):
                    if len(buy_order) >= 2:
                        price = Decimal(str(buy_order[0]))
                        amount = Decimal(str(buy_order[1]))
                        
                        await OrderBookEntry.objects.acreate(
                            order_book=order_book,
                            side='bid',
                            price=price,
                            amount=amount,
                            total=price * amount,
                            position=position
                        )
            
            # Process sell orders
            if 'sells' in orderbook_data:
                for position, sell_order in enumerate(orderbook_data['sells']):
                    if len(sell_order) >= 2:
                        price = Decimal(str(sell_order[0]))
                        amount = Decimal(str(sell_order[1]))
                        
                        await OrderBookEntry.objects.acreate(
                            order_book=order_book,
                            side='ask',
                            price=price,
                            amount=amount,
                            total=price * amount,
                            position=position
                        )
            
        except Exception as e:
            logger.error(f"Error saving orderbook to database: {e}")
    
    async def _get_exchange_trading_pair(self, pair_id: int) -> Optional[ExchangeTradingPair]:
        """Get ExchangeTradingPair by Ramzinex pair ID."""
        try:
            # This needs to be implemented based on your pair ID mapping
            # For now, return None - you'll need to create a mapping table
            return None
        except Exception:
            return None
    
    async def _ping_loop(self):
        """Send periodic ping messages."""
        while self.is_connected:
            try:
                await asyncio.sleep(self.ping_interval - 5)  # Ping 5 seconds before timeout
                if self.websocket and self.is_connected:
                    # Ramzinex expects empty object as ping
                    await self.websocket.send(json.dumps({}))
                    logger.debug("Sent ping to Ramzinex WebSocket")
            except Exception as e:
                logger.error(f"Error sending ping: {e}")
                break
    
    async def _handle_ping(self):
        """Handle ping from server."""
        try:
            # Respond with pong (empty object)
            await self.websocket.send(json.dumps({}))
            logger.debug("Responded to ping from Ramzinex WebSocket")
        except Exception as e:
            logger.error(f"Error responding to ping: {e}")
    
    def _get_message_id(self) -> int:
        """Get next message ID."""
        current_id = self.message_id
        self.message_id += 1
        return current_id


# Usage example:
async def main():
    """Example usage of RamzinexWebSocketService."""
    exchange = Exchange.objects.get(code='ramzinex')
    
    ws_service = RamzinexWebSocketService(exchange)
    
    try:
        await ws_service.connect()
        
        # Subscribe to USDT/TMN orderbook (pair_id=11)
        await ws_service.subscribe_orderbook(11)
        
        # Subscribe to BTC/TMN trades (pair_id=2)  
        await ws_service.subscribe_trades(2)
        
        # Keep running
        while ws_service.is_connected:
            await asyncio.sleep(1)
            
    except KeyboardInterrupt:
        logger.info("Shutting down...")
    finally:
        await ws_service.disconnect()


if __name__ == "__main__":
    asyncio.run(main())