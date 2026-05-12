"""
Pydantic response models for EchoFrame Argentina API.

Defines structured response schemas for all API endpoints with proper
validation and documentation for the forecasting intelligence platform.
"""

from datetime import datetime
from typing import Dict, List, Optional, Any, Union
from pydantic import BaseModel, Field
from enum import Enum


# Enums for controlled vocabularies

class SignalTypeEnum(str, Enum):
    """Market signal categories."""
    CREDIT_POLICY = "credit_policy"
    EXCHANGE_RATE = "exchange_rate"
    INFLATION = "inflation"
    CONSTRUCTION = "construction"
    REGULATION = "regulation"
    AGRICULTURAL = "agricultural"
    INVESTMENT = "investment"
    INFRASTRUCTURE = "infrastructure"


class ImpactDirectionEnum(str, Enum):
    """Impact direction on prices."""
    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"


class MarketRegimeEnum(str, Enum):
    """Market regime states."""
    CRISIS = "crisis"
    RECOVERY = "recovery"
    BOOM = "boom"


class SegmentEnum(str, Enum):
    """Real estate market segments."""
    DEPARTAMENTOS = "departamentos"
    CAMPOS = "campos"


# Base models

class ConfidenceInterval(BaseModel):
    """Confidence interval with lower and upper bounds."""
    lower: float = Field(..., description="Lower bound of confidence interval")
    upper: float = Field(..., description="Upper bound of confidence interval")
    confidence_level: int = Field(..., description="Confidence level (e.g., 80, 95)")


class ProbabilityDistribution(BaseModel):
    """Probability distribution parameters."""
    type: str = Field(..., description="Distribution type (normal, beta, etc.)")
    parameters: Dict[str, float] = Field(..., description="Distribution parameters")
    
    class Config:
        schema_extra = {
            "example": {
                "type": "normal",
                "parameters": {"mu": 6.5, "sigma": 3.2}
            }
        }


# Forecast models

class ModelEstimate(BaseModel):
    """Raw model forecast estimate."""
    median_change_pct: float = Field(..., description="Median percentage price change")
    mean_change_pct: float = Field(..., description="Mean percentage price change")
    ci_80: ConfidenceInterval = Field(..., description="80% confidence interval")
    ci_95: ConfidenceInterval = Field(..., description="95% confidence interval")
    p_increase: float = Field(..., ge=0, le=1, description="Probability of price increase")
    p_increase_5pct: float = Field(..., ge=0, le=1, description="Probability of >5% increase")
    p_increase_10pct: float = Field(..., ge=0, le=1, description="Probability of >10% increase")
    p_decrease: float = Field(..., ge=0, le=1, description="Probability of price decrease")
    p_decrease_5pct: float = Field(..., ge=0, le=1, description="Probability of >5% decrease")
    projected_price: float = Field(..., description="Projected absolute price")
    distribution: Optional[ProbabilityDistribution] = None


class BehavioralAdjustment(BaseModel):
    """Behavioral (Prospect Theory) adjusted forecast."""
    median_change_pct: float = Field(..., description="Behavioral-adjusted median change")
    ci_80: ConfidenceInterval = Field(..., description="Asymmetric 80% confidence interval")
    ci_95: ConfidenceInterval = Field(..., description="Asymmetric 95% confidence interval") 
    p_increase: float = Field(..., ge=0, le=1, description="Behavioral-adjusted probability of increase")
    p_decrease_narrative: str = Field(..., description="Explanation of downside bias")


class HorizonForecast(BaseModel):
    """Forecast for a specific time horizon."""
    year: int = Field(..., ge=1, le=5, description="Forecast horizon in years")
    model_estimate: ModelEstimate = Field(..., description="Raw model forecast")
    behavioral_adjusted: BehavioralAdjustment = Field(..., description="Prospect Theory adjusted forecast")


class RegimeContext(BaseModel):
    """Current market regime information."""
    current: MarketRegimeEnum = Field(..., description="Current market regime")
    confidence: float = Field(..., ge=0, le=1, description="Regime classification confidence")
    key_driver: str = Field(..., description="Primary driver of current regime")
    transition_probabilities: Dict[str, float] = Field(..., description="Probabilities of regime transitions")
    
    class Config:
        schema_extra = {
            "example": {
                "current": "recovery",
                "confidence": 0.82,
                "key_driver": "Transaction volumes +45% YoY signal sustained recovery momentum",
                "transition_probabilities": {
                    "remain_recovery": 0.72,
                    "transition_to_boom": 0.18,
                    "transition_to_crisis": 0.10
                }
            }
        }


class TopSignal(BaseModel):
    """Top market signal affecting forecast."""
    title: str = Field(..., description="News headline")
    impact: float = Field(..., ge=0, le=1, description="Impact magnitude")
    direction: ImpactDirectionEnum = Field(..., description="Impact direction")
    source: str = Field(..., description="News source")
    published_at: str = Field(..., description="Publication timestamp")


class ModelMetadata(BaseModel):
    """Metadata about the forecasting model."""
    model_type: str = Field(..., description="Type of model used")
    calibration_period: str = Field(..., description="Historical calibration period")
    confidence_intervals: List[int] = Field(..., description="Available confidence levels")
    behavioral_adjustment: str = Field(..., description="Behavioral adjustment method")
    scenario_applied: bool = Field(..., description="Whether scenario parameters were applied")
    zone: Optional[str] = Field(None, description="Geographic zone (for campos)")


class ForecastResponse(BaseModel):
    """Complete forecast response."""
    segment: str = Field(..., description="Market segment identifier")
    current_price: float = Field(..., description="Current market price")
    forecasts: Dict[int, HorizonForecast] = Field(..., description="Forecasts by year horizon")
    regime_context: RegimeContext = Field(..., description="Market regime information")
    top_signals: List[TopSignal] = Field(..., description="Top signals driving forecast")
    model_metadata: ModelMetadata = Field(..., description="Model metadata")
    timestamp: datetime = Field(..., description="Forecast generation timestamp")
    
    class Config:
        schema_extra = {
            "example": {
                "segment": "departamentos_caba",
                "current_price": 2400.0,
                "forecasts": {
                    "1": {
                        "year": 1,
                        "model_estimate": {
                            "median_change_pct": 6.2,
                            "mean_change_pct": 6.5,
                            "ci_80": {"lower": 3.1, "upper": 9.8, "confidence_level": 80},
                            "p_increase": 0.87,
                            "projected_price": 2549.0
                        }
                    }
                }
            }
        }


class SummaryForecast(BaseModel):
    """Summary forecast for dashboard display."""
    current_price_m2: Optional[float] = Field(None, description="Current price per m2 (departamentos)")
    current_price_ha: Optional[float] = Field(None, description="Current price per hectare (campos)")
    year_1_median_change: float = Field(..., description="Year 1 median price change %")
    year_1_probability_increase: float = Field(..., ge=0, le=1, description="Year 1 probability of increase")
    current_regime: MarketRegimeEnum = Field(..., description="Current market regime")
    regime_confidence: float = Field(..., ge=0, le=1, description="Regime confidence")


class ForecastSummaryResponse(BaseModel):
    """Summary response for dashboard header."""
    departamentos: SummaryForecast = Field(..., description="Departamentos summary")
    campos: SummaryForecast = Field(..., description="Campos summary")
    timestamp: datetime = Field(..., description="Summary generation timestamp")
    status: Optional[str] = Field(None, description="Data status (live/fallback)")


# Signal models

class SignalClassificationData(BaseModel):
    """Signal classification result."""
    signal_type: SignalTypeEnum = Field(..., description="Classified signal type")
    impact_direction: ImpactDirectionEnum = Field(..., description="Impact direction")
    impact_magnitude: float = Field(..., ge=0, le=1, description="Impact magnitude")
    confidence: float = Field(..., ge=0, le=1, description="Classification confidence")
    affected_segments: List[SegmentEnum] = Field(..., description="Affected market segments")
    matched_keywords: List[str] = Field(..., description="Keywords that triggered classification")
    reasoning: str = Field(..., description="Classification reasoning")


class SentimentData(BaseModel):
    """Sentiment analysis result."""
    polarity: str = Field(..., description="Sentiment polarity")
    confidence: float = Field(..., ge=0, le=1, description="Sentiment confidence")
    score: float = Field(..., ge=-1, le=1, description="Sentiment score (-1 to +1)")


class ExtractedEntityData(BaseModel):
    """Extracted entity information."""
    text: str = Field(..., description="Entity text")
    entity_type: str = Field(..., description="Entity type")
    confidence: float = Field(..., ge=0, le=1, description="Extraction confidence")
    normalized_form: str = Field(..., description="Normalized entity form")


class ProcessedSignalResponse(BaseModel):
    """Processed news signal."""
    article_id: str = Field(..., description="Article identifier")
    title: str = Field(..., description="Article headline")
    source: str = Field(..., description="Publication source")
    published_at: str = Field(..., description="Publication timestamp")
    signal_classification: SignalClassificationData = Field(..., description="Signal classification")
    sentiment_score: SentimentData = Field(..., description="Sentiment analysis")
    extracted_entities: List[ExtractedEntityData] = Field(..., description="Extracted entities")
    market_impact_score: float = Field(..., ge=0, le=1, description="Overall market impact score")
    processed_at: datetime = Field(..., description="Processing timestamp")
    provenance: Optional[str] = Field(
        None,
        description="Which dashboard section this signal influences, e.g. '§03 Timing · credit availability trigger'",
    )


class SignalSummaryResponse(BaseModel):
    """Aggregate signal summary."""
    total_signals: int = Field(..., description="Total signals in period")
    time_window_hours: int = Field(..., description="Time window analyzed")
    by_signal_type: Dict[str, int] = Field(..., description="Signal counts by type")
    by_segment: Dict[str, int] = Field(..., description="Signal counts by market segment")
    by_impact_direction: Dict[str, int] = Field(..., description="Signal counts by impact direction")
    high_impact_count: int = Field(..., description="Number of high impact signals")
    avg_impact_score: float = Field(..., description="Average impact score")
    avg_sentiment_score: float = Field(..., description="Average sentiment score")
    top_sources: List[Dict[str, Any]] = Field(..., description="Top news sources")
    generated_at: datetime = Field(..., description="Summary generation timestamp")


# Market data models

class MacroIndicator(BaseModel):
    """Single macro economic indicator."""
    value: float = Field(..., description="Indicator value")
    date: str = Field(..., description="Data date")
    unit: Optional[str] = Field(None, description="Unit of measurement")


class BCRADataResponse(BaseModel):
    """BCRA live data response."""
    exchange_rate: Optional[MacroIndicator] = None
    reference_rate: Optional[MacroIndicator] = None
    inflation: Optional[MacroIndicator] = None
    reserves: Optional[MacroIndicator] = None
    monetary_base: Optional[MacroIndicator] = None
    timestamp: datetime = Field(..., description="Data timestamp")
    source: str = Field("live", description="Data source (live/fallback)")


class REMForecast(BaseModel):
    """REM survey forecast."""
    median: float = Field(..., description="Median forecast")
    mean: float = Field(..., description="Mean forecast")
    period: str = Field(..., description="Forecast period")


class REMDataResponse(BaseModel):
    """REM market expectations response."""
    inflation_forecast: Optional[REMForecast] = None
    exchange_rate_forecast: Optional[REMForecast] = None
    gdp_forecast: Optional[REMForecast] = None
    timestamp: datetime = Field(..., description="Data timestamp")
    source: str = Field("live", description="Data source (live/fallback)")


class MacroIndicatorsResponse(BaseModel):
    """Combined macro indicators response."""
    bcra: BCRADataResponse = Field(..., description="BCRA data")
    rem: REMDataResponse = Field(..., description="REM data")
    sources: Dict[str, str] = Field(..., description="Data source status")
    timestamp: datetime = Field(..., description="Response timestamp")


class PropertyListing(BaseModel):
    """Property listing data."""
    id: str = Field(..., description="Listing identifier")
    price_usd: Optional[float] = Field(None, description="Price in USD")
    price_per_m2: Optional[float] = Field(None, description="Price per square meter (departamentos)")
    price_usd_per_ha: Optional[float] = Field(None, description="Price per hectare (campos)")
    location: str = Field(..., description="Location (barrio/zone)")
    property_type: str = Field(..., description="Property type")
    size: float = Field(..., description="Size (m2 or hectares)")
    segment: SegmentEnum = Field(..., description="Market segment")
    latitude: Optional[float] = Field(None, description="Latitude (WGS84)")
    longitude: Optional[float] = Field(None, description="Longitude (WGS84)")
    province: Optional[str] = Field(None, description="Province (for campos)")
    partido: Optional[str] = Field(None, description="Partido / district (for campos)")


class PropertyListingsResponse(BaseModel):
    """Property listings response."""
    listings: List[PropertyListing] = Field(..., description="Property listings")
    total_count: int = Field(..., description="Total listings found")
    segment: SegmentEnum = Field(..., description="Market segment")
    location_filter: Optional[str] = Field(None, description="Applied location filter")
    avg_price: float = Field(..., description="Average price")
    timestamp: datetime = Field(..., description="Data timestamp")


class CommodityPrice(BaseModel):
    """Commodity price data."""
    commodity: str = Field(..., description="Commodity name")
    price_usd_ton: float = Field(..., description="Price in USD per ton")
    date: str = Field(..., description="Price date")
    market: str = Field(..., description="Market (MATBA-ROFEX, etc.)")


class CommodityPricesResponse(BaseModel):
    """Commodity prices response."""
    prices: List[CommodityPrice] = Field(..., description="Commodity prices")
    commodities: List[str] = Field(..., description="Available commodities")
    date_range: Dict[str, str] = Field(..., description="Date range of data")
    timestamp: datetime = Field(..., description="Response timestamp")


# Net return decomposition models

class NetReturnComponent(BaseModel):
    """A single line in the gross→net return waterfall."""
    key: str = Field(..., description="Machine-readable component identifier")
    label: str = Field(..., description="Human-readable component label")
    value_pct: float = Field(..., description="Annual %-of-price contribution (signed)")
    kind: str = Field(..., description="'positive' or 'negative' contribution")
    source: str = Field(..., description="Origin of this number (model / market default / editable)")
    editable: bool = Field(False, description="Frontend may let the user override this")


class NetReturnAppreciation(BaseModel):
    """The model's price-appreciation component, isolated so the waterfall can render its CI separately."""
    median_pct: float = Field(..., description="Median annual %-appreciation from model")
    ci_80_lower: float = Field(..., description="Lower bound of 80% CI on annual appreciation")
    ci_80_upper: float = Field(..., description="Upper bound of 80% CI on annual appreciation")
    source: str = Field("Bayesian ensemble (year-1 horizon)", description="Provenance")


class NetReturnResponse(BaseModel):
    """
    Components of the net annual USD return on a CABA apartment hold.

    The frontend composes the waterfall locally: net = appreciation.median
    + sum(annual_components) − transaction_round_trip_pct / hold_years.
    Doing the arithmetic client-side keeps the hold-period slider instant.
    """
    segment: str = Field("departamentos", description="Market segment")
    barrio: Optional[str] = Field(None, description="Specific barrio if filtered, else aggregate CABA")
    current_price_m2: float = Field(..., description="Current USD per m² (median of priced listings)")
    appreciation: NetReturnAppreciation = Field(..., description="Model-driven price appreciation")
    annual_components: List[NetReturnComponent] = Field(..., description="Fixed annual yield/cost lines")
    transaction_round_trip_pct: float = Field(..., description="One-time round-trip transaction cost (negative); amortised over hold_years")
    default_hold_years: float = Field(5.0, description="Default hold period for amortising transaction costs")
    timestamp: datetime = Field(..., description="Response timestamp")


# Scenario models

class ScenarioParameters(BaseModel):
    """Scenario analysis input parameters."""
    inflation_target: Optional[float] = Field(None, ge=0, le=100, description="Annual inflation target %")
    usd_ars_target: Optional[float] = Field(None, ge=100, le=10000, description="USD/ARS exchange rate target")
    mortgage_rate_adjustment: Optional[float] = Field(None, ge=-10, le=20, description="Mortgage rate adjustment in percentage points")
    retenciones_change: Optional[float] = Field(None, ge=-20, le=20, description="Export tax change in percentage points")
    news_sentiment_override: Optional[float] = Field(None, ge=-1, le=1, description="News sentiment override (-1 to +1)")
    gdp_growth_override: Optional[float] = Field(None, ge=-10, le=15, description="GDP growth override %")
    
    class Config:
        schema_extra = {
            "example": {
                "inflation_target": 12.0,
                "usd_ars_target": 1200.0,
                "mortgage_rate_adjustment": -2.0,
                "retenciones_change": 5.0
            }
        }


class ScenarioForecastResponse(BaseModel):
    """Scenario analysis forecast response.""" 
    scenario_name: str = Field(..., description="Scenario identifier")
    parameters_applied: ScenarioParameters = Field(..., description="Applied scenario parameters")
    baseline_forecast: ForecastResponse = Field(..., description="Baseline forecast for comparison")
    scenario_forecast: ForecastResponse = Field(..., description="Scenario-adjusted forecast")
    impact_summary: Dict[str, float] = Field(..., description="Summary of parameter impacts")
    timestamp: datetime = Field(..., description="Analysis timestamp")


# Health and status models

class DataFreshnessStatus(BaseModel):
    """Data freshness status."""
    source: str = Field(..., description="Data source name")
    last_updated: datetime = Field(..., description="Last update timestamp")
    is_stale: bool = Field(..., description="Whether data is stale")
    staleness_threshold_hours: int = Field(..., description="Staleness threshold")


class HealthResponse(BaseModel):
    """API health status response."""
    status: str = Field(..., description="Overall API status")
    version: str = Field(..., description="API version")
    timestamp: datetime = Field(..., description="Health check timestamp")
    data_freshness: Dict[str, DataFreshnessStatus] = Field(..., description="Data source freshness")
    model_status: Dict[str, str] = Field(..., description="Model component status")
    
    class Config:
        schema_extra = {
            "example": {
                "status": "healthy",
                "version": "1.0.0",
                "timestamp": "2026-01-15T10:30:00Z",
                "data_freshness": {},
                "model_status": {
                    "bayesian_models": "operational",
                    "hmm_regime": "operational",
                    "nlp_pipeline": "operational"
                }
            }
        }