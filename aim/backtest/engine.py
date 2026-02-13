"""Backtest Engine - simulação histórica de estratégias."""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from aim.data_layer.database import Database
from aim.config.parameters import DEFAULT_BACKTEST_CONFIG

logger = logging.getLogger(__name__)


def load_historical_data(
    db: Database,
    tickers: List[str],
    start_date: str,
    end_date: str,
) -> pd.DataFrame:
    """
    Carrega dados históricos de preços para backtest.
    
    Args:
        db: Conexão com banco
        tickers: Lista de ativos
        start_date: Data inicial
        end_date: Data final
    
    Returns:
        DataFrame com preços [date, ticker, close]
    """
    placeholders = ",".join(["?"] * len(tickers))
    
    query = f"""
        SELECT date, ticker, close
        FROM prices
        WHERE ticker IN ({placeholders})
        AND date BETWEEN ? AND ?
        ORDER BY date, ticker
    """
    
    params = tickers + [start_date, end_date]
    df = db.query_to_df(query, tuple(params))
    
    if df.empty:
        logger.warning("Sem dados históricos para o período")
        return pd.DataFrame()
    
    df["date"] = pd.to_datetime(df["date"])
    df["close"] = df["close"].astype(float)
    
    return df


def calculate_portfolio_returns(
    prices_df: pd.DataFrame,
    holdings: Dict[str, float],
    rebalance_dates: List[str],
    transaction_cost: float = 0.001,
) -> pd.Series:
    """
    Calcula retornos da carteira ao longo do tempo.
    
    Args:
        prices_df: DataFrame de preços
        holdings: Pesos alvo {ticker: weight}
        rebalance_dates: Datas de rebalanceamento
        transaction_cost: Custo de transação (0.1%)
    
    Returns:
        Série de retornos diários
    """
    if prices_df.empty:
        return pd.Series()
    
    # Pivot para formato [date x ticker]
    prices_pivot = prices_df.pivot(index="date", columns="ticker", values="close")
    
    # Calcular retornos diários
    returns = prices_pivot.pct_change()
    
    # Simular rebalanceamento
    portfolio_returns = []
    current_weights = holdings.copy()
    
    for date in returns.index:
        date_str = date.strftime("%Y-%m-%d")
        
        # Verificar se é data de rebalanceamento
        if date_str in rebalance_dates and len(portfolio_returns) > 0:
            # Aplicar custo de transação
            turnover = sum(abs(current_weights.get(t, 0) - holdings.get(t, 0)) 
                          for t in set(current_weights) | set(holdings))
            cost = turnover * transaction_cost
            portfolio_returns.append(-cost)
            current_weights = holdings.copy()
        
        # Calcular retorno do dia
        daily_return = sum(
            current_weights.get(ticker, 0) * returns.loc[date, ticker]
            for ticker in returns.columns
            if not pd.isna(returns.loc[date, ticker])
        )
        
        portfolio_returns.append(daily_return)
    
    return pd.Series(portfolio_returns, index=returns.index)


def calculate_backtest_metrics(
    portfolio_returns: pd.Series,
    benchmark_returns: Optional[pd.Series] = None,
    risk_free_rate: float = 0.0,
) -> Dict[str, float]:
    """
    Calcula métricas de performance do backtest.
    
    Args:
        portfolio_returns: Série de retornos
        benchmark_returns: Retornos do benchmark (opcional)
        risk_free_rate: Taxa livre de risco anualizada
    
    Returns:
        Dict com métricas
    """
    if len(portfolio_returns) < 30:
        return {
            "total_return": 0.0,
            "cagr": 0.0,
            "volatility": 0.0,
            "sharpe_ratio": 0.0,
            "max_drawdown": 0.0,
        }
    
    # Retorno total
    total_return = (1 + portfolio_returns).prod() - 1
    
    # CAGR (retorno anualizado)
    n_years = len(portfolio_returns) / 252
    cagr = (1 + total_return) ** (1 / n_years) - 1 if n_years > 0 else 0.0
    
    # Volatilidade anualizada
    volatility = portfolio_returns.std() * np.sqrt(252)
    
    # Sharpe Ratio
    if volatility > 0:
        sharpe = (cagr - risk_free_rate) / volatility
    else:
        sharpe = 0.0
    
    # Max Drawdown
    cumulative = (1 + portfolio_returns).cumprod()
    running_max = cumulative.expanding().max()
    drawdown = (cumulative - running_max) / running_max
    max_dd = abs(drawdown.min())
    
    # Calmar Ratio
    if max_dd > 0:
        calmar = cagr / max_dd
    else:
        calmar = 0.0
    
    # Beta e Alpha (se tiver benchmark)
    beta = 0.0
    alpha = 0.0
    
    if benchmark_returns is not None and len(benchmark_returns) == len(portfolio_returns):
        # Alinhar séries
        aligned_port = portfolio_returns
        aligned_bench = benchmark_returns.loc[aligned_port.index]
        
        # Calcular beta
        covariance = aligned_port.cov(aligned_bench)
        benchmark_var = aligned_bench.var()
        
        if benchmark_var > 0:
            beta = covariance / benchmark_var
            
            # Calcular alpha (Jensen's Alpha)
            bench_cagr = (1 + aligned_bench).prod() ** (252 / len(aligned_bench)) - 1
            alpha = cagr - (risk_free_rate + beta * (bench_cagr - risk_free_rate))
    
    # Sortino Ratio (usando semi-desvio)
    negative_returns = portfolio_returns[portfolio_returns < 0]
    if len(negative_returns) > 0:
        downside_dev = negative_returns.std() * np.sqrt(252)
        if downside_dev > 0:
            sortino = (cagr - risk_free_rate) / downside_dev
        else:
            sortino = 0.0
    else:
        sortino = 0.0
    
    # Win rate
    positive_days = (portfolio_returns > 0).sum()
    win_rate = positive_days / len(portfolio_returns) if len(portfolio_returns) > 0 else 0.0
    
    return {
        "total_return": total_return,
        "cagr": cagr,
        "volatility": volatility,
        "sharpe_ratio": sharpe,
        "sortino_ratio": sortino,
        "max_drawdown": max_dd,
        "calmar_ratio": calmar,
        "beta": beta,
        "alpha": alpha,
        "win_rate": win_rate,
        "n_trades": len(portfolio_returns),
    }


def run_backtest(
    db: Database,
    strategy_name: str,
    start_date: str,
    end_date: str,
    initial_capital: float = 100_000.0,
    rebalance_frequency: str = "M",  # M = mensal, W = semanal
    max_positions: int = 10,
    transaction_cost: float = 0.001,
) -> Dict:
    """
    Executa backtest completo de uma estratégia.
    
    Args:
        db: Conexão com banco
        strategy_name: Nome da estratégia
        start_date: Data inicial
        end_date: Data final
        initial_capital: Capital inicial
        rebalance_frequency: Frequência de rebalanceamento
        max_positions: Máximo de posições
        transaction_cost: Custo de transação
    
    Returns:
        Dict com resultados do backtest
    """
    logger.info(f"Iniciando backtest: {strategy_name}")
    logger.info(f"Período: {start_date} a {end_date}")
    
    # 1. Carregar dados de mercado
    # Usar IBOV como benchmark
    prices_df = load_historical_data(
        db, ["IBOVESPA"], start_date, end_date
    )
    
    if prices_df.empty:
        return {"error": "Sem dados disponíveis para backtest"}
    
    # Calcular retornos do benchmark
    benchmark_returns = prices_df.pivot(
        index="date", columns="ticker", values="close"
    ).pct_fill()["IBOVESPA"]
    
    # 2. Simular estratégia simplificada
    # Na prática, usaria sinais históricos do banco
    # Aqui simulamos uma estratégia de momentum simples
    
    # Carregar sinais do período
    query = """
        SELECT date, ticker, score_final
        FROM signals
        WHERE date BETWEEN ? AND ?
        ORDER BY date, rank_universe
    """
    signals_df = db.query_to_df(query, (start_date, end_date))
    
    if signals_df.empty:
        logger.warning("Sem sinais históricos - usando dados simulados")
        # Criar dados simulados para teste
        dates = pd.date_range(start=start_date, end=end_date, freq="B")
        portfolio_returns = pd.Series(
            np.random.normal(0.0005, 0.015, len(dates)),
            index=dates
        )
    else:
        # Simular carteira com top N a cada rebalanceamento
        # Simplificação: usar média dos scores
        portfolio_returns = pd.Series()
        
        # Agrupar por data e pegar top N
        for date, group in signals_df.groupby("date"):
            top_signals = group.nlargest(max_positions, "score_final")
            
            # Na prática, calcularíamos retorno da carteira aqui
            # Por simplicidade, assumimos que o score prediz retorno
            avg_score = top_signals["score_final"].mean()
            # Simular retorno baseado no score (simplificação)
            simulated_return = avg_score * 0.001  # Fator arbitrário para demo
            
            portfolio_returns[pd.to_datetime(date)] = simulated_return
    
    # 3. Calcular métricas
    metrics = calculate_backtest_metrics(
        portfolio_returns,
        benchmark_returns,
    )
    
    # 4. Calcular valor da carteira ao longo do tempo
    portfolio_value = initial_capital * (1 + portfolio_returns).cumprod()
    
    result = {
        "name": strategy_name,
        "start_date": start_date,
        "end_date": end_date,
        "initial_capital": initial_capital,
        "final_capital": portfolio_value.iloc[-1] if len(portfolio_value) > 0 else initial_capital,
        **metrics,
        "rebalance_frequency": rebalance_frequency,
        "max_positions": max_positions,
        "transaction_cost": transaction_cost,
    }
    
    logger.info(f"✓ Backtest concluído")
    logger.info(f"  CAGR: {metrics['cagr']:.2%}")
    logger.info(f"  Sharpe: {metrics['sharpe_ratio']:.2f}")
    logger.info(f"  Max DD: {metrics['max_drawdown']:.2%}")
    
    return result


def save_backtest_result(db: Database, result: Dict) -> int:
    """
    Salva resultado de backtest no banco.
    
    Args:
        db: Conexão com banco
        result: Dict com resultados
    
    Returns:
        ID do backtest
    """
    record = {
        "name": result["name"],
        "start_date": result["start_date"],
        "end_date": result["end_date"],
        "initial_capital": result["initial_capital"],
        "final_capital": result["final_capital"],
        "total_return": result["total_return"],
        "cagr": result["cagr"],
        "volatility": result["volatility"],
        "sharpe_ratio": result["sharpe_ratio"],
        "sortino_ratio": result.get("sortino_ratio", 0),
        "max_drawdown": result["max_drawdown"],
        "calmar_ratio": result.get("calmar_ratio", 0),
        "benchmark": "IBOVESPA",
        "benchmark_return": 0.0,  # Calcular se tiver benchmark
        "alpha": result.get("alpha", 0),
        "beta": result.get("beta", 0),
        "total_trades": result.get("n_trades", 0),
        "parameters": str({
            "rebalance_frequency": result.get("rebalance_frequency"),
            "max_positions": result.get("max_positions"),
            "transaction_cost": result.get("transaction_cost"),
        }),
    }
    
    backtest_id = db.insert("backtests", record)
    
    logger.info(f"✓ Backtest salvo: ID {backtest_id}")
    
    return backtest_id
