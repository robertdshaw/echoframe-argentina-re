interface Props {
  height?: number;
  width?: string | number;
  radius?: number;
  style?: React.CSSProperties;
}

export const Skeleton = ({ height = 12, width = '100%', radius = 4, style }: Props) => (
  <div
    className="skel"
    style={{
      height,
      width,
      borderRadius: radius,
      ...style,
    }}
  />
);

export const SkeletonCard = ({ height = 200 }: { height?: number }) => (
  <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
    <div style={{ padding: 'var(--s-4) var(--s-6)' }}>
      <Skeleton height={10} width={120} />
      <div style={{ height: 6 }} />
      <Skeleton height={22} width="60%" />
    </div>
    <div style={{ padding: '0 var(--s-6) var(--s-6)' }}>
      <Skeleton height={height} radius={6} />
    </div>
  </div>
);

export const SkeletonHero = () => (
  <div
    style={{
      background: 'linear-gradient(135deg, var(--navy-900) 0%, var(--navy-700) 100%)',
      borderRadius: 'var(--r-lg)',
      padding: 28,
      marginBottom: 16,
    }}
  >
    <Skeleton height={10} width={220} style={{ background: 'rgba(255,255,255,0.08)' }} />
    <div style={{ height: 16 }} />
    <Skeleton height={50} width="40%" style={{ background: 'rgba(255,255,255,0.12)' }} />
    <div style={{ height: 24 }} />
    <Skeleton height={36} width="100%" style={{ background: 'rgba(255,255,255,0.06)' }} />
  </div>
);

export default Skeleton;
