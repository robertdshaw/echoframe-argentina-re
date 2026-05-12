"""
Narrative endpoint — Claude-generated executive interpretation.

POST /api/v1/insights/narrative
  Body: { "segment": "departamentos" | "campos", "location"?: string }

Returns:
  {
    "status": "ok" | "unavailable",
    "narrative": "…flowing prose, 4 paragraphs…",
    "model": "claude-sonnet-4-6",
    "generated_at": "2026-05-12T10:23:00Z",
    "reason": "explanation when unavailable"
  }

This is intentionally a POST so the route can read the full forecast
payload (which the frontend already has) without re-running the forecast
service. That keeps cost down: one Claude call per page view, max.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Body, Request
from fastapi.responses import JSONResponse

from services.forecast_service import ForecastService
from services.signal_service import SignalService
from services.data_pipeline import DataPipeline
from services.narrative_service import NarrativeService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/insights", tags=["insights"])

_DIAG = Path(__file__).resolve().parent.parent / "models" / "diagnostics"
_BACKTEST_PATH = _DIAG / "backtest_results.json"

_narrative = NarrativeService()


def _load_backtest() -> Optional[Dict[str, Any]]:
    if not _BACKTEST_PATH.exists():
        return None
    try:
        return json.loads(_BACKTEST_PATH.read_text(encoding="utf-8"))
    except Exception:
        return None


def _forecast_payload(result: Any) -> Dict[str, Any]:
    """Coerce a ForecastResult into a plain dict the narrative service can read."""
    forecasts = {}
    for year, data in (result.forecasts or {}).items():
        forecasts[str(year)] = {
            "model_estimate": {
                "median_change_pct": data["model_estimate"]["median_change_pct"],
                "mean_change_pct": data["model_estimate"]["mean_change_pct"],
                "ci_80": {
                    "lower": data["model_estimate"]["ci_80"][0],
                    "upper": data["model_estimate"]["ci_80"][1],
                },
                "ci_95": {
                    "lower": data["model_estimate"]["ci_95"][0],
                    "upper": data["model_estimate"]["ci_95"][1],
                },
                "p_increase": data["model_estimate"]["p_increase"],
                "p_decrease": data["model_estimate"]["p_decrease"],
                "p_decrease_5pct": data["model_estimate"].get("p_decrease_5pct", 0),
            }
        }
    return {
        "segment": result.segment,
        "current_price": result.current_price,
        "regime_context": result.regime_context,
        "forecasts": forecasts,
    }


@router.post("/narrative")
async def post_narrative(
    request: Request,
    segment: str = Body(..., embed=True, description="departamentos | campos"),
    location: Optional[str] = Body(None, embed=True),
) -> JSONResponse:
    """
    Generate an executive narrative for the current forecast.
    """
    if segment not in ("departamentos", "campos"):
        return JSONResponse(
            status_code=400,
            content={"status": "error", "reason": f"Invalid segment '{segment}'"},
        )

    # Reuse the shared services so the cache from earlier requests survives.
    fs = getattr(request.app.state, "forecast_service", None) or ForecastService(
        data_pipeline=getattr(request.app.state, "data_pipeline", None) or DataPipeline()
    )
    ss = getattr(request.app.state, "signal_service", None) or SignalService(
        data_pipeline=fs.data_pipeline
    )

    try:
        if segment == "departamentos":
            forecast_result = await fs.generate_departamentos_forecast(barrio=location)
        else:
            forecast_result = await fs.generate_campos_forecast(zone=location)
    except Exception as exc:
        logger.error("Narrative: forecast generation failed: %s", exc)
        return JSONResponse(
            content={
                "status": "unavailable",
                "narrative": None,
                "reason": f"Forecast unavailable: {exc}",
                "model": _narrative.model,
            }
        )

    try:
        signals: List[Dict[str, Any]] = []
        processed = await ss.process_signals_for_segment(segment=segment, limit=10)
        for p in processed[:10]:
            signals.append(
                {
                    "title": p.title,
                    "market_impact_score": p.market_impact_score,
                    "signal_classification": {
                        "impact_direction": p.signal_classification.impact_direction.value,
                        "impact_magnitude": p.signal_classification.impact_magnitude,
                    },
                }
            )
    except Exception as exc:
        logger.warning("Narrative: signal service failed: %s", exc)
        signals = []

    backtest = _load_backtest()
    insights = {"backtest": backtest} if backtest else None

    payload = await _narrative.generate(
        segment=segment,
        forecast_payload=_forecast_payload(forecast_result),
        signals=signals,
        insights=insights,
    )
    return JSONResponse(content=payload)
