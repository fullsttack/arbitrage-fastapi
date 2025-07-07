from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from arbitrage.models import ArbitrageConfig, MultiExchangeArbitrageStrategy, ArbitrageExecution
from django.db import models
from decimal import Decimal
from datetime import timedelta
from django.utils import timezone


class Command(BaseCommand):
    help = 'Optimize arbitrage configuration based on historical performance'

    def add_arguments(self, parser):
        parser.add_argument(
            '--user',
            help='Username to optimize config for'
        )
        parser.add_argument(
            '--days',
            type=int,
            default=30,
            help='Days of historical data to analyze'
        )
        parser.add_argument(
            '--apply',
            action='store_true',
            help='Apply the optimized configuration'
        )

    def handle(self, *args, **options):
        username = options.get('user')
        days = options['days']
        apply_changes = options['apply']
        
        if username:
            try:
                user = User.objects.get(username=username)
                users = [user]
            except User.DoesNotExist:
                self.stdout.write(self.style.ERROR(f'User {username} not found'))
                return
        else:
            users = User.objects.filter(arbitrage_config__isnull=False)
        
        self.stdout.write(f'Analyzing {days} days of data for {len(users)} users...')
        
        for user in users:
            self.optimize_user_config(user, days, apply_changes)

    def optimize_user_config(self, user, days, apply_changes):
        try:
            config = user.arbitrage_config
        except ArbitrageConfig.DoesNotExist:
            self.stdout.write(f'No config found for user {user.username}')
            return
        
        self.stdout.write(f'\nOptimizing config for {user.username}...')
        
        # Analyze historical performance
        start_date = timezone.now() - timedelta(days=days)
        
        # Simple arbitrage performance
        simple_executions = ArbitrageExecution.objects.filter(
            user=user,
            created_at__gte=start_date,
            status='completed'
        )
        
        # Multi-exchange performance  
        multi_strategies = MultiExchangeArbitrageStrategy.objects.filter(
            executions__strategy__user=user,
            created_at__gte=start_date,
            status='completed'
        ).distinct()
        
        # Calculate optimization recommendations
        recommendations = self.calculate_recommendations(
            config, simple_executions, multi_strategies
        )
        
        # Display recommendations
        self.display_recommendations(user.username, recommendations)
        
        # Apply if requested
        if apply_changes:
            self.apply_recommendations(config, recommendations)
            self.stdout.write(
                self.style.SUCCESS(f'Applied optimizations for {user.username}')
            )

    def calculate_recommendations(self, config, simple_executions, multi_strategies):
        recommendations = {}
        
        # Analyze profit thresholds
        if simple_executions.exists():
            profitable_simple = simple_executions.filter(final_profit__gt=0)
            if profitable_simple.exists():
                avg_profit_pct = profitable_simple.aggregate(
                    avg=models.Avg('profit_percentage')
                )['avg']
                
                # Recommend slightly lower threshold to catch more opportunities
                optimal_threshold = max(0.1, avg_profit_pct * 0.8)
                recommendations['min_profit_percentage'] = optimal_threshold
        
        # Analyze multi-exchange vs simple performance
        simple_profit = simple_executions.aggregate(
            total=models.Sum('final_profit')
        )['total'] or Decimal('0')
        
        multi_profit = multi_strategies.aggregate(
            total=models.Sum('actual_profit')
        )['total'] or Decimal('0')
        
        total_profit = simple_profit + multi_profit
        
        if total_profit > 0:
            multi_ratio = multi_profit / total_profit
            # If multi-exchange is more profitable, recommend enabling it
            if multi_ratio > 0.6 and not config.enable_multi_exchange:
                recommendations['enable_multi_exchange'] = True
            elif multi_ratio < 0.2 and config.enable_multi_exchange:
                recommendations['enable_multi_exchange'] = False
        
        # Analyze execution time performance
        successful_multi = multi_strategies.filter(
            execution_completed_at__isnull=False,
            execution_started_at__isnull=False
        )
        
        if successful_multi.exists():
            avg_execution_time = 0
            for strategy in successful_multi:
                duration = (strategy.execution_completed_at - strategy.execution_started_at).total_seconds()
                avg_execution_time += duration
            
            avg_execution_time /= successful_multi.count()
            
            # Recommend timeout slightly above average
            optimal_timeout = min(300, max(30, avg_execution_time * 1.5))
            recommendations['max_execution_time'] = int(optimal_timeout)
        
        return recommendations

    def display_recommendations(self, username, recommendations):
        if not recommendations:
            self.stdout.write(f'No optimization recommendations for {username}')
            return
        
        self.stdout.write(f'Recommendations for {username}:')
        for key, value in recommendations.items():
            self.stdout.write(f'  {key}: {value}')

    def apply_recommendations(self, config, recommendations):
        for key, value in recommendations.items():
            if hasattr(config, key):
                setattr(config, key, value)
        config.save()
