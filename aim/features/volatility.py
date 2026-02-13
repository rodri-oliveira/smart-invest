"""Cálculos de volatilidade e risco."""

from typing import Dict, Optional

import numpy as np
import pandas as pd

from aim.config.parameters import VOLATILITY_WINDOWS


def calculate_volatility(
    prices: pd.Series,
    window: int = 63,
    annualize: bool = True,
) -> Optional[float]:
    """
    Calcula volatilidade (desvio padrão dos retornos).

    Fórmula: σ_anual = σ_diária × √252

    Args:
        prices: Série de preços
        window: Período em dias (padrão: 63 = ~3 meses)
        annualize: Se True, anualiza a volatilidade

    Returns:
        Volatilidade como decimal (ex: 0.25 = 25% ao ano)
    """
    if len(prices) < window + 1:  # Precisa de n+1 para calcular retornos
        return None

    # Calcular retornos logarítmicos
    # log(Pt / Pt-1) - mais estatisticamente corretos
    log_returns = np.log(prices / prices.shift(1)).dropna()

    if len(log_returns) < window:
        return None

    # Calcular desvio padrão
    daily_vol = log_returns.tail(window).std()

    if pd.isna(daily_vol) or daily_vol == 0:
        return None

    if annualize:
        # Anualizar: σ_anual = σ_diária × √252
        return daily_vol * np.sqrt(252)
    else:
        return daily_vol


def calculate_volatility_simple(
    prices: pd.Series,
    window: int = 63,
    annualize: bool = True,
) -> Optional[float]:
    """
    Calcula volatilidade usando retornos aritméticos simples.
    Mais intuitivo, mas menos preciso estatisticamente.

    Args:
        prices: Série de preços
        window: Período em dias
        annualize: Anualizar resultado

    Returns:
        Volatilidade como decimal
    """
    if len(prices) < window + 1:
        return None

    # Retornos aritméticos simples
    simple_returns = prices.pct_change().dropna()

    if len(simple_returns) < window:
        return None

    daily_vol = simple_returns.tail(window).std()

    if pd.isna(daily_vol):
        return None

    if annualize:
        return daily_vol * np.sqrt(252)
    else:
        return daily_vol


def calculate_volatility_multiple_windows(
    prices: pd.Series,
) -> Dict[str, Optional[float]]:
    """
    Calcula volatilidade em múltiplas janelas.

    Returns:
        Dict com vol_21d, vol_63d, vol_126d
    """
    return {
        "vol_21d": calculate_volatility(prices, VOLATILITY_WINDOWS["short"]),
        "vol_63d": calculate_volatility(prices, VOLATILITY_WINDOWS["medium"]),
        "vol_126d": calculate_volatility(prices, VOLATILITY_WINDOWS["long"]),
    }


def calculate_volatility_score(
    prices: pd.Series,
    window: int = 63,
) -> Optional[float]:
    """
    Calcula score de volatilidade (inverso).
    Menor volatilidade = maior score.

    Fórmula: score = 1 / (1 + vol_anualizada)

    Score normalizado entre 0 e 1.
    """
    vol = calculate_volatility(prices, window, annualize=True)
    if vol is None:
        return None

    # Inverter: menor vol = maior score
    # Usar 1 / (1 + vol) para manter entre 0 e 1
    score = 1 / (1 + vol)

    return score


def calculate_max_drawdown(
    prices: pd.Series,
) -> Optional[float]:
    """
    Calcula Maximum Drawdown (queda máxima de pico a vale).

    Fórmula:
    - Calcular pico acumulado (running max)
    - Calcular drawdown em cada ponto: (preço - pico) / pico
    - Retornar o mínimo (maior queda)

    Args:
        prices: Série de preços

    Returns:
        Max Drawdown como decimal negativo (ex: -0.30 = -30%)
    """
    if len(prices) < 2:
        return None

    # Pego acumulado
    running_max = prices.cummax()

    # Drawdown em cada ponto
    drawdown = (prices - running_max) / running_max

    # Máximo drawdown (mais negativo)
    max_dd = drawdown.min()

    if pd.isna(max_dd):
        return None

    return max_dd


def calculate_calmar_ratio(
    prices: pd.Series,
    window: int = 252,
) -> Optional[float]:
    """
    Calcula Calmar Ratio (retorno anualizado / max drawdown).

    Fórmula: Calmar = CAGR / |Max DD|

    Interpretação:
    - > 3.0: Excelente
    - 2.0-3.0: Bom
    - 1.0-2.0: Razoável
    - < 1.0: Ruim
    """
    if len(prices) < window:
        return None

    # CAGR
    total_return = (prices.iloc[-1] / prices.iloc[-window]) - 1
    cagr = (1 + total_return) ** (252 / window) - 1

    # Max DD no período
    max_dd = calculate_max_drawdown(prices.tail(window))

    if max_dd is None or max_dd == 0:
        return None

    # Calmar = CAGR / |Max DD|
    calmar = cagr / abs(max_dd)

    return calmar


def calculate_var(
    prices: pd.Series,
    confidence: float = 0.05,
    window: int = 252,
) -> Optional[float]:
    """
    Calcula Value at Risk (VaR) histórico.

    Interpretação: Com 95% de confiança, a perda não excederá o VaR.

    Args:
        prices: Série de preços
        confidence: Nível de confiança (0.05 = 95%)
        window: Período de lookback

    Returns:
        VaR como decimal negativo (ex: -0.02 = -2%)
    """
    if len(prices) < window:
        return None

    returns = prices.pct_change().dropna().tail(window)

    if len(returns) < 20:
        return None

    # Percentil dos retornos
    var = returns.quantile(confidence)

    return var


def calculate_beta(
    asset_returns: pd.Series,
    market_returns: pd.Series,
    window: int = 252,
) -> Optional[float]:
    """
    Calcula Beta do ativo vs mercado.

    Fórmula: β = Cov(ret_ativo, ret_mercado) / Var(ret_mercado)

    Interpretação:
    - β = 1: Move igual ao mercado
    - β > 1: Mais volátil que mercado
    - β < 1: Menos volátil que mercado
    - β < 0: Inverso ao mercado (raríssimo)
    """
    if len(asset_returns) < window or len(market_returns) < window:
        return None

    # Alinhar datas
    combined = pd.DataFrame({
        "asset": asset_returns,
        "market": market_returns,
    }).dropna()

    if len(combined) < 30:  # Mínimo 1 mês
        return None

    # Usar período mais recente
    recent = combined.tail(window)

    # Calcular beta
    covariance = recent["asset"].cov(recent["market"])
    market_variance = recent["market"].var()

    if market_variance == 0:
        return None

    beta = covariance / market_variance

    return beta


def calculate_risk_metrics(
    prices: pd.Series,
    market_prices: Optional[pd.Series] = None,
) -> Dict[str, Optional[float]]:
    """
    Calcula todas as métricas de risco principais.

    Args:
        prices: Preços do ativo
        market_prices: Preços do benchmark (Ibovespa) para Beta

    Returns:
        Dict com volatilidade, max drawdown, Calmar, VaR, Beta
    """
    metrics = {
        "volatility_21d": calculate_volatility(prices, 21),
        "volatility_63d": calculate_volatility(prices, 63),
        "volatility_126d": calculate_volatility(prices, 126),
        "max_drawdown": calculate_max_drawdown(prices),
        "calmar_ratio": calculate_calmar_ratio(prices),
        "var_95": calculate_var(prices, 0.05),
        "beta": None,
    }

    if market_prices is not None:
        asset_returns = prices.pct_change()
        market_returns = market_prices.pct_change()
        metrics["beta"] = calculate_beta(asset_returns, market_returns)

    return metrics
