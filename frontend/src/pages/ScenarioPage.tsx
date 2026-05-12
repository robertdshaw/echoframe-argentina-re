import ScenarioExplorer from '../components/scenarios/ScenarioExplorer';

const ScenarioPage = () => (
  <div>
    <div className="card">
      <h2 style={{ fontSize: 20, fontWeight: 700, marginBottom: 6 }}>
        Scenario Explorer
      </h2>
      <p style={{ color: '#666', fontSize: 14 }}>
        Adjust macro assumptions to see how the forecast shifts. The Bayesian
        priors are re-evaluated server-side under your alternative path.
      </p>
    </div>
    <ScenarioExplorer />
  </div>
);

export default ScenarioPage;
