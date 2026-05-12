import { useMemo } from 'react';
import {
  MapContainer,
  TileLayer,
  CircleMarker,
  Tooltip,
  Popup,
  ZoomControl,
} from 'react-leaflet';
import 'leaflet/dist/leaflet.css';
import { useListings } from '../../hooks/useListings';
import { formatNumber, formatUsd } from '../../utils/formatters';

// Pampas-region center; gives a useful default view of the major
// agricultural belt.
const PAMPAS_CENTER: [number, number] = [-34.6, -60.5];

// Price-per-ha bins anchored to real Argentine ag zones (USD).
const PRICE_BINS: Array<{ max: number; color: string; label: string }> = [
  { max: 3000, color: '#A1887F', label: '< $3k' },
  { max: 8000, color: '#FBC02D', label: '$3k – $8k' },
  { max: 14000, color: '#FB8C00', label: '$8k – $14k' },
  { max: 22000, color: '#C62828', label: '$14k – $22k' },
  { max: Infinity, color: '#6A1B9A', label: '> $22k' },
];

const ZONE_TINT: Record<string, string> = {
  core_pampa: '#2E7D32',
  santa_fe: '#558B2F',
  frontier: '#FB8C00',
  periurban: '#6A1B9A',
};

const binFor = (price?: number | null) =>
  price === null || price === undefined
    ? { max: 0, color: '#8C95AD', label: 'Unknown' }
    : PRICE_BINS.find((b) => price < b.max) ?? PRICE_BINS[PRICE_BINS.length - 1];

interface Props {
  zone?: string;
}

const CamposMap = ({ zone }: Props) => {
  const { listings, loading, error } = useListings('campos', zone, 200);

  const geo = useMemo(
    () =>
      listings.filter(
        (l) => l.latitude !== null && l.longitude !== null && l.price_usd_per_ha,
      ),
    [listings],
  );

  const center: [number, number] = useMemo(() => {
    if (!geo.length) return PAMPAS_CENTER;
    const lat = geo.reduce((s, l) => s + (l.latitude ?? 0), 0) / geo.length;
    const lon = geo.reduce((s, l) => s + (l.longitude ?? 0), 0) / geo.length;
    return [lat, lon];
  }, [geo]);

  // Per-zone aggregates for the side ribbon.
  const byZone = useMemo(() => {
    const buckets: Record<string, number[]> = {};
    for (const l of geo) {
      const z = (l.location || 'unknown').toLowerCase().replace(/ /g, '_');
      const p = l.price_usd_per_ha ?? 0;
      if (p > 0) (buckets[z] ??= []).push(p);
    }
    return Object.entries(buckets)
      .map(([z, prices]) => ({
        zone: z,
        n: prices.length,
        median: prices.sort((a, b) => a - b)[Math.floor(prices.length / 2)] ?? 0,
      }))
      .sort((a, b) => b.median - a.median);
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
            Agricultural parcels · {zone || 'all zones'}
          </div>
        </div>
        {byZone.length > 0 && (
          <div style={{ display: 'flex', gap: 18, fontSize: 12 }}>
            {byZone.slice(0, 4).map((z) => (
              <div key={z.zone}>
                <div
                  className="eyebrow"
                  style={{ fontSize: 9, color: ZONE_TINT[z.zone] }}
                >
                  {z.zone.replace(/_/g, ' ')}
                </div>
                <div className="mono" style={{ fontWeight: 600 }}>
                  {formatUsd(z.median)} /ha
                </div>
                <div style={{ fontSize: 10, color: 'var(--text-3)' }}>
                  n = {z.n}
                </div>
              </div>
            ))}
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
            Could not load campos: {error}
          </div>
        )}
        <MapContainer
          center={center}
          zoom={6}
          style={{ height: 480, width: '100%' }}
          zoomControl={false}
          scrollWheelZoom={false}
        >
          <ZoomControl position="topright" />
          <TileLayer
            attribution='&copy; <a href="https://carto.com/attributions">CARTO</a> · <a href="https://www.openstreetmap.org/copyright">OSM</a>'
            url="https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png"
            subdomains={['a', 'b', 'c', 'd']}
          />
          {geo.map((listing) => {
            const bin = binFor(listing.price_usd_per_ha);
            // Circle radius ∝ √(hectares).
            const ha = listing.size || 0;
            const radius = Math.max(6, Math.min(22, Math.sqrt(ha) / 2.4));
            return (
              <CircleMarker
                key={listing.id}
                center={[listing.latitude!, listing.longitude!]}
                radius={radius}
                pathOptions={{
                  color: bin.color,
                  weight: 1.5,
                  fillColor: bin.color,
                  fillOpacity: 0.6,
                }}
              >
                <Tooltip direction="top" offset={[0, -8]}>
                  <div className="mono" style={{ fontSize: 11 }}>
                    {listing.partido ?? listing.location} · {formatUsd(listing.price_usd_per_ha ?? 0)}/ha
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
                      {listing.partido ?? listing.location}{' '}
                      {listing.province && `· ${listing.province}`}
                    </div>
                    <div
                      className="mono"
                      style={{ fontSize: 18, fontWeight: 700, color: bin.color }}
                    >
                      {formatUsd(listing.price_usd_per_ha ?? 0)}{' '}
                      <span style={{ fontSize: 11, color: '#8C95AD' }}>/ha</span>
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
                        <div style={{ color: '#8C95AD', fontSize: 10 }}>Total</div>
                        <div className="mono">
                          {formatUsd(listing.price_usd ?? 0)}
                        </div>
                      </div>
                      <div>
                        <div style={{ color: '#8C95AD', fontSize: 10 }}>Size</div>
                        <div className="mono">{formatNumber(listing.size, 0)} ha</div>
                      </div>
                      <div>
                        <div style={{ color: '#8C95AD', fontSize: 10 }}>Zone</div>
                        <div className="mono">{listing.location.replace(/_/g, ' ')}</div>
                      </div>
                      <div>
                        <div style={{ color: '#8C95AD', fontSize: 10 }}>Type</div>
                        <div className="mono">{listing.property_type}</div>
                      </div>
                    </div>
                  </div>
                </Popup>
              </CircleMarker>
            );
          })}
        </MapContainer>

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
            Price per hectare (USD)
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
            Circle size ∝ √hectares
          </div>
        </div>
      </div>
    </div>
  );
};

export default CamposMap;
