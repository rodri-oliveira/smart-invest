"""Dynamic Scoring Engine - Ajusta scoring baseado em intenção do usuário e regime."""

import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

import pandas as pd
import numpy as np

from aim.intent.parser import InvestmentIntent, ObjectiveType, RiskTolerance
from aim.scoring.calculator import calculate_composite_score
from aim.scoring.engine import load_features_for_scoring, load_fundamentals_for_scoring
from aim.regime.engine import get_current_regime
from aim.data_layer.database import Database

logger = logging.getLogger(__name__)


# Pesos base por tipo de intenção
INTENT_WEIGHTS = {
    ObjectiveType.RETURN: {
        'momentum': 0.35,
        'value': 0.20,
        'quality': 0.15,
        'volatility': 0.15,
        'liquidity': 0.15,
    },
    ObjectiveType.PROTECTION: {
        'momentum': 0.10,
        'value': 0.25,
        'quality': 0.35,
        'volatility': 0.10,
        'liquidity': 0.20,
    },
    ObjectiveType.INCOME: {
        'momentum': 0.15,
        'value': 0.35,
        'quality': 0.30,
        'volatility': 0.10,
        'liquidity': 0.10,
    },
    ObjectiveType.SPECULATION: {
        'momentum': 0.45,
        'value': 0.10,
        'quality': 0.10,
        'volatility': 0.25,
        'liquidity': 0.10,
    },
    ObjectiveType.BALANCED: {
        'momentum': 0.25,
        'value': 0.25,
        'quality': 0.25,
        'volatility': 0.15,
        'liquidity': 0.10,
    },
}

# Multiplicadores por tolerância de risco
RISK_MULTIPLIERS = {
    RiskTolerance.CONSERVATIVE: {
        'momentum': 0.7,
        'value': 1.2,
        'quality': 1.3,
        'volatility': 0.6,
        'liquidity': 1.2,
    },
    RiskTolerance.MODERATE: {
        'momentum': 1.0,
        'value': 1.0,
        'quality': 1.0,
        'volatility': 1.0,
        'liquidity': 1.0,
    },
    RiskTolerance.AGGRESSIVE: {
        'momentum': 1.3,
        'value': 0.9,
        'quality': 0.8,
        'volatility': 1.2,
        'liquidity': 0.9,
    },
    RiskTolerance.SPECULATIVE: {
        'momentum': 1.5,
        'value': 0.7,
        'quality': 0.6,
        'volatility': 1.4,
        'liquidity': 0.7,
    },
}


class DynamicScoringEngine:
    """
    Engine de scoring dinâmico que adapta pesos conforme intenção do usuário.
    
    Princípio: Nunca usar pesos fixos. Sempre adaptar ao objetivo.
    """
    
    def __init__(self, db: Database):
        self.db = db
    
    def calculate_scores_with_intent(
        self,
        intent: InvestmentIntent,
        date: Optional[str] = None,
    ) -> pd.DataFrame:
        """
        Calcula scores ajustados pela intenção do usuário.
        
        Args:
            intent: Intenção de investimento parseada
            date: Data de análise (None = mais recente)
            
        Returns:
            DataFrame com scores ajustados
        """
        logger.info(f"Calculando scores para intenção: {intent.objective.value}")
        logger.info(f"Horizonte: {intent.horizon.value}, Risco: {intent.risk_tolerance.value}")
        
        # 1. Carregar dados
        features_df = load_features_for_scoring(self.db, date)
        if features_df.empty:
            logger.error("Sem features disponíveis")
            return pd.DataFrame()
        
        fundamentals_df = load_fundamentals_for_scoring(self.db, date)
        
        # 2. Obter regime atual
        regime_data = get_current_regime(self.db)
        regime = regime_data["regime"] if regime_data else "TRANSITION"
        logger.info(f"Regime atual: {regime}")
        
        # 3. Calcular pesos dinâmicos
        weights = self._calculate_dynamic_weights(intent, regime)
        logger.info(f"Pesos dinâmicos: {weights}")
        
        # 4. Aplicar filtros de risco da intenção
        features_df = self._apply_risk_filters(features_df, intent)
        
        # 5. Calcular scores com pesos personalizados
        scores_df = self._calculate_with_custom_weights(
            features_df=features_df,
            fundamentals_df=fundamentals_df,
            weights=weights,
            priority_factors=intent.priority_factors,
        )
        
        # 6. Aplicar filtros de liquidez
        scores_df = self._apply_liquidity_filter(scores_df, intent.min_liquidity)
        
        # 7. Recalcular ranking após filtros
        scores_df["rank_universe"] = scores_df["score_final"].rank(
            ascending=False, method="dense"
        ).astype(int)
        
        logger.info(f"✓ Scores calculados para {len(scores_df)} ativos")
        logger.info(f"  Top 5: {scores_df.nsmallest(5, 'rank_universe')['ticker'].tolist()}")
        
        return scores_df
    
    def _calculate_dynamic_weights(
        self,
        intent: InvestmentIntent,
        regime: str,
    ) -> Dict[str, float]:
        """
        Calcula pesos dinâmicos baseados em intenção + regime.
        
        Args:
            intent: Intenção do usuário
            regime: Regime de mercado atual
            
        Returns:
            Dicionário de pesos por fator
        """
        # Pesos base por objetivo
        base_weights = INTENT_WEIGHTS.get(
            intent.objective,
            INTENT_WEIGHTS[ObjectiveType.BALANCED]
        ).copy()
        
        # Aplicar multiplicadores por tolerância de risco
        risk_mult = RISK_MULTIPLIERS.get(intent.risk_tolerance, {})
        for factor, mult in risk_mult.items():
            if factor in base_weights:
                base_weights[factor] *= mult
        
        # Ajustar por regime de mercado
        regime_adjustments = self._get_regime_adjustments(regime)
        for factor, adjustment in regime_adjustments.items():
            if factor in base_weights:
                base_weights[factor] *= adjustment
        
        # Normalizar para somar 1.0
        total = sum(base_weights.values())
        if total > 0:
            weights = {k: v / total for k, v in base_weights.items()}
        else:
            weights = base_weights
        
        return weights
    
    def _get_regime_adjustments(self, regime: str) -> Dict[str, float]:
        """
        Retorna ajustes de peso baseado no regime de mercado.
        
        Args:
            regime: Regime atual (BULL, BEAR, TRANSITION, etc.)
            
        Returns:
            Multiplicadores por fator
        """
        adjustments = {
            "BULL": {
                'momentum': 1.2,
                'value': 0.9,
                'quality': 1.0,
                'volatility': 0.9,
            },
            "BEAR": {
                'momentum': 0.7,
                'value': 1.1,
                'quality': 1.2,
                'volatility': 0.8,
            },
            "TRANSITION": {
                'momentum': 1.0,
                'value': 1.0,
                'quality': 1.1,
                'volatility': 0.9,
            },
        }
        
        return adjustments.get(regime, {})
    
    def _apply_risk_filters(
        self,
        features_df: pd.DataFrame,
        intent: InvestmentIntent,
    ) -> pd.DataFrame:
        """
        Filtra ativos que excedem limites de risco da intenção.
        
        Args:
            features_df: DataFrame com features
            intent: Intenção com limites de risco
            
        Returns:
            DataFrame filtrado
        """
        initial_count = len(features_df)
        
        # Filtrar por volatilidade máxima
        if 'vol_63d' in features_df.columns:
            # vol_63d já está anualizada (calculada como std * sqrt(252))
            # Aplicar tolerância de 50% acima do limite para não filtrar demais
            max_vol_limit = intent.max_volatility * 1.5
            
            logger.debug(f"Volatilidade limite: {max_vol_limit:.1%}")
            logger.debug(f"Volatilidade média dos ativos: {features_df['vol_63d'].mean():.1%}")
            logger.debug(f"Volatilidade máxima dos ativos: {features_df['vol_63d'].max():.1%}")
            
            features_df = features_df[
                features_df['vol_63d'] <= max_vol_limit
            ]
        
        filtered_count = len(features_df)
        if filtered_count < initial_count:
            logger.info(f"  Filtrados {initial_count - filtered_count} ativos por risco excessivo")
        else:
            logger.info(f"  Todos os {initial_count} ativos dentro dos limites de risco")
        
        return features_df
    
    def _apply_liquidity_filter(
        self,
        scores_df: pd.DataFrame,
        min_liquidity: float,
    ) -> pd.DataFrame:
        """
        Filtra ativos abaixo do threshold de liquidez.
        
        Args:
            scores_df: DataFrame com scores
            min_liquidity: Liquidez mínima exigida
            
        Returns:
            DataFrame filtrado
        """
        if 'score_liquidity' in scores_df.columns:
            initial_count = len(scores_df)
            
            # Converter z-score de liquidez para score 0-1
            # Assumindo que z-score > 0 é liquidez acima da média
            liquidity_score = (scores_df['score_liquidity'] + 2) / 4  # Normalizar aproximadamente
            liquidity_score = liquidity_score.clip(0, 1)
            
            scores_df = scores_df[liquidity_score >= min_liquidity]
            
            filtered_count = len(scores_df)
            if filtered_count < initial_count:
                logger.info(f"  Filtrados {initial_count - filtered_count} ativos por baixa liquidez")
        
        return scores_df
    
    def _calculate_with_custom_weights(
        self,
        features_df: pd.DataFrame,
        fundamentals_df: Optional[pd.DataFrame],
        weights: Dict[str, float],
        priority_factors: List[str],
    ) -> pd.DataFrame:
        """
        Calcula score final com pesos personalizados.
        
        Args:
            features_df: Features técnicas
            fundamentals_df: Dados fundamentalistas
            weights: Pesos por fator
            priority_factors: Fatores prioritários
            
        Returns:
            DataFrame com scores
        """
        from aim.scoring.calculator import (
            calculate_momentum_score,
            calculate_quality_score,
            calculate_value_score,
            calculate_volatility_score,
            calculate_liquidity_score_normalized,
            calculate_z_score,
        )
        
        results = pd.DataFrame()
        results["ticker"] = features_df["ticker"]
        if "date" in features_df.columns:
            results["date"] = features_df["date"]
        
        # Calcular scores individuais
        results["score_momentum"] = calculate_momentum_score(features_df)
        results["score_volatility"] = calculate_volatility_score(features_df)
        results["score_liquidity"] = calculate_liquidity_score_normalized(features_df)
        
        # Scores de fundamentos (se disponíveis)
        if fundamentals_df is not None and not fundamentals_df.empty:
            merged = results.merge(fundamentals_df, on="ticker", how="left")
            results["score_quality"] = calculate_quality_score(merged)
            results["score_value"] = calculate_value_score(merged)
        else:
            results["score_quality"] = 0.0
            results["score_value"] = 0.0
        
        # Aplicar boost em fatores prioritários
        for factor in priority_factors[:2]:  # Boost nos 2 principais
            col = f"score_{factor}"
            if col in results.columns:
                results[col] *= 1.2  # Boost de 20%
        
        # Calcular score final ponderado
        results["score_final"] = (
            weights.get('momentum', 0) * results['score_momentum'] +
            weights.get('quality', 0) * results['score_quality'] +
            weights.get('value', 0) * results['score_value'] +
            weights.get('volatility', 0) * results['score_volatility'] +
            weights.get('liquidity', 0) * results['score_liquidity']
        )
        
        return results


def calculate_dynamic_scores(
    db: Database,
    intent: InvestmentIntent,
    date: Optional[str] = None,
) -> pd.DataFrame:
    """
    Função conveniência para calcular scores dinâmicos.
    
    Args:
        db: Conexão com banco
        intent: Intenção parseada
        date: Data de análise
        
    Returns:
        DataFrame com scores
    """
    engine = DynamicScoringEngine(db)
    return engine.calculate_scores_with_intent(intent, date)
