import type { ModelEstimate } from '../../types';
import { formatProb } from '../../utils/formatters';

interface Props {
  estimate: ModelEstimate;
  title: string;
}

/**
 * A horizontal probability stack — a Tufte-style breakdown of where
 * the model places its mass. Reads left-to-right from worst to best:
 *
 *    [ P(↓ > 5%) ][  P(0 to -5%)  ][  P(0 to +5%)  ][ P(+5 to +10%) ][ P(>+10%) ]
 *
 * Each segment width is proportional to its probability mass.
 */
const ProbabilityGauge = ({ estimate, title }: Props) => {
  const p = {
    big_down: estimate.p_decrease_5pct,
    small_down: Math.max(0, estimate.p_decrease - estimate.p_decrease_5pct),
    small_up: Math.max(
      0,
      estimate.p_increase - estimate.p_increase_5pct,
    ),
    medium_up: Math.max(
      0,
      estimate.p_increase_5pct - estimate.p_increase_10pct,
    ),
    big_up: estimate.p_increase_10pct,
  };

  const total =
    p.big_down + p.small_down + p.small_up + p.medium_up + p.big_up || 1;

  const segments: Array<{
    key: string;
    pct: number;
    color: string;
    label: string;
  }> = [
    { key: 'big_down', pct: p.big_down / total, color: '#D93025', label: '< −5%' },
    { key: 'small_down', pct: p.small_down / total, color: '#F08C7C', label: '−5 to 0%' },
    { key: 'small_up', pct: p.small_up / total, color: '#A8DBC1', label: '0 to +5%' },
    { key: 'medium_up', pct: p.medium_up / total, color: '#5BBB89', label: '+5 to +10%' },
    { key: 'big_up', pct: p.big_up / total, color: '#0F9D58', label: '> +10%' },
  ];

  return (
    <div style={{ padding: '4px 2px' }}>
      <div style={{ marginBottom: 10 }}>
        <div
          style={{
            fontSize: 10,
            fontWeight: 600,
            letterSpacing: 0.12,
            textTransform: 'uppercase',
            color: '#8C95AD',
            marginBottom: 2,
          }}
        >
          {title}
        </div>
        <div
          style={{
            display: 'flex',
            alignItems: 'baseline',
            gap: 14,
            marginTop: 4,
          }}
        >
          <div
            className="mono"
            style={{ fontSize: 30, fontWeight: 700, color: '#0F9D58' }}
          >
            {formatProb(estimate.p_increase)}
          </div>
          <div style={{ fontSize: 12, color: '#5A6582' }}>
            P(price increase) · 1Y
          </div>
        </div>
      </div>

      <div
        style={{
          display: 'flex',
          height: 18,
          width: '100%',
          borderRadius: 3,
          overflow: 'hidden',
          border: '1px solid #E1E4EC',
        }}
      >
        {segments.map((s) => (
          <div
            key={s.key}
            title={`${s.label}: ${formatProb(s.pct)}`}
            style={{
              flexBasis: `${s.pct * 100}%`,
              background: s.color,
              minWidth: s.pct > 0 ? 2 : 0,
            }}
          />
        ))}
      </div>

      <div
        style={{
          display: 'flex',
          marginTop: 6,
          fontSize: 10,
          color: '#5A6582',
          fontVariantNumeric: 'tabular-nums',
        }}
        className="mono"
      >
        {segments.map((s) => (
          <div
            key={s.key}
            style={{ flexBasis: `${s.pct * 100}%`, textAlign: 'center', minWidth: 0 }}
          >
            {s.pct > 0.04 && (
              <>
                <div style={{ fontWeight: 600, color: s.color }}>
                  {formatProb(s.pct)}
                </div>
                <div style={{ fontSize: 9, color: '#8C95AD' }}>{s.label}</div>
              </>
            )}
          </div>
        ))}
      </div>

      <div
        style={{
          marginTop: 12,
          paddingTop: 10,
          borderTop: '1px dashed #E1E4EC',
          fontSize: 11,
          color: '#5A6582',
          display: 'flex',
          justifyContent: 'space-between',
          fontVariantNumeric: 'tabular-nums',
        }}
        className="mono"
      >
        <span>
          Downside mass:{' '}
          <strong style={{ color: '#D93025' }}>
            {formatProb(estimate.p_decrease)}
          </strong>
        </span>
        <span>
          Right-tail (&gt;+10%):{' '}
          <strong style={{ color: '#0F9D58' }}>
            {formatProb(estimate.p_increase_10pct)}
          </strong>
        </span>
      </div>
    </div>
  );
};

export default ProbabilityGauge;
