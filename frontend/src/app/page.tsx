"use client";

import { useState, useEffect } from "react";
import IntentInput from "@/components/IntentInput";
import RecommendationDashboard from "@/components/RecommendationDashboard";
import AuthForm from "@/components/AuthForm";
import { TrendingUp, User, LogOut } from "lucide-react";
import { authService } from "@/services/auth";
import { recommendationService } from "@/services/recommendation";

export default function Home() {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [user, setUser] = useState<{ name: string; email: string } | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [recommendation, setRecommendation] = useState<any>(null);
  const [authError, setAuthError] = useState<string | null>(null);

  // Verificar token ao carregar
  useEffect(() => {
    const token = authService.getToken();
    if (token) {
      authService.getCurrentUser()
        .then((userData) => {
          setUser({ name: userData.name, email: userData.email });
          setIsAuthenticated(true);
        })
        .catch(() => {
          authService.removeToken();
        });
    }
  }, []);

  const handleLogin = async (email: string, password: string) => {
    setAuthError(null);
    setIsLoading(true);
    try {
      const response = await authService.login(email, password);
      authService.setToken(response.access_token);
      setUser({ name: response.user.name, email: response.user.email });
      setIsAuthenticated(true);
    } catch (error: unknown) {
      const err = error as { response?: { data?: { detail?: string } } };
      setAuthError(err.response?.data?.detail || "Erro ao fazer login");
    } finally {
      setIsLoading(false);
    }
  };

  const handleRegister = async (email: string, password: string, name: string) => {
    setAuthError(null);
    setIsLoading(true);
    try {
      await authService.register(email, password, name);
      const loginResponse = await authService.login(email, password);
      authService.setToken(loginResponse.access_token);
      setUser({ name: loginResponse.user.name, email: loginResponse.user.email });
      setIsAuthenticated(true);
    } catch (error: unknown) {
      const err = error as { response?: { data?: { detail?: string } } };
      setAuthError(err.response?.data?.detail || "Erro ao criar conta");
    } finally {
      setIsLoading(false);
    }
  };

  const handleLogout = () => {
    authService.removeToken();
    setIsAuthenticated(false);
    setUser(null);
    setRecommendation(null);
  };

  const handleIntentSubmit = async (prompt: string) => {
    setIsLoading(true);
    try {
      const data = await recommendationService.getRecommendation(prompt);
      setRecommendation(data);
    } catch (error: any) {
      setAuthError(error.response?.data?.detail || "Erro ao gerar recomendação");
    } finally {
      setIsLoading(false);
    }
  };

  if (!isAuthenticated) {
    return (
      <main className="min-h-screen bg-[var(--background)] flex items-center justify-center p-4">
        <div className="w-full max-w-4xl">
          <div className="text-center mb-8">
            <div className="inline-flex items-center gap-3 mb-4">
              <div className="w-12 h-12 rounded-xl bg-[var(--gradient-primary)] flex items-center justify-center">
                <TrendingUp className="w-7 h-7 text-white" />
              </div>
              <span className="text-2xl font-bold text-[var(--text-primary)]">Smart Invest</span>
            </div>
            <p className="text-[var(--text-muted)]">Motor quantitativo adaptativo orientado por intenção</p>
          </div>
          <AuthForm onLogin={handleLogin} onRegister={handleRegister} isLoading={isLoading} error={authError} />
          <p className="text-center mt-8 text-sm text-[var(--text-muted)]">Demo: demo@smartinvest.com / demo123</p>
        </div>
      </main>
    );
  }

  return (
    <main className="min-h-screen bg-[var(--background)]">
      <header className="glass-card border-b border-[var(--primary-muted)]">
        <div className="max-w-7xl mx-auto px-4 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-[var(--gradient-primary)] flex items-center justify-center">
              <TrendingUp className="w-6 h-6 text-white" />
            </div>
            <span className="text-xl font-bold gradient-text">Smart Invest</span>
          </div>
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2 text-[var(--text-secondary)]">
              <div className="w-8 h-8 rounded-full bg-[var(--primary-muted)] flex items-center justify-center">
                <User className="w-4 h-4 text-[var(--primary-light)]" />
              </div>
              <span className="text-sm hidden sm:inline">{user?.name}</span>
            </div>
            <button onClick={handleLogout} className="p-2 rounded-lg hover:bg-[var(--surface-light)] text-[var(--text-muted)] hover:text-[var(--error)] transition-colors">
              <LogOut className="w-5 h-5" />
            </button>
          </div>
        </div>
      </header>
      <div className="max-w-7xl mx-auto px-4 py-8">
        <section className="mb-12">
          <IntentInput onSubmit={handleIntentSubmit} isLoading={isLoading} />
        </section>
        <section>
          <RecommendationDashboard data={recommendation} isLoading={isLoading} />
        </section>
      </div>
    </main>
  );
}
