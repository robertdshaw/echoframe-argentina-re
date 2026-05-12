/**
 * Designed skeletons that match the real component shapes so the page
 * looks "finished" on first paint — no jarring layout shifts.
 */

import { Skeleton } from './Skeleton';

export const ChartCardSkeleton = ({ title }: { title?: string }) => (
  <div className="card">
    <div
      style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        marginBottom: 16,
      }}
    >
      <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
        <Skeleton width={120} height={32} radius={6} />
        {title && (
          <Skeleton width={180} height={14} style={{ marginLeft: 8 }} />
        )}
      </div>
    </div>
    <div
      style={{
        height: 340,
        background:
          'linear-gradient(180deg, rgba(74,59,143,0.04), rgba(74,59,143,0.01))',
        borderRadius: 8,
        position: 'relative',
        overflow: 'hidden',
      }}
    >
      {/* Faux gridlines so the empty state still reads as a chart */}
      {[0.2, 0.4, 0.6, 0.8].map((p) => (
        <div
          key={p}
          style={{
            position: 'absolute',
            left: 0,
            right: 0,
            top: `${p * 100}%`,
            borderTop: '1px dashed var(--border-2)',
          }}
        />
      ))}
      <Skeleton
        width="86%"
        height={2}
        style={{
          position: 'absolute',
          top: '52%',
          left: '7%',
          borderRadius: 1,
        }}
      />
      <div
        style={{
          position: 'absolute',
          inset: 0,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          color: 'var(--text-3)',
          fontSize: 11,
          letterSpacing: 0.1,
          textTransform: 'uppercase',
          fontWeight: 600,
        }}
      >
        Loading posterior…
      </div>
    </div>
  </div>
);

export const DistributionPanelSkeleton = () => (
  <div className="card">
    <div
      style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'baseline',
        marginBottom: 14,
      }}
    >
      <Skeleton width={140} height={11} />
      <Skeleton width={180} height={28} radius={6} />
    </div>
    <Skeleton width={220} height={11} style={{ marginBottom: 8 }} />
    <Skeleton width={140} height={32} style={{ marginBottom: 16 }} />
    {/* Probability strip */}
    <div
      style={{
        display: 'flex',
        height: 18,
        borderRadius: 3,
        overflow: 'hidden',
        gap: 1,
        marginBottom: 14,
      }}
    >
      {[0.05, 0.1, 0.4, 0.3, 0.15].map((p, i) => (
        <Skeleton
          key={i}
          width={`${p * 100}%`}
          height={18}
          radius={0}
          style={{
            background:
              i < 2
                ? 'linear-gradient(90deg, rgba(217,48,37,0.08), rgba(217,48,37,0.04))'
                : 'linear-gradient(90deg, rgba(15,157,88,0.08), rgba(15,157,88,0.04))',
          }}
        />
      ))}
    </div>
    <Skeleton width="100%" height={1} />
    <div
      style={{
        display: 'flex',
        justifyContent: 'space-between',
        marginTop: 12,
      }}
    >
      <Skeleton width={120} height={11} />
      <Skeleton width={140} height={11} />
    </div>
  </div>
);

export const ForecastNumbersSkeleton = () => (
  <div className="card">
    <Skeleton width={100} height={11} style={{ marginBottom: 6 }} />
    <Skeleton width={160} height={18} style={{ marginBottom: 14 }} />
    <div
      style={{
        border: '1px solid var(--border-2)',
        borderRadius: 6,
        padding: 16,
      }}
    >
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          marginBottom: 12,
        }}
      >
        <Skeleton width={60} height={14} />
        <Skeleton width={80} height={20} />
      </div>
      <Skeleton width="100%" height={11} style={{ marginBottom: 8 }} />
      <Skeleton width="80%" height={11} style={{ marginBottom: 16 }} />
      <Skeleton width="100%" height={1} style={{ marginBottom: 12 }} />
      <div style={{ display: 'flex', justifyContent: 'space-between' }}>
        <Skeleton width={100} height={11} />
        <Skeleton width={100} height={11} />
      </div>
    </div>
  </div>
);

export const MapSkeleton = () => (
  <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
    <div
      style={{
        padding: 'var(--s-4) var(--s-6)',
        borderBottom: '1px solid var(--border-2)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        gap: 12,
      }}
    >
      <div>
        <Skeleton width={80} height={10} style={{ marginBottom: 6 }} />
        <Skeleton width={180} height={18} />
      </div>
      <div style={{ display: 'flex', gap: 18 }}>
        {[1, 2, 3, 4].map((i) => (
          <div key={i}>
            <Skeleton width={60} height={10} style={{ marginBottom: 4 }} />
            <Skeleton width={80} height={14} />
          </div>
        ))}
      </div>
    </div>
    <div
      style={{
        height: 480,
        background:
          'linear-gradient(180deg, #F4F5F9 0%, #EEF0F5 100%)',
        position: 'relative',
        overflow: 'hidden',
      }}
    >
      {/* Faux mesh tiles to suggest a map */}
      <div
        style={{
          position: 'absolute',
          inset: 0,
          backgroundImage:
            'linear-gradient(rgba(15,27,61,0.04) 1px, transparent 1px), linear-gradient(90deg, rgba(15,27,61,0.04) 1px, transparent 1px)',
          backgroundSize: '64px 64px',
        }}
      />
      {/* Floating "markers" */}
      {[
        { x: 22, y: 42, c: '#FBC02D' },
        { x: 36, y: 58, c: '#FB8C00' },
        { x: 48, y: 32, c: '#7CB342' },
        { x: 58, y: 70, c: '#C62828' },
        { x: 70, y: 46, c: '#FBC02D' },
        { x: 80, y: 30, c: '#FB8C00' },
      ].map((m, i) => (
        <div
          key={i}
          className="skel"
          style={{
            position: 'absolute',
            left: `${m.x}%`,
            top: `${m.y}%`,
            width: 14,
            height: 14,
            borderRadius: '50%',
            background: m.c,
            opacity: 0.4,
            border: '1.5px solid rgba(255,255,255,0.7)',
          }}
        />
      ))}
      <div
        style={{
          position: 'absolute',
          inset: 0,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          color: 'var(--text-3)',
          fontSize: 11,
          letterSpacing: 0.1,
          textTransform: 'uppercase',
          fontWeight: 600,
        }}
      >
        Loading geometry…
      </div>
    </div>
  </div>
);

export const ListSkeleton = ({ rows = 4 }: { rows?: number }) => (
  <div className="card">
    {Array.from({ length: rows }).map((_, i) => (
      <div
        key={i}
        style={{
          padding: '12px 0',
          borderTop: i ? '1px solid var(--border-2)' : 'none',
        }}
      >
        <Skeleton width={140} height={10} style={{ marginBottom: 6 }} />
        <Skeleton width="85%" height={14} style={{ marginBottom: 8 }} />
        <div style={{ display: 'flex', gap: 8 }}>
          <Skeleton width={60} height={16} radius={3} />
          <Skeleton width={100} height={16} radius={3} />
        </div>
      </div>
    ))}
  </div>
);
