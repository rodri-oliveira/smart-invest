"""Cálculos de momentum para ativos."""

from typing import Dict, List, Optional

import numpy as np
import pandas as pd

from aim.config.parameters import MOMENTUM_WINDOWS


def calculate_absolute_momentum(
    prices: pd.Series,
    window: int = 126,
) -> Optional[float]:
    """
    Calcula momentum absoluto (retorno total no período).

    Fórmula: (P_final / P_inicial) - 1

    Args:
        prices: Série de preços (fechamento ajustado)
        window: Período em dias (padrão: 126 = ~6 meses)

    Returns:
        Retorno percentual ou None se dados insuficientes
        Ex: 0.15 = 15% de retorno
    """
    if len(prices) < window:
        return None

    # Usar preços disponíveis (pode ter gaps)
    start_price = prices.iloc[-window]
    end_price = prices.iloc[-1]

    if pd.isna(start_price) or pd.isna(end_price) or start_price <= 0:
        return None

    return (end_price / start_price) - 1


def calculate_annualized_return(
    prices: pd.Series,
    window: int = 252,
) -> Optional[float]:
    """
    Calcula retorno anualizado.

    Fórmula: (P_final / P_inicial) ^ (252/n) - 1

    Args:
        prices: Série de preços
        window: Período em dias

    Returns:
        Retorno anualizado ou None
    """
    total_return = calculate_absolute_momentum(prices, window)
    if total_return is None:
        return None

    # Anualizar
    n = min(window, len(prices))
    if n < 20:  # Mínimo ~1 mês
        return None

    return (1 + total_return) ** (252 / n) - 1


def calculate_composite_momentum(
    prices: pd.Series,
    weights: Optional[Dict[str, float]] = None,
) -> Dict[str, Optional[float]]:
    """
    Calcula momentum composto com múltiplos períodos.

    Fórmula padrão:
    - 40% × momentum 3 meses (63 dias)
    - 30% × momentum 6 meses (126 dias)
    - 30% × momentum 12 meses (252 dias)

    Baseado em research de Meb Faber e Gary Antonacci.

    Args:
        prices: Série de preços
        weights: Pesos customizados {short: 0.4, medium: 0.3, long: 0.3}

    Returns:
        Dict com:
        - momentum_3m: Retorno 3 meses
        - momentum_6m: Retorno 6 meses
        - momentum_12m: Retorno 12 meses
        - momentum_composite: Score composto ponderado
    """
    if weights is None:
        weights = {"short": 0.4, "medium": 0.3, "long": 0.3}

    mom_3m = calculate_absolute_momentum(prices, MOMENTUM_WINDOWS["short"])
    mom_6m = calculate_absolute_momentum(prices, MOMENTUM_WINDOWS["medium"])
    mom_12m = calculate_absolute_momentum(prices, MOMENTUM_WINDOWS["long"])

    # Calcular composto apenas com os disponíveis
    available_weights = 0.0
    weighted_sum = 0.0

    if mom_3m is not None:
        weighted_sum += weights["short"] * mom_3m
        available_weights += weights["short"]

    if mom_6m is not None:
        weighted_sum += weights["medium"] * mom_6m
        available_weights += weights["medium"]

    if mom_12m is not None:
        weighted_sum += weights["long"] * mom_12m
        available_weights += weights["long"]

    # Normalizar pelos pesos disponíveis
    if available_weights > 0:
        composite = weighted_sum / available_weights
    else:
        composite = None

    return {
        "momentum_3m": mom_3m,
        "momentum_6m": mom_6m,
        "momentum_12m": mom_12m,
        "momentum_composite": composite,
    }


def calculate_relative_momentum(
    returns_dict: Dict[str, float],
) -> Dict[str, float]:
    """
    Calcula momentum relativo (cross-sectional).
    Normaliza retornos dentro do universo usando z-score.

    Fórmula: z = (retorno - média) / desvio_padrão

    Args:
        returns_dict: {ticker: retorno_absoluto}

    Returns:
        {ticker: z_score}
    """
    if len(returns_dict) < 2:
        return {ticker: 0.0 for ticker in returns_dict}

    returns = list(returns_dict.values())
    mean_return = np.mean(returns)
    std_return = np.std(returns)

    if std_return == 0:
        return {ticker: 0.0 for ticker in returns_dict}

    z_scores = {
        ticker: (ret - mean_return) / std_return
        for ticker, ret in returns_dict.items()
    }

    return z_scores


def calculate_dual_momentum_score(
    ticker: str,
    prices: pd.Series,
    benchmark_returns: Dict[str, float],
) -> Dict[str, float]:
    """
    Calcula Dual Momentum (Antonacci).

    Combina:
    1. Absolute momentum (time-series): Ativo está em tendência positiva?
    2. Relative momentum (cross-sectional): Ativo está performando bem vs outros?

    Args:
        ticker: Código do ativo
        prices: Série de preços do ativo
        benchmark_returns: Retornos de todos os ativos do universo

    Returns:
        Dict com scores absoluto, relativo e dual
    """
    # Absolute momentum (6 meses)
    abs_mom = calculate_absolute_momentum(prices, 126) or 0.0

    # Relative momentum
    rel_scores = calculate_relative_momentum(benchmark_returns)
    rel_mom = rel_scores.get(ticker, 0.0)

    # Dual momentum = combinação
    # Só pontua alto se ambos forem positivos
    if abs_mom > 0 and rel_mom > 0:
        dual_score = abs_mom * (1 + rel_mom)  # Synergy
    else:
        dual_score = min(abs_mom, 0) + min(rel_mom * 0.5, 0)  # Penalidade

    return {
        "absolute_momentum": abs_mom,
        "relative_momentum": rel_mom,
        "dual_momentum": dual_score,
    }


def calculate_momentum_for_universe(
    prices_df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Calcula momentum para universo inteiro de ativos.

    Args:
        prices_df: DataFrame com colunas [ticker, date, close]

    Returns:
        DataFrame com colunas de momentum
    """
    results = []

    for ticker in prices_df["ticker"].unique():
        ticker_prices = prices_df[prices_df["ticker"] == ticker].sort_values("date")

        if len(ticker_prices) < 63:  # Mínimo 3 meses
            continue

        prices_series = ticker_prices["close"].reset_index(drop=True)
        mom_data = calculate_composite_momentum(prices_series)

        results.append({
            "ticker": ticker,
            **mom_data,
        })

    return pd.DataFrame(results)
