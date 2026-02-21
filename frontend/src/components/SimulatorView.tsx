import React, { useEffect, useMemo, useState } from "react";
import {
  TrendingUp,
  TrendingDown,
  Plus,
  Search,
  ArrowUpRight,
  ArrowDownRight,
  RefreshCw,
  ShoppingBag,
  AlertTriangle,
} from "lucide-react";
import {
  simulationService,
  SimulatedPosition,
  OperationAlert,
  DailyPlan,
} from "@/services/simulation";
import { recommendationService } from "@/services/recommendation";
import TradeActionModal from "@/components/TradeActionModal";

interface SimulatorViewProps {
  isReal?: boolean;
  realAccessAllowed?: boolean;
}

type TradeActionType = "BUY" | "SELL";

interface TradeModalState {
  open: boolean;
  title: string;
  description: string;
  consequenceHint?: string;
  confirmLabel: string;
  defaultTicker: string;
  defaultQuantity: string;
  showTickerInput: boolean;
  orderType: TradeActionType;
  isReal: boolean;
}

function formatCurrency(value: number): string {
  return value.toLocaleString("pt-BR", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function formatPct(value: number): string {
  return value.toLocaleString("pt-BR", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function formatDateTimePtBr(value?: string | null): string | null {
  if (!value) return null;
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return null;
  return parsed.toLocaleString("pt-BR");
}

function formatElapsed(seconds: number): string {
  const mins = Math.floor(seconds / 60);
  const secs = seconds % 60;
  if (mins <= 0) return `${secs}s`;
  return `${mins}m ${secs}s`;
}

function buildDidacticGuide(params: {
  isReal: boolean;
  positionsCount: number;
  totalPLPct: number;
  alertsCount: number;
  hasPlan: boolean;
}) {
  const { isReal, positionsCount, totalPLPct, alertsCount, hasPlan } = params;
  const accountLabel = isReal ? "carteira real" : "simulador";
  const trendLabel = totalPLPct >= 0 ? "resultado positivo" : "resultado negativo";
  const absPct = Math.abs(totalPLPct);

  return {
    happened:
      positionsCount === 0
        ? `Voce ainda nao tem ativos no ${accountLabel}.`
        : `Hoje voce tem ${positionsCount} ativo(s) no ${accountLabel}, com ${trendLabel} de ${formatPct(absPct)}%.`,
    why:
      positionsCount === 0
        ? "Sem posicao ativa, nao ha risco de mercado agora e voce pode aprender com calma antes de operar."
        : "Esse resumo mostra rapidamente se a carteira esta evoluindo bem ou se precisa de ajuste.",
    now:
      positionsCount === 0
        ? "Comece com uma compra pequena no simulador para testar o fluxo com seguranca."
        : alertsCount > 0
          ? "Priorize os alertas na parte de cima: ajuste primeiro o que esta em risco alto."
          : hasPlan
            ? "Siga o plano diario e evite mudar tudo de uma vez."
            : "Acompanhe diariamente e ajuste apenas quando houver motivo claro.",
    risk:
      positionsCount === 0
        ? "O principal risco agora e operar sem plano. Use passos pequenos no inicio."
        : alertsCount > 0
          ? "Ignorar alertas pode aumentar perdas se o mercado continuar contra sua posicao."
          : "Mesmo sem alerta, o mercado oscila. Ganhos e perdas fazem parte do processo.",
  };
}

export default function SimulatorView({ isReal = false, realAccessAllowed = true }: SimulatorViewProps) {
  const [positions, setPositions] = useState<SimulatedPosition[]>([]);
  const [alerts, setAlerts] = useState<OperationAlert[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [isUpdatingMarket, setIsUpdatingMarket] = useState(false);
  const [marketDataStatus, setMarketDataStatus] = useState<string | null>(null);
  const [lastUpdateCheckAt, setLastUpdateCheckAt] = useState<string | null>(null);
  const [lastUpdateFinishedAt, setLastUpdateFinishedAt] = useState<string | null>(null);
  const [updatePid, setUpdatePid] = useState<number | null>(null);
  const [updateStartedAt, setUpdateStartedAt] = useState<string | null>(null);
  const [updateElapsedSeconds, setUpdateElapsedSeconds] = useState(0);
  const [searchQuery, setSearchQuery] = useState("");
  const [dailyPlan, setDailyPlan] = useState<DailyPlan | null>(null);
  const [accessDeniedMessage, setAccessDeniedMessage] = useState<string | null>(null);
  const [isSubmittingModal, setIsSubmittingModal] = useState(false);
  const [feedback, setFeedback] = useState<{
    tone: "success" | "error" | "info";
    title: string;
    message: string;
    checklist?: string[];
  } | null>(null);
  const [tradeModal, setTradeModal] = useState<TradeModalState>({
    open: false,
    title: "",
    description: "",
    consequenceHint: "",
    confirmLabel: "Confirmar",
    defaultTicker: "",
    defaultQuantity: "100",
    showTickerInput: false,
    orderType: "BUY",
    isReal: false,
  });

  const fetchPositions = async () => {
    if (isReal && !realAccessAllowed) {
      setAccessDeniedMessage("Seu plano atual nao permite visualizar carteira real.");
      setPositions([]);
      setAlerts([]);
      setDailyPlan(null);
      setIsLoading(false);
      setIsRefreshing(false);
      return;
    }

    setIsRefreshing(true);
    try {
      const [posData, alertData, planData] = await Promise.all([
        simulationService.getPositions(isReal),
        simulationService.getAlerts(),
        simulationService.getDailyPlan(isReal).catch(() => null),
      ]);
      setPositions(posData);
      setAlerts(alertData.filter((item) => item.is_real === isReal));
      setDailyPlan(planData);
      setAccessDeniedMessage(null);
    } catch (error) {
      const err = error as { response?: { data?: { detail?: string } } };
      const detail = err.response?.data?.detail;
      const isAccessDenied = Boolean(detail && detail.toLowerCase().includes("nao permite"));

      if (isReal && isAccessDenied) {
        setAccessDeniedMessage(detail || "Seu plano atual nao permite carteira real.");
        setPositions([]);
        setAlerts([]);
        setDailyPlan(null);
      }
      setFeedback({
        tone: "error",
        title: "Nao foi possivel carregar a carteira",
        message: detail || "Tente novamente em instantes.",
      });
      console.error("Erro ao buscar dados:", error);
    } finally {
      setIsLoading(false);
      setIsRefreshing(false);
    }
  };

  const refreshMarketStatus = async () => {
    try {
      const status = await recommendationService.getDataStatus();
      const pricesDate = status.prices_date ? new Date(status.prices_date).toLocaleDateString("pt-BR") : "desconhecida";
      const scoresDate = status.scores_date ? new Date(status.scores_date).toLocaleDateString("pt-BR") : "desconhecida";
      setMarketDataStatus(`Precos: ${pricesDate} | Sinais: ${scoresDate}`);
    } catch {
      setMarketDataStatus(null);
    }
  };

  const handleManualMarketUpdate = async () => {
    setIsUpdatingMarket(true);
    setLastUpdateFinishedAt(null);
    setLastUpdateCheckAt(null);
    setUpdateElapsedSeconds(0);
    const beforeStatus = await recommendationService.getDataStatus().catch(() => null);
    const beforePricesDate = beforeStatus?.prices_date || null;
    const beforeScoresDate = beforeStatus?.scores_date || null;
    setFeedback({
      tone: "info",
      title: "Atualizacao em andamento",
      message: "Estamos buscando novos dados de mercado em segundo plano.",
      checklist: [
        "Acao agora: aguarde a conclusao do processo.",
        "Voce pode continuar usando o sistema normalmente.",
        "So reavalie os precos quando aparecer o status de concluido.",
      ],
    });
    try {
      await recommendationService.updateData();
      let status = await recommendationService.getUpdateStatus().catch(() => null);
      setUpdatePid(status?.pid ?? null);
      setUpdateStartedAt(status?.started_at ?? new Date().toISOString());
      setLastUpdateCheckAt(new Date().toISOString());
      const startedAt = Date.now();
      const timeoutMs = 6 * 60 * 1000;
      while (status?.status === "running" && Date.now() - startedAt < timeoutMs) {
        await new Promise((resolve) => setTimeout(resolve, 4000));
        status = await recommendationService.getUpdateStatus().catch(() => null);
        setUpdatePid(status?.pid ?? null);
        if (status?.started_at) setUpdateStartedAt(status.started_at);
        setLastUpdateCheckAt(new Date().toISOString());
      }

      await Promise.all([fetchPositions(), refreshMarketStatus()]);
      const afterStatus = await recommendationService.getDataStatus().catch(() => null);
      const afterPricesDate = afterStatus?.prices_date || null;
      const afterScoresDate = afterStatus?.scores_date || null;
      const changed = beforePricesDate !== afterPricesDate || beforeScoresDate !== afterScoresDate;

      if (status?.status === "failed") {
        setLastUpdateFinishedAt(status.finished_at || new Date().toISOString());
        setFeedback({
          tone: "error",
          title: "Atualizacao finalizou com erro",
          message: "O processo terminou com falha e os precos podem continuar antigos.",
          checklist: [
            "Acao agora: tente novamente em alguns minutos.",
            "Se repetir, verifique o log do backend (daily_update.log).",
          ],
        });
      } else if (status?.status === "running") {
        setFeedback({
          tone: "info",
          title: "Atualizacao ainda em andamento",
          message: "O processo segue rodando em segundo plano.",
          checklist: [
            "Acao agora: aguarde a conclusao.",
            "Nao feche o backend durante a atualizacao.",
          ],
        });
      } else if (changed) {
        setLastUpdateFinishedAt(status?.finished_at || new Date().toISOString());
        setFeedback({
          tone: "success",
          title: "Dados atualizados",
          message: "Chegaram novas referencias de mercado e a carteira foi recalculada.",
          checklist: [
            "Acao agora: revise os resultados da carteira.",
            "Se houver alerta, ajuste posicoes com criterio.",
          ],
        });
      } else {
        setLastUpdateFinishedAt(status?.finished_at || new Date().toISOString());
        setFeedback({
          tone: "info",
          title: "Sem novo preco no momento",
          message: "A atualizacao concluiu, mas nao entrou nova referencia para esses ativos desde a ultima coleta.",
          checklist: [
            "Acao agora: aguarde proxima janela de mercado e tente novamente depois.",
            "Se continuar igual por muito tempo, revise a fonte de dados.",
          ],
        });
      }
      setIsUpdatingMarket(false);
    } catch (error: unknown) {
      const err = error as { response?: { data?: { detail?: string } }; message?: string };
      setFeedback({
        tone: "error",
        title: "Falha na atualizacao",
        message: err.response?.data?.detail || err.message || "Nao foi possivel atualizar os dados agora.",
      });
      setIsUpdatingMarket(false);
    }
  };

  useEffect(() => {
    if (!isUpdatingMarket || !updateStartedAt) return;
    const timer = setInterval(() => {
      const start = new Date(updateStartedAt).getTime();
      if (Number.isNaN(start)) return;
      const diffSeconds = Math.max(0, Math.floor((Date.now() - start) / 1000));
      setUpdateElapsedSeconds(diffSeconds);
    }, 1000);
    return () => clearInterval(timer);
  }, [isUpdatingMarket, updateStartedAt]);

  useEffect(() => {
    fetchPositions();
    refreshMarketStatus();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isReal, realAccessAllowed]);

  const totalCost = positions.reduce((acc, pos) => acc + pos.total_cost, 0);
  const currentValue = positions.reduce((acc, pos) => acc + pos.quantity * pos.current_price, 0);
  const totalPL = currentValue - totalCost;
  const totalPLPct = totalCost > 0 ? (totalPL / totalCost) * 100 : 0;

  const filteredPositions = useMemo(
    () => positions.filter((pos) => pos.ticker.toLowerCase().includes(searchQuery.trim().toLowerCase())),
    [positions, searchQuery],
  );
  const didacticGuide = buildDidacticGuide({
    isReal,
    positionsCount: positions.length,
    totalPLPct,
    alertsCount: alerts.length,
    hasPlan: Boolean(dailyPlan),
  });

  const getDidacticSuggestion = (pos: SimulatedPosition) => {
    if (pos.profit_loss_pct <= -10) return "Queda forte: reduzir risco pode proteger seu capital.";
    if (pos.profit_loss_pct >= 20) return "Lucro alto: considere realizar parte do ganho.";
    if (pos.profit_loss_pct >= 5) return "Posicao positiva: manter e acompanhar.";
    if (pos.profit_loss_pct > -5) return "Faixa neutra: observe antes de agir.";
    return "Oscilacao moderada: revise tamanho da posicao.";
  };

  const parsePositiveInt = (value: string) => {
    const n = parseInt(value, 10);
    if (!Number.isFinite(n) || n <= 0) return null;
    return n;
  };

  const findPositionByTicker = (ticker: string) =>
    positions.find((pos) => pos.ticker.toUpperCase() === ticker.toUpperCase());

  const getSuggestedAdjustmentQty = (ticker: string, severity: OperationAlert["severity"]) => {
    const pos = findPositionByTicker(ticker);
    if (!pos) return 1;
    const ratio = severity === "HIGH" ? 0.5 : severity === "MEDIUM" ? 0.3 : 0.2;
    return Math.max(1, Math.ceil(pos.quantity * ratio));
  };

  const openTradeModal = (config: Omit<TradeModalState, "open">) => {
    setTradeModal({ ...config, open: true });
  };

  const closeTradeModal = () => {
    if (isSubmittingModal) return;
    setTradeModal((prev) => ({ ...prev, open: false }));
  };

  const handleModalConfirm = async (values: { ticker: string; quantity: string }) => {
    const ticker = (values.ticker || tradeModal.defaultTicker).trim().toUpperCase();
    const parsedQty = parsePositiveInt(values.quantity);

    if (!ticker) {
      setFeedback({
        tone: "error",
        title: "Ticker invalido",
        message: "Informe um ticker valido para continuar.",
      });
      return;
    }
    if (!parsedQty) {
      setFeedback({
        tone: "error",
        title: "Quantidade invalida",
        message: "Use apenas numeros inteiros maiores que zero.",
      });
      return;
    }

    try {
      setIsSubmittingModal(true);
      await simulationService.createOrder(ticker, tradeModal.orderType, parsedQty, tradeModal.isReal);
      await fetchPositions();
      setTradeModal((prev) => ({ ...prev, open: false }));
      setFeedback({
        tone: "success",
        title: "Operacao concluida",
        message: `${tradeModal.orderType === "BUY" ? "Compra" : "Venda"} de ${parsedQty} ${ticker} registrada com sucesso.`,
        checklist: [
          "Operacao salva no historico.",
          "Resultado da carteira atualizado.",
          "Revise alertas antes da proxima decisao.",
        ],
      });
    } catch (err: unknown) {
      const error = err as { message?: string };
      setFeedback({
        tone: "error",
        title: "Falha na operacao",
        message: error.message || "Nao foi possivel registrar a operacao agora.",
      });
    } finally {
      setIsSubmittingModal(false);
    }
  };

  const handleQuickBuy = async () => {
    openTradeModal({
      title: isReal ? "Registrar compra na carteira real" : "Nova simulacao de compra",
      description: "Informe o ticker e a quantidade. Operacao em passos simples e transparentes.",
      consequenceHint:
        "Ao comprar, seu patrimonio fica mais exposto as oscilacoes desse ativo. Comece com quantidade pequena para testar.",
      confirmLabel: "Registrar compra",
      defaultTicker: "",
      defaultQuantity: "100",
      showTickerInput: true,
      orderType: "BUY",
      isReal,
    });
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <RefreshCw className="w-8 h-8 animate-spin text-primary" />
      </div>
    );
  }

  if (isReal && accessDeniedMessage) {
    return (
      <div className="space-y-6">
        <div className="p-4 rounded-xl bg-red-500/10 border border-red-500/30">
          <h4 className="text-sm font-semibold text-red-300 mb-1">Acesso restrito a carteira real</h4>
          <p className="text-xs text-(--text-secondary)">{accessDeniedMessage}</p>
        </div>

        <div className="p-4 rounded-xl bg-surface border border-surface-light">
          <h4 className="text-sm font-semibold text-primary-light mb-1">Como continuar agora</h4>
          <p className="text-xs text-(--text-secondary) leading-relaxed">
            Use a aba <strong>Simulador de Compra</strong> para acompanhar ativos e receber feedback diario
            com explicacao simples de risco, acao recomendada e proximo passo.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {feedback && (
        <div
          className={`p-4 rounded-xl border ${
            feedback.tone === "success"
              ? "bg-emerald-500/10 border-emerald-500/30"
              : feedback.tone === "error"
                ? "bg-red-500/10 border-red-500/30"
                : "bg-surface border-surface-light"
          }`}
        >
          <h4 className="text-sm font-semibold text-(--text-primary)">{feedback.title}</h4>
          <p className="text-xs text-(--text-secondary) mt-1">{feedback.message}</p>
          {feedback.checklist && (
            <ul className="mt-2 text-xs text-(--text-muted) space-y-1">
              {feedback.checklist.map((item) => (
                <li key={item}>- {item}</li>
              ))}
            </ul>
          )}
        </div>
      )}

      <div className="p-4 rounded-xl bg-(--primary-muted) border border-primary-light/20">
        <div className="flex flex-wrap items-center justify-between gap-3 mb-1">
          <h4 className="text-sm font-semibold text-primary-light">Como operar de forma simples</h4>
          <button
            onClick={handleManualMarketUpdate}
            disabled={isUpdatingMarket}
            className="px-3 py-1.5 rounded-lg bg-surface-light hover:bg-surface text-xs font-semibold text-(--text-secondary) disabled:opacity-60 inline-flex items-center gap-2"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isUpdatingMarket ? "animate-spin" : ""}`} />
            {isUpdatingMarket ? "Atualizando mercado..." : "Atualizar dados agora"}
          </button>
        </div>
        <p className="text-xs text-(--text-secondary) leading-relaxed">
          1) Na aba Recomendacao, clique no botao <strong>+</strong> no ativo desejado. 2) Informe a quantidade.
          3) Volte aqui para acompanhar resultado e sugestoes de ajuste.
        </p>
        {marketDataStatus && (
          <p className="text-[11px] text-(--text-muted) mt-2">Ultima referencia de dados: {marketDataStatus}</p>
        )}
        {isUpdatingMarket && lastUpdateCheckAt && (
          <p className="text-[11px] text-(--text-muted) mt-1">
            Ultima checagem do processo: {formatDateTimePtBr(lastUpdateCheckAt)}
          </p>
        )}
        {isUpdatingMarket && (
          <p className="text-[11px] text-(--text-muted) mt-1">
            {updatePid ? `PID: ${updatePid} | ` : ""}Tempo decorrido: {formatElapsed(updateElapsedSeconds)}
          </p>
        )}
        {isUpdatingMarket && (
          <p className="text-[11px] text-(--text-muted) mt-1">
            Acao agora: aguarde o status de concluido antes de comparar os precos da carteira.
          </p>
        )}
        {!isUpdatingMarket && lastUpdateFinishedAt && (
          <p className="text-[11px] text-(--text-muted) mt-1">
            Atualizacao concluida em: {formatDateTimePtBr(lastUpdateFinishedAt)}
          </p>
        )}
      </div>

      {dailyPlan && (
        <div className="p-4 rounded-xl bg-surface border border-primary-light/20 space-y-2">
          <h4 className="text-sm font-semibold text-primary-light">Plano diario (linguagem simples)</h4>
          <p className="text-xs text-(--text-secondary)">{dailyPlan.summary}</p>
          <p className="text-xs text-(--text-muted)">{dailyPlan.next_step}</p>
          {dailyPlan.guidance.length > 0 && (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-2 pt-1">
              {dailyPlan.guidance.slice(0, 4).map((item) => (
                <div key={item.ticker} className="rounded-lg bg-surface-light/60 p-3 border border-surface-light">
                  <div className="text-xs font-bold text-(--text-primary)">
                    {item.ticker}: {item.action}
                  </div>
                  <div className="text-[11px] text-(--text-secondary) mt-1">{item.reason}</div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      <div className="glass-card rounded-2xl p-4 border border-surface-light">
        <h4 className="text-sm font-semibold text-(--text-primary) mb-3">
          Como ler seu acompanhamento (simples e transparente)
        </h4>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
          <DidacticBox label="O que aconteceu" text={didacticGuide.happened} />
          <DidacticBox label="Por que importa" text={didacticGuide.why} />
          <DidacticBox label="O que fazer agora" text={didacticGuide.now} />
          <DidacticBox label="Qual risco" text={didacticGuide.risk} />
        </div>
      </div>

      {alerts.length > 0 && (
        <div className="space-y-2">
          {alerts.map((opAlert, idx) => (
            <div
              key={`${opAlert.ticker}-${idx}`}
              className={`flex items-center gap-3 p-4 rounded-xl border ${
                opAlert.severity === "HIGH"
                  ? "bg-red-500/10 border-red-500/30 text-red-400"
                  : opAlert.severity === "MEDIUM"
                    ? "bg-amber-500/10 border-amber-500/30 text-amber-400"
                    : "bg-blue-500/10 border-blue-500/30 text-blue-400"
              }`}
            >
              <AlertTriangle className="w-5 h-5 shrink-0" />
              <div className="flex-1">
                <span className="font-bold mr-2">{opAlert.ticker}</span>
                <span className="text-sm">{opAlert.message}</span>
              </div>
              <button
                onClick={() => {
                  const suggested = getSuggestedAdjustmentQty(opAlert.ticker, opAlert.severity);
                  openTradeModal({
                    title: `Ajustar posicao em ${opAlert.ticker}`,
                    description: "O sistema sugeriu ajuste para reduzir risco. Confirme a quantidade para simular venda.",
                    consequenceHint:
                      "Ao vender, voce reduz risco e volatilidade da carteira, mas tambem pode deixar de ganhar se o ativo voltar a subir.",
                    confirmLabel: "Aplicar ajuste",
                    defaultTicker: opAlert.ticker,
                    defaultQuantity: suggested.toString(),
                    showTickerInput: false,
                    orderType: "SELL",
                    isReal,
                  });
                }}
                className="px-3 py-1 rounded-lg bg-surface-light hover:bg-white/10 transition-colors text-xs font-bold"
              >
                Ajustar
              </button>
            </div>
          ))}
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="glass-card p-6 rounded-2xl border border-surface-light">
          <div className="text-sm text-text-muted mb-1">{isReal ? "Patrimonio Real" : "Patrimonio Simulado"}</div>
          <div className="text-2xl font-bold text-text-primary">
            R$ {formatCurrency(currentValue)}
          </div>
        </div>

        <div className="glass-card p-6 rounded-2xl border border-surface-light">
          <div className="text-sm text-text-muted mb-1">Resultado Total</div>
          <div className={`text-2xl font-bold flex items-center gap-2 ${totalPL >= 0 ? "text-success" : "text-error"}`}>
            {totalPL < 0 ? "-R$ " : "R$ "}
            {formatCurrency(Math.abs(totalPL))}
            <span className="text-sm font-medium">({formatPct(totalPLPct)}%)</span>
            {totalPL >= 0 ? <TrendingUp className="w-5 h-5" /> : <TrendingDown className="w-5 h-5" />}
          </div>
        </div>

        <div className="glass-card p-6 rounded-2xl border border-surface-light flex items-center justify-between">
          <div>
            <div className="text-sm text-text-muted mb-1">Posicoes Ativas</div>
            <div className="text-2xl font-bold text-text-primary">{positions.length}</div>
          </div>
          <button
            onClick={fetchPositions}
            className="p-2 rounded-xl bg-surface-light text-text-secondary hover:text-primary-light transition-colors"
          >
            <RefreshCw className={`w-5 h-5 ${isRefreshing ? "animate-spin" : ""}`} />
          </button>
        </div>
      </div>

      <div className="glass-card rounded-2xl border border-surface-light overflow-hidden">
        <div className="p-6 border-b border-surface-light flex items-center justify-between">
          <h3 className="font-bold text-(--text-primary)">Ativos em acompanhamento</h3>
          <div className="flex gap-2">
            <div className="relative">
              <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-(--text-muted)" />
              <input
                type="text"
                placeholder="Buscar ativo..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-9 pr-4 py-2 bg-surface-light border-none rounded-xl text-sm focus:ring-1 focus:ring-primary w-48"
              />
            </div>
          </div>
        </div>

        {positions.length === 0 ? (
          <div className="p-12 text-center">
            <ShoppingBag className="w-12 h-12 mx-auto mb-4 text-(--text-muted) opacity-20" />
            <p className="text-(--text-secondary) mb-4">
              {isReal ? "Sua carteira real esta vazia." : "Nenhuma simulacao ativa no momento."}
            </p>
            <button
              onClick={handleQuickBuy}
              className="px-6 py-2 bg-primary hover:bg-primary-light text-white rounded-xl font-medium transition-all inline-flex items-center gap-2"
            >
              <Plus className="w-4 h-4" />
              {isReal ? "Registrar compra" : "Nova simulacao"}
            </button>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left">
              <thead>
                <tr className="bg-surface-light/50 text-(--text-muted) text-xs uppercase tracking-wider">
                  <th className="px-6 py-4 font-semibold">Ativo</th>
                  <th className="px-6 py-4 font-semibold text-right">Qtd</th>
                  <th className="px-6 py-4 font-semibold text-right">Preco medio</th>
                  <th className="px-6 py-4 font-semibold text-right">Preco atual</th>
                  <th className="px-6 py-4 font-semibold text-right">Resultado</th>
                  <th className="px-6 py-4 font-semibold text-center">Acoes</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-surface-light">
                {filteredPositions.map((pos) => (
                  <tr key={pos.ticker} className="hover:bg-surface-light/30 transition-colors group">
                    <td className="px-6 py-4">
                      <div className="font-bold text-(--text-primary)">{pos.ticker}</div>
                    </td>
                    <td className="px-6 py-4 text-right text-(--text-secondary)">{pos.quantity}</td>
                    <td className="px-6 py-4 text-right text-(--text-secondary)">R$ {formatCurrency(pos.avg_price)}</td>
                    <td className="px-6 py-4 text-right">
                      <div className="font-medium text-(--text-primary)">R$ {formatCurrency(pos.current_price)}</div>
                    </td>
                    <td className="px-6 py-4 text-right">
                      <div
                        className={`font-bold flex items-center justify-end gap-1 ${
                          pos.profit_loss >= 0 ? "text-(--success)" : "text-(--error)"
                        }`}
                      >
                        {pos.profit_loss_pct >= 0 ? (
                          <ArrowUpRight className="w-3 h-3" />
                        ) : (
                          <ArrowDownRight className="w-3 h-3" />
                        )}
                        {formatPct(pos.profit_loss_pct)}%
                      </div>
                      <div className="text-[10px] text-(--text-muted)">R$ {formatCurrency(pos.profit_loss)}</div>
                      <div className="text-[10px] text-(--text-secondary) mt-1 max-w-48 ml-auto">
                        {getDidacticSuggestion(pos)}
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      <div className="flex items-center justify-center gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
                        <button
                          onClick={() => {
                            openTradeModal({
                              title: `Comprar mais ${pos.ticker}`,
                              description: "Digite a quantidade para ampliar a posicao.",
                              consequenceHint:
                                "Ao comprar mais, seu ganho potencial aumenta, mas a perda potencial tambem cresce se o ativo cair.",
                              confirmLabel: "Confirmar compra",
                              defaultTicker: pos.ticker,
                              defaultQuantity: "100",
                              showTickerInput: false,
                              orderType: "BUY",
                              isReal,
                            });
                          }}
                          className="p-1.5 rounded-lg bg-surface-light text-(--text-secondary) hover:text-primary transition-colors"
                          title="Comprar mais"
                        >
                          <Plus className="w-4 h-4" />
                        </button>
                        <button
                          onClick={() => {
                            openTradeModal({
                              title: `Vender ${pos.ticker}`,
                              description: "Digite a quantidade que deseja vender.",
                              consequenceHint:
                                "Ao vender, voce realiza o resultado atual e reduz risco da posicao. Pode perder parte da alta futura se o ativo subir.",
                              confirmLabel: "Confirmar venda",
                              defaultTicker: pos.ticker,
                              defaultQuantity: pos.quantity.toString(),
                              showTickerInput: false,
                              orderType: "SELL",
                              isReal,
                            });
                          }}
                          className="p-1.5 rounded-lg bg-surface-light text-(--text-secondary) hover:text-(--error) transition-colors"
                          title="Vender"
                        >
                          <ShoppingBag className="w-4 h-4" />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>

            {filteredPositions.length === 0 && (
              <div className="p-8 text-center text-(--text-secondary)">Nenhum ativo encontrado para {searchQuery}.</div>
            )}
          </div>
        )}
      </div>

      <div className="p-4 rounded-xl bg-(--primary-muted) border border-primary-light/20">
        <h4 className="text-sm font-semibold text-primary-light mb-1 flex items-center gap-2">
          <TrendingUp className="w-4 h-4" />
          Insight Operacional
        </h4>
        <p className="text-xs text-(--text-secondary) leading-relaxed">
          O sistema monitora suas posicoes. Quando algum ativo sair do plano esperado,
          voce recebe um alerta com sugestao de proximo passo.
        </p>
      </div>

      <TradeActionModal
        open={tradeModal.open}
        title={tradeModal.title}
        description={tradeModal.description}
        consequenceHint={tradeModal.consequenceHint}
        confirmLabel={tradeModal.confirmLabel}
        defaultTicker={tradeModal.defaultTicker}
        defaultQuantity={tradeModal.defaultQuantity}
        showTickerInput={tradeModal.showTickerInput}
        isSubmitting={isSubmittingModal}
        onCancel={closeTradeModal}
        onConfirm={handleModalConfirm}
      />
    </div>
  );
}

function DidacticBox({ label, text }: { label: string; text: string }) {
  return (
    <div className="rounded-lg bg-surface p-3 border border-surface-light">
      <p className="text-[11px] text-(--text-muted) mb-1">{label}</p>
      <p className="text-xs text-(--text-secondary) leading-relaxed">{text}</p>
    </div>
  );
}
