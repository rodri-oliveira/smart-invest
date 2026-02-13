"""Cálculos de liquidez."""

from typing import Dict, Optional

import numpy as np
import pandas as pd

from aim.config.parameters import MIN_LIQUIDITY_DAILY


def calculate_average_volume(
    volume: pd.Series,
    window: int = 20,
) -> Optional[float]:
    """
    Calcula volume médio em unidades (ações).

    Args:
        volume: Série de volumes diários
        window: Período em dias (padrão: 20 = ~1 mês)

    Returns:
        Volume médio ou None se dados insuficientes
    """
    if len(volume) < window:
        return None

    avg_volume = volume.tail(window).mean()

    if pd.isna(avg_volume) or avg_volume < 0:
        return None

    return float(avg_volume)


def calculate_average_dollar_volume(
    prices: pd.Series,
    volume: pd.Series,
    window: int = 20,
) -> Optional[float]:
    """
    Calcula volume financeiro médio diário.

    Fórmula: média(preço × volume)

    Args:
        prices: Série de preços
        volume: Série de volumes
        window: Período em dias

    Returns:
        Volume financeiro médio (R$)
    """
    if len(prices) < window or len(volume) < window:
        return None

    # Alinhar datas
    df = pd.DataFrame({"price": prices, "volume": volume}).dropna()

    if len(df) < window:
        return None

    # Volume financeiro = preço × volume
    df["dollar_volume"] = df["price"] * df["volume"]

    avg_dollar_volume = df["dollar_volume"].tail(window).mean()

    if pd.isna(avg_dollar_volume) or avg_dollar_volume < 0:
        return None

    return float(avg_dollar_volume)


def calculate_liquidity_score(
    prices: pd.Series,
    volume: pd.Series,
    window: int = 20,
) -> Optional[float]:
    """
    Calcula score de liquidez normalizado.

    Score baseado no volume financeiro médio.
    Quanto maior o volume, maior o score.

    Normalização logarítmica para evitar skewness:
    score = log(1 + volume / 1M) / log(100M / 1M)

    Args:
        prices: Série de preços
        volume: Série de volumes
        window: Período em dias

    Returns:
        Score entre 0 e 1
    """
    dollar_volume = calculate_average_dollar_volume(prices, volume, window)

    if dollar_volume is None:
        return None

    # Usar escala logarítmica para normalizar
    # Referência: 1M = score baixo, 100M = score alto
    log_score = np.log10(1 + dollar_volume / MIN_LIQUIDITY_DAILY)

    # Normalizar para 0-1 (assumindo range 1M a 1B)
    # log10(1) = 0, log10(1000) ≈ 3
    normalized_score = min(log_score / 3.0, 1.0)

    return float(normalized_score)


def calculate_relative_liquidity_score(
    ticker_dollar_volume: float,
    universe_volumes: Dict[str, float],
) -> float:
    """
    Calcula score de liquidez relativo ao universo.

    Usa percentil dentro do universo.

    Args:
        ticker_dollar_volume: Volume financeiro do ativo
        universe_volumes: Dict {ticker: volume} de todo o universo

    Returns:
        Percentil (0 a 1, onde 1 = mais líquido)
    """
    if not universe_volumes:
        return 0.5  # Neutro se não houver dados

    volumes = list(universe_volumes.values())

    if not volumes or len(volumes) < 2:
        return 0.5

    # Calcular percentil
    below = sum(1 for v in volumes if v < ticker_dollar_volume)
    percentile = below / len(volumes)

    return percentile


def check_liquidity_filter(
    prices: pd.Series,
    volume: pd.Series,
    min_dollar_volume: float = MIN_LIQUIDITY_DAILY,
    window: int = 20,
) -> bool:
    """
    Verifica se ativo passa no filtro mínimo de liquidez.

    Args:
        prices: Série de preços
        volume: Série de volumes
        min_dollar_volume: Volume mínimo requerido (R$)
        window: Período para média

    Returns:
        True se liquidez é suficiente
    """
    dollar_volume = calculate_average_dollar_volume(prices, volume, window)

    if dollar_volume is None:
        return False

    return dollar_volume >= min_dollar_volume


def calculate_liquidity_metrics(
    prices: pd.Series,
    volume: pd.Series,
    window: int = 20,
) -> Dict[str, Optional[float]]:
    """
    Calcula todas as métricas de liquidez.

    Args:
        prices: Série de preços
        volume: Série de volumes
        window: Período em dias

    Returns:
        Dict com volume médio, volume financeiro, score
    """
    return {
        "avg_volume": calculate_average_volume(volume, window),
        "avg_dollar_volume": calculate_average_dollar_volume(prices, volume, window),
        "liquidity_score": calculate_liquidity_score(prices, volume, window),
    }


def get_liquidity_tier(dollar_volume: Optional[float]) -> str:
    """
    Classifica ativo em tier de liquidez.

    Args:
        dollar_volume: Volume financeiro médio

    Returns:
        Tier: "ILLIQUID", "LOW", "MEDIUM", "HIGH", "VERY_HIGH"
    """
    if dollar_volume is None:
        return "UNKNOWN"

    if dollar_volume < 500_000:
        return "ILLIQUID"
    elif dollar_volume < 1_000_000:
        return "LOW"
    elif dollar_volume < 5_000_000:
        return "MEDIUM"
    elif dollar_volume < 20_000_000:
        return "HIGH"
    else:
        return "VERY_HIGH"
