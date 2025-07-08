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

# FIXED: Simple periodic task schedule using file-based scheduler only
# No database involvement to avoid locks
app.conf.beat_schedule = {
    # Reduced frequency to minimize database conflicts
    'update-exchange-tickers': {
        'task': 'exchanges.tasks.update_exchange_tickers',
        'schedule': 30.0,  # Every 30 seconds instead of 2
    },
    
    'scan-arbitrage-opportunities': {
        'task': 'arbitrage.tasks.scan_arbitrage_opportunities', 
        'schedule': 60.0,  # Every minute instead of 2 seconds
    },
    
    'check-exchange-health': {
        'task': 'exchanges.tasks.check_exchange_health',
        'schedule': 300.0,  # Every 5 minutes
    },
    
    'cleanup-old-opportunities': {
        'task': 'arbitrage.tasks.cleanup_old_opportunities',
        'schedule': 3600.0,  # Every hour
    },
}

# FIXED: Simple task routing
app.conf.task_routes = {
    'arbitrage.tasks.*': {'queue': 'default'},
    'exchanges.tasks.*': {'queue': 'default'},
    'trading.tasks.*': {'queue': 'default'},
    'analytics.tasks.*': {'queue': 'default'},
}

# FIXED: Minimal configuration for SQLite compatibility
app.conf.update(
    # Use file-based scheduler
    beat_scheduler='celery.beat:PersistentScheduler',
    beat_schedule_filename='logs/celerybeat-schedule',
    
    # Single worker settings
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    
    # Reduced limits
    worker_max_tasks_per_child=50,
    worker_concurrency=1,  # Single threaded to avoid DB conflicts
    
    # Task timeouts
    task_soft_time_limit=300,
    task_time_limit=600,
    
    # Serialization
    task_serializer='json',
    result_serializer='json',
    accept_content=['json'],
    
    # Results
    result_expires=3600,
    task_ignore_result=False,
    
    # Connection settings
    broker_connection_retry_on_startup=True,
    broker_connection_retry=True,
    
    # Timezone
    timezone='UTC',
    enable_utc=True,
)

@app.task(bind=True)
def debug_task(self):
    """Debug task to test Celery functionality."""
    print(f'Request: {self.request!r}')
    return 'Debug task completed successfully'