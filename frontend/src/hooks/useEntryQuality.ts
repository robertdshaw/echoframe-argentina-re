import { useEffect, useState } from 'react';
import { forecastApi } from '../api/client';
import type { EntryQualityResponse } from '../types';

interface AsyncState<T> {
  data: T | null;
  loading: boolean;
  error: string | null;
}

export const useEntryQuality = (): AsyncState<EntryQualityResponse> => {
  const [state, setState] = useState<AsyncState<EntryQualityResponse>>({
    data: null,
    loading: true,
    error: null,
  });

  useEffect(() => {
    let cancelled = false;
    forecastApi
      .getEntryQuality()
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
