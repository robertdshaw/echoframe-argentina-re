import { useMacroIndicators } from '../../hooks/useMarketData';
import { formatNumber, formatPct } from '../../utils/formatters';
import LoadingSpinner from '../common/LoadingSpinner';
import ErrorMessage from '../common/ErrorMessage';

const Metric = ({
  label,
  value,
  sub,
}: {
  label: string;
  value: string;
  sub?: string;
}) => (
  <div className="metric-card">
    <div className="metric-value mono">{value}</div>
    <div className="metric-label">{label}</div>
    {sub && (
      <div style={{ fontSize: 11, color: '#999', marginTop: 4 }}>{sub}</div>
    )}
  </div>
);

const MacroPanel = () => {
  const { data, loading, error } = useMacroIndicators();
  if (loading) return <LoadingSpinner label="Loading macro data…" />;
  if (error) return <ErrorMessage message={error} />;
  if (!data) return null;

  const { bcra, rem } = data;

  return (
    <div>
      <div className="grid grid-4">
        <Metric
          label="USD/ARS (Mayorista)"
          value={bcra.exchange_rate ? formatNumber(bcra.exchange_rate.value, 2) : '—'}
          sub={bcra.exchange_rate?.date}
        />
        <Metric
          label="Tasa de Referencia"
          value={
            bcra.reference_rate !== null && bcra.reference_rate !== undefined
              ? formatPct(bcra.reference_rate.value, 1).replace('+', '')
              : '—'
          }
          sub={bcra.reference_rate?.date}
        />
        <Metric
          label="Inflación (mensual)"
          value={
            bcra.inflation
              ? formatPct(bcra.inflation.value, 1).replace('+', '')
              : '—'
          }
          sub={bcra.inflation?.date}
        />
        <Metric
          label="Reservas BCRA"
          value={
            bcra.reserves
              ? `USD ${formatNumber(bcra.reserves.value / 1000, 1)}B`
              : '—'
          }
          sub={bcra.reserves?.date}
        />
      </div>
      {rem && (
        <div
          style={{
            marginTop: 16,
            padding: 16,
            background: '#F8F9FB',
            borderRadius: 8,
            fontSize: 13,
            color: '#444',
          }}
        >
          <strong style={{ color: '#1B2A4A' }}>REM consensus (economists):</strong>{' '}
          {rem.inflation_forecast && (
            <>
              inflación {rem.inflation_forecast.period}:{' '}
              <span className="mono">
                {rem.inflation_forecast.median.toFixed(1)}%
              </span>{' '}
              ·{' '}
            </>
          )}
          {rem.exchange_rate_forecast && (
            <>
              USD/ARS {rem.exchange_rate_forecast.period}:{' '}
              <span className="mono">
                {formatNumber(rem.exchange_rate_forecast.median, 0)}
              </span>{' '}
              ·{' '}
            </>
          )}
          {rem.gdp_forecast && (
            <>
              GDP {rem.gdp_forecast.period}:{' '}
              <span className="mono">{rem.gdp_forecast.median.toFixed(1)}%</span>
            </>
          )}
        </div>
      )}
    </div>
  );
};

export default MacroPanel;
