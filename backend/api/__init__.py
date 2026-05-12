"""
FastAPI routes and schemas for EchoFrame Argentina Real Estate Intelligence API.

This module provides RESTful API endpoints for accessing forecasting models,
market signals, and scenario analysis capabilities.
"""

from .routes_forecast import router as forecast_router
from .routes_signals import router as signals_router
from .routes_market import router as market_router
from .routes_scenarios import router as scenarios_router
from .routes_model import router as model_router
from .routes_narrative import router as narrative_router
from .schemas import *

__all__ = [
    "forecast_router",
    "signals_router",
    "market_router",
    "scenarios_router",
    "model_router",
    "narrative_router",
]