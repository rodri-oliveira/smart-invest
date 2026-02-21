import axios from 'axios';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export interface SimulatedPosition {
  ticker: string;
  quantity: number;
  avg_price: number;
  total_cost: number;
  current_price: number;
  profit_loss: number;
  profit_loss_pct: number;
}

export interface OperationAlert {
  ticker: string;
  type: 'STOP_LOSS' | 'REBALANCE' | 'TAKE_PROFIT';
  severity: 'HIGH' | 'MEDIUM' | 'LOW';
  message: string;
  is_real: boolean;
}

export interface OrderHistoryItem {
  order_id: number;
  ticker: string;
  order_type: 'BUY' | 'SELL';
  quantity: number;
  price_at_order: number;
  order_date: string;
  is_real: boolean;
}

export interface DailyGuidanceItem {
  ticker: string;
  action: string;
  reason: string;
  risk_level: string;
  signal_score?: number | null;
  profit_loss_pct?: number | null;
}

export interface DailyPlan {
  generated_at: string;
  is_real: boolean;
  profile: string;
  summary: string;
  next_step: string;
  guidance: DailyGuidanceItem[];
}

export const simulationService = {
  async getPositions(isReal: boolean = false): Promise<SimulatedPosition[]> {
    const token = localStorage.getItem('token');
    const response = await axios.get(`${API_URL}/simulation/positions`, {
      params: { is_real: isReal },
      headers: { Authorization: `Bearer ${token}` }
    });
    return response.data;
  },

  async getAlerts(): Promise<OperationAlert[]> {
    const token = localStorage.getItem('token');
    const response = await axios.get(`${API_URL}/simulation/alerts`, {
      headers: { Authorization: `Bearer ${token}` }
    });
    return response.data;
  },

  async createOrder(ticker: string, orderType: 'BUY' | 'SELL', quantity: number, isReal: boolean = false, price?: number) {
    const token = localStorage.getItem('token');
    const response = await axios.post(`${API_URL}/simulation/order`, {
      ticker,
      order_type: orderType,
      quantity,
      is_real: isReal,
      price
    }, {
      headers: { Authorization: `Bearer ${token}` }
    });
    return response.data;
  },

  async getOrdersHistory(isReal?: boolean): Promise<OrderHistoryItem[]> {
    const token = localStorage.getItem('token');
    const response = await axios.get(`${API_URL}/simulation/orders`, {
      params: { is_real: isReal },
      headers: { Authorization: `Bearer ${token}` }
    });
    return response.data;
  },

  async getDailyPlan(isReal: boolean = false): Promise<DailyPlan> {
    const token = localStorage.getItem('token');
    const response = await axios.get(`${API_URL}/simulation/daily-plan`, {
      params: { is_real: isReal },
      headers: { Authorization: `Bearer ${token}` }
    });
    return response.data;
  },
};
