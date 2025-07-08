import logging
import os
import psutil
from datetime import datetime, timedelta
from decimal import Decimal

from celery import shared_task
from django.conf import settings
from django.core.cache import cache
from django.db import connection
from django.utils import timezone

from core.models import Exchange, TradingPair
from exchanges.models import ExchangeStatus, MarketTicker

logger = logging.getLogger(__name__)


@shared_task
def security_monitoring():
    """
    Monitor system security and detect anomalies.
    """
    logger.info("Starting security monitoring...")
    
    security_report = {
        "timestamp": timezone.now().isoformat(),
        "alerts": [],
        "metrics": {}
    }
    
    # Check for suspicious API activity
    try:
        # Monitor failed login attempts (if authentication logs exist)
        # This is a placeholder - implement based on your authentication system
        failed_attempts = 0  # Get from your auth system
        
        if failed_attempts > 10:
            security_report["alerts"].append({
                "type": "auth_failure",
                "message": f"High number of failed login attempts: {failed_attempts}",
                "severity": "high"
            })
        
        # Monitor API rate limiting
        # Check Redis for rate limit violations
        try:
            # Get rate limit violations from cache
            violations = cache.get("rate_limit_violations", 0)
            if violations > 100:
                security_report["alerts"].append({
                    "type": "rate_limit",
                    "message": f"High rate limit violations: {violations}",
                    "severity": "medium"
                })
        except Exception as e:
            logger.warning(f"Could not check rate limits: {e}")
        
        # Monitor database connections
        with connection.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) FROM django_session")
            active_sessions = cursor.fetchone()[0]
            
            if active_sessions > 1000:
                security_report["alerts"].append({
                    "type": "high_sessions",
                    "message": f"High number of active sessions: {active_sessions}",
                    "severity": "medium"
                })
        
        # Monitor system resources
        cpu_percent = psutil.cpu_percent(interval=1)
        memory_percent = psutil.virtual_memory().percent
        disk_percent = psutil.disk_usage('/').percent
        
        if cpu_percent > 90:
            security_report["alerts"].append({
                "type": "high_cpu",
                "message": f"High CPU usage: {cpu_percent}%",
                "severity": "high"
            })
        
        if memory_percent > 90:
            security_report["alerts"].append({
                "type": "high_memory",
                "message": f"High memory usage: {memory_percent}%",
                "severity": "high"
            })
        
        if disk_percent > 90:
            security_report["alerts"].append({
                "type": "high_disk",
                "message": f"High disk usage: {disk_percent}%",
                "severity": "high"
            })
        
        security_report["metrics"] = {
            "cpu_percent": cpu_percent,
            "memory_percent": memory_percent,
            "disk_percent": disk_percent,
            "active_sessions": active_sessions
        }
        
        # Store security report in cache
        cache.set("security_report", security_report, 3600)
        
        if security_report["alerts"]:
            logger.warning(f"Security monitoring found {len(security_report['alerts'])} alerts")
            # Here you could send notifications to admins
        else:
            logger.info("Security monitoring completed - no alerts")
        
    except Exception as e:
        logger.error(f"Error in security monitoring: {e}")
        security_report["alerts"].append({
            "type": "monitoring_error",
            "message": f"Security monitoring failed: {str(e)}",
            "severity": "high"
        })
    
    return security_report


@shared_task
def system_health_check():
    """
    Comprehensive system health check.
    """
    logger.info("Starting system health check...")
    
    health_report = {
        "timestamp": timezone.now().isoformat(),
        "status": "healthy",
        "checks": {},
        "metrics": {}
    }
    
    try:
        # Database health
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                cursor.fetchone()
            health_report["checks"]["database"] = "healthy"
        except Exception as e:
            health_report["checks"]["database"] = f"unhealthy: {str(e)}"
            health_report["status"] = "unhealthy"
        
        # Cache health
        try:
            cache.set("health_check", "ok", 10)
            result = cache.get("health_check")
            if result == "ok":
                health_report["checks"]["cache"] = "healthy"
            else:
                health_report["checks"]["cache"] = "unhealthy: cache read/write failed"
                health_report["status"] = "degraded"
        except Exception as e:
            health_report["checks"]["cache"] = f"unhealthy: {str(e)}"
            health_report["status"] = "unhealthy"
        
        # Exchange connectivity
        exchanges_healthy = 0
        total_exchanges = 0
        
        for exchange in Exchange.objects.filter(is_active=True):
            total_exchanges += 1
            status = ExchangeStatus.objects.filter(exchange=exchange).first()
            if status and status.is_online:
                exchanges_healthy += 1
        
        if total_exchanges > 0:
            exchange_health_ratio = exchanges_healthy / total_exchanges
            if exchange_health_ratio >= 0.8:
                health_report["checks"]["exchanges"] = "healthy"
            elif exchange_health_ratio >= 0.5:
                health_report["checks"]["exchanges"] = "degraded"
                health_report["status"] = "degraded"
            else:
                health_report["checks"]["exchanges"] = "unhealthy"
                health_report["status"] = "unhealthy"
        else:
            health_report["checks"]["exchanges"] = "no_exchanges"
        
        # Market data freshness
        try:
            recent_cutoff = timezone.now() - timedelta(minutes=10)
            recent_tickers = MarketTicker.objects.filter(
                timestamp__gte=recent_cutoff
            ).count()
            
            if recent_tickers > 0:
                health_report["checks"]["market_data"] = "healthy"
            else:
                health_report["checks"]["market_data"] = "stale"
                health_report["status"] = "degraded"
        except Exception as e:
            health_report["checks"]["market_data"] = f"unhealthy: {str(e)}"
            health_report["status"] = "unhealthy"
        
        # System resources
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            memory_percent = psutil.virtual_memory().percent
            disk_percent = psutil.disk_usage('/').percent
            
            health_report["metrics"] = {
                "cpu_percent": cpu_percent,
                "memory_percent": memory_percent,
                "disk_percent": disk_percent,
                "exchanges_healthy": exchanges_healthy,
                "total_exchanges": total_exchanges,
                "recent_tickers": recent_tickers if 'recent_tickers' in locals() else 0
            }
            
            # Resource health checks
            if cpu_percent > 95:
                health_report["checks"]["cpu"] = "critical"
                health_report["status"] = "unhealthy"
            elif cpu_percent > 80:
                health_report["checks"]["cpu"] = "warning"
                if health_report["status"] == "healthy":
                    health_report["status"] = "degraded"
            else:
                health_report["checks"]["cpu"] = "healthy"
            
            if memory_percent > 95:
                health_report["checks"]["memory"] = "critical"
                health_report["status"] = "unhealthy"
            elif memory_percent > 80:
                health_report["checks"]["memory"] = "warning"
                if health_report["status"] == "healthy":
                    health_report["status"] = "degraded"
            else:
                health_report["checks"]["memory"] = "healthy"
            
            if disk_percent > 95:
                health_report["checks"]["disk"] = "critical"
                health_report["status"] = "unhealthy"
            elif disk_percent > 80:
                health_report["checks"]["disk"] = "warning"
                if health_report["status"] == "healthy":
                    health_report["status"] = "degraded"
            else:
                health_report["checks"]["disk"] = "healthy"
                
        except Exception as e:
            health_report["checks"]["system_resources"] = f"unhealthy: {str(e)}"
            health_report["status"] = "unhealthy"
        
        # Store health report in cache
        cache.set("system_health", health_report, 600)  # Cache for 10 minutes
        
        logger.info(f"System health check completed - status: {health_report['status']}")
        
    except Exception as e:
        logger.error(f"Error in system health check: {e}")
        health_report["status"] = "unhealthy"
        health_report["checks"]["health_check"] = f"failed: {str(e)}"
    
    return health_report 