# FIXED: Database configuration - Enhanced SQLite settings for Celery compatibility

import os
from pathlib import Path
from decouple import Csv, config
from cryptography.fernet import Fernet
from django.utils.translation import gettext_lazy as _
from django.urls import reverse_lazy
from django.templatetags.static import static

# Build paths inside the project
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = config("SECRET_KEY")

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = config("DEBUG", default=False, cast=bool)

ALLOWED_HOSTS = config("ALLOWED_HOSTS", default="", cast=Csv())

# ENCRYPTION KEY for API credentials (CRITICAL SECURITY)
ENCRYPTION_KEY = config("ENCRYPTION_KEY", default=Fernet.generate_key().decode())

# FIXED: Enhanced SQLite configuration with proper timeout and threading
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
        "OPTIONS": {
            # FIXED: Critical settings for Celery compatibility
            'timeout': 30,  # 30 second timeout for locked database
            'check_same_thread': False,  # Allow multiple threads
            'init_command': "PRAGMA journal_mode=WAL; PRAGMA synchronous=NORMAL; PRAGMA temp_store=memory; PRAGMA mmap_size=268435456;",
        },
        # FIXED: Connection management
        'CONN_MAX_AGE': 0,  # No persistent connections with SQLite + Celery
        'ATOMIC_REQUESTS': True,  # Wrap each request in transaction
        'AUTOCOMMIT': True,
    }
}

# FIXED: Alternative PostgreSQL configuration (recommended for production)
# Uncomment this and comment SQLite above for production use
"""
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": config("DB_NAME", default="crypto_arbitrage"),
        "USER": config("DB_USER", default="postgres"),
        "PASSWORD": config("DB_PASSWORD", default="postgres"),
        "HOST": config("DB_HOST", default="localhost"),
        "PORT": config("DB_PORT", default="5432"),
        "CONN_MAX_AGE": 60,  # 1 minute connection reuse
        "OPTIONS": {
            "MAX_CONNS": 20,
            "connect_timeout": 10,
            "options": "-c default_transaction_isolation=read_committed"
        },
        "TEST": {
            "NAME": "test_crypto_arbitrage",
        },
    }
}
"""

# Redis configuration with optimization
REDIS_URL = config("REDIS_URL", default="redis://localhost:6379/0")

# FIXED: Enhanced cache configuration with better timeouts
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": REDIS_URL,
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
            "CONNECTION_POOL_KWARGS": {
                "max_connections": 50,
                "socket_timeout": 5,
                "socket_connect_timeout": 5,
                "health_check_interval": 30,
            },
        },
        "KEY_PREFIX": "arbitrage",
        "TIMEOUT": 300,  # 5 minutes default
    },
    # FIXED: Separate cache for market data (high frequency)
    "market_data": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": config("REDIS_MARKET_URL", default="redis://localhost:6379/1"),
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
            "CONNECTION_POOL_KWARGS": {
                "max_connections": 30,
                "socket_timeout": 2,
                "socket_connect_timeout": 2,
            },
        },
        "KEY_PREFIX": "market",
        "TIMEOUT": 60,  # 1 minute for market data
    },
    # FIXED: Separate cache for rate limiting
    "ratelimit": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": config("REDIS_RATELIMIT_URL", default="redis://localhost:6379/2"),
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
            "CONNECTION_POOL_KWARGS": {
                "max_connections": 10,
                "socket_timeout": 1,
                "socket_connect_timeout": 1,
            },
        },
        "KEY_PREFIX": "ratelimit",
        "TIMEOUT": 3600,  # 1 hour for rate limits
    },
}

# FIXED: Celery Configuration with SQLite optimizations
CELERY_BROKER_URL = config("CELERY_BROKER_URL", default="redis://localhost:6379/1")
CELERY_RESULT_BACKEND = config("CELERY_RESULT_BACKEND", default="redis://localhost:6379/2")

# FIXED: Celery settings optimized for SQLite
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TIMEZONE = 'UTC'
CELERY_ENABLE_UTC = True

# FIXED: Critical settings for SQLite + Celery compatibility
CELERY_TASK_ALWAYS_EAGER = False
CELERY_TASK_EAGER_PROPAGATES = True
CELERY_WORKER_PREFETCH_MULTIPLIER = 1
CELERY_TASK_ACKS_LATE = True
CELERY_WORKER_MAX_TASKS_PER_CHILD = 100
CELERY_TASK_SOFT_TIME_LIMIT = 300
CELERY_TASK_TIME_LIMIT = 600

# FIXED: Reduced concurrency for SQLite
CELERY_WORKER_CONCURRENCY = 2

# FIXED: Use file-based beat scheduler instead of database
CELERY_BEAT_SCHEDULER = 'celery.beat:PersistentScheduler'
CELERY_BEAT_SCHEDULE_FILENAME = 'logs/celerybeat-schedule'

# FIXED: Scheduler intervals optimized for development
SCHEDULER_CONFIG = {
    'price_update_interval': config('PRICE_UPDATE_INTERVAL', default=5, cast=int),  # Increased from 2
    'arbitrage_check_interval': config('ARBITRAGE_CHECK_INTERVAL', default=10, cast=int),  # Increased from 2
    'order_book_update_interval': config('ORDER_BOOK_UPDATE_INTERVAL', default=5, cast=int),  # Increased from 1
    'balance_sync_interval': config('BALANCE_SYNC_INTERVAL', default=30, cast=int),
    'health_check_interval': config('HEALTH_CHECK_INTERVAL', default=60, cast=int),
}

# Application definition
DJANGO_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
]

THIRD_PARTY_APPS = [
    "unfold",
    "unfold.contrib.filters",
    "unfold.contrib.forms",
    "unfold.contrib.inlines",
    "unfold.contrib.import_export", 
    "corsheaders",
    "django_extensions",
    "django_celery_beat",
    "django_ratelimit",
]

LOCAL_APPS = [
    "core",
    "exchanges",
    "arbitrage",
    "trading",
    "accounts",
    "analytics",
]

INSTALLED_APPS = THIRD_PARTY_APPS + DJANGO_APPS + LOCAL_APPS

# FIXED: Middleware optimized for performance
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

# FIXED: Logging configuration optimized for debugging
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            "filename": 'logs/crypto_arbitrage.log',
            'formatter': 'verbose',
        },
        'arbitrage_file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            "filename": 'logs/arbitrage.log',
            'formatter': 'verbose',
        },
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['file', 'console'],
            'level': 'INFO',
            'propagate': True,
        },
        'arbitrage': {
            'handlers': ['arbitrage_file', 'console'],
            'level': 'INFO',
            'propagate': True,
        },
        'exchanges': {
            'handlers': ['file', 'console'],
            'level': 'INFO',
            'propagate': True,
        },
        'trading': {
            'handlers': ['file', 'console'],
            'level': 'INFO',
            'propagate': True,
        },
    },
}

# FIXED: Static files configuration
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [
    BASE_DIR / 'static',
]

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# FIXED: Security settings
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'
SECURE_HSTS_SECONDS = 31536000 if not DEBUG else 0
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# CORS settings
CORS_ALLOW_ALL_ORIGINS = DEBUG
CORS_ALLOWED_ORIGINS = config(
    "CORS_ALLOWED_ORIGINS",
    default="http://localhost:3000,http://127.0.0.1:3000",
    cast=Csv(),
)
CORS_ALLOW_CREDENTIALS = True

UNFOLD = {
    # Site branding
    "SITE_TITLE": "Crypto Arbitrage Admin",
    "SITE_HEADER": "Crypto Arbitrage Platform",
    "SITE_SUBHEADER": "Advanced Trading & Analytics Dashboard",
    "SITE_URL": "/",
    "SITE_ICON": lambda request: static("admin/img/logo.svg"),
    "SITE_LOGO": lambda request: static("admin/img/logo-full.svg"),
    "SITE_SYMBOL": "₿",
    "SITE_FAVICONS": [
        {
            "rel": "icon",
            "sizes": "32x32",
            "type": "image/svg+xml",
            "href": lambda request: static("admin/img/favicon.svg"),
        },
    ],
    
    # Color theme
    "COLORS": {
        "primary": {
            "50": "250 245 255",
            "100": "243 232 255", 
            "200": "233 213 255",
            "300": "216 180 254",
            "400": "196 181 253",
            "500": "168 85 247",   # Main brand color
            "600": "147 51 234",
            "700": "126 34 206",
            "800": "107 33 168",
            "900": "88 28 135",
            "950": "59 7 100",
        },
        "font": {
            "subtle-light": "115 115 115",
            "subtle-dark": "212 212 212",
            "default-light": "0 0 0",
            "default-dark": "255 255 255",
            "important-light": "0 0 0",
            "important-dark": "255 255 255",
        },
    },
    
    # Dashboard customization
    "DASHBOARD_CALLBACK": "core.admin_dashboard.dashboard_callback",
    "INDEX_TEMPLATE": "admin/enhanced_index.html",
    
    # Navigation and sidebar
    "SIDEBAR": {
        "show_search": True,
        "show_all_applications": True,
        "navigation": [
            {
                "title": _("Dashboard"),
                "icon": "analytics",
                "separator": True,
                "collapsible": False,
                "items": [
                    {
                        "title": _("Overview"),
                        "icon": "dashboard",
                        "link": reverse_lazy("admin:index"),
                    },
                    {
                        "title": _("System Health"),
                        "icon": "monitor_heart",
                        "link": reverse_lazy("admin:core_exchange_changelist"),
                    },
                ],
            },
            {
                "title": _("Exchange Management"),
                "icon": "currency_exchange",
                "separator": True,
                "collapsible": True,
                "items": [
                    {
                        "title": _("Exchanges"),
                        "icon": "account_balance",
                        "link": reverse_lazy("admin:core_exchange_changelist"),
                    },
                    {
                        "title": _("Trading Pairs"),
                        "icon": "swap_horiz",
                        "link": reverse_lazy("admin:core_tradingpair_changelist"),
                    },
                    {
                        "title": _("API Credentials"),
                        "icon": "vpn_key",
                        "link": reverse_lazy("admin:core_apicredential_changelist"),
                    },
                    {
                        "title": _("Market Data"),
                        "icon": "trending_up",
                        "link": reverse_lazy("admin:exchanges_marketticker_changelist"),
                    },
                ],
            },
            {
                "title": _("Arbitrage Operations"),
                "icon": "trending_up",
                "separator": True,
                "collapsible": True,
                "items": [
                    {
                        "title": _("Opportunities"),
                        "icon": "flash_on",
                        "link": reverse_lazy("admin:arbitrage_arbitrageopportunity_changelist"),
                    },
                    {
                        "title": _("Multi-Exchange Strategies"),
                        "icon": "device_hub",
                        "link": reverse_lazy("admin:arbitrage_multiexchangearbitragestrategy_changelist"),
                    },
                    {
                        "title": _("Executions"),
                        "icon": "play_arrow",
                        "link": reverse_lazy("admin:arbitrage_arbitrageexecution_changelist"),
                    },
                    {
                        "title": _("Configuration"),
                        "icon": "settings",
                        "link": reverse_lazy("admin:arbitrage_arbitrageconfig_changelist"),
                    },
                ],
            },
            {
                "title": _("Trading"),
                "icon": "show_chart",
                "separator": True,
                "collapsible": True,
                "items": [
                    {
                        "title": _("Orders"),
                        "icon": "receipt",
                        "link": reverse_lazy("admin:trading_order_changelist"),
                    },
                    {
                        "title": _("Positions"),
                        "icon": "account_balance_wallet",
                        "link": reverse_lazy("admin:trading_position_changelist"),
                    },
                    {
                        "title": _("Trades"),
                        "icon": "swap_vert",
                        "link": reverse_lazy("admin:trading_trade_changelist"),
                    },
                    {
                        "title": _("Strategies"),
                        "icon": "psychology",
                        "link": reverse_lazy("admin:trading_tradingstrategy_changelist"),
                    },
                ],
            },
            {
                "title": _("Analytics"),
                "icon": "bar_chart",
                "separator": True,
                "collapsible": True,
                "items": [
                    {
                        "title": _("Performance Reports"),
                        "icon": "assessment",
                        "link": reverse_lazy("admin:analytics_dailyarbitragesummary_changelist"),
                    },
                    {
                        "title": _("Exchange Performance"),
                        "icon": "speed",
                        "link": reverse_lazy("admin:analytics_exchangeperformance_changelist"),
                    },
                ],
            },
            {
                "title": _("User Management"),
                "icon": "people",
                "separator": True,
                "collapsible": True,
                "items": [
                    {
                        "title": _("Users"),
                        "icon": "person",
                        "link": reverse_lazy("admin:auth_user_changelist"),
                    },
                    {
                        "title": _("Groups"),
                        "icon": "group",
                        "link": reverse_lazy("admin:auth_group_changelist"),
                    },
                    {
                        "title": _("User Profiles"),
                        "icon": "account_circle",
                        "link": reverse_lazy("admin:accounts_userprofile_changelist"),
                    },
                ],
            },
        ],
    },
}