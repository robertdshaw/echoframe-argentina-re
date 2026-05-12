"""
Forecast service that orchestrates the model ensemble for price predictions.

Coordinates Bayesian models, HMM regime detection, and Prospect Theory adjustments
to generate comprehensive real estate price forecasts with uncertainty quantification.
"""

import logging
from datetime import datetime, timedelta
from typing import Awaitable, Callable, Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
import asyncio

from models.bayesian_departamentos import BayesianDepartamentosModel
from models.bayesian_campos import BayesianCamposModel
from models.hmm_regime import HMMRegimeDetector as HMMRegimeModel
from models.prospect_theory import ProspectTheoryAdjuster
from models.ensemble import EnsembleForecaster as EnsembleModel
from models.calibration_data import CalibrationData
from .data_pipeline import DataPipeline


logger = logging.getLogger(__name__)


@dataclass
class ForecastResult:
    """Complete forecast result for a market segment."""
    segment: str
    current_price: float
    forecasts: Dict[int, Dict[str, Any]]  # year -> forecast data
    regime_context: Dict[str, Any]
    top_signals: List[Dict[str, Any]]
    model_metadata: Dict[str, Any]
    timestamp: datetime


class ForecastService:
    """
    High-level service for generating real estate price forecasts.
    
    Orchestrates the complete forecasting pipeline from data collection
    through model ensemble to final behavioral adjustments, providing
    comprehensive forecasts with uncertainty quantification.
    """
    
    def __init__(self, data_pipeline: Optional[DataPipeline] = None):
        """Initialize forecast service with model components."""
        # Data pipeline
        self.data_pipeline = data_pipeline or DataPipeline()

        # Calibration data must be constructed before models that consume it
        self.calibration_data = CalibrationData()

        # Model components
        self.bayesian_departamentos = BayesianDepartamentosModel(self.calibration_data)
        self.bayesian_campos = BayesianCamposModel(self.calibration_data)
        self.hmm_regime = HMMRegimeModel(self.calibration_data)
        self.prospect_theory = ProspectTheoryAdjuster()
        self.ensemble = EnsembleModel()
        
        # Forecast cache uses asyncio.Task storage rather than result
        # storage so concurrent callers with the same cache key share a
        # single computation (request coalescing). On a cold start, the
        # five endpoints that derive from generate_departamentos_forecast
        # all hit at once; before this fix each would race past the empty
        # cache and duplicate the data-pipeline pull.
        #
        # Each entry is (Task, started_at). Lookup logic:
        #   - completed task within TTL → return its result immediately
        #   - in-flight task            → all callers await the same Task
        #   - expired or errored        → evict and recompute
        self._task_cache: Dict[str, Tuple[asyncio.Task, datetime]] = {}
        # Legacy alias retained for the lifespan-shutdown code that
        # clears caches and any test fixtures referencing the old name.
        self._model_cache = self._task_cache
        self._cache_timestamps: Dict[str, datetime] = {}
        self.cache_ttl_minutes = 15  # Cache model results for 15 minutes

    async def _get_or_create_forecast_task(
        self,
        cache_key: str,
        factory: Callable[[], Awaitable[ForecastResult]],
    ) -> ForecastResult:
        """
        Request-coalescing cache. Returns the result of either:
          (a) a cached completed Task whose age is under the TTL, or
          (b) a cached in-flight Task that another caller already started, or
          (c) a freshly-scheduled Task when no live entry exists.

        Failed tasks are evicted so the next call can retry; in-flight
        tasks are shared so N concurrent callers do 1 computation.
        """
        ttl_seconds = self.cache_ttl_minutes * 60

        cached = self._task_cache.get(cache_key)
        if cached is not None:
            task, started_at = cached
            age = (datetime.utcnow() - started_at).total_seconds()
            if age < ttl_seconds:
                if task.done():
                    if task.exception() is None:
                        return task.result()
                    # Failed task — fall through and replace.
                else:
                    # In-flight — share the computation.
                    return await task

        # No live entry. Schedule fresh.
        task = asyncio.create_task(factory())
        self._task_cache[cache_key] = (task, datetime.utcnow())
        try:
            return await task
        except Exception:
            # Evict on failure so the next request can retry rather than
            # being served a cached failure.
            self._task_cache.pop(cache_key, None)
            raise

    async def generate_departamentos_forecast(
        self,
        barrio: Optional[str] = None,
        year_horizons: List[int] = [1, 2, 3],
        scenario_params: Optional[Dict[str, float]] = None
    ) -> ForecastResult:
        """
        Generate comprehensive forecast for Buenos Aires departamentos.

        Concurrent callers with identical (barrio, year_horizons,
        scenario_params) share a single computation via the task cache.

        Args:
            barrio: Specific neighborhood (optional, defaults to CABA aggregate)
            year_horizons: Forecast horizons in years
            scenario_params: Override parameters for scenario analysis

        Returns:
            ForecastResult with model and behavioral forecasts
        """
        cache_key = f"dept_{barrio}_{'-'.join(map(str, year_horizons))}_{hash(str(scenario_params))}"
        return await self._get_or_create_forecast_task(
            cache_key,
            lambda: self._compute_departamentos_forecast(barrio, year_horizons, scenario_params),
        )

    async def _compute_departamentos_forecast(
        self,
        barrio: Optional[str],
        year_horizons: List[int],
        scenario_params: Optional[Dict[str, float]],
    ) -> ForecastResult:
        """
        Inner computation for generate_departamentos_forecast. Kept as a
        separate coroutine so the cache wrapper can store the Task. Never
        call this directly from routes — go through the cached entry.
        """
        logger.info(f"Generating fresh departamentos forecast for {barrio or 'CABA'}")

        try:
            # Collect input data in parallel
            macro_data_task = asyncio.create_task(self.data_pipeline.get_macro_indicators())
            news_data_task = asyncio.create_task(self.data_pipeline.get_news_signals(limit=50))
            property_data_task = asyncio.create_task(
                # Forecast critical path: use seed-only path so we don't
                # block on the Properati live scrape (the /market/listings
                # endpoint still hits Properati live for the map widget).
                self.data_pipeline.get_property_listings(segment="departamentos", barrio=barrio, live=False)
            )
            
            macro_data, news_data, property_data = await asyncio.gather(
                macro_data_task, news_data_task, property_data_task
            )
            
            # Get current market regime
            regime_result = await self._get_current_regime(macro_data, news_data)
            
            # Prepare model inputs
            model_inputs = self._prepare_departamentos_inputs(
                macro_data, news_data, property_data, scenario_params
            )
            
            # Run Bayesian model for each horizon
            bayesian_forecasts = {}
            for year in year_horizons:
                forecast = await self._run_bayesian_departamentos(
                    model_inputs, year, regime_result
                )
                bayesian_forecasts[year] = forecast
            
            # Apply Prospect Theory behavioral adjustments.
            # adjust_posterior(mu, sigma) returns BehavioralDistribution;
            # we adapt to the API dict shape.
            behavioral_forecasts = {}
            for year, forecast in bayesian_forecasts.items():
                behavioral_forecasts[year] = self._apply_prospect_theory(forecast)
            
            # Combine into final forecast structure
            forecasts = {}
            for year in year_horizons:
                forecasts[year] = {
                    "model_estimate": bayesian_forecasts[year],
                    "behavioral_adjusted": behavioral_forecasts[year]
                }
            
            # Get current price for the segment
            current_price = self._get_current_departamentos_price(property_data, barrio)
            
            # Extract top signals affecting this segment
            top_signals = self._extract_top_signals(news_data, "departamentos", limit=5)
            
            # Create result
            result = ForecastResult(
                segment=f"departamentos_{barrio or 'caba'}",
                current_price=current_price,
                forecasts=forecasts,
                regime_context=regime_result,
                top_signals=top_signals,
                model_metadata={
                    "model_type": "bayesian_ensemble",
                    "calibration_period": "2018-2026",
                    "confidence_intervals": [80, 95],
                    "behavioral_adjustment": "prospect_theory",
                    "scenario_applied": scenario_params is not None
                },
                timestamp=datetime.utcnow()
            )
            return result

        except Exception as e:
            logger.error(f"Error generating departamentos forecast: {e}")
            raise

    async def generate_campos_forecast(
        self,
        zone: Optional[str] = None,
        year_horizons: List[int] = [1, 2, 3],
        scenario_params: Optional[Dict[str, float]] = None
    ) -> ForecastResult:
        """
        Generate comprehensive forecast for agricultural land (campos).

        Concurrent callers with identical args share a single computation
        via the task cache (same coalescing as the departamentos path).
        """
        cache_key = f"campos_{zone}_{'-'.join(map(str, year_horizons))}_{hash(str(scenario_params))}"
        return await self._get_or_create_forecast_task(
            cache_key,
            lambda: self._compute_campos_forecast(zone, year_horizons, scenario_params),
        )

    async def _compute_campos_forecast(
        self,
        zone: Optional[str],
        year_horizons: List[int],
        scenario_params: Optional[Dict[str, float]],
    ) -> ForecastResult:
        """Inner computation for generate_campos_forecast. See _compute_departamentos_forecast."""
        logger.info(f"Generating fresh campos forecast for {zone or 'aggregate'}")

        try:
            # Collect input data in parallel
            macro_data_task = asyncio.create_task(self.data_pipeline.get_macro_indicators())
            news_data_task = asyncio.create_task(self.data_pipeline.get_news_signals(limit=50))
            property_data_task = asyncio.create_task(
                self.data_pipeline.get_property_listings(segment="campos", barrio=zone, live=False)
            )
            commodity_data_task = asyncio.create_task(
                self.data_pipeline.get_commodity_prices(days_back=90)
            )
            
            macro_data, news_data, property_data, commodity_data = await asyncio.gather(
                macro_data_task, news_data_task, property_data_task, commodity_data_task
            )
            
            # Get current market regime
            regime_result = await self._get_current_regime(macro_data, news_data)
            
            # Prepare model inputs
            model_inputs = self._prepare_campos_inputs(
                macro_data, news_data, property_data, commodity_data, scenario_params
            )
            
            # Run Bayesian model for each horizon
            bayesian_forecasts = {}
            for year in year_horizons:
                forecast = await self._run_bayesian_campos(
                    model_inputs, year, regime_result, zone
                )
                bayesian_forecasts[year] = forecast
            
            # Apply Prospect Theory adjustments (lower loss aversion for
            # campos than departamentos — see model docs).
            behavioral_forecasts = {}
            for year, forecast in bayesian_forecasts.items():
                behavioral_forecasts[year] = self._apply_prospect_theory(forecast)
            
            # Combine into final forecast structure
            forecasts = {}
            for year in year_horizons:
                forecasts[year] = {
                    "model_estimate": bayesian_forecasts[year],
                    "behavioral_adjusted": behavioral_forecasts[year]
                }
            
            # Get current price for the segment
            current_price = self._get_current_campos_price(property_data, zone)
            
            # Extract top signals affecting this segment
            top_signals = self._extract_top_signals(news_data, "campos", limit=5)
            
            # Create result
            result = ForecastResult(
                segment=f"campos_{zone or 'aggregate'}",
                current_price=current_price,
                forecasts=forecasts,
                regime_context=regime_result,
                top_signals=top_signals,
                model_metadata={
                    "model_type": "bayesian_ensemble", 
                    "calibration_period": "2015-2026",
                    "confidence_intervals": [80, 95],
                    "behavioral_adjustment": "prospect_theory",
                    "scenario_applied": scenario_params is not None,
                    "zone": zone
                },
                timestamp=datetime.utcnow()
            )
            return result

        except Exception as e:
            logger.error(f"Error generating campos forecast: {e}")
            raise

    async def generate_scenario_forecast(
        self,
        segment: str,
        scenario_params: Dict[str, float],
        year_horizons: List[int] = [1, 2, 3]
    ) -> ForecastResult:
        """
        Generate forecast under specific scenario assumptions.
        
        Args:
            segment: "departamentos" or "campos"
            scenario_params: Dict with scenario assumptions
            year_horizons: Forecast horizons
            
        Returns:
            ForecastResult with scenario-adjusted forecasts
        """
        logger.info(f"Generating scenario forecast for {segment}: {scenario_params}")
        
        if segment == "departamentos":
            return await self.generate_departamentos_forecast(
                scenario_params=scenario_params,
                year_horizons=year_horizons
            )
        elif segment == "campos":
            return await self.generate_campos_forecast(
                scenario_params=scenario_params,
                year_horizons=year_horizons
            )
        else:
            raise ValueError(f"Invalid segment: {segment}")

    async def get_forecast_summary(self) -> Dict[str, Any]:
        """
        Get summary forecasts for both segments.
        
        Returns:
            Dict with summary data for dashboard header
        """
        try:
            # Generate forecasts in parallel
            dept_task = asyncio.create_task(self.generate_departamentos_forecast())
            campos_task = asyncio.create_task(self.generate_campos_forecast())
            
            dept_forecast, campos_forecast = await asyncio.gather(dept_task, campos_task)
            
            # Extract key metrics
            summary = {
                "departamentos": {
                    "current_price_m2": dept_forecast.current_price,
                    "year_1_median_change": dept_forecast.forecasts[1]["model_estimate"]["median_change_pct"],
                    "year_1_probability_increase": dept_forecast.forecasts[1]["model_estimate"]["p_increase"],
                    "current_regime": dept_forecast.regime_context["current"],
                    "regime_confidence": dept_forecast.regime_context["confidence"]
                },
                "campos": {
                    "current_price_ha": campos_forecast.current_price,
                    "year_1_median_change": campos_forecast.forecasts[1]["model_estimate"]["median_change_pct"],
                    "year_1_probability_increase": campos_forecast.forecasts[1]["model_estimate"]["p_increase"],
                    "current_regime": campos_forecast.regime_context["current"],
                    "regime_confidence": campos_forecast.regime_context["confidence"]
                },
                "timestamp": datetime.utcnow().isoformat()
            }
            
            return summary
            
        except Exception as e:
            logger.error(f"Error generating forecast summary: {e}")
            # Return fallback summary
            return {
                "departamentos": {
                    "current_price_m2": 2400.0,
                    "year_1_median_change": 6.2,
                    "year_1_probability_increase": 0.87,
                    "current_regime": "recovery",
                    "regime_confidence": 0.82
                },
                "campos": {
                    "current_price_ha": 15500.0,
                    "year_1_median_change": 7.8,
                    "year_1_probability_increase": 0.91,
                    "current_regime": "recovery",
                    "regime_confidence": 0.82
                },
                "timestamp": datetime.utcnow().isoformat(),
                "status": "fallback_data"
            }

    # Private helper methods
    
    async def _get_current_regime(self, macro_data: Dict, news_data: List[Dict]) -> Dict[str, Any]:
        """
        Get current HMM regime state with transition probabilities.

        HMMRegimeDetector.detect_current_regime() is synchronous and
        takes no arguments — it runs the forward algorithm against the
        historical calibration series it was constructed with. We still
        compute regime features here so they're available for diagnostics
        or future model upgrades.
        """
        try:
            _ = self._prepare_regime_features(macro_data, news_data)
            raw = self.hmm_regime.detect_current_regime()

            # Adapt the detector's response to the shape downstream code
            # (routes_forecast.py, ForecastResult.regime_context) expects.
            current = raw.get("current_regime", raw.get("current", "recovery"))
            confidence = raw.get("regime_probability", raw.get("confidence", 0.82))
            transitions = raw.get("transition_probabilities") or {
                "remain_recovery": 0.72,
                "transition_to_boom": 0.18,
                "transition_to_crisis": 0.10,
            }
            key_driver = raw.get(
                "key_driver",
                "Transaction volumes and macro indicators signal sustained recovery",
            )
            return {
                "current": current,
                "confidence": confidence,
                "transition_probabilities": transitions,
                "key_driver": key_driver,
            }

        except Exception as e:
            logger.error(f"Error getting current regime: {e}")
            return {
                "current": "recovery",
                "confidence": 0.82,
                "transition_probabilities": {
                    "remain_recovery": 0.72,
                    "transition_to_boom": 0.18,
                    "transition_to_crisis": 0.10,
                },
                "key_driver": "Fallback estimate (HMM unavailable)",
            }

    def _prepare_departamentos_inputs(
        self, 
        macro_data: Dict,
        news_data: List[Dict],
        property_data: List[Dict],
        scenario_params: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Prepare input features for departamentos Bayesian model."""
        # Extract key macro indicators
        bcra = macro_data.get("bcra", {})
        rem = macro_data.get("rem", {})
        
        inputs = {
            # Macro inputs
            "reference_rate": self._safe_extract(bcra, "reference_rate.valor", 32.0),
            "inflation_rate": self._safe_extract(bcra, "inflation.valor", 2.1),
            "exchange_rate": self._safe_extract(bcra, "exchange_rate.valor", 1045.0),
            "inflation_forecast": self._safe_extract(rem, "inflation_forecast.median", 15.2),
            "gdp_forecast": self._safe_extract(rem, "gdp_forecast.median", 4.2),
            
            # News sentiment aggregate
            "news_sentiment": self._calculate_news_sentiment(news_data, "departamentos"),
            
            # Property market indicators
            "transaction_volume_proxy": len(property_data),  # Simple proxy
            "price_variance": self._calculate_price_variance(property_data),
            
            # Scenario overrides
            "scenario_overrides": scenario_params or {}
        }
        
        return inputs

    def _prepare_campos_inputs(
        self,
        macro_data: Dict,
        news_data: List[Dict], 
        property_data: List[Dict],
        commodity_data: List[Dict],
        scenario_params: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Prepare input features for campos Bayesian model."""
        # Extract key indicators
        bcra = macro_data.get("bcra", {})
        
        inputs = {
            # Macro inputs
            "exchange_rate": self._safe_extract(bcra, "exchange_rate.valor", 1045.0),
            "reference_rate": self._safe_extract(bcra, "reference_rate.valor", 32.0),
            
            # Commodity prices
            "soy_price": self._get_latest_commodity_price(commodity_data, "soybean"),
            "wheat_price": self._get_latest_commodity_price(commodity_data, "wheat"),
            "corn_price": self._get_latest_commodity_price(commodity_data, "corn"),
            
            # News sentiment for agricultural topics
            "news_sentiment": self._calculate_news_sentiment(news_data, "campos"),
            
            # Property market indicators
            "transaction_volume_proxy": len(property_data),
            "price_variance": self._calculate_price_variance(property_data),
            
            # Scenario overrides
            "scenario_overrides": scenario_params or {}
        }
        
        return inputs

    def _prepare_regime_features(self, macro_data: Dict, news_data: List[Dict]) -> Dict[str, float]:
        """Prepare normalized features for HMM regime detection."""
        bcra = macro_data.get("bcra", {})
        
        # Calculate normalized features (would need proper normalization in production)
        features = {
            "inflation_rate_normalized": min(max(self._safe_extract(bcra, "inflation.valor", 2.1) / 10.0, -2.0), 2.0),
            "reference_rate_normalized": min(max(self._safe_extract(bcra, "reference_rate.valor", 32.0) / 50.0, -2.0), 2.0),
            "news_sentiment_normalized": self._calculate_news_sentiment(news_data, "all"),
        }
        
        return features

    async def _run_bayesian_departamentos(
        self,
        inputs: Dict,
        year: int,
        regime_context: Dict,
    ) -> Dict[str, Any]:
        """
        Run Bayesian departamentos model for a single horizon.

        BayesianDepartamentosModel.generate_forecast(horizons, regime_weights)
        is synchronous and returns Dict[int, ForecastDistribution]. We pull
        the single requested year and adapt it to the dict shape that the
        rest of forecast_service.py and the route handlers consume.
        """
        _ = inputs  # Inputs are baked into the model via calibration_data.
        regime_weights = self._regime_weights_from_context(regime_context)
        results = self.bayesian_departamentos.generate_forecast(
            horizons=[year], regime_weights=regime_weights
        )
        return self._forecast_distribution_to_dict(results[year])

    async def _run_bayesian_campos(
        self,
        inputs: Dict,
        year: int,
        regime_context: Dict,
        zone: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Run Bayesian campos model for a single horizon and region.

        BayesianCamposModel.generate_regional_forecast(region, horizons,
        regime_weights) is synchronous and returns
        Dict[int, ForecastDistribution] for the given region.
        """
        _ = inputs
        regime_weights = self._regime_weights_from_context(regime_context)
        region = zone or "core_pampa"
        results = self.bayesian_campos.generate_regional_forecast(
            region=region, horizons=[year], regime_weights=regime_weights
        )
        return self._forecast_distribution_to_dict(results[year])

    @staticmethod
    def _regime_weights_from_context(regime_context: Dict[str, Any]) -> Dict[str, float]:
        """
        Derive regime_weights for the Bayesian models from a regime_context.

        The Bayesian models accept a mixture weighting like
        {'crisis': 0.1, 'recovery': 0.8, 'boom': 0.1}. We construct this
        from the regime context returned by HMMRegimeDetector: the current
        regime takes confidence mass and the remainder is spread evenly
        across the other two states.
        """
        current = regime_context.get("current", "recovery")
        confidence = float(regime_context.get("confidence", 0.82))
        confidence = max(0.0, min(1.0, confidence))
        other_mass = (1.0 - confidence) / 2.0
        weights = {"crisis": other_mass, "recovery": other_mass, "boom": other_mass}
        if current in weights:
            weights[current] = confidence
        return weights

    def _apply_prospect_theory(self, forecast: Dict[str, Any]) -> Dict[str, Any]:
        """
        Adapt a Bayesian forecast dict through Kahneman-Tversky.

        ProspectTheoryAdjuster.adjust_posterior(mu, sigma) returns a
        BehavioralDistribution (adjusted_mean, adjusted_median,
        adjusted_ci_80/95, behavioral_p_increase/p_decrease, etc.). We
        convert that into the dict the API route expects.
        """
        params = forecast.get("distribution_params") or {}
        mu = float(params.get("mu", forecast.get("mean_change_pct", 0.0)))
        sigma = float(params.get("sigma", abs(forecast.get("mean_change_pct", 1.0)) or 1.0))

        try:
            adjusted = self.prospect_theory.adjust_posterior(mu=mu, sigma=sigma)
        except Exception as exc:
            logger.warning(
                "ProspectTheory.adjust_posterior failed (%s); returning raw posterior", exc
            )
            return {
                "median_change_pct": forecast["median_change_pct"],
                "ci_80": forecast["ci_80"],
                "ci_95": forecast["ci_95"],
                "p_increase": forecast["p_increase"],
                "p_decrease_narrative": (
                    "Behavioral adjustment unavailable; showing raw model posterior."
                ),
            }

        ci_80 = adjusted.adjusted_ci_80
        ci_95 = adjusted.adjusted_ci_95
        narrative = self.prospect_theory.generate_behavioral_narrative(forecast, adjusted)
        return {
            "median_change_pct": adjusted.adjusted_median,
            "ci_80": [ci_80[0], ci_80[1]],
            "ci_95": [ci_95[0], ci_95[1]],
            "p_increase": adjusted.behavioral_p_increase,
            "p_decrease_narrative": narrative,
        }

    @staticmethod
    def _forecast_distribution_to_dict(fd: Any) -> Dict[str, Any]:
        """Adapt a ForecastDistribution dataclass into the API dict shape."""
        ci_80 = fd.credible_interval_80
        ci_95 = fd.credible_interval_95
        params = getattr(fd, "distribution_params", {}) or {}
        return {
            "median_change_pct": fd.median_change_pct,
            "mean_change_pct": fd.mean_change_pct,
            "ci_80": [ci_80[0], ci_80[1]],
            "ci_95": [ci_95[0], ci_95[1]],
            "p_increase": fd.p_increase,
            "p_increase_5pct": fd.p_increase_5pct,
            "p_increase_10pct": fd.p_increase_10pct,
            "p_decrease": fd.p_decrease,
            "p_decrease_5pct": fd.p_decrease_5pct,
            "distribution_params": params,
        }

    def _get_current_departamentos_price(self, property_data: List[Dict], barrio: Optional[str]) -> float:
        """Calculate current average price per m2 for departamentos."""
        if not property_data:
            return 2400.0  # Fallback average for CABA
        
        # Properati live listings often lack `price_per_m2` (the field
        # isn't on the search-result page). Derive it from price/surface
        # when available, and skip listings where neither path resolves.
        per_m2_values: List[float] = []
        for listing in property_data:
            ppm = listing.get("price_per_m2")
            if isinstance(ppm, (int, float)) and ppm > 0:
                per_m2_values.append(float(ppm))
                continue
            price = listing.get("price_usd")
            surface = listing.get("surface_m2")
            if (isinstance(price, (int, float)) and price > 0
                    and isinstance(surface, (int, float)) and surface > 0):
                per_m2_values.append(float(price) / float(surface))
        return sum(per_m2_values) / len(per_m2_values) if per_m2_values else 2400.0

    def _get_current_campos_price(self, property_data: List[Dict], zone: Optional[str]) -> float:
        """Calculate current average price per hectare for campos."""
        if not property_data:
            return 15500.0  # Fallback average for core pampa
        
        per_ha_values: List[float] = []
        for listing in property_data:
            pph = listing.get("price_usd_per_ha")
            if isinstance(pph, (int, float)) and pph > 0:
                per_ha_values.append(float(pph))
        return sum(per_ha_values) / len(per_ha_values) if per_ha_values else 15500.0

    def _extract_top_signals(self, news_data: List[Dict], segment: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Extract top news signals affecting the specified segment."""
        relevant_signals = []
        
        for article in news_data:
            affected_segments = article.get("affected_segments", [])
            if segment in affected_segments or "all" in affected_segments:
                # Schema field name is `published_at`, matching TopSignal.
                relevant_signals.append({
                    "title": article.get("title", ""),
                    "impact": float(article.get("impact_magnitude", 0.5) or 0.5),
                    "direction": article.get("impact_direction", "neutral"),
                    "source": article.get("source", "unknown"),
                    "published_at": article.get("published_at", ""),
                })
        
        # Sort by impact magnitude and return top signals
        relevant_signals.sort(key=lambda x: x["impact"], reverse=True)
        return relevant_signals[:limit]

    def _calculate_news_sentiment(self, news_data: List[Dict], segment: str) -> float:
        """Calculate aggregate news sentiment for a segment."""
        relevant_articles = []
        
        for article in news_data:
            affected_segments = article.get("affected_segments", [])
            if segment in affected_segments or segment == "all":
                relevant_articles.append(article)
        
        if not relevant_articles:
            return 0.0  # Neutral sentiment
        
        # Simple sentiment aggregation based on impact direction and magnitude
        total_sentiment = 0.0
        for article in relevant_articles:
            magnitude = article.get("impact_magnitude", 0.5)
            direction = article.get("impact_direction", "neutral")
            
            if direction == "positive":
                total_sentiment += magnitude
            elif direction == "negative":
                total_sentiment -= magnitude
            # neutral contributes 0
        
        # Normalize to [-1, 1] range
        return max(-1.0, min(1.0, total_sentiment / len(relevant_articles)))

    def _calculate_price_variance(self, property_data: List[Dict]) -> float:
        """Calculate price variance as market uncertainty indicator."""
        if len(property_data) < 2:
            return 0.15  # Default variance
        
        if property_data[0].get("price_per_m2"):  # Departamentos
            prices = [p["price_per_m2"] for p in property_data if p.get("price_per_m2")]
        else:  # Campos
            prices = [p["price_usd_per_ha"] for p in property_data if p.get("price_usd_per_ha")]
        
        if len(prices) < 2:
            return 0.15
        
        mean_price = sum(prices) / len(prices)
        variance = sum((p - mean_price) ** 2 for p in prices) / len(prices)
        
        # Return coefficient of variation
        return (variance ** 0.5) / mean_price if mean_price > 0 else 0.15

    def _get_latest_commodity_price(self, commodity_data: List[Dict], commodity: str) -> float:
        """Get latest price for specified commodity."""
        relevant_prices = [
            p for p in commodity_data 
            if p.get("commodity", "").lower() == commodity.lower()
        ]
        
        if not relevant_prices:
            # Return fallback prices
            fallback_prices = {
                "soybean": 420.0,
                "wheat": 280.0, 
                "corn": 180.0
            }
            return fallback_prices.get(commodity.lower(), 300.0)
        
        # Sort by date and return latest
        relevant_prices.sort(key=lambda x: x.get("date", ""), reverse=True)
        return relevant_prices[0].get("price_usd_ton", 300.0)

    def _safe_extract(self, data: Dict, path: str, default: Any) -> Any:
        """Safely extract nested dictionary value using dot notation."""
        try:
            value = data
            for key in path.split("."):
                value = value[key]
            return value if value is not None else default
        except (KeyError, TypeError):
            return default

    def _is_cache_valid(self, cache_key: str) -> bool:
        """Check if cached result is still valid."""
        if cache_key not in self._cache_timestamps:
            return False
        
        cache_age = datetime.utcnow() - self._cache_timestamps[cache_key]
        return cache_age.total_seconds() < self.cache_ttl_minutes * 60