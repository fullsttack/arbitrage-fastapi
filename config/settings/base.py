"""
Base settings for Crypto Arbitrage project.
"""

import os
from pathlib import Path

from decouple import Csv, config

# Build paths inside the project
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = config("SECRET_KEY")

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = config("DEBUG", default=False, cast=bool)

ALLOWED_HOSTS = config("ALLOWED_HOSTS", default="", cast=Csv())

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
    "corsheaders",
    "django_extensions",
    "django_celery_beat",
]

LOCAL_APPS = [
    "core",
    "exchanges",
    "arbitrage",
    "trading",
    "accounts",
    "analytics",
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "core.middleware.RequestLoggingMiddleware",
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

# Database
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": config("DB_NAME", default="crypto_arbitrage"),
        "USER": config("DB_USER", default="postgres"),
        "PASSWORD": config("DB_PASSWORD", default="postgres"),
        "HOST": config("DB_HOST", default="localhost"),
        "PORT": config("DB_PORT", default="5432"),
        "CONN_MAX_AGE": 600,
    }
}

# Redis configuration
REDIS_URL = config("REDIS_URL", default="redis://localhost:6379/0")

# Cache configuration
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": REDIS_URL,
        "TIMEOUT": 300,
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
        },
    }
}

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
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

# Celery Configuration
CELERY_BROKER_URL = config("CELERY_BROKER_URL", default="redis://localhost:6379/1")
CELERY_RESULT_BACKEND = config("CELERY_RESULT_BACKEND", default="redis://localhost:6379/2")
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = TIME_ZONE
CELERY_BEAT_SCHEDULER = "django_celery_beat.schedulers:DatabaseScheduler"

# CORS settings
CORS_ALLOWED_ORIGINS = config(
    "CORS_ALLOWED_ORIGINS",
    default="http://localhost:3000,http://127.0.0.1:3000",
    cast=Csv(),
)
CORS_ALLOW_CREDENTIALS = True

# Exchange API Configuration
EXCHANGE_CONFIG = {
    "nobitex": {
        "api_key": config("NOBITEX_API_KEY", default=""),
        "api_url": config("NOBITEX_API_URL", default="https://api.nobitex.ir"),
        "rate_limit": config("NOBITEX_RATE_LIMIT", default=300, cast=int),
    },
    "wallex": {
        "api_key": config("WALLEX_API_KEY", default=""),
        "api_url": config("WALLEX_API_URL", default="https://api.wallex.ir"),
        "rate_limit": config("WALLEX_RATE_LIMIT", default=60, cast=int),
    },
    "ramzinex": {
        "api_key": config("RAMZINEX_API_KEY", default=""),
        "secret_key": config("RAMZINEX_SECRET_KEY", default=""),
        "api_url": config("RAMZINEX_API_URL", default="https://api.ramzinex.com"),
        "rate_limit": config("RAMZINEX_RATE_LIMIT", default=60, cast=int),
    },
}

# Trading Configuration
TRADING_CONFIG = {
    "auto_trade_enabled": config("AUTO_TRADE_ENABLED", default=False, cast=bool),
    "min_arbitrage_threshold": config("MIN_ARBITRAGE_THRESHOLD", default=0.5, cast=float),
    "max_trade_amount": {
        "USDT": config("MAX_TRADE_AMOUNT_USDT", default=100, cast=float),
        "RLS": config("MAX_TRADE_AMOUNT_RLS", default=10000000, cast=float),
    },
}

# Monitoring Configuration
MONITORING_CONFIG = {
    "enabled": config("ENABLE_MONITORING", default=True, cast=bool),
    "alert_email": config("ALERT_EMAIL", default=""),
    "alert_threshold": config("ALERT_THRESHOLD", default=2.0, cast=float),
}

# Scheduler Configuration
SCHEDULER_CONFIG = {
    "price_update_interval": config("PRICE_UPDATE_INTERVAL", default=5, cast=int),
    "arbitrage_check_interval": config("ARBITRAGE_CHECK_INTERVAL", default=10, cast=int),
}

# Logging Configuration
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
    },
    "filters": {
        "require_debug_true": {
            "()": "django.utils.log.RequireDebugTrue",
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
        "apps": {
            "handlers": ["console", "file"],
            "level": config("LOG_LEVEL", default="INFO"),
            "propagate": False,
        },
    },
}