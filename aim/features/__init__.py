"""Feature Engineering - cálculos técnicos de ativos."""

from aim.features.engine import (
    calculate_all_features,
    calculate_features_for_ticker,
    get_features_for_date,
    get_latest_features,
)
from aim.features.liquidity import (
    calculate_average_dollar_volume,
    calculate_average_volume,
    calculate_liquidity_metrics,
    calculate_liquidity_score,
    calculate_relative_liquidity_score,
    check_liquidity_filter,
    get_liquidity_tier,
)
from aim.features.momentum import (
    calculate_absolute_momentum,
    calculate_annualized_return,
    calculate_composite_momentum,
    calculate_dual_momentum_score,
    calculate_momentum_for_universe,
    calculate_relative_momentum,
)
from aim.features.volatility import (
    calculate_beta,
    calculate_calmar_ratio,
    calculate_max_drawdown,
    calculate_risk_metrics,
    calculate_var,
    calculate_volatility,
    calculate_volatility_multiple_windows,
    calculate_volatility_score,
    calculate_volatility_simple,
)

__all__ = [
    # Engine
    "calculate_all_features",
    "calculate_features_for_ticker",
    "get_latest_features",
    "get_features_for_date",
    # Momentum
    "calculate_absolute_momentum",
    "calculate_annualized_return",
    "calculate_composite_momentum",
    "calculate_relative_momentum",
    "calculate_dual_momentum_score",
    "calculate_momentum_for_universe",
    # Volatility
    "calculate_volatility",
    "calculate_volatility_simple",
    "calculate_volatility_multiple_windows",
    "calculate_volatility_score",
    "calculate_max_drawdown",
    "calculate_calmar_ratio",
    "calculate_var",
    "calculate_beta",
    "calculate_risk_metrics",
    # Liquidity
    "calculate_average_volume",
    "calculate_average_dollar_volume",
    "calculate_liquidity_score",
    "calculate_relative_liquidity_score",
    "check_liquidity_filter",
    "calculate_liquidity_metrics",
    "get_liquidity_tier",
]
