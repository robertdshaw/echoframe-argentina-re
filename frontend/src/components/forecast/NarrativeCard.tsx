import { useNarrative } from '../../hooks/useNarrative';
import type { Segment } from '../../types';

interface Props {
  segment: Segment;
  location?: string;
}

const Skel = ({
  w,
  h = 12,
}: {
  w: string | number;
  h?: number;
}) => (
  <div
    className="skel"
    style={{
      width: w,
      height: h,
      borderRadius: 4,
    }}
  />
);

const NarrativeCard = ({ segment, location }: Props) => {
  const { data, loading, error } = useNarrative(segment, location);

  // Highlight the final "Bottom line: …" sentence with extra emphasis.
  const renderNarrative = (text: string) => {
    const idx = text.lastIndexOf('Bottom line:');
    if (idx === -1) {
      return text.split('\n\n').map((p, i) => (
        <p key={i} style={{ marginBottom: 12, lineHeight: 1.6 }}>
          {p}
        </p>
      ));
    }
    const main = text.slice(0, idx).trim();
    const tail = text.slice(idx).trim();
    return (
      <>
        {main.split('\n\n').map((p, i) => (
          <p key={i} style={{ marginBottom: 12, lineHeight: 1.6 }}>
            {p}
          </p>
        ))}
        <div
          style={{
            marginTop: 14,
            padding: '14px 16px',
            background:
              'linear-gradient(135deg, rgba(232,93,38,0.08), rgba(74,59,143,0.08))',
            borderLeft: '3px solid var(--orange-500)',
            borderRadius: 6,
            fontWeight: 600,
            fontSize: 14,
            color: 'var(--text-1)',
            lineHeight: 1.55,
          }}
        >
          {tail}
        </div>
      </>
    );
  };

  return (
    <div
      className="card fade-in-up"
      style={{
        position: 'relative',
        overflow: 'hidden',
      }}
    >
      <div
        style={{
          position: 'absolute',
          top: 0,
          left: 0,
          right: 0,
          height: 3,
          background:
            'linear-gradient(90deg, #4A3B8F 0%, #E85D26 50%, #4A3B8F 100%)',
        }}
      />
      <div
        style={{
          display: 'flex',
          alignItems: 'baseline',
          justifyContent: 'space-between',
          marginBottom: 14,
          marginTop: 6,
          gap: 12,
          flexWrap: 'wrap',
        }}
      >
        <div>
          <div className="eyebrow" style={{ color: 'var(--purple-600)' }}>
            Executive briefing · LLM
          </div>
          <h3 className="title-2" style={{ marginTop: 2 }}>
            Bottom line
          </h3>
        </div>
        <div style={{ textAlign: 'right' }}>
          <span
            className="badge"
            style={{
              background: 'var(--purple-50)',
              color: 'var(--purple-600)',
            }}
          >
            Claude Sonnet 4.6
          </span>
          {data?.generated_at && (
            <div
              className="caption"
              style={{ marginTop: 4 }}
            >
              {new Date(data.generated_at).toLocaleTimeString('en-GB', {
                hour: '2-digit',
                minute: '2-digit',
              })}
              {' · cached for 20 min'}
            </div>
          )}
        </div>
      </div>

      {loading && (
        <div>
          <Skel w="92%" h={14} />
          <div style={{ height: 8 }} />
          <Skel w="98%" h={14} />
          <div style={{ height: 8 }} />
          <Skel w="78%" h={14} />
          <div style={{ height: 16 }} />
          <Skel w="86%" h={14} />
          <div style={{ height: 8 }} />
          <Skel w="94%" h={14} />
          <div style={{ height: 8 }} />
          <Skel w="40%" h={14} />
          <div style={{ height: 16 }} />
          <Skel w="100%" h={50} />
          <div
            className="caption"
            style={{ marginTop: 12, color: 'var(--text-3)' }}
          >
            Generating interpretation…
          </div>
        </div>
      )}

      {!loading && data?.status === 'ok' && data.narrative && (
        <div
          className="body"
          style={{ color: 'var(--text-1)', fontSize: 15 }}
        >
          {renderNarrative(data.narrative)}
        </div>
      )}

      {!loading && data?.status === 'unavailable' && (
        <div
          style={{
            padding: '14px 16px',
            background: 'var(--surface-sunken)',
            borderRadius: 6,
            fontSize: 13,
            color: 'var(--text-2)',
            lineHeight: 1.55,
          }}
        >
          <strong style={{ color: 'var(--text-1)' }}>
            Narrative unavailable.
          </strong>{' '}
          {data.reason ?? 'Configure ANTHROPIC_API_KEY in backend/.env to enable Claude-generated interpretations.'}
        </div>
      )}

      {!loading && error && (
        <div className="error">
          <strong>Could not generate narrative.</strong> {error}
        </div>
      )}
    </div>
  );
};

export default NarrativeCard;
