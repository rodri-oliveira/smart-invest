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

  setToken(token: string): void {
    localStorage.setItem('token', token);
  },

  getToken(): string | null {
    return localStorage.getItem('token');
  },

  removeToken(): void {
    localStorage.removeItem('token');
  },
};
