"""Router de ativos."""

from typing import Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from aim.data_layer.database import Database

router = APIRouter()


class Asset(BaseModel):
    """Modelo de ativo."""
    ticker: str
    name: str
    sector: Optional[str]
    segment: Optional[str]
    market_cap_category: Optional[str]
    is_active: bool


class AssetPrice(BaseModel):
    """Modelo de preço."""
    date: str
    open: float
    high: float
    low: float
    close: float
    volume: int


@router.get("/", response_model=List[Asset])
async def list_assets(
    sector: Optional[str] = Query(None, description="Filtrar por setor"),
    active_only: bool = Query(True, description="Apenas ativos ativos"),
):
    """Lista todos os ativos do universo."""
    db = Database()
    
    query = """
        SELECT ticker, name, sector, segment, market_cap_category, is_active
        FROM assets
        WHERE 1=1
    """
    params = []
    
    if active_only:
        query += " AND is_active = 1"
    
    if sector:
        query += " AND sector = ?"
        params.append(sector)
    
    query += " ORDER BY ticker"
    
    results = db.fetch_all(query, tuple(params))
    return [Asset(**row) for row in results]


@router.get("/{ticker}", response_model=Asset)
async def get_asset(ticker: str):
    """Retorna detalhes de um ativo específico."""
    db = Database()
    
    result = db.fetch_one(
        """
        SELECT ticker, name, sector, segment, market_cap_category, is_active
        FROM assets
        WHERE ticker = ?
        """,
        (ticker.upper(),)
    )
    
    if not result:
        raise HTTPException(status_code=404, detail=f"Ativo {ticker} não encontrado")
    
    return Asset(**result)


@router.get("/{ticker}/prices", response_model=List[AssetPrice])
async def get_asset_prices(
    ticker: str,
    days: int = Query(30, ge=1, le=365, description="Dias de histórico"),
):
    """Retorna preços históricos de um ativo."""
    db = Database()
    
    query = """
        SELECT date, open, high, low, close, volume
        FROM prices
        WHERE ticker = ?
        AND date >= date('now', '-{} days')
        ORDER BY date ASC
    """.format(days)
    
    results = db.fetch_all(query, (ticker.upper(),))
    
    if not results:
        raise HTTPException(status_code=404, detail=f"Sem dados de preço para {ticker}")
    
    return [AssetPrice(**row) for row in results]
