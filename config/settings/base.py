"""
FIXED: Base settings with security hardening and performance optimization.
"""

import os
from pathlib import Path
from decouple import Csv, config
from cryptography.fernet import Fernet

# Build paths inside the project
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = config("SECRET_KEY")

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = config("DEBUG", default=False, cast=bool)

ALLOWED_HOSTS = config("ALLOWED_HOSTS", default="", cast=Csv())

# ENCRYPTION KEY for API credentials (CRITICAL SECURITY)
ENCRYPTION_KEY = config("ENCRYPTION_KEY", default=Fernet.generate_key().decode())

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
    "unfold.contrib.filters",     # Enhanced filters
    "unfold.contrib.forms",       # Form enhancements
    "unfold.contrib.inlines",     # Inline improvements
    "unfold.contrib.import_export", 
    "corsheaders",
    "django_extensions",
    "django_celery_beat",
    "django_ratelimit",  # NEW: Rate limiting
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

# Django Unfold Configuration
UNFOLD = {
    # Site branding
    "SITE_TITLE": "Crypto Arbitrage Admin",
    "SITE_HEADER": "Crypto Arbitrage Platform",
    "SITE_SUBHEADER": "Advanced Trading & Analytics",
    "SITE_URL": "/",
    "SITE_ICON": lambda request: static("admin/img/logo.svg"),
    "SITE_LOGO": lambda request: static("admin/img/logo-full.svg"),
    "SITE_SYMBOL": "₿",
    
    # Navigation and sidebar
    "SIDEBAR": {
        "show_search": True,
        "show_all_applications": True,
        "navigation": [
            {
                "title": _("Dashboard"),
                "icon": "dashboard",
                "separator": True,
                "collapsible": False,
                "items": [
                    {
                        "title": _("Overview"),
                        "icon": "analytics",
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
                        "title": _("Exchange Status"),
                        "icon": "health_and_safety",
                        "link": reverse_lazy("admin:exchanges_exchangestatus_changelist"),
                    },
                    {
                        "title": _("Market Tickers"),
                        "icon": "trending_up",
                        "link": reverse_lazy("admin:exchanges_marketticker_changelist"),
                    },
                    {
                        "title": _("Order Books"),
                        "icon": "list_alt",
                        "link": reverse_lazy("admin:exchanges_orderbook_changelist"),
                    },
                ],
            },
            {
                "title": _("Arbitrage Operations"),
                "icon": "compare_arrows",
                "separator": True,
                "collapsible": True,
                "items": [
                    {
                        "title": _("Opportunities"),
                        "icon": "trending_up",
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
                        "title": _("Configurations"),
                        "icon": "settings",
                        "link": reverse_lazy("admin:arbitrage_arbitrageconfig_changelist"),
                    },
                    {
                        "title": _("Alerts"),
                        "icon": "notifications",
                        "link": reverse_lazy("admin:arbitrage_arbitragealert_changelist"),
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
                        "title": _("Trades"),
                        "icon": "handshake",
                        "link": reverse_lazy("admin:trading_trade_changelist"),
                    },
                    {
                        "title": _("Positions"),
                        "icon": "account_balance_wallet",
                        "link": reverse_lazy("admin:trading_position_changelist"),
                    },
                    {
                        "title": _("Strategies"),
                        "icon": "psychology",
                        "link": reverse_lazy("admin:trading_tradingstrategy_changelist"),
                    },
                ],
            },
            {
                "title": _("Analytics & Reports"),
                "icon": "analytics",
                "separator": True,
                "collapsible": True,
                "items": [
                    {
                        "title": _("Daily Summary"),
                        "icon": "summarize",
                        "link": reverse_lazy("admin:analytics_dailyarbitragesummary_changelist"),
                    },
                    {
                        "title": _("Exchange Performance"),
                        "icon": "speed",
                        "link": reverse_lazy("admin:analytics_exchangeperformance_changelist"),
                    },
                    {
                        "title": _("Market Snapshots"),
                        "icon": "camera_alt",
                        "link": reverse_lazy("admin:analytics_marketsnapshot_changelist"),
                    },
                    {
                        "title": _("User Performance"),
                        "icon": "person",
                        "link": reverse_lazy("admin:analytics_userperformance_changelist"),
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
                    {
                        "title": _("API Credentials"),
                        "icon": "vpn_key",
                        "link": reverse_lazy("admin:core_apicredential_changelist"),
                    },
                ],
            },
            {
                "title": _("System"),
                "icon": "settings",
                "separator": True,
                "collapsible": True,
                "items": [
                    {
                        "title": _("Currencies"),
                        "icon": "paid",
                        "link": reverse_lazy("admin:core_currency_changelist"),
                    },
                    {
                        "title": _("Celery Tasks"),
                        "icon": "task",
                        "link": "/admin/django_celery_beat/",
                    },
                ],
            },
        ],
    },
    
    # Theme and styling
    "THEME": "auto",  # auto, light, dark
    "COLORS": {
        "primary": {
            "50": "240 249 255",    # Very light blue
            "100": "224 242 254",   # Light blue
            "200": "186 230 253",   # Lighter blue
            "300": "125 211 252",   # Light blue
            "400": "56 189 248",    # Medium blue
            "500": "14 165 233",    # Primary blue
            "600": "2 132 199",     # Darker blue
            "700": "3 105 161",     # Dark blue
            "800": "7 89 133",      # Very dark blue
            "900": "12 74 110",     # Darkest blue
            "950": "8 47 73",       # Almost black blue
        },
        "font": {
            "subtle-light": "156 163 175",
            "subtle-dark": "156 163 175",
            "default-light": "31 41 55",
            "default-dark": "209 213 219",
            "important-light": "17 24 39",
            "important-dark": "243 244 246",
        },
    },
    
    # Dashboard customization
    "DASHBOARD_CALLBACK": "core.admin_dashboard.dashboard_callback",
    
    # Login page customization
    "LOGIN": {
        "image": lambda request: static("admin/img/login-bg.jpg"),
        "redirect_after": lambda request: reverse_lazy("admin:index"),
    },
    
    # Environment indication
    "ENVIRONMENT": "crypto_arbitrage.settings.get_environment_label",
    
    # Show environment info
    "SHOW_HISTORY": True,
    "SHOW_VIEW_ON_SITE": True,
    
    # Custom styles and scripts
    "STYLES": [
        lambda request: static("admin/css/custom.css"),
    ],
    "SCRIPTS": [
        lambda request: static("admin/js/custom.js"),
    ],
    
    # Advanced features
    "TABS": [
        {
            "models": ["core.exchange", "core.tradingpair"],
            "items": [
                {
                    "title": _("Configuration"),
                    "icon": "settings",
                    "link": reverse_lazy("admin:core_exchange_changelist"),
                },
                {
                    "title": _("Performance"),
                    "icon": "speed",
                    "link": reverse_lazy("admin:analytics_exchangeperformance_changelist"),
                },
            ],
        },
    ],
}

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "core.middleware.SecurityHeadersMiddleware",  # NEW: Enhanced security
    "core.middleware.EnhancedRateLimitMiddleware",  # NEW: API rate limiting
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "core.middleware.RequestLoggingMiddleware",
    "core.middleware.MaintenanceModeMiddleware",
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

# Database configuration - Using SQLite for development
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

# PostgreSQL configuration (commented out for now)
# DATABASES = {
#     "default": {
#         "ENGINE": "django.db.backends.postgresql",
#         "NAME": config("DB_NAME", default="crypto_arbitrage"),
#         "USER": config("DB_USER", default="postgres"),
#         "PASSWORD": config("DB_PASSWORD", default="postgres"),
#         "HOST": config("DB_HOST", default="localhost"),
#         "PORT": config("DB_PORT", default="5432"),
#         "CONN_MAX_AGE": 300,  # FIXED: Reduced from 600 for faster failover
#         "OPTIONS": {
#             "MAX_CONNS": 20,
#             "connect_timeout": 10,
#             "options": "-c default_transaction_isolation=read_committed"
#         },
#         "TEST": {
#             "NAME": "test_crypto_arbitrage",
#         },
#     }
# }

# Redis configuration with optimization
REDIS_URL = config("REDIS_URL", default="redis://localhost:6379/0")

# Enhanced cache configuration
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": REDIS_URL,
        "TIMEOUT": 300,
        "KEY_PREFIX": "crypto_arbitrage",
        "VERSION": 1,
    },
    # SEPARATE cache for market data (high-frequency)
    "market_data": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": config("REDIS_MARKET_URL", default="redis://localhost:6379/1"),
        "TIMEOUT": 60,  # Shorter timeout for market data
        "KEY_PREFIX": "market",
    },
    # SEPARATE cache for API rate limiting
    "rate_limit": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": config("REDIS_RATELIMIT_URL", default="redis://localhost:6379/2"),
        "TIMEOUT": 3600,  # 1 hour for rate limiting
        "KEY_PREFIX": "ratelimit",
    }
}

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {"min_length": 12},  # FIXED: Stronger passwords
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

# Internationalization
LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]

# Media files
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

# Default primary key field type
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# FIXED: Enhanced Celery Configuration with performance optimization
CELERY_BROKER_URL = config("CELERY_BROKER_URL", default="redis://localhost:6379/1")
CELERY_RESULT_BACKEND = config("CELERY_RESULT_BACKEND", default="redis://localhost:6379/2")
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = TIME_ZONE
CELERY_BEAT_SCHEDULER = "django_celery_beat.schedulers:DatabaseScheduler"

# PERFORMANCE: Celery optimization
CELERY_WORKER_PREFETCH_MULTIPLIER = 1  # Critical for arbitrage
CELERY_TASK_ACKS_LATE = True
CELERY_TASK_REJECT_ON_WORKER_LOST = True
CELERY_WORKER_MAX_TASKS_PER_CHILD = 1000
CELERY_TASK_SOFT_TIME_LIMIT = 300
CELERY_TASK_TIME_LIMIT = 600

# CORS settings with security
CORS_ALLOWED_ORIGINS = config(
    "CORS_ALLOWED_ORIGINS",
    default="http://localhost:3000,http://127.0.0.1:3000",
    cast=Csv(),
)
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOWED_HEADERS = [
    'accept',
    'accept-encoding',
    'authorization',
    'content-type',
    'dnt',
    'origin',
    'user-agent',
    'x-csrftoken',
    'x-requested-with',
    'x-api-key',  # NEW: For API authentication
]

# ENHANCED: Exchange API Configuration with security
EXCHANGE_CONFIG = {
    "nobitex": {
        "api_key": config("NOBITEX_API_KEY", default=""),
        "api_url": config("NOBITEX_API_URL", default="https://api.nobitex.ir"),
        "rate_limit": config("NOBITEX_RATE_LIMIT", default=300, cast=int),
        "timeout": config("NOBITEX_TIMEOUT", default=10, cast=int),
        "max_retries": 3,
        "backoff_factor": 0.3,
    },
    "wallex": {
        "api_key": config("WALLEX_API_KEY", default=""),
        "api_url": config("WALLEX_API_URL", default="https://api.wallex.ir"),
        "rate_limit": config("WALLEX_RATE_LIMIT", default=60, cast=int),
        "timeout": config("WALLEX_TIMEOUT", default=10, cast=int),
        "max_retries": 3,
        "backoff_factor": 0.3,
    },
    "ramzinex": {
        "api_key": config("RAMZINEX_API_KEY", default=""),
        "secret_key": config("RAMZINEX_SECRET_KEY", default=""),
        "api_url": config("RAMZINEX_API_URL", default="https://api.ramzinex.com"),
        "rate_limit": config("RAMZINEX_RATE_LIMIT", default=60, cast=int),
        "timeout": config("RAMZINEX_TIMEOUT", default=10, cast=int),
        "max_retries": 3,
        "backoff_factor": 0.3,
    },
}

# ENHANCED: Trading Configuration with security limits
TRADING_CONFIG = {
    "auto_trade_enabled": config("AUTO_TRADE_ENABLED", default=False, cast=bool),
    "min_arbitrage_threshold": config("MIN_ARBITRAGE_THRESHOLD", default=0.5, cast=float),
    "max_trade_amount": {
        "USDT": config("MAX_TRADE_AMOUNT_USDT", default=100, cast=float),
        "RLS": config("MAX_TRADE_AMOUNT_RLS", default=10000000, cast=float),
    },
    "max_daily_trades": config("MAX_DAILY_TRADES", default=1000, cast=int),
    "max_concurrent_executions": config("MAX_CONCURRENT_EXECUTIONS", default=50, cast=int),
    "emergency_stop_loss": config("EMERGENCY_STOP_LOSS", default=5.0, cast=float),  # 5% loss
}

# NEW: Security Configuration
SECURITY_CONFIG = {
    "api_key_rotation_days": config("API_KEY_ROTATION_DAYS", default=90, cast=int),
    "max_api_calls_per_hour": config("MAX_API_CALLS_PER_HOUR", default=10000, cast=int),
    "ip_whitelist_required": config("IP_WHITELIST_REQUIRED", default=False, cast=bool),
    "two_factor_required": config("TWO_FACTOR_REQUIRED", default=False, cast=bool),
    "session_timeout_minutes": config("SESSION_TIMEOUT_MINUTES", default=60, cast=int),
}

# ENHANCED: Rate Limiting Configuration
RATELIMIT_STORAGE = 'django_ratelimit.storage.CacheStorage'
RATELIMIT_CACHE_PREFIX = 'rl:'
RATELIMIT_DEFAULT_RATE = '1000/h'  # Default rate limit

# API Rate limits per endpoint type
API_RATE_LIMITS = {
    'market_data': '2000/h',      # High frequency for market data
    'trading': '500/h',           # Moderate for trading
    'arbitrage': '100/h',         # Conservative for arbitrage
    'admin': '50/h',             # Low for admin operations
    'public': '1000/h',          # Public endpoints
}

# Monitoring Configuration
MONITORING_CONFIG = {
    "enabled": config("ENABLE_MONITORING", default=True, cast=bool),
    "alert_email": config("ALERT_EMAIL", default=""),
    "alert_threshold": config("ALERT_THRESHOLD", default=2.0, cast=float),
    "performance_tracking": config("PERFORMANCE_TRACKING", default=True, cast=bool),
    "error_tracking": config("ERROR_TRACKING", default=True, cast=bool),
}

# ENHANCED: Scheduler Configuration with faster intervals
SCHEDULER_CONFIG = {
    "price_update_interval": config("PRICE_UPDATE_INTERVAL", default=2, cast=int),  # FIXED: 2s instead of 5s
    "arbitrage_check_interval": config("ARBITRAGE_CHECK_INTERVAL", default=2, cast=int),  # FIXED: 2s instead of 10s
    "order_book_update_interval": config("ORDER_BOOK_UPDATE_INTERVAL", default=1, cast=int),  # NEW: 1s
    "balance_sync_interval": config("BALANCE_SYNC_INTERVAL", default=30, cast=int),
    "health_check_interval": config("HEALTH_CHECK_INTERVAL", default=60, cast=int),
}

# Session Configuration for security
SESSION_COOKIE_SECURE = not DEBUG
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'
SESSION_COOKIE_AGE = SECURITY_CONFIG['session_timeout_minutes'] * 60

# CSRF Configuration
CSRF_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_HTTPONLY = True
CSRF_COOKIE_SAMESITE = 'Lax'

# Security Headers
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_HSTS_SECONDS = 31536000 if not DEBUG else 0
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# ENHANCED: Logging Configuration with security and performance focus
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "{levelname} {asctime} {module} {process:d} {thread:d} {message}",
            "style": "{",
        },
        "simple": {
            "format": "{levelname} {message}",
            "style": "{",
        },
        "security": {
            "format": "SECURITY {asctime} {levelname} {module} {message}",
            "style": "{",
        },
    },
    "filters": {
        "require_debug_true": {
            "()": "django.utils.log.RequireDebugTrue",
        },
        "require_debug_false": {
            "()": "django.utils.log.RequireDebugFalse",
        },
    },
    "handlers": {
        "console": {
            "level": "INFO",
            "filters": ["require_debug_true"],
            "class": "logging.StreamHandler",
            "formatter": "simple",
        },
        "file": {
            "level": "INFO",
            "class": "logging.handlers.RotatingFileHandler",
            "filename": config("LOG_FILE", default="logs/crypto_arbitrage.log"),
            "maxBytes": 1024 * 1024 * 15,  # 15MB
            "backupCount": 10,
            "formatter": "verbose",
        },
        "security_file": {
            "level": "WARNING",
            "class": "logging.handlers.RotatingFileHandler",
            "filename": config("SECURITY_LOG_FILE", default="logs/security.log"),
            "maxBytes": 1024 * 1024 * 10,  # 10MB
            "backupCount": 20,
            "formatter": "security",
        },
        "arbitrage_file": {
            "level": "INFO",
            "class": "logging.handlers.RotatingFileHandler",
            "filename": config("ARBITRAGE_LOG_FILE", default="logs/arbitrage.log"),
            "maxBytes": 1024 * 1024 * 50,  # 50MB for high-frequency arbitrage
            "backupCount": 5,
            "formatter": "verbose",
        },
    },
    "root": {
        "handlers": ["console", "file"],
        "level": "INFO",
    },
    "loggers": {
        "django": {
            "handlers": ["console", "file"],
            "level": config("LOG_LEVEL", default="INFO"),
            "propagate": False,
        },
        "django.security": {
            "handlers": ["security_file"],
            "level": "WARNING",
            "propagate": False,
        },
        "arbitrage": {
            "handlers": ["arbitrage_file", "console"],
            "level": "INFO",
            "propagate": False,
        },
        "exchanges": {
            "handlers": ["arbitrage_file", "console"],
            "level": "INFO",
            "propagate": False,
        },
        "trading": {
            "handlers": ["arbitrage_file", "console"],
            "level": "INFO",
            "propagate": False,
        },
        "security": {
            "handlers": ["security_file", "console"],
            "level": "WARNING",
            "propagate": False,
        },
    },
}

# Performance monitoring
if config("DJANGO_DEBUG_TOOLBAR", default=False, cast=bool):
    INSTALLED_APPS.append("debug_toolbar")
    MIDDLEWARE.insert(0, "debug_toolbar.middleware.DebugToolbarMiddleware")
    INTERNAL_IPS = ["127.0.0.1", "localhost"]

# Email configuration for alerts
EMAIL_BACKEND = config("EMAIL_BACKEND", default="django.core.mail.backends.console.EmailBackend")
EMAIL_HOST = config("EMAIL_HOST", default="")
EMAIL_PORT = config("EMAIL_PORT", default=587, cast=int)
EMAIL_USE_TLS = config("EMAIL_USE_TLS", default=True, cast=bool)
EMAIL_HOST_USER = config("EMAIL_HOST_USER", default="")
EMAIL_HOST_PASSWORD = config("EMAIL_HOST_PASSWORD", default="")
DEFAULT_FROM_EMAIL = config("DEFAULT_FROM_EMAIL", default="noreply@arbitrage.local")

# Admin security
ADMIN_URL = config("ADMIN_URL", default="admin/")
ADMINS = [
    ("Admin", config("ADMIN_EMAIL", default="admin@example.com")),
]
MANAGERS = ADMINS

# NEW: API Documentation settings
API_DOCS_ENABLED = config("API_DOCS_ENABLED", default=True, cast=bool)
API_DOCS_URL = config("API_DOCS_URL", default="/docs/")

# Development settings
if DEBUG:
    # Allow all hosts in development
    ALLOWED_HOSTS = ["*"]
    
    # Development-specific logging
    LOGGING["handlers"]["console"]["level"] = "DEBUG"
    LOGGING["loggers"]["arbitrage"]["level"] = "DEBUG"
    
    # Disable security features in development
    SESSION_COOKIE_SECURE = False
    CSRF_COOKIE_SECURE = False
    SECURE_HSTS_SECONDS = 0
else:
    # Production security settings
    SECURE_SSL_REDIRECT = True
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    
    # Production performance settings
    DATABASES["default"]["CONN_MAX_AGE"] = 600
    
    # Disable debug toolbar
    if "debug_toolbar" in INSTALLED_APPS:
        INSTALLED_APPS.remove("debug_toolbar")
    
    # Production logging - reduce verbosity
    LOGGING["handlers"]["console"]["level"] = "WARNING"