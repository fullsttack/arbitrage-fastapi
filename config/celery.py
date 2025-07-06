import os

from celery import Celery
from celery.schedules import crontab

# Set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.base')

app = Celery('crypto_arbitrage')

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
# - namespace='CELERY' means all celery-related configuration keys
#   should have a `CELERY_` prefix.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Load task modules from all registered Django apps.
app.autodiscover_tasks()

# Celery beat schedule
app.conf.beat_schedule = {
    # Scan for arbitrage opportunities every 10 seconds
    'scan-arbitrage-opportunities': {
        'task': 'arbitrage.tasks.scan_arbitrage_opportunities',
        'schedule': 10.0,
    },
    
    # Update exchange tickers every 5 seconds
    'update-exchange-tickers': {
        'task': 'exchanges.tasks.update_exchange_tickers',
        'schedule': 5.0,
    },
    
    # Update order books for active opportunities every 3 seconds
    'update-order-books': {
        'task': 'exchanges.tasks.update_order_books',
        'schedule': 3.0,
    },
    
    # Check exchange health every minute
    'check-exchange-health': {
        'task': 'exchanges.tasks.check_exchange_health',
        'schedule': 60.0,
    },
    
    # Clean up old market data every hour
    'cleanup-old-market-data': {
        'task': 'exchanges.tasks.cleanup_old_market_data',
        'schedule': crontab(minute=0),
    },
    
    # Generate market summary every 5 minutes
    'generate-market-summary': {
        'task': 'exchanges.tasks.generate_market_summary',
        'schedule': 300.0,
    },
    
    # Update position P&L every 30 seconds
    'update-position-pnl': {
        'task': 'trading.tasks.update_position_pnl',
        'schedule': 30.0,
    },
    
    # Generate daily report at midnight
    'generate-daily-report': {
        'task': 'arbitrage.tasks.generate_daily_report',
        'schedule': crontab(hour=0, minute=0),
    },
    
    # Clean up old opportunities daily
    'cleanup-old-opportunities': {
        'task': 'arbitrage.tasks.cleanup_old_opportunities',
        'schedule': crontab(hour=1, minute=0),
    },
    
    # Generate analytics daily
    'generate-daily-analytics': {
        'task': 'analytics.tasks.generate_daily_analytics',
        'schedule': crontab(hour=2, minute=0),
    },
}


@app.task(bind=True)
def debug_task(self):
    """Debug task to test Celery is working."""
    print(f'Request: {self.request!r}')