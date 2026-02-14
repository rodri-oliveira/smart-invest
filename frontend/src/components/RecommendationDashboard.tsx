"use client";

import { 
  TrendingDown, 
  Shield, 
  AlertTriangle, 
  Target, 
  Zap, 
  BarChart3, 
  PieChart, 
  Activity, 
  Plus
} from "lucide-react";
import { PieChart as RePieChart, Pie, Cell, ResponsiveContainer, Tooltip, Legend } from "recharts";

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
  objective?: string;  // Objetivo real do usuário: income, return, protection, speculation, balanced
  user_regime?: string;  // RISK_ON_STRONG, RISK_ON, TRANSITION, RISK_OFF, RISK_OFF_STRONG
  max_sector_exposure?: number;  // Limite dinâmico de exposição setorial
  n_positions: number;
  total_weight: number;
  sector_exposure?: Record<string, number>;
  diversification_score?: number;
  data_date?: string;
  holdings: Array<{
    ticker: string;
    weight: number;
    score?: number;
    sector?: string;
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
}

function getStrategyExplanation(regime?: string, strategy?: string, objective?: string): { title: string; description: string } {
  // Verificar se é estratégia de renda pelo objetivo (mais confiável) ou pelo nome da estratégia
  const isIncomeObjective = objective?.toLowerCase() === 'income';
  const isIncomeStrategy = strategy?.toLowerCase().includes('income') || 
                           strategy?.toLowerCase().includes('dividend') ||
                           strategy?.toLowerCase().includes('renda');
  const isIncome = isIncomeObjective || isIncomeStrategy;
  switch (regime) {
    case 'RISK_ON_STRONG':
      return {
        title: 'Estratégia de Alta Performance',
        description: 'Esta carteira prioriza ativos com alto potencial de valorização, mesmo que isso implique maior volatilidade. O algoritmo favorece fatores de Momentum e tendências de mercado, buscando capturar movimentos de alta intensidade. A alocação maximizada (até 98%) reflete confiança no cenário de mercado favorável ao risco.',
      };
    case 'RISK_ON':
      return {
        title: 'Estratégia de Crescimento',
        description: 'Foco em ativos com potencial de alta valorização. O modelo equilibra Momentum (tendências de preço) com indicadores de Qualidade e Valor fundamentais. Com alocação de até 95% em renda variável, esta estratégia é adequada para quem busca retornos superiores à média do mercado e tolera flutuações no curto prazo.',
      };
    case 'RISK_OFF':
      return {
        title: 'Estratégia de Preservação de Capital',
        description: 'Prioridade máxima à segurança. O algoritmo seleciona ativos com os melhores fundamentos (Qualidade) e menor volatilidade histórica. A alocação limitada (máximo 20%) protege contra quedas severas, mantendo a maior parte do capital em posição defensiva. Ideal para proteger patrimônio em cenários incertos.',
      };
    case 'RISK_OFF_STRONG':
      return {
        title: 'Estratégia Ultra-Conservadora',
        description: 'Modo de máxima defesa. Apenas 5% de exposição ao mercado de ações, concentrado nos ativos de mais alta qualidade e menor risco. Esta configuração é para preservação absoluta de capital, praticamente equivalente a renda fixa.',
      };
    case 'TRANSITION':
    default:
      // Verificar se é estratégia de renda/dividendos
      if (isIncome) {
        return {
          title: 'Estratégia de Renda Passiva',
          description: 'Foco em ativos pagadores de dividendos consistentes. O modelo prioriza empresas com alto Dividend Yield (DY), boa geração de caixa (Quality) e preço justo (Value). Com alocação moderada (~50%), busca-se equilíbrio entre receber proventos regulares e preservar o capital investido.',
        };
      }
      return {
        title: 'Estratégia Balanceada',
        description: 'Abordagem equilibrada que diversifica entre diferentes fatores de retorno: Valor, Qualidade e Momentum. A alocação de 50% permite participar das altas do mercado enquanto mantém reserva de segurança. É a estratégia padrão quando o perfil de risco não é explicitamente definido no prompt.',
      };
  }
}

export default function RecommendationDashboard({ data, isLoading, alerts }: RecommendationDashboardProps) {
  // Obter explicação dinâmica baseada no regime, estratégia e objetivo
  const explanation = getStrategyExplanation(data?.user_regime, data?.strategy, data?.objective);

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
            Analisando mercado e calculando scores...
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
            Nenhuma recomendação ainda
          </h2>
          <p className="text-(--text-secondary)">
            Digite seu objetivo acima para gerar uma recomendação personalizada.
          </p>
        </div>
      </div>
    );
  }

  // Preparar dados para o gráfico de pizza - Garantir que apenas valores positivos entrem
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

  // Usar limite dinâmico do backend ou fallback para 35%
  const maxSectorLimit = data?.max_sector_exposure ?? 0.35;

  return (
    <div className="w-full max-w-6xl mx-auto p-4 space-y-6">
      {/* Header */}
      <div className="glass-card rounded-2xl p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-2xl font-bold gradient-text">
            {data.name} ({data.strategy})
          </h2>
          <div className="px-4 py-2 rounded-full text-sm font-semibold bg-warning/20 text-(--warning)">
            {data.n_positions} posições
          </div>
        </div>
        
        {/* Risk Metrics Cards */}
        <div className="grid grid-cols-2 md:grid-cols-5 gap-4 mt-6">
          <RiskCard 
            icon={<BarChart3 className="w-5 h-5" />}
            label="Posições"
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
            label="Estratégia"
            value={data.strategy}
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
              Alertas de Rebalanceamento
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
            Alocação Sugerida
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
                    <span className="font-semibold text-(--text-primary)">
                      {holding.ticker}
                    </span>
                    {holding.sector && (
                      <span className="text-[10px] text-(--text-muted) uppercase tracking-wider">
                        {holding.sector}
                      </span>
                    )}
                  </div>
                </div>
                <div className="text-right flex flex-col items-end gap-1">
                  {holding.current_price && (
                    <div className="flex items-center gap-2">
                      <button 
                        onClick={(e) => {
                          e.stopPropagation();
                          const qty = window.prompt(`Simular compra de ${holding.ticker}. Quantas ações?`, "100");
                          if (qty) {
                            import('@/services/simulation').then(m => {
                              m.simulationService.createOrder(holding.ticker, 'BUY', parseInt(qty))
                                .then(() => alert('Simulação registrada! Veja na aba Simulador.'))
                                .catch(err => alert('Erro: ' + err.message));
                            });
                          }
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
                    Alocação
                  </div>
                  {(holding.p_l || holding.dy) && (
                    <div className="flex gap-2 mt-1 justify-end">
                      {holding.p_l && (
                        <span className="text-[10px] px-1.5 py-0.5 rounded bg-surface text-(--text-secondary)" title="Preço/Lucro">
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
                  Ativos Observados (Score baixo/negativo)
                </p>
                <div className="flex flex-wrap gap-2">
                  {data.holdings
                    .filter(h => h.weight <= 0.0001)
                    .map((holding) => (
                      <span 
                        key={holding.ticker}
                        className="px-2 py-1 rounded-md bg-surface text-[10px] text-(--text-secondary) border border-surface-light"
                        title={`Score: ${holding.score?.toFixed(2)}`}
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

      {/* Exposição Setorial e Metadados */}
      <div className="grid md:grid-cols-2 gap-6">
        {/* Exposição Setorial */}
        <div className="glass-card rounded-2xl p-6">
          <div className="flex items-center gap-2 mb-4">
            <PieChart className="w-5 h-5 text-primary" />
            <h3 className="font-semibold text-(--text-primary)">
              Exposição Setorial
            </h3>
            {data.diversification_score && (
              <span className="ml-auto text-xs px-2 py-1 rounded-full bg-(--primary-muted) text-primary-light">
                {data.diversification_score} setores
              </span>
            )}
          </div>
          
          {data.sector_exposure && Object.keys(data.sector_exposure).length > 0 ? (
            <div className="space-y-3">
              {Object.entries(data.sector_exposure)
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
                          {isConcentrated && ' ⚠️'}
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
              Dados de setor não disponíveis
            </p>
          )}
          
          <p className="text-xs text-(--text-muted) mt-4">
            ⚠️ Alertas indicam concentração acima de {(maxSectorLimit * 100).toFixed(0)}% em um setor (limite para regime {data?.user_regime?.replace(/_/g, ' ') || 'padrão'})
          </p>
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
              <span className="text-(--text-muted)">Estratégia</span>
              <span className="text-(--text-primary) font-medium">{data.strategy}</span>
            </div>
            <div className="flex justify-between py-2 border-b border-surface-light">
              <span className="text-(--text-muted)">Posições Ativas</span>
              <span className="text-(--text-primary) font-medium">{data.n_positions}</span>
            </div>
            <div className="flex justify-between py-2 border-b border-surface-light">
              <span className="text-(--text-muted)">Peso Total Alocado</span>
              <span className="text-primary font-bold">{(data.total_weight * 100).toFixed(1)}%</span>
            </div>
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
              💡 <strong className="text-(--text-secondary)">Sobre o Caixa:</strong> O percentual em <strong>Caixa</strong> representa uma margem de segurança. 
              Ele ocorre quando o sistema não encontra ativos suficientes que atendam aos critérios mínimos de segurança e potencial de retorno para completar 100% da alocação.
            </p>
          </div>
        </div>
      </div>
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
