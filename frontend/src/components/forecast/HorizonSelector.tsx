interface Props {
  value: 1 | 2 | 3;
  onChange: (year: 1 | 2 | 3) => void;
}

const HorizonSelector = ({ value, onChange }: Props) => (
  <div
    style={{
      display: 'inline-flex',
      border: '1px solid #E5E7EB',
      borderRadius: 6,
      overflow: 'hidden',
    }}
  >
    {([1, 2, 3] as const).map((year) => (
      <button
        key={year}
        onClick={() => onChange(year)}
        style={{
          padding: '8px 16px',
          border: 'none',
          cursor: 'pointer',
          background: value === year ? '#1B2A4A' : '#FFFFFF',
          color: value === year ? '#FFFFFF' : '#1B2A4A',
          fontWeight: 600,
          fontSize: 13,
        }}
      >
        Year {year}
      </button>
    ))}
  </div>
);

export default HorizonSelector;
