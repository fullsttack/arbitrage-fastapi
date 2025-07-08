import os
from celery import Celery
from django.conf import settings

# Set the default Django settings module for the 'celery' program
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

# Create Celery app
app = Celery('crypto_arbitrage')

# Configure Celery using Django settings
app.config_from_object('django.conf:settings', namespace='CELERY')

# Auto-discover tasks from all registered Django apps
app.autodiscover_tasks()

# Optional: Add debug info when in development
@app.task(bind=True)
def debug_task(self):
    """Debug task to test Celery functionality."""
    print(f'Request: {self.request!r}')


# Periodic task schedule based on project requirements
app.conf.beat_schedule = {
    # Market data updates (high frequency)
    'update-exchange-tickers': {
        'task': 'exchanges.tasks.update_exchange_tickers',
        'schedule': float(getattr(settings, 'SCHEDULER_CONFIG', {}).get('price_update_interval', 2)),
    },
    
    # Arbitrage scanning (high frequency)
    'scan-arbitrage-opportunities': {
        'task': 'arbitrage.tasks.scan_arbitrage_opportunities', 
        'schedule': float(getattr(settings, 'SCHEDULER_CONFIG', {}).get('arbitrage_check_interval', 2)),
    },
    
    # Order book updates (very high frequency)
    'update-order-books': {
        'task': 'exchanges.tasks.update_order_books',
        'schedule': float(getattr(settings, 'SCHEDULER_CONFIG', {}).get('order_book_update_interval', 1)),
    },
    
    # Health monitoring (medium frequency)
    'check-exchange-health': {
        'task': 'exchanges.tasks.check_exchange_health',
        'schedule': float(getattr(settings, 'SCHEDULER_CONFIG', {}).get('health_check_interval', 60)),
    },
    
    # System health check (medium frequency) 
    'system-health-check': {
        'task': 'core.tasks.system_health_check',
        'schedule': 300.0,  # Every 5 minutes
    },
    
    # Security monitoring (medium frequency)
    'security-monitoring': {
        'task': 'core.tasks.security_monitoring',
        'schedule': 300.0,  # Every 5 minutes
    },
    
    # Daily analytics (low frequency)
    'generate-daily-analytics': {
        'task': 'analytics.tasks.generate_daily_analytics',
        'schedule': 3600.0,  # Every hour
        'options': {'queue': 'analytics'}
    },
    
    # Market snapshots (medium frequency)
    'capture-market-snapshot': {
        'task': 'analytics.tasks.capture_market_snapshot', 
        'schedule': 300.0,  # Every 5 minutes
    },
    
    # Cleanup tasks (low frequency)
    'cleanup-old-market-data': {
        'task': 'exchanges.tasks.cleanup_old_market_data',
        'schedule': 3600.0,  # Every hour
        'options': {'queue': 'maintenance'}
    },
    
    # Position P&L updates (medium frequency)
    'update-position-pnl': {
        'task': 'trading.tasks.update_position_pnl',
        'schedule': 60.0,  # Every minute
    },
    
    # Cleanup old opportunities (low frequency) 
    'cleanup-old-opportunities': {
        'task': 'arbitrage.tasks.cleanup_old_opportunities',
        'schedule': 21600.0,  # Every 6 hours
        'options': {'queue': 'maintenance'}
    },
}

# Task routing configuration
app.conf.task_routes = {
    # High-priority trading tasks
    'arbitrage.tasks.execute_arbitrage_opportunity': {'queue': 'trading'},
    'arbitrage.tasks.execute_multi_exchange_strategy': {'queue': 'trading'},
    'trading.tasks.execute_order': {'queue': 'trading'},
    'trading.tasks.monitor_order_status': {'queue': 'trading'},
    
    # Market data tasks
    'exchanges.tasks.*': {'queue': 'market_data'},
    
    # Analytics tasks (can be slower)
    'analytics.tasks.*': {'queue': 'analytics'},
    
    # Maintenance tasks (lowest priority)
    '*cleanup*': {'queue': 'maintenance'},
    'core.tasks.*': {'queue': 'system'},
}

# Worker configuration
app.conf.task_default_queue = 'default'
app.conf.task_create_missing_queues = True

# Set timezone
app.conf.timezone = getattr(settings, 'TIME_ZONE', 'UTC')

# Performance optimizations for arbitrage trading
app.conf.update(
    # Critical for real-time arbitrage
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    
    # Worker lifecycle
    worker_max_tasks_per_child=1000,
    worker_disable_rate_limits=True,
    
    # Task timeouts
    task_soft_time_limit=300,  # 5 minutes
    task_time_limit=600,       # 10 minutes
    
    # Serialization
    task_serializer='json',
    result_serializer='json',
    accept_content=['json'],
    
    # Results
    result_expires=3600,  # 1 hour
    task_ignore_result=False,
    
    # Connection settings
    broker_connection_retry_on_startup=True,
    broker_connection_retry=True,
)

# Queue priority levels (higher number = higher priority)
app.conf.task_queue_max_priority = 10
app.conf.task_default_priority = 5
app.conf.worker_prefetch_multiplier = 1

# Define priority for critical tasks
TASK_PRIORITIES = {
    'arbitrage.tasks.execute_arbitrage_opportunity': 9,
    'arbitrage.tasks.execute_multi_exchange_strategy': 9,
    'trading.tasks.execute_order': 8,
    'trading.tasks.monitor_order_status': 8,
    'exchanges.tasks.update_exchange_tickers': 7,
    'arbitrage.tasks.scan_arbitrage_opportunities': 7,
    'exchanges.tasks.update_order_books': 6,
    'exchanges.tasks.check_exchange_health': 5,
    'analytics.tasks.*': 3,
    '*cleanup*': 1,
}

@app.task(bind=True)
def route_task_with_priority(self, task_name, *args, **kwargs):
    """Route tasks with appropriate priority."""
    priority = TASK_PRIORITIES.get(task_name, 5)
    return self.apply_async(args=args, kwargs=kwargs, priority=priority)