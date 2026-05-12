import { useEffect, useState } from 'react';
import { forecastApi } from '../api/client';
import type { NetReturnResponse } from '../types';

interface AsyncState<T> {
  data: T | null;
  loading: boolean;
  error: string | null;
}

export const useNetReturn = (barrio?: string): AsyncState<NetReturnResponse> => {
  const [state, setState] = useState<AsyncState<NetReturnResponse>>({
    data: null,
    loading: true,
    error: null,
  });

  useEffect(() => {
    let cancelled = false;
    setState({ data: null, loading: true, error: null });
    forecastApi
      .getNetReturnDepartamentos(barrio)
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
  }, [barrio]);

  return state;
};
