"""Regime de mercado - classificação Risk ON/Risk OFF."""

from aim.regime.calculator import (
    calculate_capital_flow_score,
    calculate_ibov_trend_score,
    calculate_liquidity_sentiment_score,
    calculate_risk_spread_score,
    calculate_yield_curve_score,
    classify_regime_from_scores,
)
from aim.regime.engine import (
    calculate_regime_for_date,
    get_current_regime,
    get_regime_history,
    save_regime_state,
    update_daily_regime,
)

__all__ = [
    # Calculator
    "calculate_yield_curve_score",
    "calculate_risk_spread_score", 
    "calculate_ibov_trend_score",
    "calculate_capital_flow_score",
    "calculate_liquidity_sentiment_score",
    "classify_regime_from_scores",
    # Engine
    "calculate_regime_for_date",
    "save_regime_state",
    "get_current_regime",
    "get_regime_history",
    "update_daily_regime",
]
