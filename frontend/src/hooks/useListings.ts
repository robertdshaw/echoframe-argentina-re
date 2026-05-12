import { useEffect, useState } from 'react';
import { marketApi } from '../api/client';
import type { PropertyListing, Segment } from '../types';

interface State {
  listings: PropertyListing[];
  avg_price: number;
  loading: boolean;
  error: string | null;
}

export const useListings = (
  segment: Segment,
  location?: string,
  limit = 100,
): State => {
  const [state, setState] = useState<State>({
    listings: [],
    avg_price: 0,
    loading: true,
    error: null,
  });

  useEffect(() => {
    let cancelled = false;
    setState((s) => ({ ...s, loading: true, error: null }));
    marketApi
      .getListings(segment, { location, limit })
      .then((data) => {
        if (cancelled) return;
        setState({
          listings: data.listings,
          avg_price: data.avg_price,
          loading: false,
          error: null,
        });
      })
      .catch((err: Error) => {
        if (cancelled) return;
        setState({
          listings: [],
          avg_price: 0,
          loading: false,
          error: err.message,
        });
      });
    return () => {
      cancelled = true;
    };
  }, [segment, location, limit]);

  return state;
};
