import { useMemo, useState } from 'react';
import { useNetReturn } from '../../hooks/useNetReturn';
import { formatPct } from '../../utils/formatters';

interface Props {
  barrio?: string;
}

// Composite waterfall row: a label, signed % value, and a horizontal bar
// whose width scales with the magnitude relative to the largest component.
interface BarRow {
  key: string;
  label: string;
  value_pct: number;
  source: string;
  editable: boolean;
  kind: 'gross' | 'positive' | 'negative' | 'net';
  detail?: string;
}

const COLOR_POS = '#1FA66A';
const COLOR_NEG = '#C2410C';
const COLOR_NET_POS = '#1B2A4A';
const COLOR_NET_NEG = '#7F1D1D';

const NetReturnWaterfall = ({ barrio }: Props) => {
  const { data, loading, error } = useNetReturn(barrio);
  const [holdYears, setHoldYears] = useState<number>(5);

  const rows: BarRow[] = useMemo(() => {
    if (!data) return [];
    const txAmortised = data.transaction_round_trip_pct / holdYears;
    return [
      {
        key: 'appreciation',
        label: 'Gross USD appreciation',
        value_pct: data.appreciation.median_pct,
        source: data.appreciation.source,
        editable: false,
        kind: 'gross',
        detail: `80% CI ${formatPct(data.appreciation.ci_80_lower)} / ${formatPct(data.appreciation.ci_80_upper)}`,
      },
      ...data.annual_components.map((c) => ({
        key: c.key,
        label: c.label,
        value_pct: c.value_pct,
        source: c.source,
        editable: c.editable,
        kind: (c.kind === 'positive' ? 'positive' : 'negative') as
          | 'positive'
          | 'negative',
      })),
      {
        key: 'tx_amortised',
        label: 'Transaction costs (amortised)',
        value_pct: txAmortised,
        source: `Round-trip ${formatPct(data.transaction_round_trip_pct)} ÷ ${holdYears.toFixed(0)}y`,
        editable: false,
        kind: 'negative',
        detail: 'Buy + sell fees, escribano, ITI, corredor',
      },
    ];
  }, [data, holdYears]);

  const net = useMemo(() => {
    if (!data) return null;
    const txAmortised = data.transaction_round_trip_pct / holdYears;
    const fixedCosts = data.annual_components.reduce(
      (sum, c) => sum + c.value_pct,
      0,
    );
    const median = data.appreciation.median_pct + fixedCosts + txAmortised;
    const ci_lower = data.appreciation.ci_80_lower + fixedCosts + txAmortised;
    const ci_upper = data.appreciation.ci_80_upper + fixedCosts + txAmortised;
    return { median, ci_lower, ci_upper };
  }, [data, holdYears]);

  // Scale bar widths by the largest absolute % across all rows + net.
  const maxAbs = useMemo(() => {
    const vals = rows.map((r) => Math.abs(r.value_pct));
    if (net) vals.push(Math.abs(net.median));
    return Math.max(0.1, ...vals);
  }, [rows, net]);

  if (loading) {
    return (
      <div className="card">
        <div className="eyebrow">Net return decomposition</div>
        <div style={{ padding: 32, textAlign: 'center', color: 'var(--text-3)' }}>
          Loading components…
        </div>
      </div>
    );
  }
  if (error || !data || !net) {
    return (
      <div className="card">
        <div className="eyebrow">Net return decomposition</div>
        <div className="error" style={{ marginTop: 8 }}>
          Could not load net-return data: {error ?? 'unknown error'}
        </div>
      </div>
    );
  }

  return (
    <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
      <div
        style={{
          padding: 'var(--s-4) var(--s-6)',
          borderBottom: '1px solid var(--border-2)',
        }}
      >
        <div className="eyebrow">What you'll earn</div>
        <div
          style={{
            display: 'flex',
            alignItems: 'baseline',
            justifyContent: 'space-between',
            flexWrap: 'wrap',
            gap: 12,
            marginTop: 4,
          }}
        >
          <h3 className="title-3" style={{ margin: 0 }}>
            Net annual USD return · {barrio || 'CABA aggregate'}
          </h3>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <label
              htmlFor="hold-years"
              className="eyebrow"
              style={{ fontSize: 10 }}
            >
              Hold period
            </label>
            <input
              id="hold-years"
              type="range"
              min={1}
              max={15}
              step={1}
              value={holdYears}
              onChange={(e) => setHoldYears(Number(e.target.value))}
              style={{ width: 140 }}
            />
            <span
              className="mono"
              style={{ fontSize: 13, fontWeight: 600, minWidth: 38 }}
            >
              {holdYears}y
            </span>
          </div>
        </div>
      </div>

      <div style={{ padding: 'var(--s-5) var(--s-6)' }}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          {rows.map((r) => {
            const pos = r.value_pct >= 0;
            const color = pos ? COLOR_POS : COLOR_NEG;
            const widthPct = (Math.abs(r.value_pct) / maxAbs) * 100;
            return (
              <div
                key={r.key}
                style={{
                  display: 'grid',
                  gridTemplateColumns: '1fr 80px 1fr',
                  alignItems: 'center',
                  gap: 12,
                }}
              >
                <div style={{ minWidth: 0 }}>
                  <div
                    style={{
                      fontSize: 13,
                      fontWeight: 500,
                      color: 'var(--text-1)',
                      display: 'flex',
                      alignItems: 'center',
                      gap: 6,
                    }}
                  >
                    {r.label}
                    {r.editable && (
                      <span
                        title="Defaults shown; can be overridden in scenario explorer"
                        style={{
                          fontSize: 9,
                          letterSpacing: 0.1,
                          textTransform: 'uppercase',
                          color: 'var(--text-3)',
                          border: '1px solid var(--border-1)',
                          padding: '1px 4px',
                          borderRadius: 3,
                        }}
                      >
                        editable
                      </span>
                    )}
                  </div>
                  <div
                    style={{
                      fontSize: 11,
                      color: 'var(--text-3)',
                      marginTop: 1,
                    }}
                  >
                    {r.source}
                    {r.detail && (
                      <span style={{ marginLeft: 6, color: 'var(--text-3)' }}>
                        · {r.detail}
                      </span>
                    )}
                  </div>
                </div>
                <div
                  className="mono"
                  style={{
                    fontSize: 14,
                    fontWeight: 600,
                    color,
                    textAlign: 'right',
                  }}
                >
                  {formatPct(r.value_pct, 1)}
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
                      left: pos ? '50%' : `calc(50% - ${widthPct / 2}%)`,
                      top: 0,
                      bottom: 0,
                      width: `${widthPct / 2}%`,
                      background: color,
                      opacity: 0.7,
                    }}
                  />
                  <div
                    style={{
                      position: 'absolute',
                      left: '50%',
                      top: 0,
                      bottom: 0,
                      width: 1,
                      background: 'var(--border-2)',
                    }}
                  />
                </div>
              </div>
            );
          })}
        </div>

        <div
          style={{
            marginTop: 18,
            paddingTop: 14,
            borderTop: '2px solid var(--border-2)',
            display: 'grid',
            gridTemplateColumns: '1fr 80px 1fr',
            alignItems: 'center',
            gap: 12,
          }}
        >
          <div>
            <div
              style={{
                fontSize: 10,
                fontWeight: 700,
                letterSpacing: 0.12,
                textTransform: 'uppercase',
                color: 'var(--text-2)',
              }}
            >
              Net annual USD return
            </div>
            <div
              style={{
                fontSize: 11,
                color: 'var(--text-3)',
                marginTop: 2,
              }}
            >
              80% band {formatPct(net.ci_lower, 1)} / {formatPct(net.ci_upper, 1)} · band shifts with model uncertainty only
            </div>
          </div>
          <div
            className="mono"
            style={{
              fontSize: 22,
              fontWeight: 700,
              color: net.median >= 0 ? COLOR_NET_POS : COLOR_NET_NEG,
              textAlign: 'right',
            }}
          >
            {formatPct(net.median, 1)}
          </div>
          <div
            style={{
              height: 18,
              position: 'relative',
              background: 'var(--surface-sunken)',
              borderRadius: 3,
              overflow: 'hidden',
            }}
          >
            <div
              style={{
                position: 'absolute',
                left:
                  net.median >= 0
                    ? '50%'
                    : `calc(50% - ${(Math.abs(net.median) / maxAbs) * 50}%)`,
                top: 0,
                bottom: 0,
                width: `${(Math.abs(net.median) / maxAbs) * 50}%`,
                background: net.median >= 0 ? COLOR_NET_POS : COLOR_NET_NEG,
                opacity: 0.85,
              }}
            />
            <div
              style={{
                position: 'absolute',
                left: '50%',
                top: 0,
                bottom: 0,
                width: 1,
                background: 'var(--border-2)',
              }}
            />
          </div>
        </div>

        <div
          style={{
            marginTop: 14,
            fontSize: 11,
            color: 'var(--text-3)',
            lineHeight: 1.5,
          }}
        >
          The transaction-cost line amortises a one-time {formatPct(data.transaction_round_trip_pct, 0)} round-trip
          cost across {holdYears} year{holdYears === 1 ? '' : 's'}. Shortening the hold compresses net return;
          patience is the trade. The 80% band reflects model uncertainty on gross appreciation — carrying-cost
          components are treated as deterministic.
        </div>
      </div>
    </div>
  );
};

export default NetReturnWaterfall;
