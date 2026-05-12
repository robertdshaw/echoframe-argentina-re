import axios, { AxiosError } from 'axios';
import type {
  ForecastResponse,
  ForecastSummaryResponse,
  RegimeContext,
  ProcessedSignal,
  MacroIndicatorsResponse,
  ScenarioForecastResponse,
  ScenarioParameters,
  Segment,
  ModelInsightsResponse,
  PropertyListingsResponse,
  NarrativeResponse,
  NetReturnResponse,
  BarrioRankingsResponse,
  EntryQualityResponse,
  CanonicalScenariosResponse,
} from '../types';

const baseURL =
  (import.meta as unknown as { env: Record<string, string | undefined> }).env
    .VITE_API_URL || 'http://localhost:8000';

// Forecast + barrio-rankings + net-return endpoints chain through the
// model ensemble and an Argentine-data pipeline that can pull macro,
// news, and listings simultaneously. On a cold Render free-tier start
// the first request legitimately takes 30–50s before the in-memory
// cache warms; 30s was too tight and produced spurious timeout errors.
export const apiClient = axios.create({
  baseURL,
  timeout: 60000,
  headers: { 'Content-Type': 'application/json' },
});

apiClient.interceptors.response.use(
  (response) => response,
  (error: AxiosError) => {
    const message =
      (error.response?.data as { detail?: string })?.detail ?? error.message;
    return Promise.reject(new Error(message));
  },
);

export const forecastApi = {
  async getDepartamentos(barrio?: string): Promise<ForecastResponse> {
    const { data } = await apiClient.get<ForecastResponse>(
      '/api/v1/forecast/departamentos',
      { params: { barrio } },
    );
    return data;
  },

  async getCampos(zone?: string): Promise<ForecastResponse> {
    const { data } = await apiClient.get<ForecastResponse>(
      '/api/v1/forecast/campos',
      { params: { zone } },
    );
    return data;
  },

  async getSummary(): Promise<ForecastSummaryResponse> {
    const { data } = await apiClient.get<ForecastSummaryResponse>(
      '/api/v1/forecast/summary',
    );
    return data;
  },

  async getCurrentRegime(): Promise<RegimeContext> {
    const { data } = await apiClient.get<RegimeContext>(
      '/api/v1/forecast/regime/current',
    );
    return data;
  },

  async getNetReturnDepartamentos(barrio?: string): Promise<NetReturnResponse> {
    const { data } = await apiClient.get<NetReturnResponse>(
      '/api/v1/forecast/net-return/departamentos',
      { params: { barrio } },
    );
    return data;
  },

  async getBarrioRankings(): Promise<BarrioRankingsResponse> {
    const { data } = await apiClient.get<BarrioRankingsResponse>(
      '/api/v1/forecast/barrio-rankings/departamentos',
    );
    return data;
  },

  async getEntryQuality(): Promise<EntryQualityResponse> {
    const { data } = await apiClient.get<EntryQualityResponse>(
      '/api/v1/forecast/timing/entry-quality',
    );
    return data;
  },

  async getCanonicalScenarios(): Promise<CanonicalScenariosResponse> {
    const { data } = await apiClient.get<CanonicalScenariosResponse>(
      '/api/v1/forecast/scenarios/canonical/departamentos',
    );
    return data;
  },
};

export const signalsApi = {
  async getLatest(params: {
    limit?: number;
    segment?: Segment;
    minImpact?: number;
  } = {}): Promise<ProcessedSignal[]> {
    const { data } = await apiClient.get<ProcessedSignal[]>(
      '/api/v1/signals/latest',
      {
        params: {
          limit: params.limit ?? 20,
          segment: params.segment,
          min_impact: params.minImpact,
        },
      },
    );
    return data;
  },
};

export const marketApi = {
  async getMacro(): Promise<MacroIndicatorsResponse> {
    const { data } = await apiClient.get<MacroIndicatorsResponse>(
      '/api/v1/market/macro',
    );
    return data;
  },

  async getListings(
    segment: Segment,
    opts: { location?: string; limit?: number } = {},
  ): Promise<PropertyListingsResponse> {
    const { data } = await apiClient.get<PropertyListingsResponse>(
      `/api/v1/market/listings/${segment}`,
      { params: { location: opts.location, limit: opts.limit ?? 100 } },
    );
    return data;
  },
};

export const narrativeApi = {
  async generate(
    segment: Segment,
    location?: string,
  ): Promise<NarrativeResponse> {
    const { data } = await apiClient.post<NarrativeResponse>(
      '/api/v1/insights/narrative',
      { segment, location },
      { timeout: 60000 },
    );
    return data;
  },
};

export const modelApi = {
  async getInsights(): Promise<ModelInsightsResponse> {
    const { data } = await apiClient.get<ModelInsightsResponse>(
      '/api/v1/model/insights',
    );
    return data;
  },
};

export const scenariosApi = {
  async simulate(
    segment: Segment,
    parameters: ScenarioParameters,
  ): Promise<ScenarioForecastResponse> {
    const { data } = await apiClient.post<ScenarioForecastResponse>(
      '/api/v1/scenarios/simulate',
      {
        segment,
        scenario_params: parameters,
        include_baseline: true,
        year_horizons: [1, 2, 3],
      },
    );
    return data;
  },
};
