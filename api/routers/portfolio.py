"""Router de carteira e alocação."""

from typing import Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from aim.allocation.engine import (
    build_portfolio_from_scores,
    generate_portfolio_report,
    save_portfolio_to_database,
)
from aim.data_layer.database import Database

router = APIRouter()


class Holding(BaseModel):
    """Modelo de posição."""
    ticker: str
    weight: float
    score: Optional[float]
    sector: Optional[str]


class Portfolio(BaseModel):
    """Modelo de carteira."""
    name: str
    n_positions: int
    total_weight: float
    sector_exposure: Dict[str, float]
    holdings: List[Holding]


@router.post("/build")
async def build_portfolio(
    n_positions: int = Query(10, ge=3, le=20, description="Número de posições"),
    strategy: str = Query("equal_weight", description="Estratégia: equal_weight, score_weighted, risk_parity"),
    name: str = Query("SmartPortfolio", description="Nome da carteira"),
):
    """Constrói uma nova carteira otimizada."""
    db = Database()
    
    try:
        holdings = build_portfolio_from_scores(
            db=db,
            n_positions=n_positions,
            strategy=strategy,
        )
        
        if not holdings:
            raise HTTPException(status_code=400, detail="Não foi possível construir carteira")
        
        # Salvar no banco
        portfolio_id = save_portfolio_to_database(db, name, holdings)
        
        total_weight = sum(h["weight"] for h in holdings)
        
        return {
            "portfolio_id": portfolio_id,
            "name": name,
            "strategy": strategy,
            "n_positions": len(holdings),
            "total_weight": total_weight,
            "holdings": [
                Holding(
                    ticker=h["ticker"],
                    weight=h["weight"],
                    score=h.get("score"),
                    sector=h.get("sector"),
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
