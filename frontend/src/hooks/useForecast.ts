import { useEffect, useState } from 'react';
import { forecastApi } from '../api/client';
import type { ForecastResponse, ForecastSummaryResponse } from '../types';

interface AsyncState<T> {
  data: T | null;
  loading: boolean;
  error: string | null;
}

export const useForecastSummary = (): AsyncState<ForecastSummaryResponse> => {
  const [state, setState] = useState<AsyncState<ForecastSummaryResponse>>({
    data: null,
    loading: true,
    error: null,
  });

  useEffect(() => {
    let cancelled = false;
    forecastApi
      .getSummary()
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

export const useForecast = (
  segment: 'departamentos' | 'campos',
  filter?: string,
): AsyncState<ForecastResponse> => {
  const [state, setState] = useState<AsyncState<ForecastResponse>>({
    data: null,
    loading: true,
    error: null,
  });

  useEffect(() => {
    let cancelled = false;
    setState({ data: null, loading: true, error: null });
    const fetcher =
      segment === 'departamentos'
        ? forecastApi.getDepartamentos(filter)
        : forecastApi.getCampos(filter);
    fetcher
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
  }, [segment, filter]);

  return state;
};
