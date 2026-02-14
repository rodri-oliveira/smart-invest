#!/usr/bin/env python3
"""
Busca dados históricos completos (10 anos) da BRAPI.
A API tem limite de dados por requisição, então buscamos ano a ano.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import logging
from datetime import datetime, timedelta
from typing import List, Dict
import time

from aim.data_layer.database import Database
from aim.data_layer.providers import BrapiProvider

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def fetch_historical_by_year(
    provider: BrapiProvider,
    ticker: str,
    start_year: int = 2015,
    end_year: int = 2025,
) -> List[Dict]:
    """
    Busca dados históricos ano a ano para contornar limites da API.
    
    Args:
        provider: Instância do BrapiProvider
        ticker: Código do ativo
        start_year: Ano inicial
        end_year: Ano final
    
    Returns:
        Lista de candles OHLCV
    """
    all_data = []
    
    for year in range(start_year, end_year + 1):
        try:
            # Buscar 1 ano de dados
            start_date = f"{year}-01-01"
            end_date = f"{year}-12-31"
            
            logger.debug(f"Buscando {ticker} para {year}...")
            
            data = provider.get_prices(
                ticker,
                start_date=start_date,
                end_date=end_date
            )
            
            if data:
                all_data.extend(data)
                logger.info(f"  {ticker} {year}: {len(data)} registros")
            else:
                logger.warning(f"  {ticker} {year}: sem dados")
            
            # Delay para não sobrecarregar API (respeitar rate limit)
            time.sleep(0.5)
            
        except Exception as e:
            logger.warning(f"  {ticker} {year}: erro - {e}")
            continue
    
    return all_data


def insert_prices_batch(db: Database, prices: List[Dict]) -> int:
    """Insere preços em batch."""
    count = 0
    
    for price in prices:
        try:
            db.upsert(
                "prices",
                price,
                conflict_columns=["ticker", "date"]
            )
            count += 1
        except Exception as e:
            logger.debug(f"Erro ao inserir: {e}")
            continue
    
    return count


def main():
    """Função principal."""
    print("=" * 60)
    print("Coleta de Dados Históricos (2015-2025)")
    print("=" * 60)
    
    db = Database()
    provider = BrapiProvider()
    
    # Lista de ativos prioritários (top 20 mais líquidos)
    tickers = [
        "PETR4", "VALE3", "ITUB4", "BBDC4", "BBAS3",
        "MGLU3", "WEGE3", "ABEV3", "JBSS3", "RENT3",
        "B3SA3", "SUZB3", "PRIO3", "BBSE3", "ITSA4",
        "GGBR4", "ELET3", "RAIL3", "VBBR3", "SBSP3",
    ]
    
    total_records = 0
    
    for i, ticker in enumerate(tickers, 1):
        print(f"\n[{i}/{len(tickers)}] {ticker}")
        
        # Buscar dados históricos ano a ano
        data = fetch_historical_by_year(
            provider,
            ticker,
            start_year=2015,
            end_year=2025
        )
        
        if data:
            # Inserir no banco
            count = insert_prices_batch(db, data)
            total_records += count
            print(f"  ✓ Total: {count} registros")
        else:
            print(f"  ✗ Sem dados históricos")
    
    provider.close()
    
    print("\n" + "=" * 60)
    print(f"✓ Total geral: {total_records} registros")
    print("=" * 60)
    
    # Verificar período coberto
    coverage = db.fetch_one("""
        SELECT 
            MIN(date) as start_date,
            MAX(date) as end_date,
            COUNT(DISTINCT ticker) as n_tickers,
            COUNT(*) as total_records
        FROM prices
        WHERE source = 'brapi'
    """)
    
    if coverage:
        print(f"\nCobertura:")
        print(f"  De: {coverage['start_date']}")
        print(f"  Até: {coverage['end_date']}")
        print(f"  Ativos: {coverage['n_tickers']}")
        print(f"  Registros: {coverage['total_records']}")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
