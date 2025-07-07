"""
Enhanced arbitrage detection engine for multi-exchange strategies.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Tuple

from django.core.cache import cache
from django.db import transaction
from django.utils import timezone

from arbitrage.models import (
    ArbitrageOpportunity, 
    MultiExchangeArbitrageStrategy,
    MultiExchangeExecution
)
from core.models import Exchange, ExchangeTradingPair, TradingPair
from exchanges.models import MarketTicker, OrderBook

logger = logging.getLogger(__name__)


class MultiExchangeArbitrageEngine:
    """
    Enhanced engine for detecting and managing multi-exchange arbitrage opportunities.
    """

    def __init__(self):
        self.min_profit_threshold = Decimal("0.5")  # 0.5% minimum profit
        self.opportunity_expiry = 60  # seconds
        self.cache_prefix = "arbitrage"
        self.max_slippage = Decimal("0.5")  # 0.5% max slippage
        self.min_liquidity_ratio = Decimal("10.0")  # 10x order size in liquidity

    async def scan_all_opportunities(
        self, 
        user_config=None,
        enabled_exchanges: Optional[List[Exchange]] = None,
        enabled_pairs: Optional[List[TradingPair]] = None
    ) -> List:
        """
        Scan all trading pairs across all exchanges for arbitrage opportunities.
        Returns both simple and multi-exchange strategies.
        """
        all_strategies = []
        
        # Get active exchanges
        if enabled_exchanges:
            exchanges = enabled_exchanges
        else:
            exchanges = list(Exchange.objects.filter(is_active=True))
        
        # Get active trading pairs
        if enabled_pairs:
            trading_pairs = enabled_pairs
        else:
            trading_pairs = list(TradingPair.objects.filter(is_active=True))
        
        # Process each trading pair
        tasks = []
        for pair in trading_pairs:
            task = self._scan_pair_all_strategies(pair, exchanges, user_config)
            tasks.append(task)
        
        # Run all scans concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Collect valid strategies
        for result in results:
            if isinstance(result, dict):
                if result.get('simple_opportunities'):
                    all_strategies.extend(result['simple_opportunities'])
                if result.get('multi_strategies'):
                    all_strategies.extend(result['multi_strategies'])
            elif isinstance(result, Exception):
                logger.error(f"Error scanning pair: {result}")
        
        return all_strategies

    async def _scan_pair_all_strategies(
        self,
        trading_pair: TradingPair,
        exchanges: List[Exchange],
        user_config=None
    ) -> Dict:
        """
        Scan a specific trading pair for both simple and multi-exchange strategies.
        """
        result = {
            'simple_opportunities': [],
            'multi_strategies': []
        }
        
        # Get latest market data for this pair on all exchanges
        market_data = await self._get_market_data(trading_pair, exchanges)
        
        if len(market_data) < 2:
            return result
        
        # 1. Find simple pairwise opportunities (existing logic)
        simple_opportunities = await self._find_simple_opportunities(
            trading_pair, market_data, user_config
        )
        result['simple_opportunities'] = simple_opportunities
        
        # 2. Find multi-exchange strategies
        if user_config and user_config.enable_multi_exchange and len(market_data) >= 2:
            multi_strategies = await self._find_multi_exchange_strategies(
                trading_pair, market_data, user_config
            )
            result['multi_strategies'] = multi_strategies
        
        return result

    async def _find_simple_opportunities(
        self,
        trading_pair: TradingPair,
        market_data: Dict[Exchange, Dict],
        user_config=None
    ) -> List[ArbitrageOpportunity]:
        """
        Find simple pairwise arbitrage opportunities (existing logic enhanced).
        """
        opportunities = []
        
        for buy_exchange, buy_data in market_data.items():
            for sell_exchange, sell_data in market_data.items():
                if buy_exchange == sell_exchange:
                    continue
                
                opportunity = self._calculate_simple_opportunity(
                    trading_pair,
                    buy_exchange,
                    buy_data,
                    sell_exchange,
                    sell_data,
                    user_config
                )
                
                if opportunity:
                    opportunities.append(opportunity)
        
        return opportunities

    async def _find_multi_exchange_strategies(
        self,
        trading_pair: TradingPair,
        market_data: Dict[Exchange, Dict],
        user_config
    ) -> List[MultiExchangeArbitrageStrategy]:
        """
        Find complex multi-exchange arbitrage strategies.
        """
        strategies = []
        
        # Sort exchanges by price
        sorted_exchanges = self._sort_exchanges_by_price(market_data)
        
        if len(sorted_exchanges) < 2:
            return strategies
        
        # Strategy 1: One-to-Many (buy on cheapest, sell on multiple expensive ones)
        one_to_many = await self._find_one_to_many_strategy(
            trading_pair, sorted_exchanges, user_config
        )
        if one_to_many:
            strategies.append(one_to_many)
        
        # Strategy 2: Many-to-One (buy on multiple cheap, sell on most expensive)
        many_to_one = await self._find_many_to_one_strategy(
            trading_pair, sorted_exchanges, user_config
        )
        if many_to_one:
            strategies.append(many_to_one)
        
        # Strategy 3: Complex multi-exchange (buy and sell on multiple exchanges)
        if len(sorted_exchanges) >= 3:
            complex_strategies = await self._find_complex_strategies(
                trading_pair, sorted_exchanges, user_config
            )
            strategies.extend(complex_strategies)
        
        return strategies

    def _sort_exchanges_by_price(self, market_data: Dict[Exchange, Dict]) -> List[Dict]:
        """
        Sort exchanges by price (cheapest to most expensive).
        """
        exchange_prices = []
        
        for exchange, data in market_data.items():
            ticker = data.get("ticker")
            order_book = data.get("order_book")
            
            if not ticker:
                continue
            
            # Use ask price for buying, bid price for selling
            ask_price = ticker.ask_price or ticker.last_price
            bid_price = ticker.bid_price or ticker.last_price
            
            if not ask_price or not bid_price:
                continue
            
            # Calculate available liquidity
            buy_liquidity = self._calculate_available_liquidity(order_book, "ask", ask_price)
            sell_liquidity = self._calculate_available_liquidity(order_book, "bid", bid_price)
            
            exchange_prices.append({
                'exchange': exchange,
                'ticker': ticker,
                'order_book': order_book,
                'ask_price': ask_price,
                'bid_price': bid_price,
                'buy_liquidity': buy_liquidity,
                'sell_liquidity': sell_liquidity,
                'spread': (bid_price - ask_price) / ask_price * 100 if ask_price > 0 else 0
            })
        
        # Sort by ask price (for buying)
        return sorted(exchange_prices, key=lambda x: x['ask_price'])

    async def _find_one_to_many_strategy(
        self,
        trading_pair: TradingPair,
        sorted_exchanges: List[Dict],
        user_config
    ) -> Optional[MultiExchangeArbitrageStrategy]:
        """
        Find one-to-many strategy: buy on cheapest exchange, sell on multiple expensive ones.
        """
        if len(sorted_exchanges) < 2:
            return None
        
        # Cheapest exchange for buying
        buy_exchange_data = sorted_exchanges[0]
        buy_exchange = buy_exchange_data['exchange']
        buy_price = buy_exchange_data['ask_price']
        max_buy_amount = buy_exchange_data['buy_liquidity']
        
        # Find profitable sell exchanges
        sell_actions = []
        total_sell_amount = Decimal("0")
        min_profit_threshold = user_config.min_profit_per_exchange if user_config else self.min_profit_threshold
        
        for sell_exchange_data in sorted_exchanges[1:]:
            sell_exchange = sell_exchange_data['exchange']
            sell_price = sell_exchange_data['bid_price']
            max_sell_amount = sell_exchange_data['sell_liquidity']
            
            # Calculate profit margin
            gross_profit_percentage = ((sell_price - buy_price) / buy_price) * 100
            
            # Calculate fees
            buy_fee_rate = buy_exchange.taker_fee
            sell_fee_rate = sell_exchange.taker_fee
            total_fee_rate = buy_fee_rate + sell_fee_rate
            net_profit_percentage = gross_profit_percentage - (total_fee_rate * 100)
            
            # Check if profitable
            if net_profit_percentage >= min_profit_threshold:
                # Calculate optimal amount for this exchange
                optimal_amount = min(
                    max_sell_amount,
                    max_buy_amount * Decimal("0.4")  # Max 40% per sell exchange
                )
                
                if user_config and user_config.max_allocation_per_exchange:
                    max_allocation = user_config.max_allocation_per_exchange / 100
                    optimal_amount = min(optimal_amount, max_buy_amount * max_allocation)
                
                if optimal_amount > 0:
                    sell_actions.append({
                        'exchange': sell_exchange.code,
                        'amount': float(optimal_amount),
                        'price': float(sell_price),
                        'profit_percentage': float(net_profit_percentage),
                        'liquidity': float(max_sell_amount)
                    })
                    total_sell_amount += optimal_amount
        
        if not sell_actions or total_sell_amount == 0:
            return None
        
        # Create strategy
        buy_actions = [{
            'exchange': buy_exchange.code,
            'amount': float(total_sell_amount),
            'price': float(buy_price),
            'liquidity': float(max_buy_amount)
        }]
        
        # Calculate total profits
        total_buy_cost = total_sell_amount * buy_price
        total_sell_revenue = sum(
            Decimal(str(action['amount'])) * Decimal(str(action['price'])) 
            for action in sell_actions
        )
        
        # Calculate fees
        buy_fee = total_buy_cost * buy_exchange.taker_fee
        sell_fees = sum(
            Decimal(str(action['amount'])) * Decimal(str(action['price'])) * 
            Exchange.objects.get(code=action['exchange']).taker_fee
            for action in sell_actions
        )
        total_fees = buy_fee + sell_fees
        
        estimated_profit = total_sell_revenue - total_buy_cost - total_fees
        profit_percentage = (estimated_profit / total_buy_cost) * 100 if total_buy_cost > 0 else 0
        
        # Check overall profitability
        if profit_percentage < min_profit_threshold:
            return None
        
        strategy = MultiExchangeArbitrageStrategy(
            trading_pair=trading_pair,
            strategy_type="one_to_many",
            buy_actions=buy_actions,
            sell_actions=sell_actions,
            total_buy_amount=total_sell_amount,
            total_sell_amount=total_sell_amount,
            total_buy_cost=total_buy_cost,
            total_sell_revenue=total_sell_revenue,
            estimated_profit=estimated_profit,
            profit_percentage=profit_percentage,
            total_fees=total_fees,
            complexity_score=len(sell_actions) + 1,
            expires_at=timezone.now() + timedelta(seconds=self.opportunity_expiry),
            market_snapshot={
                'exchanges': [ex['exchange'].code for ex in sorted_exchanges],
                'prices': {ex['exchange'].code: float(ex['ask_price']) for ex in sorted_exchanges}
            }
        )
        
        return strategy

    async def _find_many_to_one_strategy(
        self,
        trading_pair: TradingPair,
        sorted_exchanges: List[Dict],
        user_config
    ) -> Optional[MultiExchangeArbitrageStrategy]:
        """
        Find many-to-one strategy: buy on multiple cheap exchanges, sell on most expensive.
        """
        if len(sorted_exchanges) < 2:
            return None
        
        # Most expensive exchange for selling
        sell_exchange_data = sorted_exchanges[-1]
        sell_exchange = sell_exchange_data['exchange']
        sell_price = sell_exchange_data['bid_price']
        max_sell_amount = sell_exchange_data['sell_liquidity']
        
        # Find profitable buy exchanges
        buy_actions = []
        total_buy_amount = Decimal("0")
        min_profit_threshold = user_config.min_profit_per_exchange if user_config else self.min_profit_threshold
        
        for buy_exchange_data in sorted_exchanges[:-1]:
            buy_exchange = buy_exchange_data['exchange']
            buy_price = buy_exchange_data['ask_price']
            max_buy_amount = buy_exchange_data['buy_liquidity']
            
            # Calculate profit margin
            gross_profit_percentage = ((sell_price - buy_price) / buy_price) * 100
            
            # Calculate fees
            buy_fee_rate = buy_exchange.taker_fee
            sell_fee_rate = sell_exchange.taker_fee
            total_fee_rate = buy_fee_rate + sell_fee_rate
            net_profit_percentage = gross_profit_percentage - (total_fee_rate * 100)
            
            # Check if profitable
            if net_profit_percentage >= min_profit_threshold:
                # Calculate optimal amount for this exchange
                optimal_amount = min(
                    max_buy_amount,
                    max_sell_amount * Decimal("0.4")  # Max 40% per buy exchange
                )
                
                if user_config and user_config.max_allocation_per_exchange:
                    max_allocation = user_config.max_allocation_per_exchange / 100
                    optimal_amount = min(optimal_amount, max_sell_amount * max_allocation)
                
                if optimal_amount > 0:
                    buy_actions.append({
                        'exchange': buy_exchange.code,
                        'amount': float(optimal_amount),
                        'price': float(buy_price),
                        'profit_percentage': float(net_profit_percentage),
                        'liquidity': float(max_buy_amount)
                    })
                    total_buy_amount += optimal_amount
        
        if not buy_actions or total_buy_amount == 0:
            return None
        
        # Adjust sell amount to match total buy amount
        sell_amount = min(total_buy_amount, max_sell_amount)
        
        sell_actions = [{
            'exchange': sell_exchange.code,
            'amount': float(sell_amount),
            'price': float(sell_price),
            'liquidity': float(max_sell_amount)
        }]
        
        # Calculate total profits
        total_buy_cost = sum(
            Decimal(str(action['amount'])) * Decimal(str(action['price'])) 
            for action in buy_actions
        )
        total_sell_revenue = sell_amount * sell_price
        
        # Calculate fees
        buy_fees = sum(
            Decimal(str(action['amount'])) * Decimal(str(action['price'])) * 
            Exchange.objects.get(code=action['exchange']).taker_fee
            for action in buy_actions
        )
        sell_fee = total_sell_revenue * sell_exchange.taker_fee
        total_fees = buy_fees + sell_fee
        
        estimated_profit = total_sell_revenue - total_buy_cost - total_fees
        profit_percentage = (estimated_profit / total_buy_cost) * 100 if total_buy_cost > 0 else 0
        
        # Check overall profitability
        if profit_percentage < min_profit_threshold:
            return None
        
        strategy = MultiExchangeArbitrageStrategy(
            trading_pair=trading_pair,
            strategy_type="many_to_one",
            buy_actions=buy_actions,
            sell_actions=sell_actions,
            total_buy_amount=total_buy_amount,
            total_sell_amount=sell_amount,
            total_buy_cost=total_buy_cost,
            total_sell_revenue=total_sell_revenue,
            estimated_profit=estimated_profit,
            profit_percentage=profit_percentage,
            total_fees=total_fees,
            complexity_score=len(buy_actions) + 1,
            expires_at=timezone.now() + timedelta(seconds=self.opportunity_expiry),
            market_snapshot={
                'exchanges': [ex['exchange'].code for ex in sorted_exchanges],
                'prices': {ex['exchange'].code: float(ex['ask_price']) for ex in sorted_exchanges}
            }
        )
        
        return strategy

    async def _find_complex_strategies(
        self,
        trading_pair: TradingPair,
        sorted_exchanges: List[Dict],
        user_config
    ) -> List[MultiExchangeArbitrageStrategy]:
        """
        Find complex strategies involving multiple buy and sell exchanges.
        """
        strategies = []
        
        if len(sorted_exchanges) < 3:
            return strategies
        
        # Strategy: Buy on cheapest 40%, sell on most expensive 40%
        num_exchanges = len(sorted_exchanges)
        buy_count = max(1, num_exchanges // 3)  # Use bottom 1/3 for buying
        sell_count = max(1, num_exchanges // 3)  # Use top 1/3 for selling
        
        buy_exchanges = sorted_exchanges[:buy_count]
        sell_exchanges = sorted_exchanges[-sell_count:]
        
        # Calculate total available liquidity
        total_buy_liquidity = sum(ex['buy_liquidity'] for ex in buy_exchanges)
        total_sell_liquidity = sum(ex['sell_liquidity'] for ex in sell_exchanges)
        
        if total_buy_liquidity == 0 or total_sell_liquidity == 0:
            return strategies
        
        # Determine optimal allocation
        max_amount = min(total_buy_liquidity, total_sell_liquidity) * Decimal("0.8")  # Conservative
        
        # Allocate buy amounts (weighted by liquidity and price advantage)
        buy_actions = []
        total_buy_weight = sum(
            ex['buy_liquidity'] / ex['ask_price'] for ex in buy_exchanges
        )
        
        for ex in buy_exchanges:
            weight = (ex['buy_liquidity'] / ex['ask_price']) / total_buy_weight
            amount = max_amount * Decimal(str(weight))
            
            if amount > 0:
                buy_actions.append({
                    'exchange': ex['exchange'].code,
                    'amount': float(amount),
                    'price': float(ex['ask_price']),
                    'liquidity': float(ex['buy_liquidity'])
                })
        
        # Allocate sell amounts (weighted by liquidity and price advantage)
        sell_actions = []
        total_sell_weight = sum(
            ex['sell_liquidity'] * ex['bid_price'] for ex in sell_exchanges
        )
        
        for ex in sell_exchanges:
            weight = (ex['sell_liquidity'] * ex['bid_price']) / total_sell_weight
            amount = max_amount * Decimal(str(weight))
            
            if amount > 0:
                sell_actions.append({
                    'exchange': ex['exchange'].code,
                    'amount': float(amount),
                    'price': float(ex['bid_price']),
                    'liquidity': float(ex['sell_liquidity'])
                })
        
        if not buy_actions or not sell_actions:
            return strategies
        
        # Calculate profitability
        total_buy_cost = sum(
            Decimal(str(action['amount'])) * Decimal(str(action['price'])) 
            for action in buy_actions
        )
        total_sell_revenue = sum(
            Decimal(str(action['amount'])) * Decimal(str(action['price'])) 
            for action in sell_actions
        )
        
        # Calculate fees
        buy_fees = sum(
            Decimal(str(action['amount'])) * Decimal(str(action['price'])) * 
            Exchange.objects.get(code=action['exchange']).taker_fee
            for action in buy_actions
        )
        sell_fees = sum(
            Decimal(str(action['amount'])) * Decimal(str(action['price'])) * 
            Exchange.objects.get(code=action['exchange']).taker_fee
            for action in sell_actions
        )
        total_fees = buy_fees + sell_fees
        
        estimated_profit = total_sell_revenue - total_buy_cost - total_fees
        profit_percentage = (estimated_profit / total_buy_cost) * 100 if total_buy_cost > 0 else 0
        
        min_profit_threshold = user_config.min_profit_percentage if user_config else self.min_profit_threshold
        
        if profit_percentage >= min_profit_threshold:
            strategy = MultiExchangeArbitrageStrategy(
                trading_pair=trading_pair,
                strategy_type="complex",
                buy_actions=buy_actions,
                sell_actions=sell_actions,
                total_buy_amount=sum(Decimal(str(a['amount'])) for a in buy_actions),
                total_sell_amount=sum(Decimal(str(a['amount'])) for a in sell_actions),
                total_buy_cost=total_buy_cost,
                total_sell_revenue=total_sell_revenue,
                estimated_profit=estimated_profit,
                profit_percentage=profit_percentage,
                total_fees=total_fees,
                complexity_score=len(buy_actions) + len(sell_actions),
                expires_at=timezone.now() + timedelta(seconds=self.opportunity_expiry),
                market_snapshot={
                    'exchanges': [ex['exchange'].code for ex in sorted_exchanges],
                    'prices': {ex['exchange'].code: float(ex['ask_price']) for ex in sorted_exchanges}
                }
            )
            strategies.append(strategy)
        
        return strategies

    def _calculate_available_liquidity(
        self,
        order_book: Optional[OrderBook],
        side: str,
        target_price: Decimal,
        depth_limit: int = 10
    ) -> Decimal:
        """
        Calculate available liquidity up to target price.
        """
        if not order_book:
            return Decimal("0")
        
        total_amount = Decimal("0")
        
        entries = order_book.entries.filter(side=side).order_by(
            "price" if side == "ask" else "-price"
        )[:depth_limit]
        
        for entry in entries:
            if side == "ask" and entry.price > target_price * Decimal("1.01"):  # 1% slippage tolerance
                break
            elif side == "bid" and entry.price < target_price * Decimal("0.99"):  # 1% slippage tolerance
                break
            
            total_amount += entry.amount
        
        return total_amount

    def _calculate_simple_opportunity(
        self,
        trading_pair: TradingPair,
        buy_exchange: Exchange,
        buy_data: Dict,
        sell_exchange: Exchange,
        sell_data: Dict,
        user_config=None
    ) -> Optional[ArbitrageOpportunity]:
        """
        Calculate simple pairwise arbitrage opportunity (existing logic).
        """
        try:
            buy_ticker = buy_data["ticker"]
            sell_ticker = sell_data["ticker"]
            
            # Use ask price for buying and bid price for selling
            buy_price = buy_ticker.ask_price
            sell_price = sell_ticker.bid_price
            
            if not buy_price or not sell_price or buy_price >= sell_price:
                return None
            
            # Calculate gross profit percentage
            gross_profit_percentage = ((sell_price - buy_price) / buy_price) * 100
            
            # Calculate fees
            buy_fee_rate = buy_exchange.taker_fee
            sell_fee_rate = sell_exchange.taker_fee
            total_fee_rate = buy_fee_rate + sell_fee_rate
            
            # Calculate net profit percentage
            net_profit_percentage = gross_profit_percentage - (total_fee_rate * 100)
            
            # Check minimum profit threshold
            min_threshold = self.min_profit_threshold
            if user_config and hasattr(user_config, 'min_profit_percentage'):
                min_threshold = user_config.min_profit_percentage
            
            if net_profit_percentage < min_threshold:
                return None
            
            # Calculate available amounts from order book
            buy_amount = self._calculate_available_liquidity(
                buy_data.get("order_book"), "ask", buy_price
            )
            sell_amount = self._calculate_available_liquidity(
                sell_data.get("order_book"), "bid", sell_price
            )
            
            if not buy_amount or not sell_amount:
                return None
            
            # Calculate optimal amount
            optimal_amount = min(buy_amount, sell_amount)
            
            # Apply user limits if configured
            if user_config and hasattr(user_config, 'max_trade_amount'):
                max_amount = user_config.max_trade_amount.get(
                    trading_pair.base_currency.symbol, Decimal("999999")
                )
                optimal_amount = min(optimal_amount, max_amount)
            
            # Create opportunity record
            opportunity = ArbitrageOpportunity(
                trading_pair=trading_pair,
                buy_exchange=buy_exchange,
                sell_exchange=sell_exchange,
                buy_price=buy_price,
                sell_price=sell_price,
                available_buy_amount=buy_amount,
                available_sell_amount=sell_amount,
                optimal_amount=optimal_amount,
                gross_profit_percentage=gross_profit_percentage,
                net_profit_percentage=net_profit_percentage,
                expires_at=timezone.now() + timedelta(seconds=self.opportunity_expiry),
                detection_latency=0.0,  # Would be calculated in real implementation
                market_depth={
                    "buy_exchange": {
                        "asks": self._format_order_book_side(
                            buy_data.get("order_book"), "ask"
                        ) if buy_data.get("order_book") else []
                    },
                    "sell_exchange": {
                        "bids": self._format_order_book_side(
                            sell_data.get("order_book"), "bid"
                        ) if sell_data.get("order_book") else []
                    }
                }
            )
            
            # Calculate fees and profit
            opportunity.calculate_fees()
            opportunity.calculate_profit()
            
            return opportunity
            
        except Exception as e:
            logger.error(f"Error calculating opportunity: {e}")
            return None

    async def _get_market_data(
        self,
        trading_pair: TradingPair,
        exchanges: List[Exchange]
    ) -> Dict[Exchange, Dict]:
        """
        Get latest market data for a trading pair across exchanges.
        """
        market_data = {}
        
        # Get exchange trading pairs
        exchange_pairs = ExchangeTradingPair.objects.filter(
            trading_pair=trading_pair,
            exchange__in=exchanges,
            is_active=True
        ).select_related("exchange")
        
        for exchange_pair in exchange_pairs:
            # Try to get cached data first
            cache_key = f"{self.cache_prefix}:market:{exchange_pair.id}"
            cached_data = cache.get(cache_key)
            
            if cached_data:
                market_data[exchange_pair.exchange] = cached_data
                continue
            
            # Get latest ticker
            try:
                ticker = MarketTicker.objects.filter(
                    exchange_pair=exchange_pair
                ).order_by("-timestamp").first()
                
                if ticker and ticker.timestamp > timezone.now() - timedelta(seconds=30):
                    # Get order book depth
                    order_book = OrderBook.objects.filter(
                        exchange_pair=exchange_pair
                    ).order_by("-timestamp").first()
                    
                    data = {
                        "ticker": ticker,
                        "order_book": order_book,
                        "exchange_pair": exchange_pair,
                    }
                    
                    # Cache for 5 seconds
                    cache.set(cache_key, data, 5)
                    market_data[exchange_pair.exchange] = data
                    
            except Exception as e:
                logger.error(f"Error getting market data for {exchange_pair}: {e}")
        
        return market_data

    def _format_order_book_side(
        self,
        order_book: Optional[OrderBook],
        side: str,
        limit: int = 10
    ) -> List[Dict]:
        """
        Format order book side for storage.
        """
        if not order_book:
            return []
        
        entries = order_book.entries.filter(side=side).order_by(
            "price" if side == "ask" else "-price"
        )[:limit]
        
        return [
            {
                "price": str(entry.price),
                "amount": str(entry.amount),
                "total": str(entry.total),
            }
            for entry in entries
        ]

    async def validate_strategy(
        self,
        strategy: MultiExchangeArbitrageStrategy
    ) -> Tuple[bool, str]:
        """
        Validate if a multi-exchange strategy is still valid for execution.
        """
        # Check if expired
        if strategy.expires_at < timezone.now():
            return False, "Strategy has expired"
        
        # Check if already executed
        if strategy.status != "detected":
            return False, f"Strategy is already {strategy.status}"
        
        # Get fresh market data for all involved exchanges
        involved_exchanges = []
        for action in strategy.buy_actions + strategy.sell_actions:
            exchange = Exchange.objects.filter(code=action['exchange']).first()
            if exchange:
                involved_exchanges.append(exchange)
        
        market_data = await self._get_market_data(
            strategy.trading_pair,
            involved_exchanges
        )
        
        # Validate each exchange action
        for action in strategy.buy_actions:
            exchange = Exchange.objects.get(code=action['exchange'])
            if exchange not in market_data:
                return False, f"Cannot get market data for {exchange.name}"
            
            ticker = market_data[exchange]["ticker"]
            if ticker.ask_price > Decimal(str(action['price'])) * Decimal("1.02"):  # 2% tolerance
                return False, f"Buy price on {exchange.name} has increased too much"
        
        for action in strategy.sell_actions:
            exchange = Exchange.objects.get(code=action['exchange'])
            if exchange not in market_data:
                return False, f"Cannot get market data for {exchange.name}"
            
            ticker = market_data[exchange]["ticker"]
            if ticker.bid_price < Decimal(str(action['price'])) * Decimal("0.98"):  # 2% tolerance
                return False, f"Sell price on {exchange.name} has decreased too much"
        
        return True, "Valid"

    async def mark_expired_opportunities(self):
        """
        Mark expired opportunities and strategies.
        """
        # Mark expired simple opportunities
        expired_count = ArbitrageOpportunity.objects.filter(
            status="detected",
            expires_at__lt=timezone.now()
        ).update(status="expired")
        
        # Mark expired multi-exchange strategies
        expired_strategies = MultiExchangeArbitrageStrategy.objects.filter(
            status="detected",
            expires_at__lt=timezone.now()
        ).update(status="expired")
        
        if expired_count > 0 or expired_strategies > 0:
            logger.info(f"Marked {expired_count} opportunities and {expired_strategies} strategies as expired")


# Legacy class for backward compatibility
class ArbitrageEngine(MultiExchangeArbitrageEngine):
    """
    Legacy arbitrage engine class for backward compatibility.
    """
    pass