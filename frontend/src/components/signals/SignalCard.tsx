import type { ProcessedSignal } from '../../types';
import { formatDateEs } from '../../utils/formatters';
import ImpactBadge from './ImpactBadge';

interface Props {
  signal: ProcessedSignal;
}

const SignalCard = ({ signal }: Props) => {
  const dir = signal.signal_classification.impact_direction;
  const className =
    dir === 'positive'
      ? 'signal-card signal-positive'
      : dir === 'negative'
        ? 'signal-card signal-negative'
        : 'signal-card';

  const segments = signal.signal_classification.affected_segments;

  return (
    <div className={className} style={{ background: '#FFFFFF' }}>
      <div className="signal-meta">
        <strong>{signal.source}</strong> · {formatDateEs(signal.published_at)}
      </div>
      <div className="signal-title">{signal.title}</div>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
        <ImpactBadge
          direction={dir}
          magnitude={signal.signal_classification.impact_magnitude}
        />
        <span style={{ fontSize: 11, color: '#666' }}>
          {signal.signal_classification.signal_type.replace(/_/g, ' ')}
        </span>
        <span style={{ marginLeft: 'auto', fontSize: 11, color: '#666' }}>
          {segments.map((s) => (s === 'departamentos' ? '🏢' : '🌾')).join(' ')}
        </span>
      </div>
      {signal.provenance && (
        <div
          style={{
            marginTop: 6,
            paddingTop: 6,
            borderTop: '1px dashed var(--border-1)',
            fontSize: 10.5,
            color: 'var(--text-3)',
            letterSpacing: 0.02,
          }}
        >
          → feeds {signal.provenance}
        </div>
      )}
    </div>
  );
};

export default SignalCard;
