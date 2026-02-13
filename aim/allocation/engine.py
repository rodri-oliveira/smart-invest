"""Allocation Engine - construção e rebalanceamento de carteiras."""

import logging
from typing import Dict, List, Optional, Tuple

import pandas as pd

from aim.config.parameters import (
    DEFAULT_UNIVERSE,
    MAX_POSITION_SIZE,
    MIN_POSITION_SIZE,
    TARGET_RV_ALLOCATION,
)
from aim.data_layer.database import Database
from aim.risk.manager import (
    calculate_position_size_equal_weight,
    calculate_position_size_risk_based,
    validate_portfolio_constraints,
)
from aim.scoring.engine import get_top_ranked_assets

logger = logging.getLogger(__name__)


def build_portfolio_from_scores(
    db: Database,
    date: Optional[str] = None,
    n_positions: int = 10,
    strategy: str = "equal_weight",
    regime: Optional[str] = None,
) -> List[Dict]:
    """
    Constrói carteira a partir dos scores calculados.
    
    Args:
        db: Conexão com banco
        date: Data de referência
        n_positions: Número de posições
        strategy: Estratégia de alocação (equal_weight, risk_parity, score_weighted)
        regime: Regime de mercado (se None, busca do banco)
    
    Returns:
        Lista de posições [{ticker, weight, score}]
    """
    logger.info(f"Construindo carteira: {strategy}, {n_positions} posições")
    
    # 1. Obter regime atual se não informado
    if regime is None:
        from aim.regime.engine import get_current_regime
        regime_data = get_current_regime(db)
        regime = regime_data["regime"] if regime_data else "TRANSITION"
    
    logger.info(f"Regime: {regime}")
    
    # 2. Obter top ativos ranqueados
    top_assets = get_top_ranked_assets(db, date=date, top_n=n_positions * 2)  # Pegar mais para filtrar
    
    if top_assets.empty:
        logger.error("Sem dados de ranking disponíveis")
        return []
    
    # 3. Filtrar apenas os top N
    selected = top_assets.head(n_positions)
    
    # 4. Calcular pesos conforme estratégia
    holdings = []
    
    if strategy == "equal_weight":
        weight = calculate_position_size_equal_weight(n_positions, regime)
        for _, row in selected.iterrows():
            holdings.append({
                "ticker": row["ticker"],
                "weight": weight,
                "score": row["score_final"],
                "sector": row.get("sector", "UNKNOWN"),
            })
    
    elif strategy == "score_weighted":
        # Peso proporcional ao score
        total_score = selected["score_final"].sum()
        if total_score > 0:
            for _, row in selected.iterrows():
                weight = (row["score_final"] / total_score) * TARGET_RV_ALLOCATION.get(regime, 0.8)
                # Limitar pelo máximo por posição
                max_pos = MAX_POSITION_SIZE.get(regime, 0.12)
                weight = min(weight, max_pos)
                holdings.append({
                    "ticker": row["ticker"],
                    "weight": weight,
                    "score": row["score_final"],
                    "sector": row.get("sector", "UNKNOWN"),
                })
    
    elif strategy == "risk_parity":
        # Usar volatilidade para ajustar pesos
        for _, row in selected.iterrows():
            vol = row.get("score_volatility", 0.15)  # Default 15% vol
            weight = calculate_position_size_risk_based(
                volatility=abs(vol),
                target_portfolio_vol=0.15,
            )
            # Limitar pelo máximo do regime
            max_pos = MAX_POSITION_SIZE.get(regime, 0.12)
            weight = min(weight, max_pos)
            holdings.append({
                "ticker": row["ticker"],
                "weight": weight,
                "score": row["score_final"],
                "sector": row.get("sector", "UNKNOWN"),
            })
    
    # 5. Normalizar para somar 100% da alocação alvo
    target_allocation = TARGET_RV_ALLOCATION.get(regime, 0.8)
    total_weight = sum(h["weight"] for h in holdings)
    
    if total_weight > 0:
        factor = target_allocation / total_weight
        for holding in holdings:
            holding["weight"] = min(
                holding["weight"] * factor,
                MAX_POSITION_SIZE.get(regime, 0.12)
            )
    
    # 6. Validar restrições
    weights_dict = {h["ticker"]: h["weight"] for h in holdings}
    is_valid, violations = validate_portfolio_constraints(weights_dict, regime)
    
    if not is_valid:
        logger.warning("Violações de restrição encontradas:")
        for v in violations:
            logger.warning(f"  - {v}")
    
    logger.info(f"✓ Carteira construída com {len(holdings)} posições")
    logger.info(f"  Alocação total: {sum(h['weight'] for h in holdings):.1%}")
    
    return holdings


def calculate_rebalance_trades(
    current_holdings: Dict[str, float],
    target_holdings: Dict[str, float],
    threshold: float = 0.02,
) -> List[Dict]:
    """
    Calcula trades necessários para rebalanceamento.
    
    Args:
        current_holdings: {ticker: peso_atual}
        target_holdings: {ticker: peso_alvo}
        threshold: Limiar mínimo de diferença para trade (2%)
    
    Returns:
        Lista de trades [{ticker, action, current_weight, target_weight, diff}]
    """
    trades = []
    all_tickers = set(current_holdings.keys()) | set(target_holdings.keys())
    
    for ticker in all_tickers:
        current = current_holdings.get(ticker, 0.0)
        target = target_holdings.get(ticker, 0.0)
        diff = target - current
        
        # Só rebalancear se diferença for significativa
        if abs(diff) >= threshold:
            if diff > 0:
                action = "BUY"
            else:
                action = "SELL"
            
            trades.append({
                "ticker": ticker,
                "action": action,
                "current_weight": current,
                "target_weight": target,
                "diff": diff,
            })
    
    # Ordenar: SELL primeiro (libera caixa), depois BUY
    trades.sort(key=lambda x: (x["action"] != "SELL", x["ticker"]))
    
    logger.info(f"Trades de rebalanceamento: {len(trades)}")
    for trade in trades:
        logger.info(f"  {trade['action']} {trade['ticker']}: {trade['current_weight']:.1%} -> {trade['target_weight']:.1%}")
    
    return trades


def save_portfolio_to_database(
    db: Database,
    portfolio_name: str,
    holdings: List[Dict],
    date: Optional[str] = None,
) -> int:
    """
    Salva carteira no banco de dados.
    
    Args:
        db: Conexão com banco
        portfolio_name: Nome da carteira
        holdings: Lista de posições
        date: Data do rebalanceamento
    
    Returns:
        ID da carteira
    """
    if date is None:
        from datetime import datetime
        date = datetime.now().strftime("%Y-%m-%d")
    
    # 1. Obter ou criar portfolio
    portfolio = db.fetch_one(
        "SELECT portfolio_id FROM portfolios WHERE name = ?",
        (portfolio_name,)
    )
    
    if portfolio:
        portfolio_id = portfolio["portfolio_id"]
    else:
        portfolio_id = db.insert("portfolios", {
            "name": portfolio_name,
            "description": f"Carteira quantitativa - {portfolio_name}",
            "strategy": "multi_factor",
            "is_active": True,
            "is_simulated": True,
        })
    
    # 2. Salvar holdings
    for holding in holdings:
        db.upsert(
            "portfolio_holdings",
            {
                "portfolio_id": portfolio_id,
                "ticker": holding["ticker"],
                "date": date,
                "weight": holding["weight"],
                "status": "ACTIVE",
            },
            conflict_columns=["portfolio_id", "ticker", "date"],
        )
    
    logger.info(f"✓ Carteira '{portfolio_name}' salva: {len(holdings)} posições")
    
    return portfolio_id


def generate_portfolio_report(
    db: Database,
    portfolio_name: str,
    date: Optional[str] = None,
) -> Dict:
    """
    Gera relatório de carteira.
    
    Args:
        db: Conexão com banco
        portfolio_name: Nome da carteira
        date: Data de referência
    
    Returns:
        Dict com informações da carteira
    """
    if date is None:
        date_query = "SELECT MAX(date) as max_date FROM portfolio_holdings"
        result = db.fetch_one(date_query)
        date = result["max_date"] if result else None
    
    if not date:
        return {"error": "Sem dados de carteira"}
    
    # Buscar holdings
    query = """
        SELECT 
            h.ticker,
            h.weight,
            h.price_entry,
            a.sector,
            a.name
        FROM portfolio_holdings h
        JOIN portfolios p ON h.portfolio_id = p.portfolio_id
        JOIN assets a ON h.ticker = a.ticker
        WHERE p.name = ?
        AND h.date = ?
        AND h.status = 'ACTIVE'
    """
    
    df = db.query_to_df(query, (portfolio_name, date))
    
    if df.empty:
        return {"error": f"Sem dados para {portfolio_name} em {date}"}
    
    # Calcular estatísticas
    total_weight = df["weight"].sum()
    n_positions = len(df)
    
    # Exposição por setor
    sector_exposure = df.groupby("sector")["weight"].sum().to_dict()
    
    return {
        "portfolio_name": portfolio_name,
        "date": date,
        "n_positions": n_positions,
        "total_weight": total_weight,
        "sector_exposure": sector_exposure,
        "holdings": df.to_dict("records"),
    }
