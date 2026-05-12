"""
Model diagnostics endpoints for EchoFrame Argentina RE Intelligence.

Surfaces the artefacts produced by scripts/run_backtest.py:

  * Walk-forward leave-one-out backtest of the Year-1 forecast
    (calibration coverage, Brier score, MAE, directional hit rate,
    comparison vs naive persistence baseline, calibration curve).

  * Regime-conditional priors fitted from the historical CABA price
    series — these are the same priors the live model uses, so the
    frontend can show "this is the prior we actually applied".

When the diagnostics files don't exist yet (e.g. fresh clone, backtest
hasn't been run), the endpoint returns 200 with `status: "not_run"`
rather than 500 — the frontend uses that to render a "run the backtest"
prompt instead of an error.
"""

from __future__ import annotations

import json
import logging
import math
from pathlib import Path
from typing import Any, Dict

from fastapi import APIRouter
from fastapi.responses import JSONResponse


logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/model", tags=["model"])

_DIAG_DIR = Path(__file__).resolve().parent.parent / "models" / "diagnostics"
_BACKTEST_PATH = _DIAG_DIR / "backtest_results.json"
_PRIORS_PATH = _DIAG_DIR / "fitted_priors.json"
_HMM_PATH = _DIAG_DIR / "hmm_diagnostics.json"


def _scrub_nans(obj: Any) -> Any:
    """Recursively replace NaN/Infinity with None — JSON spec doesn't allow them."""
    if isinstance(obj, dict):
        return {k: _scrub_nans(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_scrub_nans(v) for v in obj]
    if isinstance(obj, float) and (math.isnan(obj) or math.isinf(obj)):
        return None
    return obj


def _load_or_none(path: Path) -> Any:
    if not path.exists():
        return None
    try:
        # parse_constant catches NaN/Infinity tokens emitted by numpy-derived
        # dumps and converts them to None so the response is RFC-compliant.
        data = json.loads(
            path.read_text(encoding="utf-8"),
            parse_constant=lambda c: None,
        )
        return _scrub_nans(data)
    except Exception as exc:
        logger.warning("Failed to read %s: %s", path.name, exc)
        return None


@router.get("/insights")
async def get_model_insights() -> JSONResponse:
    """
    Return the model's track record and the priors it's actually using.

    Response shape:
        {
          "status": "ok" | "not_run",
          "backtest": { ... full backtest summary, see run_backtest.py ... },
          "fitted_priors": { "crisis": {...}, "recovery": {...}, ... }
        }
    """
    backtest = _load_or_none(_BACKTEST_PATH)
    priors = _load_or_none(_PRIORS_PATH)
    hmm = _load_or_none(_HMM_PATH)

    if backtest is None and priors is None and hmm is None:
        return JSONResponse(
            content={
                "status": "not_run",
                "message": (
                    "Backtest artefacts not found. Run `python scripts/run_backtest.py` "
                    "from the repo root to generate them."
                ),
            }
        )

    return JSONResponse(
        content={
            "status": "ok",
            "backtest": backtest,
            "fitted_priors": priors,
            "hmm": hmm,
        }
    )
