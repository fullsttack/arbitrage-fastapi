import hashlib
import hmac
import logging
import time
import uuid
from typing import Callable
from django.core.cache import cache, caches
from django.http import JsonResponse, HttpResponse
from django.conf import settings
from django.contrib.auth.models import User
from django.utils import timezone
from core.models import UserAPIKey
import json

logger = logging.getLogger(__name__)
security_logger = logging.getLogger('security')


class RequestLoggingMiddleware:
    """
    Enhanced middleware to log all API requests and responses with security focus.
    """

    def __init__(self, get_response: Callable):
        self.get_response = get_response
        self.sensitive_headers = {
            'authorization', 'x-api-key', 'cookie', 'x-csrftoken'
        }
        self.sensitive_paths = {
            '/api/accounts/login', '/api/accounts/register', 
            '/api/trading/orders', '/api/arbitrage/execute'
        }

    def __call__(self, request):
        # Generate request ID
        request.id = str(uuid.uuid4())
        
        # Start timer
        start_time = time.time()
        
        # Get client info
        client_ip = self.get_client_ip(request)
        user_agent = request.META.get('HTTP_USER_AGENT', '')[:200]
        
        # Check for suspicious patterns
        if self.is_suspicious_request(request, client_ip, user_agent):
            security_logger.warning(
                f"Suspicious request {request.id} from {client_ip}: "
                f"{request.method} {request.path}"
            )
        
        # Log request (without sensitive data)
        if request.path.startswith('/api/'):
            log_data = {
                'request_id': request.id,
                'method': request.method,
                'path': request.path,
                'ip': client_ip,
                'user_agent': user_agent[:100],
                'content_type': request.content_type,
            }
            
            # Add user info if authenticated
            if hasattr(request, 'user') and request.user.is_authenticated:
                log_data['user'] = request.user.username
            
            logger.info(f"API Request: {json.dumps(log_data)}")
        
        # Process request
        response = self.get_response(request)
        
        # Calculate duration
        duration = time.time() - start_time
        
        # Log response
        if request.path.startswith('/api/'):
            response_data = {
                'request_id': request.id,
                'status': response.status_code,
                'duration': round(duration, 3),
                'size': len(response.content) if hasattr(response, 'content') else 0
            }
            
            # Log errors and slow requests
            if response.status_code >= 400:
                logger.warning(f"API Error: {json.dumps(response_data)}")
            elif duration > 2.0:  # Slow request
                logger.warning(f"Slow API Request: {json.dumps(response_data)}")
            else:
                logger.info(f"API Response: {json.dumps(response_data)}")
        
        # Add headers
        response["X-Request-ID"] = request.id
        response["X-Response-Time"] = f"{duration:.3f}"
        
        return response

    def get_client_ip(self, request):
        """Get the client's real IP address."""
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            # Take the first IP (original client)
            ip = x_forwarded_for.split(",")[0].strip()
        else:
            ip = request.META.get("REMOTE_ADDR")
        return ip

    def is_suspicious_request(self, request, client_ip, user_agent):
        """Detect potentially suspicious requests."""
        # Check for common attack patterns
        suspicious_patterns = [
            'sqlmap', 'nmap', 'nikto', 'dirb', 'gobuster',
            'burpsuite', 'owasp', 'python-requests'
        ]
        
        if any(pattern in user_agent.lower() for pattern in suspicious_patterns):
            return True
        
        # Check for SQL injection attempts in query params
        query_string = request.META.get('QUERY_STRING', '').lower()
        sql_patterns = ['union', 'select', 'drop', 'insert', 'delete', "'", '"']
        if any(pattern in query_string for pattern in sql_patterns):
            return True
        
        # Check for excessive requests from same IP
        cache_key = f"request_count:{client_ip}"
        request_count = cache.get(cache_key, 0)
        if request_count > 100:  # More than 100 requests per minute
            return True
        
        return False


class EnhancedRateLimitMiddleware:
    """
    FIXED: Enhanced rate limiting middleware with per-endpoint and per-user limits.
    """

    def __init__(self, get_response: Callable):
        self.get_response = get_response
        self.rate_cache = caches['rate_limit']
        
        # Different rate limits for different endpoint types
        self.endpoint_limits = getattr(settings, 'API_RATE_LIMITS', {
            'market_data': (2000, 3600),    # 2000 per hour
            'trading': (500, 3600),         # 500 per hour
            'arbitrage': (100, 3600),       # 100 per hour
            'admin': (50, 3600),           # 50 per hour
            'public': (1000, 3600),        # 1000 per hour
        })

    def __call__(self, request):
        # Skip rate limiting for admin and static files
        if request.path.startswith("/admin/") or request.path.startswith("/static/"):
            return self.get_response(request)
        
        # Only rate limit API endpoints
        if not request.path.startswith("/api/"):
            return self.get_response(request)
        
        # Determine endpoint type and get appropriate limits
        endpoint_type = self.get_endpoint_type(request.path)
        rate_limit, window = self.endpoint_limits.get(endpoint_type, (1000, 3600))
        
        # Get client identifier
        client_id = self.get_client_identifier(request)
        
        # Check rate limit
        if self.is_rate_limited(client_id, endpoint_type, rate_limit, window):
            security_logger.warning(
                f"Rate limit exceeded for {client_id} on {endpoint_type} endpoint"
            )
            return JsonResponse(
                {
                    "error": "Rate limit exceeded",
                    "message": f"Maximum {rate_limit} requests per hour allowed for {endpoint_type} endpoints",
                    "retry_after": window
                },
                status=429
            )
        
        # Process request
        response = self.get_response(request)
        
        # Add rate limit headers
        remaining = self.get_remaining_requests(client_id, endpoint_type, rate_limit, window)
        response["X-RateLimit-Limit"] = str(rate_limit)
        response["X-RateLimit-Remaining"] = str(remaining)
        response["X-RateLimit-Reset"] = str(int(time.time()) + window)
        response["X-RateLimit-Type"] = endpoint_type
        
        return response

    def get_endpoint_type(self, path):
        """Determine the endpoint type based on the path."""
        if '/market' in path or '/ticker' in path or '/orderbook' in path:
            return 'market_data'
        elif '/trading' in path or '/orders' in path:
            return 'trading'
        elif '/arbitrage' in path:
            return 'arbitrage'
        elif '/admin' in path:
            return 'admin'
        else:
            return 'public'

    def get_client_identifier(self, request):
        """Get client identifier for rate limiting."""
        # Use API key if present
        api_key = request.META.get('HTTP_X_API_KEY')
        if api_key:
            return f"api_key:{api_key[:10]}"  # Use first 10 chars for privacy
        
        # Use authenticated user
        if hasattr(request, 'user') and request.user.is_authenticated:
            return f"user:{request.user.id}"
        
        # Fall back to IP address
        return f"ip:{self.get_client_ip(request)}"

    def get_client_ip(self, request):
        """Get the client's IP address."""
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            ip = x_forwarded_for.split(",")[0].strip()
        else:
            ip = request.META.get("REMOTE_ADDR")
        return ip

    def is_rate_limited(self, client_id, endpoint_type, limit, window):
        """Check if client has exceeded rate limit."""
        cache_key = f"rate_limit:{client_id}:{endpoint_type}"
        
        # Get current count
        current_count = self.rate_cache.get(cache_key, 0)
        
        if current_count >= limit:
            return True
        
        # Increment counter
        try:
            self.rate_cache.set(cache_key, current_count + 1, window)
        except Exception as e:
            logger.error(f"Error updating rate limit cache: {e}")
            # Allow request if cache fails
            return False
        
        return False

    def get_remaining_requests(self, client_id, endpoint_type, limit, window):
        """Get remaining requests for client."""
        cache_key = f"rate_limit:{client_id}:{endpoint_type}"
        current_count = self.rate_cache.get(cache_key, 0)
        return max(0, limit - current_count)


class APIKeyAuthenticationMiddleware:
    """
    NEW: Middleware to authenticate API requests using API keys.
    """

    def __init__(self, get_response: Callable):
        self.get_response = get_response

    def __call__(self, request):
        # Only check API endpoints
        if not request.path.startswith("/api/"):
            return self.get_response(request)
        
        # Skip authentication for public endpoints
        public_endpoints = [
            '/api/exchanges/',
            '/api/analytics/overview',
            '/api/docs',
        ]
        
        if any(request.path.startswith(endpoint) for endpoint in public_endpoints):
            return self.get_response(request)
        
        # Check for API key
        api_key = request.META.get('HTTP_X_API_KEY')
        if api_key:
            user = self.authenticate_api_key(request, api_key)
            if user:
                request.user = user
            else:
                security_logger.warning(
                    f"Invalid API key attempt from {self.get_client_ip(request)}: {api_key[:10]}..."
                )
                return JsonResponse(
                    {"error": "Invalid API key"},
                    status=401
                )
        
        return self.get_response(request)

    def authenticate_api_key(self, request, api_key):
        """Authenticate user by API key."""
        try:
            # Hash the provided key
            key_hash = hashlib.sha256(api_key.encode()).hexdigest()
            
            # Find the API key
            api_key_obj = UserAPIKey.objects.select_related('user').get(
                key_hash=key_hash,
                is_active=True
            )
            
            # Check if key is valid
            if not api_key_obj.is_valid():
                return None
            
            # Check IP whitelist
            if api_key_obj.ip_whitelist:
                client_ip = self.get_client_ip(request)
                if client_ip not in api_key_obj.ip_whitelist:
                    security_logger.warning(
                        f"API key access denied for IP {client_ip}, key: {api_key[:10]}..."
                    )
                    return None
            
            # Update usage stats
            api_key_obj.last_used = timezone.now()
            api_key_obj.usage_count += 1
            api_key_obj.save(update_fields=['last_used', 'usage_count'])
            
            return api_key_obj.user
            
        except UserAPIKey.DoesNotExist:
            return None
        except Exception as e:
            logger.error(f"Error authenticating API key: {e}")
            return None

    def get_client_ip(self, request):
        """Get the client's IP address."""
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            ip = x_forwarded_for.split(",")[0].strip()
        else:
            ip = request.META.get("REMOTE_ADDR")
        return ip


class SecurityHeadersMiddleware:
    """
    ENHANCED: Middleware to add comprehensive security headers.
    """

    def __init__(self, get_response: Callable):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        
        # Basic security headers
        response["X-Content-Type-Options"] = "nosniff"
        response["X-Frame-Options"] = "DENY"
        response["X-XSS-Protection"] = "1; mode=block"
        response["Referrer-Policy"] = "strict-origin-when-cross-origin"
        
        # HSTS for HTTPS
        if request.is_secure():
            response["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains; preload"
        
        # Content Security Policy for API endpoints
        if request.path.startswith("/api/"):
            response["Content-Security-Policy"] = (
                "default-src 'none'; "
                "script-src 'none'; "
                "style-src 'none'; "
                "img-src 'none'; "
                "connect-src 'self'; "
                "font-src 'none'; "
                "object-src 'none'; "
                "media-src 'none'; "
                "frame-src 'none';"
            )
        elif not request.path.startswith("/admin/"):
            # More restrictive CSP for non-admin pages
            response["Content-Security-Policy"] = (
                "default-src 'self'; "
                "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdnjs.cloudflare.com; "
                "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
                "font-src 'self' https://fonts.gstatic.com; "
                "img-src 'self' data: https:; "
                "connect-src 'self' https://api.nobitex.ir https://api.wallex.ir https://api.ramzinex.com; "
                "frame-ancestors 'none';"
            )
        
        # Additional security headers for API
        if request.path.startswith("/api/"):
            response["X-API-Version"] = "1.0"
            response["Cache-Control"] = "no-store, no-cache, must-revalidate, private"
            response["Pragma"] = "no-cache"
        
        return response


class MaintenanceModeMiddleware:
    """
    ENHANCED: Middleware to enable maintenance mode with bypass for admins.
    """

    def __init__(self, get_response: Callable):
        self.get_response = get_response

    def __call__(self, request):
        # Check if maintenance mode is enabled
        maintenance_mode = cache.get("maintenance_mode", False)
        
        if maintenance_mode:
            # Allow access to admin and health check
            allowed_paths = ["/admin/", "/health/", "/api/health/"]
            
            if not any(request.path.startswith(path) for path in allowed_paths):
                # Allow staff users to bypass
                if hasattr(request, 'user') and request.user.is_authenticated and request.user.is_staff:
                    pass
                else:
                    # Return maintenance response
                    if request.path.startswith("/api/"):
                        return JsonResponse(
                            {
                                "error": "Maintenance Mode",
                                "message": "The system is currently under maintenance. Please try again later.",
                                "retry_after": 300  # 5 minutes
                            },
                            status=503
                        )
                    else:
                        return HttpResponse(
                            "System under maintenance. Please try again later.",
                            status=503,
                            content_type="text/plain"
                        )
        
        return self.get_response(request)


class SecurityMonitoringMiddleware:
    """
    NEW: Middleware for security monitoring and threat detection.
    """

    def __init__(self, get_response: Callable):
        self.get_response = get_response

    def __call__(self, request):
        # Monitor for security threats
        self.check_for_threats(request)
        
        response = self.get_response(request)
        
        # Log security events
        if response.status_code in [401, 403, 429]:
            self.log_security_event(request, response)
        
        return response

    def check_for_threats(self, request):
        """Check for common security threats."""
        client_ip = self.get_client_ip(request)
        
        # Check for brute force attacks
        if request.path in ['/api/accounts/login', '/admin/login/']:
            self.check_brute_force(client_ip)
        
        # Check for suspicious user agents
        user_agent = request.META.get('HTTP_USER_AGENT', '').lower()
        suspicious_agents = ['bot', 'crawler', 'spider', 'scraper']
        if any(agent in user_agent for agent in suspicious_agents) and request.path.startswith('/api/'):
            security_logger.warning(
                f"Suspicious user agent accessing API from {client_ip}: {user_agent[:100]}"
            )
        
        # Check for abnormal request patterns
        self.check_request_pattern(client_ip)

    def check_brute_force(self, client_ip):
        """Check for brute force login attempts."""
        cache_key = f"login_attempts:{client_ip}"
        attempts = cache.get(cache_key, 0)
        
        if attempts >= 5:  # More than 5 attempts
            security_logger.error(
                f"Potential brute force attack from {client_ip}: {attempts} attempts"
            )
            # Could implement IP blocking here

    def check_request_pattern(self, client_ip):
        """Check for abnormal request patterns."""
        cache_key = f"request_pattern:{client_ip}"
        pattern = cache.get(cache_key, [])
        
        # Add current timestamp
        current_time = int(time.time())
        pattern.append(current_time)
        
        # Keep only last 100 requests
        pattern = pattern[-100:]
        
        # Check for rapid requests (more than 50 in 60 seconds)
        recent_requests = [t for t in pattern if current_time - t <= 60]
        if len(recent_requests) > 50:
            security_logger.warning(
                f"Rapid requests detected from {client_ip}: {len(recent_requests)} in 60 seconds"
            )
        
        # Update cache
        cache.set(cache_key, pattern, 300)  # 5 minutes

    def log_security_event(self, request, response):
        """Log security-related events."""
        client_ip = self.get_client_ip(request)
        event_data = {
            'ip': client_ip,
            'path': request.path,
            'method': request.method,
            'status': response.status_code,
            'user_agent': request.META.get('HTTP_USER_AGENT', '')[:200],
            'timestamp': timezone.now().isoformat()
        }
        
        if hasattr(request, 'user') and request.user.is_authenticated:
            event_data['user'] = request.user.username
        
        security_logger.warning(f"Security event: {json.dumps(event_data)}")

    def get_client_ip(self, request):
        """Get the client's IP address."""
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            ip = x_forwarded_for.split(",")[0].strip()
        else:
            ip = request.META.get("REMOTE_ADDR")
        return ip