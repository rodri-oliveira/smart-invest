"use client";

import { useState } from "react";
import { Activity, Calendar, ShieldAlert, TrendingUp } from "lucide-react";
import { AssetInsightResponse } from "@/services/recommendation";
import TradeActionModal from "@/components/TradeActionModal";

interface AssetInsightCardProps {
  data: AssetInsightResponse | null;
  isLoading: boolean;
  onAddToSimulation?: (ticker: string, quantity: number) => void | Promise<void>;
}

interface DidacticGuide {
  happened: string;
  why: string;
  now: string;
  risk: string;
}

function fmtPct(value: number): string {
  const sign = value > 0 ? "+" : "";
  return `${sign}${value.toFixed(2)}%`;
}

function buildDidacticGuide(data: AssetInsightResponse): DidacticGuide {
  const trend30 = data.change_30d_pct >= 0 ? "subiu" : "caiu";
  const trend7 = data.change_7d_pct >= 0 ? "alta" : "queda";

  return {
    happened: `${data.ticker} esta em R$ ${data.latest_price.toFixed(2)}, com ${fmtPct(data.change_1d_pct)} no dia e ${fmtPct(data.change_30d_pct)} em 30 dias.`,
    why: `No curto prazo houve ${trend7} e no mensal o ativo ${trend30}. Isso ajuda a entender se o momento esta acelerando ou perdendo forca.`,
    now: "Se for entrar, comece com quantidade pequena e acompanhe no Simulador antes de aumentar a posicao.",
    risk:
      data.risk_label.toUpperCase() === "ALTO"
        ? "Risco alto no momento: movimentos sem controle podem ampliar perdas."
        : "Mesmo com risco moderado, o preco pode oscilar e gerar perdas no curto prazo.",
  };
}

export default function AssetInsightCard({
  data,
  isLoading,
  onAddToSimulation,
}: AssetInsightCardProps) {
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [feedback, setFeedback] = useState<string | null>(null);

  if (!isLoading && !data) return null;

  if (isLoading) {
    return (
      <div className="glass-card rounded-2xl p-6 animate-pulse">
        <div className="h-5 w-48 bg-surface-light rounded mb-4"></div>
        <div className="h-4 w-full bg-surface-light rounded"></div>
      </div>
    );
  }

  if (!data) return null;
  const didactic = buildDidacticGuide(data);

  const handleConfirm = async ({ quantity }: { ticker: string; quantity: string }) => {
    const parsedQty = parseInt(quantity, 10);
    if (!Number.isFinite(parsedQty) || parsedQty <= 0) {
      setFeedback("Quantidade invalida. Use um numero inteiro maior que zero.");
      return;
    }
    try {
      setIsSubmitting(true);
      await onAddToSimulation?.(data.ticker, parsedQty);
      setFeedback(`Ativo ${data.ticker} adicionado ao simulador com sucesso.`);
      setIsModalOpen(false);
    } catch {
      setFeedback("Nao foi possivel adicionar o ativo ao simulador agora.");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="glass-card rounded-2xl p-6 space-y-4">
      {feedback && (
        <div className="p-3 rounded-xl bg-surface border border-surface-light text-sm text-(--text-secondary)">
          {feedback}
        </div>
      )}
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-bold text-(--text-primary)">
          Consulta de ativo: {data.ticker}
        </h3>
        <span className="text-xs px-2 py-1 rounded-full bg-(--primary-muted) text-primary-light">
          {data.risk_label}
        </span>
      </div>

      <p className="text-sm text-(--text-secondary)">
        {data.name} {data.sector ? `- ${data.sector}` : ""}
      </p>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <Metric label="Preco atual" value={`R$ ${data.latest_price.toFixed(2)}`} icon={<TrendingUp className="w-4 h-4" />} />
        <Metric label="1 dia" value={fmtPct(data.change_1d_pct)} icon={<Activity className="w-4 h-4" />} />
        <Metric label="7 dias" value={fmtPct(data.change_7d_pct)} icon={<Activity className="w-4 h-4" />} />
        <Metric label="30 dias" value={fmtPct(data.change_30d_pct)} icon={<Activity className="w-4 h-4" />} />
      </div>

      <div className="p-4 rounded-xl bg-surface-light border border-(--primary-muted)">
        <p className="text-sm text-(--text-primary)">{data.didactic_summary}</p>
        <p className="text-xs text-(--text-secondary) mt-2">
          <ShieldAlert className="w-3 h-3 inline mr-1" />
          {data.guidance}
        </p>
        <p className="text-xs text-(--text-muted) mt-2">
          <Calendar className="w-3 h-3 inline mr-1" />
          Dados de {data.latest_date}
        </p>
      </div>

      <div className="rounded-xl bg-surface border border-surface-light p-4">
        <h4 className="text-sm font-semibold text-(--text-primary) mb-3">
          Como interpretar este ativo (simples e transparente)
        </h4>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          <DidacticStep label="O que aconteceu" text={didactic.happened} />
          <DidacticStep label="Por que importa" text={didactic.why} />
          <DidacticStep label="O que fazer agora" text={didactic.now} />
          <DidacticStep label="Qual risco" text={didactic.risk} />
        </div>
      </div>

      <button
        onClick={() => setIsModalOpen(true)}
        className="px-4 py-2 rounded-xl bg-primary hover:bg-primary-light text-white text-sm font-medium transition-colors"
      >
        Adicionar ao Simulador
      </button>

      <TradeActionModal
        open={isModalOpen}
        title={`Adicionar ${data.ticker} ao simulador`}
        description="Informe a quantidade para iniciar o acompanhamento didatico."
        confirmLabel="Adicionar"
        defaultTicker={data.ticker}
        defaultQuantity="100"
        showTickerInput={false}
        isSubmitting={isSubmitting}
        onCancel={() => setIsModalOpen(false)}
        onConfirm={handleConfirm}
      />
    </div>
  );
}

function Metric({ label, value, icon }: { label: string; value: string; icon: React.ReactNode }) {
  return (
    <div className="p-3 rounded-xl bg-surface border border-surface-light">
      <div className="flex items-center gap-2 text-(--text-muted) text-xs mb-1">
        {icon}
        <span>{label}</span>
      </div>
      <div className="font-semibold text-(--text-primary)">{value}</div>
    </div>
  );
}

function DidacticStep({ label, text }: { label: string; text: string }) {
  return (
    <div className="rounded-lg bg-surface-light/60 p-3 border border-surface-light">
      <p className="text-xs text-(--text-muted) mb-1">{label}</p>
      <p className="text-xs text-(--text-secondary) leading-relaxed">{text}</p>
    </div>
  );
}
