"""Router de carteira e alocaÃ§Ã£o."""

import logging
from datetime import date, datetime
from typing import Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from aim.allocation.engine import (
    build_portfolio_from_scores,
    generate_portfolio_report,
    save_portfolio_to_database,
)
from aim.config.parameters import MAX_SECTOR_EXPOSURE_BY_REGIME
from aim.data_layer.database import Database
from aim.intent.parser import parse_intent

router = APIRouter()
logger = logging.getLogger(__name__)


class Holding(BaseModel):
    """Modelo de posiÃ§Ã£o com indicadores fundamentalistas."""
    ticker: str
    asset_name: Optional[str] = None
    weight: float
    score: Optional[float]
    sector: Optional[str]
    segment: Optional[str] = None
    p_l: Optional[float] = None  # PreÃ§o/Lucro
    dy: Optional[float] = None   # Dividend Yield (%)
    trend_30d: Optional[float] = None  # TendÃªncia 30 dias
    current_price: Optional[float] = None  # PreÃ§o atual R$
    price_date: Optional[date] = None  # Data do preÃ§o


class Portfolio(BaseModel):
    """Modelo de carteira."""
    name: str
    n_positions: int
    total_weight: float
    sector_exposure: Dict[str, float]
    holdings: List[Holding]


class PortfolioBuildRequest(BaseModel):
    prompt: str = "Quero alto retorno com risco moderado"

@router.post("/build")
async def build_portfolio(
    request: PortfolioBuildRequest,
    n_positions: int = 10,
    strategy: str = "auto",
    name: str = "SmartPortfolio",
):
    """ConstrÃ³i uma nova carteira otimizada baseada no prompt do usuÃ¡rio."""
    db = Database()
    
    try:
        # Parse da intenÃ§Ã£o do usuÃ¡rio
        intent = parse_intent(request.prompt)
        
        # Usar o regime definido pelo prompt (override nos dados macro)
        user_regime = intent.user_regime
        
        # Passar fatores prioritÃ¡rios do prompt para reponderar scores
        priority_factors = intent.priority_factors

        # EstratÃ©gia dinÃ¢mica orientada pelo prompt do usuÃ¡rio
        objective_strategy_map = {
            "protection": "risk_parity",
            "income": "equal_weight",
            "balanced": "equal_weight",
            "return": "score_weighted",
            "speculation": "score_weighted",
        }
        selected_strategy = strategy
        if strategy == "auto":
            selected_strategy = objective_strategy_map.get(
                intent.objective.value, "score_weighted"
            )
        
        result = build_portfolio_from_scores(
            db=db,
            n_positions=n_positions,
            strategy=selected_strategy,
            regime=user_regime,
            priority_factors=priority_factors
        )
        
        holdings = result[0] if isinstance(result, tuple) else result
        sector_exposure = result[1] if isinstance(result, tuple) and len(result) > 1 else {}
        allocation_context = result[2] if isinstance(result, tuple) and len(result) > 2 else {}
        
        if not holdings:
            raise HTTPException(status_code=400, detail="NÃ£o foi possÃ­vel construir carteira")
        
        # Enriquecer holdings com metadados e indicadores fundamentalistas
        tickers = [h["ticker"] for h in holdings]
        placeholders = ','.join(['?' for _ in tickers])

        assets_data = {}
        if tickers:
            try:
                assets_query = f"""
                    SELECT ticker, name, sector, segment
                    FROM assets
                    WHERE ticker IN ({placeholders})
                """
                assets_results = db.fetch_all(assets_query, tuple(tickers))
                for row in assets_results:
                    assets_data[row["ticker"]] = {
                        "name": row.get("name"),
                        "sector": row.get("sector"),
                        "segment": row.get("segment"),
                    }
            except Exception as e:
                logger.warning(f"Erro ao buscar metadados de ativos: {e}")
        
        fundamentals_query = f"""
            SELECT 
                f.ticker, f.p_l, f.dy, f.roe
            FROM fundamentals f
            INNER JOIN (
                SELECT ticker, MAX(reference_date) as max_date
                FROM fundamentals
                WHERE ticker IN ({placeholders})
                GROUP BY ticker
            ) latest ON f.ticker = latest.ticker AND f.reference_date = latest.max_date
        """
        
        fundamentals_data = {}
        if tickers:
            try:
                fund_results = db.fetch_all(fundamentals_query, tuple(tickers))
                for row in fund_results:
                    fundamentals_data[row["ticker"]] = {
                        "p_l": row.get("p_l"),
                        "dy": row.get("dy"),
                        "roe": row.get("roe")
                    }
            except Exception as e:
                logger.warning(f"Erro ao buscar fundamentos: {e}")
        
        # Buscar preÃ§os atuais dos ativos
        prices_data = {}
        if tickers:
            try:
                for ticker in tickers:
                    price_query = """
                        SELECT close as price, date as price_date
                        FROM prices
                        WHERE ticker = ?
                        ORDER BY date DESC
                        LIMIT 1
                    """
                    price_result = db.fetch_one(price_query, (ticker,))
                    if price_result:
                        prices_data[ticker] = {
                            "current_price": price_result.get("price"),
                            "price_date": price_result.get("price_date")
                        }
            except Exception as e:
                logger.warning(f"Erro ao buscar preÃ§os: {e}")
        
        # Salvar no banco
        portfolio_id = save_portfolio_to_database(db, name, holdings)
        
        total_weight = sum(h["weight"] for h in holdings)
        
        # Buscar data dos dados utilizados
        data_date = db.fetch_one("SELECT MAX(date) as max_date FROM signals")
        data_date_str = data_date["max_date"] if data_date else None
        
        # Definir limites dinÃ¢micos por regime
        max_sector_exposure = MAX_SECTOR_EXPOSURE_BY_REGIME.get(user_regime, 0.20)
        
        return {
            "portfolio_id": portfolio_id,
            "name": name,
            "strategy": selected_strategy,
            "objective": intent.objective.value,  # Objetivo real do usuÃ¡rio (income, return, etc.)
            "user_regime": user_regime,
            "max_sector_exposure": max_sector_exposure,
            "target_rv_allocation": allocation_context.get("target_rv_allocation"),
            "allocation_gap": allocation_context.get("allocation_gap"),
            "allocation_note": allocation_context.get("allocation_note"),
            "n_positions": len(holdings),
            "total_weight": total_weight,
            "sector_exposure": sector_exposure,
            "diversification_score": len(sector_exposure) if sector_exposure else 0,
            "data_date": data_date_str,
            "holdings": [
                Holding(
                    ticker=h["ticker"],
                    asset_name=assets_data.get(h["ticker"], {}).get("name"),
                    weight=h["weight"],
                    score=h.get("score"),
                    sector=h.get("sector") or assets_data.get(h["ticker"], {}).get("sector"),
                    segment=assets_data.get(h["ticker"], {}).get("segment"),
                    p_l=fundamentals_data.get(h["ticker"], {}).get("p_l"),
                    dy=fundamentals_data.get(h["ticker"], {}).get("dy"),
                    current_price=prices_data.get(h["ticker"], {}).get("current_price"),
                    price_date=prices_data.get(h["ticker"], {}).get("price_date"),
                )
                for h in holdings
            ],
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{name}", response_model=Portfolio)
async def get_portfolio(name: str):
    """Retorna carteira existente."""
    db = Database()
    
    report = generate_portfolio_report(db, name)
    
    if "error" in report:
        raise HTTPException(status_code=404, detail=report["error"])
    
    holdings = [
        Holding(
            ticker=h["ticker"],
            weight=h["weight"],
            sector=h.get("sector"),
        )
        for h in report["holdings"]
    ]
    
    return Portfolio(
        name=report["portfolio_name"],
        n_positions=report["n_positions"],
        total_weight=report["total_weight"],
        sector_exposure=report["sector_exposure"],
        holdings=holdings,
    )


@router.get("/alerts/rebalancing")
async def get_rebalancing_alerts():
    """Retorna alertas de rebalanceamento para a carteira mais recente."""
    from aim.portfolio.rebalancing import RebalancingMonitor, format_alerts_for_display
    
    db = Database()
    
    try:
        monitor = RebalancingMonitor(db)
        alerts = monitor.get_alerts_for_user()
        formatted_alerts = format_alerts_for_display(alerts)
        
        return {
            "alerts": formatted_alerts,
            "count": len(formatted_alerts),
            "has_urgent": any(a["priority"] <= 2 for a in formatted_alerts),
            "timestamp": datetime.now().isoformat()
        }
    except ValueError as e:
        # Carteira nÃ£o existe ou sem dados suficientes - retorna lista vazia
        if "Nenhuma carteira encontrada" in str(e) or "No portfolios found" in str(e):
            return {
                "alerts": [],
                "count": 0,
                "has_urgent": False,
                "timestamp": datetime.now().isoformat(),
                "message": "Nenhuma carteira encontrada. Gere uma recomendaÃ§Ã£o primeiro."
            }
        raise HTTPException(status_code=500, detail=f"Erro ao buscar alertas: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao buscar alertas: {str(e)}")

