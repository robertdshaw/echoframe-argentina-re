interface BaseCase {
  value: number;
  source: string;
}

interface Props {
  label: string;
  value: number;
  min: number;
  max: number;
  step: number;
  unit?: string;
  onChange: (value: number) => void;
  baseCase?: BaseCase;
}

const fmt = (n: number, step: number, unit?: string): string =>
  `${n.toFixed(step < 1 ? 1 : 0)}${unit ?? ''}`;

const ScenarioSlider = ({
  label,
  value,
  min,
  max,
  step,
  unit,
  onChange,
  baseCase,
}: Props) => {
  // Compute the tick position as a percentage along the rail. We use
  // calc() with a tiny inset so it visually centers on the input thumb.
  const tickPct =
    baseCase &&
    baseCase.value >= min &&
    baseCase.value <= max &&
    max > min
      ? ((baseCase.value - min) / (max - min)) * 100
      : null;
  const deviates =
    baseCase !== undefined && Math.abs(value - baseCase.value) > step / 2;

  return (
    <div style={{ marginBottom: 18 }}>
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'baseline',
          marginBottom: 6,
        }}
      >
        <label style={{ fontSize: 13, color: '#444', fontWeight: 600 }}>
          {label}
        </label>
        <span
          className="mono"
          style={{
            fontSize: 13,
            color: deviates ? '#E85D26' : '#1B2A4A',
            fontWeight: deviates ? 600 : 400,
          }}
        >
          {fmt(value, step, unit)}
        </span>
      </div>
      <div style={{ position: 'relative' }}>
        <input
          type="range"
          min={min}
          max={max}
          step={step}
          value={value}
          onChange={(e) => onChange(Number(e.target.value))}
          style={{ width: '100%', position: 'relative', zIndex: 1 }}
        />
        {tickPct !== null && (
          <div
            title={`Base case: ${fmt(baseCase!.value, step, unit)} (${baseCase!.source})`}
            style={{
              position: 'absolute',
              left: `calc(${tickPct}% - 1px)`,
              top: '50%',
              transform: 'translateY(-50%)',
              width: 2,
              height: 14,
              background: '#4A3B8F',
              pointerEvents: 'none',
              zIndex: 0,
            }}
          />
        )}
      </div>
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          fontSize: 11,
          color: '#999',
          marginTop: 2,
        }}
      >
        <span>{min}</span>
        {baseCase && (
          <span style={{ color: '#4A3B8F' }}>
            <span style={{ marginRight: 4 }}>▲</span>
            Base: <span className="mono">{fmt(baseCase.value, step, unit)}</span>{' '}
            <span style={{ color: '#999' }}>({baseCase.source})</span>
          </span>
        )}
        <span>{max}</span>
      </div>
    </div>
  );
};

export default ScenarioSlider;
