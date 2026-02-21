import React, { useEffect, useMemo, useState } from "react";
import { RefreshCw } from "lucide-react";
import { simulationService, OrderHistoryItem } from "@/services/simulation";

type Scope = "all" | "simulated" | "real";

function formatCurrency(value: number): string {
  return value.toLocaleString("pt-BR", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

export default function HistoryView() {
  const [orders, setOrders] = useState<OrderHistoryItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [scope, setScope] = useState<Scope>("all");

  const fetchHistory = async () => {
    setIsRefreshing(true);
    try {
      const data = await simulationService.getOrdersHistory();
      setOrders(data);
    } catch (error) {
      console.error("Erro ao carregar histórico:", error);
    } finally {
      setIsLoading(false);
      setIsRefreshing(false);
    }
  };

  useEffect(() => {
    fetchHistory();
  }, []);

  const filtered = useMemo(() => {
    if (scope === "all") return orders;
    const flag = scope === "real";
    return orders.filter((order) => order.is_real === flag);
  }, [orders, scope]);

  const summary = useMemo(() => {
    const buys = filtered.filter((order) => order.order_type === "BUY").length;
    const sells = filtered.filter((order) => order.order_type === "SELL").length;
    return {
      total: filtered.length,
      buys,
      sells,
    };
  }, [filtered]);

  const latestAction = useMemo(() => {
    if (filtered.length === 0) return null;
    const sorted = [...filtered].sort(
      (a, b) => new Date(b.order_date).getTime() - new Date(a.order_date).getTime(),
    );
    const last = sorted[0];
    const actionLabel = last.order_type === "BUY" ? "compra" : "venda";
    const accountLabel = last.is_real ? "carteira real" : "simulador";
    return {
      title: "Ultima acao registrada",
      text: `Sua ultima ${actionLabel} foi em ${last.ticker}, com ${last.quantity} unidade(s) a R$ ${formatCurrency(last.price_at_order)} no ${accountLabel}.`,
    };
  }, [filtered]);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <RefreshCw className="w-8 h-8 animate-spin text-primary" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="glass-card p-4 rounded-xl border border-surface-light">
        <h4 className="text-sm font-semibold text-(--text-primary)">Resumo rapido</h4>
        <p className="text-xs text-(--text-secondary) mt-1">
          Neste filtro voce tem {summary.total} operacoes: {summary.buys} compra(s) e {summary.sells} venda(s).
        </p>
        {latestAction && (
          <p className="text-xs text-(--text-muted) mt-2">
            <strong className="text-(--text-secondary)">{latestAction.title}:</strong> {latestAction.text}
          </p>
        )}
      </div>

      <div className="glass-card p-4 rounded-xl border border-surface-light flex items-center justify-between">
        <div className="flex items-center gap-2">
          <button
            onClick={() => setScope("all")}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold ${
              scope === "all" ? "bg-primary text-white" : "bg-surface-light text-(--text-secondary)"
            }`}
          >
            Todos
          </button>
          <button
            onClick={() => setScope("simulated")}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold ${
              scope === "simulated" ? "bg-primary text-white" : "bg-surface-light text-(--text-secondary)"
            }`}
          >
            Simulado
          </button>
          <button
            onClick={() => setScope("real")}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold ${
              scope === "real" ? "bg-primary text-white" : "bg-surface-light text-(--text-secondary)"
            }`}
          >
            Real
          </button>
        </div>
        <button
          onClick={fetchHistory}
          className="p-2 rounded-xl bg-surface-light text-text-secondary hover:text-primary-light transition-colors"
          title="Atualizar histórico"
        >
          <RefreshCw className={`w-5 h-5 ${isRefreshing ? "animate-spin" : ""}`} />
        </button>
      </div>

      <div className="glass-card rounded-2xl border border-surface-light overflow-hidden">
        <div className="p-6 border-b border-surface-light">
          <h3 className="font-bold text-(--text-primary)">Historico de operacoes</h3>
        </div>

        {filtered.length === 0 ? (
          <div className="p-10 text-center text-(--text-secondary)">
            Nenhuma ordem encontrada no filtro selecionado.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left">
              <thead>
                <tr className="bg-surface-light/50 text-(--text-muted) text-xs uppercase tracking-wider">
                  <th className="px-6 py-4 font-semibold">Data</th>
                  <th className="px-6 py-4 font-semibold">Ativo</th>
                  <th className="px-6 py-4 font-semibold">Tipo</th>
                  <th className="px-6 py-4 font-semibold text-right">Qtd</th>
                  <th className="px-6 py-4 font-semibold text-right">Preco</th>
                  <th className="px-6 py-4 font-semibold">Conta</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-surface-light">
                {filtered.map((order) => (
                  <tr key={order.order_id} className="hover:bg-surface-light/30 transition-colors">
                    <td className="px-6 py-4 text-(--text-secondary)">
                      {new Date(order.order_date).toLocaleString("pt-BR")}
                    </td>
                    <td className="px-6 py-4 font-bold text-(--text-primary)">{order.ticker}</td>
                    <td
                      className={`px-6 py-4 font-semibold ${
                        order.order_type === "BUY" ? "text-(--success)" : "text-(--warning)"
                      }`}
                    >
                      {order.order_type === "BUY" ? "Compra" : "Venda"}
                    </td>
                    <td className="px-6 py-4 text-right text-(--text-secondary)">{order.quantity}</td>
                    <td className="px-6 py-4 text-right text-(--text-secondary)">
                      R$ {formatCurrency(order.price_at_order)}
                    </td>
                    <td className="px-6 py-4 text-(--text-secondary)">
                      {order.is_real ? "Real" : "Simulada"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
