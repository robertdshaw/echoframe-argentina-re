import { useEffect, useState } from 'react';
import { narrativeApi } from '../api/client';
import type { NarrativeResponse, Segment } from '../types';

interface State {
  data: NarrativeResponse | null;
  loading: boolean;
  error: string | null;
}

/**
 * Fetches the Claude-generated executive narrative for a segment.
 * Re-fetches when segment or location changes.
 */
export const useNarrative = (segment: Segment, location?: string): State => {
  const [state, setState] = useState<State>({
    data: null,
    loading: true,
    error: null,
  });

  useEffect(() => {
    let cancelled = false;
    setState({ data: null, loading: true, error: null });
    narrativeApi
      .generate(segment, location)
      .then((data) => {
        if (!cancelled) setState({ data, loading: false, error: null });
      })
      .catch((err: Error) => {
        if (!cancelled) {
          setState({
            data: null,
            loading: false,
            error: err.message,
          });
        }
      });
    return () => {
      cancelled = true;
    };
  }, [segment, location]);

  return state;
};
