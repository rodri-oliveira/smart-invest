"""Sistema de alertas de rebalanceamento."""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

from aim.data_layer.database import Database
from aim.scoring.engine import get_top_ranked_assets

logger = logging.getLogger(__name__)


class AlertType(Enum):
    REBALANCE_SELL = "rebalance_sell"  # Ativo saiu do top 20 - vender
    REBALANCE_BUY = "rebalance_buy"    # Novo ativo entrou no top 5 - comprar
    SECTOR_CONCENTRATION = "sector_concentration"  # Concentração setorial alta
    STOP_LOSS = "stop_loss"            # Ativo caiu muito - stop
    TARGET_PROFIT = "target_profit"   # Ativo subiu muito - realizar lucro


@dataclass
class RebalanceAlert:
    """Alerta de rebalanceamento."""
    type: AlertType
    ticker: str
    message: str
    priority: int  # 1-5, sendo 1 o mais urgente
    current_position: Optional[int] = None  # Posição atual no ranking
    previous_position: Optional[int] = None  # Posição anterior no ranking
    suggested_action: str = ""
    timestamp: str = ""


class RebalancingMonitor:
    """Monitor de rebalanceamento de carteiras."""
    
    def __init__(self, db: Database):
        self.db = db
    
    def check_portfolio_health(
        self,
        portfolio_id: int,
        current_holdings: List[Dict]
    ) -> List[RebalanceAlert]:
        """
        Verifica saúde da carteira e gera alertas de rebalanceamento.
        
        Args:
            portfolio_id: ID da carteira
            current_holdings: Lista de posições atuais [{ticker, weight}]
            
        Returns:
            Lista de alertas ordenados por prioridade
        """
        alerts = []
        
        # 1. Verificar se ativos da carteira ainda estão no top 20
        top_20 = get_top_ranked_assets(self.db, top_n=20)
        top_20_tickers = set(top_20["ticker"].tolist()) if not top_20.empty else set()
        
        for holding in current_holdings:
            ticker = holding["ticker"]
            if ticker not in top_20_tickers:
                # Ativo saiu do top 20
                alerts.append(RebalanceAlert(
                    type=AlertType.REBALANCE_SELL,
                    ticker=ticker,
                    message=f"{ticker} saiu do top 20 de scores. Considere vender.",
                    priority=2,
                    suggested_action="VENDER",
                    timestamp=datetime.now().isoformat()
                ))
        
        # 2. Verificar novas oportunidades no top 5 que não estão na carteira
        top_5 = get_top_ranked_assets(self.db, top_n=5)
        current_tickers = {h["ticker"] for h in current_holdings}
        
        if not top_5.empty:
            for _, row in top_5.iterrows():
                ticker = row["ticker"]
                if ticker not in current_tickers:
                    # Nova oportunidade no top 5
                    rank = int(row.get("rank_universe", 0))
                    alerts.append(RebalanceAlert(
                        type=AlertType.REBALANCE_BUY,
                        ticker=ticker,
                        message=f"{ticker} entrou no top 5 (rank #{rank}). Considere comprar.",
                        priority=1,
                        current_position=rank,
                        suggested_action="COMPRAR",
                        timestamp=datetime.now().isoformat()
                    ))
        
        # 3. Ordenar por prioridade
        alerts.sort(key=lambda x: x.priority)
        
        return alerts
    
    def get_alerts_for_user(self, user_id: Optional[int] = None) -> List[RebalanceAlert]:
        """Busca todos os alertas pendentes para um usuário."""
        # Por enquanto, retorna alertas baseados na carteira mais recente
        # TODO: Implementar persistência de alertas no banco
        
        # Buscar carteira mais recente
        portfolio = self.db.fetch_one(
            "SELECT portfolio_id FROM portfolios ORDER BY created_at DESC LIMIT 1"
        )
        
        if not portfolio:
            return []
        
        # Buscar holdings da carteira
        holdings = self.db.fetch_all(
            "SELECT ticker, weight FROM portfolio_holdings WHERE portfolio_id = ?",
            (portfolio["portfolio_id"],)
        )
        
        return self.check_portfolio_health(portfolio["portfolio_id"], holdings)
    
    def save_alert(self, alert: RebalanceAlert, user_id: int):
        """Salva alerta no banco para histórico."""
        # TODO: Implementar tabela de alertas
        logger.info(f"Alerta salvo: {alert.ticker} - {alert.message}")


def format_alerts_for_display(alerts: List[RebalanceAlert]) -> List[Dict]:
    """Formata alertas para exibição no frontend."""
    return [
        {
            "type": alert.type.value,
            "ticker": alert.ticker,
            "message": alert.message,
            "priority": alert.priority,
            "priority_label": "URGENTE" if alert.priority == 1 else "ALTA" if alert.priority == 2 else "MÉDIA",
            "suggested_action": alert.suggested_action,
            "timestamp": alert.timestamp,
        }
        for alert in alerts
    ]
