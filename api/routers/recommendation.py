"""Endpoints para recomendação."""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Dict, Any

from aim.data_layer.database import Database
from aim.intent.parser import IntentParser
from aim.scoring.dynamic import DynamicScoringEngine
from aim.sentiment.scorer import SentimentScorer

router = APIRouter(tags=["Recomendação"])

class IntentRequest(BaseModel):
    prompt: str

class RecommendationRequest(BaseModel):
    intent: Dict[str, Any]
    signals: List[Dict[str, Any]]

def get_db():
    return Database()

@router.post("/intent")
async def parse_intent(request: IntentRequest, db: Database = Depends(get_db)):
    """Parse user intent from natural language."""
    try:
        parser = IntentParser()
        intent = parser.parse(request.prompt)
        return {
            "objective": intent.objective.value,
            "horizon_days": intent.horizon_days,
            "risk_tolerance": intent.risk_tolerance.value,
            "factor_priorities": intent.factor_priorities,
            "constraints": intent.constraints
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/data-status")
async def get_data_status(db: Database = Depends(get_db)):
    """Verifica a data dos dados mais recentes no sistema."""
    try:
        # Verificar preços mais recentes
        prices = db.fetch_one("SELECT MAX(date) as max_date, COUNT(*) as count FROM market_prices WHERE date >= date('now', '-7 days')")
        
        # Verificar scores mais recentes
        scores = db.fetch_one("SELECT MAX(date) as max_date, COUNT(*) as count FROM signals WHERE date >= date('now', '-7 days')")
        
        # Verificar se há dados de hoje
        today = db.fetch_one("SELECT date('now') as today")
        
        prices_date = prices['max_date'] if prices else None
        scores_date = scores['max_date'] if scores else None
        
        # Determinar status
        is_fresh = False
        if prices_date == today['today'] and scores_date == today['today']:
            is_fresh = True
        elif prices_date and scores_date:
            # Verificar se é do dia util anterior (permitir atraso de 1 dia util)
            days_diff = db.fetch_one("SELECT julianday('now') - julianday(?) as diff", (prices_date,))
            is_fresh = days_diff['diff'] <= 3  # Até 3 dias é aceitável (fim de semana/feriado)
        
        return {
            "status": "fresh" if is_fresh else "stale",
            "prices_date": prices_date,
            "scores_date": scores_date,
            "today": today['today'],
            "prices_count": prices['count'] if prices else 0,
            "scores_count": scores['count'] if scores else 0,
            "message": "Dados atualizados" if is_fresh else "Dados desatualizados - atualização recomendada"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao verificar status: {str(e)}")


@router.get("/sentiment")
async def get_market_sentiment(db: Database = Depends(get_db)):
    """Retorna o sentimento atual do mercado baseado em dados macro e técnicos."""
    try:
        scorer = SentimentScorer(db)
        result = scorer.calculate_daily_sentiment()
        
        return {
            "date": result["date"],
            "score": result["score"],
            "label": result["sentiment"],
            "confidence": result["confidence"],
            "components": {
                "macro": result["components"]["macro"]["score"] if "macro" in result["components"] else 0,
                "technical": result["components"]["technical"]["score"] if "technical" in result["components"] else 0,
                "volatility": result["components"]["volatility"]["score"] if "volatility" in result["components"] else 0,
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao calcular sentimento: {str(e)}")
async def trigger_data_update(db: Database = Depends(get_db)):
    """Executa o pipeline de atualização de dados sob demanda."""
    import subprocess
    import sys
    import os
    
    try:
        # Verificar se o script existe
        script_path = os.path.join(os.getcwd(), "scripts", "daily_pipeline.py")
        if not os.path.exists(script_path):
            raise HTTPException(status_code=500, detail="Script de pipeline não encontrado")
        
        # Executar pipeline em subprocesso (não bloqueia a API)
        process = subprocess.Popen(
            [sys.executable, script_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=os.getcwd()
        )
        
        return {
            "status": "started",
            "message": "Atualização de dados iniciada em background",
            "pid": process.pid,
            "estimated_time": "2-5 minutos"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao iniciar atualização: {str(e)}")
