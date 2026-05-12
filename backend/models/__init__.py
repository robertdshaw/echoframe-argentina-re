"""
EchoFrame Argentina Real Estate Intelligence - Predictive Models Package

This package contains the core probabilistic models for forecasting 
Buenos Aires apartment prices and Argentine agricultural land prices:

- Bayesian inference models with conjugate updating
- Hidden Markov Models for regime detection
- Prospect Theory behavioral adjustments
- Ensemble integration for final forecasts
"""

from .calibration_data import CalibrationData
from .bayesian_departamentos import BayesianDepartamentosModel
from .bayesian_campos import BayesianCamposModel
from .hmm_regime import HMMRegimeDetector
from .prospect_theory import ProspectTheoryAdjuster
from .ensemble import EnsembleForecaster

__all__ = [
    'CalibrationData',
    'BayesianDepartamentosModel', 
    'BayesianCamposModel',
    'HMMRegimeDetector',
    'ProspectTheoryAdjuster',
    'EnsembleForecaster'
]