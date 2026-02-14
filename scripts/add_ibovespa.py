#!/usr/bin/env python3
"""Buscar e adicionar IBOVESPA ao banco de dados."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from aim.data_layer.database import Database
from aim.data_layer.providers.brapi import BrapiProvider
from datetime import datetime, timedelta
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def add_ibovespa():
    """Adiciona IBOVESPA como ativo e busca preços históricos."""
    db = Database()
    provider = BrapiProvider()
    
    logger.info("=" * 60)
    logger.info("ADICIONANDO IBOVESPA AO BANCO")
    logger.info("=" * 60)
    
    # 1. Adicionar IBOVESPA à tabela assets
    logger.info("\n1. Adicionando IBOVESPA como ativo...")
    
    asset_data = {
        "ticker": "IBOVESPA",
        "name": "Indice Bovespa",
        "sector": "INDICE",
        "segment": "Indice de Acoes",
        "market_cap_category": "LARGE",
        "is_active": True,
        "is_index": True,
        "created_at": datetime.now().isoformat(),
    }
    
    try:
        db.upsert(
            "assets",
            asset_data,
            conflict_columns=["ticker"],
        )
        logger.info("  IBOVESPA adicionado como ativo")
    except Exception as e:
        logger.error(f"  Erro ao adicionar ativo: {e}")
    
    # 2. Buscar preços históricos
    logger.info("\n2. Buscando preços históricos...")
    
    try:
        prices = provider.get_prices("IBOVESPA")
        
        if not prices:
            logger.warning("  Sem dados de preço para IBOVESPA")
            return
        
        logger.info(f"  {len(prices)} dias de preços encontrados")
        
        # Inserir preços
        inserted = 0
        for price in prices:
            try:
                record = {
                    "ticker": "IBOVESPA",
                    "date": price["date"],
                    "open": price.get("open"),
                    "high": price.get("high"),
                    "low": price.get("low"),
                    "close": price.get("close"),
                    "volume": price.get("volume"),
                    "adjusted_close": price.get("close"),
                }
                
                db.upsert(
                    "prices",
                    record,
                    conflict_columns=["ticker", "date"],
                )
                inserted += 1
                
            except Exception as e:
                logger.debug(f"  Erro ao inserir preço {price.get('date')}: {e}")
                continue
        
        logger.info(f"  {inserted} preços inseridos")
        
    except Exception as e:
        logger.error(f"  Erro ao buscar preços: {e}")
    
    # 3. Verificar resultado
    logger.info("\n3. Verificando resultado...")
    
    result = db.fetch_one(
        "SELECT COUNT(*) as n, MIN(date) as start, MAX(date) as end FROM prices WHERE ticker = 'IBOVESPA'"
    )
    
    if result and result["n"] > 0:
        logger.info(f"  IBOVESPA: {result['n']} preços ({result['start']} a {result['end']})")
        logger.info("  IBOVESPA pronto para uso!")
    else:
        logger.warning("  IBOVESPA não foi adicionado corretamente")


if __name__ == "__main__":
    add_ibovespa()
