#!/usr/bin/env python3
"""Retry parcial: atualiza apenas tickers que falharam na ultima execucao."""

import json
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from aim.data_layer.database import Database
from aim.data_layer.providers import MultiSourceProvider

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("logs/retry_failed.log"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)


def main() -> int:
    retry_path = Path("data/retry_tickers.json")
    if not retry_path.exists():
        logger.error("Arquivo data/retry_tickers.json nao encontrado.")
        return 1

    tickers = json.loads(retry_path.read_text(encoding="utf-8"))
    if not tickers:
        logger.info("Nenhum ticker para reprocessar.")
        return 0

    logger.info("Reprocessando %d ticker(s): %s", len(tickers), tickers)

    db = Database()
    provider = MultiSourceProvider()

    from datetime import datetime, timedelta
    end_date = datetime.now().strftime("%Y-%m-%d")
    start_date = (datetime.now() - timedelta(days=5)).strftime("%Y-%m-%d")

    report = provider.fetch_universe(tickers, start_date=start_date, end_date=end_date)

    total_prices = 0
    for result in report.results:
        prices = provider.get_prices_data(result)
        if not prices:
            continue
        for price in prices:
            db.upsert("prices", price, conflict_columns=["ticker", "date"])
        total_prices += len(prices)

    # Atualizar relatorio
    report_path = Path("data/last_update_report.json")
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        json.dumps(report.to_dict(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    provider.close()

    logger.info("Retry concluido: %d precos inseridos, %d OK, %d falhas",
                total_prices, report.ok, report.failed)
    if report.failed_tickers:
        logger.warning("Ainda com falha: %s", report.failed_tickers)

    return 0 if report.failed == 0 else 1


if __name__ == "__main__":
    Path("logs").mkdir(exist_ok=True)
    sys.exit(main())
