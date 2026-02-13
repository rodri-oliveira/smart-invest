"""Risk Engine - gestão de risco e position sizing."""

import logging
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from aim.config.parameters import (
    MAX_CONCENTRATION,
    MAX_DRAWDOWN_ACTION,
    MAX_DRAWDOWN_WARNING,
    MAX_POSITION_SIZE,
    MAX_SECTOR_EXPOSURE,
    MIN_POSITION_SIZE,
    TRAILING_STOP_PCT,
)

logger = logging.getLogger(__name__)


def calculate_position_size_risk_based(
    volatility: float,
    max_risk_per_trade: float = 0.02,
    target_portfolio_vol: float = 0.15,
) -> float:
    """
    Calcula tamanho da posição baseado em volatilidade.
    
    Fórmula: Posição = (Risco máximo por trade) / Volatilidade do ativo
    
    Args:
        volatility: Volatilidade anualizada do ativo (ex: 0.25 = 25%)
        max_risk_per_trade: Risco máximo aceitável por posição (default 2%)
        target_portfolio_vol: Volatilidade alvo da carteira (default 15%)
    
    Returns:
        Tamanho da posição como decimal (ex: 0.10 = 10%)
    """
    if volatility <= 0:
        return MIN_POSITION_SIZE
    
    # Kelly Criterion simplificado
    # f* = (mu - r) / sigma^2
    # Aqui usamos uma versão conservadora baseada apenas em vol
    position_size = target_portfolio_vol / (volatility * np.sqrt(10))
    
    # Limitar entre min e max
    position_size = max(MIN_POSITION_SIZE, min(MAX_CONCENTRATION, position_size))
    
    return position_size


def calculate_position_size_equal_weight(
    n_positions: int,
    regime: str = "TRANSITION",
) -> float:
    """
    Calcula peso igual para todas as posições.
    
    Args:
        n_positions: Número de posições na carteira
        regime: Regime de mercado (afeta alocação máxima)
    
    Returns:
        Peso por posição como decimal
    """
    if n_positions <= 0:
        return 0.0
    
    # Peso igual
    equal_weight = 1.0 / n_positions
    
    # Limitar pelo máximo permitido pelo regime
    max_position = MAX_POSITION_SIZE.get(regime, 0.12)
    
    return min(equal_weight, max_position)


def calculate_trailing_stop(
    entry_price: float,
    current_price: float,
    highest_price: float,
    trailing_pct: float = TRAILING_STOP_PCT,
) -> Tuple[bool, float]:
    """
    Verifica se trailing stop foi atingido.
    
    Args:
        entry_price: Preço de entrada
        current_price: Preço atual
        highest_price: Máximo desde entrada
        trailing_pct: Percentual de trailing (default 15%)
    
    Returns:
        (stop_triggered, stop_price)
    """
    stop_price = highest_price * (1 - trailing_pct)
    stop_triggered = current_price <= stop_price
    
    return stop_triggered, stop_price


def calculate_volatility_stop(
    entry_price: float,
    current_price: float,
    volatility: float,
    multiplier: float = 2.0,
) -> Tuple[bool, float]:
    """
    Stop baseado em volatilidade (ATR-style).
    
    Args:
        entry_price: Preço de entrada
        current_price: Preço atual  
        volatility: Volatilidade anualizada
        multiplier: Multiplicador da volatilidade
    
    Returns:
        (stop_triggered, stop_price)
    """
    # Converter vol anualizada para diária aproximada
    daily_vol = volatility / np.sqrt(252)
    
    # Stop = entrada - (volatilidade * multiplicador)
    stop_distance = entry_price * daily_vol * multiplier
    stop_price = entry_price - stop_distance
    
    stop_triggered = current_price <= stop_price
    
    return stop_triggered, stop_price


def check_drawdown_control(
    portfolio_returns: pd.Series,
    current_weights: Dict[str, float],
) -> Tuple[str, Dict[str, float]]:
    """
    Verifica controle de drawdown e ajusta exposição.
    
    Regras:
    - DD < 15%: Operação normal
    - 15% <= DD < 25%: Alerta, reduzir exposição em 25%
    - DD >= 25%: Ação drástica, reduzir exposição pela metade
    
    Args:
        portfolio_returns: Série de retornos da carteira
        current_weights: Pesos atuais {ticker: weight}
    
    Returns:
        (action, new_weights)
    """
    if len(portfolio_returns) < 2:
        return "NORMAL", current_weights
    
    # Calcular drawdown atual
    cumulative = (1 + portfolio_returns).cumprod()
    running_max = cumulative.expanding().max()
    drawdown = (cumulative - running_max) / running_max
    current_dd = abs(drawdown.iloc[-1])
    
    logger.info(f"Drawdown atual: {current_dd:.2%}")
    
    if current_dd >= MAX_DRAWDOWN_ACTION:
        # Redução drástica
        reduction_factor = 0.5
        action = "DRASTIC_REDUCTION"
        logger.warning(f"ALERTA: Drawdown {current_dd:.2%} >= {MAX_DRAWDOWN_ACTION:.2%}")
        logger.warning("Reduzindo exposição pela METADE")
        
    elif current_dd >= MAX_DRAWDOWN_WARNING:
        # Redução moderada
        reduction_factor = 0.75
        action = "MODERATE_REDUCTION"
        logger.warning(f"ALERTA: Drawdown {current_dd:.2%} >= {MAX_DRAWDOWN_WARNING:.2%}")
        logger.warning("Reduzindo exposição em 25%")
        
    else:
        return "NORMAL", current_weights
    
    # Aplicar fator de redução
    new_weights = {
        ticker: weight * reduction_factor
        for ticker, weight in current_weights.items()
    }
    
    return action, new_weights


def check_sector_exposure(
    holdings: List[Dict],
    max_sector_pct: float = MAX_SECTOR_EXPOSURE,
) -> List[str]:
    """
    Verifica exposição por setor.
    
    Args:
        holdings: Lista de posições [{ticker, weight, sector}]
        max_sector_pct: Máximo permitido por setor
    
    Returns:
        Lista de alertas de concentração
    """
    sector_exposure = {}
    
    for holding in holdings:
        sector = holding.get("sector", "UNKNOWN")
        weight = holding.get("weight", 0)
        
        sector_exposure[sector] = sector_exposure.get(sector, 0) + weight
    
    alerts = []
    for sector, exposure in sector_exposure.items():
        if exposure > max_sector_pct:
            alerts.append(
                f"Setor {sector}: {exposure:.1%} (limite: {max_sector_pct:.1%})"
            )
    
    return alerts


def calculate_risk_metrics_portfolio(
    portfolio_returns: pd.Series,
    risk_free_rate: float = 0.0,
) -> Dict[str, float]:
    """
    Calcula métricas de risco da carteira.
    
    Args:
        portfolio_returns: Série de retornos
        risk_free_rate: Taxa livre de risco anualizada
    
    Returns:
        Dict com métricas
    """
    if len(portfolio_returns) < 30:
        return {
            "volatility": 0.0,
            "sharpe": 0.0,
            "max_drawdown": 0.0,
            "var_95": 0.0,
        }
    
    # Volatilidade anualizada
    vol = portfolio_returns.std() * np.sqrt(252)
    
    # Retorno anualizado
    mean_return = portfolio_returns.mean() * 252
    
    # Sharpe Ratio
    if vol > 0:
        sharpe = (mean_return - risk_free_rate) / vol
    else:
        sharpe = 0.0
    
    # Max Drawdown
    cumulative = (1 + portfolio_returns).cumprod()
    running_max = cumulative.expanding().max()
    drawdown = (cumulative - running_max) / running_max
    max_dd = abs(drawdown.min())
    
    # VaR 95%
    var_95 = portfolio_returns.quantile(0.05)
    
    return {
        "volatility": vol,
        "sharpe": sharpe,
        "max_drawdown": max_dd,
        "var_95": var_95,
        "annualized_return": mean_return,
    }


def validate_portfolio_constraints(
    weights: Dict[str, float],
    regime: str,
    sector_data: Optional[Dict[str, str]] = None,
) -> Tuple[bool, List[str]]:
    """
    Valida se carteira respeita todas as restrições.
    
    Args:
        weights: {ticker: peso}
        regime: Regime de mercado
        sector_data: {ticker: setor} (opcional)
    
    Returns:
        (is_valid, list_of_violations)
    """
    violations = []
    
    # 1. Verificar exposição máxima por ativo
    max_position = MAX_POSITION_SIZE.get(regime, 0.12)
    for ticker, weight in weights.items():
        if weight > max_position:
            violations.append(
                f"{ticker}: {weight:.1%} > max {max_position:.1%}"
            )
    
    # 2. Verificar concentração absoluta
    for ticker, weight in weights.items():
        if weight > MAX_CONCENTRATION:
            violations.append(
                f"{ticker}: {weight:.1%} > limite absoluto {MAX_CONCENTRATION:.1%}"
            )
    
    # 3. Verificar posições mínimas
    for ticker, weight in weights.items():
        if 0 < weight < MIN_POSITION_SIZE:
            violations.append(
                f"{ticker}: {weight:.1%} < mínimo {MIN_POSITION_SIZE:.1%}"
            )
    
    # 4. Verificar setores (se dados disponíveis)
    if sector_data:
        sector_exposure = {}
        for ticker, weight in weights.items():
            sector = sector_data.get(ticker, "UNKNOWN")
            sector_exposure[sector] = sector_exposure.get(sector, 0) + weight
        
        for sector, exposure in sector_exposure.items():
            if exposure > MAX_SECTOR_EXPOSURE:
                violations.append(
                    f"Setor {sector}: {exposure:.1%} > max {MAX_SECTOR_EXPOSURE:.1%}"
                )
    
    is_valid = len(violations) == 0
    
    return is_valid, violations
