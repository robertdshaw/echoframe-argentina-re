"""
Bayesian model for Buenos Aires departamentos price forecasting.

Uses conjugate Normal-Normal updating for analytically tractable posteriors
and adds a Student-t emission for credible-interval rendering so the tails
match the empirical fat-tailed distribution of Argentine USD returns.

If backend/models/diagnostics/fitted_priors.json exists (produced by
scripts/run_backtest.py), the regime-conditional priors fitted from the
historical CABA series are preferred over the hand-coded defaults. This
closes the loop between the backtest and what the live model actually uses.
"""

import json
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import numpy as np
from scipy import stats
from dataclasses import dataclass
from .calibration_data import CalibrationData

# Path to data-driven priors written by scripts/run_backtest.py. When the
# file is present, the regime-conditional Year-1 priors are sourced here
# rather than from the hand-coded calibration_data defaults.
_FITTED_PRIORS_PATH = Path(__file__).parent / "diagnostics" / "fitted_priors.json"

# Degrees of freedom for the Student-t emission. df=4 produces moderately
# heavy tails (kurtosis = 6 vs the Normal's 3) which is closer to the
# empirical kurtosis of Argentine real estate USD returns. We don't go
# lower because the model would put excessive mass on extreme outcomes.
_STUDENT_T_DF = 4


@dataclass
class ForecastDistribution:
    """Posterior distribution for a forecast horizon"""
    year: int
    median_change_pct: float
    mean_change_pct: float
    credible_interval_80: Tuple[float, float]
    credible_interval_95: Tuple[float, float]
    p_increase: float
    p_increase_5pct: float
    p_increase_10pct: float
    p_decrease: float
    p_decrease_5pct: float
    distribution_params: Dict[str, float]  # For rendering


class BayesianDepartamentosModel:
    """
    Bayesian model for CABA apartment price forecasting using conjugate priors.
    
    Prior: Normal(μ_prior, σ²_prior) based on REM consensus
    Likelihood: Observational model based on current market signals
    Posterior: Normal(μ_posterior, σ²_posterior) analytically computed
    """
    
    def __init__(self, calibration_data: CalibrationData):
        self.calibration_data = calibration_data
        self.priors = calibration_data.get_prior_beliefs()['departamentos']
        self.current_context = calibration_data.get_current_market_context()

        # Regime-conditional priors fitted from history. None when the
        # backtest hasn't been run yet — model falls back to hand-coded.
        self.fitted_regime_priors: Optional[Dict[str, Dict[str, float]]] = (
            self._load_fitted_priors()
        )

        # Signal weights for likelihood computation
        self.signal_weights = {
            'credit_expansion': 0.30,
            'inflation_adjusted_demand': 0.25,
            'transaction_momentum': 0.20,
            'construction_costs': 0.10,
            'foreign_investment': 0.10,
            'news_sentiment': 0.05
        }

    @staticmethod
    def _load_fitted_priors() -> Optional[Dict[str, Dict[str, float]]]:
        """Load the regime-conditional priors emitted by run_backtest.py."""
        if not _FITTED_PRIORS_PATH.exists():
            return None
        try:
            return json.loads(_FITTED_PRIORS_PATH.read_text(encoding="utf-8"))
        except Exception:
            return None

    def _prior_for(self, year: int, regime_weights: Optional[Dict[str, float]]) -> Tuple[float, float]:
        """
        Resolve the (mean, std) Year-1 prior to use for a given horizon,
        mixing the regime-conditional fitted priors by the regime weights
        coming from the HMM. Year>1 widens the spread by 30% per year.
        """
        # Start from hand-coded defaults.
        default_mean = self.priors[f"year_{year}_mean"]
        default_std = self.priors[f"year_{year}_std"]

        if not self.fitted_regime_priors:
            return default_mean, default_std

        weights = regime_weights or {"recovery": 1.0}
        # Filter out regimes for which the fit had insufficient data (NaN).
        valid = {
            r: w for r, w in weights.items()
            if r in self.fitted_regime_priors
            and self.fitted_regime_priors[r]["year_1_mean"]
            == self.fitted_regime_priors[r]["year_1_mean"]  # not NaN
        }
        if not valid:
            return default_mean, default_std

        total = sum(valid.values()) or 1.0
        mu = sum(
            (w / total) * self.fitted_regime_priors[r]["year_1_mean"]
            for r, w in valid.items()
        )
        # Combine within-regime variance + between-regime spread.
        within = sum(
            (w / total) * (self.fitted_regime_priors[r]["year_1_std"] ** 2)
            for r, w in valid.items()
        )
        between = sum(
            (w / total) * (self.fitted_regime_priors[r]["year_1_mean"] - mu) ** 2
            for r, w in valid.items()
        )
        sigma = float(np.sqrt(within + between))

        # Year>1 widens by 30%/year as before — uncertainty grows with horizon.
        horizon_scale = 1.0 + (year - 1) * 0.3
        return mu, sigma * horizon_scale
    
    def compute_likelihood_signals(self) -> Dict[str, float]:
        """
        Compute current market signals that inform the likelihood.
        
        Returns:
            Dictionary of normalized signal values [-3, +3] standard deviations
        """
        # Credit expansion signal
        # Current BCRA rate 25% vs historical crisis 133% = massive expansion
        current_rate = 25.0
        historical_avg = 65.0  # Long-term average
        credit_signal = (historical_avg - current_rate) / 20.0  # Normalized: +2.0
        
        # Inflation-adjusted demand
        # Current monthly inflation 1.2% vs peak 25.5% = real income recovery  
        current_inflation = 1.2
        peak_inflation = 25.5
        inflation_signal = (peak_inflation - current_inflation) / 10.0  # Normalized: +2.43
        
        # Transaction momentum  
        # Current +45% YoY vs historical range [-50%, +50%]
        transaction_yoy = 45.3
        momentum_signal = transaction_yoy / 25.0  # Normalized: +1.81
        
        # Construction costs (proxy via inflation)
        # Lower inflation = lower construction cost pressure
        cost_signal = -current_inflation / 5.0  # Normalized: -0.24
        
        # Foreign investment (proxy via stability)
        # Stable macro = higher FDI appetite
        macro_stability = 0.7  # Subjective assessment
        investment_signal = (macro_stability - 0.5) * 4.0  # Normalized: +0.8
        
        # News sentiment aggregate
        # From NLP processing - assume slightly positive in recovery
        sentiment_signal = 0.3  # Modest positive
        
        return {
            'credit_expansion': np.clip(credit_signal, -3, 3),
            'inflation_adjusted_demand': np.clip(inflation_signal, -3, 3), 
            'transaction_momentum': np.clip(momentum_signal, -3, 3),
            'construction_costs': np.clip(cost_signal, -3, 3),
            'foreign_investment': np.clip(investment_signal, -3, 3),
            'news_sentiment': np.clip(sentiment_signal, -3, 3)
        }
    
    def compute_posterior(self, year: int, regime_weights: Optional[Dict[str, float]] = None) -> ForecastDistribution:
        """
        Compute Bayesian posterior for a given forecast horizon.
        
        Args:
            year: Forecast year (1, 2, or 3)
            regime_weights: Optional regime probability weights from HMM
            
        Returns:
            ForecastDistribution with full posterior statistics
        """
        # Get prior parameters — prefers historically-fitted regime-conditional
        # priors when available, falls back to hand-coded.
        prior_mean, prior_std = self._prior_for(year, regime_weights)
        prior_precision = 1.0 / (prior_std ** 2)
        
        # Get likelihood signals
        signals = self.compute_likelihood_signals()
        
        # Compute weighted likelihood mean
        likelihood_mean = sum(
            self.signal_weights[signal] * value * 2.0  # Scale factor for % returns
            for signal, value in signals.items()
        )
        
        # Likelihood precision based on signal strength
        # Stronger signals = higher precision (lower uncertainty)
        signal_strength = np.mean([abs(v) for v in signals.values()])
        likelihood_std = 3.0 - signal_strength * 0.5  # Range: 1.5 to 3.0
        likelihood_precision = 1.0 / (likelihood_std ** 2)
        
        # Apply regime weighting if provided
        if regime_weights:
            # Weight likelihood by regime confidence
            recovery_weight = regime_weights.get('recovery', 0.8)
            likelihood_mean *= recovery_weight  # Dampen if uncertain regime
            likelihood_precision *= recovery_weight  # Increase uncertainty
        
        # Conjugate Normal-Normal update
        posterior_precision = prior_precision + likelihood_precision
        posterior_variance = 1.0 / posterior_precision
        posterior_std = np.sqrt(posterior_variance)
        
        posterior_mean = (
            prior_precision * prior_mean + 
            likelihood_precision * likelihood_mean
        ) / posterior_precision
        
        # Adjust for forecast horizon uncertainty
        horizon_adjustment = 1.0 + (year - 1) * 0.3  # Uncertainty grows with horizon
        posterior_std *= horizon_adjustment
        
        # Emission distribution: location-scale Student-t with df=4.
        # This widens both tails compared to the conjugate Normal — the
        # honest characterisation of Argentine USD-return kurtosis.
        df = _STUDENT_T_DF
        posterior_dist = stats.t(df=df, loc=posterior_mean, scale=posterior_std)

        ci_80_lower, ci_80_upper = posterior_dist.ppf([0.1, 0.9])
        ci_95_lower, ci_95_upper = posterior_dist.ppf([0.025, 0.975])

        p_increase = 1.0 - posterior_dist.cdf(0)
        p_increase_5pct = 1.0 - posterior_dist.cdf(5.0)
        p_increase_10pct = 1.0 - posterior_dist.cdf(10.0)
        p_decrease = posterior_dist.cdf(0)
        p_decrease_5pct = posterior_dist.cdf(-5.0)

        return ForecastDistribution(
            year=year,
            median_change_pct=posterior_mean,  # t is symmetric → median = location
            mean_change_pct=posterior_mean,
            credible_interval_80=(ci_80_lower, ci_80_upper),
            credible_interval_95=(ci_95_lower, ci_95_upper),
            p_increase=p_increase,
            p_increase_5pct=p_increase_5pct,
            p_increase_10pct=p_increase_10pct,
            p_decrease=p_decrease,
            p_decrease_5pct=p_decrease_5pct,
            distribution_params={
                'type': 'student_t',
                'df': float(df),
                'mu': posterior_mean,
                'sigma': posterior_std,
            }
        )
    
    def generate_forecast(self, horizons: List[int] = [1, 2, 3], 
                         regime_weights: Optional[Dict[str, float]] = None) -> Dict[int, ForecastDistribution]:
        """
        Generate multi-horizon forecast for departamentos.
        
        Args:
            horizons: List of forecast years
            regime_weights: Regime probability weights from HMM
            
        Returns:
            Dictionary mapping year to ForecastDistribution
        """
        forecasts = {}
        
        for year in horizons:
            forecasts[year] = self.compute_posterior(year, regime_weights)
            
        return forecasts
    
    def generate_scenario_forecast(self, scenario_params: Dict[str, float],
                                 horizons: List[int] = [1, 2, 3]) -> Dict[int, ForecastDistribution]:
        """
        Generate forecast under specific scenario assumptions.
        
        Args:
            scenario_params: Dict with keys like 'inflation_target', 'mortgage_rate_change'
            horizons: List of forecast years
            
        Returns:
            Dictionary mapping year to ForecastDistribution 
        """
        # Modify signal computation based on scenario
        original_signals = self.compute_likelihood_signals()
        scenario_signals = original_signals.copy()
        
        # Apply scenario adjustments
        if 'inflation_target' in scenario_params:
            # Adjust inflation-related signals
            inflation_target = scenario_params['inflation_target']
            if inflation_target < 10:  # Low inflation scenario
                scenario_signals['inflation_adjusted_demand'] += 0.5
                scenario_signals['credit_expansion'] += 0.3
            elif inflation_target > 20:  # High inflation scenario
                scenario_signals['inflation_adjusted_demand'] -= 0.8
                scenario_signals['construction_costs'] -= 0.5
        
        if 'mortgage_rate_change' in scenario_params:
            rate_change = scenario_params['mortgage_rate_change']
            # Negative rate change = easier credit = positive signal
            scenario_signals['credit_expansion'] += -rate_change / 5.0
        
        if 'usd_ars_target' in scenario_params:
            current_rate = 1130
            target_rate = scenario_params['usd_ars_target']
            devaluation_pressure = (target_rate - current_rate) / current_rate
            # Moderate devaluation can be positive for RE (USD hedge)
            # Extreme devaluation is negative (macro instability)
            if abs(devaluation_pressure) < 0.2:
                scenario_signals['foreign_investment'] += devaluation_pressure
            else:
                scenario_signals['foreign_investment'] -= abs(devaluation_pressure)
        
        # Temporarily replace signals and generate forecast
        original_compute = self.compute_likelihood_signals
        self.compute_likelihood_signals = lambda: scenario_signals
        
        forecasts = {}
        for year in horizons:
            forecasts[year] = self.compute_posterior(year)
            
        # Restore original method
        self.compute_likelihood_signals = original_compute
        
        return forecasts
    
    def get_signal_decomposition(self) -> Dict[str, Dict[str, float]]:
        """
        Return detailed breakdown of signals driving the forecast.
        Useful for explaining model decisions to users.
        """
        signals = self.compute_likelihood_signals()
        
        decomposition = {}
        for signal_name, signal_value in signals.items():
            weight = self.signal_weights[signal_name]
            contribution = weight * signal_value * 2.0  # Convert to % return contribution
            
            decomposition[signal_name] = {
                'raw_signal': signal_value,
                'weight': weight,
                'contribution_pct': contribution,
                'interpretation': self._interpret_signal(signal_name, signal_value)
            }
            
        return decomposition
    
    def _interpret_signal(self, signal_name: str, signal_value: float) -> str:
        """Provide human-readable interpretation of signal values"""
        intensity = abs(signal_value)
        direction = "positive" if signal_value > 0 else "negative"
        
        if intensity < 0.5:
            strength = "weak"
        elif intensity < 1.5:
            strength = "moderate"
        elif intensity < 2.5:
            strength = "strong"
        else:
            strength = "very strong"
            
        interpretations = {
            'credit_expansion': f"Credit conditions show {strength} {direction} impact on affordability",
            'inflation_adjusted_demand': f"Real purchasing power shows {strength} {direction} trend",
            'transaction_momentum': f"Market activity shows {strength} {direction} momentum", 
            'construction_costs': f"Construction costs show {strength} {direction} pressure on supply",
            'foreign_investment': f"Foreign capital flows show {strength} {direction} demand pressure",
            'news_sentiment': f"Market sentiment shows {strength} {direction} bias"
        }
        
        return interpretations.get(signal_name, f"{strength} {direction} signal")