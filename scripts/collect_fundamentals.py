#!/usr/bin/env python3
"""Coletar dados fundamentalistas da BRAPI para todos os ativos."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from aim.data_layer.database import Database
from aim.data_layer.providers.brapi import BrapiProvider
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def collect_fundamentals():
    """Coleta fundamentos para todos os ativos do universo."""
    db = Database()
    provider = BrapiProvider()

    # Buscar todos os ativos ativos
    assets = db.fetch_all("SELECT ticker FROM assets WHERE is_active = TRUE")
    tickers = [a["ticker"] for a in assets]

    logger.info(f"Coletando fundamentos para {len(tickers)} ativos...")

    total = 0
    errors = 0

    for i, ticker in enumerate(tickers, 1):
        try:
            logger.info(f"[{i}/{len(tickers)}] {ticker}...")

            # Buscar dados fundamentalistas
            fundamentals = provider.get_fundamentals(ticker)

            if not fundamentals:
                logger.warning(f"  Sem dados para {ticker}")
                continue

            # Adicionar campos necessários para o schema
            from datetime import datetime
            fundamentals["reference_date"] = datetime.now().strftime("%Y-%m-%d")
            fundamentals["report_type"] = "SNAPSHOT"  # Dados em tempo real da API

            # Inserir/atualizar no banco
            db.upsert(
                "fundamentals",
                fundamentals,
                conflict_columns=["ticker", "reference_date", "report_type"],
            )

            total += 1
            logger.info(f"  ✓ P/L: {fundamentals.get('p_l')}, ROE: {fundamentals.get('roe')}")

        except Exception as e:
            logger.error(f"  ✗ Erro em {ticker}: {e}")
            errors += 1

    logger.info(f"\n{'='*50}")
    logger.info(f"Fundamentos coletados: {total}/{len(tickers)}")
    logger.info(f"Erros: {errors}")
    logger.info(f"{'='*50}")

    # Mostrar amostra
    sample = db.fetch_all(
        "SELECT ticker, p_l, roe, ebitda, dy FROM fundamentals WHERE p_l IS NOT NULL ORDER BY reference_date DESC LIMIT 5"
    )
    logger.info("\nAmostra dos dados:")
    for row in sample:
        logger.info(f"  {row['ticker']}: P/L={row['p_l']}, ROE={row['roe']}, DY={row['dy']}")


if __name__ == "__main__":
    collect_fundamentals()
