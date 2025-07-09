"""
Celery tasks for WebSocket management.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List

from celery import shared_task
from django.conf import settings
from django.core.cache import cache
from django.utils import timezone

from core.models import Exchange, ExchangeTradingPair
from exchanges.websocket.manager import websocket_manager

logger = logging.getLogger(__name__)


@shared_task(bind=True, autoretry_for=(Exception,), retry_kwargs={'max_retries': 3, 'countdown': 60})
def start_websocket_connections(self):
    """
    Start WebSocket connections for all supported exchanges.
    This task should be run once when the system starts.
    """
    try:
        logger.info("Starting WebSocket connections task...")
        
        # Run the async manager in a new event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            loop.run_until_complete(websocket_manager.start_all_exchanges())
            logger.info("WebSocket connections started successfully")
            return "WebSocket connections started"
        finally:
            # Don't close the loop as WebSocket connections need to keep running
            pass
            
    except Exception as e:
        logger.error(f"Error starting WebSocket connections: {e}")
        raise self.retry(exc=e)


@shared_task
def stop_websocket_connections():
    """
    Stop all WebSocket connections.
    This should be called during system shutdown.
    """
    try:
        logger.info("Stopping WebSocket connections...")
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            loop.run_until_complete(websocket_manager.stop_all_exchanges())
            logger.info("WebSocket connections stopped successfully")
            return "WebSocket connections stopped"
        finally:
            loop.close()
            
    except Exception as e:
        logger.error(f"Error stopping WebSocket connections: {e}")
        return f"Error: {str(e)}"


@shared_task
def monitor_websocket_health():
    """
    Monitor WebSocket connection health and report status.
    This task should run periodically.
    """
    try:
        health_status = websocket_manager.get_health_status()
        
        # Log current status
        for exchange_code, status in health_status.items():
            if status.get('connected', False):
                last_seen = status.get('last_seen')
                if last_seen:
                    time_diff = timezone.now() - last_seen
                    logger.info(f"WebSocket {exchange_code}: Connected, last seen {time_diff.total_seconds()}s ago")
                else:
                    logger.info(f"WebSocket {exchange_code}: Connected")
            else:
                last_error = status.get('last_error', 'Unknown error')
                logger.warning(f"WebSocket {exchange_code}: Disconnected - {last_error}")
        
        # Store health status in cache for admin dashboard
        cache.set('websocket_health_status', health_status, timeout=300)
        
        # Check for dead connections
        current_time = timezone.now()
        alerts = []
        
        for exchange_code, status in health_status.items():
            if not status.get('connected', False):
                alerts.append(f"WebSocket for {exchange_code} is disconnected")
            elif status.get('last_seen'):
                time_diff = current_time - status['last_seen']
                if time_diff > timedelta(minutes=10):
                    alerts.append(f"WebSocket for {exchange_code} hasn't been seen for {time_diff}")
        
        if alerts:
            logger.warning(f"WebSocket alerts: {'; '.join(alerts)}")
            # You can add email/Telegram notifications here
        
        return {
            'status': 'success',
            'health_data': health_status,
            'alerts': alerts
        }
        
    except Exception as e:
        logger.error(f"Error monitoring WebSocket health: {e}")
        return {'status': 'error', 'message': str(e)}


@shared_task
def restart_websocket_connection(exchange_code: str):
    """
    Restart WebSocket connection for a specific exchange.
    
    Args:
        exchange_code: Exchange code (e.g., 'ramzinex', 'wallex')
    """
    try:
        logger.info(f"Restarting WebSocket connection for {exchange_code}")
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            # Stop existing connection
            if exchange_code in websocket_manager.connections:
                loop.run_until_complete(
                    websocket_manager.connections[exchange_code].disconnect()
                )
            
            # Start new connection
            loop.run_until_complete(
                websocket_manager.start_exchange_connection(exchange_code)
            )
            
            logger.info(f"Successfully restarted WebSocket for {exchange_code}")
            return f"WebSocket for {exchange_code} restarted successfully"
            
        finally:
            # Don't close loop as connection needs to stay alive
            pass
            
    except Exception as e:
        logger.error(f"Error restarting WebSocket for {exchange_code}: {e}")
        return f"Error restarting WebSocket for {exchange_code}: {str(e)}"


@shared_task
def sync_websocket_subscriptions():
    """
    Synchronize WebSocket subscriptions with active trading pairs.
    This should run periodically to add new pairs or remove inactive ones.
    """
    try:
        logger.info("Synchronizing WebSocket subscriptions...")
        
        # Get all active exchanges with WebSocket support
        active_exchanges = Exchange.objects.filter(is_active=True)
        
        sync_results = {}
        
        for exchange in active_exchanges:
            if not websocket_manager._is_websocket_supported(exchange.code):
                continue
            
            try:
                # Get current active trading pairs
                active_pairs = ExchangeTradingPair.objects.filter(
                    exchange=exchange,
                    is_active=True
                ).count()
                
                # Check if WebSocket is connected
                connection = websocket_manager.connections.get(exchange.code)
                is_connected = connection and getattr(connection, 'is_connected', False)
                
                sync_results[exchange.code] = {
                    'active_pairs': active_pairs,
                    'is_connected': is_connected,
                    'status': 'ok' if is_connected else 'disconnected'
                }
                
                # If not connected, attempt to restart
                if not is_connected:
                    restart_websocket_connection.delay(exchange.code)
                    sync_results[exchange.code]['action'] = 'restart_triggered'
                
            except Exception as e:
                logger.error(f"Error syncing WebSocket for {exchange.code}: {e}")
                sync_results[exchange.code] = {
                    'status': 'error',
                    'error': str(e)
                }
        
        logger.info(f"WebSocket sync completed: {sync_results}")
        return sync_results
        
    except Exception as e:
        logger.error(f"Error synchronizing WebSocket subscriptions: {e}")
        return {'error': str(e)}


@shared_task
def cleanup_websocket_cache():
    """
    Clean up old WebSocket data from cache.
    This should run periodically to prevent cache bloat.
    """
    try:
        logger.info("Cleaning up WebSocket cache...")
        
        current_time = timezone.now().timestamp()
        cleanup_count = 0
        
        # Define cache patterns to clean
        cache_patterns = [
            'orderbook:*',
            'trades:*',
            'ticker:*',
            'last_price:*'
        ]
        
        # Get all cache keys (this is Redis-specific)
        try:
            from django.core.cache.backends.redis import RedisCache
            if isinstance(cache, RedisCache):
                redis_client = cache._cache.get_client(None)
                
                for pattern in cache_patterns:
                    # Get keys matching pattern
                    keys = redis_client.keys(pattern)
                    
                    for key in keys:
                        # Get the data
                        data = cache.get(key.decode() if isinstance(key, bytes) else key)
                        
                        if data and isinstance(data, dict) and 'timestamp' in data:
                            # Check if data is older than 1 hour
                            if current_time - data['timestamp'] > 3600:
                                cache.delete(key.decode() if isinstance(key, bytes) else key)
                                cleanup_count += 1
                
            logger.info(f"Cleaned up {cleanup_count} old cache entries")
            return f"Cleaned up {cleanup_count} cache entries"
            
        except ImportError:
            logger.warning("Cache cleanup requires Redis backend")
            return "Cache cleanup skipped - Redis required"
        
    except Exception as e:
        logger.error(f"Error cleaning up WebSocket cache: {e}")
        return f"Error: {str(e)}"


@shared_task
def websocket_performance_report():
    """
    Generate performance report for WebSocket connections.
    """
    try:
        logger.info("Generating WebSocket performance report...")
        
        health_status = websocket_manager.get_health_status()
        
        report = {
            'timestamp': timezone.now().isoformat(),
            'total_connections': len(health_status),
            'connected_count': sum(1 for s in health_status.values() if s.get('connected', False)),
            'disconnected_count': sum(1 for s in health_status.values() if not s.get('connected', False)),
            'exchanges': {}
        }
        
        for exchange_code, status in health_status.items():
            exchange_report = {
                'connected': status.get('connected', False),
                'last_seen': status.get('last_seen').isoformat() if status.get('last_seen') else None,
                'reconnect_count': status.get('reconnect_count', 0),
                'last_error': status.get('last_error'),
                'last_error_time': status.get('last_error_time').isoformat() if status.get('last_error_time') else None
            }
            
            # Add cache statistics
            try:
                # Count cached data for this exchange
                cache_stats = {
                    'orderbook_count': 0,
                    'ticker_count': 0,
                    'trade_count': 0
                }
                
                # This would need Redis-specific implementation
                exchange_report['cache_stats'] = cache_stats
                
            except Exception:
                pass
            
            report['exchanges'][exchange_code] = exchange_report
        
        # Store report in cache for dashboard
        cache.set('websocket_performance_report', report, timeout=3600)
        
        logger.info(f"Performance report generated: {report['connected_count']}/{report['total_connections']} connected")
        return report
        
    except Exception as e:
        logger.error(f"Error generating WebSocket performance report: {e}")
        return {'error': str(e)}


# Utility function to check if WebSocket data is fresh
def is_websocket_data_fresh(exchange_code: str, pair_identifier: str, max_age_seconds: int = 300) -> bool:
    """
    Check if WebSocket data for a trading pair is fresh.
    
    Args:
        exchange_code: Exchange code
        pair_identifier: Trading pair identifier
        max_age_seconds: Maximum age in seconds (default 5 minutes)
    
    Returns:
        True if data is fresh, False otherwise
    """
    try:
        orderbook_data = websocket_manager.get_cached_orderbook(exchange_code, pair_identifier)
        
        if not orderbook_data or 'timestamp' not in orderbook_data:
            return False
        
        data_age = timezone.now().timestamp() - orderbook_data['timestamp']
        return data_age <= max_age_seconds
        
    except Exception as e:
        logger.error(f"Error checking WebSocket data freshness: {e}")
        return False