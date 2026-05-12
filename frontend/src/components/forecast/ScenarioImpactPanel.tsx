import { useMemo } from 'react';
import { useCanonicalScenarios } from '../../hooks/useScenarios';
import type { ScenarioEntry } from '../../types';
import { formatPct, formatProb, formatUsd } from '../../utils/formatters';

const COLOR_UP = '#1FA66A';
const COLOR_DOWN = '#C2410C';
const COLOR_DEEP_DOWN = '#7F1D1D';

const scenarioColor = (median: number): string => {
  if (median >= 0) return COLOR_UP;
  if (median > -10) return COLOR_DOWN;
  return COLOR_DEEP_DOWN;
};

interface ScenarioRowProps {
  s: ScenarioEntry;
  currentPriceM2: number;
  domain: [number, number];
}

const ScenarioRow = ({ s, currentPriceM2, domain }: ScenarioRowProps) => {
  const color = scenarioColor(s.median_pct);
  const [dLo, dHi] = domain;
  const span = dHi - dLo;
  const lowerPx = ((s.band_lower_pct - dLo) / span) * 100;
  const upperPx = ((s.band_upper_pct - dLo) / span) * 100;
  const medianPx = ((s.median_pct - dLo) / span) * 100;
  const zeroPx = ((0 - dLo) / span) * 100;

  const projected = currentPriceM2 * (1 + s.median_pct / 100);

  return (
    <div
      style={{
        padding: 'var(--s-4) 0',
        borderBottom: '1px dashed var(--border-1)',
      }}
    >
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'minmax(0, 1.4fr) 70px minmax(220px, 2fr) 100px',
          gap: 16,
          alignItems: 'center',
        }}
      >
        {/* Label + description */}
        <div style={{ minWidth: 0 }}>
          <div
            style={{
              fontSize: 13,
              fontWeight: 600,
              color: 'var(--text-1)',
            }}
          >
            {s.label}
          </div>
          <div style={{ fontSize: 11.5, color: 'var(--text-2)', marginTop: 2, lineHeight: 1.45 }}>
            {s.description}
          </div>
          {s.historical_analogue && (
            <div
              style={{
                fontSize: 10.5,
                color: 'var(--text-3)',
                marginTop: 3,
                fontStyle: 'italic',
              }}
            >
              Last episode: {s.historical_analogue}
            </div>
          )}
        </div>

        {/* Probability */}
        <div style={{ textAlign: 'right' }}>
          <div
            className="mono"
            style={{ fontSize: 18, fontWeight: 700, color: 'var(--text-1)' }}
          >
            {formatProb(s.probability)}
          </div>
          <div
            style={{
              fontSize: 9.5,
              letterSpacing: 0.12,
              textTransform: 'uppercase',
              color: 'var(--text-3)',
            }}
          >
            12m prob
          </div>
        </div>

        {/* Impact band */}
        <div>
          <div
            style={{
              position: 'relative',
              height: 18,
              background: 'var(--surface-sunken)',
              borderRadius: 3,
              border: '1px solid var(--border-1)',
            }}
          >
            <div
              style={{
                position: 'absolute',
                left: `${zeroPx}%`,
                top: -2,
                bottom: -2,
                width: 1,
                background: 'var(--border-2)',
              }}
            />
            <div
              style={{
                position: 'absolute',
                left: `${lowerPx}%`,
                width: `${upperPx - lowerPx}%`,
                top: 2,
                bottom: 2,
                background: color,
                opacity: 0.6,
                borderRadius: 2,
              }}
            />
            <div
              style={{
                position: 'absolute',
                left: `${medianPx}%`,
                top: -2,
                bottom: -2,
                width: 2,
                background: color,
                transform: 'translateX(-1px)',
              }}
            />
          </div>
          <div
            className="mono"
            style={{
              display: 'flex',
              justifyContent: 'space-between',
              fontSize: 10,
              color: 'var(--text-3)',
              marginTop: 3,
            }}
          >
            <span>{formatPct(s.band_lower_pct, 0)}</span>
            <span style={{ color, fontWeight: 600 }}>{formatPct(s.median_pct, 1)}</span>
            <span>{formatPct(s.band_upper_pct, 0)}</span>
          </div>
        </div>

        {/* Projected price */}
        <div style={{ textAlign: 'right' }}>
          <div
            className="mono"
            style={{ fontSize: 14, fontWeight: 600, color }}
          >
            {formatUsd(projected, { decimals: 0 })}
          </div>
          <div
            style={{
              fontSize: 9.5,
              letterSpacing: 0.12,
              textTransform: 'uppercase',
              color: 'var(--text-3)',
            }}
          >
            12m USD/m²
          </div>
        </div>
      </div>
    </div>
  );
};

const ScenarioImpactPanel = () => {
  const { data, loading, error } = useCanonicalScenarios();

  const domain: [number, number] = useMemo(() => {
    if (!data) return [-20, 15];
    const lowers = data.scenarios.map((s) => s.band_lower_pct);
    const uppers = data.scenarios.map((s) => s.band_upper_pct);
    const lo = Math.min(...lowers) - 2;
    const hi = Math.max(...uppers) + 2;
    return [Math.floor(lo / 5) * 5, Math.ceil(hi / 5) * 5];
  }, [data]);

  if (loading) {
    return (
      <div className="card" style={{ padding: 24 }}>
        <div className="eyebrow">What could go wrong</div>
        <div style={{ color: 'var(--text-3)', marginTop: 8, fontSize: 13 }}>
          Composing scenarios…
        </div>
      </div>
    );
  }
  if (error || !data) {
    return (
      <div className="card">
        <div className="eyebrow">What could go wrong</div>
        <div className="error" style={{ marginTop: 8 }}>
          Scenarios unavailable: {error ?? 'unknown error'}
        </div>
      </div>
    );
  }

  const totalProb = data.scenarios.reduce((s, x) => s + x.probability, 0);

  return (
    <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
      <div
        style={{
          padding: 'var(--s-4) var(--s-6)',
          borderBottom: '1px solid var(--border-2)',
        }}
      >
        <div className="eyebrow">What could go wrong</div>
        <h3 className="title-3" style={{ margin: '4px 0 0 0' }}>
          Three canonical 12-month scenarios
        </h3>
        <div className="body-sm" style={{ marginTop: 4, maxWidth: 640 }}>
          Base case from the model posterior; FX shock impact calibrated to
          empirical drawdowns in the 2018Q3, 2019Q3 and 2020Q4 brecha-spike
          episodes; regime crisis uses the calibration crisis-conditional prior.
          Probabilities sum to {formatProb(totalProb, 0)} — the remainder is
          assigned to outcomes outside these three named regimes.
        </div>
      </div>

      <div style={{ padding: '0 var(--s-6) var(--s-5)' }}>
        {data.scenarios.map((s) => (
          <ScenarioRow
            key={s.key}
            s={s}
            currentPriceM2={data.current_price_m2}
            domain={domain}
          />
        ))}
      </div>

      <div
        style={{
          padding: 'var(--s-3) var(--s-6) var(--s-5)',
          fontSize: 10.5,
          color: 'var(--text-3)',
          lineHeight: 1.5,
        }}
      >
        Median markers anchor each row at the scenario&apos;s expected
        12-month USD/m² impact; bands show the 80% range. Hover the row
        labels (in a future build) to drill into the underlying drivers.
      </div>
    </div>
  );
};

export default ScenarioImpactPanel;
