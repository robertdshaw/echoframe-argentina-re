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
import ModelAccuracyPanel from '../components/model/ModelAccuracyPanel';
import HmmPanel from '../components/model/HmmPanel';
import CamposMap from '../components/maps/CamposMap';
import SignalFeed from '../components/signals/SignalFeed';
import ErrorBoundary from '../components/common/ErrorBoundary';
import EvidenceDrawer from '../components/common/EvidenceDrawer';
import {
  CamposZonePanel,
  CamposReturnPanel,
  CamposHurdleBar,
  CamposScenariosPanel,
} from '../components/forecast/CamposPanels';
import {
  ChartCardSkeleton,
  DistributionPanelSkeleton,
  ForecastNumbersSkeleton,
} from '../components/common/SectionSkeletons';

const ZONE_LABEL: Record<string, string> = {
  core_pampa: 'Core Pampa',
  santa_fe: 'Santa Fe',
  frontier: 'Frontier',
  periurban: 'Peri-urban',
};

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
      {/* HERO — the call */}
      <section>
        <ErrorBoundary fallbackTitle="Forecast unavailable">
          {forecast ? (
            <ExecutiveCard
              forecast={forecast}
              segment="campos"
              location={zone ? ZONE_LABEL[zone] : undefined}
            />
          ) : (
            <ExecutiveCardSkeleton />
          )}
        </ErrorBoundary>
        {error && (
          <div className="error">
            <strong>Forecast service:</strong> {error}. Showing cached values
            elsewhere on the page where available.
          </div>
        )}
        <NarrativeCard segment="campos" location={zone || undefined} />
      </section>

      {/* §01 WHERE TO BUY — zone-level forecast cards */}
      <section>
        <SectionLabel
          number="01"
          eyebrow="Where to buy"
          title="Argentine farmland · zone-level 12-month forecast"
          sub="Each region has a different soil-quality profile and commodity mix. Click any zone to refocus the rest of the page on its prices, scenarios, and benchmarks."
        />
        <ErrorBoundary fallbackTitle="Zone forecast unavailable">
          <CamposZonePanel selected={zone} onSelect={(z) => setZone(z)} />
        </ErrorBoundary>
      </section>

      {/* §02 WHAT YOU'LL EARN — net return waterfall */}
      <section>
        <SectionLabel
          number="02"
          eyebrow="What you'll earn"
          title="Net annual USD return"
          sub="Land-value appreciation plus lease yield, minus input costs, retenciones, taxes, FX friction, and amortised transaction costs. Drag the hold-period slider to see how patience changes the take-home — longer holds favour farmland materially."
        />
        <ErrorBoundary fallbackTitle="Net return unavailable">
          <CamposReturnPanel zone={zone || undefined} />
        </ErrorBoundary>
      </section>

      {/* §03 VERSUS ALTERNATIVES — hurdle-rate comparison */}
      <section>
        <SectionLabel
          number="03"
          eyebrow="Versus alternatives"
          title="Hurdle-rate comparison"
          sub="Where Argentine farmland sits against passive USD alternatives. The pitch is 'a productive USD asset with cash yield plus optionality on commodity strength,' not equity-beating growth."
        />
        <ErrorBoundary fallbackTitle="Hurdle comparison unavailable">
          <CamposHurdleBar zone={zone || undefined} />
        </ErrorBoundary>
      </section>

      {/* §04 GEOGRAPHY — sampled estancias */}
      <section>
        <SectionLabel
          number="04"
          eyebrow="Geography"
          title="Sampled estancias across Argentina"
          sub="Real coordinates on parcels by zone. Click any marker for detail."
        />
        <ErrorBoundary fallbackTitle="Map unavailable">
          <CamposMap zone={zone || undefined} />
        </ErrorBoundary>
      </section>

      {/* §05 SIGNALS — agricultural news */}
      <section>
        <SectionLabel
          number="05"
          eyebrow="News intelligence"
          title="Signals driving the current forecast"
          sub="Live Spanish-language news, filtered for commodity, retenciones, and weather-driven items. Each surviving headline carries a provenance tag naming the section it influences."
        />
        <ErrorBoundary fallbackTitle="News feed unavailable">
          <div className="card">
            <SignalFeed defaultSegment="campos" limit={8} showFilters={false} />
          </div>
        </ErrorBoundary>
      </section>

      {/* EVIDENCE DRAWER — model machinery + tail-risk scenarios.
          Tail scenarios live in here (rather than as a top-level panel)
          because for a typical farmland investor the 80% band on the
          call already does the tail-risk work; three discrete
          probability-weighted scenarios read as academic for non-quant
          buyers. Analysts and skeptics still get them on click. */}
      <EvidenceDrawer
        title="Model machinery & methodology"
        subtitle="Forecast trajectory, outcome distribution, regime detection, tail-risk scenarios, calibration backtest. Collapsed by default."
      >
        <ErrorBoundary fallbackTitle="Scenarios unavailable">
          <CamposScenariosPanel zone={zone || undefined} />
        </ErrorBoundary>

        <ErrorBoundary>
          {forecast ? (
            <div className="card">
              <div
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  marginBottom: 16,
                  flexWrap: 'wrap',
                  gap: 12,
                }}
              >
                <div>
                  <div className="eyebrow">Forecast trajectory</div>
                  <div className="title-3" style={{ marginTop: 4 }}>
                    Bayesian posterior · land-value path
                  </div>
                  <div className="body-sm" style={{ marginTop: 2, maxWidth: 560 }}>
                    Historical USD/ha path with regional sub-models. Student-t
                    bands widen at longer horizons.
                  </div>
                </div>
                <select value={zone} onChange={(e) => setZone(e.target.value)}>
                  <option value="">Aggregate (all zones)</option>
                  {Object.entries(ZONE_LABEL).map(([k, v]) => (
                    <option key={k} value={k}>
                      {v}
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
                  <div>
                    <div className="eyebrow">Outcome distribution</div>
                    <div className="title-3" style={{ marginTop: 4 }}>
                      Year {horizon} · 5-bucket probability
                    </div>
                  </div>
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

        <ErrorBoundary>
          {forecast ? (
            <RegimeIndicator regime={forecast.regime_context} />
          ) : (
            <ForecastNumbersSkeleton />
          )}
        </ErrorBoundary>

        <ErrorBoundary fallbackTitle="Model insights unavailable">
          {insights?.status === 'ok' &&
          insights.backtest &&
          insights.fitted_priors ? (
            <>
              <ModelAccuracyPanel
                backtest={insights.backtest}
                priors={insights.fitted_priors}
              />
              {insights.hmm && <HmmPanel hmm={insights.hmm} />}
              <RegimeHistoryStrip
                records={insights.backtest.records}
                currentRegime={forecast?.regime_context.current ?? 'recovery'}
              />
            </>
          ) : (
            <ChartCardSkeleton />
          )}
        </ErrorBoundary>
      </EvidenceDrawer>
    </div>
  );
};

export default CamposPage;
