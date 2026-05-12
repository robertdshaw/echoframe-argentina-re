export type PageKey = 'departamentos' | 'campos' | 'signals' | 'scenarios';

interface NavItem {
  key: PageKey;
  label: string;
  sub: string;
  icon: JSX.Element;
}

const ICON_PROPS = {
  width: 18,
  height: 18,
  viewBox: '0 0 24 24',
  fill: 'none',
  stroke: 'currentColor',
  strokeWidth: 1.75,
  strokeLinecap: 'round' as const,
  strokeLinejoin: 'round' as const,
};

const ITEMS: NavItem[] = [
  {
    key: 'departamentos',
    label: 'Departamentos',
    sub: 'Buenos Aires apartments',
    icon: (
      <svg {...ICON_PROPS}>
        <rect x="4" y="3" width="16" height="18" rx="1" />
        <line x1="9" y1="7" x2="9" y2="7.01" />
        <line x1="15" y1="7" x2="15" y2="7.01" />
        <line x1="9" y1="11" x2="9" y2="11.01" />
        <line x1="15" y1="11" x2="15" y2="11.01" />
        <line x1="9" y1="15" x2="9" y2="15.01" />
        <line x1="15" y1="15" x2="15" y2="15.01" />
        <path d="M10 21v-3a2 2 0 014 0v3" />
      </svg>
    ),
  },
  {
    key: 'campos',
    label: 'Campos',
    sub: 'Agricultural land',
    icon: (
      <svg {...ICON_PROPS}>
        <path d="M3 21h18" />
        <path d="M3 21V12l9-7 9 7v9" />
        <path d="M9 21v-6h6v6" />
      </svg>
    ),
  },
  {
    key: 'signals',
    label: 'Signals',
    sub: 'News intelligence',
    icon: (
      <svg {...ICON_PROPS}>
        <path d="M4 4l16 7-7 3-3 7-6-17z" />
      </svg>
    ),
  },
  {
    key: 'scenarios',
    label: 'Scenarios',
    sub: 'What-if explorer',
    icon: (
      <svg {...ICON_PROPS}>
        <circle cx="12" cy="12" r="9" />
        <path d="M12 7v5l3 2" />
      </svg>
    ),
  },
];

interface Props {
  active: PageKey;
  onChange: (page: PageKey) => void;
}

const Sidebar = ({ active, onChange }: Props) => (
  <nav
    style={{
      background: 'var(--surface-card)',
      border: '1px solid var(--border-1)',
      borderRadius: 'var(--r-lg)',
      padding: 'var(--s-2)',
      position: 'sticky',
      top: 88,
      boxShadow: 'var(--shadow-xs)',
    }}
  >
    {ITEMS.map((item) => {
      const isActive = item.key === active;
      return (
        <button
          key={item.key}
          onClick={() => onChange(item.key)}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: 12,
            width: '100%',
            textAlign: 'left',
            padding: '10px 12px',
            marginBottom: 2,
            borderRadius: 6,
            background: isActive ? 'var(--navy-800)' : 'transparent',
            color: isActive ? '#FFFFFF' : 'var(--text-1)',
            transition: 'background var(--d-fast) var(--ease-out), color var(--d-fast) var(--ease-out)',
            position: 'relative',
          }}
          onMouseEnter={(e) => {
            if (!isActive) {
              (e.currentTarget as HTMLButtonElement).style.background = 'var(--surface-sunken)';
            }
          }}
          onMouseLeave={(e) => {
            if (!isActive) {
              (e.currentTarget as HTMLButtonElement).style.background = 'transparent';
            }
          }}
        >
          {isActive && (
            <span
              style={{
                position: 'absolute',
                left: -1,
                top: 6,
                bottom: 6,
                width: 3,
                background: 'var(--orange-500)',
                borderRadius: 999,
              }}
            />
          )}
          <span
            style={{
              display: 'flex',
              color: isActive ? '#FFFFFF' : 'var(--text-2)',
              transition: 'color var(--d-fast) var(--ease-out)',
            }}
          >
            {item.icon}
          </span>
          <span style={{ display: 'flex', flexDirection: 'column', lineHeight: 1.2, gap: 2 }}>
            <span style={{ fontSize: 14, fontWeight: 600, letterSpacing: '-0.01em' }}>{item.label}</span>
            <span
              style={{
                fontSize: 11,
                color: isActive ? 'rgba(255,255,255,0.6)' : 'var(--text-3)',
              }}
            >
              {item.sub}
            </span>
          </span>
        </button>
      );
    })}

    <div
      style={{
        marginTop: 12,
        padding: '10px 12px',
        borderTop: '1px solid var(--border-2)',
        display: 'flex',
        flexDirection: 'column',
        gap: 4,
      }}
    >
      <div
        style={{
          fontSize: 10,
          fontWeight: 600,
          letterSpacing: 0.14,
          textTransform: 'uppercase',
          color: 'var(--text-3)',
        }}
      >
        Data sources
      </div>
      <div style={{ fontSize: 11, color: 'var(--text-2)', display: 'flex', alignItems: 'center', gap: 6 }}>
        <span className="dot dot-green" /> BCRA · live
      </div>
      <div style={{ fontSize: 11, color: 'var(--text-2)', display: 'flex', alignItems: 'center', gap: 6 }}>
        <span className="dot dot-green" /> REM · live
      </div>
      <div style={{ fontSize: 11, color: 'var(--text-2)', display: 'flex', alignItems: 'center', gap: 6 }}>
        <span className="dot dot-green" /> NewsData.io · live
      </div>
      <div style={{ fontSize: 11, color: 'var(--text-2)', display: 'flex', alignItems: 'center', gap: 6 }}>
        <span className="dot dot-green" /> Properati · scraped
      </div>
    </div>
  </nav>
);

export default Sidebar;
