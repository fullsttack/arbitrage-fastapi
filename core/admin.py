from django.contrib import admin
from core.models import Currency, TradingPair, Exchange, ExchangeTradingPair, APICredential

@admin.register(Currency)
class CurrencyAdmin(admin.ModelAdmin):
    list_display = ['symbol', 'name', 'is_crypto', 'is_active']
    list_filter = ['is_crypto', 'is_active']
    search_fields = ['symbol', 'name']

@admin.register(TradingPair)
class TradingPairAdmin(admin.ModelAdmin):
    list_display = ['symbol', 'base_currency', 'quote_currency', 'is_active']
    list_filter = ['is_active']
    search_fields = ['symbol']

@admin.register(Exchange)
class ExchangeAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'is_active', 'rate_limit']
    list_filter = ['is_active']

@admin.register(ExchangeTradingPair)
class ExchangeTradingPairAdmin(admin.ModelAdmin):
    list_display = ['exchange', 'trading_pair', 'exchange_symbol', 'is_active']
    list_filter = ['exchange', 'is_active']
    search_fields = ['trading_pair__symbol', 'exchange_symbol']

@admin.register(APICredential)
class APICredentialAdmin(admin.ModelAdmin):
    list_display = ['user', 'exchange', 'is_active', 'last_used']
    list_filter = ['exchange', 'is_active']
    search_fields = ['user__username']