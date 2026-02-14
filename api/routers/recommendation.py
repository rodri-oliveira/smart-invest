"""Endpoints para recomendação."""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Dict, Any

from aim.data_layer.database import Database
from aim.intent.parser import IntentParser
from aim.scoring.dynamic import DynamicScoringEngine
from aim.portfolio.constructor import PortfolioConstructor

router = APIRouter(prefix="/recommendation", tags=["Recomendação"])

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

@router.post("/")
async def get_recommendation(request: RecommendationRequest, db: Database = Depends(get_db)):
    """Generate full recommendation based on intent and signals."""
    try:
        # Mock response for now - real implementation needs proper scoring
        return {
            "tickers": ["PETR4", "VALE3", "ITUB4", "BBDC4", "ABEV3"],
            "weights": [0.25, 0.25, 0.2, 0.15, 0.15],
            "scores": [1.02, 0.89, 0.76, 0.65, 0.58],
            "risk_metrics": {
                "volatility": 0.248,
                "expected_drawdown": 0.18,
                "var_95": 0.15,
                "concentration": 0.2,
            },
            "sentiment": {"score": 0.15, "label": "MODERADAMENTE OTIMISTA"},
            "rationale": "Recomendação baseada em análise quantitativa dos dados disponíveis.",
            "scenarios": {
                "best_case": "Retorno positivo se mercado continuar favorável",
                "worst_case": "Perda limitada por diversificação"
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
