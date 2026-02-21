"use client";

import Sidebar from "@/components/Sidebar";
import SimulatorView from "@/components/SimulatorView";
import HistoryView from "@/components/HistoryView";
import { useState, useEffect } from "react";
import IntentInput from "@/components/IntentInput";
import RecommendationDashboard from "@/components/RecommendationDashboard";
import AssetInsightCard from "@/components/AssetInsightCard";
import AuthForm from "@/components/AuthForm";
import SettingsView from "@/components/SettingsView";
import { TrendingUp, User, LogOut, AlertTriangle, RefreshCw, Database } from "lucide-react";
import { authService, TenantProfile } from "@/services/auth";
import {
  recommendationService,
  DataStatusResponse,
  RebalancingAlert,
  getRebalancingAlerts,
  RecommendationResponse,
  AssetInsightResponse,
  PromptRouteResponse,
} from "@/services/recommendation";
import { simulationService } from "@/services/simulation";

export default function Home() {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [user, setUser] = useState<{ name: string; email: string } | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [recommendation, setRecommendation] = useState<RecommendationResponse | null>(null);
  const [assetInsight, setAssetInsight] = useState<AssetInsightResponse | null>(null);
  const [authError, setAuthError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState("recommendation");
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(false);
  const [tenantProfile, setTenantProfile] = useState<TenantProfile | null>(null);

  const [dataStatus, setDataStatus] = useState<DataStatusResponse | null>(null);
  const [rebalancingAlerts, setRebalancingAlerts] = useState<RebalancingAlert[]>([]);
  const [showDataAlert, setShowDataAlert] = useState(false);
  const [isUpdatingData, setIsUpdatingData] = useState(false);
  const [uiMessage, setUiMessage] = useState<{ tone: "info" | "success" | "error"; text: string } | null>(null);
  const [assetRequestPrompt, setAssetRequestPrompt] = useState<string | null>(null);
  const [showOutOfScopeShortcuts, setShowOutOfScopeShortcuts] = useState(false);
  const [disambiguationState, setDisambiguationState] = useState<{
    prompt: string;
    detectedTicker?: string | null;
    options: Array<{ id: "asset_query" | "portfolio"; label: string }>;
  } | null>(null);

  useEffect(() => {
    const token = authService.getToken();
    if (!token) return;

    Promise.all([authService.getCurrentUser(), authService.getTenantProfile().catch(() => null)])
      .then(([userData, profile]) => {
        setUser({ name: userData.name, email: userData.email });
        setTenantProfile(profile);
        setIsAuthenticated(true);
        checkDataStatus();
      })
      .catch(() => {
        authService.removeToken();
      });
  }, []);

  useEffect(() => {
    if (!tenantProfile) return;
    const features = tenantProfile.features;
    if (activeTab === "history" && !features.allow_history) {
      setActiveTab("recommendation");
    }
  }, [activeTab, tenantProfile]);

  useEffect(() => {
    setUiMessage(null);
    setAssetRequestPrompt(null);
    setShowOutOfScopeShortcuts(false);
    setDisambiguationState(null);
  }, [activeTab]);

  const checkDataStatus = async () => {
    try {
      const status = await recommendationService.getDataStatus();
      setDataStatus(status);
      if (status.status === "stale") setShowDataAlert(true);
    } catch (error) {
      console.error("Erro ao verificar status dos dados:", error);
    }
  };

  const handleUpdateData = async () => {
    setIsUpdatingData(true);
    try {
      await recommendationService.updateData();
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
      const profile = await authService.getTenantProfile().catch(() => null);
      setTenantProfile(profile);
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
      const profile = await authService.getTenantProfile().catch(() => null);
      setTenantProfile(profile);
      setIsAuthenticated(true);
    } catch (error: unknown) {
      const err = error as { response?: { data?: { detail?: string } } };
      setAuthError(err.response?.data?.detail || "Erro ao criar conta");
    } finally {
      setIsLoading(false);
    }
  };

  const handleLogout = async () => {
    await authService.logout();
    setIsAuthenticated(false);
    setUser(null);
    setTenantProfile(null);
    setRecommendation(null);
    setAssetInsight(null);
  };

  const handleIntentSubmit = async (prompt: string) => {
    setIsLoading(true);
    setUiMessage(null);
    setAssetRequestPrompt(null);
    setShowOutOfScopeShortcuts(false);
    setDisambiguationState(null);
    try {
      const route: PromptRouteResponse = await recommendationService.routePrompt(prompt);

      if (route.route === "out_of_scope") {
        setUiMessage({ tone: "info", text: route.safe_response });
        setShowOutOfScopeShortcuts(route.reason !== "intencao ambigua entre ativo e carteira");
        if (route.reason === "intencao ambigua entre ativo e carteira" && route.disambiguation_options?.length) {
          setDisambiguationState({
            prompt,
            detectedTicker: route.detected_ticker,
            options: route.disambiguation_options,
          });
        }
        setAssetInsight(null);
        setRecommendation(null);
        setRebalancingAlerts([]);
        setAssetRequestPrompt(null);
        return;
      }

      if (route.route === "asset_query") {
        const insight = await recommendationService.getAssetInsight(prompt);
        setAssetInsight(insight);
        setRecommendation(null);
        setRebalancingAlerts([]);
        setShowOutOfScopeShortcuts(false);
        return;
      }

      const [data, alertsData] = await Promise.all([
        recommendationService.getRecommendation(prompt),
        getRebalancingAlerts().catch(() => ({ alerts: [], count: 0, has_urgent: false })),
      ]);
      setRecommendation(data);
      setAssetInsight(null);
      setRebalancingAlerts(alertsData.alerts);
      setAssetRequestPrompt(null);
      setShowOutOfScopeShortcuts(false);
    } catch (error: unknown) {
      const err = error as {
        response?: {
          data?: {
            detail?:
              | string
              | {
                  code?: string;
                  message?: string;
                  didactic_message?: string;
                  suggestions?: Array<{ ticker?: string }>;
                };
          };
        };
      };
      const detail = err.response?.data?.detail;

      if (typeof detail === "object" && detail) {
        const suggestions = (detail.suggestions || [])
          .map((s) => s.ticker)
          .filter(Boolean)
          .slice(0, 5)
          .join(", ");
        const baseMessage = detail.didactic_message || detail.message || "Não foi possível processar sua consulta.";
        const finalMessage = suggestions ? `${baseMessage} Sugestões: ${suggestions}.` : baseMessage;
        setUiMessage({ tone: "error", text: finalMessage });
        if (detail.code === "ASSET_NOT_FOUND") {
          setAssetRequestPrompt(prompt);
        }
      } else {
        setUiMessage({ tone: "error", text: (typeof detail === "string" && detail) || "Erro ao gerar recomendação." });
        setAssetRequestPrompt(null);
      }

      setAssetInsight(null);
      setRecommendation(null);
      setRebalancingAlerts([]);
      setShowOutOfScopeShortcuts(false);
    } finally {
      setIsLoading(false);
    }
  };

  const handleOutOfScopeShortcut = async (action: "conservative" | "income" | "simulator") => {
    if (action === "simulator") {
      setActiveTab("simulator");
      setUiMessage(null);
      setShowOutOfScopeShortcuts(false);
      return;
    }

    const prompt =
      action === "conservative"
        ? "quero proteger meu capital de forma conservadora"
        : "quero renda passiva com dividendos";
    await handleIntentSubmit(prompt);
  };

  const handleDisambiguationSelect = async (choice: "asset_query" | "portfolio") => {
    if (!disambiguationState) return;
    setIsLoading(true);
    setUiMessage(null);
    setAssetRequestPrompt(null);
    try {
      if (choice === "asset_query") {
        const promptForAsset = disambiguationState.detectedTicker
          ? `como esta ${disambiguationState.detectedTicker} hoje?`
          : disambiguationState.prompt;
        const insight = await recommendationService.getAssetInsight(promptForAsset);
        setAssetInsight(insight);
        setRecommendation(null);
        setRebalancingAlerts([]);
      } else {
        const [data, alertsData] = await Promise.all([
          recommendationService.getRecommendation(disambiguationState.prompt),
          getRebalancingAlerts().catch(() => ({ alerts: [], count: 0, has_urgent: false })),
        ]);
        setRecommendation(data);
        setAssetInsight(null);
        setRebalancingAlerts(alertsData.alerts);
      }
      setDisambiguationState(null);
    } catch (error: unknown) {
      const err = error as { response?: { data?: { detail?: string } }; message?: string };
      setUiMessage({
        tone: "error",
        text: err.response?.data?.detail || err.message || "Nao foi possivel seguir com a opcao escolhida.",
      });
    } finally {
      setIsLoading(false);
    }
  };

  const handleAddToSimulationFromInsight = async (ticker: string, quantity: number) => {
    try {
      await simulationService.createOrder(ticker, "BUY", quantity);
      setActiveTab("simulator");
      setUiMessage({ tone: "success", text: `Compra simulada registrada: ${ticker} (${quantity}).` });
    } catch (error: unknown) {
      const err = error as { response?: { data?: { detail?: string } }; message?: string };
      const detail = err.response?.data?.detail || err.message || "falha desconhecida";
      setUiMessage({ tone: "error", text: "Erro ao adicionar no simulador: " + detail });
      throw error;
    }
  };

  const handleRequestAssetInclusion = async () => {
    if (!assetRequestPrompt) return;
    try {
      const response = await recommendationService.requestAssetInclusion(assetRequestPrompt);
      setUiMessage({ tone: "success", text: response.message });
      setAssetRequestPrompt(null);
    } catch (error: unknown) {
      const err = error as { response?: { data?: { detail?: string } } };
      setUiMessage({
        tone: "error",
        text: err.response?.data?.detail || "Não foi possível registrar a solicitação agora.",
      });
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
            <p className="text-(--text-muted)">Motor quantitativo adaptativo orientado por intencao</p>
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
        features={
          tenantProfile
            ? {
                allow_real_portfolio: tenantProfile.features.allow_real_portfolio,
                allow_history: tenantProfile.features.allow_history,
              }
            : undefined
        }
      />

      <div className={`flex-1 transition-all duration-300 ${isSidebarCollapsed ? "ml-20" : "ml-64"}`}>
        <header className="glass-card border-b border-(--primary-muted) sticky top-0 z-40 bg-(--background)/80 backdrop-blur-md">
          <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
            <h1 className="text-xl font-bold gradient-text uppercase tracking-wider">
              {activeTab === "recommendation"
                ? "Inteligencia de Mercado"
                : activeTab === "simulator"
                  ? "Simulador de Operacoes"
                  : activeTab === "portfolio"
                    ? "Minha Carteira Real"
                    : activeTab === "history"
                      ? "Historico"
                      : "Configuracoes"}
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
          {activeTab === "recommendation" && (
            <>
              {uiMessage && (
                <div
                  className={`mb-6 p-4 rounded-xl border text-sm ${
                    uiMessage.tone === "success"
                      ? "bg-emerald-500/10 border-emerald-500/30 text-emerald-300"
                      : uiMessage.tone === "error"
                        ? "bg-red-500/10 border-red-500/30 text-red-300"
                        : "bg-surface border-surface-light text-(--text-secondary)"
                  }`}
                >
                  <div>{uiMessage.text}</div>
                  {disambiguationState && uiMessage.tone === "info" && (
                    <div className="mt-3 flex flex-wrap gap-2">
                      {disambiguationState.options.map((opt) => (
                        <button
                          key={opt.id}
                          onClick={() => handleDisambiguationSelect(opt.id)}
                          className="px-3 py-1.5 rounded-lg bg-primary/20 hover:bg-primary/30 text-primary-light transition-colors"
                        >
                          {opt.label}
                        </button>
                      ))}
                    </div>
                  )}
                  {showOutOfScopeShortcuts && uiMessage.tone === "info" && !disambiguationState && (
                    <div className="mt-3 flex flex-wrap gap-2">
                      <button
                        onClick={() => handleOutOfScopeShortcut("conservative")}
                        className="px-3 py-1.5 rounded-lg bg-primary/20 hover:bg-primary/30 text-primary-light transition-colors"
                      >
                        Montar carteira conservadora
                      </button>
                      <button
                        onClick={() => handleOutOfScopeShortcut("income")}
                        className="px-3 py-1.5 rounded-lg bg-primary/20 hover:bg-primary/30 text-primary-light transition-colors"
                      >
                        Buscar renda passiva
                      </button>
                      <button
                        onClick={() => handleOutOfScopeShortcut("simulator")}
                        className="px-3 py-1.5 rounded-lg bg-surface-light hover:bg-surface text-(--text-secondary) transition-colors"
                      >
                        Ir para simulador
                      </button>
                    </div>
                  )}
                  {uiMessage.tone === "error" && assetRequestPrompt && (
                    <button
                      onClick={handleRequestAssetInclusion}
                      className="mt-3 px-3 py-1.5 rounded-lg bg-primary/20 hover:bg-primary/30 text-primary-light transition-colors"
                    >
                      Solicitar inclusão desse ativo
                    </button>
                  )}
                </div>
              )}

              {showDataAlert && dataStatus && (
                <div className="mb-6 p-4 rounded-xl bg-(--warning)/10 border border-(--warning)/30 flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <AlertTriangle className="w-5 h-5 text-(--warning)" />
                    <div>
                      <p className="text-sm font-medium text-(--warning)">Dados desatualizados</p>
                      <p className="text-xs text-(--text-muted)">
                        Ultima atualizacao: {dataStatus.prices_date || "desconhecida"} - Cobertura de sinais:{" "}
                        {dataStatus.active_universe
                          ? `${dataStatus.scores_count}/${dataStatus.active_universe}`
                          : dataStatus.scores_count}
                        {" "}({((dataStatus.scores_coverage || 0) * 100).toFixed(0)}%) - hoje: {dataStatus.today}
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
                <div className="space-y-6">
                  <AssetInsightCard
                    data={assetInsight}
                    isLoading={isLoading && !recommendation}
                    onAddToSimulation={handleAddToSimulationFromInsight}
                  />
                  {(recommendation || (isLoading && !assetInsight)) && (
                    <RecommendationDashboard
                      data={recommendation}
                      isLoading={isLoading && !assetInsight}
                      alerts={rebalancingAlerts}
                      onAddedToSimulation={() => setActiveTab("simulator")}
                    />
                  )}
                </div>
              </section>
            </>
          )}

          {activeTab === "simulator" && <SimulatorView />}

          {activeTab === "portfolio" && (
            <SimulatorView
              isReal={true}
              realAccessAllowed={tenantProfile?.features.allow_real_portfolio !== false}
            />
          )}

          {activeTab === "history" && <HistoryView />}

          {activeTab === "settings" && <SettingsView tenantProfile={tenantProfile} />}
        </div>
      </div>
    </main>
  );
}

