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
from services.timing_signals import TimingSignals
from models.bayesian_barrios import BarrioForecaster

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

    # Gather slot extras for the slot-driven briefing template. Each is
    # best-effort: when the underlying service errors, we drop the slot
    # rather than fabricate. The template paragraphs that depend on
    # missing slots are quietly omitted from the draft.
    slot_extras = await _gather_slot_extras(
        segment=segment,
        forecast_result=forecast_result,
        data_pipeline=fs.data_pipeline,
    )

    payload = await _narrative.generate(
        segment=segment,
        forecast_payload=_forecast_payload(forecast_result),
        signals=signals,
        insights=insights,
        slot_extras=slot_extras,
    )
    return JSONResponse(content=payload)


# Carrying-cost constants for the briefing's "What you take home" slot.
# Keep these in sync with backend.api.routes_forecast._NET_RETURN_DEFAULTS;
# narrative is read-only at the data layer so duplicating here keeps the
# briefing endpoint self-contained.
_BRIEFING_NET_DEFAULTS: Dict[str, float] = {
    "gross_yield_pct": 4.6,
    "vacancy_pct": -0.7,
    "abl_tax_pct": -0.8,
    "expensas_pct": -0.4,
    "fx_friction_pct": -0.4,
    "tx_round_trip_pct": -7.0,
    "hold_years": 5,
}


async def _gather_slot_extras(
    segment: str,
    forecast_result: Any,
    data_pipeline: DataPipeline,
) -> Dict[str, Any]:
    """Best-effort fetch of the structured slots the new template needs."""
    extras: Dict[str, Any] = {}

    # Departamentos-only slots — the briefing template's "Where" / net
    # return / scenarios paragraphs are CABA-specific. For campos the
    # briefing degrades to The Call + Confidence sections only.
    if segment != "departamentos":
        return extras

    year_1 = (forecast_result.forecasts or {}).get(1, {}).get("model_estimate") or {}
    median_pct = float(year_1.get("median_change_pct", 0))
    ci80 = year_1.get("ci_80") or [0, 0]
    ci_lower = float(ci80[0])
    ci_upper = float(ci80[1])
    # Derive sigma from the 80% half-width for the barrio model.
    caba_sigma = max(0.1, (ci_upper - ci_lower) / (2 * 1.2816))

    # Top barrios — use the existing partial-pooled forecaster.
    try:
        forecaster = BarrioForecaster()
        ranked = forecaster.forecast_all(caba_mu=median_pct, caba_sigma=caba_sigma)
        # Drop thin-data barrios; the template only quotes barrios we
        # can stand behind quantitatively.
        eligible = [b for b in ranked if not b.thin_data]
        extras["top_barrios"] = [
            {
                "name": b.name,
                "total_return_pct": b.total_return_pct,
                "median_change_pct": b.median_change_pct,
                "gross_yield_pct": b.gross_yield_pct,
            }
            for b in eligible[:3]
        ]
    except Exception as exc:
        logger.warning("Narrative slot fetch (barrios) failed: %s", exc)

    # Entry-quality reading — keep it isolated from listing scrapes.
    try:
        timing = TimingSignals(data_pipeline=data_pipeline)
        reading = await timing.get_entry_quality()
        extras["entry_quality"] = reading.as_dict()
    except Exception as exc:
        logger.warning("Narrative slot fetch (entry quality) failed: %s", exc)

    # Net return decomposition — deterministic arithmetic, no service call.
    try:
        d = _BRIEFING_NET_DEFAULTS
        hold = int(d["hold_years"])
        tx_amortised = d["tx_round_trip_pct"] / hold
        net_annual = (
            median_pct
            + d["gross_yield_pct"]
            + d["vacancy_pct"]
            + d["abl_tax_pct"]
            + d["expensas_pct"]
            + d["fx_friction_pct"]
            + tx_amortised
        )
        extras["net_return"] = {
            "appreciation_pct": round(median_pct, 1),
            "gross_yield_pct": round(d["gross_yield_pct"], 1),
            "net_annual_pct": round(net_annual, 1),
            "hold_years": hold,
        }
    except Exception as exc:
        logger.warning("Narrative slot fetch (net return) failed: %s", exc)

    # Canonical scenarios — same probabilities/impacts the panel uses.
    try:
        regime = forecast_result.regime_context or {}
        transitions = regime.get("transition_probabilities", {}) or {}
        base_prob = float(
            transitions.get("remain_recovery")
            or transitions.get("remain_in_regime")
            or 0.70
        )
        crisis_prob = float(transitions.get("transition_to_crisis") or 0.08)
        fx_prob = max(0.05, 1.0 - base_prob - crisis_prob)
        extras["scenarios"] = [
            {
                "key": "base_case",
                "probability": round(base_prob, 2),
                "median_pct": round(median_pct, 1),
                "band_lower_pct": round(ci_lower, 1),
                "band_upper_pct": round(ci_upper, 1),
            },
            {
                "key": "fx_shock",
                "probability": round(fx_prob, 2),
                "median_pct": -11.0,
                "band_lower_pct": -15.0,
                "band_upper_pct": -8.0,
            },
            {
                "key": "regime_crisis",
                "probability": round(crisis_prob, 2),
                "median_pct": -9.4,
                "band_lower_pct": -14.2,
                "band_upper_pct": -4.6,
            },
        ]
    except Exception as exc:
        logger.warning("Narrative slot fetch (scenarios) failed: %s", exc)

    return extras
