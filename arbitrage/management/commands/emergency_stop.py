from django.core.management.base import BaseCommand
from arbitrage.models import MultiExchangeArbitrageStrategy, MultiExchangeExecution
from arbitrage.tasks import cancel_single_execution


class Command(BaseCommand):
    help = 'Emergency stop all active arbitrage strategies'

    def add_arguments(self, parser):
        parser.add_argument(
            '--strategy-id',
            help='Stop specific strategy ID only'
        )
        parser.add_argument(
            '--confirm',
            action='store_true',
            help='Confirm the emergency stop'
        )

    def handle(self, *args, **options):
        if not options['confirm']:
            self.stdout.write(
                self.style.WARNING(
                    'This will stop all active strategies and cancel pending orders.\n'
                    'Add --confirm to proceed.'
                )
            )
            return
        
        strategy_id = options.get('strategy_id')
        
        if strategy_id:
            strategies = MultiExchangeArbitrageStrategy.objects.filter(
                id=strategy_id,
                status__in=['executing', 'validating']
            )
        else:
            strategies = MultiExchangeArbitrageStrategy.objects.filter(
                status__in=['executing', 'validating']
            )
        
        if not strategies:
            self.stdout.write('No active strategies to stop.')
            return
        
        stopped_count = 0
        cancelled_orders = 0
        
        for strategy in strategies:
            self.stdout.write(f'Stopping strategy {strategy.id}...')
            
            # Cancel all pending executions
            for execution in strategy.executions.filter(
                status__in=['pending', 'order_placed', 'partially_filled']
            ):
                cancel_single_execution.delay(execution.id)
                cancelled_orders += 1
            
            # Mark strategy as cancelled
            strategy.status = 'cancelled'
            strategy.save()
            stopped_count += 1
        
        self.stdout.write(
            self.style.SUCCESS(
                f'Emergency stop completed. '
                f'Stopped {stopped_count} strategies, '
                f'cancelled {cancelled_orders} orders.'
            )
        )