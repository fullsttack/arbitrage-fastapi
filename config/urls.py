# ===== CONFIG/URLS.PY (Updated) =====

"""
URL configuration for Crypto Arbitrage project.
"""

from django.contrib import admin
from django.urls import path, include
from django.views.generic import RedirectView
from ninja import NinjaAPI

from accounts.api import router as accounts_router
from analytics.api import router as analytics_router
from arbitrage.api import router as arbitrage_router
from exchanges.api import router as exchanges_router
from trading.api import router as trading_router
from core.admin_dashboard import dashboard_stats_api

# Configure admin site
admin.site.site_header = "Crypto Arbitrage Administration"
admin.site.site_title = "Arbitrage Admin"
admin.site.index_title = "Dashboard"

# Create the main API instance
api = NinjaAPI(
    title="Crypto Arbitrage API",
    version="1.0.0",
    description="API for monitoring and executing cryptocurrency arbitrage opportunities",
    docs_url="/api/docs/",
)

# Add routers to the API
api.add_router("/accounts/", accounts_router, tags=["Accounts"])
api.add_router("/exchanges/", exchanges_router, tags=["Exchanges"])
api.add_router("/arbitrage/", arbitrage_router, tags=["Arbitrage"])
api.add_router("/trading/", trading_router, tags=["Trading"])
api.add_router("/analytics/", analytics_router, tags=["Analytics"])

urlpatterns = [
    # Admin interface
    path("admin/", admin.site.urls),
    
    # API endpoints
    path("api/", api.urls),
    
    # Dashboard API for real-time updates
    path("admin/api/dashboard-stats/", dashboard_stats_api, name="dashboard_stats_api"),
    
    # Redirect root to admin for convenience
    path("", RedirectView.as_view(url="/admin/", permanent=False)),
]