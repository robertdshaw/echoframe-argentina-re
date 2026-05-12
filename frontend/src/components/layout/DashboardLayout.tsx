import type { ReactNode } from 'react';
import StatusBar from './StatusBar';
import Sidebar from './Sidebar';
import type { PageKey } from './Sidebar';
import DisclaimerBanner from '../common/DisclaimerBanner';

interface Props {
  active: PageKey;
  onPageChange: (page: PageKey) => void;
  children: ReactNode;
}

const PAGE_LABEL: Record<PageKey, { title: string; sub: string }> = {
  departamentos: {
    title: 'Departamentos · CABA',
    sub: 'Buenos Aires apartment forecasts, regime detection, live market data.',
  },
  campos: {
    title: 'Campos · Agricultural Land',
    sub: 'Pampas land valuation, commodity-driven outlook, regional spread.',
  },
  signals: {
    title: 'Market intelligence',
    sub: 'Live news signals classified by impact, segment, and direction.',
  },
  scenarios: {
    title: 'Scenario explorer',
    sub: 'Counterfactual analysis under alternative macro assumptions.',
  },
};

const DashboardLayout = ({ active, onPageChange, children }: Props) => (
  <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column' }}>
    <StatusBar />

    <main className="container" style={{ flex: 1, paddingTop: 24, paddingBottom: 32 }}>
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: '256px minmax(0, 1fr)',
          gap: 24,
          alignItems: 'start',
        }}
      >
        <Sidebar active={active} onChange={onPageChange} />
        <div className="fade-in-up" style={{ minWidth: 0 }}>
          <div
            style={{
              display: 'flex',
              alignItems: 'baseline',
              justifyContent: 'space-between',
              marginBottom: 18,
              flexWrap: 'wrap',
              gap: 12,
            }}
          >
            <div>
              <div className="eyebrow" style={{ marginBottom: 4 }}>
                Dashboard
              </div>
              <h1 className="title-1">{PAGE_LABEL[active].title}</h1>
              <div className="body-sm" style={{ marginTop: 4 }}>
                {PAGE_LABEL[active].sub}
              </div>
            </div>
          </div>
          {children}
        </div>
      </div>
    </main>

    <DisclaimerBanner />
  </div>
);

export default DashboardLayout;
