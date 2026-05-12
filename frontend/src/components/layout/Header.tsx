import { useMacroIndicators } from '../../hooks/useMarketData';
import { formatNumber, formatPct } from '../../utils/formatters';

const Header = () => {
  const { data } = useMacroIndicators();
  const usd = data?.bcra.exchange_rate?.value;
  const refRate = data?.bcra.reference_rate?.value;
  const inflationMonth = data?.bcra.inflation?.value;

  return (
    <header className="header">
      <div className="container">
        <h1>EchoFrame Intelligence</h1>
        <div className="header-subtitle">
          Argentina Real Estate Forecast — Probabilistic Market Analytics
        </div>
        <div
          style={{
            marginTop: 16,
            display: 'flex',
            gap: 24,
            flexWrap: 'wrap',
            fontSize: 14,
            opacity: 0.95,
          }}
          className="mono"
        >
          <span>
            USD/ARS:{' '}
            <strong>{usd ? formatNumber(usd, 2) : '…'}</strong>
          </span>
          <span>
            Tasa Ref.:{' '}
            <strong>
              {refRate !== undefined ? formatPct(refRate, 1).replace('+', '') : '…'}
            </strong>
          </span>
          <span>
            IPC mensual:{' '}
            <strong>
              {inflationMonth !== undefined
                ? formatPct(inflationMonth, 1).replace('+', '')
                : '…'}
            </strong>
          </span>
          <span style={{ marginLeft: 'auto', opacity: 0.7 }}>
            Source: BCRA live · {data?.bcra.source ?? '…'}
          </span>
        </div>
      </div>
    </header>
  );
};

export default Header;
