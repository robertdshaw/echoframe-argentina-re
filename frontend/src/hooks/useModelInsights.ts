import { useEffect, useState } from 'react';
import { modelApi } from '../api/client';
import type { ModelInsightsResponse } from '../types';

interface State {
  data: ModelInsightsResponse | null;
  loading: boolean;
  error: string | null;
}

export const useModelInsights = (): State => {
  const [state, setState] = useState<State>({
    data: null,
    loading: true,
    error: null,
  });

  useEffect(() => {
    let cancelled = false;
    modelApi
      .getInsights()
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
