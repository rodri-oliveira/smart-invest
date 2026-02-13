#!/usr/bin/env python3
"""
Coleta dados históricos reais via yfinance.
Permite backtest em 5-10 anos de dados reais.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import logging
from datetime import datetime, timedelta
from typing import List, Dict

import yfinance as yf
import pandas as pd
import time

from aim.data_layer.database import Database

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def fetch_historical_data(
    ticker: str,
    period: str = "10y",
    interval: str = "1d",
    max_retries: int = 3,
) -> pd.DataFrame:
    """
    Busca dados históricos via yfinance com retry.
    
    Args:
        ticker: Código do ativo (ex: PETR4)
        period: Período (1y, 5y, 10y, max)
        interval: Intervalo (1d, 1wk, 1mo)
        max_retries: Número de tentativas
    
    Returns:
        DataFrame com OHLCV
    """
    # Tentar com e sem .SA
    suffixes = [".SA", ""]
    
    for suffix in suffixes:
        yf_ticker = f"{ticker}{suffix}"
        
        for attempt in range(max_retries):
            try:
                # Delay para não sobrecarregar API
                time.sleep(0.5)
                
                stock = yf.Ticker(yf_ticker)
                df = stock.history(period=period, interval=interval)
                
                if not df.empty:
                    # Resetar índice para ter date como coluna
                    df = df.reset_index()
                    
                    # Renomear colunas
                    df = df.rename(columns={
                        'Date': 'date',
                        'Open': 'open',
                        'High': 'high',
                        'Low': 'low',
                        'Close': 'close',
                        'Volume': 'volume',
                    })
                    
                    # Adicionar ticker original (sem sufixo)
                    df['ticker'] = ticker
                    df['adjusted_close'] = df['close']
                    df['source'] = 'yfinance'
                    
                    return df[['ticker', 'date', 'open', 'high', 'low', 'close', 'volume', 'adjusted_close', 'source']]
                
            except Exception as e:
                if attempt < max_retries - 1:
                    time.sleep(1)  # Esperar antes de retry
                else:
                    logger.debug(f"Erro em {yf_ticker}: {e}")
    
    logger.warning(f"Sem dados para {ticker} após {max_retries} tentativas")
    return pd.DataFrame()


def insert_historical_prices(db: Database, df: pd.DataFrame) -> int:
    """Insere dados históricos no banco."""
    if df.empty:
        return 0
    
    count = 0
    for _, row in df.iterrows():
        try:
            # Converter Timestamp para string
            date_str = row['date'].strftime('%Y-%m-%d') if hasattr(row['date'], 'strftime') else str(row['date'])[:10]
            
            record = {
                'ticker': row['ticker'],
                'date': date_str,
                'open': round(float(row['open']), 4),
                'high': round(float(row['high']), 4),
                'low': round(float(row['low']), 4),
                'close': round(float(row['close']), 4),
                'volume': int(row['volume']),
                'adjusted_close': round(float(row['adjusted_close']), 4),
                'source': row['source'],
            }
            
            db.upsert(
                'prices',
                record,
                conflict_columns=['ticker', 'date']
            )
            count += 1
            
        except Exception as e:
            logger.error(f"Erro ao inserir registro: {e}")
    
    return count


def main():
    """Função principal."""
    print("=" * 60)
    print("Coleta de Dados Históricos (5-10 anos)")
    print("=" * 60)
    
    db = Database()
    
    # Lista de ativos para coletar
    tickers = [
        # Ibovespa (benchmark)
        "^BVSP",
        # Top 20 ações mais líquidas
        "PETR4", "VALE3", "ITUB4", "BBDC4", "BBAS3",
        "MGLU3", "WEGE3", "ABEV3", "JBSS3", "RENT3",
        "B3SA3", "SUZB3", "PRIO3", "BBSE3", "ITSA4",
        "GGBR4", "ELET3", "RAIL3", "VBBR3", "SBSP3",
    ]
    
    total_records = 0
    
    for i, ticker in enumerate(tickers, 1):
        print(f"\n[{i}/{len(tickers)}] Coletando {ticker}...")
        
        df = fetch_historical_data(ticker, period="10y")
        
        if not df.empty:
            count = insert_historical_prices(db, df)
            total_records += count
            print(f"  ✓ {count} registros inseridos ({df['date'].min()[:10]} a {df['date'].max()[:10]})")
        else:
            print(f"  ✗ Sem dados")
    
    print("\n" + "=" * 60)
    print(f"✓ Total: {total_records} registros inseridos")
    print("=" * 60)
    
    # Verificar período coberto
    coverage = db.fetch_one("""
        SELECT 
            MIN(date) as start_date,
            MAX(date) as end_date,
            COUNT(DISTINCT ticker) as n_tickers,
            COUNT(*) as total_records
        FROM prices
        WHERE source = 'yfinance'
    """)
    
    if coverage:
        print(f"\nCobertura:")
        print(f"  De: {coverage['start_date']}")
        print(f"  Até: {coverage['end_date']}")
        print(f"  Ativos: {coverage['n_tickers']}")
        print(f"  Registros: {coverage['total_records']}")
    
    print("\nAgora você pode:")
    print("  1. Rodar backtest: python scripts/run_backtest.py")
    print("  2. Recalcular features: python scripts/daily_update.py --offline")


if __name__ == "__main__":
    main()
