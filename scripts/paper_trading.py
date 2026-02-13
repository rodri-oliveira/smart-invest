#!/usr/bin/env python3
"""
Paper Trading Module.
Simula operações em tempo real sem dinheiro real.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
import json

from aim.data_layer.database import Database
from aim.scoring.engine import get_top_ranked_assets
from aim.regime.engine import get_current_regime
from aim.allocation.engine import build_portfolio_from_scores

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@dataclass
class PaperPosition:
    """Posição em paper trading."""
    ticker: str
    shares: int
    entry_price: float
    entry_date: str
    weight: float
    current_price: float = 0.0
    current_value: float = 0.0
    pnl: float = 0.0
    pnl_pct: float = 0.0
    stop_loss: float = 0.0


@dataclass
class PaperPortfolio:
    """Carteira de paper trading."""
    name: str
    start_date: str
    initial_capital: float
    current_capital: float
    positions: List[PaperPosition]
    cash: float
    total_value: float
    total_return: float
    total_return_pct: float
    trades_count: int
    winning_trades: int
    losing_trades: int
    max_drawdown: float
    last_rebalance: str


class PaperTradingEngine:
    """
    Motor de paper trading.
    
    Simula operações com regras reais:
    - Rebalanceamento mensal
    - Stops de 15%
    - Regime filters (reduz exposição em RISK OFF)
    """
    
    def __init__(
        self,
        db: Database,
        name: str = "PaperPortfolio",
        initial_capital: float = 100_000.0,
        n_positions: int = 5,
        rebalance_freq: str = "monthly",  # monthly, weekly
    ):
        self.db = db
        self.name = name
        self.initial_capital = initial_capital
        self.n_positions = n_positions
        self.rebalance_freq = rebalance_freq
        
        # Carregar ou criar carteira
        self.portfolio = self._load_or_create_portfolio()
    
    def _load_or_create_portfolio(self) -> PaperPortfolio:
        """Carrega carteira existente ou cria nova."""
        # Verificar se existe no banco
        portfolio = self.db.fetch_one(
            "SELECT * FROM portfolios WHERE name = ?",
            (self.name,)
        )
        
        if portfolio:
            # Carregar posições
            positions = self._load_positions()
            return PaperPortfolio(
                name=self.name,
                start_date=portfolio.get("created_at", datetime.now().strftime("%Y-%m-%d")),
                initial_capital=self.initial_capital,
                current_capital=self._calculate_cash(positions),
                positions=positions,
                cash=self._calculate_cash(positions),
                total_value=self._calculate_total_value(positions),
                total_return=0.0,
                total_return_pct=0.0,
                trades_count=0,
                winning_trades=0,
                losing_trades=0,
                max_drawdown=0.0,
                last_rebalance=datetime.now().strftime("%Y-%m-%d"),
            )
        
        # Criar nova
        return PaperPortfolio(
            name=self.name,
            start_date=datetime.now().strftime("%Y-%m-%d"),
            initial_capital=self.initial_capital,
            current_capital=self.initial_capital,
            positions=[],
            cash=self.initial_capital,
            total_value=self.initial_capital,
            total_return=0.0,
            total_return_pct=0.0,
            trades_count=0,
            winning_trades=0,
            losing_trades=0,
            max_drawdown=0.0,
            last_rebalance=datetime.now().strftime("%Y-%m-%d"),
        )
    
    def _load_positions(self) -> List[PaperPosition]:
        """Carrega posições do banco."""
        # Implementar se houver tabela de paper positions
        return []
    
    def _calculate_cash(self, positions: List[PaperPosition]) -> float:
        """Calcula caixa disponível."""
        invested = sum(p.current_value for p in positions)
        return self.initial_capital - invested
    
    def _calculate_total_value(self, positions: List[PaperPosition]) -> float:
        """Calcula valor total da carteira."""
        cash = self._calculate_cash(positions)
        invested = sum(p.current_value for p in positions)
        return cash + invested
    
    def should_rebalance(self) -> bool:
        """Verifica se é hora de rebalancear."""
        last = datetime.strptime(self.portfolio.last_rebalance, "%Y-%m-%d")
        today = datetime.now()
        
        if self.rebalance_freq == "monthly":
            return (today - last).days >= 30
        elif self.rebalance_freq == "weekly":
            return (today - last).days >= 7
        
        return False
    
    def check_stops(self) -> List[str]:
        """Verifica stops atingidos."""
        stops_triggered = []
        
        for position in self.portfolio.positions:
            # Stop de 15%
            stop_price = position.entry_price * 0.85
            
            if position.current_price <= stop_price:
                stops_triggered.append(position.ticker)
                logger.info(f"🛑 Stop atingido: {position.ticker} ({position.pnl_pct:+.1%})")
        
        return stops_triggered
    
    def rebalance(self) -> Dict:
        """
        Executa rebalanceamento da carteira.
        
        1. Verifica regime
        2. Seleciona novos ativos
        3. Calcula alocação
        4. Executa trades virtuais
        """
        logger.info("=" * 60)
        logger.info("REBALANCEAMENTO PAPER TRADING")
        logger.info("=" * 60)
        
        # 1. Verificar regime
        regime_data = get_current_regime(self.db)
        if not regime_data:
            logger.error("Sem dados de regime")
            return {"error": "Sem regime"}
        
        regime = regime_data["regime"]
        logger.info(f"Regime atual: {regime} (score: {regime_data['score_total']:.2f})")
        
        # 2. Construir nova carteira
        target_holdings = build_portfolio_from_scores(
            self.db,
            n_positions=self.n_positions,
            strategy="equal_weight",
            regime=regime,
        )
        
        if not target_holdings:
            logger.error("Não foi possível construir carteira")
            return {"error": "Sem carteira"}
        
        logger.info(f"Nova carteira: {[h['ticker'] for h in target_holdings]}")
        
        # 3. Calcular trades
        current_tickers = {p.ticker for p in self.portfolio.positions}
        target_tickers = {h["ticker"] for h in target_holdings}
        
        sells = current_tickers - target_tickers
        buys = target_tickers - current_tickers
        
        # 4. Executar vendas
        for ticker in sells:
            position = next((p for p in self.portfolio.positions if p.ticker == ticker), None)
            if position:
                # Vender
                proceeds = position.current_value
                self.portfolio.cash += proceeds
                self.portfolio.positions.remove(position)
                self.portfolio.trades_count += 1
                
                if position.pnl > 0:
                    self.portfolio.winning_trades += 1
                else:
                    self.portfolio.losing_trades += 1
                
                logger.info(f"📉 VENDA: {ticker} @ {position.current_price:.2f} ({position.pnl_pct:+.1%})")
        
        # 5. Executar compras
        for holding in target_holdings:
            ticker = holding["ticker"]
            weight = holding["weight"]
            
            # Buscar preço atual
            price_data = self.db.fetch_one(
                "SELECT close FROM prices WHERE ticker = ? ORDER BY date DESC LIMIT 1",
                (ticker,)
            )
            
            if not price_data:
                logger.warning(f"Sem preço para {ticker}")
                continue
            
            price = price_data["close"]
            amount = self.portfolio.total_value * weight
            shares = int(amount / price)
            
            if shares > 0:
                cost = shares * price
                if cost <= self.portfolio.cash:
                    # Comprar
                    position = PaperPosition(
                        ticker=ticker,
                        shares=shares,
                        entry_price=price,
                        entry_date=datetime.now().strftime("%Y-%m-%d"),
                        weight=weight,
                        current_price=price,
                        current_value=cost,
                        stop_loss=price * 0.85,
                    )
                    self.portfolio.positions.append(position)
                    self.portfolio.cash -= cost
                    self.portfolio.trades_count += 1
                    
                    logger.info(f"📈 COMPRA: {ticker} - {shares} shares @ {price:.2f} ({weight:.1%})")
        
        # 6. Atualizar data de rebalanceamento
        self.portfolio.last_rebalance = datetime.now().strftime("%Y-%m-%d")
        
        # 7. Salvar no banco
        self._save_portfolio()
        
        return {
            "regime": regime,
            "sells": list(sells),
            "buys": list(buys),
            "positions": len(self.portfolio.positions),
            "cash": self.portfolio.cash,
            "total_value": self._calculate_total_value(self.portfolio.positions),
        }
    
    def update_prices(self) -> Dict:
        """Atualiza preços das posições."""
        total_value = self.portfolio.cash
        
        for position in self.portfolio.positions:
            # Buscar preço atual
            price_data = self.db.fetch_one(
                "SELECT close FROM prices WHERE ticker = ? ORDER BY date DESC LIMIT 1",
                (position.ticker,)
            )
            
            if price_data:
                position.current_price = price_data["close"]
                position.current_value = position.shares * position.current_price
                position.pnl = position.current_value - (position.shares * position.entry_price)
                position.pnl_pct = position.pnl / (position.shares * position.entry_price)
                
                total_value += position.current_value
        
        self.portfolio.total_value = total_value
        self.portfolio.total_return = total_value - self.initial_capital
        self.portfolio.total_return_pct = self.portfolio.total_return / self.initial_capital
        
        return {
            "total_value": total_value,
            "total_return": self.portfolio.total_return,
            "total_return_pct": self.portfolio.total_return_pct,
            "positions": len(self.portfolio.positions),
        }
    
    def get_report(self) -> Dict:
        """Gera relatório da carteira."""
        self.update_prices()
        
        return {
            "name": self.portfolio.name,
            "start_date": self.portfolio.start_date,
            "days_running": (datetime.now() - datetime.strptime(self.portfolio.start_date, "%Y-%m-%d")).days,
            "initial_capital": self.portfolio.initial_capital,
            "current_value": self.portfolio.total_value,
            "total_return": self.portfolio.total_return_pct,
            "cash": self.portfolio.cash,
            "positions": [
                {
                    "ticker": p.ticker,
                    "shares": p.shares,
                    "entry": p.entry_price,
                    "current": p.current_price,
                    "value": p.current_value,
                    "pnl": p.pnl_pct,
                }
                for p in self.portfolio.positions
            ],
            "trades": {
                "total": self.portfolio.trades_count,
                "winning": self.portfolio.winning_trades,
                "losing": self.portfolio.losing_trades,
                "win_rate": self.portfolio.winning_trades / max(self.portfolio.trades_count, 1),
            },
            "next_rebalance": self.portfolio.last_rebalance,
        }
    
    def _save_portfolio(self):
        """Salva carteira no banco."""
        # Implementar persistência
        pass


def main():
    """Paper trading CLI."""
    print("=" * 60)
    print("Paper Trading - Simulação em Tempo Real")
    print("=" * 60)
    
    db = Database()
    engine = PaperTradingEngine(
        db,
        name="PaperPortfolio_v1",
        initial_capital=100_000.0,
        n_positions=5,
    )
    
    # Verificar se precisa rebalancear
    if engine.should_rebalance():
        result = engine.rebalance()
        print(f"\nRebalanceamento executado:")
        print(f"  Regime: {result.get('regime')}")
        print(f"  Posições: {result.get('positions')}")
        print(f"  Cash: R$ {result.get('cash', 0):,.2f}")
    else:
        print("\nNão é hora de rebalancear ainda.")
    
    # Mostrar relatório
    report = engine.get_report()
    
    print("\n" + "=" * 60)
    print("RELATÓRIO DA CARTEIRA")
    print("=" * 60)
    print(f"Valor inicial: R$ {report['initial_capital']:,.2f}")
    print(f"Valor atual: R$ {report['current_value']:,.2f}")
    print(f"Retorno: {report['total_return']:+.2%}")
    print(f"Dias operando: {report['days_running']}")
    print(f"\nPosições ({len(report['positions'])}):")
    
    for pos in report['positions']:
        print(f"  {pos['ticker']:6s} - {pos['shares']:4d} shares @ R$ {pos['current']:7.2f} ({pos['pnl']:+.1%})")
    
    print(f"\nTrades: {report['trades']['total']} (Win: {report['trades']['winning']}, Loss: {report['trades']['losing']})")
    print(f"Win rate: {report['trades']['win_rate']:.1%}")
    print("=" * 60)


if __name__ == "__main__":
    main()
