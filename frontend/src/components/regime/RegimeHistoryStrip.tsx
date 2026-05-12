import type { BacktestRecord } from '../../types';

interface Props {
  records: BacktestRecord[];
  currentRegime: 'crisis' | 'recovery' | 'boom';
}

const REGIME_COLOR: Record<string, string> = {
  crisis: '#D93025',
  recovery: '#0F9D58',
  boom: '#B26A00',
};

const REGIME_LABEL: Record<string, string> = {
  crisis: 'Crisis',
  recovery: 'Recovery',
  boom: 'Boom',
};

const RegimeHistoryStrip = ({ records, currentRegime }: Props) => {
  if (!records.length) return null;

  const last = records[records.length - 1];

  return (
    <div className="card card-tight">
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'baseline',
          marginBottom: 10,
        }}
      >
        <div className="card-eyebrow">Regime history</div>
        <div style={{ fontSize: 11, color: '#8C95AD' }}>
          {records.length} quarters · {records[0].anchor_quarter} →{' '}
          {last.anchor_quarter} · current:{' '}
          <span
            className="mono"
            style={{
              color: REGIME_COLOR[currentRegime],
              fontWeight: 600,
            }}
          >
            {REGIME_LABEL[currentRegime]?.toUpperCase()}
          </span>
        </div>
      </div>
      <div
        style={{
          display: 'flex',
          gap: 2,
          height: 36,
          alignItems: 'stretch',
        }}
      >
        {records.map((r) => (
          <div
            key={r.anchor_quarter}
            title={`${r.anchor_quarter} · ${REGIME_LABEL[r.regime_at_anchor]} · realized ${r.realized_pct.toFixed(1)}%`}
            style={{
              flex: 1,
              background: REGIME_COLOR[r.regime_at_anchor] ?? '#5A6582',
              opacity: 0.85,
              borderRadius: 2,
              position: 'relative',
            }}
          />
        ))}
      </div>
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          fontSize: 10,
          color: '#8C95AD',
          marginTop: 6,
          fontVariantNumeric: 'tabular-nums',
        }}
        className="mono"
      >
        <span>{records[0].anchor_quarter}</span>
        <span>{records[Math.floor(records.length / 2)].anchor_quarter}</span>
        <span>{last.anchor_quarter}</span>
      </div>
      <div
        style={{
          display: 'flex',
          gap: 14,
          marginTop: 10,
          fontSize: 11,
          color: '#5A6582',
        }}
      >
        {Object.entries(REGIME_LABEL).map(([key, label]) => (
          <span key={key} style={{ display: 'inline-flex', alignItems: 'center', gap: 4 }}>
            <span
              style={{
                display: 'inline-block',
                width: 10,
                height: 10,
                borderRadius: 2,
                background: REGIME_COLOR[key],
              }}
            />
            {label}
          </span>
        ))}
      </div>
    </div>
  );
};

export default RegimeHistoryStrip;
