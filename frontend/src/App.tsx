import { useState } from 'react';
import DashboardLayout from './components/layout/DashboardLayout';
import type { PageKey } from './components/layout/Sidebar';
import DepartamentosPage from './pages/DepartamentosPage';
import CamposPage from './pages/CamposPage';
import SignalsPage from './pages/SignalsPage';
import ScenarioPage from './pages/ScenarioPage';

const App = () => {
  const [page, setPage] = useState<PageKey>('departamentos');

  const content = (() => {
    switch (page) {
      case 'departamentos':
        return <DepartamentosPage />;
      case 'campos':
        return <CamposPage />;
      case 'signals':
        return <SignalsPage />;
      case 'scenarios':
        return <ScenarioPage />;
    }
  })();

  return (
    <DashboardLayout active={page} onPageChange={setPage}>
      {content}
    </DashboardLayout>
  );
};

export default App;
