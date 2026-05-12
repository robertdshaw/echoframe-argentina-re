import { useEffect, useState } from 'react';
import { marketApi } from '../api/client';
import type { MacroIndicatorsResponse } from '../types';

interface MacroState {
  data: MacroIndicatorsResponse | null;
  loading: boolean;
  error: string | null;
}

export const useMacroIndicators = (): MacroState => {
  const [state, setState] = useState<MacroState>({
    data: null,
    loading: true,
    error: null,
  });

  useEffect(() => {
    let cancelled = false;
    marketApi
      .getMacro()
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
