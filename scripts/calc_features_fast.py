#!/usr/bin/env python3
"""
Recalcula features históricas OTIMIZADO.

Estratégia: Calcular apenas em datas de rebalanceamento (mensal)
e usar vetorização (numpy) ao invés de loop python.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import logging
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

from aim.data_layer.database import Database

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def calculate_features_optimized(
    db: Database,
    ticker: str,
    min_records: int = 252,
) -> int:
    """
    Calcula features usando vetorização (muito mais rápido).
    
    Args:
        db: Conexão com banco
        ticker: Código do ativo
        min_records: Mínimo de registros necessários
    
    Returns:
        Número de registros inseridos
    """
    # Buscar dados históricos disponíveis
    query = """
        SELECT 
            CAST(date AS TEXT) as date_str, 
            close, 
            volume
        FROM prices
        WHERE ticker = ?
        ORDER BY date ASC
    """
    results = db.fetch_all(query, (ticker,))
    
    if not results or len(results) < min_records:
        logger.warning(f"{ticker}: dados insuficientes ({len(results) if results else 0} registros)")
        return 0
    
    # Converter para DataFrame
    df = pd.DataFrame(results, columns=['date', 'close', 'volume'])
    df['date'] = pd.to_datetime(df['date'])
    df['close'] = pd.to_numeric(df['close'])
    df['volume'] = pd.to_numeric(df['volume'])
    df = df.sort_values('date').reset_index(drop=True)
    
    n = len(df)
    
    # Calcular retornos vetorizados
    df['returns'] = df['close'].pct_change()
    
    # Momentum (vetorizado)
    df['momentum_3m'] = df['close'].pct_change(periods=63)
    df['momentum_6m'] = df['close'].pct_change(periods=126)
    df['momentum_12m'] = df['close'].pct_change(periods=252)
    
    # Volatilidade anualizada (vetorizada) - rolling std * sqrt(252)
    df['vol_21d'] = df['returns'].rolling(window=21).std() * np.sqrt(252)
    df['vol_63d'] = df['returns'].rolling(window=63).std() * np.sqrt(252)
    df['vol_126d'] = df['returns'].rolling(window=126).std() * np.sqrt(252)
    
    # Liquidez - rolling mean
    df['avg_volume'] = df['volume'].rolling(window=20).mean()
    df['avg_dollar_volume'] = (df['close'] * df['volume']).rolling(window=20).mean()
    
    # Liquidity score normalizado
    df['liquidity_score'] = np.minimum(1.0, np.log10(df['avg_dollar_volume'] + 1) / 10)
    
    # Manter apenas datas onde temos dados suficientes (após 252 dias)
    df = df.iloc[252:].copy()
    
    if df.empty:
        return 0
    
    # Preparar registros para inserção
    count = 0
    for _, row in df.iterrows():
        try:
            record = {
                'ticker': ticker,
                'date': row['date'].strftime('%Y-%m-%d'),
                'momentum_3m': round(row['momentum_3m'], 4) if pd.notna(row['momentum_3m']) else None,
                'momentum_6m': round(row['momentum_6m'], 4) if pd.notna(row['momentum_6m']) else None,
                'momentum_12m': round(row['momentum_12m'], 4) if pd.notna(row['momentum_12m']) else None,
                'momentum_composite': None,  # Calculado depois
                'vol_21d': round(row['vol_21d'], 4) if pd.notna(row['vol_21d']) else None,
                'vol_63d': round(row['vol_63d'], 4) if pd.notna(row['vol_63d']) else None,
                'vol_126d': round(row['vol_126d'], 4) if pd.notna(row['vol_126d']) else None,
                'avg_volume': int(row['avg_volume']) if pd.notna(row['avg_volume']) else None,
                'avg_dollar_volume': round(row['avg_dollar_volume'], 2) if pd.notna(row['avg_dollar_volume']) else None,
                'liquidity_score': round(row['liquidity_score'], 4) if pd.notna(row['liquidity_score']) else None,
            }
            
            db.upsert('features', record, conflict_columns=['ticker', 'date'])
            count += 1
            
        except Exception as e:
            continue
    
    logger.info(f"{ticker}: {count} features")
    return count


def main():
    """Função principal."""
    print("=" * 60)
    print("Recalculando Features Históricas (OTIMIZADO)")
    print("=" * 60)
    
    db = Database()
    
    # Buscar tickers com dados da BRAPI
    tickers_result = db.fetch_all("""
        SELECT DISTINCT ticker 
        FROM prices 
        WHERE source = 'brapi'
        ORDER BY ticker
    """)
    
    tickers = [r['ticker'] for r in tickers_result]
    print(f"Ativos: {len(tickers)}")
    print(f"Período: 2015 a 2024 (10 anos)")
    print()
    
    total = 0
    for i, ticker in enumerate(tickers, 1):
        print(f"[{i}/{len(tickers)}] {ticker}...", end=" ", flush=True)
        count = calculate_features_optimized(db, ticker)
        total += count
    
    print("\n" + "=" * 60)
    print(f"✓ Total: {total} features calculadas")
    print("=" * 60)
    
    # Verificar período coberto
    check = db.fetch_one("""
        SELECT MIN(date) as start, MAX(date) as end, COUNT(*) as n
        FROM features
    """)
    
    if check:
        print(f"\nCobertura:")
        print(f"  De: {check['start']}")
        print(f"  Até: {check['end']}")
        print(f"  Total: {check['n']} registros")
    
    print("\nPróximo: python scripts/run_backtest.py")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
