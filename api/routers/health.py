"""Router de health check."""

from datetime import datetime
from typing import Dict

from fastapi import APIRouter, HTTPException

from aim.data_layer.database import Database
from aim.regime.engine import get_current_regime

router = APIRouter()


@router.get("/")
async def health_check() -> Dict:
    """
    Health check completo do sistema.
    
    Verifica:
    - Conexão com banco de dados
    - Dados recentes
    - Regime atual
    """
    try:
        db = Database()
        
        # Verificar banco
        db_status = db.table_exists("assets")
        
        # Verificar dados recentes
        recent_prices = db.fetch_one(
            "SELECT MAX(date) as max_date FROM prices"
        )
        
        # Verificar regime
        regime = get_current_regime(db)
        
        status = "healthy" if db_status else "unhealthy"
        
        return {
            "status": status,
            "timestamp": datetime.utcnow().isoformat(),
            "database": "connected" if db_status else "error",
            "latest_price_date": recent_prices["max_date"] if recent_prices else None,
            "current_regime": regime["regime"] if regime else None,
            "regime_score": regime["score_total"] if regime else None,
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail={"status": "unhealthy", "error": str(e)}
        )


@router.get("/simple")
async def simple_health() -> Dict:
    """Health check simples para load balancers."""
    return {"status": "ok"}
