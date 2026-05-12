import { useEffect, useState } from 'react';
import { forecastApi } from '../api/client';
import type { BarrioRankingsResponse } from '../types';

interface AsyncState<T> {
  data: T | null;
  loading: boolean;
  error: string | null;
}

export const useBarrioRankings = (): AsyncState<BarrioRankingsResponse> => {
  const [state, setState] = useState<AsyncState<BarrioRankingsResponse>>({
    data: null,
    loading: true,
    error: null,
  });

  useEffect(() => {
    let cancelled = false;
    forecastApi
      .getBarrioRankings()
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
