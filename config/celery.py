"""
FIXED: Celery configuration with optimized performance for competitive arbitrage.
"""

import os
from celery import Celery
from celery.schedules import crontab

# Set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.base')

app = Celery('crypto_arbitrage')

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Load task modules from all registered Django apps.
app.autodiscover_tasks()

# FIXED: Enhanced Celery beat schedule with competitive arbitrage timing
app.conf.beat_schedule = {
    # CRITICAL: Faster arbitrage scanning - EVERY 2 SECONDS
    'scan-arbitrage-opportunities': {
        'task': 'arbitrage.tasks.scan_arbitrage_opportunities',
        'schedule': 2.0,  # FIXED: 2 seconds instead of 10
        'options': {
            'queue': 'arbitrage_scan',
            'priority': 10,  # HIGHEST priority
            'expires': 5,    # Expire if not processed within 5 seconds
        }
    },
    
    # CRITICAL: Market data updates - EVERY 1 SECOND
    'update-exchange-tickers': {
        'task': 'exchanges.tasks.update_exchange_tickers',
        'schedule': 1.0,  # FIXED: 1 second instead of 5
        'options': {
            'queue': 'market_data',
            'priority': 9,
            'expires': 3,
        }
    },
    
    # CRITICAL: Order book updates - EVERY 500ms for active opportunities
    'update-order-books': {
        'task': 'exchanges.tasks.update_order_books',
        'schedule': 0.5,  # FIXED: 500ms for competitive edge
        'options': {
            'queue': 'market_data',
            'priority': 9,
            'expires': 2,
        }
    },
    
    # Market validation every 5 seconds
    'validate-market-data': {
        'task': 'exchanges.tasks.validate_market_data',
        'schedule': 5.0,
        'options': {
            'queue': 'validation',
            'priority': 7,
        }
    },
    
    # Strategy validation every 10 seconds
    'validate-active-strategies': {
        'task': 'arbitrage.tasks.validate_active_strategies',
        'schedule': 10.0,
        'options': {
            'queue': 'validation',
            'priority': 8,
        }
    },
    
    # Monitor multi-exchange strategies every 5 seconds
    'monitor-multi-strategies': {
        'task': 'arbitrage.tasks.monitor_active_multi_strategies',
        'schedule': 5.0,
        'options': {
            'queue': 'execution_monitoring',
            'priority': 8,
        }
    },
    
    # Exchange health monitoring every 30 seconds
    'check-exchange-health': {
        'task': 'exchanges.tasks.check_exchange_health',
        'schedule': 30.0,
        'options': {
            'queue': 'monitoring',
            'priority': 5,
        }
    },
    
    # Position P&L updates every 10 seconds
    'update-position-pnl': {
        'task': 'trading.tasks.update_position_pnl',
        'schedule': 10.0,
        'options': {
            'queue': 'trading',
            'priority': 6,
        }
    },
    
    # Risk assessment every minute
    'calculate-strategy-risks': {
        'task': 'arbitrage.tasks.calculate_strategy_risks',
        'schedule': 60.0,
        'options': {
            'queue': 'risk_analysis',
            'priority': 4,
        }
    },
    
    # Performance optimization every 5 minutes
    'optimize-allocation-strategies': {
        'task': 'arbitrage.tasks.optimize_allocation_strategies',
        'schedule': 300.0,
        'options': {
            'queue': 'optimization',
            'priority': 3,
        }
    },
    
    # Exchange reliability updates every 10 minutes
    'update-exchange-reliability': {
        'task': 'arbitrage.tasks.update_exchange_reliability',
        'schedule': 600.0,
        'options': {
            'queue': 'analytics',
            'priority': 3,
        }
    },
    
    # Market summary every 5 minutes
    'generate-market-summary': {
        'task': 'exchanges.tasks.generate_market_summary',
        'schedule': 300.0,
        'options': {
            'queue': 'analytics',
            'priority': 4,
        }
    },
    
    # Clean up expired opportunities every 2 minutes
    'cleanup-expired-opportunities': {
        'task': 'arbitrage.tasks.cleanup_expired_opportunities',
        'schedule': 120.0,
        'options': {
            'queue': 'cleanup',
            'priority': 2,
        }
    },
    
    # Clean up old market data every 30 minutes
    'cleanup-old-market-data': {
        'task': 'exchanges.tasks.cleanup_old_market_data',
        'schedule': crontab(minute='*/30'),
        'options': {
            'queue': 'cleanup',
            'priority': 2,
        }
    },
    
    # Daily analytics at 2 AM
    'generate-daily-analytics': {
        'task': 'analytics.tasks.generate_daily_analytics',
        'schedule': crontab(hour=2, minute=0),
        'options': {
            'queue': 'analytics',
            'priority': 3,
        }
    },
    
    # Performance comparison reports every 6 hours
    'generate-performance-comparison': {
        'task': 'arbitrage.tasks.generate_performance_comparison',
        'schedule': crontab(minute=0, hour='*/6'),
        'options': {
            'queue': 'reports',
            'priority': 3,
        }
    },
    
    # Security monitoring every minute
    'security-monitoring': {
        'task': 'core.tasks.security_monitoring',
        'schedule': 60.0,
        'options': {
            'queue': 'monitoring',
            'priority': 6,
        }
    },
    
    # System health check every 5 minutes
    'system-health-check': {
        'task': 'core.tasks.system_health_check',
        'schedule': 300.0,
        'options': {
            'queue': 'monitoring',
            'priority': 5,
        }
    },
}

# ENHANCED: Celery configuration optimized for high-frequency trading
app.conf.update(
    # CRITICAL: Task routing for optimal performance
    task_routes={
        # HIGHEST PRIORITY: Arbitrage detection and execution
        'arbitrage.tasks.scan_arbitrage_opportunities': {
            'queue': 'arbitrage_scan',
            'priority': 10
        },
        'arbitrage.tasks.execute_multi_exchange_strategy': {
            'queue': 'arbitrage_execution',
            'priority': 10
        },
        'arbitrage.tasks.execute_single_exchange_action': {
            'queue': 'arbitrage_execution',
            'priority': 10
        },
        
        # HIGH PRIORITY: Market data and monitoring
        'exchanges.tasks.update_exchange_tickers': {
            'queue': 'market_data',
            'priority': 9
        },
        'exchanges.tasks.update_order_books': {
            'queue': 'market_data',
            'priority': 9
        },
        'arbitrage.tasks.monitor_multi_strategy_execution': {
            'queue': 'execution_monitoring',
            'priority': 8
        },
        'arbitrage.tasks.monitor_single_execution': {
            'queue': 'execution_monitoring',
            'priority': 8
        },
        
        # MEDIUM PRIORITY: Trading operations
        'trading.tasks.execute_order': {
            'queue': 'trading',
            'priority': 7
        },
        'trading.tasks.monitor_order_status': {
            'queue': 'trading',
            'priority': 7
        },
        'trading.tasks.update_position_pnl': {
            'queue': 'trading',
            'priority': 6
        },
        
        # VALIDATION tasks
        'arbitrage.tasks.validate_active_strategies': {
            'queue': 'validation',
            'priority': 7
        },
        'exchanges.tasks.validate_market_data': {
            'queue': 'validation',
            'priority': 7
        },
        
        # ANALYTICS and reporting
        'analytics.tasks.*': {
            'queue': 'analytics',
            'priority': 4
        },
        'arbitrage.tasks.generate_performance_comparison': {
            'queue': 'reports',
            'priority': 3
        },
        
        # BACKGROUND tasks
        'arbitrage.tasks.cleanup_old_opportunities': {
            'queue': 'cleanup',
            'priority': 2
        },
        'exchanges.tasks.cleanup_old_market_data': {
            'queue': 'cleanup',
            'priority': 2
        },
        
        # MONITORING tasks
        'exchanges.tasks.check_exchange_health': {
            'queue': 'monitoring',
            'priority': 5
        },
        'core.tasks.security_monitoring': {
            'queue': 'monitoring',
            'priority': 6
        },
    },
    
    # PERFORMANCE: Optimized worker configuration
    worker_prefetch_multiplier=1,  # CRITICAL: Prevent task hoarding
    task_acks_late=True,           # Ensure task completion
    task_reject_on_worker_lost=True,
    worker_max_tasks_per_child=500,  # Prevent memory leaks
    worker_max_memory_per_child=200000,  # 200MB limit
    
    # TIMING: Aggressive timeouts for trading
    task_soft_time_limit=30,   # 30 seconds soft limit
    task_time_limit=60,        # 60 seconds hard limit
    
    # SPECIFIC time limits for critical tasks
    task_annotations={
        # ARBITRAGE: Very short timeouts for competitive advantage
        'arbitrage.tasks.scan_arbitrage_opportunities': {
            'rate_limit': '30/m',  # 30 scans per minute max
            'time_limit': 15,      # 15 seconds max
            'soft_time_limit': 10,
            'expires': 5,          # Expire in 5 seconds if not started
        },
        'arbitrage.tasks.execute_multi_exchange_strategy': {
            'rate_limit': '100/m',
            'time_limit': 120,     # 2 minutes for strategy execution
            'soft_time_limit': 90,
        },
        'arbitrage.tasks.execute_single_exchange_action': {
            'rate_limit': '200/m',
            'time_limit': 30,      # 30 seconds for single action
            'soft_time_limit': 20,
        },
        
        # MARKET DATA: High frequency, short timeouts
        'exchanges.tasks.update_exchange_tickers': {
            'rate_limit': '60/m',  # Once per second
            'time_limit': 10,      # 10 seconds max
            'soft_time_limit': 7,
            'expires': 3,
        },
        'exchanges.tasks.update_order_books': {
            'rate_limit': '120/m', # Twice per second
            'time_limit': 8,       # 8 seconds max
            'soft_time_limit': 5,
            'expires': 2,
        },
        
        # TRADING: Medium timeouts
        'trading.tasks.execute_order': {
            'rate_limit': '100/m',
            'time_limit': 45,
            'soft_time_limit': 30,
        },
        'trading.tasks.monitor_order_status': {
            'rate_limit': '200/m',
            'time_limit': 20,
            'soft_time_limit': 15,
        },
    },
    
    # RESULT backend optimization
    result_expires=300,        # Results expire after 5 minutes
    result_compression='gzip',
    result_backend_transport_options={
        'master_name': 'mymaster',
        'retry_policy': {
            'timeout': 5.0
        }
    },
    
    # SERIALIZATION
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    
    # TIMEZONE
    timezone='UTC',
    enable_utc=True,
    
    # BROKER optimization
    broker_transport_options={
        'priority_steps': list(range(11)),  # 0-10 priority levels
        'sep': ':',
        'queue_order_strategy': 'priority',
        'socket_timeout': 10.0,
        'socket_connect_timeout': 10.0,
    },
    
    # BEAT scheduler
    beat_scheduler='django_celery_beat.schedulers:DatabaseScheduler',
    beat_schedule_filename='celerybeat-schedule',
    beat_max_loop_interval=60,  # Check for new tasks every minute
    
    # QUEUE configuration with priorities
    task_default_queue='default',
    task_default_exchange='default',
    task_default_exchange_type='direct',
    task_default_routing_key='default',
    
    # ENHANCED queue definitions with priority support
    task_queues={
        # HIGHEST PRIORITY: Arbitrage scanning
        'arbitrage_scan': {
            'exchange': 'arbitrage_scan',
            'routing_key': 'arbitrage_scan',
            'priority': 10,
        },
        
        # HIGH PRIORITY: Arbitrage execution
        'arbitrage_execution': {
            'exchange': 'arbitrage_execution',
            'routing_key': 'arbitrage_execution',
            'priority': 10,
        },
        
        # HIGH PRIORITY: Execution monitoring
        'execution_monitoring': {
            'exchange': 'execution_monitoring',
            'routing_key': 'execution_monitoring',
            'priority': 9,
        },
        
        # HIGH PRIORITY: Market data
        'market_data': {
            'exchange': 'market_data',
            'routing_key': 'market_data',
            'priority': 9,
        },
        
        # MEDIUM PRIORITY: Trading
        'trading': {
            'exchange': 'trading',
            'routing_key': 'trading',
            'priority': 7,
        },
        
        # MEDIUM PRIORITY: Validation
        'validation': {
            'exchange': 'validation',
            'routing_key': 'validation',
            'priority': 7,
        },
        
        # LOWER PRIORITY: Analytics
        'analytics': {
            'exchange': 'analytics',
            'routing_key': 'analytics',
            'priority': 4,
        },
        
        # LOWER PRIORITY: Reports
        'reports': {
            'exchange': 'reports',
            'routing_key': 'reports',
            'priority': 3,
        },
        
        # LOW PRIORITY: Cleanup
        'cleanup': {
            'exchange': 'cleanup',
            'routing_key': 'cleanup',
            'priority': 2,
        },
        
        # MEDIUM PRIORITY: Monitoring
        'monitoring': {
            'exchange': 'monitoring',
            'routing_key': 'monitoring',
            'priority': 5,
        },
        
        # MEDIUM PRIORITY: Risk analysis
        'risk_analysis': {
            'exchange': 'risk_analysis',
            'routing_key': 'risk_analysis',
            'priority': 6,
        },
        
        # LOW PRIORITY: Optimization
        'optimization': {
            'exchange': 'optimization',
            'routing_key': 'optimization',
            'priority': 3,
        },
        
        # VERY LOW PRIORITY: Backup
        'backup': {
            'exchange': 'backup',
            'routing_key': 'backup',
            'priority': 1,
        },
    },
    
    # WORKER pool configuration
    worker_pool='prefork',
    worker_concurrency=4,  # Adjust based on CPU cores
    
    # ERROR handling
    task_ignore_result=False,
    task_store_errors_even_if_ignored=True,
    
    # SECURITY
    worker_hijack_root_logger=False,
    worker_log_color=False,
    
    # MONITORING
    worker_send_task_events=True,
    task_send_sent_event=True,
    
    # OPTIMIZATION: Disable UTC conversion for performance
    task_always_eager=False,  # Never set to True in production
    task_eager_propagates=False,
)


@app.task(bind=True)
def debug_task(self):
    """Debug task to test Celery is working."""
    print(f'Request: {self.request!r}')


@app.task
def worker_health_check():
    """Health check task for monitoring worker status."""
    return {
        'status': 'healthy',
        'timestamp': app.now(),
        'worker_id': app.control.inspect().stats(),
    }


@app.task(bind=True, max_retries=0)
def emergency_stop_all_strategies(self):
    """CRITICAL: Emergency task to stop all active arbitrage strategies."""
    from arbitrage.models import MultiExchangeArbitrageStrategy
    
    try:
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
        
    except Exception as exc:
        print(f"Emergency stop failed: {exc}")
        raise


@app.task
def performance_monitoring():
    """Task to monitor system performance and alert on issues."""
    import psutil
    from django.core.cache import cache
    
    # Check CPU usage
    cpu_percent = psutil.cpu_percent(interval=1)
    if cpu_percent > 90:
        print(f"HIGH CPU USAGE: {cpu_percent}%")
    
    # Check memory usage
    memory = psutil.virtual_memory()
    if memory.percent > 90:
        print(f"HIGH MEMORY USAGE: {memory.percent}%")
    
    # Check Redis connection
    try:
        cache.set('health_check', 'ok', 10)
        cache.get('health_check')
    except Exception as e:
        print(f"REDIS CONNECTION ERROR: {e}")
    
    # Check active tasks
    inspect = app.control.inspect()
    active_tasks = inspect.active()
    if active_tasks:
        total_active = sum(len(tasks) for tasks in active_tasks.values())
        if total_active > 100:
            print(f"HIGH TASK LOAD: {total_active} active tasks")
    
    return {
        'cpu_percent': cpu_percent,
        'memory_percent': memory.percent,
        'active_tasks': total_active if 'total_active' in locals() else 0
    }


# Task retry configuration for resilience
app.conf.task_default_retry_delay = 1  # 1 second for fast retry
app.conf.task_max_retries = 3

# Enhanced logging configuration
app.conf.worker_log_format = '[%(asctime)s: %(levelname)s/%(processName)s][%(task_name)s] %(message)s'
app.conf.worker_task_log_format = '[%(asctime)s: %(levelname)s/%(processName)s][%(task_name)s(%(task_id)s)] %(message)s'

# Monitor configuration for performance tracking
app.conf.worker_send_task_events = True
app.conf.task_send_sent_event = True

# Performance optimization signals
@app.task(bind=True)
def task_failure_handler(self, task_id, error, einfo):
    """Handle task failures for monitoring."""
    print(f'Task {task_id} failed: {error}')


# Setup periodic performance monitoring
app.conf.beat_schedule['performance-monitoring'] = {
    'task': 'config.celery.performance_monitoring',
    'schedule': 60.0,  # Every minute
    'options': {
        'queue': 'monitoring',
        'priority': 5,
    }
}