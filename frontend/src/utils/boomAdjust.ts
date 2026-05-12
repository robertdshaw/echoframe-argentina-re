import type { ConfidenceInterval, ModelEstimate, RegimeContext } from '../types';

/**
 * Probability above which we widen the upside band to absorb the
 * unidentified boom-state σ (boom regime fitted from n=1 quarter).
 */
export const BOOM_ALERT_THRESHOLD = 0.15;

/**
 * Multiplier applied to the upside half of the 80% band when the
 * boom-transition probability crosses the threshold. The downside half
 * is unchanged — crisis regime has plenty of training data and its σ is
 * already well-identified by the calibration.
 */
const BOOM_UPSIDE_WIDEN = 1.4;

export const shouldWidenForBoom = (regime?: RegimeContext | null): boolean => {
  if (!regime) return false;
  const p = regime.transition_probabilities?.transition_to_boom ?? 0;
  return p > BOOM_ALERT_THRESHOLD;
};

/**
 * Returns a new ConfidenceInterval with the upside half widened when
 * the boom-transition probability is above threshold. Median is the
 * anchor point; band[lower, median] is unchanged; band[median, upper]
 * is stretched by BOOM_UPSIDE_WIDEN.
 */
export const widenBandForBoom = (
  ci: ConfidenceInterval,
  median: number,
  regime?: RegimeContext | null,
): ConfidenceInterval => {
  if (!shouldWidenForBoom(regime)) return ci;
  const upsideHalf = ci.upper - median;
  if (upsideHalf <= 0) return ci;
  return {
    ...ci,
    upper: median + upsideHalf * BOOM_UPSIDE_WIDEN,
  };
};

/**
 * Convenience wrapper that returns a copy of the ModelEstimate with
 * both ci_80 and ci_95 widened. Use this when rendering bands in the
 * hero card or fan chart — callers downstream that need raw model
 * output (e.g. analytics) should keep the original.
 */
export const applyBoomAdjustment = (
  estimate: ModelEstimate,
  regime?: RegimeContext | null,
): ModelEstimate => {
  if (!shouldWidenForBoom(regime)) return estimate;
  return {
    ...estimate,
    ci_80: widenBandForBoom(estimate.ci_80, estimate.median_change_pct, regime),
    ci_95: widenBandForBoom(estimate.ci_95, estimate.median_change_pct, regime),
  };
};
