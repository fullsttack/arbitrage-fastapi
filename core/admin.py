from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin, GroupAdmin as BaseGroupAdmin
from django.contrib.auth.models import User, Group
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe

from unfold.admin import ModelAdmin, TabularInline, StackedInline
from unfold.forms import AdminPasswordChangeForm, UserChangeForm, UserCreationForm
from unfold.decorators import display

from core.models import Currency, TradingPair, Exchange, ExchangeTradingPair, APICredential

# Unregister default User and Group admin
admin.site.unregister(User)
admin.site.unregister(Group)


@admin.register(User)
class UserAdmin(BaseUserAdmin, ModelAdmin):
    """Enhanced User admin with Unfold styling."""
    
    form = UserChangeForm
    add_form = UserCreationForm
    change_password_form = AdminPasswordChangeForm
    
    list_display = [
        'username', 'email', 'first_name', 'last_name', 
        'is_active', 'is_staff', 'last_login'
    ]
    list_filter = ['is_active', 'is_staff', 'is_superuser', 'date_joined']
    search_fields = ['username', 'first_name', 'last_name', 'email']
    
    # Unfold specific settings
    list_fullwidth = True
    warn_unsaved_form = True
    compressed_fields = True


@admin.register(Group)
class GroupAdmin(BaseGroupAdmin, ModelAdmin):
    """Enhanced Group admin with Unfold styling."""
    
    list_fullwidth = True
    search_fields = ['name']


@admin.register(Currency)
class CurrencyAdmin(ModelAdmin):
    """Enhanced Currency admin with visual indicators."""
    
    list_display = ['symbol', 'name', 'currency_type', 'is_active_display', 'decimal_places']
    list_filter = ['is_crypto', 'is_active']
    search_fields = ['symbol', 'name']
    list_per_page = 50
    
    # Unfold settings
    list_fullwidth = True
    compressed_fields = True
    
    @display(description="Type", label=True)
    def currency_type(self, obj):
        if obj.is_crypto:
            return format_html(
                '<span class="bg-blue-100 text-blue-800 px-2 py-1 rounded-full text-xs font-medium">Crypto</span>'
            )
        return format_html(
            '<span class="bg-green-100 text-green-800 px-2 py-1 rounded-full text-xs font-medium">Fiat</span>'
        )
    
    @display(description="Status", boolean=True)
    def is_active_display(self, obj):
        return obj.is_active


@admin.register(TradingPair)
class TradingPairAdmin(ModelAdmin):
    """Enhanced Trading Pair admin with relationship info."""
    
    list_display = [
        'symbol', 'base_currency', 'quote_currency', 
        'is_active_display', 'exchanges_count'
    ]
    list_filter = ['is_active', 'base_currency__is_crypto', 'quote_currency__is_crypto']
    search_fields = ['symbol', 'base_currency__symbol', 'quote_currency__symbol']
    raw_id_fields = ['base_currency', 'quote_currency']
    
    # Unfold settings
    list_fullwidth = True
    compressed_fields = True
    
    @display(description="Status", boolean=True)
    def is_active_display(self, obj):
        return obj.is_active
    
    @display(description="Exchanges")
    def exchanges_count(self, obj):
        count = obj.exchange_trading_pairs.filter(is_active=True).count()
        if count > 0:
            url = reverse('admin:core_exchangetradingpair_changelist')
            return format_html(
                '<a href="{}?trading_pair__id__exact={}" class="text-blue-600 hover:text-blue-800">{} exchanges</a>',
                url, obj.id, count
            )
        return "0 exchanges"


class ExchangeTradingPairInline(TabularInline):
    """Inline for Exchange Trading Pairs."""
    
    model = ExchangeTradingPair
    extra = 0
    fields = ['trading_pair', 'exchange_symbol', 'is_active', 'min_trade_amount']
    raw_id_fields = ['trading_pair']


@admin.register(Exchange)
class ExchangeAdmin(ModelAdmin):
    """Enhanced Exchange admin with performance metrics."""
    
    list_display = [
        'name', 'code', 'status_indicator', 'reliability_score_display',
        'rate_limit', 'is_active_display', 'trading_pairs_count'
    ]
    list_filter = ['is_active', 'code', 'requires_ip_whitelist']
    search_fields = ['name', 'code', 'api_url']
    readonly_fields = ['reliability_score']
    inlines = [ExchangeTradingPairInline]
    
    # Unfold settings
    list_fullwidth = True
    warn_unsaved_form = True
    tab_overview = {
        "fields": [
            ('name', 'code'),
            ('api_url', 'is_active'),
            ('rate_limit', 'reliability_score'),
            ('maker_fee', 'taker_fee'),
        ]
    }
    tab_security = {
        "fields": [
            ('requires_ip_whitelist', 'max_daily_volume'),
            ('connection_timeout', 'read_timeout'),
        ]
    }
    
    fieldsets = [
        ("Overview", tab_overview),
        ("Security & Limits", tab_security),
    ]
    
    @display(description="Status", label=True)
    def status_indicator(self, obj):
        try:
            status = obj.exchange_status
            if status.is_online:
                return format_html(
                    '<span class="bg-green-100 text-green-800 px-2 py-1 rounded-full text-xs font-medium flex items-center">'
                    '<span class="w-2 h-2 bg-green-600 rounded-full mr-1"></span>Online</span>'
                )
            else:
                return format_html(
                    '<span class="bg-red-100 text-red-800 px-2 py-1 rounded-full text-xs font-medium flex items-center">'
                    '<span class="w-2 h-2 bg-red-600 rounded-full mr-1"></span>Offline</span>'
                )
        except:
            return format_html(
                '<span class="bg-gray-100 text-gray-800 px-2 py-1 rounded-full text-xs font-medium">Unknown</span>'
            )
    
    @display(description="Reliability", ordering="reliability_score")
    def reliability_score_display(self, obj):
        score = obj.reliability_score
        if score >= 95:
            color = "green"
        elif score >= 85:
            color = "yellow"
        else:
            color = "red"
        
        return format_html(
            '<div class="flex items-center">'
            '<div class="w-16 bg-gray-200 rounded-full h-2 mr-2">'
            '<div class="bg-{}-600 h-2 rounded-full" style="width: {}%"></div>'
            '</div>'
            '<span class="text-{}-800 font-medium">{:.1f}%</span>'
            '</div>',
            color, score, color, score
        )
    
    @display(description="Status", boolean=True)
    def is_active_display(self, obj):
        return obj.is_active
    
    @display(description="Trading Pairs")
    def trading_pairs_count(self, obj):
        count = obj.exchange_trading_pairs.filter(is_active=True).count()
        return f"{count} pairs"


@admin.register(ExchangeTradingPair)
class ExchangeTradingPairAdmin(ModelAdmin):
    """Enhanced Exchange Trading Pair admin."""
    
    list_display = [
        'exchange', 'trading_pair', 'exchange_symbol', 
        'is_active_display', 'min_trade_amount', 'last_sync'
    ]
    list_filter = ['exchange', 'is_active', 'last_sync']
    search_fields = [
        'trading_pair__symbol', 'exchange_symbol', 
        'exchange__name', 'trading_pair__base_currency__symbol'
    ]
    raw_id_fields = ['exchange', 'trading_pair']
    
    # Unfold settings
    list_fullwidth = True
    compressed_fields = True
    
    @display(description="Status", boolean=True)
    def is_active_display(self, obj):
        return obj.is_active


@admin.register(APICredential)
class APICredentialAdmin(ModelAdmin):
    """Enhanced API Credential admin with security features."""
    
    list_display = [
        'user', 'exchange', 'is_active_display', 
        'last_used', 'usage_count', 'security_status'
    ]
    list_filter = ['exchange', 'is_active', 'last_used']
    search_fields = ['user__username', 'exchange__name']
    readonly_fields = ['last_used', 'usage_count', 'encrypted_api_key', 'encrypted_api_secret']
    
    # Unfold settings
    list_fullwidth = True
    warn_unsaved_form = True
    
    fieldsets = [
        ("Basic Information", {
            "fields": [
                ('user', 'exchange'),
                ('is_active',),
            ]
        }),
        ("API Credentials", {
            "fields": [
                ('api_key', 'api_secret'),
                ('encrypted_api_key', 'encrypted_api_secret'),
            ],
            "description": "Credentials are automatically encrypted when saved."
        }),
        ("Usage Statistics", {
            "fields": [
                ('last_used', 'usage_count'),
            ]
        }),
    ]
    
    @display(description="Status", boolean=True)
    def is_active_display(self, obj):
        return obj.is_active
    
    @display(description="Security", label=True)
    def security_status(self, obj):
        if obj.is_active and obj.api_key:
            return format_html(
                '<span class="bg-green-100 text-green-800 px-2 py-1 rounded-full text-xs font-medium">'
                '<i class="fas fa-lock mr-1"></i>Encrypted</span>'
            )
        return format_html(
            '<span class="bg-gray-100 text-gray-800 px-2 py-1 rounded-full text-xs font-medium">'
            '<i class="fas fa-exclamation-triangle mr-1"></i>Inactive</span>'
        )