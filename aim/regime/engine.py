"""Engine principal de classificação de regime de mercado."""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

import pandas as pd

from aim.config.parameters import REGIME_VARIABLE_WEIGHTS
from aim.data_layer.database import Database
from aim.regime.calculator import (
    calculate_capital_flow_score,
    calculate_ibov_trend_score,
    calculate_liquidity_sentiment_score,
    calculate_risk_spread_score,
    calculate_yield_curve_score,
    classify_regime_from_scores,
)

logger = logging.getLogger(__name__)


def load_macro_data(
    db: Database,
    days: int = 252,
) -> Dict[str, pd.DataFrame]:
    """
    Carrega dados macroeconômicos do banco.
    
    Args:
        db: Conexão com banco
        days: Quantos dias de histórico
    
    Returns:
        Dict com DataFrames de cada indicador
    """
    start_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    
    data = {}
    
    # SELIC
    query = """
        SELECT date, value
        FROM macro_indicators
        WHERE indicator = 'SELIC'
        AND date >= ?
        ORDER BY date ASC
    """
    data["selic"] = db.query_to_df(query, (start_date,))
    if not data["selic"].empty:
        data["selic"]["date"] = pd.to_datetime(data["selic"]["date"])
    
    # USD
    query = """
        SELECT date, value
        FROM macro_indicators
        WHERE indicator = 'USD_BRL'
        AND date >= ?
        ORDER BY date ASC
    """
    data["usd"] = db.query_to_df(query, (start_date,))
    if not data["usd"].empty:
        data["usd"]["date"] = pd.to_datetime(data["usd"]["date"])
    
    # Ibovespa (como proxy de mercado)
    query = """
        SELECT date, close as value, volume
        FROM prices
        WHERE ticker = 'IBOVESPA'
        AND date >= ?
        ORDER BY date ASC
    """
    data["ibov"] = db.query_to_df(query, (start_date,))
    if not data["ibov"].empty:
        data["ibov"]["date"] = pd.to_datetime(data["ibov"]["date"])
    
    return data


def calculate_regime_for_date(
    db: Database,
    date: Optional[str] = None,
) -> Dict:
    """
    Calcula classificação de regime para uma data específica.
    
    Args:
        db: Conexão com banco
        date: Data no formato YYYY-MM-DD. Se None, usa data mais recente.
    
    Returns:
        Dict com regime, scores e detalhes
    """
    if date is None:
        date = datetime.now().strftime("%Y-%m-%d")
    
    logger.info(f"Calculando regime para {date}...")
    
    # Carregar dados macro
    macro_data = load_macro_data(db)
    
    scores = {}
    raw_values = {}
    
    # 1. Yield Curve Score (SELIC)
    if not macro_data["selic"].empty:
        score, value = calculate_yield_curve_score(macro_data["selic"])
        scores["yield_curve"] = score
        raw_values["yield_curve"] = value
        logger.info(f"  Yield Curve: {score:.2f} (value: {value})")
    else:
        scores["yield_curve"] = 0.0
        raw_values["yield_curve"] = None
    
    # 2. Risk Spread Score (USD)
    if not macro_data["usd"].empty:
        score, value = calculate_risk_spread_score(macro_data["usd"])
        scores["risk_spread"] = score
        raw_values["risk_spread"] = value
        logger.info(f"  Risk Spread: {score:.2f} (value: {value})")
    else:
        scores["risk_spread"] = 0.0
        raw_values["risk_spread"] = None
    
    # 3. Ibovespa Trend Score
    if not macro_data["ibov"].empty:
        ibov_prices = macro_data["ibov"]["value"]
        score, details = calculate_ibov_trend_score(ibov_prices)
        scores["ibov_trend"] = score
        raw_values["ibov_trend"] = details
        logger.info(f"  Ibov Trend: {score:.2f}")
    else:
        scores["ibov_trend"] = 0.0
        raw_values["ibov_trend"] = None
    
    # 4. Capital Flow Score (correlação USD x IBOV)
    if not macro_data["usd"].empty and not macro_data["ibov"].empty:
        # Preparar dados do Ibov no mesmo formato
        ibov_df = macro_data["ibov"][["date", "value"]].copy()
        score, value = calculate_capital_flow_score(macro_data["usd"], ibov_df)
        scores["capital_flow"] = score
        raw_values["capital_flow"] = value
        logger.info(f"  Capital Flow: {score:.2f} (corr: {value})")
    else:
        scores["capital_flow"] = 0.0
        raw_values["capital_flow"] = None
    
    # 5. Liquidity/Sentiment Score
    if not macro_data["ibov"].empty and len(macro_data["ibov"]) > 21:
        volume = macro_data["ibov"]["volume"]
        # Calcular volatilidade móvel
        prices = macro_data["ibov"]["value"]
        returns = prices.pct_change()
        volatility = returns.rolling(window=21).std() * (252 ** 0.5)  # Anualizada
        
        score, details = calculate_liquidity_sentiment_score(volume, volatility)
        scores["liquidity_sentiment"] = score
        raw_values["liquidity_sentiment"] = details
        logger.info(f"  Liquidity/Sentiment: {score:.2f}")
    else:
        scores["liquidity_sentiment"] = 0.0
        raw_values["liquidity_sentiment"] = None
    
    # Classificar regime
    regime, score_total, details = classify_regime_from_scores(scores)
    
    logger.info(f"  Regime: {regime} (score: {score_total:.2f})")
    
    return {
        "date": date,
        "regime": regime,
        "score_total": score_total,
        "scores": scores,
        "raw_values": raw_values,
        "details": details,
    }


def save_regime_state(db: Database, regime_data: Dict) -> None:
    """
    Salva estado de regime no banco.
    
    Args:
        db: Conexão com banco
        regime_data: Dados do regime calculado
    """
    scores = regime_data["scores"]
    raw = regime_data["raw_values"]
    
    record = {
        "date": regime_data["date"],
        "regime": regime_data["regime"],
        "score_total": regime_data["score_total"],
        # Scores individuais
        "score_yield_curve": scores.get("yield_curve"),
        "score_risk_spread": scores.get("risk_spread"),
        "score_ibov_trend": scores.get("ibov_trend"),
        "score_capital_flow": scores.get("capital_flow"),
        "score_liquidity": scores.get("liquidity_sentiment"),
        # Valores brutos
        "yield_curve_value": raw.get("yield_curve"),
        "risk_spread_value": raw.get("risk_spread"),
        "ibov_trend_value": raw.get("ibov_trend", {}).get("current_price") if isinstance(raw.get("ibov_trend"), dict) else raw.get("ibov_trend"),
        "capital_flow_value": raw.get("capital_flow"),
        "liquidity_value": raw.get("liquidity_sentiment", {}).get("volume_ratio") if isinstance(raw.get("liquidity_sentiment"), dict) else None,
    }
    
    db.upsert(
        "regime_state",
        record,
        conflict_columns=["date"],
    )
    
    logger.info(f"✓ Regime salvo: {regime_data['regime']} @ {regime_data['date']}")


def get_current_regime(db: Database) -> Optional[Dict]:
    """
    Retorna regime mais recente do banco.
    
    Args:
        db: Conexão com banco
    
    Returns:
        Dict com dados do regime ou None
    """
    query = """
        SELECT *
        FROM regime_state
        ORDER BY date DESC
        LIMIT 1
    """
    
    result = db.fetch_one(query)
    return result


def get_regime_history(
    db: Database,
    days: int = 90,
) -> pd.DataFrame:
    """
    Retorna histórico de regimes.
    
    Args:
        db: Conexão com banco
        days: Quantos dias de histórico
    
    Returns:
        DataFrame com histórico de regimes
    """
    start_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    
    query = """
        SELECT *
        FROM regime_state
        WHERE date >= ?
        ORDER BY date ASC
    """
    
    return db.query_to_df(query, (start_date,))


def update_daily_regime(db: Database) -> Dict:
    """
    Pipeline diário de atualização de regime.
    
    Args:
        db: Conexão com banco
    
    Returns:
        Dados do regime calculado
    """
    logger.info("Atualizando classificação de regime...")
    
    # Calcular regime atual
    regime_data = calculate_regime_for_date(db)
    
    # Salvar no banco
    save_regime_state(db, regime_data)
    
    return regime_data
