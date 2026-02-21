"use client";

import { useState } from "react";

import { 
  TrendingDown, 
  Shield, 
  AlertTriangle, 
  Target, 
  Zap, 
  BarChart3, 
  PieChart, 
  Activity, 
  Plus,
  CircleHelp
} from "lucide-react";
import { PieChart as RePieChart, Pie, Cell, ResponsiveContainer, Tooltip, Legend } from "recharts";
import { simulationService } from "@/services/simulation";
import TradeActionModal from "@/components/TradeActionModal";

interface Sentiment {
  score: number;
  label: string;
  confidence: number;
}

interface RebalancingAlert {
  type: string;
  ticker: string;
  message: string;
  priority: number;
  priority_label: string;
  suggested_action: string;
  timestamp: string;
}

interface RecommendationData {
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
  sentiment?: Sentiment;
}

interface RecommendationDashboardProps {
  data: RecommendationData | null;
  isLoading: boolean;
  alerts?: RebalancingAlert[];
  onAddedToSimulation?: (ticker: string, quantity: number) => void;
}

interface DidacticGuide {
  happened: string;
  why: string;
  now: string;
  risk: string;
}

function getStrategyExplanation(
  regime?: string,
  strategy?: string,
  objective?: string,
  totalWeight?: number,
  maxSectorExposure?: number,
  targetAllocation?: number
): { title: string; description: string } {
  // Detecta foco em renda pelo objetivo (preferencial) ou pelo nome da estrategia.
  const isIncomeObjective = objective?.toLowerCase() === 'income';
  const isIncomeStrategy = strategy?.toLowerCase().includes('income') || 
                           strategy?.toLowerCase().includes('dividend') ||
                           strategy?.toLowerCase().includes('renda');
  const isIncome = isIncomeObjective || isIncomeStrategy;
  const allocatedPct = ((totalWeight ?? 0) * 100).toFixed(1);
  const sectorLimitPct = ((maxSectorExposure ?? 0.35) * 100).toFixed(0);
  const targetPct = ((targetAllocation ?? totalWeight ?? 0) * 100).toFixed(1);

  switch (regime) {
    case 'RISK_ON_STRONG':
      return {
        title: 'Plano de alto crescimento',
        description: `Hoje a carteira esta com ${allocatedPct}% em acoes (meta ${targetPct}%). Isso pode aumentar retorno, mas tambem aumenta oscilacao. Limite por setor: ${sectorLimitPct}%.`,
      };
    case 'RISK_ON':
      return {
        title: 'Plano de crescimento',
        description: `A carteira esta com ${allocatedPct}% em acoes (meta ${targetPct}%), buscando valorizacao com risco controlado. Limite por setor: ${sectorLimitPct}%.`,
      };
    case 'RISK_OFF':
      return {
        title: 'Plano de preservacao de capital',
        description: `Objetivo principal: proteger patrimonio e reduzir sustos. Hoje a carteira esta com ${allocatedPct}% em acoes (meta ${targetPct}%), com limite por setor de ${sectorLimitPct}%.`,
      };
    case 'RISK_OFF_STRONG':
      return {
        title: 'Plano ultra conservador',
        description: `Modo de defesa. Exposicao em acoes de ${allocatedPct}% (meta ${targetPct}%) e limite de ${sectorLimitPct}% por setor para reduzir risco.`,
      };
    case 'TRANSITION':
    default:
      if (isIncome) {
        return {
          title: 'Plano de renda passiva',
          description: `Foco em dividendos e previsibilidade. A carteira esta com ${allocatedPct}% em acoes (meta ${targetPct}%) e limite de ${sectorLimitPct}% por setor.`,
        };
      }
      return {
        title: 'Plano equilibrado',
        description: `Busca equilibrio entre retorno e protecao. Exposicao em acoes: ${allocatedPct}% (meta ${targetPct}%). Limite por setor: ${sectorLimitPct}%.`,
      };
  }
}

function getFriendlyStrategyLabel(strategy: string, objective?: string): string {
  const base = (strategy || "").toLowerCase();
  if (objective?.toLowerCase() === "income") return "renda_passiva";
  if (base.includes("score_weighted")) return "crescimento";
  if (base.includes("risk_parity")) return "protecao";
  if (base.includes("equal_weight")) return "equilibrado";
  return strategy.replace(/_/g, " ");
}

function buildDidacticGuide(
  explanation: { title: string; description: string },
  totalWeight: number,
  hasSectorConcentration: boolean,
  alertsCount: number,
  objective?: string,
): DidacticGuide {
  const allocatedPct = (totalWeight * 100).toFixed(1);
  const inCashPct = ((1 - totalWeight) * 100).toFixed(1);
  const needsAttention = hasSectorConcentration || alertsCount > 0;
  const title = explanation.title.toLowerCase();
  const isProtection =
    objective?.toLowerCase() === "protection" ||
    title.includes("preservacao") ||
    title.includes("ultra conservador") ||
    title.includes("protecao");

  if (isProtection) {
    return {
      happened: `Hoje, de cada R$ 100, cerca de R$ ${allocatedPct} estao em acoes e R$ ${inCashPct} ficam em caixa para protecao.`,
      why: "Esse formato prioriza estabilidade e diminui o impacto das oscilacoes fortes do mercado.",
      now: needsAttention
        ? "Mantenha postura conservadora e ajuste apenas os ativos com alerta."
        : "Siga com disciplina. Reavalie aos poucos, sem pressa para aumentar risco.",
      risk: "Mesmo nesse plano, o valor pode oscilar. A meta e reduzir risco, nao eliminar risco.",
    };
  }

  return {
    happened: `Hoje, de cada R$ 100, cerca de R$ ${allocatedPct} estao alocados e R$ ${inCashPct} ficam em caixa.`,
    why: "Essa distribuicao tenta equilibrar oportunidade e protecao, usando regras de risco e diversificacao.",
    now: needsAttention
      ? "Priorize os alertas e evite aumentar posicao sem revisar risco no simulador."
      : "Mantenha a disciplina, acompanhe o plano diario e ajuste apenas com criterio.",
    risk: needsAttention
      ? "Ha sinais de atencao no momento. Movimentos sem controle podem aumentar perda."
      : "Mesmo em cenario estavel, retorno maior sempre vem com oscilacao e possibilidade de perda.",
  };
}

export default function RecommendationDashboard({ data, isLoading, alerts, onAddedToSimulation }: RecommendationDashboardProps) {
  const [selectedTicker, setSelectedTicker] = useState<string | null>(null);
  const [helpTicker, setHelpTicker] = useState<string | null>(null);
  const [isSubmittingModal, setIsSubmittingModal] = useState(false);
  const [feedback, setFeedback] = useState<string | null>(null);
  const strategyLabel = data ? getFriendlyStrategyLabel(data.strategy, data.objective) : "";
  const explanation = getStrategyExplanation(
    data?.user_regime,
    data?.strategy,
    data?.objective,
    data?.total_weight,
    data?.max_sector_exposure,
    data?.target_rv_allocation
  );

  if (isLoading) {
    return (
      <div className="w-full max-w-6xl mx-auto p-8">
        <div className="glass-card rounded-2xl p-12 text-center">
          <div className="animate-pulse">
            <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-(--primary-muted)"></div>
            <div className="h-4 bg-surface-light rounded w-48 mx-auto mb-2"></div>
            <div className="h-3 bg-surface-light rounded w-32 mx-auto"></div>
          </div>
          <p className="mt-6 text-(--text-secondary)">
            Analisando mercado e montando sua sugestao...
          </p>
        </div>
      </div>
    );
  }

  if (!data) {
    return (
      <div className="w-full max-w-6xl mx-auto p-8">
        <div className="glass-card rounded-2xl p-12 text-center">
          <Target className="w-16 h-16 mx-auto mb-4 text-(--primary-muted)" />
          <h2 className="text-xl font-semibold text-(--text-primary) mb-2">
            Nenhuma recomendacao ainda
          </h2>
          <p className="text-(--text-secondary)">
            Digite seu objetivo acima para gerar uma recomendacao personalizada.
          </p>
        </div>
      </div>
    );
  }

  // Apenas valores positivos entram no grafico.
  const pieData = data.holdings
    .filter(h => h.weight > 0.0001)
    .map((holding) => ({
      name: holding.ticker,
      value: Number((holding.weight * 100).toFixed(2)),
      score: holding.score || 0,
    }));

  const COLORS = [
    "#10b981", // primary
    "#34d399", // primary-light
    "#fbbf24", // accent
    "#059669", // primary-dark
    "#fcd34d", // accent-light
    "#065f46", // primary-muted
  ];

  // Limite dinamico vindo do backend (fallback 35%).
  const maxSectorLimit = data?.max_sector_exposure ?? 0.35;
  const sectorEntries = data?.sector_exposure ? Object.entries(data.sector_exposure) : [];
  const hasSectorConcentration = sectorEntries.some(([, weight]) => weight > maxSectorLimit);
  const targetAllocation = data?.target_rv_allocation;
  const allocationGap = typeof data?.allocation_gap === 'number'
    ? data.allocation_gap
    : (typeof targetAllocation === 'number' ? targetAllocation - data.total_weight : 0);
  const hasMaterialAllocationGap = allocationGap > 0.01;
  const targetReached = typeof targetAllocation === 'number' && Math.abs(allocationGap) <= 0.01;
  const didacticGuide = buildDidacticGuide(
    explanation,
    data.total_weight,
    hasSectorConcentration,
    alerts?.length || 0,
    data.objective,
  );

  const getTickerTooltip = (holding: RecommendationData["holdings"][number]) => {
    const company = holding.asset_name || holding.ticker;
    const sector = holding.sector ? `Setor: ${holding.sector}. ` : "";
    const segment = holding.segment ? `Segmento: ${holding.segment}. ` : "";
    return `Codigo ${holding.ticker}: etiqueta da empresa na bolsa. Empresa: ${company}. ${sector}${segment}Use + para testar no simulador antes de decidir.`;
  };

  const getTickerDescription = (holding: RecommendationData["holdings"][number]) => {
    const company = holding.asset_name || holding.ticker;
    const sector = holding.sector ? ` Atua no setor ${holding.sector.toLowerCase()}.` : "";
    const segment = holding.segment ? ` Segmento: ${holding.segment}.` : "";
    return `${holding.ticker} e acao da empresa ${company}.${sector}${segment}`;
  };

  const handleTradeConfirm = async ({ quantity }: { ticker: string; quantity: string }) => {
    if (!selectedTicker) return;
    const parsedQty = parseInt(quantity, 10);
    if (!Number.isFinite(parsedQty) || parsedQty <= 0) {
      setFeedback("Quantidade invalida. Use um numero inteiro maior que zero.");
      return;
    }
    try {
      setIsSubmittingModal(true);
      await simulationService.createOrder(selectedTicker, "BUY", parsedQty);
      onAddedToSimulation?.(selectedTicker, parsedQty);
      setFeedback(`Compra simulada de ${selectedTicker} registrada com sucesso.`);
      setSelectedTicker(null);
    } catch (err: unknown) {
      const error = err as { message?: string };
      setFeedback("Erro ao simular compra: " + (error.message || "falha desconhecida"));
    } finally {
      setIsSubmittingModal(false);
    }
  };

  return (
    <div className="w-full max-w-6xl mx-auto p-4 space-y-6">
      {/* Header */}
      <div className="glass-card rounded-2xl p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-2xl font-bold gradient-text">
            {data.name} ({strategyLabel})
          </h2>
          <div className="px-4 py-2 rounded-full text-sm font-semibold bg-warning/20 text-(--warning)">
            {data.n_positions} posicoes
          </div>
        </div>
        
        {/* Risk Metrics Cards */}
        <div className="grid grid-cols-2 md:grid-cols-5 gap-4 mt-6">
          <RiskCard 
            icon={<BarChart3 className="w-5 h-5" />}
            label="Posicoes"
            value={`${data.n_positions}`}
            color="var(--primary)"
          />
          <RiskCard 
            icon={<TrendingDown className="w-5 h-5" />}
            label="Peso Total"
            value={`${(data.total_weight * 100).toFixed(1)}%`}
            color="var(--warning)"
          />
          <RiskCard 
            icon={<Shield className="w-5 h-5" />}
            label="Plano"
            value={strategyLabel}
            color="var(--accent)"
          />
          {data.sentiment && (
            <RiskCard 
              icon={<Activity className="w-5 h-5" />}
              label="Sentimento"
              value={data.sentiment.label}
              color={data.sentiment.score > 0.3 ? "var(--success)" : data.sentiment.score < -0.3 ? "var(--error)" : "var(--warning)"}
            />
          )}
          <RiskCard 
            icon={<PieChart className="w-5 h-5" />}
            label="ID"
            value={`#${data.portfolio_id}`}
            color="var(--info)"
          />
        </div>
      </div>

      {/* Alertas de Rebalanceamento */}
      {alerts && alerts.length > 0 && (
        <div className="mb-6 space-y-3">
          <div className="flex items-center gap-2 mb-2">
            <AlertTriangle className="w-5 h-5 text-amber-400" />
            <h3 className="font-semibold text-(--text-primary)">
              Alertas de ajuste
            </h3>
            <span className="ml-auto text-xs px-2 py-1 rounded-full bg-amber-500/20 text-amber-400">
              {alerts.length} alerta{alerts.length > 1 ? 's' : ''}
            </span>
          </div>
          
          <div className="space-y-2">
            {alerts.slice(0, 3).map((alert, index) => (
              <div
                key={`${alert.ticker}-${index}`}
                className={`
                  p-3 rounded-xl border-l-4
                  ${alert.priority <= 2 ? 'border-l-red-500 bg-red-500/10' : 
                    alert.priority === 3 ? 'border-l-amber-500 bg-amber-500/10' : 
                    'border-l-blue-500 bg-blue-500/10'}
                `}
              >
                <div className="flex items-start justify-between">
                  <div className="flex items-center gap-2">
                    <span className="font-semibold text-(--text-primary)">
                      {alert.ticker}
                    </span>
                    <span className={`
                      text-xs px-1.5 py-0.5 rounded
                      ${alert.suggested_action === 'VENDER' ? 'bg-red-500/20 text-red-400' : 
                        alert.suggested_action === 'COMPRAR' ? 'bg-green-500/20 text-green-400' : 
                        'bg-blue-500/20 text-blue-400'}
                    `}>
                      {alert.suggested_action}
                    </span>
                  </div>
                  <span className="text-xs text-(--text-muted)">
                    {alert.priority_label}
                  </span>
                </div>
                <p className="text-sm text-(--text-secondary) mt-1">
                  {alert.message}
                </p>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="grid md:grid-cols-2 gap-6">
        {/* Allocation Chart */}
        <div className="glass-card rounded-2xl p-6">
          <h3 className="text-lg font-semibold text-(--text-primary) mb-4 flex items-center gap-2">
            <PieChart className="w-5 h-5 text-primary" />
            Alocacao sugerida
          </h3>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <RePieChart>
                <Pie
                  data={pieData}
                  cx="50%"
                  cy="50%"
                  innerRadius={60}
                  outerRadius={80}
                  paddingAngle={5}
                  dataKey="value"
                >
                  {pieData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip 
                  contentStyle={{
                    backgroundColor: "var(--surface)",
                    border: "1px solid var(--primary-muted)",
                    borderRadius: "8px",
                  }}
                  itemStyle={{ color: "var(--text-primary)" }}
                />
                <Legend 
                  verticalAlign="bottom" 
                  height={36}
                  iconType="circle"
                />
              </RePieChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Assets List */}
        <div className="glass-card rounded-2xl p-6">
          <h3 className="text-lg font-semibold text-(--text-primary) mb-4 flex items-center gap-2">
            <Zap className="w-5 h-5 text-accent" />
            Ativos Selecionados
          </h3>
          <div className="space-y-3">
            {data.holdings
              .filter(h => h.weight > 0.0001)
              .map((holding, index) => (
              <div
                key={holding.ticker}
                className="
                  flex items-center justify-between
                  p-3 rounded-xl
                  bg-surface
                  hover:bg-surface-light
                  transition-colors
                  group
                "
              >
                <div className="flex items-center gap-3">
                  <span className="
                    w-8 h-8 rounded-lg
                    flex items-center justify-center
                    text-sm font-bold
                    bg-(--primary-muted)
                    text-primary-light
                  ">
                    {index + 1}
                  </span>
                  <div className="flex flex-col">
                    <div className="flex items-center gap-1">
                      <span className="font-semibold text-(--text-primary)">
                        {holding.ticker}
                      </span>
                      <div className="relative">
                        <button
                          type="button"
                          onClick={() => setHelpTicker((prev) => (prev === holding.ticker ? null : holding.ticker))}
                          className="text-(--text-muted) hover:text-primary-light transition-colors cursor-help"
                          aria-label={`Ajuda sobre ${holding.ticker}`}
                        >
                          <CircleHelp className="w-3.5 h-3.5" />
                        </button>
                        <div
                          className={`
                            absolute left-0 top-6 z-20 w-72 rounded-md border border-surface-light
                            bg-(--surface) p-2 text-xs leading-relaxed text-(--text-secondary) shadow-lg
                            transition-opacity
                            ${helpTicker === holding.ticker ? "opacity-100 visible" : "opacity-0 invisible md:group-hover:visible md:group-hover:opacity-100"}
                          `}
                        >
                          <p>{getTickerTooltip(holding)}</p>
                        </div>
                      </div>
                    </div>
                    <span className="text-xs text-(--text-secondary) leading-relaxed">
                      {getTickerDescription(holding)}
                    </span>
                  </div>
                </div>
                <div className="text-right flex flex-col items-end gap-1">
                  {holding.current_price && (
                    <div className="flex items-center gap-2">
                      <button 
                        onClick={async (e) => {
                          e.stopPropagation();
                          setSelectedTicker(holding.ticker);
                        }}
                        className="p-1 rounded bg-(--primary-muted) text-primary-light hover:bg-primary hover:text-white transition-all"
                        title="Simular Compra"
                      >
                        <Plus className="w-3 h-3" />
                      </button>
                      <div className="text-sm font-bold text-(--text-primary)">
                        R$ {holding.current_price.toFixed(2)}
                      </div>
                    </div>
                  )}
                  <div className="text-sm font-bold text-primary-light">
                    {(holding.weight * 100).toFixed(1)}%
                  </div>
                  <div className="text-[10px] text-(--text-muted) uppercase">
                    Alocacao
                  </div>
                  {(holding.p_l || holding.dy) && (
                    <div className="flex gap-2 mt-1 justify-end">
                      {holding.p_l && (
                        <span className="text-[10px] px-1.5 py-0.5 rounded bg-surface text-(--text-secondary)" title="Preco/Lucro">
                          P/L: {holding.p_l.toFixed(1)}
                        </span>
                      )}
                      {holding.dy && (
                        <span className="text-[10px] px-1.5 py-0.5 rounded bg-surface text-(--success)" title="Dividend Yield">
                          DY: {(holding.dy * 100).toFixed(1)}%
                        </span>
                      )}
                    </div>
                  )}
                </div>
              </div>
            ))}
            {data.holdings.filter(h => h.weight <= 0.0001).length > 0 && (
              <div className="pt-4 border-t border-surface-light">
                <p className="text-[10px] text-(--text-muted) uppercase tracking-widest mb-2 px-1">
                  Ativos em observacao (sinal fraco)
                </p>
                <div className="flex flex-wrap gap-2">
                  {data.holdings
                    .filter(h => h.weight <= 0.0001)
                    .map((holding) => (
                      <span 
                        key={holding.ticker}
                        className="px-2 py-1 rounded-md bg-surface text-[10px] text-(--text-secondary) border border-surface-light"
                        title={`${holding.ticker}: sinal ${holding.score?.toFixed(2)}. Codigo do ativo na bolsa.`}
                      >
                        {holding.ticker}
                      </span>
                    ))}
                </div>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Exposicao setorial e detalhes */}
      <div className="grid md:grid-cols-2 gap-6">
        {/* Exposicao setorial */}
        <div className="glass-card rounded-2xl p-6">
          <div className="flex items-center gap-2 mb-4">
            <PieChart className="w-5 h-5 text-primary" />
            <h3 className="font-semibold text-(--text-primary)">
              Exposicao setorial
            </h3>
            {data.diversification_score && (
              <span className="ml-auto text-xs px-2 py-1 rounded-full bg-(--primary-muted) text-primary-light">
                {data.diversification_score} setores
              </span>
            )}
          </div>
          
          {sectorEntries.length > 0 ? (
            <div className="space-y-3">
              {sectorEntries
                .sort(([,a], [,b]) => b - a)
                .map(([sector, weight]) => {
                  const percentage = (weight * 100).toFixed(1);
                  const isConcentrated = weight > maxSectorLimit;
                  return (
                    <div key={sector} className="space-y-1">
                      <div className="flex justify-between text-sm">
                        <span className="text-(--text-secondary)">{sector}</span>
                        <span className={`font-semibold ${isConcentrated ? 'text-amber-400' : 'text-(--text-primary)'}`}>
                          {percentage}%
                          {isConcentrated && " !"}
                        </span>
                      </div>
                      <div className="h-2 bg-surface rounded-full overflow-hidden">
                        <div 
                          className={`h-full rounded-full transition-all duration-500 ${
                            isConcentrated ? 'bg-amber-500' : 'bg-primary'
                          }`}
                          style={{ width: `${Math.min(parseFloat(percentage), 100)}%` }}
                        />
                      </div>
                    </div>
                  );
                })}
            </div>
          ) : (
            <p className="text-sm text-(--text-muted)">
              Dados de setor nao disponiveis
            </p>
          )}
          
          {hasSectorConcentration ? (
            <p className="text-xs text-amber-300 mt-4">
              Alerta: concentracao acima de {(maxSectorLimit * 100).toFixed(0)}% em pelo menos um setor.
            </p>
          ) : (
            <p className="text-xs text-emerald-300 mt-4">
              Exposicao setorial dentro do limite de {(maxSectorLimit * 100).toFixed(0)}%.
            </p>
          )}
        </div>

        {/* Metadados da Carteira */}
        <div className="glass-card rounded-2xl p-6">
          <div className="flex items-center gap-2 mb-4">
            <BarChart3 className="w-5 h-5 text-primary" />
            <h3 className="font-semibold text-(--text-primary)">
              Detalhes da Carteira
            </h3>
          </div>
          
          <div className="space-y-3 text-sm">
            <div className="flex justify-between py-2 border-b border-surface-light">
              <span className="text-(--text-muted)">Plano</span>
              <span className="text-(--text-primary) font-medium">{strategyLabel}</span>
            </div>
            <div className="flex justify-between py-2 border-b border-surface-light">
              <span className="text-(--text-muted)">Posicoes ativas</span>
              <span className="text-(--text-primary) font-medium">{data.n_positions}</span>
            </div>
            <div className="flex justify-between py-2 border-b border-surface-light">
              <span className="text-(--text-muted)">Peso Total Alocado</span>
              <span className="text-primary font-bold">{(data.total_weight * 100).toFixed(1)}%</span>
            </div>
            {typeof data.target_rv_allocation === 'number' && (
              <div className="flex justify-between py-2 border-b border-surface-light">
                <span className="text-(--text-muted)">Meta em acoes</span>
                <span className="text-(--text-secondary) font-medium">{(data.target_rv_allocation * 100).toFixed(1)}%</span>
              </div>
            )}
            <div className="flex justify-between py-2 border-b border-surface-light">
              <span className="text-(--text-muted)">Em Caixa</span>
              <span className="text-(--text-secondary) font-medium">
                {((1 - data.total_weight) * 100).toFixed(1)}%
              </span>
            </div>
            {data.data_date && (
              <div className="flex justify-between py-2">
                <span className="text-(--text-muted)">Dados atualizados em</span>
                <span className="text-(--text-muted) text-xs">
                  {data.data_date}
                </span>
              </div>
            )}
          </div>
          
          <div className="mt-4 p-4 rounded-xl bg-surface-light border border-(--primary-muted)">
            <h4 className="text-sm font-semibold text-(--text-primary) mb-2 flex items-center gap-2">
              <Shield className="w-4 h-4 text-primary" />
              {explanation.title}
            </h4>
            <p className="text-xs text-(--text-secondary) leading-relaxed">
              {explanation.description}
            </p>
          </div>
          
          <div className="mt-4 p-3 rounded-lg bg-surface border border-surface-light">
            <p className="text-xs text-(--text-muted) leading-relaxed">
              <strong className="text-(--text-secondary)">Sobre a reserva:</strong> O valor em <strong>Caixa</strong> e uma margem de seguranca.
              Ela aparece quando o sistema nao encontra ativos com qualidade suficiente para completar 100% da alocacao.
            </p>
          </div>
          {targetReached && typeof targetAllocation === 'number' && (
            <div className="mt-3 p-3 rounded-lg bg-emerald-500/10 border border-emerald-500/30">
              <p className="text-xs text-emerald-300 leading-relaxed">
                <strong>Meta de alocacao atingida:</strong> {(data.total_weight * 100).toFixed(1)}% de {(targetAllocation * 100).toFixed(1)}% em renda variavel.
              </p>
            </div>
          )}
          {hasMaterialAllocationGap && data.allocation_note && (
            <div className="mt-3 p-3 rounded-lg bg-amber-500/10 border border-amber-500/30">
              <p className="text-xs text-amber-300 leading-relaxed">
                <strong>Ajuste de alocacao:</strong> {data.allocation_note}
              </p>
            </div>
          )}
        </div>
      </div>

      {feedback && (
        <div className="p-3 rounded-xl bg-surface border border-surface-light text-sm text-(--text-secondary)">
          {feedback}
        </div>
      )}

      <div className="glass-card rounded-2xl p-6 border border-surface-light">
        <h3 className="text-base font-semibold text-(--text-primary) mb-4">
          Como ler esta recomendacao (simples e transparente)
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-sm">
          <DidacticStep label="O que aconteceu" text={didacticGuide.happened} />
          <DidacticStep label="Por que importa" text={didacticGuide.why} />
          <DidacticStep label="O que fazer agora" text={didacticGuide.now} />
          <DidacticStep label="Qual risco" text={didacticGuide.risk} />
        </div>
      </div>

      <TradeActionModal
        open={Boolean(selectedTicker)}
        title={selectedTicker ? `Simular compra de ${selectedTicker}` : "Simular compra"}
        description="Informe a quantidade para adicionar o ativo ao simulador com acompanhamento didatico."
        consequenceHint="Ao comprar, voce aumenta a exposicao ao ativo: pode ganhar mais se subir, mas pode perder mais se cair. Prefira entrada gradual."
        confirmLabel="Confirmar compra"
        defaultTicker={selectedTicker || ""}
        defaultQuantity="100"
        showTickerInput={false}
        isSubmitting={isSubmittingModal}
        onCancel={() => setSelectedTicker(null)}
        onConfirm={handleTradeConfirm}
      />
    </div>
  );
}

function RiskCard({ 
  icon, 
  label, 
  value, 
  color 
}: { 
  icon: React.ReactNode; 
  label: string; 
  value: string;
  color: string;
}) {
  return (
    <div className="
      glass-card rounded-xl p-4
      hover:scale-105 transition-transform
    ">
      <div className="flex items-center gap-2 mb-2" style={{ color }}>
        {icon}
        <span className="text-xs text-(--text-muted)">{label}</span>
      </div>
      <div className="text-xl font-bold" style={{ color }}>
        {value}
      </div>
    </div>
  );
}

function DidacticStep({ label, text }: { label: string; text: string }) {
  return (
    <div className="rounded-xl bg-surface p-3 border border-surface-light">
      <p className="text-xs text-(--text-muted) mb-1">{label}</p>
      <p className="text-(--text-secondary)">{text}</p>
    </div>
  );
}

