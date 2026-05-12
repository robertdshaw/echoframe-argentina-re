import { useEntryQuality } from '../../hooks/useEntryQuality';
import { formatPct } from '../../utils/formatters';
import type { TimingTriggerState } from '../../types';

const GAUGE_GOOD = '#1FA66A';
const GAUGE_MID = '#F59E0B';
const GAUGE_BAD = '#C2410C';

const gaugeColor = (score: number): string => {
  if (score >= 7) return GAUGE_GOOD;
  if (score >= 4) return GAUGE_MID;
  return GAUGE_BAD;
};

const TriggerRow = ({ t }: { t: TimingTriggerState }) => {
  const active = t.status === 'active';
  return (
    <div
      style={{
        display: 'grid',
        gridTemplateColumns: '24px 1fr auto',
        gap: 10,
        alignItems: 'flex-start',
        padding: '8px 0',
        borderBottom: '1px dashed var(--border-1)',
      }}
    >
      <div
        aria-hidden
        style={{
          fontSize: 16,
          color: active ? GAUGE_GOOD : 'var(--text-3)',
          marginTop: 1,
        }}
      >
        {active ? '✓' : '○'}
      </div>
      <div style={{ minWidth: 0 }}>
        <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-1)' }}>
          {t.name}
        </div>
        <div style={{ fontSize: 11.5, color: 'var(--text-2)', marginTop: 2 }}>
          {t.observed}{' '}
          <span style={{ color: 'var(--text-3)' }}>· threshold: {t.threshold}</span>
        </div>
        <div style={{ fontSize: 10.5, color: 'var(--text-3)', marginTop: 1 }}>
          Source: {t.source}
          {t.note ? ` · ${t.note}` : ''}
        </div>
      </div>
      <div
        className="mono"
        style={{
          fontSize: 12,
          color: active ? GAUGE_GOOD : 'var(--text-3)',
          fontWeight: 600,
          textAlign: 'right',
          minWidth: 50,
        }}
      >
        {(t.score * 100).toFixed(0)}/100
      </div>
    </div>
  );
};

const TimingTriggerPanel = () => {
  const { data, loading, error } = useEntryQuality();

  if (loading) {
    return (
      <div className="card" style={{ padding: 24 }}>
        <div className="eyebrow">When to act</div>
        <div style={{ color: 'var(--text-3)', marginTop: 8, fontSize: 13 }}>
          Computing entry-quality reading…
        </div>
      </div>
    );
  }
  if (error || !data) {
    return (
      <div className="card">
        <div className="eyebrow">When to act</div>
        <div className="error" style={{ marginTop: 8 }}>
          Entry-quality unavailable: {error ?? 'unknown error'}
        </div>
      </div>
    );
  }

  const color = gaugeColor(data.score_out_of_10);
  const fillPct = Math.min(100, (data.score_out_of_10 / 10) * 100);
  const verdict =
    data.score_out_of_10 >= 7
      ? 'Buy window'
      : data.score_out_of_10 >= 4
        ? 'Mixed signals'
        : 'Wait';

  return (
    <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
      <div
        style={{
          padding: 'var(--s-4) var(--s-6)',
          borderBottom: '1px solid var(--border-2)',
        }}
      >
        <div className="eyebrow">When to act</div>
        <h3 className="title-3" style={{ margin: '4px 0 0 0' }}>
          Entry-quality reading
        </h3>
      </div>

      <div
        style={{
          padding: 'var(--s-5) var(--s-6)',
          display: 'grid',
          gridTemplateColumns: 'minmax(0, 1fr) minmax(0, 1.4fr)',
          gap: 24,
        }}
      >
        {/* Left: gauge + verdict */}
        <div>
          <div
            style={{
              display: 'flex',
              alignItems: 'baseline',
              gap: 8,
              marginBottom: 10,
            }}
          >
            <div
              className="mono"
              style={{ fontSize: 56, fontWeight: 700, color, lineHeight: 1 }}
            >
              {data.score_out_of_10.toFixed(1)}
            </div>
            <div
              style={{
                fontSize: 18,
                fontWeight: 600,
                color: 'var(--text-2)',
                marginLeft: 2,
              }}
            >
              / 10
            </div>
          </div>
          <div
            style={{
              fontSize: 13,
              fontWeight: 600,
              color,
              letterSpacing: 0.1,
              textTransform: 'uppercase',
            }}
          >
            {verdict}
          </div>
          <div
            style={{
              height: 12,
              background: 'var(--surface-sunken)',
              borderRadius: 6,
              overflow: 'hidden',
              marginTop: 12,
            }}
          >
            <div
              style={{
                height: '100%',
                width: `${fillPct}%`,
                background: color,
                transition: 'width 0.4s ease',
              }}
            />
          </div>
          <div
            style={{
              marginTop: 14,
              padding: 12,
              background: 'var(--surface-sunken)',
              borderRadius: 6,
              fontSize: 12,
              color: 'var(--text-2)',
              lineHeight: 1.5,
            }}
          >
            <strong style={{ color: 'var(--text-1)' }}>
              Historical analogy.
            </strong>{' '}
            This configuration was last observed in{' '}
            <span className="mono">{data.historical_analogy_period}</span>;
            realised 12-month return:{' '}
            <span className="mono" style={{ color, fontWeight: 600 }}>
              {formatPct(data.historical_analogy_realised_pct, 1)}
            </span>
            . Anchor period reads from the calibration data backtest, not a
            generative model.
          </div>
        </div>

        {/* Right: trigger breakdown */}
        <div>
          <div
            style={{
              fontSize: 10,
              fontWeight: 700,
              letterSpacing: 0.14,
              textTransform: 'uppercase',
              color: 'var(--text-3)',
              marginBottom: 4,
            }}
          >
            Trigger breakdown
          </div>
          <div>
            {data.triggers.map((t) => (
              <TriggerRow key={t.key} t={t} />
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};

export default TimingTriggerPanel;
