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

# Enhanced Celery beat schedule for multi-exchange arbitrage
app.conf.beat_schedule = {
    # Enhanced arbitrage scanning every 10 seconds
    'scan-arbitrage-opportunities': {
        'task': 'arbitrage.tasks.scan_arbitrage_opportunities',
        'schedule': 10.0,
        'options': {
            'queue': 'arbitrage_scan',
            'priority': 9,  # High priority for opportunity detection
        }
    },
    
    # Update exchange tickers every 5 seconds
    'update-exchange-tickers': {
        'task': 'exchanges.tasks.update_exchange_tickers',
        'schedule': 5.0,
        'options': {
            'queue': 'market_data',
            'priority': 8,
        }
    },
    
    # Update order books for active opportunities every 3 seconds
    'update-order-books': {
        'task': 'exchanges.tasks.update_order_books',
        'schedule': 3.0,
        'options': {
            'queue': 'market_data',
            'priority': 8,
        }
    },
    
    # Check exchange health every minute
    'check-exchange-health': {
        'task': 'exchanges.tasks.check_exchange_health',
        'schedule': 60.0,
        'options': {
            'queue': 'monitoring',
            'priority': 5,
        }
    },
    
    # Clean up old market data every hour
    'cleanup-old-market-data': {
        'task': 'exchanges.tasks.cleanup_old_market_data',
        'schedule': crontab(minute=0),
        'options': {
            'queue': 'cleanup',
            'priority': 2,
        }
    },
    
    # Generate market summary every 5 minutes
    'generate-market-summary': {
        'task': 'exchanges.tasks.generate_market_summary',
        'schedule': 300.0,
        'options': {
            'queue': 'analytics',
            'priority': 4,
        }
    },
    
    # Update position P&L every 30 seconds
    'update-position-pnl': {
        'task': 'trading.tasks.update_position_pnl',
        'schedule': 30.0,
        'options': {
            'queue': 'trading',
            'priority': 6,
        }
    },
    
    # Clean up old opportunities and strategies every 30 minutes
    'cleanup-old-opportunities': {
        'task': 'arbitrage.tasks.cleanup_old_opportunities',
        'schedule': crontab(minute='*/30'),
        'options': {
            'queue': 'cleanup',
            'priority': 2,
        }
    },
    
    # Generate daily analytics at 2 AM
    'generate-daily-analytics': {
        'task': 'analytics.tasks.generate_daily_analytics',
        'schedule': crontab(hour=2, minute=0),
        'options': {
            'queue': 'analytics',
            'priority': 3,
        }
    },
    
    # Generate daily arbitrage report at midnight
    'generate-daily-report': {
        'task': 'arbitrage.tasks.generate_daily_report',
        'schedule': crontab(hour=0, minute=0),
        'options': {
            'queue': 'reports',
            'priority': 3,
        }
    },
    
    # New multi-exchange specific tasks
    
    # Monitor multi-exchange strategy executions every 10 seconds
    'monitor-multi-strategies': {
        'task': 'arbitrage.tasks.monitor_active_multi_strategies',
        'schedule': 10.0,
        'options': {
            'queue': 'execution_monitoring',
            'priority': 8,
        }
    },
    
    # Validate active strategies every 30 seconds
    'validate-active-strategies': {
        'task': 'arbitrage.tasks.validate_active_strategies',
        'schedule': 30.0,
        'options': {
            'queue': 'validation',
            'priority': 7,
        }
    },
    
    # Calculate strategy risk scores every 5 minutes
    'calculate-strategy-risks': {
        'task': 'arbitrage.tasks.calculate_strategy_risks',
        'schedule': 300.0,
        'options': {
            'queue': 'risk_analysis',
            'priority': 4,
        }
    },
    
    # Update exchange reliability weights every hour
    'update-exchange-reliability': {
        'task': 'arbitrage.tasks.update_exchange_reliability',
        'schedule': crontab(minute=0),
        'options': {
            'queue': 'analytics',
            'priority': 3,
        }
    },
    
    # Optimize allocation strategies every 6 hours
    'optimize-allocation-strategies': {
        'task': 'arbitrage.tasks.optimize_allocation_strategies',
        'schedule': crontab(minute=0, hour='*/6'),
        'options': {
            'queue': 'optimization',
            'priority': 2,
        }
    },
    
    # Generate performance comparison reports daily at 3 AM
    'generate-performance-comparison': {
        'task': 'arbitrage.tasks.generate_performance_comparison',
        'schedule': crontab(hour=3, minute=0),
        'options': {
            'queue': 'reports',
            'priority': 3,
        }
    },
    
    # Cleanup failed executions daily at 4 AM
    'cleanup-failed-executions': {
        'task': 'arbitrage.tasks.cleanup_failed_executions',
        'schedule': crontab(hour=4, minute=0),
        'options': {
            'queue': 'cleanup',
            'priority': 2,
        }
    },
    
    # Backup strategy configurations daily at 5 AM
    'backup-strategy-configs': {
        'task': 'arbitrage.tasks.backup_strategy_configs',
        'schedule': crontab(hour=5, minute=0),
        'options': {
            'queue': 'backup',
            'priority': 1,
        }
    },
}

# Enhanced Celery configuration for multi-exchange operations
app.conf.update(
    # Task routing for different queues
    task_routes={
        # High priority arbitrage tasks
        'arbitrage.tasks.scan_arbitrage_opportunities': {'queue': 'arbitrage_scan'},
        'arbitrage.tasks.execute_multi_exchange_strategy': {'queue': 'arbitrage_execution'},
        'arbitrage.tasks.execute_single_exchange_action': {'queue': 'arbitrage_execution'},
        'arbitrage.tasks.monitor_multi_strategy_execution': {'queue': 'execution_monitoring'},
        'arbitrage.tasks.monitor_single_execution': {'queue': 'execution_monitoring'},
        
        # Market data tasks
        'exchanges.tasks.update_exchange_tickers': {'queue': 'market_data'},
        'exchanges.tasks.update_order_books': {'queue': 'market_data'},
        'exchanges.tasks.sync_exchange_markets': {'queue': 'market_data'},
        
        # Trading tasks
        'trading.tasks.execute_order': {'queue': 'trading'},
        'trading.tasks.monitor_order_status': {'queue': 'trading'},
        'trading.tasks.update_position_pnl': {'queue': 'trading'},
        
        # Analytics and reporting
        'analytics.tasks.*': {'queue': 'analytics'},
        'arbitrage.tasks.generate_daily_report': {'queue': 'reports'},
        'arbitrage.tasks.generate_performance_comparison': {'queue': 'reports'},
        
        # Background cleanup
        'arbitrage.tasks.cleanup_old_opportunities': {'queue': 'cleanup'},
        'exchanges.tasks.cleanup_old_market_data': {'queue': 'cleanup'},
        
        # Monitoring and health checks
        'exchanges.tasks.check_exchange_health': {'queue': 'monitoring'},
        'exchanges.tasks.check_exchange_status': {'queue': 'monitoring'},
    },
    
    # Worker configuration for different queue types
    worker_prefetch_multiplier=1,  # Important for real-time tasks
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    
    # Task time limits
    task_soft_time_limit=300,  # 5 minutes soft limit
    task_time_limit=600,       # 10 minutes hard limit
    
    # Specific time limits for different task types
    task_annotations={
        'arbitrage.tasks.execute_multi_exchange_strategy': {
            'rate_limit': '10/m',  # Max 10 strategy executions per minute
            'time_limit': 300,     # 5 minutes for strategy execution
            'soft_time_limit': 240,
        },
        'arbitrage.tasks.execute_single_exchange_action': {
            'rate_limit': '100/m',  # Max 100 single actions per minute
            'time_limit': 60,       # 1 minute for single action
            'soft_time_limit': 45,
        },
        'arbitrage.tasks.scan_arbitrage_opportunities': {
            'rate_limit': '6/m',    # Every 10 seconds
            'time_limit': 30,       # 30 seconds for scanning
            'soft_time_limit': 25,
        },
        'exchanges.tasks.update_exchange_tickers': {
            'rate_limit': '12/m',   # Every 5 seconds
            'time_limit': 15,       # 15 seconds for ticker updates
            'soft_time_limit': 12,
        },
        'exchanges.tasks.update_order_books': {
            'rate_limit': '20/m',   # Every 3 seconds
            'time_limit': 10,       # 10 seconds for order book updates
            'soft_time_limit': 8,
        },
    },
    
    # Result backend configuration
    result_expires=3600,  # Results expire after 1 hour
    result_compression='gzip',
    
    # Serialization
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    
    # Timezone
    timezone='UTC',
    enable_utc=True,
    
    # Beat scheduler
    beat_scheduler='django_celery_beat.schedulers:DatabaseScheduler',
    beat_schedule_filename='celerybeat-schedule',
    
    # Queue configuration
    task_default_queue='default',
    task_default_exchange='default',
    task_default_exchange_type='direct',
    task_default_routing_key='default',
    
    # Custom queue definitions
    task_queues={
        'arbitrage_scan': {
            'exchange': 'arbitrage_scan',
            'routing_key': 'arbitrage_scan',
        },
        'arbitrage_execution': {
            'exchange': 'arbitrage_execution',
            'routing_key': 'arbitrage_execution',
        },
        'execution_monitoring': {
            'exchange': 'execution_monitoring',
            'routing_key': 'execution_monitoring',
        },
        'market_data': {
            'exchange': 'market_data',
            'routing_key': 'market_data',
        },
        'trading': {
            'exchange': 'trading',
            'routing_key': 'trading',
        },
        'analytics': {
            'exchange': 'analytics',
            'routing_key': 'analytics',
        },
        'reports': {
            'exchange': 'reports',
            'routing_key': 'reports',
        },
        'cleanup': {
            'exchange': 'cleanup',
            'routing_key': 'cleanup',
        },
        'monitoring': {
            'exchange': 'monitoring',
            'routing_key': 'monitoring',
        },
        'validation': {
            'exchange': 'validation',
            'routing_key': 'validation',
        },
        'risk_analysis': {
            'exchange': 'risk_analysis',
            'routing_key': 'risk_analysis',
        },
        'optimization': {
            'exchange': 'optimization',
            'routing_key': 'optimization',
        },
        'backup': {
            'exchange': 'backup',
            'routing_key': 'backup',
        },
    },
    
    # Worker pool configuration
    worker_pool='prefork',
    worker_concurrency=4,  # Adjust based on your server capacity
    
    # Error handling
    task_ignore_result=False,
    task_store_errors_even_if_ignored=True,
    
    # Security
    worker_hijack_root_logger=False,
    worker_log_color=False,
)


@app.task(bind=True)
def debug_task(self):
    """Debug task to test Celery is working."""
    print(f'Request: {self.request!r}')


# Task for monitoring worker health
@app.task
def worker_health_check():
    """Health check task for monitoring worker status."""
    return {
        'status': 'healthy',
        'timestamp': app.now(),
        'worker_id': app.control.inspect().stats(),
    }


# Custom task for emergency shutdown
@app.task
def emergency_stop_all_strategies():
    """Emergency task to stop all active arbitrage strategies."""
    from arbitrage.models import MultiExchangeArbitrageStrategy
    
    active_strategies = MultiExchangeArbitrageStrategy.objects.filter(
        status__in=['executing', 'validating']
    )
    
    stopped_count = 0
    for strategy in active_strategies:
        try:
            # Cancel all active executions
            for execution in strategy.executions.filter(
                status__in=['pending', 'order_placed', 'partially_filled']
            ):
                from arbitrage.tasks import cancel_single_execution
                cancel_single_execution.delay(execution.id)
            
            strategy.status = 'cancelled'
            strategy.save()
            stopped_count += 1
            
        except Exception as e:
            print(f"Error stopping strategy {strategy.id}: {e}")
    
    return f"Emergency stop completed. Stopped {stopped_count} strategies."


# Task retry configuration
app.conf.task_default_retry_delay = 30  # 30 seconds
app.conf.task_max_retries = 3

# Logging configuration
app.conf.worker_log_format = '[%(asctime)s: %(levelname)s/%(processName)s] %(message)s'
app.conf.worker_task_log_format = '[%(asctime)s: %(levelname)s/%(processName)s][%(task_name)s(%(task_id)s)] %(message)s'

# Monitor configuration
app.conf.worker_send_task_events = True
app.conf.task_send_sent_event = True