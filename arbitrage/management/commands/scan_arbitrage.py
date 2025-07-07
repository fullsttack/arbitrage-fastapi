from django.core.management.base import BaseCommand
from django.utils import timezone
import asyncio
from arbitrage.engine import MultiExchangeArbitrageEngine
from arbitrage.models import ArbitrageConfig
from core.models import Exchange, TradingPair


class Command(BaseCommand):
    help = 'Manually scan for arbitrage opportunities'

    def add_arguments(self, parser):
        parser.add_argument(
            '--exchanges',
            nargs='+',
            help='Limit to specific exchanges (e.g., nobitex wallex)'
        )
        parser.add_argument(
            '--pairs',
            nargs='+',
            help='Limit to specific trading pairs (e.g., BTCUSDT ETHUSDT)'
        )
        parser.add_argument(
            '--min-profit',
            type=float,
            default=0.5,
            help='Minimum profit percentage'
        )
        parser.add_argument(
            '--multi-only',
            action='store_true',
            help='Only scan for multi-exchange strategies'
        )
        parser.add_argument(
            '--simple-only',
            action='store_true',
            help='Only scan for simple opportunities'
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Starting arbitrage scan...'))
        
        # Get filters
        exchanges = None
        if options['exchanges']:
            exchanges = list(Exchange.objects.filter(
                code__in=options['exchanges'],
                is_active=True
            ))
            if not exchanges:
                self.stdout.write(self.style.ERROR('No valid exchanges found'))
                return
        
        pairs = None
        if options['pairs']:
            pairs = list(TradingPair.objects.filter(
                symbol__in=options['pairs'],
                is_active=True
            ))
            if not pairs:
                self.stdout.write(self.style.ERROR('No valid trading pairs found'))
                return
        
        # Create mock user config
        class MockConfig:
            min_profit_percentage = options['min_profit']
            enable_multi_exchange = not options['simple_only']
            enabled_exchanges = exchanges or Exchange.objects.filter(is_active=True)
            enabled_pairs = pairs or TradingPair.objects.filter(is_active=True)
        
        # Run scan
        engine = MultiExchangeArbitrageEngine()
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            start_time = timezone.now()
            
            strategies = loop.run_until_complete(
                engine.scan_all_opportunities(
                    user_config=MockConfig(),
                    enabled_exchanges=exchanges,
                    enabled_pairs=pairs
                )
            )
            
            duration = (timezone.now() - start_time).total_seconds()
            
            # Separate results
            simple_opportunities = [s for s in strategies if hasattr(s, 'buy_exchange')]
            multi_strategies = [s for s in strategies if hasattr(s, 'strategy_type')]
            
            # Display results
            self.stdout.write(f'\nScan completed in {duration:.2f} seconds')
            self.stdout.write(f'Found {len(simple_opportunities)} simple opportunities')
            self.stdout.write(f'Found {len(multi_strategies)} multi-exchange strategies')
            
            if simple_opportunities and not options['multi_only']:
                self.stdout.write('\n' + '='*50)
                self.stdout.write('SIMPLE ARBITRAGE OPPORTUNITIES')
                self.stdout.write('='*50)
                
                for opp in sorted(simple_opportunities, key=lambda x: x.net_profit_percentage, reverse=True)[:10]:
                    self.stdout.write(
                        f'{opp.trading_pair.symbol}: '
                        f'{opp.buy_exchange.name} → {opp.sell_exchange.name} '
                        f'({opp.net_profit_percentage:.2f}% profit, '
                        f'{opp.optimal_amount} amount)'
                    )
            
            if multi_strategies and not options['simple_only']:
                self.stdout.write('\n' + '='*50)
                self.stdout.write('MULTI-EXCHANGE STRATEGIES')
                self.stdout.write('='*50)
                
                for strategy in sorted(multi_strategies, key=lambda x: x.profit_percentage, reverse=True)[:10]:
                    exchanges_involved = len(set([a['exchange'] for a in strategy.buy_actions + strategy.sell_actions]))
                    self.stdout.write(
                        f'{strategy.trading_pair.symbol} ({strategy.strategy_type}): '
                        f'{strategy.profit_percentage:.2f}% profit, '
                        f'{exchanges_involved} exchanges, '
                        f'complexity: {strategy.complexity_score}'
                    )
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error during scan: {e}'))
        finally:
            loop.close()