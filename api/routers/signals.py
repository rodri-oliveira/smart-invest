"""Router de sinais e scores."""

from typing import Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from aim.data_layer.database import Database
from aim.regime.engine import get_current_regime, get_regime_history
from aim.scoring.engine import get_top_ranked_assets

router = APIRouter()


class Signal(BaseModel):
    """Modelo de sinal/score."""
    ticker: str
    date: str
    score_final: float
    score_momentum: Optional[float]
    score_quality: Optional[float]
    score_value: Optional[float]
    score_volatility: Optional[float]
    score_liquidity: Optional[float]
    rank_universe: int
    regime_at_date: str


class RegimeState(BaseModel):
    """Modelo de regime de mercado."""
    date: str
    regime: str
    score_total: float
    score_yield_curve: Optional[float]
    score_risk_spread: Optional[float]
    score_ibov_trend: Optional[float]
    score_capital_flow: Optional[float]
    score_liquidity: Optional[float]


@router.get("/regime/current", response_model=RegimeState)
async def get_current_regime_endpoint():
    """Retorna o regime de mercado atual."""
    db = Database()
    regime = get_current_regime(db)
    
    if not regime:
        raise HTTPException(status_code=404, detail="Sem dados de regime")
    
    return RegimeState(**regime)


@router.get("/regime/history", response_model=List[RegimeState])
async def get_regime_history_endpoint(
    days: int = Query(90, ge=1, le=365, description="Dias de histórico"),
):
    """Retorna histórico de regimes de mercado."""
    db = Database()
    history = get_regime_history(db, days=days)
    
    if history.empty:
        raise HTTPException(status_code=404, detail="Sem histórico de regime")
    
    return [RegimeState(**row) for row in history.to_dict("records")]


@router.get("/ranking", response_model=List[Signal])
async def get_ranking(
    top_n: int = Query(20, ge=1, le=50, description="Top N ativos"),
    date: Optional[str] = Query(None, description="Data específica (YYYY-MM-DD)"),
):
    """Retorna ranking dos melhores ativos."""
    db = Database()
    
    results = get_top_ranked_assets(db, date=date, top_n=top_n)
    
    if results.empty:
        raise HTTPException(status_code=404, detail="Sem dados de ranking")
    
    # Mapear colunas do banco para o modelo
    signals = []
    for _, row in results.iterrows():
        signals.append(Signal(
            ticker=row["ticker"],
            date=row.get("date", date or ""),
            score_final=row["score_final"],
            score_momentum=row.get("score_momentum"),
            score_quality=row.get("score_quality"),
            score_value=row.get("score_value"),
            score_volatility=row.get("score_volatility"),
            score_liquidity=row.get("score_liquidity"),
            rank_universe=row["rank_universe"],
            regime_at_date=row.get("regime_at_date", "UNKNOWN"),
        ))
    
    return signals


@router.get("/ranking/{ticker}", response_model=Signal)
async def get_asset_signal(ticker: str):
    """Retorna sinal específico de um ativo."""
    db = Database()
    
    result = db.fetch_one(
        """
        SELECT 
            s.ticker, s.date, s.score_final, s.score_momentum,
            s.score_quality, s.score_value, s.score_volatility, s.score_liquidity,
            s.rank_universe, s.regime_at_date
        FROM signals s
        WHERE s.ticker = ?
        ORDER BY s.date DESC
        LIMIT 1
        """,
        (ticker.upper(),)
    )
    
    if not result:
        raise HTTPException(status_code=404, detail=f"Sem sinal para {ticker}")
    
    return Signal(**result)
