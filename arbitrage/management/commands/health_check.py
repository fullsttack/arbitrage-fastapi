from django.core.management.base import BaseCommand
from django.utils import timezone
from arbitrage.models import MultiExchangeArbitrageStrategy, MultiExchangeExecution
from exchanges.models import ExchangeStatus
from core.models import Exchange
from celery import current_app
import redis
from django.db import connection
from datetime import timedelta


class Command(BaseCommand):
    help = 'Perform comprehensive health check of the arbitrage system'

    def handle(self, *args, **options):
        self.stdout.write('='*60)
        self.stdout.write('ARBITRAGE SYSTEM HEALTH CHECK')
        self.stdout.write('='*60)
        
        # Check database connectivity
        self.check_database()
        
        # Check Redis connectivity
        self.check_redis()
        
        # Check Celery workers
        self.check_celery()
        
        # Check exchange connectivity
        self.check_exchanges()
        
        # Check strategy execution health
        self.check_strategy_health()
        
        # Check system performance
        self.check_performance()
        
        self.stdout.write('='*60)
        self.stdout.write('Health check completed.')

    def check_database(self):
        self.stdout.write('\n📁 Database Connectivity:')
        try:
            with connection.cursor() as cursor:
                cursor.execute('SELECT 1')
                cursor.fetchone()
            self.stdout.write(self.style.SUCCESS('  ✅ Database connection OK'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'  ❌ Database error: {e}'))

    def check_redis(self):
        self.stdout.write('\n🗄️  Redis Connectivity:')
        try:
            from django.core.cache import cache
            cache.set('health_check', 'ok', 10)
            result = cache.get('health_check')
            if result == 'ok':
                self.stdout.write(self.style.SUCCESS('  ✅ Redis connection OK'))
            else:
                self.stdout.write(self.style.ERROR('  ❌ Redis cache test failed'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'  ❌ Redis error: {e}'))

    def check_celery(self):
        self.stdout.write('\n⚙️  Celery Workers:')
        try:
            inspect = current_app.control.inspect()
            stats = inspect.stats()
            
            if stats:
                for worker, worker_stats in stats.items():
                    self.stdout.write(f'  ✅ {worker}: {worker_stats.get("total", 0)} tasks processed')
            else:
                self.stdout.write(self.style.WARNING('  ⚠️  No active workers found'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'  ❌ Celery error: {e}'))

    def check_exchanges(self):
        self.stdout.write('\n🏦 Exchange Status:')
        exchanges = Exchange.objects.filter(is_active=True)
        
        for exchange in exchanges:
            try:
                status = ExchangeStatus.objects.filter(exchange=exchange).first()
                if status:
                    if status.is_online:
                        response_time = status.response_time or 0
                        self.stdout.write(
                            f'  ✅ {exchange.name}: Online '
                            f'({response_time:.2f}s response)'
                        )
                    else:
                        self.stdout.write(
                            self.style.WARNING(
                                f'  ⚠️  {exchange.name}: Offline'
                            )
                        )
                else:
                    self.stdout.write(
                        self.style.WARNING(
                            f'  ⚠️  {exchange.name}: No status data'
                        )
                    )
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(
                        f'  ❌ {exchange.name}: Error - {e}'
                    )
                )

    def check_strategy_health(self):
        self.stdout.write('\n🎯 Strategy Execution Health:')
        
        # Check for stuck strategies
        stuck_strategies = MultiExchangeArbitrageStrategy.objects.filter(
            status='executing',
            execution_started_at__lt=timezone.now() - timedelta(minutes=10)
        )
        
        if stuck_strategies.exists():
            self.stdout.write(
                self.style.WARNING(
                    f'  ⚠️  {stuck_strategies.count()} strategies appear stuck'
                )
            )
        else:
            self.stdout.write('  ✅ No stuck strategies detected')
        
        # Check execution success rate (last 24h)
        recent_strategies = MultiExchangeArbitrageStrategy.objects.filter(
            created_at__gte=timezone.now() - timedelta(hours=24)
        )
        
        if recent_strategies.exists():
            completed = recent_strategies.filter(status='completed').count()
            total = recent_strategies.count()
            success_rate = (completed / total) * 100
            
            if success_rate > 80:
                self.stdout.write(
                    self.style.SUCCESS(
                        f'  ✅ Strategy success rate: {success_rate:.1f}%'
                    )
                )
            elif success_rate > 60:
                self.stdout.write(
                    self.style.WARNING(
                        f'  ⚠️  Strategy success rate: {success_rate:.1f}%'
                    )
                )
            else:
                self.stdout.write(
                    self.style.ERROR(
                        f'  ❌ Low strategy success rate: {success_rate:.1f}%'
                    )
                )

    def check_performance(self):
        self.stdout.write('\n📊 Performance Metrics:')
        
        # Check recent opportunity detection
        recent_opportunities = MultiExchangeArbitrageStrategy.objects.filter(
            created_at__gte=timezone.now() - timedelta(hours=1)
        ).count()
        
        self.stdout.write(f'  📈 Opportunities detected (last hour): {recent_opportunities}')
        
        # Check execution latency
        recent_executions = MultiExchangeExecution.objects.filter(
            created_at__gte=timezone.now() - timedelta(hours=1),
            execution_latency__isnull=False
        )
        
        if recent_executions.exists():
            avg_latency = recent_executions.aggregate(
                avg=models.Avg('execution_latency')
            )['avg']
            
            if avg_latency < 5:
                self.stdout.write(
                    self.style.SUCCESS(
                        f'  ✅ Average execution latency: {avg_latency:.2f}s'
                    )
                )
            else:
                self.stdout.write(
                    self.style.WARNING(
                        f'  ⚠️  Average execution latency: {avg_latency:.2f}s'
                    )
                )