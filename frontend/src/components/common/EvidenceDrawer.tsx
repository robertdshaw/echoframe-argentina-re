import { ReactNode, useState } from 'react';

interface Props {
  title: string;
  subtitle?: string;
  defaultOpen?: boolean;
  children: ReactNode;
}

/**
 * Collapsible container for analytical evidence — model trajectories,
 * outcome distributions, calibration tables, HMM diagnostics — that
 * supports the headline call but isn't itself the call. Closed by
 * default so the narrative panels stay above the fold; opens to reveal
 * the full model machinery for analysts or skeptical clients.
 */
const EvidenceDrawer = ({ title, subtitle, defaultOpen = false, children }: Props) => {
  const [open, setOpen] = useState(defaultOpen);

  return (
    <div
      style={{
        border: '1px solid var(--border-2)',
        borderRadius: 10,
        background: 'var(--surface-sunken)',
        overflow: 'hidden',
      }}
    >
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        aria-expanded={open}
        style={{
          display: 'flex',
          width: '100%',
          alignItems: 'center',
          gap: 12,
          background: 'transparent',
          border: 'none',
          padding: 'var(--s-4) var(--s-6)',
          cursor: 'pointer',
          textAlign: 'left',
        }}
      >
        <div
          aria-hidden
          style={{
            display: 'inline-block',
            transform: open ? 'rotate(90deg)' : 'rotate(0deg)',
            transition: 'transform 180ms ease',
            color: 'var(--text-2)',
            fontSize: 12,
            width: 12,
          }}
        >
          ▶
        </div>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div
            style={{
              fontSize: 10,
              fontWeight: 700,
              letterSpacing: 0.14,
              textTransform: 'uppercase',
              color: 'var(--text-3)',
            }}
          >
            Evidence
          </div>
          <div
            style={{
              fontSize: 16,
              fontWeight: 600,
              color: 'var(--text-1)',
              marginTop: 2,
            }}
          >
            {title}
          </div>
          {subtitle && (
            <div
              style={{
                fontSize: 12,
                color: 'var(--text-3)',
                marginTop: 2,
                lineHeight: 1.5,
              }}
            >
              {subtitle}
            </div>
          )}
        </div>
        <div
          style={{
            fontSize: 11,
            fontWeight: 600,
            color: 'var(--text-2)',
            letterSpacing: 0.05,
            padding: '4px 10px',
            border: '1px solid var(--border-1)',
            borderRadius: 999,
            background: '#FFFFFF',
            whiteSpace: 'nowrap',
          }}
        >
          {open ? 'Hide' : 'Show'}
        </div>
      </button>
      {open && (
        <div
          style={{
            background: '#FFFFFF',
            borderTop: '1px solid var(--border-2)',
            padding: 'var(--s-5) var(--s-6)',
            display: 'flex',
            flexDirection: 'column',
            gap: 24,
          }}
        >
          {children}
        </div>
      )}
    </div>
  );
};

export default EvidenceDrawer;
