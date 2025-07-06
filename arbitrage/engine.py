"""
Arbitrage detection engine for identifying profitable opportunities.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Tuple

from django.core.cache import cache
from django.db import transaction
from django.utils import timezone

from arbitrage.models import ArbitrageOpportunity
from core.models import Exchange, ExchangeTradingPair, TradingPair
from exchanges.models import MarketTicker, OrderBook

logger = logging.getLogger(__name__)


class ArbitrageEngine:
    """
    Engine for detecting arbitrage opportunities across exchanges.
    """

    def __init__(self):
        self.min_profit_threshold = Decimal("0.5")  # 0.5% minimum profit
        self.opportunity_expiry = 60  # seconds
        self.cache_prefix = "arbitrage"

    async def scan_all_opportunities(
        self, 
        user_config=None,
        enabled_exchanges: Optional[List[Exchange]] = None,
        enabled_pairs: Optional[List[TradingPair]] = None
    ) -> List[ArbitrageOpportunity]:
        """
        Scan all trading pairs across all exchanges for arbitrage opportunities.
        """
        opportunities = []
        
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
            task = self._scan_pair_opportunities(pair, exchanges, user_config)
            tasks.append(task)
        
        # Run all scans concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Collect valid opportunities
        for result in results:
            if isinstance(result, list):
                opportunities.extend(result)
            elif isinstance(result, Exception):
                logger.error(f"Error scanning pair: {result}")
        
        return opportunities

    async def _scan_pair_opportunities(
        self,
        trading_pair: TradingPair,
        exchanges: List[Exchange],
        user_config=None
    ) -> List[ArbitrageOpportunity]:
        """
        Scan a specific trading pair across exchanges for opportunities.
        """
        opportunities = []
        
        # Get latest market data for this pair on all exchanges
        market_data = await self._get_market_data(trading_pair, exchanges)
        
        if len(market_data) < 2:
            return opportunities
        
        # Find arbitrage opportunities
        for buy_exchange, buy_data in market_data.items():
            for sell_exchange, sell_data in market_data.items():
                if buy_exchange == sell_exchange:
                    continue
                
                opportunity = self._calculate_opportunity(
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

    def _calculate_opportunity(
        self,
        trading_pair: TradingPair,
        buy_exchange: Exchange,
        buy_data: Dict,
        sell_exchange: Exchange,
        sell_data: Dict,
        user_config=None
    ) -> Optional[ArbitrageOpportunity]:
        """
        Calculate if there's a profitable arbitrage opportunity.
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
            buy_amount = self._get_available_amount(
                buy_data.get("order_book"), "ask", buy_price
            )
            sell_amount = self._get_available_amount(
                sell_data.get("order_book"), "bid", sell_price
            )
            
            if not buy_amount or not sell_amount:
                return None
            
            # Calculate optimal amount
            optimal_amount = min(buy_amount, sell_amount)
            
            # Apply user limits if configured
            if user_config:
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

    def _get_available_amount(
        self,
        order_book: Optional[OrderBook],
        side: str,
        target_price: Decimal
    ) -> Optional[Decimal]:
        """
        Get available amount at or better than target price from order book.
        """
        if not order_book:
            return None
        
        total_amount = Decimal("0")
        
        entries = order_book.entries.filter(side=side).order_by(
            "price" if side == "ask" else "-price"
        )
        
        for entry in entries:
            if side == "ask" and entry.price > target_price:
                break
            elif side == "bid" and entry.price < target_price:
                break
            
            total_amount += entry.amount
        
        return total_amount if total_amount > 0 else None

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

    async def validate_opportunity(
        self,
        opportunity: ArbitrageOpportunity
    ) -> Tuple[bool, str]:
        """
        Validate if an opportunity is still valid for execution.
        """
        # Check if expired
        if opportunity.expires_at < timezone.now():
            return False, "Opportunity has expired"
        
        # Check if already executed
        if opportunity.status != "detected":
            return False, f"Opportunity is already {opportunity.status}"
        
        # Get fresh market data
        market_data = await self._get_market_data(
            opportunity.trading_pair,
            [opportunity.buy_exchange, opportunity.sell_exchange]
        )
        
        # Validate buy side
        buy_data = market_data.get(opportunity.buy_exchange)
        if not buy_data:
            return False, "Cannot get buy exchange market data"
        
        buy_ticker = buy_data["ticker"]
        if buy_ticker.ask_price > opportunity.buy_price * Decimal("1.01"):
            return False, "Buy price has increased too much"
        
        # Validate sell side
        sell_data = market_data.get(opportunity.sell_exchange)
        if not sell_data:
            return False, "Cannot get sell exchange market data"
        
        sell_ticker = sell_data["ticker"]
        if sell_ticker.bid_price < opportunity.sell_price * Decimal("0.99"):
            return False, "Sell price has decreased too much"
        
        # Recalculate profit
        current_buy_price = buy_ticker.ask_price
        current_sell_price = sell_ticker.bid_price
        
        if current_buy_price >= current_sell_price:
            return False, "No longer profitable"
        
        gross_profit = ((current_sell_price - current_buy_price) / current_buy_price) * 100
        net_profit = gross_profit - (
            (opportunity.buy_exchange.taker_fee + opportunity.sell_exchange.taker_fee) * 100
        )
        
        if net_profit < opportunity.net_profit_percentage * Decimal("0.8"):
            return False, "Profit has decreased significantly"
        
        return True, "Valid"

    async def mark_expired_opportunities(self):
        """
        Mark expired opportunities.
        """
        expired_count = ArbitrageOpportunity.objects.filter(
            status="detected",
            expires_at__lt=timezone.now()
        ).update(status="expired")
        
        if expired_count > 0:
            logger.info(f"Marked {expired_count} opportunities as expired")

    def get_active_opportunities(
        self,
        user_config=None,
        limit: int = 100
    ) -> List[ArbitrageOpportunity]:
        """
        Get active arbitrage opportunities sorted by profit.
        """
        queryset = ArbitrageOpportunity.objects.filter(
            status="detected",
            expires_at__gt=timezone.now()
        ).select_related(
            "trading_pair",
            "buy_exchange",
            "sell_exchange"
        ).order_by("-net_profit_percentage")
        
        if user_config:
            # Apply user filters
            if user_config.enabled_exchanges.exists():
                queryset = queryset.filter(
                    buy_exchange__in=user_config.enabled_exchanges.all(),
                    sell_exchange__in=user_config.enabled_exchanges.all()
                )
            
            if user_config.enabled_pairs.exists():
                queryset = queryset.filter(
                    trading_pair__in=user_config.enabled_pairs.all()
                )
            
            # Apply profit threshold
            queryset = queryset.filter(
                net_profit_percentage__gte=user_config.min_profit_percentage
            )
        
        return list(queryset[:limit])