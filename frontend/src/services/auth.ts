import { apiClient } from './api';

export interface LoginResponse {
  access_token: string;
  token_type: string;
  user: {
    id: number;
    email: string;
    name: string;
  };
}

export interface TenantProfile {
  tenant_id: number;
  tenant_name?: string;
  tenant_slug?: string;
  plan_code: string;
  plan_name: string;
  limits: {
    max_simulated_positions: number;
  };
  features: {
    allow_real_portfolio: boolean;
    allow_history: boolean;
    allow_daily_plan: boolean;
  };
}

export interface AuditEvent {
  id: number;
  tenant_id: number;
  user_id?: number | null;
  event_type: string;
  severity: "INFO" | "WARN" | "ERROR";
  message: string;
  ip_address?: string | null;
  metadata?: string | null;
  created_at: string;
}

export interface AuditEventListResponse {
  items: AuditEvent[];
  total: number;
  limit: number;
  offset: number;
  has_more: boolean;
}

export const authService = {
  async login(email: string, password: string): Promise<LoginResponse> {
    const response = await apiClient.post('/auth/login', {
      email,
      password,
    });
    return response.data;
  },

  async register(email: string, password: string, name: string): Promise<{ message: string }> {
    const response = await apiClient.post('/auth/register', {
      email,
      password,
      name,
    });
    return response.data;
  },

  async getCurrentUser(): Promise<{ user_id: number; email: string; name: string }> {
    const response = await apiClient.get('/auth/me');
    return response.data;
  },

  async getTenantProfile(): Promise<TenantProfile> {
    const response = await apiClient.get('/auth/tenant-profile');
    return response.data;
  },

  async getRecentAuditEvents(params?: {
    limit?: number;
    offset?: number;
    event_type?: string;
    severity?: "INFO" | "WARN" | "ERROR";
    days?: number;
  }): Promise<AuditEventListResponse> {
    const response = await apiClient.get('/auth/audit/recent', { params });
    return response.data;
  },

  setToken(token: string): void {
    localStorage.setItem('token', token);
  },

  getToken(): string | null {
    return localStorage.getItem('token');
  },

  removeToken(): void {
    localStorage.removeItem('token');
  },

  async logout(): Promise<void> {
    try {
      await apiClient.post('/auth/logout');
    } catch {
      // Ignora falha de rede no logout remoto; limpeza local ainda ocorre.
    } finally {
      this.removeToken();
    }
  },
};
