import { useEffect, useState } from 'react';
import { useMacroIndicators } from '../../hooks/useMarketData';
import { forecastApi } from '../../api/client';
import type { ForecastSummaryResponse } from '../../types';
import { formatNumber, formatPct, formatProb } from '../../utils/formatters';

const REGIME_TINT: Record<string, string> = {
  crisis: '#FF5A4D',
  recovery: '#36D399',
  boom: '#FBBF24',
};
const REGIME_LABEL: Record<string, string> = {
  crisis: 'CRISIS',
  recovery: 'RECOVERY',
  boom: 'BOOM',
};

interface CellProps {
  label: string;
  value: string | null;
  sub?: string | null;
  accent?: string;
  loading?: boolean;
}

const Cell = ({ label, value, sub, accent, loading }: CellProps) => (
  <div
    style={{
      display: 'flex',
      flexDirection: 'column',
      gap: 2,
      paddingLeft: 18,
      paddingRight: 18,
      borderLeft: '1px solid rgba(255,255,255,0.08)',
      minWidth: 92,
    }}
  >
    <div
      style={{
        fontSize: 9,
        fontWeight: 600,
        letterSpacing: 0.16,
        textTransform: 'uppercase',
        color: 'rgba(255,255,255,0.42)',
        whiteSpace: 'nowrap',
      }}
    >
      {label}
    </div>
    {loading ? (
      <div
        className="skel"
        style={{
          width: 60,
          height: 14,
          background: 'rgba(255,255,255,0.08)',
        }}
      />
    ) : (
      <div
        className="mono"
        style={{
          fontSize: 13,
          fontWeight: 600,
          color: accent ?? 'rgba(255,255,255,0.96)',
          lineHeight: 1.2,
          letterSpacing: '-0.01em',
          whiteSpace: 'nowrap',
        }}
      >
        {value ?? '—'}
      </div>
    )}
    {sub && (
      <div
        style={{
          fontSize: 10,
          color: 'rgba(255,255,255,0.4)',
          whiteSpace: 'nowrap',
        }}
        className="mono"
      >
        {sub}
      </div>
    )}
  </div>
);

const StatusBar = () => {
  const { data: macro, loading: macroLoading } = useMacroIndicators();
  const [summary, setSummary] = useState<ForecastSummaryResponse | null>(null);
  const [time, setTime] = useState<Date>(new Date());

  useEffect(() => {
    let cancelled = false;
    forecastApi
      .getSummary()
      .then((d) => !cancelled && setSummary(d))
      .catch(() => {});
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    const t = setInterval(() => setTime(new Date()), 30_000);
    return () => clearInterval(t);
  }, []);

  const regime = summary?.departamentos.current_regime ?? 'recovery';
  const regimeColor = REGIME_TINT[regime];

  return (
    <div
      style={{
        background: 'linear-gradient(180deg, #050B1F 0%, #0A1530 100%)',
        color: '#FFFFFF',
        borderBottom: '1px solid rgba(255,255,255,0.06)',
        position: 'sticky',
        top: 0,
        zIndex: 50,
        boxShadow: '0 1px 0 rgba(255,255,255,0.04) inset',
      }}
    >
      <div
        className="container"
        style={{
          display: 'flex',
          alignItems: 'stretch',
          gap: 0,
          minHeight: 64,
          paddingTop: 0,
          paddingBottom: 0,
        }}
      >
        {/* Brand block — fixed width, won't shrink */}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: 12,
            paddingRight: 20,
            flex: '0 0 auto',
          }}
        >
          <div
            style={{
              width: 32,
              height: 32,
              borderRadius: 7,
              background:
                'linear-gradient(135deg, #FF7847 0%, #E85D26 55%, #C84B1C 100%)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontFamily: "'JetBrains Mono', monospace",
              fontWeight: 700,
              fontSize: 14,
              color: '#FFFFFF',
              boxShadow: '0 6px 16px rgba(232,93,38,0.35), 0 1px 0 rgba(255,255,255,0.2) inset',
              flexShrink: 0,
            }}
          >
            E
          </div>
          <div style={{ minWidth: 0 }}>
            <div
              style={{
                fontSize: 14,
                fontWeight: 700,
                letterSpacing: '-0.015em',
                lineHeight: 1.1,
                whiteSpace: 'nowrap',
              }}
            >
              EchoFrame
            </div>
            <div
              style={{
                fontSize: 10,
                color: 'rgba(255,255,255,0.45)',
                marginTop: 1,
                letterSpacing: 0.05,
                whiteSpace: 'nowrap',
              }}
            >
              Argentina · RE Intelligence
            </div>
          </div>
        </div>

        {/* Live indicator — fixed */}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            flexShrink: 0,
          }}
        >
          <div
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: 6,
              padding: '4px 10px',
              background: 'rgba(54,211,153,0.12)',
              border: '1px solid rgba(54,211,153,0.28)',
              borderRadius: 999,
              fontSize: 10,
              fontWeight: 700,
              letterSpacing: 0.12,
              color: '#36D399',
              textTransform: 'uppercase',
            }}
          >
            <span className="dot dot-green dot-pulse" />
            Live
          </div>
        </div>

        {/* Scrollable cell rail */}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            marginLeft: 'auto',
            overflowX: 'auto',
            scrollbarWidth: 'none',
          }}
        >
          <Cell
            label="Regime"
            value={REGIME_LABEL[regime]}
            accent={regimeColor}
            sub={
              summary
                ? `${formatProb(summary.departamentos.regime_confidence)} conf.`
                : null
            }
            loading={!summary}
          />
          <Cell
            label="USD/ARS"
            value={
              macro?.bcra.exchange_rate
                ? formatNumber(macro.bcra.exchange_rate.value, 2)
                : null
            }
            sub={macro?.bcra.exchange_rate?.date}
            loading={macroLoading}
          />
          <Cell
            label="IPC m/m"
            value={
              macro?.bcra.inflation
                ? formatPct(macro.bcra.inflation.value, 1).replace('+', '')
                : null
            }
            sub={macro?.bcra.inflation?.date}
            loading={macroLoading}
          />
          <Cell
            label="BCRA rate"
            value={
              macro?.bcra.reference_rate
                ? formatPct(macro.bcra.reference_rate.value, 1).replace('+', '')
                : null
            }
            sub={macro?.bcra.reference_rate?.date}
            loading={macroLoading}
          />
          <Cell
            label="REM ipc"
            value={
              macro?.rem.inflation_forecast
                ? `${macro.rem.inflation_forecast.median.toFixed(1)}%`
                : null
            }
            sub="consensus"
            loading={macroLoading}
          />
          <div
            style={{
              display: 'flex',
              flexDirection: 'column',
              gap: 2,
              paddingLeft: 18,
              paddingRight: 0,
              borderLeft: '1px solid rgba(255,255,255,0.08)',
              minWidth: 92,
            }}
          >
            <div
              style={{
                fontSize: 9,
                fontWeight: 600,
                letterSpacing: 0.16,
                textTransform: 'uppercase',
                color: 'rgba(255,255,255,0.42)',
                whiteSpace: 'nowrap',
              }}
            >
              Local time
            </div>
            <div
              className="mono"
              style={{
                fontSize: 13,
                fontWeight: 600,
                color: 'rgba(255,255,255,0.96)',
                lineHeight: 1.2,
                whiteSpace: 'nowrap',
              }}
            >
              {time.toLocaleTimeString('en-GB', {
                hour: '2-digit',
                minute: '2-digit',
              })}
            </div>
            <div
              style={{ fontSize: 10, color: 'rgba(255,255,255,0.4)', whiteSpace: 'nowrap' }}
              className="mono"
            >
              {time.toLocaleDateString('en-GB', {
                day: '2-digit',
                month: 'short',
              })}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default StatusBar;
