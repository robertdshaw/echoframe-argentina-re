"""
FastAPI application entry point for EchoFrame Argentina Real Estate Intelligence.

Main application module that configures FastAPI, registers routes, sets up middleware,
and initializes the forecasting and signal processing systems.
"""

import logging
from contextlib import asynccontextmanager
from datetime import datetime
import asyncio
import sys
import os

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.openapi.utils import get_openapi

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import settings
from api import (
    forecast_router,
    signals_router,
    market_router,
    scenarios_router,
    model_router,
    narrative_router,
)
from services.data_pipeline import DataPipeline
from services.forecast_service import ForecastService
from services.signal_service import SignalService


logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.
    
    Handles startup and shutdown tasks including model initialization,
    data pipeline setup, and graceful resource cleanup.
    """
    # Startup
    logger.info("Starting EchoFrame Argentina RE Intelligence API")
    
    try:
        # Initialize core services
        logger.info("Initializing data pipeline...")
        app.state.data_pipeline = DataPipeline()
        
        logger.info("Initializing forecast service...")
        app.state.forecast_service = ForecastService(app.state.data_pipeline)
        
        logger.info("Initializing signal service...")
        app.state.signal_service = SignalService(app.state.data_pipeline)
        
        # Warm up models and cache key data
        if settings.enable_live_apis:
            logger.info("Warming up with live data...")
            try:
                # Pre-fetch macro indicators to warm up cache
                await app.state.data_pipeline.get_macro_indicators()
                logger.info("Live data cache warmed up successfully")
            except Exception as e:
                logger.warning(f"Failed to warm up live data cache: {e}")
        
        # Pre-load some seed data
        logger.info("Pre-loading seed data...")
        try:
            await app.state.data_pipeline.get_news_signals(limit=20)
            await app.state.data_pipeline.get_property_listings(segment="departamentos", limit=10)
            logger.info("Seed data pre-loaded successfully")
        except Exception as e:
            logger.warning(f"Failed to pre-load seed data: {e}")
        
        # Pre-compute and cache the two forecast shapes the dashboard hits
        # most often. Five of the departamentos page's endpoints
        # (forecast, barrio-rankings, net-return, scenarios, narrative)
        # all share the same year_horizons=[1,2,3] cache key — with the
        # cache warmed here, the first user request returns from cache
        # instead of triggering a 5-way parallel data-pipeline race.
        if settings.enable_regime_detection:
            logger.info("Pre-fetching dashboard-critical forecasts...")
            try:
                await asyncio.gather(
                    app.state.forecast_service.generate_departamentos_forecast(
                        barrio=None, year_horizons=[1, 2, 3]
                    ),
                    app.state.forecast_service.generate_campos_forecast(
                        zone=None, year_horizons=[1, 2, 3]
                    ),
                    return_exceptions=True,
                )
                logger.info("Dashboard forecasts cached; first user request will return instantly")
            except Exception as e:
                logger.warning(f"Failed to pre-fetch dashboard forecasts: {e}")
        
        logger.info("Application startup completed successfully")
        
        yield
        
    except Exception as e:
        logger.error(f"Critical error during startup: {e}")
        raise
    
    # Shutdown
    logger.info("Shutting down EchoFrame Argentina RE Intelligence API")
    
    # Cleanup resources
    try:
        if hasattr(app.state, 'data_pipeline'):
            # Clear caches
            app.state.data_pipeline._cache.clear()
            logger.info("Data pipeline cache cleared")
        
        if hasattr(app.state, 'forecast_service'):
            app.state.forecast_service._model_cache.clear()
            logger.info("Model cache cleared")
            
        if hasattr(app.state, 'signal_service'):
            app.state.signal_service._signal_cache.clear()
            logger.info("Signal cache cleared")
        
    except Exception as e:
        logger.error(f"Error during shutdown: {e}")
    
    logger.info("Application shutdown completed")


# Create FastAPI application
app = FastAPI(
    lifespan=lifespan,
    **settings.get_api_metadata()
)

# Add middleware

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    **settings.get_cors_settings()
)

# Gzip compression middleware
app.add_middleware(GZipMiddleware, minimum_size=1000)


# HTTP browser-cache headers for the read-only dashboard endpoints.
# A 60-second cache lets the browser serve repeats during a page
# refresh / back-navigation without re-hitting the backend, which is
# the largest contributor to perceived load time after a cold start.
# Mutating endpoints (POST scenarios, POST narrative) get no-store.
_BROWSER_CACHE_PREFIXES = (
    "/api/v1/forecast/",
    "/api/v1/market/",
    "/api/v1/signals/",
    "/api/v1/model/",
)

_BROWSER_CACHE_MAX_AGE = 60  # seconds


@app.middleware("http")
async def add_cache_control(request, call_next):
    """Attach Cache-Control headers tuned per endpoint family."""
    response = await call_next(request)
    # Only cache successful GETs from the read-only API surface.
    if request.method != "GET":
        response.headers.setdefault("Cache-Control", "no-store")
        return response
    if response.status_code >= 400:
        return response
    path = request.url.path
    if any(path.startswith(p) for p in _BROWSER_CACHE_PREFIXES):
        response.headers["Cache-Control"] = (
            f"public, max-age={_BROWSER_CACHE_MAX_AGE}, "
            f"stale-while-revalidate={_BROWSER_CACHE_MAX_AGE * 4}"
        )
    return response


# Custom exception handlers

@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """Handle HTTP exceptions with structured error responses."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.status_code,
                "message": exc.detail,
                "type": "http_error",
                "timestamp": datetime.utcnow().isoformat()
            }
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """Handle unexpected exceptions with generic error response."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    
    # Don't expose internal error details in production
    if settings.is_production():
        detail = "Internal server error"
    else:
        detail = str(exc)
    
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": 500,
                "message": detail,
                "type": "internal_error",
                "timestamp": datetime.utcnow().isoformat()
            }
        }
    )


# Register API routes
app.include_router(forecast_router)
app.include_router(signals_router)
app.include_router(market_router)
app.include_router(model_router)
app.include_router(narrative_router)

if settings.enable_scenario_analysis:
    app.include_router(scenarios_router)


# Root endpoints

@app.get("/", tags=["root"])
async def root():
    """
    API root endpoint.
    
    Returns basic API information and status.
    """
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "environment": settings.environment,
        "status": "operational",
        "timestamp": datetime.utcnow().isoformat(),
        "endpoints": {
            "forecasts": "/api/v1/forecast/",
            "signals": "/api/v1/signals/",
            "market_data": "/api/v1/market/",
            "scenarios": "/api/v1/scenarios/",
            "health": "/health",
            "docs": "/docs",
            "openapi": "/openapi.json"
        },
        "features": {
            "live_apis_enabled": settings.enable_live_apis,
            "nlp_processing_enabled": settings.enable_nlp_processing,
            "behavioral_adjustments_enabled": settings.enable_behavioral_adjustments,
            "scenario_analysis_enabled": settings.enable_scenario_analysis
        }
    }


@app.get("/health", tags=["monitoring"])
async def health_check():
    """
    Health check endpoint for monitoring and load balancers.
    
    Returns detailed health information about all system components.
    """
    try:
        health_status = {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "version": settings.app_version,
            "environment": settings.environment,
            "uptime_check": "ok"
        }
        
        # Check data pipeline health
        if hasattr(app.state, 'data_pipeline'):
            try:
                freshness_status = await app.state.data_pipeline.get_data_freshness_status()
                stale_sources = sum(1 for status in freshness_status.values() if status.is_stale)
                
                health_status["data_pipeline"] = {
                    "status": "degraded" if stale_sources > 0 else "healthy",
                    "total_sources": len(freshness_status),
                    "stale_sources": stale_sources
                }
            except Exception as e:
                health_status["data_pipeline"] = {"status": "error", "error": str(e)}
        
        # Check forecast service health
        if hasattr(app.state, 'forecast_service'):
            try:
                # Quick health check - this should be fast
                summary = await app.state.forecast_service.get_forecast_summary()
                health_status["forecast_service"] = {
                    "status": "healthy" if summary else "degraded",
                    "cache_size": len(app.state.forecast_service._model_cache)
                }
            except Exception as e:
                health_status["forecast_service"] = {"status": "error", "error": str(e)}
        
        # Check signal service health
        if hasattr(app.state, 'signal_service'):
            try:
                # Basic signal service check
                signals = await app.state.signal_service.process_latest_signals(limit=1)
                health_status["signal_service"] = {
                    "status": "healthy" if signals else "degraded",
                    "cache_size": len(app.state.signal_service._signal_cache)
                }
            except Exception as e:
                health_status["signal_service"] = {"status": "error", "error": str(e)}
        
        # External API health
        health_status["external_apis"] = {
            "bcra": {"url": settings.bcra_api_base_url, "enabled": settings.enable_live_apis},
            "rem": {"url": settings.rem_api_base_url, "enabled": settings.enable_live_apis}
        }
        
        # Overall status determination
        component_statuses = [
            health_status.get("data_pipeline", {}).get("status", "unknown"),
            health_status.get("forecast_service", {}).get("status", "unknown"),
            health_status.get("signal_service", {}).get("status", "unknown")
        ]
        
        if any(status == "error" for status in component_statuses):
            health_status["status"] = "unhealthy"
        elif any(status == "degraded" for status in component_statuses):
            health_status["status"] = "degraded"
        
        return health_status
        
    except Exception as e:
        logger.error(f"Health check error: {e}")
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
        )


@app.get("/version", tags=["monitoring"])
async def version_info():
    """
    Get detailed version and build information.
    
    Returns version, build time, configuration, and feature flags.
    """
    return {
        "version": settings.app_version,
        "environment": settings.environment,
        "build_info": {
            "python_version": sys.version,
            "fastapi_version": "0.115.0",  # Would be dynamically imported in real app
            "build_timestamp": "2026-01-15T10:00:00Z"  # Would be set during build
        },
        "configuration": {
            "debug_mode": settings.debug,
            "cors_origins": settings.cors_origins,
            "api_prefix": settings.api_prefix,
            "cache_enabled": settings.cache_enabled,
            "max_workers": settings.max_workers
        },
        "feature_flags": {
            "live_apis": settings.enable_live_apis,
            "nlp_processing": settings.enable_nlp_processing,
            "regime_detection": settings.enable_regime_detection,
            "behavioral_adjustments": settings.enable_behavioral_adjustments,
            "scenario_analysis": settings.enable_scenario_analysis
        },
        "model_settings": {
            "hmm_states": settings.hmm_n_states,
            "prospect_theory_lambda": settings.prospect_theory_lambda,
            "cache_ttl_minutes": settings.model_cache_ttl_minutes
        }
    }


# Custom OpenAPI schema
def custom_openapi():
    """Generate custom OpenAPI schema with enhanced documentation."""
    if app.openapi_schema:
        return app.openapi_schema
    
    openapi_schema = get_openapi(
        title=settings.app_name,
        version=settings.app_version,
        description=settings.get_api_metadata()["description"],
        routes=app.routes,
        tags=settings.get_api_metadata()["tags_metadata"]
    )
    
    # Add custom schema elements
    openapi_schema["info"]["contact"] = settings.get_api_metadata()["contact"]
    openapi_schema["info"]["license"] = settings.get_api_metadata()["license_info"]
    
    # Add server information
    openapi_schema["servers"] = [
        {
            "url": f"http://{settings.api_host}:{settings.api_port}",
            "description": f"EchoFrame API ({settings.environment})"
        }
    ]
    
    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi


# Application startup logging
@app.on_event("startup") 
async def startup_logging():
    """Log application startup information."""
    logger.info("=" * 60)
    logger.info("EchoFrame Argentina Real Estate Intelligence API")
    logger.info("=" * 60)
    logger.info(f"Version: {settings.app_version}")
    logger.info(f"Environment: {settings.environment}")
    logger.info(f"Host: {settings.api_host}:{settings.api_port}")
    logger.info(f"Debug Mode: {settings.debug}")
    logger.info(f"Live APIs: {settings.enable_live_apis}")
    logger.info(f"NLP Processing: {settings.enable_nlp_processing}")
    logger.info(f"Behavioral Adjustments: {settings.enable_behavioral_adjustments}")
    logger.info("=" * 60)


if __name__ == "__main__":
    import uvicorn
    
    logger.info(f"Starting server on {settings.api_host}:{settings.api_port}")
    
    uvicorn.run(
        "main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.debug,
        log_level=settings.log_level.lower(),
        workers=1 if settings.debug else settings.max_workers,
        access_log=settings.debug,
        keepalive_timeout=settings.keepalive_timeout
    )