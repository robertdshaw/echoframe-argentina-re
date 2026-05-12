// Shared TypeScript types mirroring backend Pydantic schemas in
// backend/api/schemas.py. Keep these in sync when schemas change.

export type Segment = 'departamentos' | 'campos';
export type Regime = 'crisis' | 'recovery' | 'boom';
export type ImpactDirection = 'positive' | 'negative' | 'neutral';

export type SignalType =
  | 'credit_policy'
  | 'exchange_rate'
  | 'inflation'
  | 'construction'
  | 'regulation'
  | 'agricultural'
  | 'investment'
  | 'infrastructure';

export interface ConfidenceInterval {
  lower: number;
  upper: number;
  confidence_level: number;
}

export interface ModelEstimate {
  median_change_pct: number;
  mean_change_pct: number;
  ci_80: ConfidenceInterval;
  ci_95: ConfidenceInterval;
  p_increase: number;
  p_increase_5pct: number;
  p_increase_10pct: number;
  p_decrease: number;
  p_decrease_5pct: number;
  projected_price: number;
}

export interface BehavioralAdjustment {
  median_change_pct: number;
  ci_80: ConfidenceInterval;
  ci_95: ConfidenceInterval;
  p_increase: number;
  p_decrease_narrative: string;
}

export interface HorizonForecast {
  year: number;
  model_estimate: ModelEstimate;
  behavioral_adjusted: BehavioralAdjustment | null;
}

export interface RegimeContext {
  current: Regime;
  confidence: number;
  key_driver: string;
  transition_probabilities: Record<string, number>;
}

export interface TopSignal {
  title: string;
  impact: number;
  direction: ImpactDirection;
  source: string;
  published_at: string;
}

export interface ForecastResponse {
  segment: string;
  current_price: number;
  forecasts: Record<string, HorizonForecast>;
  regime_context: RegimeContext;
  top_signals: TopSignal[];
  model_metadata: {
    model_type: string;
    calibration_period: string;
    confidence_intervals: number[];
    behavioral_adjustment: string;
    scenario_applied: boolean;
    zone?: string | null;
  };
  timestamp: string;
}

export interface SummaryForecast {
  current_price_m2?: number | null;
  current_price_ha?: number | null;
  year_1_median_change: number;
  year_1_probability_increase: number;
  current_regime: Regime;
  regime_confidence: number;
}

export interface ForecastSummaryResponse {
  departamentos: SummaryForecast;
  campos: SummaryForecast;
  timestamp: string;
  status?: string | null;
}

export interface SignalClassification {
  signal_type: SignalType;
  impact_direction: ImpactDirection;
  impact_magnitude: number;
  confidence: number;
  affected_segments: Segment[];
  matched_keywords: string[];
  reasoning: string;
}

export interface ProcessedSignal {
  article_id: string;
  title: string;
  source: string;
  published_at: string;
  signal_classification: SignalClassification;
  sentiment_score: {
    polarity: string;
    confidence: number;
    score: number;
  };
  extracted_entities: Array<{
    text: string;
    entity_type: string;
    confidence: number;
    normalized_form: string;
  }>;
  market_impact_score: number;
  processed_at: string;
}

export interface MacroIndicator {
  value: number;
  date: string;
  unit?: string | null;
}

export interface BCRAData {
  exchange_rate: MacroIndicator | null;
  reference_rate: MacroIndicator | null;
  inflation: MacroIndicator | null;
  reserves: MacroIndicator | null;
  monetary_base: MacroIndicator | null;
  timestamp: string;
  source: string;
}

export interface REMForecast {
  median: number;
  mean: number;
  period: string;
}

export interface REMData {
  inflation_forecast: REMForecast | null;
  exchange_rate_forecast: REMForecast | null;
  gdp_forecast: REMForecast | null;
  timestamp: string;
  source: string;
}

export interface MacroIndicatorsResponse {
  bcra: BCRAData;
  rem: REMData;
  sources: Record<string, string>;
  timestamp: string;
}

export interface PropertyListing {
  id: string;
  price_usd: number | null;
  price_per_m2: number | null;
  price_usd_per_ha: number | null;
  location: string;
  property_type: string;
  size: number;
  segment: Segment;
  latitude: number | null;
  longitude: number | null;
  province: string | null;
  partido: string | null;
}

export interface PropertyListingsResponse {
  listings: PropertyListing[];
  total_count: number;
  segment: Segment;
  location_filter: string | null;
  avg_price: number;
  timestamp: string;
}

export interface ScenarioParameters {
  inflation_target?: number;
  usd_ars_target?: number;
  mortgage_rate_adjustment?: number;
  retenciones_change?: number;
  news_sentiment_override?: number;
  gdp_growth_override?: number;
}

export interface ScenarioForecastResponse {
  scenario_name: string;
  parameters_applied: ScenarioParameters;
  baseline_forecast: ForecastResponse;
  scenario_forecast: ForecastResponse;
  impact_summary: Record<string, number>;
  timestamp: string;
}

// Model insights — backtest results & fitted priors from /api/v1/model/insights.

export interface BacktestBlockStats {
  n: number;
  ci80_coverage: number;
  ci95_coverage: number;
  directional_hit_rate: number;
  brier_score: number;
  mae_pct: number;
  naive_baseline_mae_pct: number;
  model_vs_naive_mae_delta: number;
  regime_breakdown: Record<string, number>;
  calibration_curve: Array<{
    bucket: string;
    predicted_midpoint: number;
    realized_rate: number | null;
    n: number;
  }>;
}

export interface BacktestRecord {
  anchor_quarter: string;
  realized_pct: number;
  predicted_median: number;
  predicted_mean: number;
  predicted_std: number;
  ci80_lower: number;
  ci80_upper: number;
  ci95_lower: number;
  ci95_upper: number;
  p_increase: number;
  in_ci80: boolean;
  in_ci95: boolean;
  directional_hit: boolean;
  naive_predicted: number;
  regime_at_anchor: string;
  in_sample: boolean;
}

export interface BacktestResults {
  methodology: string;
  in_sample: BacktestBlockStats;
  out_of_sample: BacktestBlockStats;
  all: BacktestBlockStats;
  records: BacktestRecord[];
}

export interface FittedPriors {
  [regime: string]: {
    n: number;
    // Both fields are null when the regime has insufficient history
    // (e.g. boom has n=1 in the current calibration). The backend
    // serializes NaN as null to keep the JSON RFC-compliant.
    year_1_mean: number | null;
    year_1_std: number | null;
  };
}

export interface HmmStateSequenceEntry {
  quarter: string;
  fitted_state: number;
  regime: 'crisis' | 'recovery' | 'boom';
}

export interface HmmDiagnostics {
  training_method: 'hmm_unsupervised' | 'kmeans_unsupervised' | string;
  n_observations: number;
  n_states: number;
  log_likelihood: number | null;
  label_agreement_rate: number;
  transition_matrix: number[][];
  state_sequence: HmmStateSequenceEntry[];
  feature_names: string[];
  state_means_aligned: Record<string, number[]>;
}

// Net return waterfall — gross→net decomposition for CABA apartments.

export interface NetReturnComponent {
  key: string;
  label: string;
  value_pct: number;        // signed
  kind: 'positive' | 'negative';
  source: string;
  editable: boolean;
}

export interface NetReturnAppreciation {
  median_pct: number;
  ci_80_lower: number;
  ci_80_upper: number;
  source: string;
}

export interface NetReturnResponse {
  segment: string;
  barrio: string | null;
  current_price_m2: number;
  appreciation: NetReturnAppreciation;
  annual_components: NetReturnComponent[];
  transaction_round_trip_pct: number;    // negative; amortise over hold_years
  default_hold_years: number;
  timestamp: string;
}

export interface NarrativeResponse {
  status: 'ok' | 'unavailable' | 'error';
  narrative: string | null;
  model: string;
  reason?: string;
  generated_at?: string;
}

export interface ModelInsightsResponse {
  status: 'ok' | 'not_run';
  message?: string;
  backtest?: BacktestResults;
  fitted_priors?: FittedPriors;
  hmm?: HmmDiagnostics;
}
