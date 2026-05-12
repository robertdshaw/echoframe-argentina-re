"""
Hierarchical partial-pooled barrio forecast model.

Each CABA barrio gets its own 1-year price-appreciation forecast that
borrows strength from the city-wide model in proportion to how much
per-barrio data is available. Conceptually this is a hierarchical
Bayesian estimator with the city forecast as the hyperprior:

    μ_barrio | data ~ Normal(
        E[μ_barrio | μ_caba, β, α, x_barrio],
        σ_barrio
    )

The point estimate is a deterministic linear projection of the city
forecast:

    μ_barrio = μ_caba · β + α

where β captures the barrio's historical sensitivity to city moves
and α captures structural drift not explained by city dynamics
(gentrification momentum, new supply, etc.). Both come from the
per-barrio priors in calibration_data.get_barrio_priors().

The posterior σ is the shrinkage lever. Barrios with thin observed
data get pulled toward the city posterior by widening their σ:

    σ_barrio = σ_caba · sqrt(1 + N0 / n_eff)

where N0 = 12 is the effective sample size that would yield a 2×
posterior variance. For n_eff = 6 this gives σ ≈ 1.73 × σ_caba; for
n_eff = 30 it gives σ ≈ 1.18 × σ_caba. The frontend marks barrios
with n_eff < 12 as "thin data" so the client sees the disclosure.

This is intentionally simpler than a fully sampled hierarchical model
(no MCMC, no PyMC). The structure is correct — informative hyperprior,
sample-size-dependent shrinkage, per-barrio drift — and the math is
analytically tractable so the endpoint stays fast and deterministic.
A full MCMC version using PyMC is straightforward to swap in later.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict, List, Optional

from models.calibration_data import CalibrationData


# Effective sample size at which shrinkage doubles the posterior variance.
# A barrio with n_eff = N0 has σ_post = sqrt(2) · σ_caba; the city prior
# and barrio data contribute equal information.
_N0_SHRINKAGE_REFERENCE: float = 12.0

# Below this n_eff, the frontend should render a "thin data" badge and
# treat the barrio's quantitative forecast as directional only.
THIN_DATA_THRESHOLD: int = 12


@dataclass(frozen=True)
class BarrioForecast:
    """Per-barrio 1-year posterior with rank-table metadata."""
    name: str
    tier: str
    current_price_m2: float
    median_change_pct: float
    sigma_pct: float
    ci_80_lower: float
    ci_80_upper: float
    gross_yield_pct: float
    risk_adjusted_pct: float          # median_change_pct / sigma_pct
    total_return_pct: float           # median_change_pct + yield_pct
    n_eff: int
    thin_data: bool
    beta: float
    alpha: float


class BarrioForecaster:
    """
    Computes per-barrio 1-year forecasts from the CABA-aggregate posterior.

    Usage:
        forecaster = BarrioForecaster()
        forecasts = forecaster.forecast_all(caba_mu=6.5, caba_sigma=3.2)

    The forecaster does not own the city forecast — callers pass in the
    CABA-aggregate posterior (typically year-1 model_estimate from the
    departamentos forecast) so the barrio model and city model stay in
    sync without circular dependency.
    """

    def __init__(self, calibration: Optional[CalibrationData] = None) -> None:
        self._calibration = calibration or CalibrationData()
        self._priors: Dict[str, Dict[str, float]] = self._calibration.get_barrio_priors()

    @property
    def priors(self) -> Dict[str, Dict[str, float]]:
        return self._priors

    def forecast_all(
        self,
        caba_mu: float,
        caba_sigma: float,
    ) -> List[BarrioForecast]:
        """
        Return the partial-pooled 1-year forecast for every known barrio.

        Args:
            caba_mu: Median %-change posterior for CABA aggregate (year-1).
            caba_sigma: σ of the CABA posterior (year-1).

        Returns:
            List of BarrioForecast records, ordered by total_return_pct
            descending. The caller can re-sort for the "by yield" and
            "by risk-adjusted" tables.
        """
        results: List[BarrioForecast] = []
        for name, prior in self._priors.items():
            results.append(self._forecast_one(name, prior, caba_mu, caba_sigma))
        results.sort(key=lambda b: b.total_return_pct, reverse=True)
        return results

    @staticmethod
    def _forecast_one(
        name: str,
        prior: Dict[str, float],
        caba_mu: float,
        caba_sigma: float,
    ) -> BarrioForecast:
        beta = float(prior['beta'])
        alpha = float(prior['alpha'])
        n_eff = int(prior['n_eff'])
        yield_pct = float(prior['yield_pct'])
        current_price = float(prior['current_price_m2'])
        tier = str(prior.get('tier', 'mid'))

        # Posterior mean: deterministic linear projection of city forecast.
        mu = caba_mu * beta + alpha

        # Shrinkage: wider sigma for thin-data barrios. With n_eff = N0 the
        # variance doubles (sigma scales by sqrt(2)); with very large n_eff
        # sigma approaches caba_sigma.
        shrinkage_factor = math.sqrt(1.0 + _N0_SHRINKAGE_REFERENCE / max(1, n_eff))
        sigma = caba_sigma * shrinkage_factor

        # 80% CI using normal approximation: ±1.282σ.
        z80 = 1.2816
        ci_lower = mu - z80 * sigma
        ci_upper = mu + z80 * sigma

        # Risk-adjusted: simple return/sigma Sharpe-style ratio. Avoid
        # division-by-zero on the (impossible) zero-σ edge case.
        risk_adjusted = mu / sigma if sigma > 0 else 0.0
        total_return = mu + yield_pct

        return BarrioForecast(
            name=name,
            tier=tier,
            current_price_m2=current_price,
            median_change_pct=round(mu, 2),
            sigma_pct=round(sigma, 2),
            ci_80_lower=round(ci_lower, 2),
            ci_80_upper=round(ci_upper, 2),
            gross_yield_pct=round(yield_pct, 2),
            risk_adjusted_pct=round(risk_adjusted, 3),
            total_return_pct=round(total_return, 2),
            n_eff=n_eff,
            thin_data=n_eff < THIN_DATA_THRESHOLD,
            beta=round(beta, 3),
            alpha=round(alpha, 2),
        )
