"""
Ensemble model integration combining Bayesian, HMM, and Prospect Theory.

Orchestrates the complete forecasting pipeline and produces final outputs
for the EchoFrame dashboard.
"""

from typing import Dict, List, Optional, Union
import numpy as np
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta

from .calibration_data import CalibrationData
from .bayesian_departamentos import BayesianDepartamentosModel, ForecastDistribution
from .bayesian_campos import BayesianCamposModel
from .hmm_regime import HMMRegimeDetector
from .prospect_theory import ProspectTheoryAdjuster, BehavioralDistribution


@dataclass
class EnsembleForecast:
    """Complete ensemble forecast for a market segment and horizon"""
    segment: str  # 'departamentos_caba' or 'campos_{region}'
    year: int
    current_price: float  # Current USD/m2 or USD/ha
    
    # Model estimate (raw Bayesian-HMM)
    model_estimate: Dict
    
    # Behavioral adjusted (Prospect Theory)
    behavioral_adjusted: Dict
    
    # Regime context
    regime_context: Dict
    
    # Top driving signals
    top_signals: List[Dict]
    
    # Metadata
    generated_at: str
    confidence_grade: str  # 'High', 'Medium', 'Low'


class EnsembleForecaster:
    """
    Master forecasting system combining all models.
    
    Pipeline:
    1. HMM detects current regime + transition probabilities
    2. Bayesian models generate regime-conditional posteriors  
    3. Regime-weighted ensemble combines posteriors
    4. Prospect Theory applies behavioral adjustments
    5. Final output formatted for dashboard consumption
    """
    
    def __init__(self):
        self.calibration_data = CalibrationData()
        self.departamentos_model = BayesianDepartamentosModel(self.calibration_data)
        self.campos_model = BayesianCamposModel(self.calibration_data)
        self.regime_detector = HMMRegimeDetector(self.calibration_data)
        self.prospect_adjuster = ProspectTheoryAdjuster.create_argentine_calibrated()
        
        # Initialize regime detector
        self.regime_detector.train()
        
    def generate_departamentos_forecast(self, horizons: List[int] = [1, 2, 3],
                                      barrio: Optional[str] = None) -> Dict[int, EnsembleForecast]:
        """
        Generate complete forecast for CABA departamentos.
        
        Args:
            horizons: List of forecast years
            barrio: Specific neighborhood (future enhancement)
            
        Returns:
            Dictionary mapping year to EnsembleForecast
        """
        # Step 1: Regime detection
        regime_info = self.regime_detector.detect_current_regime()
        regime_weights = {
            'recovery': regime_info['regime_probability'] if regime_info['current_regime'] == 'recovery' else 0.0,
            'crisis': regime_info['regime_probability'] if regime_info['current_regime'] == 'crisis' else 0.0,
            'boom': regime_info['regime_probability'] if regime_info['current_regime'] == 'boom' else 0.0
        }
        
        # Step 2: Bayesian forecast
        bayesian_forecasts = self.departamentos_model.generate_forecast(horizons, regime_weights)
        
        # Step 3: Signal decomposition
        signal_breakdown = self.departamentos_model.get_signal_decomposition()
        top_signals = self._format_top_signals(signal_breakdown, segment='departamentos')
        
        # Step 4: Generate ensemble forecasts for each horizon
        ensemble_forecasts = {}
        
        current_price = self.calibration_data.get_current_market_context()['current_price_usd_m2']
        
        for year in horizons:
            bayesian_forecast = bayesian_forecasts[year]
            
            # Apply Prospect Theory adjustment
            behavioral_adj = self.prospect_adjuster.adjust_posterior(
                bayesian_forecast.mean_change_pct,
                bayesian_forecast.distribution_params['sigma']
            )
            
            # Format model estimate
            model_estimate = {
                'median_change_pct': bayesian_forecast.median_change_pct,
                'mean_change_pct': bayesian_forecast.mean_change_pct,
                'ci_80': bayesian_forecast.credible_interval_80,
                'ci_95': bayesian_forecast.credible_interval_95,
                'p_increase': bayesian_forecast.p_increase,
                'p_increase_5pct': bayesian_forecast.p_increase_5pct,
                'p_decrease': bayesian_forecast.p_decrease,
                'projected_price_m2': current_price * (1 + bayesian_forecast.median_change_pct / 100),
                'distribution_params': bayesian_forecast.distribution_params
            }
            
            # Format behavioral adjustment  
            behavioral_adjusted = {
                'median_change_pct': behavioral_adj.adjusted_median,
                'mean_change_pct': behavioral_adj.adjusted_mean,
                'ci_80': behavioral_adj.adjusted_ci_80,
                'ci_95': behavioral_adj.adjusted_ci_95,
                'p_increase': behavioral_adj.behavioral_p_increase,
                'p_decrease': behavioral_adj.behavioral_p_decrease,
                'projected_price_m2': current_price * (1 + behavioral_adj.adjusted_median / 100),
                'loss_aversion_effect': behavioral_adj.loss_aversion_effect,
                'behavioral_narrative': self._create_behavioral_narrative(behavioral_adj)
            }
            
            # Confidence grading
            confidence_grade = self._assess_confidence(regime_info, bayesian_forecast, year)
            
            ensemble_forecasts[year] = EnsembleForecast(
                segment='departamentos_caba',
                year=year,
                current_price=current_price,
                model_estimate=model_estimate,
                behavioral_adjusted=behavioral_adjusted,
                regime_context={
                    'current_regime': regime_info['current_regime'],
                    'confidence': regime_info['regime_probability'],
                    'description': regime_info['description'],
                    'key_driver': self._identify_key_driver(signal_breakdown)
                },
                top_signals=top_signals[:3],  # Top 3 signals
                generated_at=datetime.now().isoformat(),
                confidence_grade=confidence_grade
            )
        
        return ensemble_forecasts
    
    def generate_campos_forecast(self, region: str = 'core_pampa', 
                               horizons: List[int] = [1, 2, 3]) -> Dict[int, EnsembleForecast]:
        """
        Generate complete forecast for agricultural land in specific region.
        
        Args:
            region: 'core_pampa', 'santa_fe', 'frontier', 'periurban'
            horizons: List of forecast years
            
        Returns:
            Dictionary mapping year to EnsembleForecast
        """
        # Regime detection (same for all segments)
        regime_info = self.regime_detector.detect_current_regime()
        regime_weights = {regime_info['current_regime']: regime_info['regime_probability']}
        
        # Regional Bayesian forecast
        bayesian_forecasts = self.campos_model.generate_regional_forecast(region, horizons, regime_weights)
        
        # Current regional land price (estimate based on calibration data)
        regional_prices = {
            'core_pampa': 16000,    # USD/ha
            'santa_fe': 11800,
            'frontier': 6500, 
            'periurban': 28000
        }
        current_price = regional_prices.get(region, 16000)
        
        ensemble_forecasts = {}
        
        for year in horizons:
            bayesian_forecast = bayesian_forecasts[year]
            
            # Apply Prospect Theory (agricultural investors also subject to behavioral biases)
            behavioral_adj = self.prospect_adjuster.adjust_posterior(
                bayesian_forecast.mean_change_pct,
                bayesian_forecast.distribution_params['sigma']
            )
            
            model_estimate = {
                'median_change_pct': bayesian_forecast.median_change_pct,
                'mean_change_pct': bayesian_forecast.mean_change_pct,
                'ci_80': bayesian_forecast.credible_interval_80,
                'ci_95': bayesian_forecast.credible_interval_95,
                'p_increase': bayesian_forecast.p_increase,
                'projected_price_ha': current_price * (1 + bayesian_forecast.median_change_pct / 100),
                'distribution_params': bayesian_forecast.distribution_params
            }
            
            behavioral_adjusted = {
                'median_change_pct': behavioral_adj.adjusted_median,
                'mean_change_pct': behavioral_adj.adjusted_mean,
                'ci_80': behavioral_adj.adjusted_ci_80,
                'ci_95': behavioral_adj.adjusted_ci_95,
                'p_increase': behavioral_adj.behavioral_p_increase,
                'p_decrease': behavioral_adj.behavioral_p_decrease,
                'projected_price_ha': current_price * (1 + behavioral_adj.adjusted_median / 100),
                'behavioral_narrative': self._create_behavioral_narrative(behavioral_adj)
            }
            
            # Agricultural-specific signals
            commodity_analysis = self.campos_model.get_commodity_correlation_analysis()
            campos_signals = [
                {
                    'title': f'Commodity prices: {commodity_analysis["interpretation"]}',
                    'impact': abs(commodity_analysis['composite_commodity_signal']) / 3.0,
                    'direction': 'positive' if commodity_analysis['composite_commodity_signal'] > 0 else 'negative',
                    'category': 'commodity_prices'
                }
            ]
            
            confidence_grade = self._assess_confidence(regime_info, bayesian_forecast, year)
            
            ensemble_forecasts[year] = EnsembleForecast(
                segment=f'campos_{region}',
                year=year,
                current_price=current_price,
                model_estimate=model_estimate,
                behavioral_adjusted=behavioral_adjusted,
                regime_context={
                    'current_regime': regime_info['current_regime'], 
                    'confidence': regime_info['regime_probability'],
                    'description': regime_info['description'],
                    'key_driver': f'Regional {region} dynamics + {commodity_analysis["current_regime"]}'
                },
                top_signals=campos_signals,
                generated_at=datetime.now().isoformat(),
                confidence_grade=confidence_grade
            )
        
        return ensemble_forecasts
    
    def generate_all_segments_summary(self) -> Dict[str, Dict]:
        """
        Generate summary forecast for all segments - optimized for dashboard header.
        
        Returns:
            Compact summary for dashboard display
        """
        # Quick forecasts for Year 1 only
        dept_forecast = self.generate_departamentos_forecast([1])
        campos_core_forecast = self.generate_campos_forecast('core_pampa', [1])
        
        regime_info = self.regime_detector.detect_current_regime()
        
        summary = {
            'regime': {
                'current': regime_info['current_regime'],
                'confidence': regime_info['regime_probability'],
                'description': regime_info['description']
            },
            'departamentos_caba': {
                'year_1_median_change': dept_forecast[1].model_estimate['median_change_pct'],
                'year_1_p_increase': dept_forecast[1].model_estimate['p_increase'],
                'current_price_m2': dept_forecast[1].current_price,
                'confidence_grade': dept_forecast[1].confidence_grade
            },
            'campos_core_pampa': {
                'year_1_median_change': campos_core_forecast[1].model_estimate['median_change_pct'],
                'year_1_p_increase': campos_core_forecast[1].model_estimate['p_increase'], 
                'current_price_ha': campos_core_forecast[1].current_price,
                'confidence_grade': campos_core_forecast[1].confidence_grade
            },
            'last_updated': datetime.now().isoformat()
        }
        
        return summary
    
    def generate_scenario_forecast(self, segment: str, scenario_params: Dict,
                                 horizons: List[int] = [1, 2, 3]) -> Dict[int, EnsembleForecast]:
        """
        Generate forecast under specific scenario assumptions.
        
        Args:
            segment: 'departamentos' or 'campos_{region}'
            scenario_params: Scenario parameter overrides
            horizons: Forecast years
            
        Returns:
            Scenario-adjusted forecasts
        """
        if segment == 'departamentos':
            scenario_forecasts = self.departamentos_model.generate_scenario_forecast(
                scenario_params, horizons
            )
            current_price = self.calibration_data.get_current_market_context()['current_price_usd_m2']
            
        elif segment.startswith('campos_'):
            region = segment.split('_')[1]  
            scenario_forecasts = self.campos_model.generate_scenario_forecast(
                region, scenario_params, horizons
            )
            regional_prices = {'core_pampa': 16000, 'santa_fe': 11800, 'frontier': 6500, 'periurban': 28000}
            current_price = regional_prices.get(region, 16000)
        else:
            raise ValueError(f"Unknown segment: {segment}")
        
        # Convert to EnsembleForecast format (simplified for scenarios)
        ensemble_scenarios = {}
        
        for year in horizons:
            forecast = scenario_forecasts[year]
            
            behavioral_adj = self.prospect_adjuster.adjust_posterior(
                forecast.mean_change_pct, forecast.distribution_params['sigma']
            )
            
            ensemble_scenarios[year] = EnsembleForecast(
                segment=segment,
                year=year,
                current_price=current_price,
                model_estimate={
                    'median_change_pct': forecast.median_change_pct,
                    'mean_change_pct': forecast.mean_change_pct,
                    'ci_80': forecast.credible_interval_80,
                    'p_increase': forecast.p_increase,
                    'scenario_adjusted': True
                },
                behavioral_adjusted={
                    'median_change_pct': behavioral_adj.adjusted_median,
                    'ci_80': behavioral_adj.adjusted_ci_80,
                    'p_increase': behavioral_adj.behavioral_p_increase
                },
                regime_context={'scenario_mode': True},
                top_signals=[],
                generated_at=datetime.now().isoformat(),
                confidence_grade='Scenario'
            )
            
        return ensemble_scenarios
    
    def _format_top_signals(self, signal_breakdown: Dict, segment: str) -> List[Dict]:
        """Format signal decomposition for user display"""
        signals = []
        
        for signal_name, signal_info in signal_breakdown.items():
            signals.append({
                'title': signal_info['interpretation'],
                'impact': abs(signal_info['contribution_pct']) / 10.0,  # Scale to [0,1]
                'direction': 'positive' if signal_info['contribution_pct'] > 0 else 'negative',
                'category': signal_name,
                'affected_segment': segment
            })
        
        # Sort by impact magnitude
        signals.sort(key=lambda x: x['impact'], reverse=True)
        
        return signals
    
    def _identify_key_driver(self, signal_breakdown: Dict) -> str:
        """Identify the primary driver of current forecast"""
        max_impact = 0
        key_signal = ""
        
        for signal_name, signal_info in signal_breakdown.items():
            impact = abs(signal_info['contribution_pct'])
            if impact > max_impact:
                max_impact = impact
                key_signal = signal_name
        
        driver_descriptions = {
            'credit_expansion': 'BCRA rate cuts driving credit expansion',
            'transaction_momentum': 'Strong transaction volume growth (+45% YoY)', 
            'inflation_adjusted_demand': 'Real income recovery as inflation declines',
            'commodity_prices': 'Commodity price momentum affecting rural land values',
            'export_tax_policy': 'Agricultural export tax policy environment'
        }
        
        return driver_descriptions.get(key_signal, f'{key_signal.replace("_", " ").title()} dynamics')
    
    def _create_behavioral_narrative(self, behavioral_adj: BehavioralDistribution) -> str:
        """Create narrative explaining behavioral adjustments"""
        if abs(behavioral_adj.loss_aversion_effect) < 0.5:
            return "Behavioral adjustments minimal given current market confidence"
        else:
            return f"Argentine loss aversion (λ=2.25) reduces expected returns by {abs(behavioral_adj.loss_aversion_effect):.1f}pp"
    
    def _assess_confidence(self, regime_info: Dict, bayesian_forecast: ForecastDistribution, year: int) -> str:
        """Assess overall confidence in forecast"""
        regime_confidence = regime_info['regime_probability']
        forecast_uncertainty = bayesian_forecast.distribution_params['sigma']
        
        # Confidence decreases with horizon and uncertainty
        base_confidence = regime_confidence * (1.0 - (year - 1) * 0.15)  # Decay with horizon
        
        if forecast_uncertainty > 5.0:  # High uncertainty
            base_confidence *= 0.8
        elif forecast_uncertainty < 3.0:  # Low uncertainty
            base_confidence *= 1.1
        
        base_confidence = min(1.0, max(0.0, base_confidence))
        
        if base_confidence > 0.8:
            return 'High'
        elif base_confidence > 0.6:
            return 'Medium'
        else:
            return 'Low'
    
    def get_health_status(self) -> Dict[str, any]:
        """Return system health and data freshness status"""
        return {
            'models_initialized': True,
            'regime_detector_trained': self.regime_detector.is_trained,
            'calibration_data_loaded': True,
            'last_regime_detection': datetime.now().isoformat(),
            'hmm_available': getattr(self.regime_detector, 'model', None) is not None,
            'system_status': 'operational'
        }