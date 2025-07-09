import asyncio
import logging
from typing import Dict, List, Optional
from datetime import datetime, timedelta

from django.conf import settings
from django.utils import timezone
from django.core.cache import cache

from core.models import Exchange, ExchangeTradingPair
from .ramzinex_websocket import RamzinexWebSocketService
from .wallex_websocket import WallexWebSocketService

logger = logging.getLogger(__name__)


class WebSocketManager:
    """
    Centralized manager for all exchange WebSocket connections.
    
    Features:
    - Auto-reconnection on failure
    - Health monitoring
    - Subscription management
    - Data callbacks to arbitrage engine
    """
    
    def __init__(self):
        self.connections = {}
        self.health_status = {}
        self.is_running = False
        self.health_check_task = None
        self.reconnect_tasks = {}
        
        # Callbacks for real-time data
        self.orderbook_callbacks = []
        self.trade_callbacks = []
        self.ticker_callbacks = []
    
    async def start_all_exchanges(self):
        """Start WebSocket connections for all active exchanges."""
        logger.info("Starting WebSocket connections for all exchanges...")
        
        try:
            active_exchanges = Exchange.objects.filter(
                is_active=True
            ).values_list('code', flat=True)
            
            tasks = []
            for exchange_code in active_exchanges:
                if self._is_websocket_supported(exchange_code):
                    task = asyncio.create_task(
                        self.start_exchange_connection(exchange_code)
                    )
                    tasks.append(task)
            
            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)
            
            # Start health monitoring
            self.is_running = True
            self.health_check_task = asyncio.create_task(self._health_monitor())
            
            logger.info(f"Started WebSocket connections for {len(tasks)} exchanges")
            
        except Exception as e:
            logger.error(f"Error starting WebSocket connections: {e}")
    
    async def stop_all_exchanges(self):
        """Stop all WebSocket connections."""
        logger.info("Stopping all WebSocket connections...")
        
        self.is_running = False
        
        # Cancel health check task
        if self.health_check_task:
            self.health_check_task.cancel()
        
        # Cancel reconnect tasks
        for task in self.reconnect_tasks.values():
            if task and not task.done():
                task.cancel()
        
        # Disconnect all exchanges
        disconnect_tasks = []
        for exchange_code, connection in self.connections.items():
            if connection:
                disconnect_tasks.append(connection.disconnect())
        
        if disconnect_tasks:
            await asyncio.gather(*disconnect_tasks, return_exceptions=True)
        
        self.connections.clear()
        self.health_status.clear()
        
        logger.info("Stopped all WebSocket connections")
    
    async def start_exchange_connection(self, exchange_code: str):
        """Start WebSocket connection for a specific exchange."""
        try:
            logger.info(f"Starting WebSocket connection for {exchange_code}")
            
            # Get exchange instance
            exchange = Exchange.objects.get(code=exchange_code)
            
            # Create appropriate WebSocket service
            if exchange_code == 'ramzinex':
                ws_service = RamzinexWebSocketService(exchange)
            elif exchange_code == 'wallex':
                ws_service = WallexWebSocketService(exchange)
            else:
                logger.warning(f"WebSocket not supported for {exchange_code}")
                return
            
            # Connect
            await ws_service.connect()
            
            # Store connection
            self.connections[exchange_code] = ws_service
            self.health_status[exchange_code] = {
                'connected': True,
                'last_seen': timezone.now(),
                'reconnect_count': 0
            }
            
            # Subscribe to active trading pairs
            await self._subscribe_to_active_pairs(exchange_code, ws_service)
            
            logger.info(f"Successfully started WebSocket for {exchange_code}")
            
        except Exception as e:
            logger.error(f"Error starting WebSocket for {exchange_code}: {e}")
            self.health_status[exchange_code] = {
                'connected': False,
                'last_error': str(e),
                'last_error_time': timezone.now()
            }
    
    async def _subscribe_to_active_pairs(self, exchange_code: str, ws_service):
        """Subscribe to all active trading pairs for an exchange."""
        try:
            # Get active trading pairs for this exchange
            trading_pairs = ExchangeTradingPair.objects.filter(
                exchange__code=exchange_code,
                is_active=True
            ).select_related('trading_pair')
            
            subscription_tasks = []
            
            for pair in trading_pairs:
                # Create callbacks that will forward data to arbitrage engine
                orderbook_callback = self._create_orderbook_callback(exchange_code, pair)
                trade_callback = self._create_trade_callback(exchange_code, pair)
                
                if exchange_code == 'ramzinex':
                    # For Ramzinex, we need pair_id (this should be stored in metadata)
                    pair_id = pair.metadata.get('ramzinex_pair_id') if hasattr(pair, 'metadata') else None
                    if pair_id:
                        subscription_tasks.extend([
                            ws_service.subscribe_orderbook(pair_id, orderbook_callback),
                            ws_service.subscribe_trades(pair_id, trade_callback)
                        ])
                
                elif exchange_code == 'wallex':
                    # For Wallex, use exchange_symbol
                    symbol = pair.exchange_symbol
                    subscription_tasks.extend([
                        ws_service.subscribe_orderbook(symbol, orderbook_callback),
                        ws_service.subscribe_trades(symbol, trade_callback),
                        ws_service.subscribe_market_data(symbol, self._create_ticker_callback(exchange_code, pair))
                    ])
            
            # Execute all subscriptions
            if subscription_tasks:
                await asyncio.gather(*subscription_tasks, return_exceptions=True)
                logger.info(f"Subscribed to {len(subscription_tasks)} channels for {exchange_code}")
            
        except Exception as e:
            logger.error(f"Error subscribing to trading pairs for {exchange_code}: {e}")
    
    def _create_orderbook_callback(self, exchange_code: str, trading_pair):
        """Create callback function for order book updates."""
        async def callback(pair_identifier, orderbook_data):
            try:
                # Update cache for quick access
                cache_key = f"orderbook:{exchange_code}:{pair_identifier}"
                cache.set(cache_key, {
                    'data': orderbook_data,
                    'timestamp': timezone.now().timestamp(),
                    'trading_pair': trading_pair.trading_pair.symbol
                }, timeout=300)  # 5 minutes
                
                # Notify arbitrage engine
                for callback_func in self.orderbook_callbacks:
                    try:
                        await callback_func(exchange_code, trading_pair, orderbook_data)
                    except Exception as e:
                        logger.error(f"Error in orderbook callback: {e}")
                
                # Update health status
                if exchange_code in self.health_status:
                    self.health_status[exchange_code]['last_seen'] = timezone.now()
                
            except Exception as e:
                logger.error(f"Error in orderbook callback for {exchange_code}: {e}")
        
        return callback
    
    def _create_trade_callback(self, exchange_code: str, trading_pair):
        """Create callback function for trade updates."""
        async def callback(pair_identifier, trade_data):
            try:
                # Update cache
                cache_key = f"trades:{exchange_code}:{pair_identifier}"
                cache.set(cache_key, {
                    'data': trade_data,
                    'timestamp': timezone.now().timestamp(),
                    'trading_pair': trading_pair.trading_pair.symbol
                }, timeout=60)  # 1 minute
                
                # Notify arbitrage engine
                for callback_func in self.trade_callbacks:
                    try:
                        await callback_func(exchange_code, trading_pair, trade_data)
                    except Exception as e:
                        logger.error(f"Error in trade callback: {e}")
                
            except Exception as e:
                logger.error(f"Error in trade callback for {exchange_code}: {e}")
        
        return callback
    
    def _create_ticker_callback(self, exchange_code: str, trading_pair):
        """Create callback function for ticker updates."""
        async def callback(pair_identifier, ticker_data):
            try:
                # Update cache
                cache_key = f"ticker:{exchange_code}:{pair_identifier}"
                cache.set(cache_key, {
                    'data': ticker_data,
                    'timestamp': timezone.now().timestamp(),
                    'trading_pair': trading_pair.trading_pair.symbol
                }, timeout=300)  # 5 minutes
                
                # Notify arbitrage engine
                for callback_func in self.ticker_callbacks:
                    try:
                        await callback_func(exchange_code, trading_pair, ticker_data)
                    except Exception as e:
                        logger.error(f"Error in ticker callback: {e}")
                
            except Exception as e:
                logger.error(f"Error in ticker callback for {exchange_code}: {e}")
        
        return callback
    
    async def _health_monitor(self):
        """Monitor WebSocket connection health and handle reconnections."""
        while self.is_running:
            try:
                current_time = timezone.now()
                
                for exchange_code, status in self.health_status.items():
                    if not status.get('connected', False):
                        continue
                    
                    # Check if connection is stale
                    last_seen = status.get('last_seen')
                    if last_seen and (current_time - last_seen) > timedelta(minutes=5):
                        logger.warning(f"WebSocket connection for {exchange_code} appears stale")
                        await self._reconnect_exchange(exchange_code)
                    
                    # Check if WebSocket is actually connected
                    connection = self.connections.get(exchange_code)
                    if connection and hasattr(connection, 'is_connected') and not connection.is_connected:
                        logger.warning(f"WebSocket connection for {exchange_code} is disconnected")
                        await self._reconnect_exchange(exchange_code)
                
                await asyncio.sleep(30)  # Check every 30 seconds
                
            except Exception as e:
                logger.error(f"Error in health monitor: {e}")
                await asyncio.sleep(60)  # Wait longer on error
    
    async def _reconnect_exchange(self, exchange_code: str):
        """Reconnect to a specific exchange."""
        if exchange_code in self.reconnect_tasks and not self.reconnect_tasks[exchange_code].done():
            return  # Already reconnecting
        
        async def reconnect():
            try:
                logger.info(f"Attempting to reconnect WebSocket for {exchange_code}")
                
                # Disconnect existing connection
                if exchange_code in self.connections:
                    try:
                        await self.connections[exchange_code].disconnect()
                    except Exception:
                        pass
                    del self.connections[exchange_code]
                
                # Update health status
                if exchange_code in self.health_status:
                    self.health_status[exchange_code]['reconnect_count'] = \
                        self.health_status[exchange_code].get('reconnect_count', 0) + 1
                
                # Wait before reconnecting
                await asyncio.sleep(5)
                
                # Reconnect
                await self.start_exchange_connection(exchange_code)
                
                logger.info(f"Successfully reconnected WebSocket for {exchange_code}")
                
            except Exception as e:
                logger.error(f"Failed to reconnect WebSocket for {exchange_code}: {e}")
                
                # Update health status with error
                if exchange_code in self.health_status:
                    self.health_status[exchange_code].update({
                        'connected': False,
                        'last_error': str(e),
                        'last_error_time': timezone.now()
                    })
        
        self.reconnect_tasks[exchange_code] = asyncio.create_task(reconnect())
    
    def register_orderbook_callback(self, callback_func):
        """Register callback for order book updates."""
        self.orderbook_callbacks.append(callback_func)
    
    def register_trade_callback(self, callback_func):
        """Register callback for trade updates."""
        self.trade_callbacks.append(callback_func)
    
    def register_ticker_callback(self, callback_func):
        """Register callback for ticker updates."""
        self.ticker_callbacks.append(callback_func)
    
    def get_health_status(self) -> Dict:
        """Get health status of all WebSocket connections."""
        return self.health_status.copy()
    
    def get_cached_orderbook(self, exchange_code: str, pair_identifier: str) -> Optional[Dict]:
        """Get cached order book data."""
        cache_key = f"orderbook:{exchange_code}:{pair_identifier}"
        return cache.get(cache_key)
    
    def get_cached_ticker(self, exchange_code: str, pair_identifier: str) -> Optional[Dict]:
        """Get cached ticker data."""
        cache_key = f"ticker:{exchange_code}:{pair_identifier}"
        return cache.get(cache_key)
    
    def _is_websocket_supported(self, exchange_code: str) -> bool:
        """Check if WebSocket is supported for an exchange."""
        exchange_features = settings.EXCHANGE_FEATURES.get(exchange_code, {})
        return exchange_features.get('websocket', False)


# Global WebSocket manager instance
websocket_manager = WebSocketManager()


# Integration with Arbitrage Engine
async def arbitrage_orderbook_callback(exchange_code: str, trading_pair, orderbook_data):
    """Callback for arbitrage engine to receive orderbook updates."""
    try:
        # Import here to avoid circular imports
        from arbitrage.engine import MultiExchangeArbitrageEngine
        
        # Create a simple arbitrage check
        engine = MultiExchangeArbitrageEngine()
        
        # This could trigger real-time arbitrage detection
        # You can implement this based on your arbitrage logic
        
    except Exception as e:
        logger.error(f"Error in arbitrage orderbook callback: {e}")


async def arbitrage_trade_callback(exchange_code: str, trading_pair, trade_data):
    """Callback for arbitrage engine to receive trade updates."""
    try:
        # Update last trade price for quick access
        cache_key = f"last_price:{exchange_code}:{trading_pair.trading_pair.symbol}"
        
        if isinstance(trade_data, dict) and 'price' in trade_data:
            cache.set(cache_key, trade_data['price'], timeout=3600)
        
    except Exception as e:
        logger.error(f"Error in arbitrage trade callback: {e}")


# Register callbacks with the manager
websocket_manager.register_orderbook_callback(arbitrage_orderbook_callback)
websocket_manager.register_trade_callback(arbitrage_trade_callback)