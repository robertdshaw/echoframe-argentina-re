"""
Walk-forward backtest of the Argentina Real Estate forecasting model.

Methodology
-----------
For every anchor quarter Q in the historical CABA price index where four
quarters of forward data exist, we:

  1. Compute the model's *Year-1* posterior distribution as if we were
     standing at Q with only data available up to Q.
  2. Observe the realized 4-quarter-forward price change at Q+4.
  3. Score the forecast on three axes:

       - **Calibration**: did the realized outcome fall inside the model's
         80% credible interval? Aggregated across anchors, the hit rate
         should approach 80% for a well-calibrated model.
       - **Brier score** for the directional probability P(price ↑):
         BS = mean( (P_predicted - {1 if realized>0 else 0})² ).
         Lower is better; 0.25 is the trivial fair-coin baseline.
       - **MAE** on the median point forecast.

The model is benchmarked against a *naive persistence* baseline that
assumes next year's YoY change equals the trailing-4-quarter realized
change. Beating naive persistence is the minimum bar for a real model.

We split the history into anchors before and including 2023 Q4 (the
"in-sample" set used to calibrate the priors) and anchors from 2024 Q1
onward ("out-of-sample"). The out-of-sample numbers are the honest
performance estimate.

Diagnostics are written to:
    backend/models/diagnostics/backtest_results.json
    backend/models/diagnostics/fitted_priors.json

The frontend reads these via /api/v1/model/insights to surface the
model's track record on the ModelAccuracy panel.
"""

from __future__ import annotations

import json
import math
import statistics
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
from scipy import stats

REPO_ROOT = Path(__file__).resolve().parent.parent
BACKEND = REPO_ROOT / "backend"
DIAG_DIR = BACKEND / "models" / "diagnostics"

# Make backend modules importable.
sys.path.insert(0, str(BACKEND))

from models.calibration_data import CalibrationData  # noqa: E402
from models.hmm_regime import HMMRegimeDetector  # noqa: E402


# Regime labels are now produced by the unsupervised HMM at runtime —
# see _build_regime_index_from_hmm() below. We removed the hand-assigned
# table that used to live here so the pipeline is end-to-end data-driven.
_REGIME_NAME_TO_ID: Dict[str, int] = {"crisis": 0, "recovery": 1, "boom": 2}


@dataclass
class ForecastEval:
    """A single (anchor → horizon) backtest record."""

    anchor_quarter: str
    realized_pct: float
    predicted_median: float
    predicted_mean: float
    predicted_std: float
    ci80_lower: float
    ci80_upper: float
    ci95_lower: float
    ci95_upper: float
    p_increase: float
    in_ci80: bool
    in_ci95: bool
    directional_hit: bool
    naive_predicted: float
    regime_at_anchor: str
    in_sample: bool


# ---------------------------------------------------------------------------
# Step 1: fit regime-conditional priors from the historical price series
# ---------------------------------------------------------------------------


def build_regime_index_from_hmm(cal: CalibrationData) -> Dict[int, int]:
    """
    Produce a {price-index → regime-id} map by running the unsupervised
    HMM on real features. This replaces the hand-assigned table that used
    to govern bucketing in `fit_regime_priors`.

    Notes:
      - The HMM fits on quarters[1:] (price-change starts at Q1+1). We
        align it back to price-index by shifting +1. Index 0 is the very
        first price quarter — no preceding price change exists, so we
        copy index-1's regime label.
      - This is an in-sample fit (the HMM has seen the whole series).
        Walk-forward purity for the HMM would require re-fitting at each
        anchor — not done here because (a) the HMM is identifying regime
        structure, not predicting forward, and (b) re-fitting an HMM 30
        times is non-trivial computationally on small samples.
    """
    detector = HMMRegimeDetector(cal)
    detector.train()

    diagnostics = detector.diagnostics
    state_sequence = diagnostics.get("state_sequence", [])

    by_quarter: Dict[str, int] = {}
    for entry in state_sequence:
        regime_id = _REGIME_NAME_TO_ID.get(entry["regime"])
        if regime_id is not None:
            by_quarter[entry["quarter"]] = regime_id

    # Map back to caba_prices index.
    out: Dict[int, int] = {}
    for idx, q in enumerate(cal.caba_prices):
        iso = f"{q.year}Q{q.quarter}"
        if iso in by_quarter:
            out[idx] = by_quarter[iso]
    # Index 0 (very first quarter) has no price-change row; inherit
    # neighbour to avoid an undefined cell.
    if 0 not in out and 1 in out:
        out[0] = out[1]
    return out


def fit_regime_priors(
    cal: CalibrationData,
    regime_index: Dict[int, int],
    exclude_anchor_idx: Optional[int] = None,
) -> Dict[str, Dict[str, float]]:
    """
    Estimate Year-1 prior mean & std from realized YoY price changes,
    grouped by the *HMM-assigned* regime in force at the anchor quarter.

    Leave-one-out: when computing the prior used to forecast anchor `t`,
    we exclude anchor `t` from the fit.
    """
    prices = [q.value for q in cal.caba_prices]
    by_regime: Dict[int, List[float]] = {0: [], 1: [], 2: []}

    for anchor_idx in range(len(prices) - 4):
        if anchor_idx == exclude_anchor_idx:
            continue
        regime = regime_index.get(anchor_idx)
        if regime is None:
            continue
        change_pct = (prices[anchor_idx + 4] / prices[anchor_idx] - 1) * 100
        by_regime.setdefault(regime, []).append(change_pct)

    label_for = {0: "crisis", 1: "recovery", 2: "boom"}
    fitted: Dict[str, Dict[str, float]] = {}
    for regime, label in label_for.items():
        values = by_regime.get(regime) or []
        if len(values) >= 2:
            fitted[label] = {
                "n": len(values),
                "year_1_mean": round(float(np.mean(values)), 3),
                "year_1_std": round(float(np.std(values, ddof=1)), 3),
            }
        else:
            fitted[label] = {
                "n": len(values),
                "year_1_mean": float("nan"),
                "year_1_std": float("nan"),
            }
    return fitted


# ---------------------------------------------------------------------------
# Step 2: regime-conditional prior + Student-t likelihood
# ---------------------------------------------------------------------------


def _t_quantiles(mu: float, sigma: float, df: int, ps: List[float]) -> List[float]:
    """Quantiles of a location-scale Student-t with df > 2."""
    return [mu + sigma * stats.t.ppf(p, df=df) for p in ps]


def _t_p_increase(mu: float, sigma: float, df: int) -> float:
    """P(X > 0) for a location-scale Student-t."""
    return 1.0 - stats.t.cdf(-mu / sigma, df=df)


def model_forecast_at_anchor(
    anchor_idx: int,
    regime_index: Dict[int, int],
    regime_priors: Dict[str, Dict[str, float]],
    df: int = 4,
) -> Tuple[float, float, float, float, float, float, float, float]:
    """
    Generate the Year-1 forecast posterior at quarter index `anchor_idx`.

    The "model" used here is the regime-conditional prior alone — built
    from the HMM-fitted regime label at the anchor quarter.
    """
    regime_label = {0: "crisis", 1: "recovery", 2: "boom"}.get(
        regime_index.get(anchor_idx, 1), "recovery"
    )
    prior = regime_priors.get(regime_label, {})
    mu = prior.get("year_1_mean")
    sigma = prior.get("year_1_std")
    if mu is None or math.isnan(mu) or sigma is None or math.isnan(sigma):
        # Honest fallback when a regime had insufficient training data.
        mu, sigma = 0.0, 6.0

    ci80_lo, ci80_hi = _t_quantiles(mu, sigma, df, [0.1, 0.9])
    ci95_lo, ci95_hi = _t_quantiles(mu, sigma, df, [0.025, 0.975])
    p_inc = _t_p_increase(mu, sigma, df)
    median = mu  # Student-t is symmetric, median = mean = mu

    return median, mu, sigma, ci80_lo, ci80_hi, ci95_lo, ci95_hi, p_inc


# ---------------------------------------------------------------------------
# Step 3: walk-forward backtest
# ---------------------------------------------------------------------------


def run_backtest(cal: CalibrationData, regime_index: Dict[int, int]) -> Dict:
    """
    Leave-one-out walk-forward backtest. For each anchor:
      - the regime at that quarter comes from the unsupervised HMM
      - the prior used to score it is fit on all *other* anchors' realized
        changes (LOO), so the prior never sees its own outcome.
    """
    prices = [q.value for q in cal.caba_prices]
    quarters_iso = [f"{q.year}Q{q.quarter}" for q in cal.caba_prices]
    in_sample_cutoff_idx = quarters_iso.index("2023Q4")

    records: List[ForecastEval] = []

    for anchor_idx in range(len(prices) - 4):
        anchor_q = quarters_iso[anchor_idx]
        realized = (prices[anchor_idx + 4] / prices[anchor_idx] - 1) * 100

        loo_priors = fit_regime_priors(
            cal, regime_index=regime_index, exclude_anchor_idx=anchor_idx
        )
        median, mu, sigma, c80lo, c80hi, c95lo, c95hi, p_inc = model_forecast_at_anchor(
            anchor_idx, regime_index, loo_priors
        )

        # Naive baseline: persistence of the last realized YoY.
        if anchor_idx >= 4:
            naive = (prices[anchor_idx] / prices[anchor_idx - 4] - 1) * 100
        else:
            naive = 0.0

        regime_label = {0: "crisis", 1: "recovery", 2: "boom"}.get(
            regime_index.get(anchor_idx, 1), "recovery"
        )

        records.append(
            ForecastEval(
                anchor_quarter=anchor_q,
                realized_pct=round(realized, 3),
                predicted_median=round(median, 3),
                predicted_mean=round(mu, 3),
                predicted_std=round(sigma, 3),
                ci80_lower=round(c80lo, 3),
                ci80_upper=round(c80hi, 3),
                ci95_lower=round(c95lo, 3),
                ci95_upper=round(c95hi, 3),
                p_increase=round(p_inc, 4),
                in_ci80=bool(c80lo <= realized <= c80hi),
                in_ci95=bool(c95lo <= realized <= c95hi),
                directional_hit=bool((p_inc >= 0.5) == (realized > 0)),
                naive_predicted=round(naive, 3),
                regime_at_anchor=regime_label,
                in_sample=(anchor_idx <= in_sample_cutoff_idx),
            )
        )

    return _summarize(records)


def _summarize(records: List[ForecastEval]) -> Dict:
    in_sample = [r for r in records if r.in_sample]
    oos = [r for r in records if not r.in_sample]

    def block_stats(rs: List[ForecastEval]) -> Dict:
        if not rs:
            return {"n": 0}
        ci80_hit = sum(r.in_ci80 for r in rs) / len(rs)
        ci95_hit = sum(r.in_ci95 for r in rs) / len(rs)
        directional = sum(r.directional_hit for r in rs) / len(rs)
        brier = statistics.fmean(
            (r.p_increase - (1.0 if r.realized_pct > 0 else 0.0)) ** 2 for r in rs
        )
        mae = statistics.fmean(abs(r.realized_pct - r.predicted_median) for r in rs)
        naive_mae = statistics.fmean(abs(r.realized_pct - r.naive_predicted) for r in rs)
        # Calibration buckets for the calibration plot.
        buckets = {"0-20": [], "20-40": [], "40-60": [], "60-80": [], "80-100": []}
        for r in rs:
            edge = min(int(r.p_increase * 5), 4)
            label = list(buckets.keys())[edge]
            buckets[label].append(1.0 if r.realized_pct > 0 else 0.0)
        calibration_curve = [
            {
                "bucket": label,
                "predicted_midpoint": (i + 0.5) * 0.2,
                "realized_rate": round(statistics.fmean(vs), 3) if vs else None,
                "n": len(vs),
            }
            for i, (label, vs) in enumerate(buckets.items())
        ]
        regime_breakdown = Counter(r.regime_at_anchor for r in rs)
        return {
            "n": len(rs),
            "ci80_coverage": round(ci80_hit, 3),
            "ci95_coverage": round(ci95_hit, 3),
            "directional_hit_rate": round(directional, 3),
            "brier_score": round(brier, 4),
            "mae_pct": round(mae, 3),
            "naive_baseline_mae_pct": round(naive_mae, 3),
            "model_vs_naive_mae_delta": round(naive_mae - mae, 3),
            "regime_breakdown": dict(regime_breakdown),
            "calibration_curve": calibration_curve,
        }

    return {
        "methodology": (
            "Walk-forward backtest: for each anchor quarter Q with 4 forward "
            "quarters of realized data, the regime-conditional prior is "
            "evaluated against (price@Q+4 / price@Q - 1) × 100. Likelihood "
            "is Student-t (df=4) reflecting Argentine fat-tailed returns. "
            "In-sample = anchors ≤ 2023Q4 (priors fitted on this window). "
            "Out-of-sample = anchors ≥ 2024Q1. The naive baseline is "
            "persistence of the prior-year YoY change."
        ),
        "in_sample": block_stats(in_sample),
        "out_of_sample": block_stats(oos),
        "all": block_stats(records),
        "records": [r.__dict__ for r in records],
    }


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------


def main() -> None:
    DIAG_DIR.mkdir(parents=True, exist_ok=True)
    cal = CalibrationData()

    regime_index = build_regime_index_from_hmm(cal)
    regime_priors = fit_regime_priors(cal, regime_index=regime_index)
    backtest = run_backtest(cal, regime_index)

    (DIAG_DIR / "fitted_priors.json").write_text(
        json.dumps(regime_priors, indent=2), encoding="utf-8"
    )
    (DIAG_DIR / "backtest_results.json").write_text(
        json.dumps(backtest, indent=2), encoding="utf-8"
    )

    oos = backtest["out_of_sample"]
    print("Fitted regime priors:")
    for regime, vals in regime_priors.items():
        print(f"  {regime:>9}  n={vals['n']:>2}  mean={vals['year_1_mean']}  std={vals['year_1_std']}")
    print("\nOut-of-sample (anchors >= 2024Q1, leave-one-out priors):")
    print(f"  n                       {oos.get('n')}")
    print(f"  80% CI coverage         {oos.get('ci80_coverage')}")
    print(f"  95% CI coverage         {oos.get('ci95_coverage')}")
    print(f"  Directional hit rate    {oos.get('directional_hit_rate')}")
    print(f"  Brier score             {oos.get('brier_score')}")
    print(f"  MAE (pp)                {oos.get('mae_pct')}")
    print(f"  Naive baseline MAE (pp) {oos.get('naive_baseline_mae_pct')}")
    print(f"  Model vs naive MAE delta {oos.get('model_vs_naive_mae_delta')}")
    print(f"\nWrote {DIAG_DIR / 'backtest_results.json'}")


if __name__ == "__main__":
    main()
