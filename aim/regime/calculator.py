"""Cálculos de regime de mercado baseados em indicadores macro."""

from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from aim.config.parameters import (
    REGIME_THRESHOLDS,
    REGIME_VARIABLE_WEIGHTS,
)


def calculate_yield_curve_score(
    selic_data: pd.DataFrame,
    lookback_days: int = 21,
) -> Tuple[Optional[float], Optional[float]]:
    """
    Calcula score da curva de juros.
    
    Proxy: Tendência da SELIC (quando sobe = aperto = RISK OFF)
    
    Args:
        selic_data: DataFrame com [date, value]
        lookback_days: Janela de análise
    
    Returns:
        (score, valor_raw)
        Score: -2 a +2
    """
    if selic_data.empty or len(selic_data) < lookback_days:
        return None, None
    
    recent = selic_data.tail(lookback_days)
    
    # Calcular inclinação (tendência)
    x = np.arange(len(recent))
    y = recent["value"].values
    
    slope = np.polyfit(x, y, 1)[0]
    
    # Normalizar: slope de -0.1 a +0.1 por dia
    # SELIC caindo = RISK ON (+2)
    # SELIC estável = NEUTRO (0)
    # SELIC subindo = RISK OFF (-2)
    normalized = max(-2, min(2, -slope * 100))
    
    return normalized, slope


def calculate_risk_spread_score(
    usd_data: pd.DataFrame,
    lookback_days: int = 21,
) -> Tuple[Optional[float], Optional[float]]:
    """
    Calcula score do spread de risco.
    
    Proxy: Tendência do dólar (quando sobe = fuga de capital = RISK OFF)
    
    Args:
        usd_data: DataFrame com [date, value]
        lookback_days: Janela de análise
    
    Returns:
        (score, valor_raw)
    """
    if usd_data.empty or len(usd_data) < lookback_days:
        return None, None
    
    recent = usd_data.tail(lookback_days)
    
    # Calcular inclinação
    x = np.arange(len(recent))
    y = recent["value"].values
    
    slope = np.polyfit(x, y, 1)[0]
    
    # Dólar caindo = RISK ON (+2)
    # Dólar estável = NEUTRO (0)
    # Dólar subindo = RISK OFF (-2)
    normalized = max(-2, min(2, -slope * 100))
    
    return normalized, slope


def calculate_ibov_trend_score(
    ibov_prices: pd.Series,
    mm_short: int = 50,
    mm_long: int = 200,
) -> Tuple[Optional[float], Dict]:
    """
    Calcula score da tendência do Ibovespa.
    
    Baseado em:
    - Preço vs MM200 (trend following)
    - Inclinação da MM50 (momentum)
    
    Args:
        ibov_prices: Série de preços do IBOV
        mm_short: Período da média curta (50)
        mm_long: Período da média longa (200)
    
    Returns:
        (score, detalhes)
    """
    if len(ibov_prices) < mm_long:
        return None, {}
    
    # Calcular médias móveis
    mm50 = ibov_prices.rolling(window=mm_short).mean()
    mm200 = ibov_prices.rolling(window=mm_long).mean()
    
    # Score 1: Preço vs MM200
    # Acima = bullish (+1), Abaixo = bearish (-1)
    price_vs_mm200 = 1 if ibov_prices.iloc[-1] > mm200.iloc[-1] else -1
    
    # Score 2: Inclinação da MM50 (últimos 20 dias)
    mm50_recent = mm50.tail(20)
    x = np.arange(len(mm50_recent))
    y = mm50_recent.values
    mm50_slope = np.polyfit(x, y, 1)[0]
    
    # MM50 subindo = +1, descendo = -1
    mm50_trend = 1 if mm50_slope > 0 else -1 if mm50_slope < 0 else 0
    
    # Score composto (máximo +2, mínimo -2)
    score = price_vs_mm200 + mm50_trend
    
    details = {
        "price_vs_mm200": price_vs_mm200,
        "mm50_trend": mm50_trend,
        "mm50_slope": mm50_slope,
        "current_price": ibov_prices.iloc[-1],
        "mm50_current": mm50.iloc[-1],
        "mm200_current": mm200.iloc[-1],
    }
    
    return score, details


def calculate_capital_flow_score(
    usd_data: pd.DataFrame,
    ibov_data: pd.DataFrame,
    lookback_days: int = 21,
) -> Tuple[Optional[float], Optional[float]]:
    """
    Calcula score do fluxo de capitais.
    
    Proxy: Correlação entre dólar e Ibovespa
    - Corr negativa forte = fluxo entrando (RISK ON)
    - Corr positiva = fuga (RISK OFF)
    
    Args:
        usd_data: DataFrame com [date, value]
        ibov_data: DataFrame com [date, value]
        lookback_days: Janela de análise
    
    Returns:
        (score, correlação)
    """
    if usd_data.empty or ibov_data.empty:
        return None, None
    
    # Merge por data
    merged = pd.merge(usd_data, ibov_data, on="date", suffixes=("_usd", "_ibov"))
    
    if len(merged) < lookback_days:
        return None, None
    
    recent = merged.tail(lookback_days)
    
    # Calcular correlação
    correlation = recent["value_usd"].corr(recent["value_ibov"])
    
    if pd.isna(correlation):
        return None, None
    
    # Normalizar: corr de -1 a +1
    # -1 (dólar cai, ibov sobe) = RISK ON (+2)
    # 0 (sem relação) = NEUTRO (0)
    # +1 (dólar sobe, ibov cai) = RISK OFF (-2)
    score = -correlation * 2  # Inverter e escalar
    score = max(-2, min(2, score))
    
    return score, correlation


def calculate_liquidity_sentiment_score(
    ibov_volume: pd.Series,
    ibov_volatility: pd.Series,
    lookback_days: int = 21,
) -> Tuple[Optional[float], Dict]:
    """
    Calcula score de liquidez/sentimento.
    
    Baseado em:
    - Volume médio (liquidez)
    - Volatilidade implícita (medo = VIX-like)
    
    Args:
        ibov_volume: Série de volumes do IBOV
        ibov_volatility: Série de volatilidade (std dos retornos)
        lookback_days: Janela de análise
    
    Returns:
        (score, detalhes)
    """
    if len(ibov_volume) < lookback_days or len(ibov_volatility) < lookback_days:
        return None, {}
    
    # Volume: acima da média = interesse = RISK ON (+1)
    volume_recent = ibov_volume.tail(lookback_days).mean()
    volume_baseline = ibov_volume.tail(252).mean()  # Média anual
    
    if volume_baseline > 0:
        volume_ratio = volume_recent / volume_baseline
        volume_score = 1 if volume_ratio > 1.1 else -1 if volume_ratio < 0.9 else 0
    else:
        volume_score = 0
    
    # Volatilidade: baixa = calma = RISK ON (+1)
    # Alta = medo = RISK OFF (-1)
    vol_recent = ibov_volatility.tail(lookback_days).mean()
    vol_baseline = ibov_volatility.tail(252).mean()
    
    if vol_baseline > 0:
        vol_ratio = vol_recent / vol_baseline
        vol_score = 1 if vol_ratio < 0.9 else -1 if vol_ratio > 1.1 else 0
    else:
        vol_score = 0
    
    # Score composto
    score = volume_score + vol_score
    
    details = {
        "volume_score": volume_score,
        "volatility_score": vol_score,
        "volume_ratio": volume_ratio if volume_baseline > 0 else None,
        "volatility_ratio": vol_ratio if vol_baseline > 0 else None,
    }
    
    return score, details


def classify_regime_from_scores(
    scores: Dict[str, float],
) -> Tuple[str, float, Dict]:
    """
    Classifica regime baseado nos scores individuais.
    
    Args:
        scores: Dict com scores de cada variável
    
    Returns:
        (regime, score_total, detalhes)
    """
    weights = REGIME_VARIABLE_WEIGHTS
    
    # Calcular score ponderado
    total_score = 0.0
    weighted_sum = 0.0
    
    for variable, score in scores.items():
        if score is not None:
            weight = weights.get(variable, 1.0)
            weighted_sum += score * weight
            total_score += weight
    
    # Normalizar
    if total_score > 0:
        final_score = weighted_sum / (total_score / 2)  # Dividir por metade do peso total
    else:
        final_score = 0.0
    
    # Classificar
    if final_score >= REGIME_THRESHOLDS["risk_on_strong"]:
        regime = "RISK_ON_STRONG"
    elif final_score >= REGIME_THRESHOLDS["risk_on"]:
        regime = "RISK_ON"
    elif final_score <= REGIME_THRESHOLDS["risk_off_strong"]:
        regime = "RISK_OFF_STRONG"
    elif final_score <= REGIME_THRESHOLDS["risk_off"]:
        regime = "RISK_OFF"
    else:
        regime = "TRANSITION"
    
    details = {
        "final_score": final_score,
        "weighted_sum": weighted_sum,
        "total_weight": total_score,
        "individual_scores": scores,
    }
    
    return regime, final_score, details
