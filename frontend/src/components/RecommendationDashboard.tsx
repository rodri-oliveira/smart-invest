"use client";

import { TrendingUp, TrendingDown, Shield, AlertTriangle, Target, Zap, BarChart3, PieChart } from "lucide-react";
import { PieChart as RePieChart, Pie, Cell, ResponsiveContainer, Tooltip, Legend } from "recharts";

interface RecommendationData {
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

interface RecommendationDashboardProps {
  data: RecommendationData | null;
  isLoading: boolean;
}

export default function RecommendationDashboard({ data, isLoading }: RecommendationDashboardProps) {
  if (isLoading) {
    return (
      <div className="w-full max-w-6xl mx-auto p-8">
        <div className="glass-card rounded-2xl p-12 text-center">
          <div className="animate-pulse">
            <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-[var(--primary-muted)]"></div>
            <div className="h-4 bg-[var(--surface-light)] rounded w-48 mx-auto mb-2"></div>
            <div className="h-3 bg-[var(--surface-light)] rounded w-32 mx-auto"></div>
          </div>
          <p className="mt-6 text-[var(--text-secondary)]">
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
          <Target className="w-16 h-16 mx-auto mb-4 text-[var(--primary-muted)]" />
          <h2 className="text-xl font-semibold text-[var(--text-primary)] mb-2">
            Nenhuma recomendação ainda
          </h2>
          <p className="text-[var(--text-secondary)]">
            Digite seu objetivo acima para gerar uma recomendação personalizada.
          </p>
        </div>
      </div>
    );
  }

  // Preparar dados para o gráfico de pizza
  const pieData = data.holdings.map((holding) => ({
    name: holding.ticker,
    value: Math.round(holding.weight * 100),
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

  return (
    <div className="w-full max-w-6xl mx-auto p-4 space-y-6">
      {/* Header */}
      <div className="glass-card rounded-2xl p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-2xl font-bold gradient-text">
            {data.name} ({data.strategy})
          </h2>
          <div className="px-4 py-2 rounded-full text-sm font-semibold bg-[var(--warning)]/20 text-[var(--warning)]">
            {data.n_positions} posições
          </div>
        </div>
        
        {/* Risk Metrics Cards */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-6">
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
          <RiskCard 
            icon={<PieChart className="w-5 h-5" />}
            label="ID"
            value={`#${data.portfolio_id}`}
            color="var(--info)"
          />
        </div>
      </div>

      <div className="grid md:grid-cols-2 gap-6">
        {/* Allocation Chart */}
        <div className="glass-card rounded-2xl p-6">
          <h3 className="text-lg font-semibold text-[var(--text-primary)] mb-4 flex items-center gap-2">
            <PieChart className="w-5 h-5 text-[var(--primary)]" />
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
          <h3 className="text-lg font-semibold text-[var(--text-primary)] mb-4 flex items-center gap-2">
            <Zap className="w-5 h-5 text-[var(--accent)]" />
            Ativos Selecionados
          </h3>
          <div className="space-y-3">
            {data.holdings.map((holding, index) => (
              <div
                key={holding.ticker}
                className="
                  flex items-center justify-between
                  p-3 rounded-xl
                  bg-[var(--surface)]
                  hover:bg-[var(--surface-light)]
                  transition-colors
                "
              >
                <div className="flex items-center gap-3">
                  <span className="
                    w-8 h-8 rounded-lg
                    flex items-center justify-center
                    text-sm font-bold
                    bg-[var(--primary-muted)]
                    text-[var(--primary-light)]
                  ">
                    {index + 1}
                  </span>
                  <span className="font-semibold text-[var(--text-primary)]">
                    {holding.ticker}
                  </span>
                  {holding.sector && (
                    <span className="text-xs text-[var(--text-muted)]">({holding.sector})</span>
                  )}
                </div>
                <div className="text-right">
                  <div className="text-sm font-semibold text-[var(--primary-light)]">
                    {(holding.weight * 100).toFixed(1)}%
                  </div>
                  <div className="text-xs text-[var(--text-muted)]">
                    Peso na carteira
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Scenarios - REMOVIDO (dados não disponíveis no backend real) */}
      <div className="grid md:grid-cols-1 gap-6">
        <div className="glass-card rounded-2xl p-6 border-l-4 border-[var(--primary)]">
          <div className="flex items-center gap-2 mb-3">
            <TrendingUp className="w-5 h-5 text-[var(--primary)]" />
            <h3 className="font-semibold text-[var(--primary)]">
              Carteira Gerada
            </h3>
          </div>
          <p className="text-sm text-[var(--text-secondary)]">
            Carteira construída com estratégia {data.strategy} usando dados históricos reais do mercado.
          </p>
        </div>
      </div>

      {/* Rationale - Simplificado */}
      <div className="glass-card rounded-2xl p-6">
        <h3 className="text-lg font-semibold text-[var(--text-primary)] mb-3">
          Detalhes
        </h3>
        <p className="text-sm text-[var(--text-secondary)]">
          Estratégia: {data.strategy} | Posições: {data.n_positions} | Peso Total: {(data.total_weight * 100).toFixed(1)}%
        </p>
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
        <span className="text-xs text-[var(--text-muted)]">{label}</span>
      </div>
      <div className="text-xl font-bold" style={{ color }}>
        {value}
      </div>
    </div>
  );
}
