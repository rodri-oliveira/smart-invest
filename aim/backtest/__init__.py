"""Backtest Engine - simulação histórica de estratégias."""

from aim.backtest.engine import (
    calculate_backtest_metrics,
    load_historical_data,
    run_backtest,
    save_backtest_result,
)

__all__ = [
    "load_historical_data",
    "calculate_backtest_metrics",
    "run_backtest",
    "save_backtest_result",
]
