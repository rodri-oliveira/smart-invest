import { apiClient } from './api';

export interface RecommendationResponse {
  portfolio_id: number;
  name: string;
  strategy: string;
  n_positions: number;
  total_weight: number;
  holdings: Array<{
    ticker: string;
    weight: number;
    score?: number;
    sector?: string;
  }>;
}

export const recommendationService = {
  async getRecommendation(prompt: string): Promise<RecommendationResponse> {
    // Usar a API real de construção de portfolio
    const response = await apiClient.post('/portfolio/build?n_positions=10&strategy=score_weighted&name=SmartPortfolio');
    return response.data;
  }
};
