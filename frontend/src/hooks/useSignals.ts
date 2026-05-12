import { useEffect, useState } from 'react';
import { signalsApi } from '../api/client';
import type { ProcessedSignal, Segment } from '../types';

interface SignalsState {
  signals: ProcessedSignal[];
  loading: boolean;
  error: string | null;
}

export const useSignals = (
  segment?: Segment,
  limit = 20,
): SignalsState => {
  const [state, setState] = useState<SignalsState>({
    signals: [],
    loading: true,
    error: null,
  });

  useEffect(() => {
    let cancelled = false;
    setState((s) => ({ ...s, loading: true, error: null }));
    signalsApi
      .getLatest({ segment, limit })
      .then((signals) => {
        if (!cancelled) setState({ signals, loading: false, error: null });
      })
      .catch((err: Error) => {
        if (!cancelled)
          setState({ signals: [], loading: false, error: err.message });
      });
    return () => {
      cancelled = true;
    };
  }, [segment, limit]);

  return state;
};
