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
import NetReturnWaterfall from '../components/forecast/NetReturnWaterfall';
import HurdleRateBar from '../components/forecast/HurdleRateBar';
import BarrioForecastPanel from '../components/forecast/BarrioForecastPanel';
import TimingTriggerPanel from '../components/forecast/TimingTriggerPanel';
import ScenarioImpactPanel from '../components/forecast/ScenarioImpactPanel';
import EvidenceDrawer from '../components/common/EvidenceDrawer';
import RegimeIndicator from '../components/regime/RegimeIndicator';
import RegimeHistoryStrip from '../components/regime/RegimeHistoryStrip';
import ModelAccuracyPanel from '../components/model/ModelAccuracyPanel';
import HmmPanel from '../components/model/HmmPanel';
import PropertyMap from '../components/maps/PropertyMap';
import SignalFeed from '../components/signals/SignalFeed';
import ErrorBoundary from '../components/common/ErrorBoundary';
import {
  ChartCardSkeleton,
  DistributionPanelSkeleton,
  ForecastNumbersSkeleton,
} from '../components/common/SectionSkeletons';

const BARRIOS = [
  '',
  'Palermo',
  'Recoleta',
  'Belgrano',
  'Caballito',
  'Villa Urquiza',
  'Villa Crespo',
  'Puerto Madero',
  'La Boca',
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

const DepartamentosPage = () => {
  const [barrio, setBarrio] = useState<string>('');
  const [horizon, setHorizon] = useState<1 | 2 | 3>(1);
  const [showBehavioral, setShowBehavioral] = useState(false);
  const { data: forecast, error: fError } = useForecast(
    'departamentos',
    barrio || undefined,
  );
  const { data: insights } = useModelInsights();

  const horizonForecast = forecast?.forecasts[String(horizon)];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
      {/* 1. HERO — renders skeleton while forecast loads */}
      <section>
        <ErrorBoundary fallbackTitle="Forecast unavailable">
          {forecast ? (
            <ExecutiveCard
              forecast={forecast}
              segment="departamentos"
              location={barrio || undefined}
            />
          ) : (
            <ExecutiveCardSkeleton />
          )}
        </ErrorBoundary>
        {fError && (
          <div className="error">
            <strong>Forecast service:</strong> {fError}. Showing cached values
            elsewhere on the page where available.
          </div>
        )}
        <NarrativeCard segment="departamentos" location={barrio || undefined} />
      </section>

      {/* §01 WHERE TO BUY — barrio hierarchical heat map + ranked tables */}
      <section>
        <SectionLabel
          number="01"
          eyebrow="Where to buy"
          title="Best Buenos Aires neighborhoods · next 12 months"
          sub="Where the strongest expected returns sit, blending each neighborhood's own sales history with the citywide trend. Click any circle on the map to drill in."
        />
        <ErrorBoundary fallbackTitle="Neighborhood forecast unavailable">
          <BarrioForecastPanel onSelectBarrio={(name) => setBarrio(name)} />
        </ErrorBoundary>
      </section>

      {/* §02 WHEN TO ACT — entry-quality timing triggers */}
      <section>
        <SectionLabel
          number="02"
          eyebrow="When to act"
          title="Is this a good time to buy?"
          sub="Four real-world conditions that historically marked good entry windows — peso stability, inventory levels, central bank reserves, mortgage availability. A 0–10 read with the closest historical match."
        />
        <ErrorBoundary fallbackTitle="Entry-quality unavailable">
          <TimingTriggerPanel />
        </ErrorBoundary>
      </section>

      {/* §03 WHAT YOU'LL EARN — net annual USD return waterfall */}
      <section>
        <SectionLabel
          number="03"
          eyebrow="What you'll earn"
          title="Net annual USD return"
          sub="Gross appreciation plus rental yield, minus carrying costs, taxes, and amortised transaction friction. Drag the hold-period slider to see how patience changes the take-home."
        />
        <ErrorBoundary fallbackTitle="Net return unavailable">
          <NetReturnWaterfall barrio={barrio || undefined} />
        </ErrorBoundary>
      </section>

      {/* §04 VERSUS ALTERNATIVES — hurdle-rate comparison.
          Tail-risk scenarios moved into Evidence drawer below: for a
          property investor the 80% band on the call already does the
          tail-risk work; three discrete probability-weighted scenarios
          read as academic. Analysts still get them on click. */}
      <section>
        <SectionLabel
          number="04"
          eyebrow="Versus alternatives"
          title="Hurdle-rate comparison"
          sub="Where the apartment thesis sits against passive USD alternatives. The right framing is 'Treasuries plus optionality on Argentine normalisation,' not 'equity beating.'"
        />
        <ErrorBoundary fallbackTitle="Hurdle comparison unavailable">
          <HurdleRateBar barrio={barrio || undefined} />
        </ErrorBoundary>
      </section>

      {/* §05 GEOGRAPHY — sampled listings map */}
      <section>
        <SectionLabel
          number="05"
          eyebrow="Geography"
          title="Listings across CABA"
          sub="Sampled apartments with real coordinates. Color = price/m² band, circle size ∝ surface."
        />
        <ErrorBoundary fallbackTitle="Map unavailable">
          <PropertyMap barrio={barrio || undefined} />
        </ErrorBoundary>
      </section>

      {/* §06 SIGNALS — denoised news driving the call */}
      <section>
        <SectionLabel
          number="06"
          eyebrow="News intelligence"
          title="Signals driving the current forecast"
          sub="Live Spanish-language news, classified by impact direction and magnitude. Each surviving headline carries a provenance tag naming the section it influences."
        />
        <ErrorBoundary fallbackTitle="News feed unavailable">
          <div className="card">
            <SignalFeed
              defaultSegment="departamentos"
              limit={8}
              showFilters={false}
            />
          </div>
        </ErrorBoundary>
      </section>

      {/* EVIDENCE DRAWER — model machinery; collapsed by default so the
          narrative panels lead the page. Forecast trajectory, outcome
          distribution, regime detection, and backtest live in here for
          analysts or skeptical clients who want to inspect the math. */}
      <EvidenceDrawer
        title="Model machinery & methodology"
        subtitle="Forecast trajectory, outcome distribution, regime detection, tail-risk scenarios, calibration backtest. Collapsed by default."
      >
        <ErrorBoundary fallbackTitle="Scenarios unavailable">
          <ScenarioImpactPanel />
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
                    Bayesian posterior · price path
                  </div>
                  <div className="body-sm" style={{ marginTop: 2, maxWidth: 560 }}>
                    Historical USD/m² recovery from 2018Q1 trough, with
                    Student-t (df=4) posterior bands at Y1/Y2/Y3.
                  </div>
                </div>
                <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
                  <select
                    value={barrio}
                    onChange={(e) => setBarrio(e.target.value)}
                  >
                    {BARRIOS.map((b) => (
                      <option key={b} value={b}>
                        {b === '' ? 'All CABA' : b}
                      </option>
                    ))}
                  </select>
                  <label
                    style={{
                      display: 'inline-flex',
                      alignItems: 'center',
                      gap: 6,
                      fontSize: 12,
                      color: 'var(--text-2)',
                      paddingLeft: 8,
                    }}
                  >
                    <input
                      type="checkbox"
                      checked={showBehavioral}
                      onChange={(e) => setShowBehavioral(e.target.checked)}
                    />
                    Behavioral overlay
                  </label>
                </div>
              </div>
              <FanChart
                forecast={forecast}
                unit="usd_per_m2"
                showBehavioral={showBehavioral}
              />
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
                  unitLabel="USD/m²"
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
          ) : insights?.status === 'not_run' ? (
            <div
              className="card"
              style={{ background: 'var(--amber-50)', borderColor: '#FCD3AB' }}
            >
              <div className="eyebrow" style={{ color: 'var(--amber-600)' }}>
                Backtest not run
              </div>
              <div className="body-sm" style={{ marginTop: 4 }}>
                Run{' '}
                <code
                  className="mono"
                  style={{
                    background: '#FFFFFF',
                    padding: '2px 6px',
                    borderRadius: 3,
                    fontSize: 12,
                  }}
                >
                  python scripts/run_backtest.py
                </code>{' '}
                from the repo root to populate the model-accuracy panel.
              </div>
            </div>
          ) : (
            <>
              <ChartCardSkeleton />
              <ChartCardSkeleton />
            </>
          )}
        </ErrorBoundary>
      </EvidenceDrawer>
    </div>
  );
};

export default DepartamentosPage;
