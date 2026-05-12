import { useEffect, useState } from 'react';
import { forecastApi } from '../api/client';
import type { CanonicalScenariosResponse } from '../types';

interface AsyncState<T> {
  data: T | null;
  loading: boolean;
  error: string | null;
}

export const useCanonicalScenarios = (): AsyncState<CanonicalScenariosResponse> => {
  const [state, setState] = useState<AsyncState<CanonicalScenariosResponse>>({
    data: null,
    loading: true,
    error: null,
  });

  useEffect(() => {
    let cancelled = false;
    forecastApi
      .getCanonicalScenarios()
      .then((data) => {
        if (!cancelled) setState({ data, loading: false, error: null });
      })
      .catch((err: Error) => {
        if (!cancelled)
          setState({ data: null, loading: false, error: err.message });
      });
    return () => {
      cancelled = true;
    };
  }, []);

  return state;
};
