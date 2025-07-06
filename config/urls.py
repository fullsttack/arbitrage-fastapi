"""
URL configuration for Crypto Arbitrage project.
"""

from django.contrib import admin
from django.urls import path
from ninja import NinjaAPI

from accounts.api import router as accounts_router
from analytics.api import router as analytics_router
from arbitrage.api import router as arbitrage_router
from exchanges.api import router as exchanges_router
from trading.api import router as trading_router

# Create the main API instance
api = NinjaAPI(
    title="Crypto Arbitrage API",
    version="1.0.0",
    description="API for monitoring and executing cryptocurrency arbitrage opportunities",
)

# Add routers to the API
api.add_router("/accounts/", accounts_router, tags=["Accounts"])
api.add_router("/exchanges/", exchanges_router, tags=["Exchanges"])
api.add_router("/arbitrage/", arbitrage_router, tags=["Arbitrage"])
api.add_router("/trading/", trading_router, tags=["Trading"])
api.add_router("/analytics/", analytics_router, tags=["Analytics"])

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", api.urls),
]