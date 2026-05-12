import { useMemo, useState } from 'react';
import {
  MapContainer,
  TileLayer,
  CircleMarker,
  Tooltip,
  ZoomControl,
} from 'react-leaflet';
import 'leaflet/dist/leaflet.css';
import MapSizingFix from '../maps/MapSizingFix';
import { useBarrioRankings } from '../../hooks/useBarrioRankings';
import type { BarrioForecastEntry } from '../../types';
import { formatPct, formatUsd } from '../../utils/formatters';

const CABA_CENTER: [number, number] = [-34.6087, -58.4173];

// Diverging palette anchored to typical CABA total-return range. We use
// total_return_pct (appreciation + gross yield) for color so the heat
// map matches what the by-total-return table ranks.
type HeatStop = { max: number; color: string; label: string };
const HEAT_STOPS: HeatStop[] = [
  { max: 5, color: '#FED7AA', label: '< 5%' },
  { max: 8, color: '#FDBA74', label: '5 – 8%' },
  { max: 10, color: '#F97316', label: '8 – 10%' },
  { max: 12, color: '#C2410C', label: '10 – 12%' },
  { max: Infinity, color: '#7C2D12', label: '> 12%' },
];

const colorFor = (totalReturn: number): string =>
  (HEAT_STOPS.find((s) => totalReturn < s.max) ?? HEAT_STOPS[HEAT_STOPS.length - 1]).color;

interface Props {
  onSelectBarrio?: (name: string) => void;
}

type SortMode = 'total_return' | 'yield' | 'risk_adjusted';

const SORT_LABEL: Record<SortMode, string> = {
  total_return: 'Top 5 · total return (appreciation + yield)',
  yield: 'Top 5 · gross rental yield',
  risk_adjusted: 'Top 5 · risk-adjusted (μ / σ)',
};

const SORT_VALUE: Record<SortMode, (b: BarrioForecastEntry) => number> = {
  total_return: (b) => b.total_return_pct,
  yield: (b) => b.gross_yield_pct,
  risk_adjusted: (b) => b.risk_adjusted_pct,
};

const SORT_DISPLAY_KEY: Record<SortMode, keyof BarrioForecastEntry> = {
  total_return: 'total_return_pct',
  yield: 'gross_yield_pct',
  risk_adjusted: 'risk_adjusted_pct',
};

const BarrioForecastPanel = ({ onSelectBarrio }: Props) => {
  const { data, loading, error } = useBarrioRankings();
  const [selected, setSelected] = useState<string | null>(null);

  const tables: Record<SortMode, BarrioForecastEntry[]> = useMemo(() => {
    if (!data) {
      return { total_return: [], yield: [], risk_adjusted: [] };
    }
    const eligible = data.barrios.filter((b) => !b.thin_data);
    const sortDesc = (mode: SortMode) =>
      [...eligible]
        .sort((a, b) => SORT_VALUE[mode](b) - SORT_VALUE[mode](a))
        .slice(0, 5);
    return {
      total_return: sortDesc('total_return'),
      yield: sortDesc('yield'),
      risk_adjusted: sortDesc('risk_adjusted'),
    };
  }, [data]);

  const selectedBarrio = useMemo(
    () => data?.barrios.find((b) => b.name === selected) ?? null,
    [data, selected],
  );

  const handleSelect = (name: string) => {
    setSelected(name);
    onSelectBarrio?.(name);
  };

  if (loading) {
    return (
      <div className="card" style={{ padding: 24 }}>
        <div className="eyebrow">Where to buy</div>
        <div style={{ color: 'var(--text-3)', marginTop: 8, fontSize: 13 }}>
          Loading per-barrio forecast…
        </div>
      </div>
    );
  }
  if (error || !data) {
    return (
      <div className="card">
        <div className="eyebrow">Where to buy</div>
        <div className="error" style={{ marginTop: 8 }}>
          Could not load barrio rankings: {error ?? 'unknown error'}
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
          display: 'flex',
          alignItems: 'baseline',
          justifyContent: 'space-between',
          flexWrap: 'wrap',
          gap: 8,
        }}
      >
        <div>
          <div className="eyebrow">Where to buy</div>
          <h3 className="title-3" style={{ margin: '4px 0 0 0' }}>
            Per-barrio 1y forecast · hierarchical partial pooling
          </h3>
          <div className="body-sm" style={{ marginTop: 4, maxWidth: 620 }}>
            Each barrio is projected from the CABA-aggregate posterior
            ({formatPct(data.caba_mu_pct, 1)} ± {data.caba_sigma_pct.toFixed(1)}pp σ) via β / α
            priors. Thin-data barrios (n_eff &lt; {data.thin_data_threshold}) are excluded
            from the ranked tables — their σ is dominated by the city prior.
          </div>
        </div>
      </div>

      {/* Map + side drawer */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: selectedBarrio ? 'minmax(0, 2fr) minmax(280px, 1fr)' : '1fr',
          gap: 0,
          position: 'relative',
        }}
      >
        <div style={{ position: 'relative' }}>
          <MapContainer
            key="barrio-heat-map"
            center={CABA_CENTER}
            zoom={12}
            style={{ height: 460, width: '100%' }}
            zoomControl={false}
            scrollWheelZoom={false}
            attributionControl
          >
            <MapSizingFix />
            <ZoomControl position="topright" />
            <TileLayer
              attribution='&copy; <a href="https://carto.com/attributions">CARTO</a> · <a href="https://www.openstreetmap.org/copyright">OSM</a>'
              url="https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png"
              subdomains={['a', 'b', 'c', 'd']}
            />
            {data.barrios
              .filter((b) => b.latitude !== null && b.longitude !== null)
              .map((b) => {
                const radius = 8 + Math.min(12, b.total_return_pct);
                const isSel = b.name === selected;
                return (
                  <CircleMarker
                    key={b.name}
                    center={[b.latitude as number, b.longitude as number]}
                    radius={radius}
                    pathOptions={{
                      color: isSel ? '#1B2A4A' : colorFor(b.total_return_pct),
                      weight: isSel ? 3 : 1.5,
                      fillColor: colorFor(b.total_return_pct),
                      fillOpacity: b.thin_data ? 0.35 : 0.7,
                    }}
                    eventHandlers={{ click: () => handleSelect(b.name) }}
                  >
                    <Tooltip direction="top" offset={[0, -8]} opacity={1}>
                      <div className="mono" style={{ fontSize: 11 }}>
                        <strong>{b.name}</strong> · total return {formatPct(b.total_return_pct, 1)}
                        {b.thin_data ? ' · thin data' : ''}
                      </div>
                    </Tooltip>
                  </CircleMarker>
                );
              })}
          </MapContainer>

          {/* Floating heat-scale legend */}
          <div
            style={{
              position: 'absolute',
              left: 12,
              bottom: 12,
              zIndex: 401,
              background: 'rgba(255,255,255,0.96)',
              border: '1px solid var(--border-1)',
              borderRadius: 8,
              padding: '10px 12px',
              boxShadow: 'var(--shadow-md)',
              fontSize: 11,
            }}
          >
            <div
              style={{
                fontSize: 9,
                fontWeight: 600,
                letterSpacing: 0.14,
                textTransform: 'uppercase',
                color: 'var(--text-3)',
                marginBottom: 6,
              }}
            >
              Total return (1y)
            </div>
            {HEAT_STOPS.map((s) => (
              <div
                key={s.label}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 6,
                  lineHeight: 1.8,
                }}
              >
                <span
                  style={{
                    width: 12,
                    height: 12,
                    borderRadius: 3,
                    background: s.color,
                  }}
                />
                <span className="mono" style={{ color: 'var(--text-2)' }}>
                  {s.label}
                </span>
              </div>
            ))}
            <div
              style={{
                marginTop: 6,
                paddingTop: 6,
                borderTop: '1px dashed var(--border-1)',
                color: 'var(--text-3)',
                fontSize: 10,
              }}
            >
              Faded fill = thin data
            </div>
          </div>
        </div>

        {selectedBarrio && (
          <div
            style={{
              borderLeft: '1px solid var(--border-2)',
              padding: 'var(--s-5) var(--s-5)',
              background: 'var(--surface-sunken)',
              overflowY: 'auto',
              maxHeight: 460,
            }}
          >
            <div
              style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'baseline',
              }}
            >
              <div>
                <div className="eyebrow">Barrio detail</div>
                <h4 className="title-3" style={{ marginTop: 4, marginBottom: 0 }}>
                  {selectedBarrio.name}
                </h4>
              </div>
              <button
                onClick={() => setSelected(null)}
                style={{
                  fontSize: 11,
                  background: 'transparent',
                  border: '1px solid var(--border-1)',
                  borderRadius: 4,
                  padding: '2px 8px',
                  cursor: 'pointer',
                  color: 'var(--text-2)',
                }}
              >
                Close
              </button>
            </div>
            <div style={{ marginTop: 16, display: 'flex', flexDirection: 'column', gap: 10 }}>
              <Stat
                label="1y median appreciation"
                value={formatPct(selectedBarrio.median_change_pct, 1)}
                detail={`80% CI ${formatPct(selectedBarrio.ci_80_lower, 1)} / ${formatPct(selectedBarrio.ci_80_upper, 1)}`}
              />
              <Stat
                label="Gross rental yield"
                value={formatPct(selectedBarrio.gross_yield_pct, 1)}
                detail="Pre-cost; see waterfall for net"
              />
              <Stat
                label="Total return (1y)"
                value={formatPct(selectedBarrio.total_return_pct, 1)}
                detail="Appreciation + gross yield"
              />
              <Stat
                label="Risk-adjusted ratio"
                value={selectedBarrio.risk_adjusted_pct.toFixed(2)}
                detail={`σ = ${selectedBarrio.sigma_pct.toFixed(1)}pp`}
              />
              <Stat
                label="Current price"
                value={`${formatUsd(selectedBarrio.current_price_m2, { decimals: 0 })}/m²`}
                detail={`Tier · ${selectedBarrio.tier.replace(/_/g, ' ')}`}
              />
              <Stat
                label="Model parameters"
                value={`β=${selectedBarrio.beta.toFixed(2)} · α=${selectedBarrio.alpha.toFixed(1)}pp`}
                detail={`n_eff = ${selectedBarrio.n_eff}${selectedBarrio.thin_data ? ' (thin data — directional only)' : ''}`}
              />
            </div>
          </div>
        )}
      </div>

      {/* Three ranked tables side-by-side */}
      <div
        style={{
          padding: 'var(--s-5) var(--s-6)',
          borderTop: '1px solid var(--border-2)',
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))',
          gap: 16,
        }}
      >
        {(Object.keys(tables) as SortMode[]).map((mode) => (
          <RankTable
            key={mode}
            title={SORT_LABEL[mode]}
            rows={tables[mode]}
            valueKey={SORT_DISPLAY_KEY[mode]}
            unit={mode === 'risk_adjusted' ? '' : '%'}
            decimals={mode === 'risk_adjusted' ? 2 : 1}
            onSelect={handleSelect}
            selected={selected}
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
        Hierarchical structure: μ_barrio = μ_caba · β + α, with σ shrunk
        toward the city posterior in proportion to effective sample size.
        Barrios with n_eff &lt; {data.thin_data_threshold} are excluded from the ranked tables;
        click any centroid on the map to see its forecast regardless.
      </div>
    </div>
  );
};

interface StatProps {
  label: string;
  value: string;
  detail?: string;
}
const Stat = ({ label, value, detail }: StatProps) => (
  <div>
    <div
      style={{
        fontSize: 10,
        fontWeight: 600,
        letterSpacing: 0.1,
        textTransform: 'uppercase',
        color: 'var(--text-3)',
      }}
    >
      {label}
    </div>
    <div
      className="mono"
      style={{ fontSize: 15, fontWeight: 600, color: 'var(--text-1)', marginTop: 2 }}
    >
      {value}
    </div>
    {detail && (
      <div style={{ fontSize: 11, color: 'var(--text-3)', marginTop: 2 }}>{detail}</div>
    )}
  </div>
);

interface RankTableProps {
  title: string;
  rows: BarrioForecastEntry[];
  valueKey: keyof BarrioForecastEntry;
  unit: string;
  decimals: number;
  onSelect: (name: string) => void;
  selected: string | null;
}
const RankTable = ({
  title,
  rows,
  valueKey,
  unit,
  decimals,
  onSelect,
  selected,
}: RankTableProps) => (
  <div>
    <div
      style={{
        fontSize: 10,
        fontWeight: 700,
        letterSpacing: 0.12,
        textTransform: 'uppercase',
        color: 'var(--text-3)',
        marginBottom: 8,
      }}
    >
      {title}
    </div>
    <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
      {rows.length === 0 ? (
        <div style={{ fontSize: 11, color: 'var(--text-3)' }}>No barrios with sufficient data.</div>
      ) : (
        rows.map((r, idx) => {
          const value = r[valueKey];
          const display =
            unit === '%'
              ? `${(value as number).toFixed(decimals)}%`
              : (value as number).toFixed(decimals);
          const isSel = r.name === selected;
          return (
            <button
              key={r.name}
              onClick={() => onSelect(r.name)}
              style={{
                display: 'grid',
                gridTemplateColumns: '18px 1fr auto',
                gap: 6,
                alignItems: 'center',
                padding: '4px 6px',
                background: isSel ? 'var(--orange-50, #FFF4EC)' : 'transparent',
                border: '1px solid',
                borderColor: isSel ? 'var(--orange-500)' : 'var(--border-1)',
                borderRadius: 4,
                cursor: 'pointer',
                fontSize: 12,
                textAlign: 'left',
              }}
            >
              <span style={{ color: 'var(--text-3)', fontWeight: 600 }}>
                {idx + 1}.
              </span>
              <span style={{ color: 'var(--text-1)', fontWeight: 500 }}>
                {r.name}
              </span>
              <span
                className="mono"
                style={{ color: 'var(--navy-700, #1B2A4A)', fontWeight: 600 }}
              >
                {display}
              </span>
            </button>
          );
        })
      )}
    </div>
  </div>
);

export default BarrioForecastPanel;
