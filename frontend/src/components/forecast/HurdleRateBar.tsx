import { useMemo } from 'react';
import { useNetReturn } from '../../hooks/useNetReturn';
import { formatPct } from '../../utils/formatters';

interface Props {
  barrio?: string;
}

// Benchmark expected returns (USD, annual) used to frame the CABA apartment
// thesis against passive alternatives. Numbers are documented constants
// rather than live feeds — the perceptual win is the framing, not real-time
// precision. The 10Y Treasury will move to a FRED feed when the hurdle
// panel is promoted out of demo state.
//
//   US 10Y Treasury (4.5%) — late-2025 nominal yield, FRED series DGS10.
//   S&P 500 long-run (6.5%) — consensus 10y forward equity return, per
//       BlackRock CMA / Vanguard CMA midpoint. Not next-12-month.
//   Argentine USD sovereign Bonar 30 (~12%) — current yield-to-maturity
//       on AL30D as of 2026Q1. Includes substantial default-risk premium.
const BENCHMARKS = [
  {
    key: 'caba_net',
    label: 'CABA apartment · net annual',
    value_pct: null,            // filled from useNetReturn
    risk: 'Med-high',
    note: 'This model · after costs, taxes, FX friction',
    highlight: true,
    asterisk: false,
  },
  {
    key: 'spx',
    label: 'S&P 500 (long-run consensus)',
    value_pct: 6.5,
    risk: 'Medium',
    note: '10y forward CMA midpoint (BlackRock / Vanguard)',
    highlight: false,
    asterisk: false,
  },
  {
    key: 'caba_gross',
    label: 'CABA gross rental yield only',
    value_pct: null,            // filled from useNetReturn components
    risk: 'Low-med',
    note: 'Pre-cost, pre-tax — useful only as a floor',
    highlight: false,
    asterisk: false,
  },
  {
    key: 'us10y',
    label: 'US 10Y Treasury (risk-free)',
    value_pct: 4.5,
    risk: 'Low',
    note: 'FRED DGS10 · benchmark',
    highlight: false,
    asterisk: false,
  },
  {
    key: 'bonar',
    label: 'Argentine USD sovereign · Bonar 30',
    value_pct: 12.0,
    risk: 'Very high',
    note: 'AL30D YTM · priced for default risk',
    highlight: false,
    asterisk: true,
  },
] as const;

const HurdleRateBar = ({ barrio }: Props) => {
  const { data, loading } = useNetReturn(barrio);

  const rows = useMemo(() => {
    if (!data) return null;
    const tx_amortised = data.transaction_round_trip_pct / data.default_hold_years;
    const fixed = data.annual_components.reduce((s, c) => s + c.value_pct, 0);
    const caba_net = data.appreciation.median_pct + fixed + tx_amortised;
    const caba_gross =
      data.annual_components.find((c) => c.key === 'gross_yield')?.value_pct ?? 4.6;

    return BENCHMARKS.map((b) => {
      if (b.key === 'caba_net') return { ...b, value_pct: caba_net };
      if (b.key === 'caba_gross') return { ...b, value_pct: caba_gross };
      return b;
    })
      .filter((b): b is typeof b & { value_pct: number } => b.value_pct !== null)
      .slice()
      .sort((a, b) => b.value_pct - a.value_pct);
  }, [data]);

  if (loading || !rows) {
    return (
      <div className="card">
        <div className="eyebrow">Versus alternatives</div>
        <div style={{ padding: 24, color: 'var(--text-3)', fontSize: 13 }}>
          Loading benchmarks…
        </div>
      </div>
    );
  }

  const maxAbs = Math.max(...rows.map((r) => Math.abs(r.value_pct)));

  return (
    <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
      <div
        style={{
          padding: 'var(--s-4) var(--s-6)',
          borderBottom: '1px solid var(--border-2)',
        }}
      >
        <div className="eyebrow">Versus alternatives</div>
        <h3 className="title-3" style={{ marginTop: 4, marginBottom: 0 }}>
          Hurdle-rate comparison
        </h3>
        <div className="body-sm" style={{ marginTop: 4, maxWidth: 620 }}>
          Where the CABA apartment thesis sits against passive USD alternatives.
          The pitch is &quot;Treasuries plus optionality on Argentine
          normalisation,&quot; not equity-beating growth.
        </div>
      </div>

      <div style={{ padding: 'var(--s-5) var(--s-6)' }}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          {rows.map((r) => {
            const widthPct = (Math.abs(r.value_pct) / maxAbs) * 100;
            const color = r.highlight
              ? 'var(--orange-500)'
              : r.value_pct >= 0
                ? 'var(--navy-700)'
                : '#7F1D1D';
            const bg = r.highlight ? 'var(--orange-50, #FFF4EC)' : 'transparent';
            return (
              <div
                key={r.key}
                style={{
                  display: 'grid',
                  gridTemplateColumns: 'minmax(220px, 1.2fr) minmax(0, 2fr) 90px 80px',
                  alignItems: 'center',
                  gap: 12,
                  padding: '6px 8px',
                  background: bg,
                  borderRadius: 4,
                }}
              >
                <div style={{ minWidth: 0 }}>
                  <div
                    style={{
                      fontSize: 13,
                      fontWeight: r.highlight ? 600 : 500,
                      color: 'var(--text-1)',
                    }}
                  >
                    {r.label}
                    {r.asterisk && <span>*</span>}
                  </div>
                  <div style={{ fontSize: 11, color: 'var(--text-3)', marginTop: 1 }}>
                    {r.note}
                  </div>
                </div>
                <div
                  style={{
                    height: 14,
                    position: 'relative',
                    background: 'var(--surface-sunken)',
                    borderRadius: 3,
                    overflow: 'hidden',
                  }}
                >
                  <div
                    style={{
                      position: 'absolute',
                      left: 0,
                      top: 0,
                      bottom: 0,
                      width: `${widthPct}%`,
                      background: color,
                      opacity: r.highlight ? 0.9 : 0.65,
                    }}
                  />
                </div>
                <div
                  className="mono"
                  style={{
                    fontSize: 14,
                    fontWeight: r.highlight ? 700 : 600,
                    color,
                    textAlign: 'right',
                  }}
                >
                  {formatPct(r.value_pct, 1)}
                </div>
                <div
                  style={{
                    fontSize: 10,
                    color: 'var(--text-3)',
                    letterSpacing: 0.08,
                    textTransform: 'uppercase',
                    textAlign: 'right',
                  }}
                >
                  {r.risk}
                </div>
              </div>
            );
          })}
        </div>
        <div
          style={{
            marginTop: 14,
            paddingTop: 10,
            borderTop: '1px dashed var(--border-1)',
            fontSize: 10.5,
            color: 'var(--text-3)',
            lineHeight: 1.5,
          }}
        >
          * Argentine USD sovereign yield reflects substantial default-risk
          premium; the spread to Treasuries is what the market charges to hold
          country risk and is not a clean apples-to-apples comparison with the
          apartment thesis.
        </div>
      </div>
    </div>
  );
};

export default HurdleRateBar;
