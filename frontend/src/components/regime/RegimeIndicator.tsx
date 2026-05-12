import type { RegimeContext } from '../../types';
import { regimeColor } from '../../utils/colors';
import { formatProb } from '../../utils/formatters';

interface Props {
  regime: RegimeContext;
}

// Threshold above which the dashboard widens the upside 80% band to
// reflect the fact that the boom regime was fitted on n=1 quarter and
// its sigma is essentially unidentified — see the disclosure footnote.
const BOOM_ALERT_THRESHOLD = 0.15;

const RegimeIndicator = ({ regime }: Props) => {
  const color = regimeColor(regime.current);
  const pBoom = regime.transition_probabilities.transition_to_boom ?? 0;
  const boomAlert = pBoom > BOOM_ALERT_THRESHOLD;

  return (
    <div className="card">
      <div style={{ display: 'flex', alignItems: 'baseline', gap: 16 }}>
        <div>
          <div style={{ fontSize: 12, color: '#666', fontWeight: 600, letterSpacing: 0.5 }}>
            CURRENT MARKET REGIME
          </div>
          <div
            style={{
              fontSize: 32,
              fontWeight: 700,
              color,
              textTransform: 'uppercase',
              marginTop: 4,
            }}
          >
            {regime.current}
          </div>
          <div style={{ fontSize: 14, color: '#444', marginTop: 4 }}>
            <span className="mono">{formatProb(regime.confidence)}</span> confidence
          </div>
        </div>
        <div style={{ marginLeft: 'auto', textAlign: 'right' }}>
          <div style={{ fontSize: 12, color: '#666', marginBottom: 6 }}>
            Transition probabilities
          </div>
          {Object.entries(regime.transition_probabilities).map(([key, val]) => {
            const isBoom = key === 'transition_to_boom';
            return (
              <div key={key} style={{ fontSize: 13, color: '#444' }}>
                {key.replace(/_/g, ' ')}:{' '}
                <span className="mono" style={{ color: '#1B2A4A', fontWeight: 600 }}>
                  {formatProb(val)}
                </span>
                {isBoom && boomAlert && (
                  <span
                    title="Boom regime fitted on n=1 quarter. Upside 80% band widened 1.4× as a precaution."
                    style={{ marginLeft: 4, cursor: 'help' }}
                  >
                    ⚠️
                  </span>
                )}
              </div>
            );
          })}
        </div>
      </div>
      {regime.key_driver && (
        <div
          style={{
            marginTop: 16,
            padding: 12,
            background: '#F8F9FB',
            borderRadius: 6,
            fontSize: 13,
            color: '#444',
            borderLeft: `3px solid ${color}`,
          }}
        >
          <strong>Key driver:</strong> {regime.key_driver}
        </div>
      )}
      <div
        style={{
          marginTop: 12,
          padding: '8px 12px',
          fontSize: 11,
          color: 'var(--text-3)',
          background: 'var(--surface-sunken)',
          borderRadius: 4,
          lineHeight: 1.5,
        }}
      >
        <strong style={{ color: 'var(--text-2)' }}>Boom-state caveat:</strong>{' '}
        The boom regime in this calibration was fitted from a single
        historical quarter (n=1). Forecasts conditional on boom should be
        treated as directional only, not quantitative. When P(transition →
        boom) exceeds {formatProb(BOOM_ALERT_THRESHOLD)} the upside 80% band on the
        ensemble forecast is widened 1.4× to absorb the unidentified σ.
      </div>
    </div>
  );
};

export default RegimeIndicator;
