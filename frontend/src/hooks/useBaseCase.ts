import { useEffect, useState } from 'react';
import { marketApi } from '../api/client';

// "Base case" = the parameter values the model is currently using when
// it produces the un-modified forecast. The Scenario Explorer renders
// these as slider defaults plus a tick mark, so the user can see what
// they're overriding when they drag a slider.
export interface BaseCaseValue {
  value: number;
  source: string; // human-readable provenance, e.g. "REM consensus"
}

export interface BaseCase {
  inflation_target: BaseCaseValue;
  usd_ars_target: BaseCaseValue;
  mortgage_rate_adjustment: BaseCaseValue;
  retenciones_change: BaseCaseValue;
  news_sentiment_override: BaseCaseValue;
  gdp_growth_override: BaseCaseValue;
}

// Fallback used when the macro endpoint is unavailable. Same shape as
// REM/BCRA so the rest of the UI behaves identically.
const FALLBACK: BaseCase = {
  inflation_target: { value: 15.2, source: 'fallback' },
  usd_ars_target: { value: 1400, source: 'fallback' },
  mortgage_rate_adjustment: { value: 0, source: 'delta vs. current' },
  retenciones_change: { value: 0, source: 'delta vs. current' },
  news_sentiment_override: { value: 0, source: 'delta vs. current' },
  gdp_growth_override: { value: 4.5, source: 'fallback' },
};

interface State {
  baseCase: BaseCase;
  loading: boolean;
  error: string | null;
}

export const useBaseCase = (): State => {
  const [state, setState] = useState<State>({
    baseCase: FALLBACK,
    loading: true,
    error: null,
  });

  useEffect(() => {
    let cancelled = false;
    marketApi
      .getMacro()
      .then((data) => {
        if (cancelled) return;

        const inflation = data.rem?.inflation_forecast?.median;
        const usdArs =
          data.rem?.exchange_rate_forecast?.median ??
          data.bcra?.exchange_rate?.value;
        const gdp = data.rem?.gdp_forecast?.median;

        setState({
          baseCase: {
            inflation_target:
              inflation !== undefined && inflation !== null
                ? { value: inflation, source: 'REM consensus' }
                : FALLBACK.inflation_target,
            usd_ars_target:
              usdArs !== undefined && usdArs !== null
                ? {
                    value: usdArs,
                    source: data.rem?.exchange_rate_forecast
                      ? 'REM consensus'
                      : 'BCRA spot',
                  }
                : FALLBACK.usd_ars_target,
            mortgage_rate_adjustment: FALLBACK.mortgage_rate_adjustment,
            retenciones_change: FALLBACK.retenciones_change,
            news_sentiment_override: FALLBACK.news_sentiment_override,
            gdp_growth_override:
              gdp !== undefined && gdp !== null
                ? { value: gdp, source: 'REM consensus' }
                : FALLBACK.gdp_growth_override,
          },
          loading: false,
          error: null,
        });
      })
      .catch((err: Error) => {
        if (cancelled) return;
        setState({ baseCase: FALLBACK, loading: false, error: err.message });
      });
    return () => {
      cancelled = true;
    };
  }, []);

  return state;
};
