"""
Bayesian model for Argentine agricultural land (campos) price forecasting.

Regional sub-models with commodity price correlation and export policy sensitivity.
"""

from typing import Dict, List, Tuple, Optional
import numpy as np
from scipy import stats
from dataclasses import dataclass
from .calibration_data import CalibrationData


@dataclass
class CamposRegion:
    """Agricultural region characteristics"""
    name: str
    prior_mean: float
    prior_std: float
    commodity_sensitivity: float
    policy_sensitivity: float
    

class BayesianCamposModel:
    """
    Bayesian model for agricultural land price forecasting.
    
    Regional specialization with different prior beliefs and sensitivities:
    - Core Pampa: High commodity sensitivity, stable returns
    - Santa Fe: Moderate sensitivity, mixed agriculture  
    - Frontier: High volatility, expansion opportunity
    - Peri-urban: Development optionality, highest returns
    """
    
    def __init__(self, calibration_data: CalibrationData):
        self.calibration_data = calibration_data
        self.priors = calibration_data.get_prior_beliefs()['campos']
        self.current_context = calibration_data.get_current_market_context()
        
        # Define regional characteristics
        self.regions = {
            'core_pampa': CamposRegion(
                name='core_pampa',
                prior_mean=self.priors['core_pampa']['year_1_mean'],
                prior_std=self.priors['core_pampa']['year_1_std'],
                commodity_sensitivity=0.8,  # High sensitivity to soy/wheat/corn
                policy_sensitivity=0.6      # Moderate retenciones sensitivity
            ),
            'santa_fe': CamposRegion(
                name='santa_fe', 
                prior_mean=self.priors['santa_fe']['year_1_mean'],
                prior_std=self.priors['santa_fe']['year_1_std'],
                commodity_sensitivity=0.7,
                policy_sensitivity=0.7
            ),
            'frontier': CamposRegion(
                name='frontier',
                prior_mean=self.priors['frontier']['year_1_mean'],
                prior_std=self.priors['frontier']['year_1_std'],
                commodity_sensitivity=0.6,  # Lower commodity correlation
                policy_sensitivity=0.4      # Less affected by export taxes
            ),
            'periurban': CamposRegion(
                name='periurban',
                prior_mean=self.priors['periurban']['year_1_mean'],
                prior_std=self.priors['periurban']['year_1_std'],
                commodity_sensitivity=0.3,  # Driven by development, not commodities
                policy_sensitivity=0.2
            )
        }
        
        # Signal weights for likelihood computation
        self.signal_weights = {
            'commodity_prices': 0.35,
            'export_tax_policy': 0.20,
            'usd_ars_trajectory': 0.15,
            'agricultural_profitability': 0.15,
            'news_sentiment_ag': 0.10,
            'frontier_expansion': 0.05
        }
    
    def get_commodity_signal(self) -> float:
        """
        Compute commodity price signal based on current futures vs historical.
        
        Returns:
            Normalized signal [-3, +3] representing commodity price momentum
        """
        # Current approximate commodity levels (USD/ton)
        current_soybean = 420  # Moderate level
        current_wheat = 280   # Good level
        current_corn = 190    # Moderate level
        
        # Historical ranges for normalization
        soy_historical_range = (320, 580)  # Min, max from calibration data
        wheat_historical_range = (180, 400)
        corn_historical_range = (140, 280)
        
        # Normalize current prices within historical ranges [0, 1]
        soy_norm = (current_soybean - soy_historical_range[0]) / (soy_historical_range[1] - soy_historical_range[0])
        wheat_norm = (current_wheat - wheat_historical_range[0]) / (wheat_historical_range[1] - wheat_historical_range[0])
        corn_norm = (current_corn - corn_historical_range[0]) / (corn_historical_range[1] - corn_historical_range[0])
        
        # Average and convert to signal [-3, +3]
        avg_commodity_position = np.mean([soy_norm, wheat_norm, corn_norm])
        # 0.5 = neutral, <0.5 = negative, >0.5 = positive
        commodity_signal = (avg_commodity_position - 0.5) * 4.0
        
        return np.clip(commodity_signal, -3, 3)
    
    def get_policy_signal(self) -> float:
        """
        Assess export tax (retenciones) policy environment.
        
        Returns:
            Normalized signal [-3, +3] where negative = higher taxes expected
        """
        # Current government has been reducing retenciones incrementally
        # Assume moderate positive policy environment
        # Soy retenciones ~33% (down from peak ~35%), wheat/corn lower
        
        current_soy_tax = 33.0  # %
        historical_avg_tax = 30.0  # Long-term average
        historical_peak = 35.0
        
        # Lower taxes relative to peak = positive signal
        policy_position = (historical_peak - current_soy_tax) / (historical_peak - 20.0)  # Normalize
        policy_signal = (policy_position - 0.5) * 2.0  # Convert to signal
        
        return np.clip(policy_signal, -3, 3)
    
    def get_profitability_signal(self) -> float:
        """
        Compute agricultural profitability index signal.
        
        Returns:
            Signal based on input costs vs commodity revenues
        """
        # Proxy: Current commodity prices vs input cost inflation
        # Lower inflation = lower input costs = higher profitability
        current_monthly_inflation = 1.2
        historical_avg_inflation = 8.0  # Long-term average
        
        # Lower inflation = positive profitability signal
        profitability_signal = (historical_avg_inflation - current_monthly_inflation) / 3.0
        
        return np.clip(profitability_signal, -3, 3)
    
    def compute_likelihood_signals(self, region: str) -> Dict[str, float]:
        """
        Compute regional market signals for likelihood computation.
        
        Args:
            region: 'core_pampa', 'santa_fe', 'frontier', or 'periurban'
            
        Returns:
            Dictionary of normalized signal values
        """
        region_info = self.regions[region]
        
        # Base signals
        commodity_signal = self.get_commodity_signal()
        policy_signal = self.get_policy_signal() 
        profitability_signal = self.get_profitability_signal()
        
        # USD-ARS trajectory signal
        # Moderate devaluation is positive for agro exports
        current_rate = 1130
        implied_annual_devaluation = 0.15  # ~15% annual pace
        optimal_devaluation = 0.20  # Sweet spot for agro
        usd_signal = 1.0 - abs(implied_annual_devaluation - optimal_devaluation) / 0.1
        
        # Agricultural news sentiment (assume neutral to positive)
        ag_sentiment_signal = 0.4
        
        # Frontier expansion pressure (land scarcity driving prices)
        if region == 'frontier':
            expansion_signal = 1.2  # Frontier benefits from expansion
        elif region == 'periurban':
            expansion_signal = 1.8  # Highest pressure near urban areas
        else:
            expansion_signal = 0.3  # Core areas less affected
        
        # Apply regional sensitivities
        adjusted_signals = {
            'commodity_prices': commodity_signal * region_info.commodity_sensitivity,
            'export_tax_policy': policy_signal * region_info.policy_sensitivity,
            'usd_ars_trajectory': usd_signal,
            'agricultural_profitability': profitability_signal,
            'news_sentiment_ag': ag_sentiment_signal,
            'frontier_expansion': expansion_signal
        }
        
        return adjusted_signals
    
    def compute_posterior(self, region: str, year: int, 
                         regime_weights: Optional[Dict[str, float]] = None) -> 'ForecastDistribution':
        """
        Compute Bayesian posterior for agricultural land in specific region.
        
        Args:
            region: Agricultural region name
            year: Forecast year (1, 2, or 3)
            regime_weights: Optional regime weights from HMM
            
        Returns:
            ForecastDistribution with posterior statistics
        """
        # Import here to avoid circular import
        from .bayesian_departamentos import ForecastDistribution
        
        # Get regional prior parameters  
        region_priors = self.priors[region]
        prior_mean = region_priors[f'year_{year}_mean']
        prior_std = region_priors[f'year_{year}_std']
        prior_precision = 1.0 / (prior_std ** 2)
        
        # Get likelihood signals
        signals = self.compute_likelihood_signals(region)
        
        # Compute weighted likelihood mean
        likelihood_mean = sum(
            self.signal_weights[signal] * value * 2.5  # Scale factor for % returns
            for signal, value in signals.items()
        )
        
        # Likelihood precision based on signal strength and regional volatility
        signal_strength = np.mean([abs(v) for v in signals.values()])
        base_uncertainty = 4.0  # Agricultural land inherently more volatile
        likelihood_std = base_uncertainty - signal_strength * 0.4
        likelihood_precision = 1.0 / (likelihood_std ** 2)
        
        # Apply regime weighting
        if regime_weights:
            recovery_weight = regime_weights.get('recovery', 0.8)
            # Agricultural land is less sensitive to financial regime than urban RE
            regime_adjustment = 0.5 + 0.5 * recovery_weight
            likelihood_mean *= regime_adjustment
            likelihood_precision *= regime_adjustment
        
        # Conjugate update
        posterior_precision = prior_precision + likelihood_precision
        posterior_variance = 1.0 / posterior_precision
        posterior_std = np.sqrt(posterior_variance)
        
        posterior_mean = (
            prior_precision * prior_mean + 
            likelihood_precision * likelihood_mean
        ) / posterior_precision
        
        # Horizon uncertainty adjustment (agricultural land more stable long-term)
        horizon_adjustment = 1.0 + (year - 1) * 0.25
        posterior_std *= horizon_adjustment
        
        # Student-t emission (df=4) to capture commodity-driven fat tails
        # in Argentine agricultural land returns. Same justification as the
        # departamentos model — see bayesian_departamentos.py header.
        df = 4
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
            median_change_pct=posterior_mean,
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
    
    def generate_regional_forecast(self, region: str, horizons: List[int] = [1, 2, 3],
                                 regime_weights: Optional[Dict[str, float]] = None) -> Dict[int, 'ForecastDistribution']:
        """
        Generate multi-horizon forecast for specific agricultural region.
        
        Args:
            region: Agricultural region name
            horizons: List of forecast years
            regime_weights: Regime weights from HMM
            
        Returns:
            Dictionary mapping year to ForecastDistribution
        """
        forecasts = {}
        
        for year in horizons:
            forecasts[year] = self.compute_posterior(region, year, regime_weights)
            
        return forecasts
    
    def generate_all_regions_forecast(self, horizons: List[int] = [1, 2, 3],
                                    regime_weights: Optional[Dict[str, float]] = None) -> Dict[str, Dict[int, 'ForecastDistribution']]:
        """
        Generate forecast for all agricultural regions.
        
        Returns:
            Nested dictionary: {region: {year: ForecastDistribution}}
        """
        all_forecasts = {}
        
        for region_name in self.regions.keys():
            all_forecasts[region_name] = self.generate_regional_forecast(
                region_name, horizons, regime_weights
            )
            
        return all_forecasts
    
    def get_commodity_correlation_analysis(self) -> Dict[str, float]:
        """
        Analyze current commodity price position relative to historical ranges.
        
        Returns:
            Dictionary with commodity analysis for user display
        """
        soybean_signal = self.get_commodity_signal()
        
        return {
            'current_soybean_usd_ton': 420,
            'current_wheat_usd_ton': 280,
            'current_corn_usd_ton': 190,
            'composite_commodity_signal': soybean_signal,
            'interpretation': self._interpret_commodity_signal(soybean_signal),
            'land_price_correlation': 'When soybean > $450/ton, agricultural land appreciates faster. Below $350/ton, appreciation stalls.',
            'current_regime': 'Moderate commodity prices support stable land appreciation'
        }
    
    def _interpret_commodity_signal(self, signal: float) -> str:
        """Interpret commodity signal for user display"""
        if signal > 1.0:
            return "Strong positive - commodity prices well above historical average"
        elif signal > 0.5:
            return "Moderate positive - commodity prices above average" 
        elif signal > -0.5:
            return "Neutral - commodity prices near historical average"
        elif signal > -1.0:
            return "Moderate negative - commodity prices below average"
        else:
            return "Strong negative - commodity prices well below historical average"
    
    def generate_scenario_forecast(self, region: str, scenario_params: Dict[str, float],
                                 horizons: List[int] = [1, 2, 3]) -> Dict[int, 'ForecastDistribution']:
        """
        Generate forecast under specific scenario for agricultural land.
        
        Args:
            region: Agricultural region
            scenario_params: Scenario assumptions (retenciones_change, commodity_shock, etc.)
            horizons: Forecast years
            
        Returns:
            Scenario-adjusted forecasts
        """
        # Store original methods
        original_commodity = self.get_commodity_signal
        original_policy = self.get_policy_signal
        
        # Create scenario-adjusted signal methods
        def scenario_commodity_signal():
            base_signal = original_commodity()
            if 'commodity_shock' in scenario_params:
                shock = scenario_params['commodity_shock']  # e.g., +20% price shock
                shock_signal = shock / 10.0  # Convert % to signal scale
                return np.clip(base_signal + shock_signal, -3, 3)
            return base_signal
        
        def scenario_policy_signal():
            base_signal = original_policy()
            if 'retenciones_change' in scenario_params:
                # Negative change = tax reduction = positive signal
                tax_change = scenario_params['retenciones_change']  # e.g., -5pp
                policy_impact = -tax_change / 2.5  # Convert pp to signal scale
                return np.clip(base_signal + policy_impact, -3, 3)
            return base_signal
        
        # Apply scenario modifications
        self.get_commodity_signal = scenario_commodity_signal
        self.get_policy_signal = scenario_policy_signal
        
        # Generate forecast
        forecasts = {}
        for year in horizons:
            forecasts[year] = self.compute_posterior(region, year)
        
        # Restore original methods
        self.get_commodity_signal = original_commodity
        self.get_policy_signal = original_policy
        
        return forecasts