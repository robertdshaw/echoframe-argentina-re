import { useEffect, useMemo, useState } from 'react';
import { forecastApi } from '../../api/client';
import type { ForecastResponse } from '../../types';
import { formatPct, formatUsd } from '../../utils/formatters';

/*
 * Campos-specific narrative panels. Mirrors the departamentos
 * design pattern (Where / Earn / Risk / Vs) but adapted to
 * agricultural-land economics:
 *   - income is lease/operating yield (not rental yield)
 *   - retenciones (export tax) replaces ABL property tax
 *   - input costs replace expensas / vacancy
 *   - transaction round-trip is lower (~3-4% vs 7%)
 *   - hold periods are longer (default 7 years vs 5)
 *   - tail risks are commodity-price / drought / retenciones-hike
 *     rather than FX-shock / regime-crisis
 *
 * Numbers are documented Q1 2026 Argentine farmland defaults; sources
 * are noted in-comment. They're seeded constants rather than live API
 * pulls so this redesign ships without a multi-day backend extension.
 */

// ============================================================
// Where to buy — zone-level forecast cards
// ============================================================

const ZONES: { key: string; label: string; description: string }[] = [
  {
    key: 'core_pampa',
    label: 'Core Pampa',
    description: 'Premium soils · Pergamino / Junín / Rojas · highest output per ha',
  },
  {
    key: 'santa_fe',
    label: 'Santa Fe',
    description: 'Strong soils · centre-south Santa Fe province · soybean and wheat',
  },
  {
    key: 'frontier',
    label: 'Frontier',
    description: 'Northern expansion zones · Santiago del Estero / Chaco · higher return, higher risk',
  },
  {
    key: 'periurban',
    label: 'Peri-urban',
    description: 'Within 60km of CABA · structural development optionality · highest dispersion',
  },
];

interface ZoneForecastEntry {
  key: string;
  label: string;
  description: string;
  median_pct: number;
  ci_lower: number;
  ci_upper: number;
  current_price_ha: number;
}

interface CamposZonePanelProps {
  selected?: string;
  onSelect?: (zone: string) => void;
}

export const CamposZonePanel = ({ selected, onSelect }: CamposZonePanelProps) => {
  const [data, setData] = useState<ZoneForecastEntry[] | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    Promise.all(
      ZONES.map(async (z) => {
        try {
          const r: ForecastResponse = await forecastApi.getCampos(z.key);
          const m = r.forecasts['1']?.model_estimate;
          if (!m) return null;
          return {
            key: z.key,
            label: z.label,
            description: z.description,
            median_pct: m.median_change_pct,
            ci_lower: m.ci_80.lower,
            ci_upper: m.ci_80.upper,
            current_price_ha: r.current_price,
          };
        } catch {
          return null;
        }
      }),
    )
      .then((rows) => {
        if (cancelled) return;
        const filtered = rows.filter((r): r is ZoneForecastEntry => r !== null);
        // Sort by median appreciation descending.
        filtered.sort((a, b) => b.median_pct - a.median_pct);
        setData(filtered);
        setLoading(false);
      })
      .catch((err: Error) => {
        if (cancelled) return;
        setError(err.message);
        setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  if (loading) {
    return (
      <div className="card" style={{ padding: 24 }}>
        <div className="eyebrow">Where to buy</div>
        <div style={{ color: 'var(--text-3)', marginTop: 8, fontSize: 13 }}>
          Loading zone forecasts…
        </div>
      </div>
    );
  }
  if (error || !data) {
    return (
      <div className="card">
        <div className="eyebrow">Where to buy</div>
        <div className="error" style={{ marginTop: 8 }}>
          Zone forecasts unavailable: {error ?? 'unknown error'}
        </div>
      </div>
    );
  }

  const maxAbs = Math.max(...data.map((z) => Math.abs(z.median_pct)), 1);

  return (
    <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
      <div
        style={{
          padding: 'var(--s-4) var(--s-6)',
          borderBottom: '1px solid var(--border-2)',
        }}
      >
        <div className="eyebrow">Where to buy</div>
        <h3 className="title-3" style={{ margin: '4px 0 0 0' }}>
          Argentine farmland · zone-level 12-month forecast
        </h3>
        <div className="body-sm" style={{ marginTop: 4, maxWidth: 640 }}>
          Each region has a different soil-quality profile, commodity mix,
          and risk envelope. Click any zone to refocus the rest of the
          page on it.
        </div>
      </div>
      <div style={{ padding: 'var(--s-4) var(--s-6)', display: 'grid', gap: 10 }}>
        {data.map((z) => {
          const isSel = selected === z.key;
          const positive = z.median_pct >= 0;
          const barColor = positive ? '#1FA66A' : '#C2410C';
          const widthPct = (Math.abs(z.median_pct) / maxAbs) * 100;
          return (
            <button
              key={z.key}
              onClick={() => onSelect?.(z.key)}
              style={{
                display: 'grid',
                gridTemplateColumns: 'minmax(0, 1.2fr) minmax(0, 1.4fr) 90px',
                gap: 14,
                alignItems: 'center',
                padding: '10px 12px',
                background: isSel ? 'var(--orange-50)' : 'var(--surface-raised)',
                border: '1px solid',
                borderColor: isSel ? 'var(--orange-500)' : 'var(--border-1)',
                borderRadius: 8,
                cursor: 'pointer',
                textAlign: 'left',
                transition: 'border-color 120ms ease, background 120ms ease',
              }}
            >
              <div style={{ minWidth: 0 }}>
                <div
                  style={{
                    fontSize: 14,
                    fontWeight: 600,
                    color: 'var(--text-1)',
                  }}
                >
                  {z.label}
                </div>
                <div
                  style={{
                    fontSize: 11.5,
                    color: 'var(--text-2)',
                    marginTop: 2,
                  }}
                >
                  {z.description}
                </div>
                <div
                  style={{
                    fontSize: 11,
                    color: 'var(--text-3)',
                    marginTop: 4,
                  }}
                  className="mono"
                >
                  Current {formatUsd(z.current_price_ha, { decimals: 0 })}/ha
                </div>
              </div>
              <div>
                <div
                  style={{
                    height: 14,
                    background: 'var(--surface-sunken)',
                    borderRadius: 3,
                    overflow: 'hidden',
                    position: 'relative',
                  }}
                >
                  <div
                    style={{
                      position: 'absolute',
                      left: 0,
                      top: 0,
                      bottom: 0,
                      width: `${widthPct}%`,
                      background: barColor,
                      opacity: 0.7,
                    }}
                  />
                </div>
                <div
                  style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    marginTop: 3,
                    fontSize: 10,
                    color: 'var(--text-3)',
                  }}
                  className="mono"
                >
                  <span>Likely {formatPct(z.ci_lower, 1)}</span>
                  <span>to {formatPct(z.ci_upper, 1)}</span>
                </div>
              </div>
              <div
                className="mono"
                style={{
                  fontSize: 18,
                  fontWeight: 700,
                  color: barColor,
                  textAlign: 'right',
                }}
              >
                {formatPct(z.median_pct, 1)}
              </div>
            </button>
          );
        })}
      </div>
    </div>
  );
};

// ============================================================
// What you'll earn — net return waterfall (campos)
// ============================================================

interface CamposReturnPanelProps {
  zone?: string;
}

// Q1 2026 Argentine farmland defaults. Documented sources:
//   gross_lease_yield (11.0%) — typical CABA-fronted core-pampa lease
//       rate as % of land value (Bichara Real Estate / Pampa Inmobiliaria
//       2025 surveys); range 8-14% by zone.
//   input_costs   (-4.0%) — seed / fertiliser / fuel / machinery as
//       fraction of land value, INTA insumos cost-share data.
//   labor          (-0.5%) — labour + admin (typical lease arrangements
//       transfer most labour to the tenant).
//   retenciones    (-2.5%) — DJVE-weighted average export-tax drag at
//       2026 rates (soybean 33%, wheat 12%, maize 12%); ~25-30% of net
//       commodity revenue effectively reduces yield by ~2-3% of land
//       value depending on crop mix.
//   land_tax       (-0.3%) — provincial impuesto inmobiliario rural
//       (Buenos Aires province rates).
//   fx_friction    (-0.4%) — round-trip MEP spread on ARS-to-USD
//       conversion of lease income.
//   tx_round_trip  (-4.0%) — buy + sell escribano + corredor fees,
//       amortised over hold period. Lower than urban (~7%) because
//       rural agencies charge thinner spreads.
//   default_hold_years (7) — campos are intergenerational holdings;
//       a 7-year window is the conservative-investor convention.
const CAMPOS_DEFAULTS = {
  gross_lease_yield: 11.0,
  input_costs: -4.0,
  labor: -0.5,
  retenciones: -2.5,
  land_tax: -0.3,
  fx_friction: -0.4,
  tx_round_trip: -4.0,
  default_hold_years: 7,
};

interface ReturnRow {
  label: string;
  value_pct: number;
  source: string;
}

export const CamposReturnPanel = ({ zone }: CamposReturnPanelProps) => {
  const [forecast, setForecast] = useState<ForecastResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [holdYears, setHoldYears] = useState(CAMPOS_DEFAULTS.default_hold_years);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    forecastApi
      .getCampos(zone)
      .then((r) => {
        if (!cancelled) {
          setForecast(r);
          setLoading(false);
        }
      })
      .catch((err: Error) => {
        if (!cancelled) {
          setError(err.message);
          setLoading(false);
        }
      });
    return () => {
      cancelled = true;
    };
  }, [zone]);

  const computed = useMemo(() => {
    if (!forecast) return null;
    const m = forecast.forecasts['1']?.model_estimate;
    if (!m) return null;
    const appreciation = m.median_change_pct;
    const ciLower = m.ci_80.lower;
    const ciUpper = m.ci_80.upper;
    const txAmortised = CAMPOS_DEFAULTS.tx_round_trip / holdYears;
    const rows: ReturnRow[] = [
      {
        label: 'Land-value appreciation',
        value_pct: appreciation,
        source: 'Bayesian ensemble · year-1 posterior',
      },
      {
        label: 'Gross lease yield',
        value_pct: CAMPOS_DEFAULTS.gross_lease_yield,
        source: 'Annual lease as % of land value (typical Argentine farmland)',
      },
      {
        label: 'Input costs (seed / fertiliser / fuel)',
        value_pct: CAMPOS_DEFAULTS.input_costs,
        source: 'INTA insumos cost-share data',
      },
      {
        label: 'Labour & admin',
        value_pct: CAMPOS_DEFAULTS.labor,
        source: 'Tenant-borne in most leases · light owner-side admin',
      },
      {
        label: 'Retenciones (export tax)',
        value_pct: CAMPOS_DEFAULTS.retenciones,
        source: 'DJVE-weighted average · 2026 rates · soy 33% / wheat 12% / maize 12%',
      },
      {
        label: 'Land tax (Buenos Aires rural)',
        value_pct: CAMPOS_DEFAULTS.land_tax,
        source: 'Provincial impuesto inmobiliario rural',
      },
      {
        label: 'FX conversion friction',
        value_pct: CAMPOS_DEFAULTS.fx_friction,
        source: 'Round-trip MEP spread',
      },
      {
        label: 'Transaction costs (amortised)',
        value_pct: txAmortised,
        source: `Round-trip ${formatPct(CAMPOS_DEFAULTS.tx_round_trip, 0)} ÷ ${holdYears}y`,
      },
    ];
    const fixed = rows.reduce((s, r) => s + r.value_pct, 0);
    return {
      rows,
      net: fixed,
      ci_lower: fixed - appreciation + ciLower,
      ci_upper: fixed - appreciation + ciUpper,
    };
  }, [forecast, holdYears]);

  if (loading) {
    return (
      <div className="card" style={{ padding: 24 }}>
        <div className="eyebrow">What you'll earn</div>
        <div style={{ color: 'var(--text-3)', marginTop: 8, fontSize: 13 }}>
          Computing net return…
        </div>
      </div>
    );
  }
  if (error || !computed) {
    return (
      <div className="card">
        <div className="eyebrow">What you'll earn</div>
        <div className="error" style={{ marginTop: 8 }}>
          Net return unavailable: {error ?? 'unknown error'}
        </div>
      </div>
    );
  }

  const maxAbs = Math.max(
    ...computed.rows.map((r) => Math.abs(r.value_pct)),
    Math.abs(computed.net),
    1,
  );

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
            Net annual USD return · {zone ? humanZone(zone) : 'Argentine farmland'}
          </h3>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <label htmlFor="campos-hold" className="eyebrow" style={{ fontSize: 10 }}>
              Hold period
            </label>
            <input
              id="campos-hold"
              type="range"
              min={3}
              max={20}
              step={1}
              value={holdYears}
              onChange={(e) => setHoldYears(Number(e.target.value))}
              style={{ width: 140 }}
            />
            <span className="mono" style={{ fontSize: 13, fontWeight: 600, minWidth: 38 }}>
              {holdYears}y
            </span>
          </div>
        </div>
      </div>

      <div style={{ padding: 'var(--s-5) var(--s-6)' }}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          {computed.rows.map((r) => {
            const pos = r.value_pct >= 0;
            const color = pos ? '#1FA66A' : '#C2410C';
            const widthPct = (Math.abs(r.value_pct) / maxAbs) * 100;
            return (
              <div
                key={r.label}
                style={{
                  display: 'grid',
                  gridTemplateColumns: '1fr 80px 1fr',
                  alignItems: 'center',
                  gap: 12,
                }}
              >
                <div>
                  <div style={{ fontSize: 13, fontWeight: 500, color: 'var(--text-1)' }}>
                    {r.label}
                  </div>
                  <div style={{ fontSize: 11, color: 'var(--text-3)', marginTop: 1 }}>
                    {r.source}
                  </div>
                </div>
                <div
                  className="mono"
                  style={{ fontSize: 14, fontWeight: 600, color, textAlign: 'right' }}
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
            <div style={{ fontSize: 11, color: 'var(--text-3)', marginTop: 2 }}>
              80% band {formatPct(computed.ci_lower, 1)} / {formatPct(computed.ci_upper, 1)} ·
              uncertainty driven by land-value forecast only
            </div>
          </div>
          <div
            className="mono"
            style={{
              fontSize: 22,
              fontWeight: 700,
              color: computed.net >= 0 ? '#1B2A4A' : '#7F1D1D',
              textAlign: 'right',
            }}
          >
            {formatPct(computed.net, 1)}
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
                  computed.net >= 0
                    ? '50%'
                    : `calc(50% - ${(Math.abs(computed.net) / maxAbs) * 50}%)`,
                top: 0,
                bottom: 0,
                width: `${(Math.abs(computed.net) / maxAbs) * 50}%`,
                background: computed.net >= 0 ? '#1B2A4A' : '#7F1D1D',
                opacity: 0.85,
              }}
            />
          </div>
        </div>

        <div style={{ marginTop: 14, fontSize: 11, color: 'var(--text-3)', lineHeight: 1.5 }}>
          Drag the hold-period slider to see how patience changes the
          take-home. Transaction costs amortise over the chosen years;
          shorter holds compress net return materially in farmland because
          the lease-income flywheel hasn't had time to compound.
        </div>
      </div>
    </div>
  );
};

const humanZone = (key: string): string => {
  const found = ZONES.find((z) => z.key === key);
  return found?.label ?? key;
};

// ============================================================
// What could go wrong — 3 scenarios (campos-specific)
// ============================================================

interface ScenarioRow {
  key: string;
  label: string;
  probability: number;
  median_pct: number;
  band_lower_pct: number;
  band_upper_pct: number;
  description: string;
  analogue: string;
}

interface CamposScenariosPanelProps {
  zone?: string;
}

export const CamposScenariosPanel = ({ zone }: CamposScenariosPanelProps) => {
  const [forecast, setForecast] = useState<ForecastResponse | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    forecastApi.getCampos(zone).then((r) => {
      if (!cancelled) {
        setForecast(r);
        setLoading(false);
      }
    });
    return () => {
      cancelled = true;
    };
  }, [zone]);

  const scenarios: ScenarioRow[] = useMemo(() => {
    const m = forecast?.forecasts['1']?.model_estimate;
    const base_med = m?.median_change_pct ?? 7.0;
    const base_lo = m?.ci_80.lower ?? 2.0;
    const base_up = m?.ci_80.upper ?? 12.0;
    return [
      {
        key: 'base',
        label: 'Base case · commodity strength continues',
        probability: 0.65,
        median_pct: base_med,
        band_lower_pct: base_lo,
        band_upper_pct: base_up,
        description:
          'Current soy / maize / wheat futures hold near 2025 levels; retenciones unchanged at 33%. Lease cash yield continues to capitalise into land prices.',
        analogue: '2024-2025 anchor → +6 to +9% realised by zone',
      },
      {
        key: 'commodity_crash',
        label: 'Commodity crash · soy < $300/ton durably',
        probability: 0.22,
        median_pct: -8.5,
        band_lower_pct: -14.0,
        band_upper_pct: -3.5,
        description:
          'Global oilseed glut compresses prices below break-even for Argentine producers. Lease income falls, land sales lengthen, USD/ha re-anchors lower.',
        analogue: '2018-2019 soy bust → -10% over the following 12 months',
      },
      {
        key: 'drought_or_retenciones',
        label: 'Drought or retenciones hike',
        probability: 0.13,
        median_pct: -6.0,
        band_lower_pct: -11.0,
        band_upper_pct: -2.0,
        description:
          'La Niña pattern returns and the BA / Santa Fe core suffers a >25% yield loss, OR retenciones step up materially. Either path compresses owner cash returns by 30-50% for the year.',
        analogue: '2022-23 drought + 2008 retenciones hike → -8 to -12%',
      },
    ];
  }, [forecast]);

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

  const domain: [number, number] = [-20, 18];
  const [dLo, dHi] = domain;
  const span = dHi - dLo;
  const totalProb = scenarios.reduce((s, x) => s + x.probability, 0);

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
          Base case from the model posterior; tail scenarios use empirical
          drawdowns from the 2018-19 soy bust and 2022-23 drought episodes.
          Probabilities sum to {(totalProb * 100).toFixed(0)}% — remainder
          is assigned to outcomes outside these three named regimes.
        </div>
      </div>
      <div style={{ padding: '0 var(--s-6) var(--s-5)' }}>
        {scenarios.map((s) => {
          const color =
            s.median_pct >= 0 ? '#1FA66A' : s.median_pct > -10 ? '#C2410C' : '#7F1D1D';
          const lowerPx = ((s.band_lower_pct - dLo) / span) * 100;
          const upperPx = ((s.band_upper_pct - dLo) / span) * 100;
          const medianPx = ((s.median_pct - dLo) / span) * 100;
          const zeroPx = ((0 - dLo) / span) * 100;
          return (
            <div
              key={s.key}
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
                <div>
                  <div
                    style={{
                      fontSize: 13,
                      fontWeight: 600,
                      color: 'var(--text-1)',
                    }}
                  >
                    {s.label}
                  </div>
                  <div
                    style={{
                      fontSize: 11.5,
                      color: 'var(--text-2)',
                      marginTop: 2,
                      lineHeight: 1.45,
                    }}
                  >
                    {s.description}
                  </div>
                  <div
                    style={{
                      fontSize: 10.5,
                      color: 'var(--text-3)',
                      fontStyle: 'italic',
                      marginTop: 3,
                    }}
                  >
                    Last episode: {s.analogue}
                  </div>
                </div>
                <div style={{ textAlign: 'right' }}>
                  <div
                    className="mono"
                    style={{ fontSize: 18, fontWeight: 700, color: 'var(--text-1)' }}
                  >
                    {(s.probability * 100).toFixed(0)}%
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
                      }}
                    />
                  </div>
                </div>
                <div style={{ textAlign: 'right' }}>
                  <div className="mono" style={{ fontSize: 14, fontWeight: 600, color }}>
                    {formatPct(s.median_pct, 1)}
                  </div>
                  <div
                    style={{
                      fontSize: 9.5,
                      letterSpacing: 0.12,
                      textTransform: 'uppercase',
                      color: 'var(--text-3)',
                    }}
                  >
                    median impact
                  </div>
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};

// ============================================================
// Versus alternatives — campos hurdle bar
// ============================================================

interface CamposHurdleBarProps {
  zone?: string;
}

export const CamposHurdleBar = ({ zone }: CamposHurdleBarProps) => {
  const [forecast, setForecast] = useState<ForecastResponse | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    forecastApi.getCampos(zone).then((r) => {
      if (!cancelled) {
        setForecast(r);
        setLoading(false);
      }
    });
    return () => {
      cancelled = true;
    };
  }, [zone]);

  const rows = useMemo(() => {
    const m = forecast?.forecasts['1']?.model_estimate;
    const appreciation = m?.median_change_pct ?? 7.0;
    // Use the same campos cost stack the waterfall uses, with a 7y
    // amortisation. Net = appreciation + 11 - 4 - 0.5 - 2.5 - 0.3 - 0.4 - 4/7.
    const tx = CAMPOS_DEFAULTS.tx_round_trip / CAMPOS_DEFAULTS.default_hold_years;
    const net =
      appreciation +
      CAMPOS_DEFAULTS.gross_lease_yield +
      CAMPOS_DEFAULTS.input_costs +
      CAMPOS_DEFAULTS.labor +
      CAMPOS_DEFAULTS.retenciones +
      CAMPOS_DEFAULTS.land_tax +
      CAMPOS_DEFAULTS.fx_friction +
      tx;
    return [
      {
        key: 'campos_net',
        label: 'Argentine farmland · net annual',
        value_pct: net,
        risk: 'Med-high',
        note: 'This model · after costs, retenciones, FX, transaction friction',
        highlight: true,
        asterisk: false,
      },
      {
        key: 'soy_futures',
        label: 'Soybean futures (CBOT, expected)',
        value_pct: 4.0,
        risk: 'Medium',
        note: 'Long-run real return on soy futures · USDA / CBOT consensus',
        highlight: false,
        asterisk: false,
      },
      {
        key: 'campos_yield_only',
        label: 'Campos cash yield only',
        value_pct: 4.2,
        risk: 'Low-med',
        note: 'Lease income net of costs — before any appreciation',
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
    ]
      .slice()
      .sort((a, b) => b.value_pct - a.value_pct);
  }, [forecast]);

  if (loading) {
    return (
      <div className="card" style={{ padding: 24 }}>
        <div className="eyebrow">Versus alternatives</div>
        <div style={{ color: 'var(--text-3)', marginTop: 8, fontSize: 13 }}>
          Loading benchmarks…
        </div>
      </div>
    );
  }

  const maxAbs = Math.max(...rows.map((r) => Math.abs(r.value_pct)), 1);

  return (
    <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
      <div
        style={{
          padding: 'var(--s-4) var(--s-6)',
          borderBottom: '1px solid var(--border-2)',
        }}
      >
        <div className="eyebrow">Versus alternatives</div>
        <h3 className="title-3" style={{ margin: '4px 0 0 0' }}>
          Hurdle-rate comparison
        </h3>
        <div className="body-sm" style={{ marginTop: 4, maxWidth: 640 }}>
          Where Argentine farmland sits against passive USD alternatives.
          The pitch is &quot;a productive USD asset with cash yield plus
          optionality on Argentine soft-commodity strength&quot; — not
          equity-beating growth.
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
            const bg = r.highlight ? 'var(--orange-50)' : 'transparent';
            return (
              <div
                key={r.key}
                style={{
                  display: 'grid',
                  gridTemplateColumns: 'minmax(220px, 1.2fr) minmax(0, 2fr) 90px 80px',
                  gap: 12,
                  alignItems: 'center',
                  padding: '6px 8px',
                  background: bg,
                  borderRadius: 4,
                }}
              >
                <div>
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
          premium; the spread to Treasuries is what the market charges to
          hold country risk and is not an apples-to-apples comparison with
          a productive asset like farmland.
        </div>
      </div>
    </div>
  );
};
