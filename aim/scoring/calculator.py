"""Scoring Engine - cálculo de scores multi-fator para ativos."""

import logging
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

from aim.config.parameters import FACTOR_WEIGHTS

logger = logging.getLogger(__name__)


def calculate_z_score(values: pd.Series) -> pd.Series:
    """
    Calcula z-score para uma série de valores.
    
    Fórmula: z = (x - μ) / σ
    
    Args:
        values: Série de valores
    
    Returns:
        Série de z-scores
    """
    mean = values.mean()
    std = values.std()
    
    if std == 0 or pd.isna(std):
        return pd.Series(0.0, index=values.index)
    
    return (values - mean) / std


def calculate_percentile_rank(values: pd.Series) -> pd.Series:
    """
    Calcula percentil rank (0-100) para uma série.
    
    Args:
        values: Série de valores
    
    Returns:
        Série com percentis (0-100)
    """
    return values.rank(pct=True) * 100


def calculate_momentum_score(
    df: pd.DataFrame,
) -> pd.Series:
    """
    Calcula score de momentum composto.
    
    Usa momentum 3m, 6m, 12m com pesos definidos.
    
    Args:
        df: DataFrame com colunas momentum_3m, momentum_6m, momentum_12m
    
    Returns:
        Série de scores de momentum (z-score)
    """
    # Preencher NaN com 0 para evitar problemas
    mom_3m = df["momentum_3m"].fillna(0)
    mom_6m = df["momentum_6m"].fillna(0)
    mom_12m = df["momentum_12m"].fillna(0)
    
    # Calcular momentum composto
    composite = (
        0.4 * mom_3m +
        0.3 * mom_6m +
        0.3 * mom_12m
    )
    
    # Normalizar com z-score
    return calculate_z_score(composite)


def calculate_quality_score(
    fundamentals_df: pd.DataFrame,
) -> pd.Series:
    """
    Calcula score de qualidade baseado em fundamentos.
    
    Componentes:
    - ROE (Return on Equity)
    - Margem líquida
    - ROIC
    - Payout ratio (conservadorismo)
    
    Args:
        fundamentals_df: DataFrame com dados fundamentalistas
    
    Returns:
        Série de scores de qualidade
    """
    # Preencher valores ausentes com mediana do universo
    roe = fundamentals_df["roe"].fillna(fundamentals_df["roe"].median())
    margin = fundamentals_df["margem_liquida"].fillna(fundamentals_df["margem_liquida"].median())
    roic = fundamentals_df["roic"].fillna(fundamentals_df["roic"].median())
    
    # Normalizar cada componente
    z_roe = calculate_z_score(roe)
    z_margin = calculate_z_score(margin)
    z_roic = calculate_z_score(roic)
    
    # Score composto
    quality_score = (
        0.4 * z_roe +
        0.3 * z_margin +
        0.3 * z_roic
    )
    
    return quality_score


def calculate_value_score(
    fundamentals_df: pd.DataFrame,
) -> pd.Series:
    """
    Calcula score de valor (inverso dos múltiplos).
    
    Componentes:
    - Inverso do P/L (maior = mais barato)
    - Inverso do P/VP
    - Dividend Yield
    
    Args:
        fundamentals_df: DataFrame com dados fundamentalistas
    
    Returns:
        Série de scores de valor
    """
    # Inverso de P/L (Evitar divisão por zero)
    pl = fundamentals_df["p_l"].replace(0, np.nan)
    inv_pl = (1 / pl).fillna(0)
    
    # Inverso de P/VP
    pvp = fundamentals_df["p_vp"].replace(0, np.nan)
    inv_pvp = (1 / pvp).fillna(0)
    
    # Dividend Yield
    dy = fundamentals_df["dy"].fillna(0)
    
    # Normalizar
    z_inv_pl = calculate_z_score(inv_pl)
    z_inv_pvp = calculate_z_score(inv_pvp)
    z_dy = calculate_z_score(dy)
    
    # Score composto
    value_score = (
        0.4 * z_inv_pl +
        0.3 * z_inv_pvp +
        0.3 * z_dy
    )
    
    return value_score


def calculate_volatility_score(
    features_df: pd.DataFrame,
) -> pd.Series:
    """
    Calcula score de volatilidade (inverso - menos vol = maior score).
    
    Args:
        features_df: DataFrame com colunas de volatilidade
    
    Returns:
        Série de scores de volatilidade
    """
    # Usar vol de 63 dias (~3 meses)
    vol = features_df["vol_63d"].fillna(features_df["vol_63d"].median())
    
    # Inverso (menor vol = maior score)
    inv_vol = 1 / (vol + 0.001)  # Evitar divisão por zero
    
    return calculate_z_score(inv_vol)


def calculate_liquidity_score_normalized(
    features_df: pd.DataFrame,
) -> pd.Series:
    """
    Normaliza score de liquidez para z-score.
    
    Args:
        features_df: DataFrame com liquidity_score
    
    Returns:
        Série de scores de liquidez normalizado
    """
    liquidity = features_df["liquidity_score"].fillna(0.5)
    return calculate_z_score(liquidity)


def calculate_composite_score(
    features_df: pd.DataFrame,
    fundamentals_df: Optional[pd.DataFrame] = None,
    regime: str = "TRANSITION",
) -> pd.DataFrame:
    """
    Calcula score final multi-fator para todos os ativos.
    
    Args:
        features_df: DataFrame com features técnicas
        fundamentals_df: DataFrame com dados fundamentalistas (opcional)
        regime: Regime de mercado atual (afeta pesos)
    
    Returns:
        DataFrame com scores individuais e final
    """
    logger.info(f"Calculando scores com pesos de regime: {regime}")
    
    # Obter pesos do regime
    weights = FACTOR_WEIGHTS.get(regime, FACTOR_WEIGHTS["TRANSITION"])
    
    # Preparar DataFrame de resultados
    results = pd.DataFrame()
    results["ticker"] = features_df["ticker"]
    
    # 1. Score de Momentum (sempre disponível)
    results["score_momentum"] = calculate_momentum_score(features_df)
    
    # 2. Score de Volatilidade (sempre disponível)
    results["score_volatility"] = calculate_volatility_score(features_df)
    
    # 3. Score de Liquidez (sempre disponível)
    results["score_liquidity"] = calculate_liquidity_score_normalized(features_df)
    
    # 4. Score de Qualidade (se houver fundamentos)
    if fundamentals_df is not None and not fundamentals_df.empty:
        # Merge por ticker
        merged = results.merge(
            fundamentals_df,
            on="ticker",
            how="left"
        )
        results["score_quality"] = calculate_quality_score(merged)
        has_quality = True
    else:
        results["score_quality"] = 0.0
        has_quality = False
        logger.warning("Sem dados fundamentalistas - score de qualidade = 0")
    
    # 5. Score de Valor (se houver fundamentos)
    if fundamentals_df is not None and not fundamentals_df.empty:
        merged = results.merge(
            fundamentals_df,
            on="ticker",
            how="left"
        )
        results["score_value"] = calculate_value_score(merged)
        has_value = True
    else:
        results["score_value"] = 0.0
        has_value = False
        logger.warning("Sem dados fundamentalistas - score de valor = 0")
    
    # Calcular score final ponderado
    # Se não houver qualidade/valor, redistribuir pesos
    if not has_quality and not has_value:
        # Usar apenas momentum, volatilidade, liquidez
        effective_weights = {
            "momentum": 0.5,
            "volatility": 0.3,
            "liquidity": 0.2,
        }
    elif not has_quality:
        effective_weights = {
            "momentum": weights["momentum"] + weights["quality"] * 0.5,
            "value": weights["value"] + weights["quality"] * 0.5,
            "volatility": weights["volatility"],
            "liquidity": weights["liquidity"],
        }
    elif not has_value:
        effective_weights = {
            "momentum": weights["momentum"] + weights["value"] * 0.5,
            "quality": weights["quality"] + weights["value"] * 0.5,
            "volatility": weights["volatility"],
            "liquidity": weights["liquidity"],
        }
    else:
        effective_weights = weights
    
    # Calcular score final
    results["score_final"] = (
        effective_weights.get("momentum", 0) * results["score_momentum"] +
        effective_weights.get("quality", 0) * results["score_quality"] +
        effective_weights.get("value", 0) * results["score_value"] +
        effective_weights.get("volatility", 0) * results["score_volatility"] +
        effective_weights.get("liquidity", 0) * results["score_liquidity"]
    )
    
    # Calcular ranking no universo
    results["rank_universe"] = results["score_final"].rank(ascending=False).astype(int)
    
    # Adicionar data e regime
    results["date"] = features_df["date"].iloc[0] if "date" in features_df.columns else None
    results["regime_at_date"] = regime
    
    logger.info(f"✓ Scores calculados para {len(results)} ativos")
    logger.info(f"  Top 5: {results.nlargest(5, 'score_final')['ticker'].tolist()}")
    
    return results
