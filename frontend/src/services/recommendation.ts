import { apiClient } from './api';

export interface SentimentResponse {
  date: string;
  score: number;
  label: string;
  confidence: number;
  components: {
    macro: number;
    technical: number;
    volatility: number;
  };
}

export interface RecommendationResponse {
  portfolio_id: number;
  name: string;
  strategy: string;
  objective?: string;
  user_regime?: string;
  max_sector_exposure?: number;
  target_rv_allocation?: number;
  allocation_gap?: number;
  allocation_note?: string;
  n_positions: number;
  total_weight: number;
  sector_exposure?: Record<string, number>;
  diversification_score?: number;
  data_date?: string;
  sentiment?: SentimentResponse;
  holdings: Array<{
    ticker: string;
    asset_name?: string;
    weight: number;
    score?: number;
    sector?: string;
    segment?: string;
    p_l?: number;
    dy?: number;
    current_price?: number;
    price_date?: string;
  }>;
}

export interface DataStatusResponse {
  status: 'fresh' | 'stale';
  prices_date: string;
  scores_date: string;
  today: string;
  prices_count: number;
  scores_count: number;
  active_universe?: number;
  prices_coverage?: number;
  scores_coverage?: number;
  days_since_prices?: number | null;
  message: string;
}

export interface UpdateDataResponse {
  status: 'started' | 'running';
  message: string;
  pid: number;
  estimated_time: string;
}

export interface UpdateStatusResponse {
  status: 'idle' | 'running' | 'finished' | 'failed';
  message: string;
  pid?: number;
  started_at?: string;
  finished_at?: string;
  exit_code?: number;
}

export interface RebalancingAlert {
  type: string;
  ticker: string;
  message: string;
  priority: number;
  priority_label: string;
  suggested_action: string;
  timestamp: string;
}

export interface RebalancingAlertsResponse {
  alerts: RebalancingAlert[];
  count: number;
  has_urgent: boolean;
  timestamp: string;
}

export interface AssetInsightResponse {
  mode: 'asset_query';
  ticker: string;
  name?: string;
  sector?: string;
  latest_price: number;
  latest_date: string;
  change_1d_pct: number;
  change_7d_pct: number;
  change_30d_pct: number;
  score_final?: number | null;
  risk_label: string;
  guidance: string;
  didactic_summary: string;
}

export interface PromptRouteResponse {
  route: 'portfolio' | 'asset_query' | 'out_of_scope';
  in_scope: boolean;
  reason: string;
  safe_response: string;
  confidence: number;
  detected_ticker?: string | null;
  disambiguation_options?: Array<{ id: 'asset_query' | 'portfolio'; label: string }>;
}

export interface AssetRequestResponse {
  status: 'created' | 'already_requested';
  message: string;
  request_id?: number | null;
}

export const getRebalancingAlerts = async (): Promise<RebalancingAlertsResponse> => {
  const response = await apiClient.get('/portfolio/alerts/rebalancing');
  return response.data;
};

export const recommendationService = {
  async getSentiment(): Promise<SentimentResponse> {
    const response = await apiClient.get('/recommendation/sentiment');
    return response.data;
  },

  async getDataStatus(): Promise<DataStatusResponse> {
    const response = await apiClient.get('/recommendation/data-status');
    return response.data;
  },

  async updateData(): Promise<UpdateDataResponse> {
    const response = await apiClient.post('/recommendation/update-data');
    return response.data;
  },

  async getUpdateStatus(): Promise<UpdateStatusResponse> {
    const response = await apiClient.get('/recommendation/update-status');
    return response.data;
  },

  async getRecommendation(prompt: string): Promise<RecommendationResponse> {
    // Buscar carteira e sentimento em paralelo
    const [portfolioResponse, sentiment] = await Promise.all([
      apiClient.post('/portfolio/build?n_positions=10&name=SmartPortfolio', { prompt }),
      this.getSentiment().catch(() => undefined) // Fallback se sentimento falhar
    ]);
    
    return {
      ...portfolioResponse.data,
      sentiment
    };
  },

  async getAssetInsight(prompt: string): Promise<AssetInsightResponse> {
    const response = await apiClient.post('/recommendation/asset-insight', { prompt });
    return response.data;
  },

  async routePrompt(prompt: string): Promise<PromptRouteResponse> {
    const response = await apiClient.post('/recommendation/route', { prompt });
    return response.data;
  },

  async requestAssetInclusion(prompt: string): Promise<AssetRequestResponse> {
    const response = await apiClient.post('/recommendation/asset-request', { prompt });
    return response.data;
  }
};
