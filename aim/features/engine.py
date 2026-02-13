"""Engine de cálculo de features para todos os ativos."""

import logging
from typing import Dict, List, Optional

import pandas as pd

from aim.data_layer.database import Database
from aim.features.liquidity import calculate_liquidity_metrics
from aim.features.momentum import calculate_composite_momentum
from aim.features.volatility import calculate_volatility_multiple_windows

logger = logging.getLogger(__name__)


def load_prices_for_ticker(
    db: Database,
    ticker: str,
    days: int = 400,  # ~1.5 anos para cobrir 252 dias úteis + margem
) -> Optional[pd.DataFrame]:
    """
    Carrega preços históricos de um ativo.

    Args:
        db: Conexão com banco
        ticker: Código do ativo
        days: Quantos dias de histórico

    Returns:
        DataFrame com colunas [date, open, high, low, close, volume]
    """
    query = """
        SELECT date, open, high, low, close, volume
        FROM prices
        WHERE ticker = ?
        AND date >= date('now', '-{} days')
        ORDER BY date ASC
    """.format(days)

    df = db.query_to_df(query, (ticker,))

    if df.empty:
        return None

    df["date"] = pd.to_datetime(df["date"])
    return df


def calculate_features_for_ticker(
    db: Database,
    ticker: str,
) -> Optional[Dict[str, any]]:
    """
    Calcula todas as features para um ativo.

    Args:
        db: Conexão com banco
        ticker: Código do ativo

    Returns:
        Dict com todas as features calculadas
    """
    # Carregar dados
    df = load_prices_for_ticker(db, ticker)

    if df is None or len(df) < 63:  # Mínimo 3 meses
        logger.warning(f"Dados insuficientes para {ticker}")
        return None

    prices = df["close"].reset_index(drop=True)
    volume = df["volume"].reset_index(drop=True)

    # Calcular momentum
    momentum = calculate_composite_momentum(prices)

    # Calcular volatilidade
    volatility = calculate_volatility_multiple_windows(prices)

    # Calcular liquidez
    liquidity = calculate_liquidity_metrics(prices, volume)

    # Consolidar
    features = {
        "ticker": ticker,
        "date": df["date"].iloc[-1].strftime("%Y-%m-%d"),
        # Momentum
        "momentum_3m": momentum["momentum_3m"],
        "momentum_6m": momentum["momentum_6m"],
        "momentum_12m": momentum["momentum_12m"],
        # Volatilidade
        "vol_21d": volatility["vol_21d"],
        "vol_63d": volatility["vol_63d"],
        "vol_126d": volatility["vol_126d"],
        # Liquidez
        "avg_volume": liquidity["avg_volume"],
        "avg_dollar_volume": liquidity["avg_dollar_volume"],
        "liquidity_score": liquidity["liquidity_score"],
    }

    return features


def calculate_all_features(
    db: Database,
    tickers: Optional[List[str]] = None,
) -> Dict[str, int]:
    """
    Calcula features para todos os ativos do universo.

    Args:
        db: Conexão com banco
        tickers: Lista de ativos. Se None, usa todos do universo.

    Returns:
        Estatísticas do processamento
    """
    if tickers is None:
        # Carregar universo do banco
        result = db.fetch_all("SELECT ticker FROM assets WHERE is_active = 1")
        tickers = [r["ticker"] for r in result]

    logger.info(f"Calculando features para {len(tickers)} ativos...")

    processed = 0
    errors = 0
    features_list = []

    for i, ticker in enumerate(tickers, 1):
        try:
            features = calculate_features_for_ticker(db, ticker)

            if features:
                features_list.append(features)
                processed += 1

                if i % 10 == 0:
                    logger.info(f"  Progresso: {i}/{len(tickers)}")

        except Exception as e:
            logger.error(f"Erro ao calcular features de {ticker}: {e}")
            errors += 1

    # Inserir no banco (upsert)
    if features_list:
        _insert_features_batch(db, features_list)
        logger.info(f"✓ {len(features_list)} conjuntos de features inseridos")

    return {
        "processed": processed,
        "errors": errors,
        "total": len(tickers),
    }


def _insert_features_batch(db: Database, features_list: List[Dict]) -> None:
    """Insere features em batch no banco."""
    # Preparar dados para upsert
    for features in features_list:
        # O features já está no formato correto
        db.upsert(
            "features",  # Tabela a ser criada
            features,
            conflict_columns=["ticker", "date"],
        )


def get_latest_features(
    db: Database,
    ticker: str,
) -> Optional[Dict]:
    """
    Retorna features mais recentes de um ativo.

    Args:
        db: Conexão com banco
        ticker: Código do ativo

    Returns:
        Dict com features ou None
    """
    query = """
        SELECT *
        FROM features
        WHERE ticker = ?
        ORDER BY date DESC
        LIMIT 1
    """

    result = db.fetch_one(query, (ticker,))
    return result


def get_features_for_date(
    db: Database,
    date: str,
) -> pd.DataFrame:
    """
    Retorna features de todos os ativos em uma data.

    Args:
        db: Conexão com banco
        date: Data no formato YYYY-MM-DD

    Returns:
        DataFrame com features de todos os ativos
    """
    query = """
        SELECT *
        FROM features
        WHERE date = ?
    """

    return db.query_to_df(query, (date,))
