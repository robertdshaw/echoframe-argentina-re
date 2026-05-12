import { useMemo } from 'react';
import {
  MapContainer,
  TileLayer,
  CircleMarker,
  Tooltip,
  Popup,
  ZoomControl,
} from 'react-leaflet';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import { useListings } from '../../hooks/useListings';
import { formatNumber, formatUsd } from '../../utils/formatters';

// CABA city centre (Plaza de Mayo); used when no listings have geometry.
const CABA_CENTER: [number, number] = [-34.6087, -58.4173];

// Price-per-m² → marker color. Five bins anchored to real BA distribution.
const PRICE_BINS: Array<{ max: number; color: string; label: string }> = [
  { max: 1500, color: '#2E7D32', label: '< $1,500' },
  { max: 2200, color: '#7CB342', label: '$1,500 – $2,200' },
  { max: 3000, color: '#FBC02D', label: '$2,200 – $3,000' },
  { max: 4500, color: '#FB8C00', label: '$3,000 – $4,500' },
  { max: Infinity, color: '#C62828', label: '> $4,500' },
];

const binFor = (price?: number | null) => {
  if (price === null || price === undefined) {
    return { max: 0, color: '#8C95AD', label: 'Unknown' };
  }
  return PRICE_BINS.find((b) => price < b.max) ?? PRICE_BINS[PRICE_BINS.length - 1];
};

// Patch Leaflet's default icon paths so markers don't 404 in Vite bundlers.
// (We don't use the default marker — only CircleMarker — but other libs may.)
// eslint-disable-next-line @typescript-eslint/no-explicit-any
delete (L.Icon.Default.prototype as any)._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl:
    'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png',
  iconUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png',
  shadowUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png',
});

interface Props {
  barrio?: string;
}

const PropertyMap = ({ barrio }: Props) => {
  const { listings, loading, error, avg_price } = useListings(
    'departamentos',
    barrio,
    150,
  );

  // Accept any listing with coordinates. Live scraped listings have
  // total price (price_usd) but not price_per_m2 — they still get
  // plotted, just bucketed by total-price proxy.
  const geo = useMemo(
    () =>
      listings.filter(
        (l) =>
          l.latitude !== null &&
          l.longitude !== null &&
          (l.price_per_m2 || l.price_usd),
      ),
    [listings],
  );

  const center: [number, number] = useMemo(() => {
    if (!geo.length) return CABA_CENTER;
    const lat = geo.reduce((s, l) => s + (l.latitude ?? 0), 0) / geo.length;
    const lon = geo.reduce((s, l) => s + (l.longitude ?? 0), 0) / geo.length;
    return [lat, lon];
  }, [geo]);

  // Quick stats for the legend ribbon. Median is computed only over listings
  // that actually have a per-m² price — live Properati listings carry total
  // price but not surface, so they're plotted on the map but excluded from
  // the aggregate to avoid silently anchoring it to $0.
  const stats = useMemo(() => {
    if (!geo.length) return null;
    const prices = geo
      .map((l) => l.price_per_m2 ?? 0)
      .filter((p) => p > 0)
      .sort((a, b) => a - b);
    const median = prices[Math.floor(prices.length / 2)] ?? 0;
    return {
      n: geo.length,
      n_priced: prices.length,
      median,
      min: prices[0] ?? 0,
      max: prices[prices.length - 1] ?? 0,
    };
  }, [geo]);

  return (
    <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
      <div
        style={{
          padding: 'var(--s-4) var(--s-6)',
          borderBottom: '1px solid var(--border-2)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          flexWrap: 'wrap',
          gap: 12,
        }}
      >
        <div>
          <div className="eyebrow">Geospatial</div>
          <div className="title-2" style={{ marginTop: 2 }}>
            Listings map · {barrio || 'All CABA'}
          </div>
        </div>
        {stats && (
          <div style={{ display: 'flex', gap: 18, fontSize: 12 }}>
            <div>
              <div className="eyebrow" style={{ fontSize: 9 }}>
                Plotted
              </div>
              <div className="mono" style={{ fontWeight: 600 }}>
                {stats.n} listings
              </div>
            </div>
            <div>
              <div className="eyebrow" style={{ fontSize: 9 }}>
                Median (n={stats.n_priced})
              </div>
              <div className="mono" style={{ fontWeight: 600 }}>
                {formatUsd(stats.median)} /m²
              </div>
            </div>
            <div>
              <div className="eyebrow" style={{ fontSize: 9 }}>
                Avg /m²
              </div>
              <div className="mono" style={{ fontWeight: 600 }}>
                {formatUsd(avg_price)} /m²
              </div>
            </div>
            <div>
              <div className="eyebrow" style={{ fontSize: 9 }}>
                Range
              </div>
              <div className="mono" style={{ fontWeight: 600 }}>
                {formatUsd(stats.min)} – {formatUsd(stats.max)}
              </div>
            </div>
          </div>
        )}
      </div>

      <div style={{ position: 'relative' }}>
        {loading && (
          <div
            style={{
              position: 'absolute',
              inset: 0,
              background: 'var(--surface-sunken)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              zIndex: 400,
              fontSize: 13,
              color: 'var(--text-3)',
            }}
          >
            Loading map…
          </div>
        )}
        {error && (
          <div className="error" style={{ margin: 16 }}>
            Could not load listings: {error}
          </div>
        )}
        <MapContainer
          center={center}
          zoom={12}
          style={{ height: 480, width: '100%' }}
          zoomControl={false}
          scrollWheelZoom={false}
          attributionControl
        >
          <ZoomControl position="topright" />
          <TileLayer
            attribution='&copy; <a href="https://carto.com/attributions">CARTO</a> · <a href="https://www.openstreetmap.org/copyright">OSM</a>'
            url="https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png"
            subdomains={['a', 'b', 'c', 'd']}
          />
          {geo.map((listing) => {
            const bin = binFor(listing.price_per_m2);
            // Larger surface → larger circle (capped).
            const radius = Math.min(
              16,
              6 + Math.sqrt(Math.max(0, listing.size)) / 2,
            );
            return (
              <CircleMarker
                key={listing.id}
                center={[listing.latitude!, listing.longitude!]}
                radius={radius}
                pathOptions={{
                  color: bin.color,
                  weight: 1.5,
                  fillColor: bin.color,
                  fillOpacity: 0.55,
                }}
              >
                <Tooltip direction="top" offset={[0, -8]} opacity={1}>
                  <div className="mono" style={{ fontSize: 11 }}>
                    {listing.location} · {formatUsd(listing.price_per_m2 ?? 0)}/m²
                  </div>
                </Tooltip>
                <Popup>
                  <div style={{ minWidth: 220 }}>
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
                      {listing.location}
                    </div>
                    <div
                      className="mono"
                      style={{ fontSize: 18, fontWeight: 700, color: bin.color }}
                    >
                      {formatUsd(listing.price_per_m2 ?? 0)}{' '}
                      <span style={{ fontSize: 11, color: '#8C95AD' }}>/m²</span>
                    </div>
                    <div
                      style={{
                        marginTop: 8,
                        paddingTop: 8,
                        borderTop: '1px dashed #E1E4EC',
                        fontSize: 12,
                        display: 'grid',
                        gridTemplateColumns: '1fr 1fr',
                        gap: 6,
                      }}
                    >
                      <div>
                        <div style={{ color: '#8C95AD', fontSize: 10 }}>Price</div>
                        <div className="mono">
                          {formatUsd(listing.price_usd ?? 0)}
                        </div>
                      </div>
                      <div>
                        <div style={{ color: '#8C95AD', fontSize: 10 }}>Surface</div>
                        <div className="mono">{formatNumber(listing.size, 0)} m²</div>
                      </div>
                    </div>
                  </div>
                </Popup>
              </CircleMarker>
            );
          })}
        </MapContainer>

        {/* Floating legend */}
        <div
          style={{
            position: 'absolute',
            left: 12,
            bottom: 12,
            zIndex: 401,
            background: 'rgba(255,255,255,0.96)',
            backdropFilter: 'blur(4px)',
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
            Price per m² (USD)
          </div>
          {PRICE_BINS.map((b) => (
            <div
              key={b.label}
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
                  borderRadius: '50%',
                  background: b.color,
                  border: '1.5px solid rgba(255,255,255,0.7)',
                }}
              />
              <span className="mono" style={{ color: 'var(--text-2)' }}>
                {b.label}
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
            Circle size ∝ surface (m²)
          </div>
        </div>
      </div>
    </div>
  );
};

export default PropertyMap;
