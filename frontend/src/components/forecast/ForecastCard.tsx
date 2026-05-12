import type { HorizonForecast } from '../../types';
import { formatPct, formatProb, formatUsd } from '../../utils/formatters';
import ConfidenceIntervalDisplay from '../common/ConfidenceInterval';

interface Props {
  horizon: HorizonForecast;
  currentPrice: number;
  unitLabel: string;
}

const ForecastCard = ({ horizon, currentPrice, unitLabel }: Props) => {
  const m = horizon.model_estimate;
  const projected = currentPrice * (1 + m.median_change_pct / 100);
  const isUp = m.median_change_pct >= 0;

  return (
    <div
      style={{
        border: '1px solid #E5E7EB',
        borderRadius: 8,
        padding: 16,
        background: '#FFFFFF',
      }}
    >
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'baseline',
          marginBottom: 8,
        }}
      >
        <div style={{ fontWeight: 600, fontSize: 14, color: '#666' }}>
          Year {horizon.year}
        </div>
        <div
          className="mono"
          style={{
            color: isUp ? '#10B981' : '#EF4444',
            fontWeight: 700,
            fontSize: 18,
          }}
        >
          {formatPct(m.median_change_pct)}
        </div>
      </div>
      <div style={{ fontSize: 12, color: '#666', marginBottom: 12 }}>
        Projected: <span className="mono">{formatUsd(projected)}</span>{' '}
        <span style={{ color: '#999' }}>{unitLabel}</span>
      </div>
      <ConfidenceIntervalDisplay ci={m.ci_80} label="80% CI" />
      <div style={{ height: 4 }} />
      <ConfidenceIntervalDisplay ci={m.ci_95} label="95% CI" />
      <div
        style={{
          marginTop: 12,
          paddingTop: 12,
          borderTop: '1px dashed #E5E7EB',
          fontSize: 12,
          color: '#444',
          display: 'flex',
          justifyContent: 'space-between',
        }}
      >
        <span>
          P(increase): <span className="mono">{formatProb(m.p_increase)}</span>
        </span>
        <span>
          P(decrease): <span className="mono">{formatProb(m.p_decrease)}</span>
        </span>
      </div>
      {horizon.behavioral_adjusted && (
        <div
          style={{
            marginTop: 10,
            padding: 10,
            background: '#FFF7ED',
            borderRadius: 6,
            fontSize: 12,
            color: '#7C2D12',
          }}
        >
          <strong>Behavioral-adjusted:</strong>{' '}
          {formatPct(horizon.behavioral_adjusted.median_change_pct)} median ·
          80% CI <span className="mono">
            {formatPct(horizon.behavioral_adjusted.ci_80.lower)} →{' '}
            {formatPct(horizon.behavioral_adjusted.ci_80.upper)}
          </span>
        </div>
      )}
    </div>
  );
};

export default ForecastCard;
