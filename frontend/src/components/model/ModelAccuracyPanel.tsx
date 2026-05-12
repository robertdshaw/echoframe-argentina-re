import { useMemo } from 'react';
import {
  ResponsiveContainer,
  ScatterChart,
  Scatter,
  Line,
  XAxis,
  YAxis,
  ReferenceLine,
  CartesianGrid,
  Tooltip,
  ComposedChart,
} from 'recharts';
import type { BacktestResults, FittedPriors } from '../../types';
import { formatPct, formatProb } from '../../utils/formatters';

interface Props {
  backtest: BacktestResults;
  priors: FittedPriors;
}

interface StatProps {
  label: string;
  value: string;
  hint?: string;
  tone?: 'good' | 'neutral' | 'bad';
}

const Stat = ({ label, value, hint, tone = 'neutral' }: StatProps) => {
  const color =
    tone === 'good' ? '#0F9D58' : tone === 'bad' ? '#D93025' : '#0F1B3D';
  return (
    <div>
      <div
        style={{
          fontSize: 10,
          fontWeight: 600,
          letterSpacing: 0.12,
          textTransform: 'uppercase',
          color: '#8C95AD',
          marginBottom: 4,
        }}
      >
        {label}
      </div>
      <div
        className="mono"
        style={{ fontSize: 22, fontWeight: 600, color, lineHeight: 1.1 }}
      >
        {value}
      </div>
      {hint && (
        <div style={{ fontSize: 11, color: '#8C95AD', marginTop: 3 }}>{hint}</div>
      )}
    </div>
  );
};

const ModelAccuracyPanel = ({ backtest, priors }: Props) => {
  const all = backtest.all;

  // Calibration plot: predicted P(increase) bucket midpoint vs realized rate.
  const calibrationData = useMemo(
    () =>
      all.calibration_curve
        .filter((b) => b.realized_rate !== null)
        .map((b) => ({
          predicted: b.predicted_midpoint * 100,
          realized: (b.realized_rate ?? 0) * 100,
          n: b.n,
        })),
    [all.calibration_curve],
  );

  // Predicted-vs-realized scatter for each anchor quarter.
  const scatterData = useMemo(
    () =>
      backtest.records.map((r) => ({
        predicted: r.predicted_median,
        realized: r.realized_pct,
        anchor: r.anchor_quarter,
        regime: r.regime_at_anchor,
        in_ci80: r.in_ci80,
      })),
    [backtest.records],
  );

  const ci80Coverage = all.ci80_coverage * 100;
  const ci95Coverage = all.ci95_coverage * 100;
  const coverageTone = (target: number, actual: number): 'good' | 'neutral' | 'bad' => {
    const delta = Math.abs(actual - target);
    if (delta < 5) return 'good';
    if (delta < 12) return 'neutral';
    return 'bad';
  };

  return (
    <div className="card">
      <div
        style={{
          display: 'flex',
          alignItems: 'baseline',
          justifyContent: 'space-between',
          marginBottom: 16,
        }}
      >
        <div>
          <div className="card-eyebrow">Model accuracy</div>
          <h3 style={{ fontSize: 18, fontWeight: 700, marginTop: 2 }}>
            Historical track record
          </h3>
        </div>
        <div style={{ fontSize: 11, color: '#8C95AD', textAlign: 'right' }}>
          Walk-forward leave-one-out · {all.n} anchor quarters · 2018Q1 → 2025Q1
        </div>
      </div>

      <div className="grid grid-5" style={{ marginBottom: 20 }}>
        <Stat
          label="80% CI coverage"
          value={`${ci80Coverage.toFixed(1)}%`}
          hint={`target 80% (${ci80Coverage >= 75 && ci80Coverage <= 85 ? 'calibrated' : 'off-target'})`}
          tone={coverageTone(80, ci80Coverage)}
        />
        <Stat
          label="95% CI coverage"
          value={`${ci95Coverage.toFixed(1)}%`}
          hint="target 95%"
          tone={coverageTone(95, ci95Coverage)}
        />
        <Stat
          label="Directional hit"
          value={formatProb(all.directional_hit_rate)}
          hint={`${Math.round(all.directional_hit_rate * all.n)}/${all.n} correct`}
          tone={all.directional_hit_rate >= 0.75 ? 'good' : 'neutral'}
        />
        <Stat
          label="Brier score"
          value={all.brier_score.toFixed(3)}
          hint="0 = perfect · 0.25 = coin flip"
          tone={all.brier_score < 0.2 ? 'good' : 'neutral'}
        />
        <Stat
          label="MAE vs naive"
          value={`${all.mae_pct.toFixed(2)} pp`}
          hint={`naive: ${all.naive_baseline_mae_pct.toFixed(2)} pp · ${
            all.model_vs_naive_mae_delta > 0 ? 'model better' : 'naive better'
          }`}
          tone={all.model_vs_naive_mae_delta > 0 ? 'good' : 'bad'}
        />
      </div>

      <div className="grid grid-2" style={{ gap: 24 }}>
        <div>
          <div className="card-title" style={{ marginBottom: 6 }}>
            Calibration curve — predicted P(↑) vs realized
          </div>
          <div style={{ width: '100%', height: 200 }}>
            <ResponsiveContainer>
              <ComposedChart margin={{ top: 8, right: 8, left: 0, bottom: 8 }}>
                <CartesianGrid stroke="#EEF0F5" strokeDasharray="3 3" />
                <XAxis
                  type="number"
                  dataKey="predicted"
                  domain={[0, 100]}
                  ticks={[0, 25, 50, 75, 100]}
                  tickFormatter={(v: number) => `${v}%`}
                  tick={{ fontSize: 11, fill: '#5A6582' }}
                />
                <YAxis
                  type="number"
                  dataKey="realized"
                  domain={[0, 100]}
                  ticks={[0, 25, 50, 75, 100]}
                  tickFormatter={(v: number) => `${v}%`}
                  tick={{ fontSize: 11, fill: '#5A6582' }}
                  width={40}
                />
                <Tooltip
                  formatter={(v: number) => `${v.toFixed(0)}%`}
                  contentStyle={{ borderRadius: 6, fontSize: 12 }}
                />
                <ReferenceLine
                  segment={[
                    { x: 0, y: 0 },
                    { x: 100, y: 100 },
                  ]}
                  stroke="#8C95AD"
                  strokeDasharray="4 4"
                  ifOverflow="extendDomain"
                />
                <Line
                  type="monotone"
                  data={calibrationData}
                  dataKey="realized"
                  stroke="#E85D26"
                  strokeWidth={2}
                  dot={{ fill: '#E85D26', r: 5 }}
                  name="Realized"
                />
                <Scatter data={calibrationData} fill="#E85D26" />
              </ComposedChart>
            </ResponsiveContainer>
          </div>
          <div
            style={{ fontSize: 11, color: '#8C95AD', marginTop: 4, lineHeight: 1.5 }}
          >
            Dashed line is perfect calibration. Points on or near it mean
            "when the model said 70%, it happened 70% of the time".
          </div>
        </div>

        <div>
          <div className="card-title" style={{ marginBottom: 6 }}>
            Predicted vs realized Year-1 change
          </div>
          <div style={{ width: '100%', height: 200 }}>
            <ResponsiveContainer>
              <ScatterChart margin={{ top: 8, right: 8, left: 0, bottom: 8 }}>
                <CartesianGrid stroke="#EEF0F5" strokeDasharray="3 3" />
                <XAxis
                  type="number"
                  dataKey="predicted"
                  name="Predicted"
                  tickFormatter={(v: number) => `${v.toFixed(0)}%`}
                  tick={{ fontSize: 11, fill: '#5A6582' }}
                  domain={['auto', 'auto']}
                />
                <YAxis
                  type="number"
                  dataKey="realized"
                  name="Realized"
                  tickFormatter={(v: number) => `${v.toFixed(0)}%`}
                  tick={{ fontSize: 11, fill: '#5A6582' }}
                  width={48}
                  domain={['auto', 'auto']}
                />
                <ReferenceLine
                  segment={[
                    { x: -30, y: -30 },
                    { x: 30, y: 30 },
                  ]}
                  stroke="#8C95AD"
                  strokeDasharray="4 4"
                  ifOverflow="extendDomain"
                />
                <Tooltip
                  formatter={(v: number) => formatPct(v)}
                  labelFormatter={() => ''}
                  contentStyle={{ borderRadius: 6, fontSize: 12 }}
                />
                <Scatter
                  data={scatterData.filter((d) => d.regime === 'crisis')}
                  fill="#D93025"
                  name="Crisis"
                />
                <Scatter
                  data={scatterData.filter((d) => d.regime === 'recovery')}
                  fill="#0F9D58"
                  name="Recovery"
                />
              </ScatterChart>
            </ResponsiveContainer>
          </div>
          <div
            style={{
              display: 'flex',
              gap: 12,
              fontSize: 11,
              color: '#5A6582',
              marginTop: 4,
            }}
          >
            <span>
              <span
                style={{
                  display: 'inline-block',
                  width: 8,
                  height: 8,
                  borderRadius: '50%',
                  background: '#D93025',
                  marginRight: 4,
                }}
              />
              Crisis anchors
            </span>
            <span>
              <span
                style={{
                  display: 'inline-block',
                  width: 8,
                  height: 8,
                  borderRadius: '50%',
                  background: '#0F9D58',
                  marginRight: 4,
                }}
              />
              Recovery anchors
            </span>
          </div>
        </div>
      </div>

      <div
        style={{
          marginTop: 18,
          padding: 12,
          background: '#F6F7FB',
          borderRadius: 6,
          fontSize: 12,
          color: '#5A6582',
          lineHeight: 1.6,
        }}
      >
        <strong style={{ color: '#0F1B3D' }}>Methodology.</strong>{' '}
        {backtest.methodology}
      </div>

      <div style={{ marginTop: 14 }}>
        <div className="card-title">Regime-conditional priors fitted from history</div>
        <div className="grid grid-3">
          {Object.entries(priors).map(([regime, p]) => {
            // Backend scrubs NaN → null for JSON; treat both as "no data".
            const hasData =
              p.year_1_mean !== null &&
              p.year_1_mean !== undefined &&
              !Number.isNaN(p.year_1_mean) &&
              p.year_1_std !== null &&
              p.year_1_std !== undefined &&
              !Number.isNaN(p.year_1_std);
            return (
              <div
                key={regime}
                style={{
                  border: '1px solid #EEF0F5',
                  borderRadius: 6,
                  padding: '10px 12px',
                  background: '#FFFFFF',
                }}
              >
                <div
                  style={{
                    fontSize: 10,
                    fontWeight: 600,
                    letterSpacing: 0.12,
                    textTransform: 'uppercase',
                    color: '#8C95AD',
                  }}
                >
                  {regime}
                </div>
                {hasData ? (
                  (() => {
                    // hasData already proved both are non-null numbers.
                    const mean = p.year_1_mean as number;
                    const std = p.year_1_std as number;
                    return (
                      <>
                        <div
                          className="mono"
                          style={{
                            fontSize: 18,
                            fontWeight: 600,
                            color: mean >= 0 ? '#0F9D58' : '#D93025',
                          }}
                        >
                          μ {formatPct(mean)} · σ {std.toFixed(2)}
                        </div>
                        <div style={{ fontSize: 11, color: '#8C95AD' }}>
                          n = {p.n} historical quarters
                        </div>
                      </>
                    );
                  })()
                ) : (
                  <div style={{ fontSize: 12, color: '#8C95AD', marginTop: 4 }}>
                    Insufficient history (n={p.n}) — falls back to hand-coded.
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
};

export default ModelAccuracyPanel;
