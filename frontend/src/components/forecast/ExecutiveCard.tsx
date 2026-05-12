import type { ForecastResponse } from '../../types';
import { formatPct, formatProb, formatUsd } from '../../utils/formatters';

interface Props {
  forecast: ForecastResponse;
  segment: 'departamentos' | 'campos';
  location?: string;
}

/**
 * The hero answer card. Reads like a magazine pull-quote with
 * supporting metrics. Asymmetric composition: oversized verdict on
 * the left, ladder of horizon outcomes on the right.
 */
const ExecutiveCard = ({ forecast, segment, location }: Props) => {
  const y1 = forecast.forecasts['1'] ?? forecast.forecasts[1];
  const y2 = forecast.forecasts['2'] ?? forecast.forecasts[2];
  const y3 = forecast.forecasts['3'] ?? forecast.forecasts[3];
  if (!y1) return null;

  const m = y1.model_estimate;
  const isUp = m.median_change_pct >= 0;
  const unitLabel = segment === 'departamentos' ? 'USD / m²' : 'USD / ha';
  const placeLabel =
    segment === 'departamentos'
      ? location || 'Buenos Aires · all CABA'
      : location || 'Aggregate · all zones';

  const ciSpread = m.ci_80.upper - m.ci_80.lower;
  const skew =
    Math.abs(m.ci_80.upper - m.median_change_pct) >
    Math.abs(m.median_change_pct - m.ci_80.lower)
      ? 'upside'
      : 'downside';

  return (
    <div
      className="fade-in-up"
      style={{
        position: 'relative',
        background:
          'radial-gradient(ellipse at top right, #1F2D52 0%, #0F1B3D 45%, #050B1F 100%)',
        color: '#FFFFFF',
        borderRadius: 14,
        overflow: 'hidden',
        marginBottom: 16,
        boxShadow:
          '0 18px 40px rgba(15,27,61,0.18), 0 4px 12px rgba(15,27,61,0.12), 0 1px 0 rgba(255,255,255,0.08) inset',
      }}
    >
      {/* Subtle dot-grid overlay */}
      <div
        style={{
          position: 'absolute',
          inset: 0,
          backgroundImage:
            'radial-gradient(circle at 1px 1px, rgba(255,255,255,0.05) 1px, transparent 0)',
          backgroundSize: '24px 24px',
          opacity: 0.6,
          pointerEvents: 'none',
        }}
      />
      {/* Soft accent glow */}
      <div
        style={{
          position: 'absolute',
          right: -120,
          top: -120,
          width: 360,
          height: 360,
          borderRadius: '50%',
          background:
            'radial-gradient(circle, rgba(232,93,38,0.22) 0%, transparent 60%)',
          pointerEvents: 'none',
        }}
      />

      <div
        style={{
          position: 'relative',
          padding: '32px 36px 28px',
          display: 'grid',
          gridTemplateColumns: 'minmax(0, 1.4fr) minmax(0, 1fr)',
          gap: 36,
          alignItems: 'stretch',
        }}
      >
        {/* LEFT — the verdict */}
        <div style={{ minWidth: 0 }}>
          <div
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: 8,
              padding: '4px 10px',
              background: 'rgba(232,93,38,0.14)',
              border: '1px solid rgba(232,93,38,0.32)',
              borderRadius: 999,
              fontSize: 10,
              fontWeight: 700,
              letterSpacing: 0.16,
              textTransform: 'uppercase',
              color: '#FFB199',
              marginBottom: 18,
            }}
          >
            <span
              style={{
                width: 6,
                height: 6,
                borderRadius: '50%',
                background: '#E85D26',
              }}
            />
            12-month outlook
          </div>

          <div
            style={{
              fontSize: 11,
              color: 'rgba(255,255,255,0.55)',
              fontWeight: 500,
              letterSpacing: 0.06,
              marginBottom: 10,
            }}
          >
            {placeLabel.toUpperCase()}
          </div>

          <div
            style={{
              display: 'flex',
              alignItems: 'baseline',
              gap: 10,
              flexWrap: 'wrap',
              marginBottom: 8,
            }}
          >
            <div
              className="mono"
              style={{
                fontSize: 'clamp(56px, 7vw, 88px)',
                fontWeight: 700,
                color: isUp ? '#36D399' : '#FF6B6B',
                lineHeight: 1,
                letterSpacing: '-0.045em',
                textShadow: isUp
                  ? '0 0 40px rgba(54,211,153,0.25)'
                  : '0 0 40px rgba(255,107,107,0.25)',
              }}
            >
              {formatPct(m.median_change_pct, 1)}
            </div>
            <div
              style={{
                fontSize: 13,
                color: 'rgba(255,255,255,0.55)',
                fontWeight: 500,
                paddingBottom: 8,
              }}
            >
              median<br />expected change
            </div>
          </div>

          <div
            style={{
              fontSize: 14,
              color: 'rgba(255,255,255,0.72)',
              maxWidth: 460,
              lineHeight: 1.5,
              marginBottom: 22,
            }}
          >
            80% credible band{' '}
            <span className="mono" style={{ color: '#FFFFFF', fontWeight: 600 }}>
              {formatPct(m.ci_80.lower, 1)} → {formatPct(m.ci_80.upper, 1)}
            </span>{' '}
            · {ciSpread.toFixed(1)} pp spread, asymmetric to the{' '}
            <span style={{ color: skew === 'upside' ? '#36D399' : '#FF6B6B' }}>
              {skew}
            </span>.
          </div>

          {/* Confidence bar */}
          <div style={{ marginBottom: 8 }}>
            <div
              style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'baseline',
                marginBottom: 6,
              }}
            >
              <span
                style={{
                  fontSize: 10,
                  fontWeight: 600,
                  letterSpacing: 0.14,
                  textTransform: 'uppercase',
                  color: 'rgba(255,255,255,0.45)',
                }}
              >
                Probability of increase
              </span>
              <span
                className="mono"
                style={{ fontSize: 14, fontWeight: 700, color: '#36D399' }}
              >
                {formatProb(m.p_increase, 1)}
              </span>
            </div>
            <div
              style={{
                height: 6,
                background: 'rgba(255,255,255,0.08)',
                borderRadius: 999,
                overflow: 'hidden',
              }}
            >
              <div
                style={{
                  width: `${m.p_increase * 100}%`,
                  height: '100%',
                  background:
                    'linear-gradient(90deg, #36D399 0%, #59E3B2 100%)',
                  borderRadius: 999,
                  boxShadow: '0 0 12px rgba(54,211,153,0.5)',
                  transition: 'width 600ms cubic-bezier(0.16,1,0.3,1)',
                }}
              />
            </div>
          </div>

          <div
            style={{
              marginTop: 18,
              paddingTop: 16,
              borderTop: '1px solid rgba(255,255,255,0.08)',
              display: 'flex',
              gap: 28,
              flexWrap: 'wrap',
            }}
          >
            <KeyStat
              label="Current price"
              value={formatUsd(forecast.current_price)}
              sub={unitLabel}
            />
            <KeyStat
              label="Projected (12m)"
              value={formatUsd(
                forecast.current_price * (1 + m.median_change_pct / 100),
              )}
              sub={`Δ ${formatUsd(
                forecast.current_price * (m.median_change_pct / 100),
              )}`}
              accent={isUp ? '#36D399' : '#FF6B6B'}
            />
            <KeyStat
              label="Regime"
              value={forecast.regime_context.current.toUpperCase()}
              sub={`${formatProb(forecast.regime_context.confidence)} confidence`}
              accent="#FFB199"
            />
          </div>
        </div>

        {/* RIGHT — horizon ladder */}
        <div
          style={{
            position: 'relative',
            background: 'rgba(255,255,255,0.04)',
            border: '1px solid rgba(255,255,255,0.08)',
            borderRadius: 12,
            padding: 22,
            display: 'flex',
            flexDirection: 'column',
            gap: 18,
            backdropFilter: 'blur(8px)',
          }}
        >
          <div>
            <div
              style={{
                fontSize: 10,
                fontWeight: 600,
                letterSpacing: 0.16,
                textTransform: 'uppercase',
                color: 'rgba(255,255,255,0.45)',
                marginBottom: 4,
              }}
            >
              Horizon ladder
            </div>
            <div
              style={{
                fontSize: 13,
                color: 'rgba(255,255,255,0.55)',
                lineHeight: 1.45,
              }}
            >
              Posterior medians and 80% credible bands at three horizons.
            </div>
          </div>

          {[y1, y2, y3].filter(Boolean).map((h) => {
            const me = h!.model_estimate;
            const positive = me.median_change_pct >= 0;
            return (
              <div key={h!.year}>
                <div
                  style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'baseline',
                    marginBottom: 6,
                  }}
                >
                  <span
                    style={{
                      fontSize: 11,
                      fontWeight: 600,
                      letterSpacing: 0.1,
                      textTransform: 'uppercase',
                      color: 'rgba(255,255,255,0.65)',
                    }}
                  >
                    Year {h!.year}
                  </span>
                  <span
                    className="mono"
                    style={{
                      fontSize: 20,
                      fontWeight: 700,
                      color: positive ? '#36D399' : '#FF6B6B',
                      letterSpacing: '-0.02em',
                    }}
                  >
                    {formatPct(me.median_change_pct, 1)}
                  </span>
                </div>
                <HorizonRange
                  lower={me.ci_80.lower}
                  upper={me.ci_80.upper}
                  median={me.median_change_pct}
                  domain={[-12, 16]}
                />
                <div
                  style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    marginTop: 4,
                    fontSize: 10,
                    color: 'rgba(255,255,255,0.45)',
                  }}
                  className="mono"
                >
                  <span>{formatPct(me.ci_80.lower, 1)}</span>
                  <span>P(↑) {formatProb(me.p_increase)}</span>
                  <span>{formatPct(me.ci_80.upper, 1)}</span>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
};

const KeyStat = ({
  label,
  value,
  sub,
  accent,
}: {
  label: string;
  value: string;
  sub?: string;
  accent?: string;
}) => (
  <div>
    <div
      style={{
        fontSize: 10,
        fontWeight: 600,
        letterSpacing: 0.16,
        textTransform: 'uppercase',
        color: 'rgba(255,255,255,0.42)',
        marginBottom: 4,
      }}
    >
      {label}
    </div>
    <div
      className="mono"
      style={{
        fontSize: 17,
        fontWeight: 600,
        color: accent ?? '#FFFFFF',
        lineHeight: 1.1,
        letterSpacing: '-0.01em',
      }}
    >
      {value}
    </div>
    {sub && (
      <div
        style={{ fontSize: 11, color: 'rgba(255,255,255,0.45)', marginTop: 2 }}
        className="mono"
      >
        {sub}
      </div>
    )}
  </div>
);

const HorizonRange = ({
  lower,
  upper,
  median,
  domain,
}: {
  lower: number;
  upper: number;
  median: number;
  domain: [number, number];
}) => {
  const [dLo, dHi] = domain;
  const span = dHi - dLo;
  const left = ((lower - dLo) / span) * 100;
  const right = ((upper - dLo) / span) * 100;
  const medianPct = ((median - dLo) / span) * 100;
  const zero = ((0 - dLo) / span) * 100;

  return (
    <div
      style={{
        position: 'relative',
        height: 14,
        background: 'rgba(255,255,255,0.05)',
        borderRadius: 4,
        border: '1px solid rgba(255,255,255,0.06)',
      }}
    >
      {/* zero reference line */}
      <div
        style={{
          position: 'absolute',
          left: `${zero}%`,
          top: -2,
          bottom: -2,
          width: 1,
          background: 'rgba(255,255,255,0.18)',
        }}
      />
      {/* CI band */}
      <div
        style={{
          position: 'absolute',
          left: `${left}%`,
          width: `${right - left}%`,
          top: 2,
          bottom: 2,
          background:
            'linear-gradient(90deg, rgba(74,59,143,0.35), rgba(107,93,170,0.55))',
          borderRadius: 3,
        }}
      />
      {/* median marker */}
      <div
        style={{
          position: 'absolute',
          left: `${medianPct}%`,
          top: -2,
          bottom: -2,
          width: 2,
          background: '#FFFFFF',
          transform: 'translateX(-1px)',
          boxShadow: '0 0 8px rgba(255,255,255,0.6)',
        }}
      />
    </div>
  );
};

export default ExecutiveCard;
