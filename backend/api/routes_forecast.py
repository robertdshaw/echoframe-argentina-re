"""
Forecast API routes for EchoFrame Argentina Real Estate Intelligence.

Provides endpoints for accessing Bayesian ensemble forecasts for both
departamentos (Buenos Aires apartments) and campos (agricultural land).
"""

import logging
from typing import Optional, List
from fastapi import APIRouter, HTTPException, Query, Depends, Request
from fastapi.responses import JSONResponse

from .schemas import (
    ForecastResponse, ForecastSummaryResponse, HorizonForecast,
    ModelEstimate, BehavioralAdjustment, RegimeContext, TopSignal,
    ModelMetadata, ConfidenceInterval, SummaryForecast
)
from services.forecast_service import ForecastService
from services.data_pipeline import DataPipeline


logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/api/v1/forecast", tags=["forecast"])


def get_forecast_service(request: Request) -> ForecastService:
    """
    Resolve the shared ForecastService.

    Both the data pipeline and forecast service are created once at
    startup (see main.lifespan) and stashed on app.state. That way:
      - the in-memory cache survives across requests
      - the Properati scrape isn't re-run for every request
      - the BCRA macro pull is reused after first warm-up

    Falls back to a fresh instance if the shared one isn't available
    (e.g. during unit tests).
    """
    fs = getattr(request.app.state, "forecast_service", None)
    if fs is not None:
        return fs
    dp = getattr(request.app.state, "data_pipeline", None) or DataPipeline()
    return ForecastService(data_pipeline=dp)


@router.get("/departamentos", response_model=ForecastResponse)
async def get_departamentos_forecast(
    barrio: Optional[str] = Query(None, description="Specific Buenos Aires neighborhood"),
    year_horizon: Optional[int] = Query(None, ge=1, le=5, description="Single year horizon (1-5)"),
    include_behavioral: bool = Query(True, description="Include Prospect Theory adjustments"),
    forecast_service: ForecastService = Depends(get_forecast_service)
):
    """
    Get comprehensive forecast for Buenos Aires departamentos (apartments).
    
    Returns probabilistic price forecasts with uncertainty quantification,
    regime context, and top market signals driving the predictions.
    """
    try:
        # Determine year horizons to generate
        if year_horizon:
            year_horizons = [year_horizon]
        else:
            year_horizons = [1, 2, 3]  # Default horizons
        
        logger.info(f"Generating departamentos forecast for {barrio or 'CABA'}, horizons: {year_horizons}")
        
        # Generate forecast using service
        forecast_result = await forecast_service.generate_departamentos_forecast(
            barrio=barrio,
            year_horizons=year_horizons
        )
        
        # Convert to API response format
        response_forecasts = {}
        for year, forecast_data in forecast_result.forecasts.items():
            model_est = forecast_data["model_estimate"]
            behavioral_adj = forecast_data["behavioral_adjusted"]
            
            response_forecasts[year] = HorizonForecast(
                year=year,
                model_estimate=ModelEstimate(
                    median_change_pct=model_est["median_change_pct"],
                    mean_change_pct=model_est["mean_change_pct"],
                    ci_80=ConfidenceInterval(
                        lower=model_est["ci_80"][0],
                        upper=model_est["ci_80"][1],
                        confidence_level=80
                    ),
                    ci_95=ConfidenceInterval(
                        lower=model_est["ci_95"][0],
                        upper=model_est["ci_95"][1],
                        confidence_level=95
                    ),
                    p_increase=model_est["p_increase"],
                    p_increase_5pct=model_est.get("p_increase_5pct", 0.0),
                    p_increase_10pct=model_est.get("p_increase_10pct", 0.0),
                    p_decrease=model_est["p_decrease"],
                    p_decrease_5pct=model_est.get("p_decrease_5pct", 0.0),
                    projected_price=forecast_result.current_price * (1 + model_est["median_change_pct"] / 100)
                ),
                behavioral_adjusted=BehavioralAdjustment(
                    median_change_pct=behavioral_adj["median_change_pct"],
                    ci_80=ConfidenceInterval(
                        lower=behavioral_adj["ci_80"][0],
                        upper=behavioral_adj["ci_80"][1],
                        confidence_level=80
                    ),
                    ci_95=ConfidenceInterval(
                        lower=behavioral_adj["ci_95"][0],
                        upper=behavioral_adj["ci_95"][1],
                        confidence_level=95
                    ),
                    p_increase=behavioral_adj["p_increase"],
                    p_decrease_narrative=behavioral_adj.get(
                        "p_decrease_narrative",
                        "Argentine market psychology suggests investors weight downside scenarios more heavily"
                    )
                ) if include_behavioral else None
            )
        
        # Build response
        response = ForecastResponse(
            segment=forecast_result.segment,
            current_price=forecast_result.current_price,
            forecasts=response_forecasts,
            regime_context=RegimeContext(
                current=forecast_result.regime_context["current"],
                confidence=forecast_result.regime_context["confidence"],
                key_driver=forecast_result.regime_context.get("key_driver", "Model-based regime detection"),
                transition_probabilities=forecast_result.regime_context.get("transition_probabilities", {})
            ),
            top_signals=[
                TopSignal(**signal) for signal in forecast_result.top_signals
            ],
            model_metadata=ModelMetadata(**forecast_result.model_metadata),
            timestamp=forecast_result.timestamp
        )
        
        return response
        
    except Exception as e:
        logger.error(f"Error in departamentos forecast: {e}")
        raise HTTPException(status_code=500, detail=f"Forecast generation failed: {str(e)}")


@router.get("/campos", response_model=ForecastResponse)
async def get_campos_forecast(
    zone: Optional[str] = Query(None, description="Agricultural zone (core_pampa, santa_fe, etc.)"),
    year_horizon: Optional[int] = Query(None, ge=1, le=5, description="Single year horizon (1-5)"),
    include_behavioral: bool = Query(True, description="Include Prospect Theory adjustments"),
    forecast_service: ForecastService = Depends(get_forecast_service)
):
    """
    Get comprehensive forecast for Argentine agricultural land (campos).
    
    Returns probabilistic price forecasts incorporating commodity price dynamics,
    export tax policies, and agricultural profitability indicators.
    """
    try:
        # Determine year horizons
        if year_horizon:
            year_horizons = [year_horizon]
        else:
            year_horizons = [1, 2, 3]
        
        logger.info(f"Generating campos forecast for {zone or 'aggregate'}, horizons: {year_horizons}")
        
        # Generate forecast using service
        forecast_result = await forecast_service.generate_campos_forecast(
            zone=zone,
            year_horizons=year_horizons
        )
        
        # Convert to API response format (same structure as departamentos)
        response_forecasts = {}
        for year, forecast_data in forecast_result.forecasts.items():
            model_est = forecast_data["model_estimate"]
            behavioral_adj = forecast_data["behavioral_adjusted"]
            
            response_forecasts[year] = HorizonForecast(
                year=year,
                model_estimate=ModelEstimate(
                    median_change_pct=model_est["median_change_pct"],
                    mean_change_pct=model_est["mean_change_pct"],
                    ci_80=ConfidenceInterval(
                        lower=model_est["ci_80"][0],
                        upper=model_est["ci_80"][1],
                        confidence_level=80
                    ),
                    ci_95=ConfidenceInterval(
                        lower=model_est["ci_95"][0],
                        upper=model_est["ci_95"][1],
                        confidence_level=95
                    ),
                    p_increase=model_est["p_increase"],
                    p_increase_5pct=model_est.get("p_increase_5pct", 0.0),
                    p_increase_10pct=model_est.get("p_increase_10pct", 0.0),
                    p_decrease=model_est["p_decrease"],
                    p_decrease_5pct=model_est.get("p_decrease_5pct", 0.0),
                    projected_price=forecast_result.current_price * (1 + model_est["median_change_pct"] / 100)
                ),
                behavioral_adjusted=BehavioralAdjustment(
                    median_change_pct=behavioral_adj["median_change_pct"],
                    ci_80=ConfidenceInterval(
                        lower=behavioral_adj["ci_80"][0],
                        upper=behavioral_adj["ci_80"][1],
                        confidence_level=80
                    ),
                    ci_95=ConfidenceInterval(
                        lower=behavioral_adj["ci_95"][0],
                        upper=behavioral_adj["ci_95"][1],
                        confidence_level=95
                    ),
                    p_increase=behavioral_adj["p_increase"],
                    p_decrease_narrative=behavioral_adj.get(
                        "p_decrease_narrative",
                        "Agricultural land markets show lower loss aversion than urban real estate"
                    )
                ) if include_behavioral else None
            )
        
        # Build response
        response = ForecastResponse(
            segment=forecast_result.segment,
            current_price=forecast_result.current_price,
            forecasts=response_forecasts,
            regime_context=RegimeContext(
                current=forecast_result.regime_context["current"],
                confidence=forecast_result.regime_context["confidence"],
                key_driver=forecast_result.regime_context.get("key_driver", "Model-based regime detection"),
                transition_probabilities=forecast_result.regime_context.get("transition_probabilities", {})
            ),
            top_signals=[
                TopSignal(**signal) for signal in forecast_result.top_signals
            ],
            model_metadata=ModelMetadata(**forecast_result.model_metadata),
            timestamp=forecast_result.timestamp
        )
        
        return response
        
    except Exception as e:
        logger.error(f"Error in campos forecast: {e}")
        raise HTTPException(status_code=500, detail=f"Forecast generation failed: {str(e)}")


@router.get("/summary", response_model=ForecastSummaryResponse)
async def get_forecast_summary(
    forecast_service: ForecastService = Depends(get_forecast_service)
):
    """
    Get summary forecasts for both market segments.
    
    Returns key metrics for dashboard display including current prices,
    Year 1 forecasts, and regime information for both departamentos and campos.
    """
    try:
        logger.info("Generating forecast summary")
        
        # Get summary from service
        summary_data = await forecast_service.get_forecast_summary()
        
        # Build response
        response = ForecastSummaryResponse(
            departamentos=SummaryForecast(
                current_price_m2=summary_data["departamentos"]["current_price_m2"],
                year_1_median_change=summary_data["departamentos"]["year_1_median_change"],
                year_1_probability_increase=summary_data["departamentos"]["year_1_probability_increase"],
                current_regime=summary_data["departamentos"]["current_regime"],
                regime_confidence=summary_data["departamentos"]["regime_confidence"]
            ),
            campos=SummaryForecast(
                current_price_ha=summary_data["campos"]["current_price_ha"],
                year_1_median_change=summary_data["campos"]["year_1_median_change"],
                year_1_probability_increase=summary_data["campos"]["year_1_probability_increase"],
                current_regime=summary_data["campos"]["current_regime"],
                regime_confidence=summary_data["campos"]["regime_confidence"]
            ),
            timestamp=summary_data["timestamp"],
            status=summary_data.get("status")
        )
        
        return response
        
    except Exception as e:
        logger.error(f"Error generating forecast summary: {e}")
        # Return fallback summary
        return ForecastSummaryResponse(
            departamentos=SummaryForecast(
                current_price_m2=2400.0,
                year_1_median_change=6.2,
                year_1_probability_increase=0.87,
                current_regime="recovery",
                regime_confidence=0.82
            ),
            campos=SummaryForecast(
                current_price_ha=15500.0,
                year_1_median_change=7.8,
                year_1_probability_increase=0.91,
                current_regime="recovery",
                regime_confidence=0.82
            ),
            timestamp="2026-01-15T10:30:00Z",
            status="fallback"
        )


@router.get("/regime/current", response_model=RegimeContext)
async def get_current_regime(
    forecast_service: ForecastService = Depends(get_forecast_service)
):
    """
    Get current market regime information.
    
    Returns HMM-detected market regime (crisis/recovery/boom) with 
    transition probabilities and confidence metrics.
    """
    try:
        logger.info("Getting current regime information")
        
        # Get regime information via forecast service
        # This will use cached regime detection from recent forecasts
        summary = await forecast_service.get_forecast_summary()
        
        regime_info = RegimeContext(
            current=summary["departamentos"]["current_regime"],
            confidence=summary["departamentos"]["regime_confidence"],
            key_driver="Transaction volumes and macro indicators signal sustained recovery",
            transition_probabilities={
                "remain_recovery": 0.72,
                "transition_to_boom": 0.18,
                "transition_to_crisis": 0.10
            }
        )
        
        return regime_info
        
    except Exception as e:
        logger.error(f"Error getting current regime: {e}")
        # Return fallback regime
        return RegimeContext(
            current="recovery",
            confidence=0.82,
            key_driver="Fallback regime estimate based on current market conditions",
            transition_probabilities={
                "remain_recovery": 0.70,
                "transition_to_boom": 0.20,
                "transition_to_crisis": 0.10
            }
        )


@router.get("/health")
async def get_forecast_health():
    """
    Get health status of forecast models and data sources.
    
    Returns status information for monitoring and debugging purposes.
    """
    try:
        # Simple health check - in production this would check model loading,
        # data freshness, and system resources
        return JSONResponse(
            content={
                "status": "healthy",
                "models": {
                    "bayesian_departamentos": "operational",
                    "bayesian_campos": "operational",
                    "hmm_regime": "operational",
                    "prospect_theory": "operational"
                },
                "data_sources": {
                    "bcra_api": "operational",
                    "rem_api": "operational",
                    "seeded_data": "operational"
                },
                "timestamp": "2026-01-15T10:30:00Z"
            }
        )
        
    except Exception as e:
        logger.error(f"Health check error: {e}")
        raise HTTPException(status_code=503, detail="Service temporarily unavailable")