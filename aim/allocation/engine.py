"""Allocation Engine - construção e rebalanceamento de carteiras."""

import logging
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

from aim.config.parameters import (
    DEFAULT_UNIVERSE,
    MAX_ASSET_EXPOSURE_BY_REGIME,
    MAX_POSITION_SIZE,
    MAX_SECTOR_EXPOSURE_BY_REGIME,
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
    priority_factors: Optional[List[str]] = None,
) -> Tuple[List[Dict], Dict[str, float], Dict[str, Any]] | List[Dict]:
    """
    Constrói carteira a partir dos scores calculados.
    
    Args:
        db: Conexão com banco
        date: Data de referência
        n_positions: Número de posições
        strategy: Estratégia de alocação (equal_weight, risk_parity, score_weighted)
        regime: Regime de mercado (se None, busca do banco)
        priority_factors: Fatores prioritários do prompt (momentum, value, quality, etc.)
    
    Returns:
        Lista de posições [{ticker, weight, score}]
    """
    logger.info(f"Construindo carteira: {strategy}, {n_positions} posições, fatores: {priority_factors}")
    
    # 1. Obter regime atual se não informado
    if regime is None:
        from aim.regime.engine import get_current_regime
        regime_data = get_current_regime(db)
        regime = regime_data["regime"] if regime_data else "TRANSITION"
    
    logger.info(f"Regime: {regime}")
    target_allocation = TARGET_RV_ALLOCATION.get(regime, 0.8)
    allocation_note = ""
    positive_score_count = 0
    
    # 2. Obter top ativos ranqueados
    # score_weighted precisa de um universo maior para reduzir subalocação.
    candidate_multiplier = 8 if strategy == "score_weighted" else 3
    top_assets = get_top_ranked_assets(
        db, date=date, top_n=n_positions * candidate_multiplier
    )
    
    if top_assets.empty:
        logger.error("Sem dados de ranking disponíveis")
        return []
    
    # 2.1 Se há fatores prioritários do prompt, recalcular scores ponderando esses fatores
    if priority_factors and len(priority_factors) > 0:
        logger.info(f"Aplicando prioridade aos fatores: {priority_factors}")
        
        # Definir pesos para cada fator
        factor_weights = {
            'momentum': 0.15,
            'quality': 0.15,
            'value': 0.15,
            'volatility': 0.15,
            'liquidity': 0.10,
        }
        
        # Aumentar peso dos fatores prioritários
        for factor in priority_factors:
            if factor in factor_weights:
                factor_weights[factor] = 0.35  # Dá mais peso aos fatores do prompt
        
        # Normalizar pesos
        total_weight = sum(factor_weights.values())
        factor_weights = {k: v/total_weight for k, v in factor_weights.items()}
        
        # Recalcular score_final ponderado
        top_assets['score_original'] = top_assets['score_final']
        top_assets['score_final'] = (
            top_assets.get('score_momentum', 0) * factor_weights.get('momentum', 0.2) +
            top_assets.get('score_quality', 0) * factor_weights.get('quality', 0.2) +
            top_assets.get('score_value', 0) * factor_weights.get('value', 0.2) +
            top_assets.get('score_volatility', 0) * factor_weights.get('volatility', 0.2) +
            top_assets.get('score_liquidity', 0) * factor_weights.get('liquidity', 0.2)
        )
        
        # Re-ordenar pelo novo score
        top_assets = top_assets.sort_values('score_final', ascending=False)
        
        logger.info(f"Top 5 após reponderação: {top_assets.head(5)[['ticker', 'score_final']].to_dict('records')}")
    
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
        # Validar scores primeiro - remover NaN/None
        raw_scores = selected["score_final"].fillna(0)
        valid_scores = raw_scores[raw_scores > 0]  # Apenas scores positivos
        positive_score_count = len(valid_scores)
        
        if len(valid_scores) == 0:
            logger.warning("Sem scores válidos para score_weighted, usando equal_weight")
            allocation_note = (
                "Nenhum ativo com score positivo no recorte atual. "
                "Aplicado fallback equal_weight."
            )
            weight = calculate_position_size_equal_weight(n_positions, regime)
            for _, row in selected.iterrows():
                holdings.append({
                    "ticker": row["ticker"],
                    "weight": weight,
                    "score": 0.0,
                    "sector": row.get("sector", "UNKNOWN"),
                })
        else:
            # Com poucos scores positivos, deslocamos scores pelo ranking
            # para reduzir caixa em perfis pró-risco.
            if len(valid_scores) < n_positions:
                min_score = raw_scores.min()
                effective_scores = raw_scores - min_score + 1e-6
                allocation_note = (
                    f"Apenas {len(valid_scores)}/{n_positions} ativos tinham score "
                    "positivo. Aplicada redistribuição por ranking."
                )
            else:
                effective_scores = raw_scores.clip(lower=0)

            total_score = effective_scores.sum()
            
            for idx, row in selected.iterrows():
                score = row["score_final"] if pd.notna(row["score_final"]) else 0
                effective_score = effective_scores.loc[idx] if total_score > 0 else 0
                if total_score > 0:
                    # Calcular peso baseado no score relativo
                    weight = (effective_score / total_score) * target_allocation
                    # Limitar pelo máximo por posição
                    max_pos = MAX_POSITION_SIZE.get(regime, 0.12)
                    weight = min(weight, max_pos)
                else:
                    weight = 0.0
                
                holdings.append({
                    "ticker": row["ticker"],
                    "weight": weight,
                    "score": score,
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
    # Log da configuração aplicada
    logger.info(f"Target allocation para regime {regime}: {target_allocation:.1%}")

    # AJUSTE ADICIONAL: Refinar pesos dos fatores baseado no prompt do usuário
    # Isso garante que ativos 'Conservadores' (Value/Quality) tenham peso maior se o prompt for conservador
    if "RISK_OFF" in regime:
        # Aumentar peso de Value e Quality, reduzir Momentum
        for _, row in top_assets.iterrows():
            ticker = row["ticker"]
            # Encontrar na lista de holdings e ajustar score para dar mais peso a quem tem melhores fundamentos
            for h in holdings:
                if h["ticker"] == ticker:
                    # Ajuste artificial do score para priorizar ativos mais estáveis no modo conservador
                    # (Assumindo que score_value e score_quality estão disponíveis no dataframe)
                    h["score"] = (row.get("score_value", 0) * 0.4 + 
                                 row.get("score_quality", 0) * 0.4 + 
                                 row.get("score_momentum", 0) * 0.2)

    total_weight = sum(h["weight"] for h in holdings)
    
    # 5.1 Aplicar limites de exposição setorial rigorosos
    max_sector_exposure = MAX_SECTOR_EXPOSURE_BY_REGIME.get(regime, 0.20)
    
    # Limite por ativo individual baseado no regime (força diversificação)
    max_asset_exposure = MAX_ASSET_EXPOSURE_BY_REGIME.get(regime, 0.06)
    
    # Aplicar limites individuais primeiro
    for h in holdings:
        if h["weight"] > max_asset_exposure:
            h["weight"] = max_asset_exposure
            h["asset_capped"] = True
    
    # Calcular exposição atual por setor
    sector_exposure = {}
    for h in holdings:
        sector = h.get("sector", "UNKNOWN")
        sector_exposure[sector] = sector_exposure.get(sector, 0) + h["weight"]
    
    logger.info(f"Exposição setorial antes do ajuste: {sector_exposure}")
    
    # Reduzir pesos de setores que excederam o limite
    for sector, exposure in sector_exposure.items():
        if exposure > max_sector_exposure:
            # Calcular fator de redução
            reduction_factor = max_sector_exposure / exposure
            logger.warning(f"Setor {sector} excedeu limite ({exposure:.1%} > {max_sector_exposure:.1%}). Reduzindo...")
            
            # Aplicar redução aos ativos desse setor
            for h in holdings:
                if h.get("sector", "UNKNOWN") == sector:
                    h["weight"] = h["weight"] * reduction_factor
                    h["sector_capped"] = True  # Marcar que foi limitado
    
    # Recalcular exposição após ajuste
    sector_exposure = {}
    for h in holdings:
        sector = h.get("sector", "UNKNOWN")
        sector_exposure[sector] = sector_exposure.get(sector, 0) + h["weight"]
    
    logger.info(f"Exposição setorial após ajuste: {sector_exposure}")
    
    # Atualizar total de pesos após ajuste setorial
    total_weight = sum(h["weight"] for h in holdings)
    
    # Validar se o peso total é válido
    if total_weight <= 0 or not pd.notna(total_weight):
        logger.error(f"Peso total inválido: {total_weight}, usando equal_weight")
        # Fallback para equal_weight
        equal_weight = target_allocation / len(holdings) if holdings else 0
        for holding in holdings:
            holding["weight"] = equal_weight
        total_weight = sum(h["weight"] for h in holdings)
    
    if total_weight > 0 and abs(total_weight - target_allocation) > 0.01:
        # Normalizar para atingir a alocação alvo
        factor = target_allocation / total_weight
        for holding in holdings:
            new_weight = holding["weight"] * factor
            # Limitar pelo máximo por posição
            max_pos = MAX_POSITION_SIZE.get(regime, 0.12)
            holding["weight"] = min(new_weight, max_pos)
    
    # NOVO: Redistribuir peso excedente de ativos que atingiram o teto
    final_total = sum(h["weight"] for h in holdings)
    iterations = 0
    max_iterations = 20  # Evitar loop infinito
    
    while abs(final_total - target_allocation) > 0.001 and iterations < max_iterations:
        # Calcular peso disponível para redistribuir
        excess = target_allocation - final_total
        
        # Encontrar ativos que ainda podem receber mais peso (não atingiram o teto)
        uncapped = [h for h in holdings if h["weight"] < MAX_POSITION_SIZE.get(regime, 0.12) - 0.001]
        
        if not uncapped:
            break  # Todos atingiram o teto, não há como redistribuir
            
        # Distribuir o excesso proporcionalmente entre ativos não-capped
        total_uncapped_weight = sum(h["weight"] for h in uncapped)
        if total_uncapped_weight > 0:
            for h in uncapped:
                share = (h["weight"] / total_uncapped_weight) * excess
                max_pos = MAX_POSITION_SIZE.get(regime, 0.12)
                h["weight"] = min(h["weight"] + share, max_pos)
        
        final_total = sum(h["weight"] for h in holdings)
        iterations += 1
    
    # Garantir que todos os pesos são válidos (não NaN, não negativos)
    for holding in holdings:
        if not pd.notna(holding["weight"]) or holding["weight"] < 0:
            holding["weight"] = 0.0
        # Arredondar para evitar precisão excessiva
        holding["weight"] = round(holding["weight"], 4)
    
    # 6. Validar restrições
    weights_dict = {h["ticker"]: h["weight"] for h in holdings}
    is_valid, violations = validate_portfolio_constraints(weights_dict, regime)
    
    if not is_valid:
        logger.warning("Violações de restrição encontradas:")
        for v in violations:
            logger.warning(f"  - {v}")
    
    # 7. Calcular exposição setorial final para retorno
    final_sector_exposure = {}
    for h in holdings:
        sector = h.get("sector", "UNKNOWN")
        final_sector_exposure[sector] = final_sector_exposure.get(sector, 0) + h["weight"]
    
    # Adicionar metadata aos holdings
    for h in holdings:
        h["sector_exposure_pct"] = final_sector_exposure.get(h.get("sector", "UNKNOWN"), 0)
    
    logger.info(f"✓ Carteira construída com {len(holdings)} posições")
    logger.info(f"  Alocação total: {sum(h['weight'] for h in holdings):.1%}")
    logger.info(f"  Exposição setorial: {final_sector_exposure}")

    achieved_allocation = sum(h["weight"] for h in holdings)
    allocation_gap = target_allocation - achieved_allocation
    capped_assets = sum(1 for h in holdings if h.get("asset_capped"))
    sector_capped_assets = sum(1 for h in holdings if h.get("sector_capped"))

    if not allocation_note and allocation_gap > 0.02:
        allocation_note = (
            f"Alocação abaixo do alvo por restrições ativas "
            f"(ativos no teto: {capped_assets}, ajustes setoriais: {sector_capped_assets})."
        )

    allocation_diagnostics = {
        "target_rv_allocation": round(target_allocation, 4),
        "achieved_rv_allocation": round(achieved_allocation, 4),
        "allocation_gap": round(allocation_gap, 4),
        "allocation_note": allocation_note,
        "positive_score_assets": positive_score_count,
        "asset_caps_applied": capped_assets,
        "sector_caps_applied": sector_capped_assets,
    }
    
    return holdings, final_sector_exposure, allocation_diagnostics


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
