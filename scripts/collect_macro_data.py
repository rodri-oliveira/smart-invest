#!/usr/bin/env python3
"""Coletar dados macroeconômicos do BCB (Selic, IPCA, CDI)."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from aim.data_layer.database import Database
from aim.data_layer.providers.bcb import BCBProvider
from datetime import datetime, timedelta
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def collect_macro_data():
    """Coleta dados macro do BCB e insere no banco."""
    db = Database()
    bcb = BCBProvider()
    
    logger.info("=" * 60)
    logger.info("COLETA DE DADOS MACROECONÔMICOS - BCB")
    logger.info("=" * 60)
    
    # Definir período (últimos 10 anos)
    end_date = datetime.now()
    start_date = end_date - timedelta(days=365 * 10)
    
    start_str = start_date.strftime("%d/%m/%Y")
    end_str = end_date.strftime("%d/%m/%Y")
    
    # Séries a coletar
    series_to_collect = [
        ("SELIC_META", 432, "SELIC", "% a.a."),
        ("CDI", 12, "CDI", "% a.a."),
        ("IPCA", 433, "IPCA", "% a.m."),
        ("IGPM", 189, "IGPM", "% a.m."),
        ("USD_PTAX", 1, "USD", "BRL/USD"),
        ("PIB_MENSAL", 4380, "IBC-Br", "Índice"),
    ]
    
    total_inserted = 0
    
    for series_name, series_code, indicator, unit in series_to_collect:
        try:
            logger.info(f"\nColetando {series_name} (código {series_code})...")
            
            data = bcb.get_series(series_code, start_str, end_str)
            
            if not data:
                logger.warning(f"  Sem dados para {series_name}")
                continue
            
            inserted = 0
            for item in data:
                record = {
                    "date": item["date"],
                    "indicator": indicator,
                    "value": item["value"],
                    "unit": unit,
                    "frequency": "MENSAL" if "IPCA" in series_name or "IGPM" in series_name else "DAILY",
                    "source": "BCB",
                    "notes": f"Série {series_code}",
                }
                
                db.upsert(
                    "macro_indicators",
                    record,
                    conflict_columns=["date", "indicator"],
                )
                inserted += 1
            
            total_inserted += inserted
            logger.info(f"  ✓ {inserted} registros inseridos")
            
        except Exception as e:
            logger.error(f"  ✗ Erro em {series_name}: {e}")
            continue
    
    logger.info(f"\n{'=' * 60}")
    logger.info(f"Total: {total_inserted} registros macro inseridos")
    logger.info(f"{'=' * 60}")
    
    # Mostrar amostra
    sample = db.fetch_all(
        "SELECT indicator, COUNT(*) as n, MIN(date) as start, MAX(date) as end FROM macro_indicators GROUP BY indicator ORDER BY n DESC"
    )
    
    logger.info("\nDados coletados:")
    for row in sample:
        logger.info(f"  {row['indicator']}: {row['n']} registros ({row['start']} a {row['end']})")


if __name__ == "__main__":
    collect_macro_data()
