import React, { useEffect, useState } from 'react';
import { 
  TrendingUp, 
  TrendingDown, 
  Plus, 
  Search,
  ArrowUpRight,
  ArrowDownRight,
  RefreshCw,
  ShoppingBag,
  AlertTriangle
} from 'lucide-react';
import { simulationService, SimulatedPosition, OperationAlert } from '@/services/simulation';

interface SimulatorViewProps {
  isReal?: boolean;
}

export default function SimulatorView({ isReal = false }: SimulatorViewProps) {
  const [positions, setPositions] = useState<SimulatedPosition[]>([]);
  const [alerts, setAlerts] = useState<OperationAlert[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);

  const fetchPositions = async () => {
    setIsRefreshing(true);
    try {
      const [posData, alertData] = await Promise.all([
        simulationService.getPositions(isReal),
        simulationService.getAlerts()
      ]);
      setPositions(posData);
      setAlerts(alertData.filter(a => a.is_real === isReal));
    } catch (error) {
      console.error(`Erro ao buscar dados:`, error);
    } finally {
      setIsLoading(false);
      setIsRefreshing(false);
    }
  };

  useEffect(() => {
    fetchPositions();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isReal]);

  const totalCost = positions.reduce((acc, pos) => acc + pos.total_cost, 0);
  const currentValue = positions.reduce((acc, pos) => acc + (pos.quantity * pos.current_price), 0);
  const totalPL = currentValue - totalCost;
  const totalPLPct = totalCost > 0 ? (totalPL / totalCost) * 100 : 0;

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <RefreshCw className="w-8 h-8 animate-spin text-primary" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Alertas Operacionais */}
      {alerts.length > 0 && (
        <div className="space-y-2">
          {alerts.map((alert, idx) => (
          <div 
              key={`${alert.ticker}-${idx}`}
              className={`flex items-center gap-3 p-4 rounded-xl border ${
                alert.severity === 'HIGH' ? 'bg-red-500/10 border-red-500/30 text-red-400' :
                alert.severity === 'MEDIUM' ? 'bg-amber-500/10 border-amber-500/30 text-amber-400' :
                'bg-blue-500/10 border-blue-500/30 text-blue-400'
              }`}
            >
            <AlertTriangle className="w-5 h-5 shrink-0" />
            <div className="flex-1">
              <span className="font-bold mr-2">{alert.ticker}</span>
              <span className="text-sm">{alert.message}</span>
            </div>
              <button 
                onClick={() => {
                  const qty = window.prompt(`Simular ajuste para ${alert.ticker}. Quantidade?`, "0");
                  if (qty) simulationService.createOrder(alert.ticker, 'SELL', parseInt(qty), isReal).then(() => fetchPositions());
                }}
                className="px-3 py-1 rounded-lg bg-surface-light hover:bg-white/10 transition-colors text-xs font-bold"
              >
                Ajustar
              </button>
            </div>
          ))}
        </div>
      )}

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="glass-card p-6 rounded-2xl border border-surface-light">
          <div className="text-sm text-text-muted mb-1">
            {isReal ? 'Patrimônio Real' : 'Patrimônio Simulado'}
          </div>
          <div className="text-2xl font-bold text-text-primary">R$ {currentValue.toLocaleString('pt-BR', { minimumFractionDigits: 2 })}</div>
        </div>
        
        <div className="glass-card p-6 rounded-2xl border border-surface-light">
          <div className="text-sm text-text-muted mb-1">Resultado Total</div>
          <div className={`text-2xl font-bold flex items-center gap-2 ${totalPL >= 0 ? 'text-success' : 'text-error'}`}>
            R$ {Math.abs(totalPL).toLocaleString('pt-BR', { minimumFractionDigits: 2 })}
            <span className="text-sm font-medium">({totalPLPct.toFixed(2)}%)</span>
            {totalPL >= 0 ? <TrendingUp className="w-5 h-5" /> : <TrendingDown className="w-5 h-5" />}
          </div>
        </div>

        <div className="glass-card p-6 rounded-2xl border border-surface-light flex items-center justify-between">
          <div>
            <div className="text-sm text-text-muted mb-1">Posições Ativas</div>
            <div className="text-2xl font-bold text-text-primary">{positions.length}</div>
          </div>
          <button 
            onClick={fetchPositions}
            className="p-2 rounded-xl bg-surface-light text-text-secondary hover:text-primary-light transition-colors"
          >
            <RefreshCw className={`w-5 h-5 ${isRefreshing ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      {/* Positions Table */}
      <div className="glass-card rounded-2xl border border-surface-light overflow-hidden">
        <div className="p-6 border-b border-surface-light flex items-center justify-between">
          <h3 className="font-bold text-(--text-primary)">Ativos em Acompanhamento</h3>
          <div className="flex gap-2">
            <div className="relative">
              <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-(--text-muted)" />
              <input 
                type="text" 
                placeholder="Buscar ativo..." 
                className="pl-9 pr-4 py-2 bg-surface-light border-none rounded-xl text-sm focus:ring-1 focus:ring-primary w-48"
              />
            </div>
          </div>
        </div>

        {positions.length === 0 ? (
          <div className="p-12 text-center">
            <ShoppingBag className="w-12 h-12 mx-auto mb-4 text-(--text-muted) opacity-20" />
            <p className="text-(--text-secondary) mb-4">
              {isReal ? 'Sua carteira real está vazia.' : 'Nenhuma simulação ativa no momento.'}
            </p>
            <button className="px-6 py-2 bg-primary hover:bg-primary-light text-white rounded-xl font-medium transition-all inline-flex items-center gap-2">
              <Plus className="w-4 h-4" />
              {isReal ? 'Registrar Compra' : 'Nova Simulação'}
            </button>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left">
              <thead>
                <tr className="bg-surface-light/50 text-(--text-muted) text-xs uppercase tracking-wider">
                  <th className="px-6 py-4 font-semibold">Ativo</th>
                  <th className="px-6 py-4 font-semibold text-right">Qtd</th>
                  <th className="px-6 py-4 font-semibold text-right">Preço Médio</th>
                  <th className="px-6 py-4 font-semibold text-right">Preço Atual</th>
                  <th className="px-6 py-4 font-semibold text-right">Resultado</th>
                  <th className="px-6 py-4 font-semibold text-center">Ações</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-surface-light">
                {positions.map((pos) => (
                  <tr key={pos.ticker} className="hover:bg-surface-light/30 transition-colors group">
                    <td className="px-6 py-4">
                      <div className="font-bold text-(--text-primary)">{pos.ticker}</div>
                    </td>
                    <td className="px-6 py-4 text-right text-(--text-secondary)">{pos.quantity}</td>
                    <td className="px-6 py-4 text-right text-(--text-secondary)">R$ {pos.avg_price.toFixed(2)}</td>
                    <td className="px-6 py-4 text-right">
                      <div className="font-medium text-(--text-primary)">R$ {pos.current_price.toFixed(2)}</div>
                    </td>
                    <td className="px-6 py-4 text-right">
                      <div className={`font-bold flex items-center justify-end gap-1 ${pos.profit_loss >= 0 ? 'text-(--success)' : 'text-(--error)'}`}>
                        {pos.profit_loss_pct >= 0 ? <ArrowUpRight className="w-3 h-3" /> : <ArrowDownRight className="w-3 h-3" />}
                        {pos.profit_loss_pct.toFixed(2)}%
                      </div>
                      <div className="text-[10px] text-(--text-muted)">
                        R$ {pos.profit_loss.toFixed(2)}
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      <div className="flex items-center justify-center gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
                        <button 
                          onClick={() => {
                            const qty = window.prompt(`Quantas ações de ${pos.ticker} deseja comprar?`, "100");
                            if (qty) simulationService.createOrder(pos.ticker, 'BUY', parseInt(qty), isReal).then(() => fetchPositions());
                          }}
                          className="p-1.5 rounded-lg bg-surface-light text-(--text-secondary) hover:text-primary transition-colors" 
                          title="Comprar mais"
                        >
                          <Plus className="w-4 h-4" />
                        </button>
                        <button 
                          onClick={() => {
                            const qty = window.prompt(`Quantas ações de ${pos.ticker} deseja vender?`, pos.quantity.toString());
                            if (qty) simulationService.createOrder(pos.ticker, 'SELL', parseInt(qty), isReal).then(() => fetchPositions());
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
          </div>
        )}
      </div>

      {/* Alertas Operacionais (Placeholder para lógica futura) */}
      <div className="p-4 rounded-xl bg-(--primary-muted) border border-primary-light/20">
        <h4 className="text-sm font-semibold text-primary-light mb-1 flex items-center gap-2">
          <TrendingUp className="w-4 h-4" />
          Insight Operacional
        </h4>
        <p className="text-xs text-(--text-secondary) leading-relaxed">
          O sistema está monitorando suas posições. Quando um ativo atingir o critério de rebalanceamento ou stop, você receberá um alerta aqui para simular a operação.
        </p>
      </div>
    </div>
  );
}
