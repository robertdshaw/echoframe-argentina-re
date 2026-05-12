/**
 * Skeleton variant of ExecutiveCard. Pixel-matches the real card's
 * structure so the page doesn't reflow on data arrival — only the
 * shimmer blocks swap for real content.
 */
const Skel = ({
  w,
  h,
  r = 4,
  style,
}: {
  w: number | string;
  h: number;
  r?: number;
  style?: React.CSSProperties;
}) => (
  <div
    className="skel"
    style={{
      width: w,
      height: h,
      borderRadius: r,
      background:
        'linear-gradient(90deg, rgba(255,255,255,0.04) 0%, rgba(255,255,255,0.12) 50%, rgba(255,255,255,0.04) 100%)',
      backgroundSize: '200% 100%',
      animation: 'shimmer 1.6s cubic-bezier(0.65,0,0.35,1) infinite',
      ...style,
    }}
  />
);

const ExecutiveCardSkeleton = () => (
  <div
    style={{
      position: 'relative',
      background:
        'radial-gradient(ellipse at top right, #1F2D52 0%, #0F1B3D 45%, #050B1F 100%)',
      color: '#FFFFFF',
      borderRadius: 14,
      overflow: 'hidden',
      marginBottom: 16,
      boxShadow:
        '0 18px 40px rgba(15,27,61,0.18), 0 4px 12px rgba(15,27,61,0.12)',
    }}
  >
    <div
      style={{
        position: 'absolute',
        inset: 0,
        backgroundImage:
          'radial-gradient(circle at 1px 1px, rgba(255,255,255,0.05) 1px, transparent 0)',
        backgroundSize: '24px 24px',
        opacity: 0.6,
        pointerEvents: 'none',
      }}
    />
    <div
      style={{
        position: 'absolute',
        right: -120,
        top: -120,
        width: 360,
        height: 360,
        borderRadius: '50%',
        background:
          'radial-gradient(circle, rgba(232,93,38,0.22) 0%, transparent 60%)',
        pointerEvents: 'none',
      }}
    />
    <div
      style={{
        position: 'relative',
        padding: '32px 36px 28px',
        display: 'grid',
        gridTemplateColumns: 'minmax(0, 1.4fr) minmax(0, 1fr)',
        gap: 36,
      }}
    >
      {/* LEFT */}
      <div style={{ minWidth: 0 }}>
        <Skel w={140} h={22} r={999} style={{ marginBottom: 18 }} />
        <Skel w={220} h={11} style={{ marginBottom: 14 }} />
        <Skel w="60%" h={80} r={6} style={{ marginBottom: 14 }} />
        <Skel w="80%" h={14} style={{ marginBottom: 24 }} />
        <Skel w="100%" h={6} r={999} style={{ marginBottom: 24 }} />
        <div style={{ display: 'flex', gap: 28 }}>
          <div>
            <Skel w={80} h={10} style={{ marginBottom: 6 }} />
            <Skel w={100} h={18} />
          </div>
          <div>
            <Skel w={80} h={10} style={{ marginBottom: 6 }} />
            <Skel w={100} h={18} />
          </div>
          <div>
            <Skel w={80} h={10} style={{ marginBottom: 6 }} />
            <Skel w={100} h={18} />
          </div>
        </div>
      </div>
      {/* RIGHT */}
      <div
        style={{
          background: 'rgba(255,255,255,0.04)',
          border: '1px solid rgba(255,255,255,0.08)',
          borderRadius: 12,
          padding: 22,
          display: 'flex',
          flexDirection: 'column',
          gap: 18,
        }}
      >
        <div>
          <Skel w={120} h={10} style={{ marginBottom: 6 }} />
          <Skel w="80%" h={12} />
        </div>
        {[1, 2, 3].map((i) => (
          <div key={i}>
            <div
              style={{
                display: 'flex',
                justifyContent: 'space-between',
                marginBottom: 6,
              }}
            >
              <Skel w={60} h={11} />
              <Skel w={60} h={20} />
            </div>
            <Skel w="100%" h={14} r={4} />
            <div
              style={{ display: 'flex', justifyContent: 'space-between', marginTop: 4 }}
            >
              <Skel w={40} h={10} />
              <Skel w={50} h={10} />
              <Skel w={40} h={10} />
            </div>
          </div>
        ))}
      </div>
    </div>
  </div>
);

export default ExecutiveCardSkeleton;
