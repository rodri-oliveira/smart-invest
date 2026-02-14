"""Sentiment Scorer - Análise de sentimento de notícias e eventos macro."""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import pandas as pd

from aim.data_layer.database import Database

logger = logging.getLogger(__name__)


class SentimentScorer:
    """Calcula scores de sentimento baseado em eventos macro e notícias."""
    
    # Eventos macro de alto impacto
    HIGH_IMPACT_EVENTS = [
        "rate_decision",      # Decisão de taxa de juros (Selic, Fed)
        "inflation_report",   # Relatório de inflação (IPCA, CPI)
        "gdp_report",         # PIB
        "employment_report",  # Dados de emprego
        "political_crisis",   # Crise política
        "commodity_shock",    # Choque de commodities (petróleo, minério)
        "currency_crisis",    # Crise cambial
    ]
    
    def __init__(self, db: Database):
        self.db = db
    
    def calculate_daily_sentiment(
        self,
        date: Optional[str] = None,
        lookback_days: int = 5,
    ) -> Dict[str, Any]:
        """
        Calcula sentimento geral do mercado para uma data.
        
        Args:
            date: Data de análise. Se None, usa data mais recente.
            lookback_days: Dias para olhar no passado
            
        Returns:
            Dict com score de sentimento e componentes
        """
        if date is None:
            date = datetime.now().strftime("%Y-%m-%d")
        
        # Calcular data de início do lookback
        end_date = datetime.strptime(date, "%Y-%m-%d")
        start_date = end_date - timedelta(days=lookback_days)
        start_str = start_date.strftime("%Y-%m-%d")
        
        sentiment_score = 0.0
        components = {}
        
        # 1. Sentimento de dados macro (Selic, IPCA)
        macro_sentiment = self._calculate_macro_sentiment(start_str, date)
        sentiment_score += macro_sentiment["score"] * 0.3
        components["macro"] = macro_sentiment
        
        # 2. Sentimento técnico do mercado (tendência do IBOV)
        technical_sentiment = self._calculate_technical_sentiment(date)
        sentiment_score += technical_sentiment["score"] * 0.4
        components["technical"] = technical_sentiment
        
        # 3. Sentimento de volatilidade (VIX-like)
        vol_sentiment = self._calculate_volatility_sentiment(date)
        sentiment_score += vol_sentiment["score"] * 0.3
        components["volatility"] = vol_sentiment
        
        # Normalizar para escala -1 a 1
        final_score = max(-1, min(1, sentiment_score))
        
        return {
            "date": date,
            "score": final_score,
            "sentiment": self._interpret_score(final_score),
            "components": components,
            "confidence": self._calculate_confidence(components),
        }
    
    def _calculate_macro_sentiment(
        self,
        start_date: str,
        end_date: str,
    ) -> Dict[str, Any]:
        """Calcula sentimento baseado em indicadores macro."""
        score = 0.0
        factors = []
        
        # Buscar dados macro do período
        query = """
            SELECT indicator, value, date
            FROM macro_indicators
            WHERE date BETWEEN ? AND ?
            AND indicator IN ('SELIC', 'IPCA', 'CDI', 'IBOVESPA')
            ORDER BY date DESC
        """
        
        results = self.db.fetch_all(query, (start_date, end_date))
        
        if not results:
            return {"score": 0, "factors": [], "data_available": False}
        
        # Analisar tendência de Selic
        selic_data = [r for r in results if r["indicator"] == "SELIC"]
        if len(selic_data) >= 2:
            recent = selic_data[0]["value"]
            previous = selic_data[-1]["value"]
            if recent < previous:
                score += 0.3  # Queda de juros = positivo
                factors.append("selic_falling")
            elif recent > previous:
                score -= 0.3  # Alta de juros = negativo
                factors.append("selic_rising")
        
        # Analisar IPCA
        ipca_data = [r for r in results if r["indicator"] == "IPCA"]
        if ipca_data:
            ipca = ipca_data[0]["value"]
            if ipca < 0.005:  # < 0.5% ao mês
                score += 0.2
                factors.append("low_inflation")
            elif ipca > 0.01:  # > 1% ao mês
                score -= 0.2
                factors.append("high_inflation")
        
        return {
            "score": max(-1, min(1, score)),
            "factors": factors,
            "data_available": True,
        }
    
    def _calculate_technical_sentiment(self, date: str) -> Dict[str, Any]:
        """Calcula sentimento baseado em tendência técnica dos principais ativos."""
        score = 0.0
        factors = []
        
        # Usar média dos top 5 ativos como proxy de mercado (IBOVESPA não disponível)
        query = """
            SELECT date, AVG(close) as avg_close
            FROM prices
            WHERE ticker IN ('PETR4', 'VALE3', 'ITUB4', 'BBDC4', 'ABEV3')
            AND date <= ?
            GROUP BY date
            ORDER BY date DESC
            LIMIT 22
        """
        
        results = self.db.fetch_all(query, (date,))
        
        if len(results) < 10:
            # Fallback: usar qualquer ativo disponível
            query_fallback = """
                SELECT date, AVG(close) as avg_close
                FROM prices
                WHERE date <= ?
                GROUP BY date
                ORDER BY date DESC
                LIMIT 22
            """
            results = self.db.fetch_all(query_fallback, (date,))
        
        if len(results) < 10:
            return {"score": 0, "factors": [], "data_available": False}
        
        prices = [r["avg_close"] for r in results if r["avg_close"]]
        
        if len(prices) >= 10:
            # Tendência de curto prazo
            recent = prices[0]
            previous = prices[5]  # ~1 semana atrás
            month_ago = prices[-1]
            
            if recent > previous:
                score += 0.2
                factors.append("short_uptrend")
            else:
                score -= 0.2
                factors.append("short_downtrend")
            
            if recent > month_ago:
                score += 0.3
                factors.append("monthly_uptrend")
            else:
                score -= 0.3
                factors.append("monthly_downtrend")
        
        return {
            "score": max(-1, min(1, score)),
            "factors": factors,
            "data_available": True,
        }
    
    def _calculate_volatility_sentiment(self, date: str) -> Dict[str, Any]:
        """Calcula sentimento baseado em volatilidade média do mercado."""
        score = 0.0
        factors = []
        
        # Buscar volatilidade média dos principais ativos
        query = """
            SELECT AVG(vol_21d) as avg_vol
            FROM features
            WHERE ticker IN ('PETR4', 'VALE3', 'ITUB4', 'BBDC4', 'ABEV3')
            AND date <= ?
            AND vol_21d IS NOT NULL
            GROUP BY date
            ORDER BY date DESC
            LIMIT 1
        """
        
        result = self.db.fetch_one(query, (date,))
        
        if not result or not result["avg_vol"]:
            # Fallback: usar qualquer volatilidade disponível
            query_fallback = """
                SELECT AVG(vol_21d) as avg_vol
                FROM features
                WHERE date <= ?
                AND vol_21d IS NOT NULL
                GROUP BY date
                ORDER BY date DESC
                LIMIT 1
            """
            result = self.db.fetch_one(query_fallback, (date,))
        
        if not result or not result["avg_vol"]:
            return {"score": 0, "factors": [], "data_available": False}
        
        vol = result["avg_vol"]
        
        # Volatilidade anualizada
        annual_vol = vol * 100  # Converter para percentual
        
        if annual_vol < 15:
            score += 0.4  # Baixa vol = positivo
            factors.append("low_volatility")
        elif annual_vol > 30:
            score -= 0.4  # Alta vol = negativo
            factors.append("high_volatility")
        elif annual_vol > 25:
            score -= 0.2  # Vol moderada-alta
            factors.append("elevated_volatility")
        else:
            score += 0.1  # Vol normal
            factors.append("normal_volatility")
        
        return {
            "score": score,
            "factors": factors,
            "volatility": annual_vol,
            "data_available": True,
        }
    
    def _interpret_score(self, score: float) -> str:
        """Interpreta o score de sentimento."""
        if score > 0.5:
            return "BULLISH"
        elif score > 0.2:
            return "MODERATELY_BULLISH"
        elif score < -0.5:
            return "BEARISH"
        elif score < -0.2:
            return "MODERATELY_BEARISH"
        else:
            return "NEUTRAL"
    
    def _calculate_confidence(self, components: Dict) -> float:
        """Calcula confiança do sentimento baseado em dados disponíveis."""
        available = sum(
            1 for c in components.values()
            if c.get("data_available", False)
        )
        return available / len(components) if components else 0.0


def update_sentiment_to_database(db: Database, date: Optional[str] = None) -> bool:
    """
    Atualiza sentimento do dia no banco de dados.
    
    Args:
        db: Conexão com banco
        date: Data específica. Se None, usa data atual.
        
    Returns:
        True se sucesso
    """
    try:
        scorer = SentimentScorer(db)
        sentiment = scorer.calculate_daily_sentiment(date)
        
        # Inserir na tabela de regime_state (ou criar nova tabela sentiment)
        # Por enquanto, logar o resultado
        logger.info(f"Sentimento {sentiment['date']}: {sentiment['sentiment']} "
                   f"(score: {sentiment['score']:+.2f}, "
                   f"confiança: {sentiment['confidence']:.0%})")
        
        # Salvar componentes detalhados
        for component, data in sentiment["components"].items():
            logger.debug(f"  {component}: {data}")
        
        return True
        
    except Exception as e:
        logger.error(f"Erro ao calcular sentimento: {e}")
        return False
