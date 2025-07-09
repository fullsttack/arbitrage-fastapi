"""
Celery Configuration for Crypto Arbitrage Project
Complete and simplified configuration without complexity.
"""

import os
from celery import Celery
from django.conf import settings

# Set Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

# Create Celery app instance
app = Celery('crypto_arbitrage')

# Configure Celery using Django settings
app.config_from_object('django.conf:settings', namespace='CELERY')

# Auto-discover tasks from all Django apps
app.autodiscover_tasks()


# ==========================================
# CELERY CONFIGURATION
# ==========================================

app.conf.update(
    # Broker settings
    broker_url=os.getenv('CELERY_BROKER_URL', 'redis://localhost:6379/1'),
    result_backend=os.getenv('CELERY_RESULT_BACKEND', 'redis://localhost:6379/2'),
    
    # Task settings
    task_serializer='json',
    result_serializer='json',
    accept_content=['json'],
    result_expires=3600,  # 1 hour
    timezone='UTC',
    enable_utc=True,
    
    # Worker settings
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    worker_max_tasks_per_child=100,
    worker_concurrency=2,  # Simple concurrency for SQLite compatibility
    
    # Task timeouts
    task_soft_time_limit=300,  # 5 minutes
    task_time_limit=600,       # 10 minutes
    
    # Connection settings
    broker_connection_retry_on_startup=True,
    broker_connection_retry=True,
    
    # Beat scheduler settings
    beat_scheduler='celery.beat:PersistentScheduler',
    beat_schedule_filename='logs/celerybeat-schedule',
)


# ==========================================
# PERIODIC TASKS SCHEDULE
# ==========================================

app.conf.beat_schedule = {
    # Exchange data updates
    'update-exchange-tickers': {
        'task': 'exchanges.tasks.update_exchange_tickers',
        'schedule': 30.0,  # Every 30 seconds
    },
    
    'check-exchange-health': {
        'task': 'exchanges.tasks.check_exchange_health',
        'schedule': 300.0,  # Every 5 minutes
    },
    
    # Arbitrage scanning
    'scan-arbitrage-opportunities': {
        'task': 'arbitrage.tasks.scan_arbitrage_opportunities',
        'schedule': 60.0,  # Every minute
    },
    
    'cleanup-old-opportunities': {
        'task': 'arbitrage.tasks.cleanup_old_opportunities',
        'schedule': 3600.0,  # Every hour
    },
    
    # WebSocket monitoring
    'monitor-websocket-health': {
        'task': 'exchanges.tasks.websocket_tasks.monitor_websocket_health',
        'schedule': 60.0,  # Every minute
    },
    
    'sync-websocket-subscriptions': {
        'task': 'exchanges.tasks.websocket_tasks.sync_websocket_subscriptions',
        'schedule': 300.0,  # Every 5 minutes
    },
    
    'cleanup-websocket-cache': {
        'task': 'exchanges.tasks.websocket_tasks.cleanup_websocket_cache',
        'schedule': 3600.0,  # Every hour
    },
    
    'websocket-performance-report': {
        'task': 'exchanges.tasks.websocket_tasks.websocket_performance_report',
        'schedule': 1800.0,  # Every 30 minutes
    },
}


# ==========================================
# TASK ROUTING (OPTIONAL)
# ==========================================

app.conf.task_routes = {
    # Regular tasks go to default queue
    'arbitrage.tasks.*': {'queue': 'default'},
    'exchanges.tasks.update_exchange_tickers': {'queue': 'default'},
    'exchanges.tasks.check_exchange_health': {'queue': 'default'},
    'trading.tasks.*': {'queue': 'default'},
    'analytics.tasks.*': {'queue': 'default'},
    
    # WebSocket tasks can go to separate queue if needed
    'exchanges.tasks.websocket_tasks.*': {'queue': 'default'},  # Keep simple - same queue
}


# ==========================================
# DEBUG TASK
# ==========================================

@app.task(bind=True)
def debug_task(self):
    """Simple debug task to test Celery functionality."""
    print(f'Request: {self.request!r}')
    return {
        'status': 'success',
        'message': 'Celery is working correctly!',
        'worker_id': self.request.id
    }


# ==========================================
# STARTUP CONFIGURATION
# ==========================================

@app.on_after_configure.connect
def setup_periodic_tasks(sender, **kwargs):
    """
    Setup any additional periodic tasks here if needed.
    This runs after Celery is configured.
    """
    print("Celery configured successfully!")
    
    # Optionally start WebSocket connections when worker starts
    # Uncomment the lines below if you want automatic WebSocket startup
    """
    try:
        from exchanges.tasks.websocket_tasks import start_websocket_connections
        # Start WebSocket connections after 30 seconds
        start_websocket_connections.apply_async(countdown=30)
    except ImportError:
        print("WebSocket tasks not available")
    except Exception as e:
        print(f"Error setting up WebSocket connections: {e}")
    """


# ==========================================
# USAGE INSTRUCTIONS
# ==========================================

"""
To run Celery with this configuration:

1. Start Celery Worker:
   celery -A config worker --loglevel=info

2. Start Celery Beat (in another terminal):
   celery -A config beat --loglevel=info

3. Start WebSocket connections (in another terminal):
   python manage.py websocket start --daemon

4. Monitor tasks:
   celery -A config events

5. Test Celery:
   python manage.py shell
   >>> from config.celery import debug_task
   >>> result = debug_task.delay()
   >>> result.get()

6. View logs:
   tail -f logs/celerybeat-schedule
   tail -f logs/crypto_arbitrage.log

Environment Variables needed in .env:
- CELERY_BROKER_URL=redis://localhost:6379/1
- CELERY_RESULT_BACKEND=redis://localhost:6379/2

For production, you might want to run multiple workers:
   celery -A config worker --loglevel=info --concurrency=4

For specific queues (if you enable task routing):
   celery -A config worker --loglevel=info --queues=default,websocket
"""


# ==========================================
# WORKER SIGNALS (OPTIONAL)
# ==========================================

from celery.signals import worker_ready, worker_shutdown

@worker_ready.connect
def worker_ready_handler(sender=None, **kwargs):
    """Called when worker is ready to receive tasks."""
    print(f"Celery worker {sender} is ready!")

@worker_shutdown.connect 
def worker_shutdown_handler(sender=None, **kwargs):
    """Called when worker is shutting down."""
    print(f"Celery worker {sender} is shutting down!")
    
    # Cleanup WebSocket connections if they exist
    try:
        from exchanges.websocket import websocket_manager
        import asyncio
        
        # Try to stop WebSocket connections gracefully
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(websocket_manager.stop_all_exchanges())
        loop.close()
        print("WebSocket connections closed during worker shutdown")
    except Exception as e:
        print(f"Error closing WebSocket connections during shutdown: {e}")


# ==========================================
# HEALTH CHECK TASK
# ==========================================

@app.task
def health_check():
    """Simple health check task for monitoring."""
    try:
        from django.db import connection
        from django.core.cache import cache
        
        # Test database
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            db_status = "ok"
        
        # Test cache
        cache.set('health_check', 'ok', 10)
        cache_status = "ok" if cache.get('health_check') == 'ok' else "error"
        
        return {
            'status': 'healthy',
            'database': db_status,
            'cache': cache_status,
            'timestamp': app.now()
        }
        
    except Exception as e:
        return {
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': app.now()
        }


# ==========================================
# EXPORT
# ==========================================

# Make sure the app is available for import
__all__ = ['app']