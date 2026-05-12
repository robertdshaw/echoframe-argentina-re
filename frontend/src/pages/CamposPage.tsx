import { useState } from 'react';
import { useForecast } from '../hooks/useForecast';
import { useModelInsights } from '../hooks/useModelInsights';
import ExecutiveCard from '../components/forecast/ExecutiveCard';
import ExecutiveCardSkeleton from '../components/forecast/ExecutiveCardSkeleton';
import NarrativeCard from '../components/forecast/NarrativeCard';
import FanChart from '../components/forecast/FanChart';
import ForecastCard from '../components/forecast/ForecastCard';
import ProbabilityGauge from '../components/forecast/ProbabilityGauge';
import HorizonSelector from '../components/forecast/HorizonSelector';
import RegimeIndicator from '../components/regime/RegimeIndicator';
import RegimeHistoryStrip from '../components/regime/RegimeHistoryStrip';
import DataProvenanceStrip from '../components/common/DataProvenanceStrip';
import CamposMap from '../components/maps/CamposMap';
import SignalFeed from '../components/signals/SignalFeed';
import ErrorBoundary from '../components/common/ErrorBoundary';
import {
  ChartCardSkeleton,
  DistributionPanelSkeleton,
  ForecastNumbersSkeleton,
} from '../components/common/SectionSkeletons';

const ZONES: { key: string; label: string }[] = [
  { key: '', label: 'Aggregate (all zones)' },
  { key: 'core_pampa', label: 'Core Pampa' },
  { key: 'santa_fe', label: 'Santa Fe' },
  { key: 'frontier', label: 'Frontier' },
  { key: 'periurban', label: 'Peri-urban' },
];

const SectionLabel = ({
  number,
  eyebrow,
  title,
  sub,
}: {
  number: string;
  eyebrow: string;
  title: string;
  sub?: string;
}) => (
  <div style={{ marginBottom: 14, display: 'flex', gap: 16, alignItems: 'baseline' }}>
    <div
      className="mono"
      style={{
        fontSize: 14,
        fontWeight: 700,
        color: 'var(--orange-500)',
        letterSpacing: 0.05,
        flexShrink: 0,
      }}
    >
      {number}
    </div>
    <div style={{ flex: 1, borderTop: '1px solid var(--border-2)', paddingTop: 12 }}>
      <div className="eyebrow">{eyebrow}</div>
      <h2 className="title-2" style={{ marginTop: 4, marginBottom: sub ? 2 : 0 }}>
        {title}
      </h2>
      {sub && (
        <div className="body-sm" style={{ maxWidth: 560 }}>
          {sub}
        </div>
      )}
    </div>
  </div>
);

const CamposPage = () => {
  const [zone, setZone] = useState<string>('');
  const [horizon, setHorizon] = useState<1 | 2 | 3>(1);
  const { data: forecast, error } = useForecast('campos', zone || undefined);
  const { data: insights } = useModelInsights();
  const horizonForecast = forecast?.forecasts[String(horizon)];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
      <section>
        <ErrorBoundary>
          {forecast ? (
            <ExecutiveCard
              forecast={forecast}
              segment="campos"
              location={ZONES.find((z) => z.key === zone)?.label}
            />
          ) : (
            <ExecutiveCardSkeleton />
          )}
        </ErrorBoundary>
        {error && (
          <div className="error">
            <strong>Forecast service:</strong> {error}.
          </div>
        )}
        <NarrativeCard segment="campos" location={zone || undefined} />
        <DataProvenanceStrip listingsFreshness="static_seed" newsFreshness="live" />
      </section>

      <section>
        <SectionLabel
          number="01"
          eyebrow="Forecast trajectory"
          title="Land value path · USD per hectare"
          sub="Commodity-driven posterior with regional sub-models. Student-t bands widen at longer horizons."
        />
        <ErrorBoundary>
          {forecast ? (
            <div className="card">
              <div
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  marginBottom: 16,
                }}
              >
                <select value={zone} onChange={(e) => setZone(e.target.value)}>
                  {ZONES.map((z) => (
                    <option key={z.key} value={z.key}>
                      {z.label}
                    </option>
                  ))}
                </select>
              </div>
              <FanChart forecast={forecast} unit="usd_per_ha" />
            </div>
          ) : (
            <ChartCardSkeleton />
          )}
        </ErrorBoundary>
      </section>

      <section>
        <SectionLabel
          number="02"
          eyebrow="Outcome distribution"
          title="Where the model places its mass"
        />
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'minmax(0, 1.4fr) minmax(0, 1fr)',
            gap: 16,
          }}
        >
          <ErrorBoundary>
            {horizonForecast ? (
              <div className="card">
                <div
                  style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'baseline',
                    marginBottom: 12,
                  }}
                >
                  <div className="eyebrow">5-bucket distribution</div>
                  <HorizonSelector value={horizon} onChange={setHorizon} />
                </div>
                <ProbabilityGauge
                  estimate={horizonForecast.model_estimate}
                  title={`Year ${horizon}`}
                />
              </div>
            ) : (
              <DistributionPanelSkeleton />
            )}
          </ErrorBoundary>
          <ErrorBoundary>
            {horizonForecast && forecast ? (
              <div className="card">
                <div className="eyebrow">Horizon detail</div>
                <h3 className="title-3" style={{ marginTop: 2, marginBottom: 12 }}>
                  Year {horizon} numbers
                </h3>
                <ForecastCard
                  horizon={horizonForecast}
                  currentPrice={forecast.current_price}
                  unitLabel="USD/ha"
                />
              </div>
            ) : (
              <ForecastNumbersSkeleton />
            )}
          </ErrorBoundary>
        </div>
      </section>

      <section>
        <SectionLabel
          number="03"
          eyebrow="Geography"
          title="Pampas parcels"
          sub="40 sampled estancias with real coordinates."
        />
        <ErrorBoundary fallbackTitle="Map unavailable">
          <CamposMap zone={zone || undefined} />
        </ErrorBoundary>
      </section>

      {insights?.status === 'ok' && insights.backtest && (
        <section>
          <SectionLabel number="04" eyebrow="Regime detection" title="HMM regime history" />
          <ErrorBoundary>
            <RegimeHistoryStrip
              records={insights.backtest.records}
              currentRegime={forecast?.regime_context.current ?? 'recovery'}
            />
          </ErrorBoundary>
        </section>
      )}

      <section>
        <SectionLabel number="05" eyebrow="Macro regime" title="Current state of the market" />
        <ErrorBoundary>
          {forecast ? (
            <RegimeIndicator regime={forecast.regime_context} />
          ) : (
            <ForecastNumbersSkeleton />
          )}
        </ErrorBoundary>
      </section>

      <section>
        <SectionLabel
          number="06"
          eyebrow="News intelligence"
          title="Agricultural signals"
          sub="Live commodity, retenciones and weather-driven signals."
        />
        <ErrorBoundary>
          <div className="card">
            <SignalFeed defaultSegment="campos" limit={8} showFilters={false} />
          </div>
        </ErrorBoundary>
      </section>
    </div>
  );
};

export default CamposPage;
