import logging
import time
import uuid
from typing import Callable

from django.core.cache import cache
from django.http import JsonResponse

logger = logging.getLogger(__name__)


class RequestLoggingMiddleware:
    """
    Middleware to log all API requests and responses.
    """

    def __init__(self, get_response: Callable):
        self.get_response = get_response

    def __call__(self, request):
        # Generate request ID
        request.id = str(uuid.uuid4())
        
        # Start timer
        start_time = time.time()
        
        # Log request
        logger.info(
            f"Request {request.id} - {request.method} {request.path} "
            f"from {self.get_client_ip(request)}"
        )
        
        # Process request
        response = self.get_response(request)
        
        # Calculate duration
        duration = time.time() - start_time
        
        # Log response
        logger.info(
            f"Response {request.id} - Status: {response.status_code} "
            f"Duration: {duration:.3f}s"
        )
        
        # Add headers
        response["X-Request-ID"] = request.id
        response["X-Response-Time"] = f"{duration:.3f}"
        
        return response

    def get_client_ip(self, request):
        """Get the client's IP address."""
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            ip = x_forwarded_for.split(",")[0]
        else:
            ip = request.META.get("REMOTE_ADDR")
        return ip


class RateLimitMiddleware:
    """
    Simple rate limiting middleware using cache.
    """

    def __init__(self, get_response: Callable):
        self.get_response = get_response
        self.rate_limit = 100  # requests per minute
        self.window = 60  # seconds

    def __call__(self, request):
        # Skip rate limiting for admin and static files
        if request.path.startswith("/admin/") or request.path.startswith("/static/"):
            return self.get_response(request)
        
        # Get client identifier
        if request.user.is_authenticated:
            client_id = f"user:{request.user.id}"
        else:
            client_id = f"ip:{self.get_client_ip(request)}"
        
        # Check rate limit
        cache_key = f"rate_limit:{client_id}"
        request_count = cache.get(cache_key, 0)
        
        if request_count >= self.rate_limit:
            return JsonResponse(
                {
                    "error": "Rate limit exceeded",
                    "message": f"Maximum {self.rate_limit} requests per minute allowed"
                },
                status=429
            )
        
        # Increment counter
        cache.set(cache_key, request_count + 1, self.window)
        
        # Process request
        response = self.get_response(request)
        
        # Add rate limit headers
        response["X-RateLimit-Limit"] = str(self.rate_limit)
        response["X-RateLimit-Remaining"] = str(self.rate_limit - request_count - 1)
        response["X-RateLimit-Reset"] = str(int(time.time()) + self.window)
        
        return response

    def get_client_ip(self, request):
        """Get the client's IP address."""
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            ip = x_forwarded_for.split(",")[0]
        else:
            ip = request.META.get("REMOTE_ADDR")
        return ip


class SecurityHeadersMiddleware:
    """
    Middleware to add security headers to responses.
    """

    def __init__(self, get_response: Callable):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        
        # Add security headers
        response["X-Content-Type-Options"] = "nosniff"
        response["X-Frame-Options"] = "DENY"
        response["X-XSS-Protection"] = "1; mode=block"
        response["Referrer-Policy"] = "strict-origin-when-cross-origin"
        
        # Content Security Policy
        if not request.path.startswith("/admin/"):
            response["Content-Security-Policy"] = (
                "default-src 'self'; "
                "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdnjs.cloudflare.com; "
                "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
                "font-src 'self' https://fonts.gstatic.com; "
                "img-src 'self' data: https:; "
                "connect-src 'self' https://api.nobitex.ir https://api.wallex.ir https://api.ramzinex.com;"
            )
        
        return response


class MaintenanceModeMiddleware:
    """
    Middleware to enable maintenance mode.
    """

    def __init__(self, get_response: Callable):
        self.get_response = get_response

    def __call__(self, request):
        # Check if maintenance mode is enabled
        maintenance_mode = cache.get("maintenance_mode", False)
        
        if maintenance_mode and not request.user.is_staff:
            # Allow access to admin
            if not request.path.startswith("/admin/"):
                return JsonResponse(
                    {
                        "error": "Maintenance Mode",
                        "message": "The system is currently under maintenance. Please try again later."
                    },
                    status=503
                )
        
        return self.get_response(request)