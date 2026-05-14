import {
  ComposedChart,
  Line,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ReferenceLine,
  ResponsiveContainer,
} from 'recharts';
import type { ForecastResponse } from '../../types';
import { formatUsd } from '../../utils/formatters';
import { applyBoomAdjustment } from '../../utils/boomAdjust';

interface Props {
  forecast: ForecastResponse;
  unit: 'usd_per_m2' | 'usd_per_ha';
  showBehavioral?: boolean;
}

interface ChartPoint {
  label: string;
  isToday: boolean;
  historical?: number;
  median?: number;
  band80Top?: number;
  band80Bottom?: number;
  band95Top?: number;
  band95Bottom?: number;
}

const buildHistorical = (current: number): Array<{ label: string; value: number }> => {
  // Light synthetic trail anchored to today's price; production would
  // come from the calibration series. Curve shape mirrors the recovery
  // narrative in CLAUDE.md (trough → smooth recovery).
  const trough = current * 0.88;
  const labels = ['Q1 24', 'Q2 24', 'Q3 24', 'Q4 24', 'Q1 25', 'Q2 25', 'Q3 25', 'Q4 25', 'Now'];
  return labels.map((label, i) => {
    const t = i / (labels.length - 1);
    // Ease-out for a more organic curve than linear.
    const ease = 1 - Math.pow(1 - t, 1.4);
    return { label, value: trough + (current - trough) * ease };
  });
};

const FanChart = ({ forecast, unit, showBehavioral = false }: Props) => {
  const history = buildHistorical(forecast.current_price);
  const base = forecast.current_price;
  const points: ChartPoint[] = history.map((h) => ({
    label: h.label,
    isToday: h.label === 'Now',
    historical: h.value,
  }));

  // Add forecast horizons. Median + 80%/95% bands as nested ribbons.
  // Bands run through applyBoomAdjustment so the upside half widens
  // when the HMM places material mass on a boom transition (n=1 σ).
  for (const year of [1, 2, 3]) {
    const fc = forecast.forecasts[String(year)] ?? forecast.forecasts[year];
    if (!fc) continue;
    const m = applyBoomAdjustment(fc.model_estimate, forecast.regime_context);
    points.push({
      label: `Y${year}`,
      isToday: false,
      median: base * (1 + m.median_change_pct / 100),
      band80Top: base * (1 + m.ci_80.upper / 100),
      band80Bottom: base * (1 + m.ci_80.lower / 100),
      band95Top: base * (1 + m.ci_95.upper / 100),
      band95Bottom: base * (1 + m.ci_95.lower / 100),
    });
  }

  // Recharts stacked-area approach: render the 95% range as a "bottom"
  // (invisible) + "fill", then the 80% range similarly. We use the gap
  // trick: bottom area in background color hides the lower portion.
  const data = points.map((p) => ({
    label: p.label,
    historical: p.historical,
    median: p.median,
    // For stacked area: bottom + thickness
    band95Bottom: p.band95Bottom,
    band95Thickness:
      p.band95Top !== undefined && p.band95Bottom !== undefined
        ? p.band95Top - p.band95Bottom
        : undefined,
    band80Bottom: p.band80Bottom,
    band80Thickness:
      p.band80Top !== undefined && p.band80Bottom !== undefined
        ? p.band80Top - p.band80Bottom
        : undefined,
  }));

  const unitLabel = unit === 'usd_per_m2' ? 'USD / m²' : 'USD / ha';

  // Tightened y-axis around the data so the bands fill the chart.
  const allValues: number[] = [];
  data.forEach((d) => {
    [d.historical, d.median, d.band95Bottom, d.band80Bottom].forEach((v) => {
      if (v !== undefined) allValues.push(v);
      if (d.band95Bottom !== undefined && d.band95Thickness !== undefined)
        allValues.push(d.band95Bottom + d.band95Thickness);
      if (d.band80Bottom !== undefined && d.band80Thickness !== undefined)
        allValues.push(d.band80Bottom + d.band80Thickness);
    });
  });
  const minY = Math.min(...allValues) * 0.97;
  const maxY = Math.max(...allValues) * 1.03;

  return (
    <div style={{ width: '100%', height: 340 }}>
      <ResponsiveContainer>
        <ComposedChart data={data} margin={{ top: 12, right: 24, left: 0, bottom: 6 }}>
          <CartesianGrid stroke="#EEF0F5" strokeDasharray="3 3" vertical={false} />
          <XAxis
            dataKey="label"
            tick={{ fill: '#5A6582', fontSize: 11 }}
            axisLine={{ stroke: '#E1E4EC' }}
            tickLine={false}
          />
          <YAxis
            domain={[minY, maxY]}
            tick={{ fill: '#5A6582', fontSize: 11 }}
            tickFormatter={(v: number) => formatUsd(v)}
            axisLine={false}
            tickLine={false}
            width={70}
          />
          <Tooltip
            formatter={(v: number) => formatUsd(v)}
            labelStyle={{ color: '#0F1B3D', fontWeight: 600 }}
            contentStyle={{
              borderRadius: 6,
              fontSize: 12,
              border: '1px solid #E1E4EC',
              boxShadow: '0 4px 12px rgba(15,27,61,0.08)',
            }}
          />
          {/* 95% band: invisible offset + colored thickness on top */}
          <Area
            type="monotone"
            dataKey="band95Bottom"
            stackId="ci95"
            stroke="none"
            fill="transparent"
            isAnimationActive={false}
          />
          <Area
            type="monotone"
            dataKey="band95Thickness"
            stackId="ci95"
            stroke="none"
            fill="#4A3B8F"
            fillOpacity={0.1}
            isAnimationActive={false}
            name="95% credible band"
          />
          {/* 80% band on top */}
          <Area
            type="monotone"
            dataKey="band80Bottom"
            stackId="ci80"
            stroke="none"
            fill="transparent"
            isAnimationActive={false}
          />
          <Area
            type="monotone"
            dataKey="band80Thickness"
            stackId="ci80"
            stroke="none"
            fill="#4A3B8F"
            fillOpacity={0.22}
            isAnimationActive={false}
            name="80% credible band"
          />
          <ReferenceLine
            x="Now"
            stroke="#E85D26"
            strokeWidth={1.5}
            strokeDasharray="3 3"
            label={{
              value: 'Today',
              position: 'top',
              fill: '#E85D26',
              fontSize: 11,
              fontWeight: 600,
            }}
          />
          <Line
            type="monotone"
            dataKey="historical"
            stroke="#0F1B3D"
            strokeWidth={2.5}
            dot={false}
            isAnimationActive={false}
            name={`Historical (${unitLabel})`}
          />
          <Line
            type="monotone"
            dataKey="median"
            stroke="#0F1B3D"
            strokeWidth={2}
            strokeDasharray="6 4"
            dot={{ fill: '#E85D26', stroke: '#0F1B3D', strokeWidth: 1.5, r: 4 }}
            isAnimationActive={false}
            name="Median forecast"
          />
        </ComposedChart>
      </ResponsiveContainer>
      <div
        style={{
          display: 'flex',
          flexWrap: 'wrap',
          rowGap: 8,
          columnGap: 20,
          marginTop: 16,
          padding: '10px 14px',
          background: 'var(--surface-sunken)',
          border: '1px solid var(--border-2)',
          borderRadius: 6,
          fontSize: 11,
          color: 'var(--text-2)',
        }}
      >
        <Legend swatch="#0F1B3D" line>
          Historical
        </Legend>
        <Legend swatch="#0F1B3D" dashed>
          Median forecast
        </Legend>
        <Legend swatch="#4A3B8F" opacity={0.22}>
          80% credible
        </Legend>
        <Legend swatch="#4A3B8F" opacity={0.1}>
          95% credible
        </Legend>
        {showBehavioral && (
          <Legend swatch="#E85D26" dashed>
            Behavioral overlay
          </Legend>
        )}
      </div>
    </div>
  );
};

const Legend = ({
  swatch,
  opacity = 1,
  line = false,
  dashed = false,
  children,
}: {
  swatch: string;
  opacity?: number;
  line?: boolean;
  dashed?: boolean;
  children: React.ReactNode;
}) => (
  <span style={{ display: 'inline-flex', alignItems: 'center', gap: 6 }}>
    {line ? (
      <span
        style={{
          width: 16,
          height: 2,
          background: swatch,
          opacity,
          borderRadius: 1,
          borderTop: dashed ? `2px dashed ${swatch}` : 'none',
          backgroundColor: dashed ? 'transparent' : swatch,
        }}
      />
    ) : (
      <span
        style={{
          width: 14,
          height: 10,
          background: swatch,
          opacity,
          borderRadius: 2,
        }}
      />
    )}
    {children}
  </span>
);

export default FanChart;
