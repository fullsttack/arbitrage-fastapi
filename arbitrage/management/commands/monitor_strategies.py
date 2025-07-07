from django.core.management.base import BaseCommand
from django.utils import timezone
from arbitrage.models import MultiExchangeArbitrageStrategy, MultiExchangeExecution
import time


class Command(BaseCommand):
    help = 'Monitor active multi-exchange strategies in real-time'

    def add_arguments(self, parser):
        parser.add_argument(
            '--refresh',
            type=int,
            default=5,
            help='Refresh interval in seconds'
        )
        parser.add_argument(
            '--strategy-id',
            help='Monitor specific strategy ID'
        )

    def handle(self, *args, **options):
        refresh_interval = options['refresh']
        strategy_id = options.get('strategy_id')
        
        self.stdout.write(self.style.SUCCESS(
            f'Monitoring strategies (refresh every {refresh_interval}s)...'
        ))
        self.stdout.write('Press Ctrl+C to stop\n')
        
        try:
            while True:
                self.clear_screen()
                self.display_strategies(strategy_id)
                time.sleep(refresh_interval)
        except KeyboardInterrupt:
            self.stdout.write('\nMonitoring stopped.')

    def clear_screen(self):
        import os
        os.system('clear' if os.name == 'posix' else 'cls')

    def display_strategies(self, strategy_id=None):
        # Header
        self.stdout.write('='*80)
        self.stdout.write(f'MULTI-EXCHANGE STRATEGY MONITOR - {timezone.now().strftime("%H:%M:%S")}')
        self.stdout.write('='*80)
        
        # Get strategies
        if strategy_id:
            strategies = MultiExchangeArbitrageStrategy.objects.filter(id=strategy_id)
        else:
            strategies = MultiExchangeArbitrageStrategy.objects.filter(
                status__in=['executing', 'validating', 'detected']
            ).order_by('-created_at')[:10]
        
        if not strategies:
            self.stdout.write('No active strategies found.')
            return
        
        for strategy in strategies:
            self.display_strategy_detail(strategy)
            self.stdout.write('-' * 80)

    def display_strategy_detail(self, strategy):
        # Strategy header
        status_color = self.get_status_color(strategy.status)
        self.stdout.write(
            f'Strategy: {strategy.trading_pair.symbol} '
            f'({strategy.strategy_type}) - '
            f'{status_color(strategy.status.upper())}'
        )
        
        # Basic info
        self.stdout.write(
            f'Profit: {strategy.profit_percentage:.2f}% '
            f'| Complexity: {strategy.complexity_score} '
            f'| Risk: {strategy.risk_score:.1f}%'
        )
        
        # Execution progress
        executions = strategy.executions.all()
        if executions:
            total = executions.count()
            filled = executions.filter(status='filled').count()
            failed = executions.filter(status='failed').count()
            pending = total - filled - failed
            
            self.stdout.write(
                f'Executions: {filled}/{total} filled, '
                f'{pending} pending, {failed} failed'
            )
            
            # Show individual executions
            for execution in executions:
                self.display_execution_detail(execution)
        
        # Timing info
        if strategy.execution_started_at:
            elapsed = (timezone.now() - strategy.execution_started_at).total_seconds()
            self.stdout.write(f'Running for: {elapsed:.1f}s')

    def display_execution_detail(self, execution):
        status_symbol = self.get_execution_symbol(execution.status)
        fill_pct = execution.fill_percentage
        
        self.stdout.write(
            f'  {status_symbol} {execution.exchange.name} '
            f'{execution.action_type} {execution.target_amount} '
            f'@ {execution.target_price} ({fill_pct:.1f}% filled)'
        )

    def get_status_color(self, status):
        colors = {
            'executing': self.style.WARNING,
            'completed': self.style.SUCCESS,
            'failed': self.style.ERROR,
            'detected': self.style.HTTP_INFO,
            'validating': self.style.NOTICE,
        }
        return colors.get(status, self.style.HTTP_NOT_MODIFIED)

    def get_execution_symbol(self, status):
        symbols = {
            'pending': '⏳',
            'order_placed': '📤',
            'partially_filled': '🔄',
            'filled': '✅',
            'failed': '❌',
            'cancelled': '⏹️',
        }
        return symbols.get(status, '❓')