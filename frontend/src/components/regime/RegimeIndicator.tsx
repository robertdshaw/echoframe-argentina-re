import type { RegimeContext } from '../../types';
import { regimeColor } from '../../utils/colors';
import { formatProb } from '../../utils/formatters';

interface Props {
  regime: RegimeContext;
}

const RegimeIndicator = ({ regime }: Props) => {
  const color = regimeColor(regime.current);
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
          {Object.entries(regime.transition_probabilities).map(([key, val]) => (
            <div key={key} style={{ fontSize: 13, color: '#444' }}>
              {key.replace(/_/g, ' ')}:{' '}
              <span className="mono" style={{ color: '#1B2A4A', fontWeight: 600 }}>
                {formatProb(val)}
              </span>
            </div>
          ))}
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
    </div>
  );
};

export default RegimeIndicator;
