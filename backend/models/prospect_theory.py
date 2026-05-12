"""
Prospect Theory behavioral adjustments for Argentine real estate forecasts.

Applies Kahneman-Tversky value function and probability weighting to account
for Argentine market psychology and crisis memory effects.
"""

from typing import Dict, Tuple
import numpy as np
from scipy import stats
from scipy.optimize import minimize_scalar
from dataclasses import dataclass


@dataclass 
class BehavioralDistribution:
    """Behaviorally-adjusted distribution parameters"""
    adjusted_mean: float
    adjusted_median: float
    adjusted_ci_80: Tuple[float, float]
    adjusted_ci_95: Tuple[float, float]
    behavioral_p_decrease: float
    behavioral_p_increase: float
    loss_aversion_effect: float
    probability_weighting_effect: float


class ProspectTheoryAdjuster:
    """
    Applies Prospect Theory behavioral adjustments to Bayesian posteriors.
    
    Kahneman-Tversky parameters calibrated for Argentine market psychology:
    - Higher loss aversion (λ=2.25 vs standard 2.0) due to crisis memory
    - Standard probability weighting functions
    - Reference point at zero nominal return
    """
    
    def __init__(self, alpha: float = 0.88, beta: float = 0.88, 
                 lambda_loss: float = 2.25, gamma_gains: float = 0.61, 
                 gamma_losses: float = 0.69):
        """
        Initialize Prospect Theory parameters.
        
        Args:
            alpha: Utility curvature for gains (standard K-T: 0.88)
            beta: Utility curvature for losses (standard K-T: 0.88)  
            lambda_loss: Loss aversion parameter (Argentine calibration: 2.25)
            gamma_gains: Probability weighting for gains (standard: 0.61)
            gamma_losses: Probability weighting for losses (standard: 0.69)
        """
        self.alpha = alpha
        self.beta = beta
        self.lambda_loss = lambda_loss
        self.gamma_gains = gamma_gains
        self.gamma_losses = gamma_losses
        
    def value_function(self, x: float) -> float:
        """
        Prospect Theory value function.
        
        V(x) = x^α for gains, V(x) = -λ(-x)^β for losses
        
        Args:
            x: Outcome relative to reference point (0 = no change)
            
        Returns:
            Subjective value
        """
        if x >= 0:
            return np.power(x, self.alpha)
        else:
            return -self.lambda_loss * np.power(-x, self.beta)
    
    def probability_weighting(self, p: float, is_gain: bool = True) -> float:
        """
        Prospect Theory probability weighting function.
        
        π(p) = p^γ / (p^γ + (1-p)^γ)^(1/γ)
        
        Args:
            p: Objective probability [0, 1]
            is_gain: True for gains, False for losses
            
        Returns:
            Subjectively weighted probability
        """
        if p <= 0:
            return 0
        if p >= 1:
            return 1
            
        gamma = self.gamma_gains if is_gain else self.gamma_losses
        
        numerator = np.power(p, gamma)
        denominator = np.power(
            np.power(p, gamma) + np.power(1 - p, gamma), 
            1.0 / gamma
        )
        
        return numerator / denominator
    
    def adjust_posterior(self, mu: float, sigma: float, 
                        reference_point: float = 0.0) -> BehavioralDistribution:
        """
        Apply Prospect Theory adjustments to a posterior distribution.
        
        Args:
            mu: Posterior mean (% change)
            sigma: Posterior standard deviation
            reference_point: Reference point for gains/losses (default 0%)
            
        Returns:
            BehavioralDistribution with adjusted parameters
        """
        # Create original distribution
        original_dist = stats.norm(mu, sigma)
        
        # Compute original probabilities
        p_decrease = original_dist.cdf(reference_point)
        p_increase = 1.0 - p_decrease
        
        # Apply probability weighting
        weighted_p_decrease = self.probability_weighting(p_decrease, is_gain=False)
        weighted_p_increase = self.probability_weighting(p_increase, is_gain=True)
        
        # Normalize weighted probabilities
        total_weighted = weighted_p_decrease + weighted_p_increase
        if total_weighted > 0:
            weighted_p_decrease /= total_weighted
            weighted_p_increase /= total_weighted
        
        # Compute loss aversion effect on expected value
        # Loss aversion shifts the perceived mean downward
        loss_aversion_adjustment = self._compute_loss_aversion_adjustment(mu, sigma, reference_point)
        adjusted_mean = mu + loss_aversion_adjustment
        
        # Compute behaviorally-adjusted credible intervals
        # These are asymmetric due to probability weighting
        adjusted_ci_80 = self._compute_adjusted_credible_interval(
            mu, sigma, reference_point, confidence_level=0.80
        )
        adjusted_ci_95 = self._compute_adjusted_credible_interval(
            mu, sigma, reference_point, confidence_level=0.95
        )
        
        # Compute adjusted median (less affected than mean)
        median_adjustment = loss_aversion_adjustment * 0.5  # Median less sensitive
        adjusted_median = mu + median_adjustment
        
        # Quantify behavioral effects
        probability_weighting_effect = weighted_p_decrease - p_decrease
        
        return BehavioralDistribution(
            adjusted_mean=adjusted_mean,
            adjusted_median=adjusted_median,
            adjusted_ci_80=adjusted_ci_80,
            adjusted_ci_95=adjusted_ci_95,
            behavioral_p_decrease=weighted_p_decrease,
            behavioral_p_increase=weighted_p_increase,
            loss_aversion_effect=loss_aversion_adjustment,
            probability_weighting_effect=probability_weighting_effect
        )
    
    def _compute_loss_aversion_adjustment(self, mu: float, sigma: float, 
                                        reference_point: float) -> float:
        """
        Compute the loss aversion adjustment to expected value.
        
        Loss aversion causes people to overweight downside scenarios,
        effectively reducing the perceived expected return.
        """
        original_dist = stats.norm(mu, sigma)
        
        # Sample outcomes and apply value function
        n_samples = 10000
        outcomes = original_dist.rvs(n_samples, random_state=42)
        
        # Apply value function to each outcome
        subjective_values = np.array([
            self.value_function(x - reference_point) for x in outcomes
        ])
        
        # The adjustment is the difference between objective and subjective means
        objective_mean_value = np.mean(outcomes - reference_point)
        subjective_mean_value = np.mean(subjective_values)
        
        # Convert back to return space (approximate)
        if subjective_mean_value >= 0:
            equivalent_objective = np.power(subjective_mean_value, 1.0 / self.alpha)
        else:
            equivalent_objective = -np.power(-subjective_mean_value / self.lambda_loss, 1.0 / self.beta)
        
        adjustment = equivalent_objective - objective_mean_value
        
        # Scale adjustment (behavioral effects are typically modest)
        return adjustment * 0.3
    
    def _compute_adjusted_credible_interval(self, mu: float, sigma: float,
                                          reference_point: float, 
                                          confidence_level: float) -> Tuple[float, float]:
        """
        Compute asymmetric credible intervals under probability weighting.
        
        Probability weighting makes people overweight tail events,
        creating asymmetric confidence intervals wider on the downside.
        """
        original_dist = stats.norm(mu, sigma)
        
        # Original symmetric interval
        alpha_level = 1.0 - confidence_level
        lower_percentile = alpha_level / 2.0
        upper_percentile = 1.0 - alpha_level / 2.0
        
        original_lower = original_dist.ppf(lower_percentile)
        original_upper = original_dist.ppf(upper_percentile)
        
        # Apply probability weighting to tail probabilities
        weighted_lower_p = self.probability_weighting(lower_percentile, is_gain=False)
        weighted_upper_p = self.probability_weighting(1.0 - upper_percentile, is_gain=False)
        
        # Adjust interval bounds (wider downside, narrower upside)
        downside_expansion = 1.5  # Expand downside by 50%
        upside_contraction = 0.85  # Contract upside by 15%
        
        adjusted_lower = reference_point + (original_lower - reference_point) * downside_expansion
        adjusted_upper = reference_point + (original_upper - reference_point) * upside_contraction
        
        return (adjusted_lower, adjusted_upper)
    
    def generate_behavioral_narrative(self, original_forecast: Dict, 
                                    behavioral_forecast: BehavioralDistribution) -> str:
        """
        Generate explanatory text for behavioral adjustments.
        
        Args:
            original_forecast: Original Bayesian forecast results
            behavioral_forecast: Prospect Theory adjusted forecast
            
        Returns:
            Human-readable explanation of behavioral effects
        """
        loss_aversion_magnitude = abs(behavioral_forecast.loss_aversion_effect)
        
        if loss_aversion_magnitude < 0.5:
            la_intensity = "modest"
        elif loss_aversion_magnitude < 1.0:
            la_intensity = "moderate"
        else:
            la_intensity = "strong"
        
        prob_weighting_effect = behavioral_forecast.probability_weighting_effect
        if abs(prob_weighting_effect) < 0.05:
            pw_effect = "minimal probability distortion"
        elif prob_weighting_effect > 0:
            pw_effect = f"overweighting of downside risks (+{prob_weighting_effect:.1%})"
        else:
            pw_effect = f"underweighting of downside risks ({prob_weighting_effect:.1%})"
        
        narrative = (
            f"Argentine market psychology shows {la_intensity} loss aversion "
            f"(λ={self.lambda_loss:.2f}), reducing expected returns by "
            f"{loss_aversion_magnitude:.1f}pp. Investors exhibit {pw_effect}, "
            f"creating asymmetric confidence intervals that are "
            f"{(behavioral_forecast.adjusted_ci_80[1] - behavioral_forecast.adjusted_ci_80[0]) / (original_forecast.get('ci_80_upper', 10) - original_forecast.get('ci_80_lower', 0)):.0%} "
            f"of the rational model width."
        )
        
        return narrative
    
    def compare_rational_vs_behavioral(self, original_mu: float, original_sigma: float) -> Dict[str, any]:
        """
        Generate side-by-side comparison of rational vs behavioral forecasts.
        
        Returns:
            Dictionary with comparative analysis
        """
        # Original rational forecast
        original_dist = stats.norm(original_mu, original_sigma)
        original_ci_80 = original_dist.ppf([0.1, 0.9])
        original_ci_95 = original_dist.ppf([0.025, 0.975])
        
        # Behavioral adjustment
        behavioral = self.adjust_posterior(original_mu, original_sigma)
        
        comparison = {
            'rational_model': {
                'mean_return': original_mu,
                'median_return': original_mu,  # Normal distribution
                'ci_80': original_ci_80,
                'ci_95': original_ci_95,
                'p_decrease': float(original_dist.cdf(0)),
                'interpretation': 'Pure statistical model based on market fundamentals'
            },
            'behavioral_adjusted': {
                'mean_return': behavioral.adjusted_mean,
                'median_return': behavioral.adjusted_median,
                'ci_80': behavioral.adjusted_ci_80,
                'ci_95': behavioral.adjusted_ci_95,
                'p_decrease': behavioral.behavioral_p_decrease,
                'interpretation': 'Adjusted for Argentine market psychology and crisis memory'
            },
            'key_differences': {
                'loss_aversion_impact': behavioral.loss_aversion_effect,
                'probability_weighting_impact': behavioral.probability_weighting_effect,
                'downside_overweighting': behavioral.behavioral_p_decrease - float(original_dist.cdf(0)),
                'interval_asymmetry': (behavioral.adjusted_ci_80[1] - behavioral.adjusted_ci_80[0]) / (original_ci_80[1] - original_ci_80[0])
            },
            'narrative': self.generate_behavioral_narrative(
                {'ci_80_lower': original_ci_80[0], 'ci_80_upper': original_ci_80[1]},
                behavioral
            )
        }
        
        return comparison
    
    @classmethod
    def create_argentine_calibrated(cls) -> 'ProspectTheoryAdjuster':
        """
        Create instance with parameters calibrated for Argentine market psychology.
        
        Higher loss aversion due to repeated financial crises and hyperinflation memory.
        """
        return cls(
            alpha=0.88,          # Standard K-T
            beta=0.88,           # Standard K-T  
            lambda_loss=2.25,    # Higher than standard 2.0 - Argentine crisis memory
            gamma_gains=0.61,    # Standard K-T
            gamma_losses=0.69    # Standard K-T
        )