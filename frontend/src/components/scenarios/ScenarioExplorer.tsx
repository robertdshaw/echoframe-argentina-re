import { useEffect, useState } from 'react';
import { scenariosApi } from '../../api/client';
import type { ScenarioForecastResponse, Segment, ScenarioParameters } from '../../types';
import { useBaseCase } from '../../hooks/useBaseCase';
import ScenarioSlider from './ScenarioSlider';
import FanChart from '../forecast/FanChart';
import ForecastCard from '../forecast/ForecastCard';
import LoadingSpinner from '../common/LoadingSpinner';
import ErrorMessage from '../common/ErrorMessage';

const ScenarioExplorer = () => {
  const { baseCase, loading: baseLoading } = useBaseCase();
  const [segment, setSegment] = useState<Segment>('departamentos');
  const [params, setParams] = useState<Required<ScenarioParameters> | null>(null);
  const [result, setResult] = useState<ScenarioForecastResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Initialise sliders from the live base case once it arrives. After that,
  // user edits are preserved — we only re-sync on an explicit Reset.
  useEffect(() => {
    if (baseLoading || params !== null) return;
    setParams({
      inflation_target: baseCase.inflation_target.value,
      usd_ars_target: baseCase.usd_ars_target.value,
      mortgage_rate_adjustment: baseCase.mortgage_rate_adjustment.value,
      retenciones_change: baseCase.retenciones_change.value,
      news_sentiment_override: baseCase.news_sentiment_override.value,
      gdp_growth_override: baseCase.gdp_growth_override.value,
    });
  }, [baseCase, baseLoading, params]);

  const run = async () => {
    setLoading(true);
    setError(null);
    if (!params) return;
    try {
      const data = await scenariosApi.simulate(segment, params);
      setResult(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  };

  const reset = () => {
    setParams({
      inflation_target: baseCase.inflation_target.value,
      usd_ars_target: baseCase.usd_ars_target.value,
      mortgage_rate_adjustment: baseCase.mortgage_rate_adjustment.value,
      retenciones_change: baseCase.retenciones_change.value,
      news_sentiment_override: baseCase.news_sentiment_override.value,
      gdp_growth_override: baseCase.gdp_growth_override.value,
    });
    setResult(null);
  };

  const update = (key: keyof ScenarioParameters, value: number) =>
    setParams((p) => (p ? { ...p, [key]: value } : p));

  if (!params) {
    return <LoadingSpinner label="Loading base case from live macro data…" />;
  }

  return (
    <div style={{ display: 'grid', gridTemplateColumns: '320px 1fr', gap: 24 }}>
      <div className="card">
        <h3 style={{ fontSize: 16, marginBottom: 16 }}>Scenario parameters</h3>

        <label style={{ fontSize: 13, fontWeight: 600, color: '#444' }}>
          Segment
        </label>
        <select
          value={segment}
          onChange={(e) => setSegment(e.target.value as Segment)}
          style={{
            display: 'block',
            width: '100%',
            padding: '6px 10px',
            margin: '6px 0 18px',
            border: '1px solid #E5E7EB',
            borderRadius: 4,
          }}
        >
          <option value="departamentos">Departamentos (CABA)</option>
          <option value="campos">Campos (agricultural)</option>
        </select>

        <div
          style={{
            padding: '10px 12px',
            background: '#F8F9FB',
            border: '1px solid #E5E7EB',
            borderRadius: 6,
            fontSize: 12,
            color: '#444',
            marginBottom: 16,
            lineHeight: 1.5,
          }}
        >
          Sliders start at the model's current view (▲ markers). Move any of
          them to ask <em>"what if this changed?"</em> — the forecast re-runs
          under your counterfactual.
        </div>

        <ScenarioSlider
          label="Inflation target (annual)"
          value={params.inflation_target}
          min={5}
          max={40}
          step={1}
          unit="%"
          onChange={(v) => update('inflation_target', v)}
          baseCase={baseCase.inflation_target}
        />
        <ScenarioSlider
          label="USD/ARS rate"
          value={params.usd_ars_target}
          min={800}
          max={3000}
          step={50}
          onChange={(v) => update('usd_ars_target', v)}
          baseCase={baseCase.usd_ars_target}
        />
        <ScenarioSlider
          label="Mortgage rate Δ (pp)"
          value={params.mortgage_rate_adjustment}
          min={-5}
          max={10}
          step={0.5}
          unit="pp"
          onChange={(v) => update('mortgage_rate_adjustment', v)}
          baseCase={baseCase.mortgage_rate_adjustment}
        />
        <ScenarioSlider
          label="Retenciones Δ (pp)"
          value={params.retenciones_change}
          min={-10}
          max={10}
          step={1}
          unit="pp"
          onChange={(v) => update('retenciones_change', v)}
          baseCase={baseCase.retenciones_change}
        />
        <ScenarioSlider
          label="News sentiment override"
          value={params.news_sentiment_override}
          min={-1}
          max={1}
          step={0.1}
          onChange={(v) => update('news_sentiment_override', v)}
          baseCase={baseCase.news_sentiment_override}
        />

        <div style={{ display: 'flex', gap: 8, marginTop: 16 }}>
          <button
            onClick={run}
            disabled={loading}
            style={{
              flex: 1,
              padding: '10px 14px',
              border: 'none',
              background: '#1B2A4A',
              color: '#FFFFFF',
              borderRadius: 6,
              fontWeight: 600,
              cursor: loading ? 'wait' : 'pointer',
            }}
          >
            {loading ? 'Running…' : 'Run scenario'}
          </button>
          <button
            onClick={reset}
            style={{
              padding: '10px 14px',
              background: '#FFFFFF',
              color: '#1B2A4A',
              border: '1px solid #E5E7EB',
              borderRadius: 6,
              fontWeight: 600,
              cursor: 'pointer',
            }}
          >
            Reset
          </button>
        </div>
      </div>

      <div>
        {error && <ErrorMessage message={error} />}
        {loading && <LoadingSpinner label="Computing scenario…" />}
        {!loading && !result && (
          <div className="card" style={{ color: '#666', textAlign: 'center', padding: 40 }}>
            Adjust the assumptions on the left and click <strong>Run scenario</strong> to
            see how the forecast shifts under your alternative macro path.
          </div>
        )}
        {result && (
          <>
            <div className="card">
              <h3 style={{ fontSize: 16, marginBottom: 12 }}>Scenario forecast trajectory</h3>
              <FanChart
                forecast={result.scenario_forecast}
                unit={segment === 'departamentos' ? 'usd_per_m2' : 'usd_per_ha'}
              />
            </div>
            <div className="card">
              <h3 style={{ fontSize: 16, marginBottom: 12 }}>Scenario horizons</h3>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 12 }}>
                {[1, 2, 3].map((year) => {
                  const horizon =
                    result.scenario_forecast.forecasts[String(year)] ??
                    result.scenario_forecast.forecasts[year];
                  if (!horizon) return null;
                  return (
                    <ForecastCard
                      key={year}
                      horizon={horizon}
                      currentPrice={result.scenario_forecast.current_price}
                      unitLabel={segment === 'departamentos' ? 'USD/m²' : 'USD/ha'}
                    />
                  );
                })}
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
};

export default ScenarioExplorer;
