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
import RegimeIndicator from '../components/regime/RegimeIndicator';
import RegimeHistoryStrip from '../components/regime/RegimeHistoryStrip';
import ModelAccuracyPanel from '../components/model/ModelAccuracyPanel';
import HmmPanel from '../components/model/HmmPanel';
import PropertyMap from '../components/maps/PropertyMap';
import DataProvenanceStrip from '../components/common/DataProvenanceStrip';
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
        <DataProvenanceStrip listingsFreshness="live" newsFreshness="live" />
      </section>

      {/* 2. TRAJECTORY */}
      <section>
        <SectionLabel
          number="01"
          eyebrow="Forecast trajectory"
          title="Bayesian posterior · price path"
          sub="Historical USD/m² recovery from 2018Q1 trough, with Student-t (df=4) posterior bands at Y1/Y2/Y3."
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
                  flexWrap: 'wrap',
                  gap: 12,
                }}
              >
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
      </section>

      {/* 3. DISTRIBUTION + HORIZON */}
      <section>
        <SectionLabel
          number="02"
          eyebrow="Outcome distribution"
          title="Where the model places its mass"
          sub="Probability decomposed into five outcome buckets across the selected horizon."
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
                  unitLabel="USD/m²"
                />
              </div>
            ) : (
              <ForecastNumbersSkeleton />
            )}
          </ErrorBoundary>
        </div>
      </section>

      {/* 4. BARRIO HEAT MAP + RANKED TABLES — answers "where to buy" */}
      <section>
        <SectionLabel
          number="03"
          eyebrow="Where to buy"
          title="Per-barrio 1y forecast"
          sub="Hierarchical partial-pooled model. Each barrio borrows strength from the CABA-aggregate posterior; thin-data barrios are flagged."
        />
        <ErrorBoundary fallbackTitle="Barrio forecast unavailable">
          <BarrioForecastPanel onSelectBarrio={(name) => setBarrio(name)} />
        </ErrorBoundary>
      </section>

      {/* 5. TIMING TRIGGER PANEL — answers "when to act" */}
      <section>
        <SectionLabel
          number="04"
          eyebrow="When to act"
          title="Entry-quality reading"
          sub="Four named triggers from BCRA, Properati, and the news feed roll up to a 0–10 gauge, with the closest historical analogy from the backtest."
        />
        <ErrorBoundary fallbackTitle="Entry-quality unavailable">
          <TimingTriggerPanel />
        </ErrorBoundary>
      </section>

      {/* 6. NET RETURN WATERFALL — answers "what will I actually earn?" */}
      <section>
        <SectionLabel
          number="05"
          eyebrow="What you'll earn"
          title="Net annual USD return"
          sub="Gross appreciation plus rental yield, minus carrying costs, taxes, and amortised transaction friction. Drag the hold-period slider to see how patience changes the take-home."
        />
        <ErrorBoundary fallbackTitle="Net return unavailable">
          <NetReturnWaterfall barrio={barrio || undefined} />
        </ErrorBoundary>
      </section>

      {/* 7. HURDLE-RATE COMPARISON — answers "versus what?" */}
      <section>
        <SectionLabel
          number="06"
          eyebrow="Versus alternatives"
          title="Hurdle-rate comparison"
          sub="Where the apartment thesis sits against passive USD alternatives. The right framing is 'Treasuries plus optionality on Argentine normalisation,' not 'equity beating.'"
        />
        <ErrorBoundary fallbackTitle="Hurdle comparison unavailable">
          <HurdleRateBar barrio={barrio || undefined} />
        </ErrorBoundary>
      </section>

      {/* 8. GEOSPATIAL LISTINGS — map handles its own loading state internally,
              but if forecast errors, fall back to a clean skeleton. */}
      <section>
        <SectionLabel
          number="07"
          eyebrow="Geography"
          title="Listings across CABA"
          sub="Sampled apartments with real coordinates. Color = price/m² band, circle size ∝ surface."
        />
        <ErrorBoundary fallbackTitle="Map unavailable">
          <PropertyMap barrio={barrio || undefined} />
        </ErrorBoundary>
      </section>

      {/* 9. MODEL VALIDATION */}
      <section>
        <SectionLabel
          number="08"
          eyebrow="Model validation"
          title="Historical track record"
          sub="Walk-forward leave-one-out backtest across 29 anchor quarters. Calibration, Brier, MAE vs naive."
        />
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
      </section>

      {/* 10. REGIME */}
      <section>
        <SectionLabel
          number="09"
          eyebrow="Macro regime"
          title="What state is the market in?"
          sub="HMM posterior over Crisis / Recovery / Boom, with transition probabilities forward 4Q."
        />
        <ErrorBoundary>
          {forecast ? (
            <RegimeIndicator regime={forecast.regime_context} />
          ) : (
            <ForecastNumbersSkeleton />
          )}
        </ErrorBoundary>
      </section>

      {/* 11. SIGNALS */}
      <section>
        <SectionLabel
          number="10"
          eyebrow="News intelligence"
          title="Signals driving the current forecast"
          sub="Live Spanish-language news, classified by impact direction and magnitude."
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
    </div>
  );
};

export default DepartamentosPage;
