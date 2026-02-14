"use client";

import Sidebar from "@/components/Sidebar";
import SimulatorView from "@/components/SimulatorView";
import { useState, useEffect } from "react";
import IntentInput from "@/components/IntentInput";
import RecommendationDashboard from "@/components/RecommendationDashboard";
import AuthForm from "@/components/AuthForm";
import { TrendingUp, User, LogOut, AlertTriangle, RefreshCw, Database } from "lucide-react";
import { authService } from "@/services/auth";
import { recommendationService, DataStatusResponse, RebalancingAlert, getRebalancingAlerts, RecommendationResponse } from "@/services/recommendation";

export default function Home() {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [user, setUser] = useState<{ name: string; email: string } | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [recommendation, setRecommendation] = useState<RecommendationResponse | null>(null);
  const [authError, setAuthError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState("recommendation");
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(false);
  
  // Estados para verificação de dados
  const [dataStatus, setDataStatus] = useState<DataStatusResponse | null>(null);
  const [rebalancingAlerts, setRebalancingAlerts] = useState<RebalancingAlert[]>([]);
  const [showDataAlert, setShowDataAlert] = useState(false);
  const [isUpdatingData, setIsUpdatingData] = useState(false);

  // Verificar token e status dos dados ao carregar
  useEffect(() => {
    const token = authService.getToken();
    if (token) {
      authService.getCurrentUser()
        .then((userData) => {
          setUser({ name: userData.name, email: userData.email });
          setIsAuthenticated(true);
          // Verificar status dos dados após login
          checkDataStatus();
        })
        .catch(() => {
          authService.removeToken();
        });
    }
  }, []);

  // Verificar status dos dados
  const checkDataStatus = async () => {
    try {
      const status = await recommendationService.getDataStatus();
      setDataStatus(status);
      // Mostrar alerta se dados estiverem desatualizados
      if (status.status === 'stale') {
        setShowDataAlert(true);
      }
    } catch (error) {
      console.error('Erro ao verificar status dos dados:', error);
    }
  };

  // Atualizar dados manualmente
  const handleUpdateData = async () => {
    setIsUpdatingData(true);
    try {
      await recommendationService.updateData();
      // Aguardar um pouco e verificar novamente
      setTimeout(async () => {
        await checkDataStatus();
        setIsUpdatingData(false);
      }, 3000);
    } catch (error: unknown) {
      const err = error as { response?: { data?: { detail?: string } } };
      setAuthError(err.response?.data?.detail || "Erro ao atualizar dados");
      setIsUpdatingData(false);
    }
  };

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
      const [data, alertsData] = await Promise.all([
        recommendationService.getRecommendation(prompt),
        getRebalancingAlerts().catch(() => ({ alerts: [], count: 0, has_urgent: false }))
      ]);
      setRecommendation(data);
      setRebalancingAlerts(alertsData.alerts);
    } catch (error: unknown) {
      const err = error as { response?: { data?: { detail?: string } } };
      setAuthError(err.response?.data?.detail || "Erro ao gerar recomendação");
    } finally {
      setIsLoading(false);
    }
  };

  if (!isAuthenticated) {
    return (
      <main className="min-h-screen bg-background flex items-center justify-center p-4">
        <div className="w-full max-w-4xl">
          <div className="text-center mb-8">
            <div className="inline-flex items-center gap-3 mb-4">
              <div className="w-12 h-12 rounded-xl bg-(--gradient-primary) flex items-center justify-center">
                <TrendingUp className="w-7 h-7 text-white" />
              </div>
              <span className="text-2xl font-bold text-(--text-primary)">Smart Invest</span>
            </div>
            <p className="text-(--text-muted)">Motor quantitativo adaptativo orientado por intenção</p>
          </div>
          <AuthForm onLogin={handleLogin} onRegister={handleRegister} isLoading={isLoading} error={authError} />
          <p className="text-center mt-8 text-sm text-(--text-muted)">Demo: demo@smartinvest.com / demo123</p>
        </div>
      </main>
    );
  }

  return (
    <main className="min-h-screen bg-background flex text-(--text-primary)">
      <Sidebar 
        activeTab={activeTab} 
        onTabChange={setActiveTab} 
        isCollapsed={isSidebarCollapsed} 
        setIsCollapsed={setIsSidebarCollapsed} 
      />
      
      <div className={`flex-1 transition-all duration-300 ${isSidebarCollapsed ? 'ml-20' : 'ml-64'}`}>
        <header className="glass-card border-b border-(--primary-muted) sticky top-0 z-40 bg-(--background)/80 backdrop-blur-md">
          <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
            <h1 className="text-xl font-bold gradient-text uppercase tracking-wider">
              {activeTab === 'recommendation' ? 'Inteligência de Mercado' : 
               activeTab === 'simulator' ? 'Simulador de Operações' : 
               activeTab === 'portfolio' ? 'Minha Carteira Real' : 'Histórico'}
            </h1>
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2 text-text-secondary">
              <div className="w-8 h-8 rounded-full bg-primary-muted flex items-center justify-center">
                <User className="w-4 h-4 text-primary-light" />
              </div>
              <span className="text-sm hidden sm:inline">{user?.name}</span>
            </div>
            <button onClick={handleLogout} className="p-2 rounded-lg hover:bg-surface-light text-text-muted hover:text-error transition-colors">
              <LogOut className="w-5 h-5" />
            </button>
          </div>
          </div>
        </header>

        <div className="max-w-7xl mx-auto px-6 py-8">
          {activeTab === 'recommendation' && (
            <>
              {/* Alerta de dados desatualizados */}
              {showDataAlert && dataStatus && (
                <div className="mb-6 p-4 rounded-xl bg-(--warning)/10 border border-(--warning)/30 flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <AlertTriangle className="w-5 h-5 text-(--warning)" />
                    <div>
                      <p className="text-sm font-medium text-(--warning)">
                        Dados desatualizados
                      </p>
                      <p className="text-xs text-(--text-muted)">
                        Última atualização: {dataStatus.prices_date || 'desconhecida'} · 
                        Recomendado atualizar para dados de hoje ({dataStatus.today})
                      </p>
                    </div>
                  </div>
                  <button
                    onClick={handleUpdateData}
                    disabled={isUpdatingData}
                    className="flex items-center gap-2 px-4 py-2 rounded-lg bg-(--warning)/20 hover:bg-(--warning)/30 text-(--warning) text-sm font-medium transition-colors disabled:opacity-50"
                  >
                    {isUpdatingData ? (
                      <>
                        <RefreshCw className="w-4 h-4 animate-spin" />
                        Atualizando...
                      </>
                    ) : (
                      <>
                        <Database className="w-4 h-4" />
                        Atualizar agora
                      </>
                    )}
                  </button>
                </div>
              )}

              <section className="mb-12">
                <IntentInput onSubmit={handleIntentSubmit} isLoading={isLoading} />
              </section>
              <section>
                <RecommendationDashboard data={recommendation} isLoading={isLoading} alerts={rebalancingAlerts} />
              </section>
            </>
          )}

          {activeTab === 'simulator' && (
            <SimulatorView />
          )}

          {activeTab === 'portfolio' && (
            <SimulatorView isReal={true} />
          )}
        </div>
      </div>
    </main>
  );
}
