import SignalFeed from '../components/signals/SignalFeed';

const SignalsPage = () => (
  <div className="card">
    <h2 style={{ fontSize: 20, fontWeight: 700, marginBottom: 6 }}>
      Market Intelligence Feed
    </h2>
    <p style={{ color: '#666', fontSize: 14, marginBottom: 20 }}>
      News signals classified by impact direction, signal type, and affected
      segment. These signals feed directly into the Bayesian forecasting models.
    </p>
    <SignalFeed limit={40} />
  </div>
);

export default SignalsPage;
