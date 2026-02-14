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
  n_positions: number;
  total_weight: number;
  sector_exposure?: Record<string, number>;
  diversification_score?: number;
  data_date?: string;
  sentiment?: SentimentResponse;
  holdings: Array<{
    ticker: string;
    weight: number;
    score?: number;
    sector?: string;
    p_l?: number;
    dy?: number;
  }>;
}

export interface DataStatusResponse {
  status: 'fresh' | 'stale';
  prices_date: string;
  scores_date: string;
  today: string;
  prices_count: number;
  scores_count: number;
  message: string;
}

export interface UpdateDataResponse {
  status: 'started';
  message: string;
  pid: number;
  estimated_time: string;
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

  async getRecommendation(prompt: string): Promise<RecommendationResponse> {
    // Buscar carteira e sentimento em paralelo
    const [portfolioResponse, sentiment] = await Promise.all([
      apiClient.post('/portfolio/build?n_positions=10&strategy=score_weighted&name=SmartPortfolio', { prompt }),
      this.getSentiment().catch(() => undefined) // Fallback se sentimento falhar
    ]);
    
    return {
      ...portfolioResponse.data,
      sentiment
    };
  }
};
