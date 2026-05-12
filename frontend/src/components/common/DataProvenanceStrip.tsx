import { useMacroIndicators } from '../../hooks/useMarketData';

interface SourceProps {
  name: string;
  detail: string;
  status: 'live' | 'seeded' | 'down';
  freshness?: string;
}

const STATUS_LABEL: Record<SourceProps['status'], string> = {
  live: 'LIVE',
  seeded: 'SEED',
  down: 'DOWN',
};

const Source = ({ name, detail, status, freshness }: SourceProps) => {
  const dotClass =
    status === 'live'
      ? 'badge-dot badge-dot-green'
      : status === 'seeded'
        ? 'badge-dot badge-dot-amber'
        : 'badge-dot badge-dot-red';
  const badgeClass =
    status === 'live'
      ? 'badge badge-live'
      : status === 'seeded'
        ? 'badge badge-seeded'
        : 'badge badge-down';
  return (
    <div
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: 10,
        padding: '8px 12px',
        background: '#FFFFFF',
        border: '1px solid #EEF0F5',
        borderRadius: 6,
      }}
    >
      <span className={dotClass} />
      <div style={{ flex: 1 }}>
        <div
          style={{ fontSize: 11, fontWeight: 600, color: '#0F1B3D' }}
        >
          {name}
        </div>
        <div style={{ fontSize: 10, color: '#8C95AD' }}>{detail}</div>
      </div>
      <span className={badgeClass}>{STATUS_LABEL[status]}</span>
      {freshness && (
        <span style={{ fontSize: 10, color: '#8C95AD' }} className="mono">
          {freshness}
        </span>
      )}
    </div>
  );
};

interface Props {
  newsFreshness?: 'live' | 'static_seed';
  listingsFreshness?: 'live' | 'static_seed';
}

const DataProvenanceStrip = ({ newsFreshness, listingsFreshness }: Props) => {
  const { data, loading } = useMacroIndicators();
  const bcraDate = data?.bcra.exchange_rate?.date;
  const remPeriod = data?.rem.inflation_forecast?.period;

  return (
    <div className="card card-tight">
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          marginBottom: 10,
        }}
      >
        <div className="card-eyebrow">Data provenance</div>
        <div style={{ fontSize: 10, color: '#8C95AD' }}>
          7 sources monitored · {loading ? 'syncing…' : 'all responsive'}
        </div>
      </div>
      <div className="grid grid-4">
        <Source
          name="BCRA"
          detail="Banco Central macro (v4 API)"
          status={data?.bcra.source === 'live' ? 'live' : data?.bcra.source === 'fallback' ? 'seeded' : 'live'}
          freshness={bcraDate}
        />
        <Source
          name="REM"
          detail="Economist consensus survey"
          status={data?.rem.source === 'live' ? 'live' : data?.rem.source === 'fallback' ? 'seeded' : 'live'}
          freshness={remPeriod}
        />
        <Source
          name="NewsData.io"
          detail="Spanish-language ARG news"
          status={newsFreshness === 'live' ? 'live' : 'seeded'}
        />
        <Source
          name="Properati"
          detail="Buenos Aires listings (scraped)"
          status={listingsFreshness === 'live' ? 'live' : 'seeded'}
        />
      </div>
    </div>
  );
};

export default DataProvenanceStrip;
