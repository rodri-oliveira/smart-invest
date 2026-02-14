#!/usr/bin/env python3
"""
Recalcula features para todo o período histórico.
Necessário para backtest completo.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import logging
from datetime import datetime, timedelta
from typing import List
import pandas as pd
import numpy as np

from aim.data_layer.database import Database

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def calculate_rolling_features(
    db: Database,
    ticker: str,
    lookback_days: int = 252,
) -> int:
    """
    Calcula features históricas para um ativo.
    
    Args:
        db: Conexão com banco
        ticker: Código do ativo
        lookback_days: Janelas para cálculo (3m=63, 6m=126, 12m=252)
    
    Returns:
        Número de registros inseridos
    """
    # Buscar todos os preços históricos
    query = """
        SELECT date(date) as date_str, close, volume
        FROM prices
        WHERE ticker = ?
        ORDER BY date ASC
    """
    results = db.fetch_all(query, (ticker,))
    
    if not results or len(results) < 63:
        logger.warning(f"{ticker}: dados insuficientes ({len(results) if results else 0} registros)")
        return 0
    
    # Converter para DataFrame
    df = pd.DataFrame(results)
    df.columns = ['date', 'close', 'volume']
    df['date'] = pd.to_datetime(df['date'])
    df['close'] = pd.to_numeric(df['close'])
    df['volume'] = pd.to_numeric(df['volume'])
    df = df.sort_values('date')
    
    count = 0
    
    # Calcular para cada data (a partir de quando temos histórico suficiente)
    for i in range(252, len(df)):
        try:
            current_date = df.iloc[i]['date']
            
            # Dados até a data atual
            hist = df.iloc[:i+1]
            
            if len(hist) < 63:
                continue
            
            # Calcular momentum (retornos)
            current_price = hist['close'].iloc[-1]
            
            # 3m (~63 dias)
            if len(hist) >= 63:
                price_3m = hist['close'].iloc[-63]
                mom_3m = (current_price / price_3m) - 1
            else:
                mom_3m = None
            
            # 6m (~126 dias)
            if len(hist) >= 126:
                price_6m = hist['close'].iloc[-126]
                mom_6m = (current_price / price_6m) - 1
            else:
                mom_6m = None
            
            # 12m (~252 dias)
            if len(hist) >= 252:
                price_12m = hist['close'].iloc[-252]
                mom_12m = (current_price / price_12m) - 1
            else:
                mom_12m = None
            
            # Volatilidade (21d, 63d, 126d)
            returns = hist['close'].pct_change().dropna()
            
            vol_21d = returns.tail(21).std() * np.sqrt(252) if len(returns) >= 21 else None
            vol_63d = returns.tail(63).std() * np.sqrt(252) if len(returns) >= 63 else None
            vol_126d = returns.tail(126).std() * np.sqrt(252) if len(returns) >= 126 else None
            
            # Liquidez
            avg_volume = hist['volume'].tail(20).mean() if len(hist) >= 20 else None
            avg_dollar_volume = (hist['close'] * hist['volume']).tail(20).mean() if len(hist) >= 20 else None
            
            # Liquidity score (normalizado 0-1)
            if avg_dollar_volume:
                # Log scale normalization
                liq_score = min(1.0, np.log10(avg_dollar_volume + 1) / 10)
            else:
                liq_score = None
            
            # Inserir no banco
            record = {
                'ticker': ticker,
                'date': current_date.strftime('%Y-%m-%d'),
                'momentum_3m': round(mom_3m, 4) if mom_3m else None,
                'momentum_6m': round(mom_6m, 4) if mom_6m else None,
                'momentum_12m': round(mom_12m, 4) if mom_12m else None,
                'vol_21d': round(vol_21d, 4) if vol_21d else None,
                'vol_63d': round(vol_63d, 4) if vol_63d else None,
                'vol_126d': round(vol_126d, 4) if vol_126d else None,
                'avg_volume': int(avg_volume) if avg_volume else None,
                'avg_dollar_volume': round(avg_dollar_volume, 2) if avg_dollar_volume else None,
                'liquidity_score': round(liq_score, 4) if liq_score else None,
            }
            
            db.upsert(
                'features',
                record,
                conflict_columns=['ticker', 'date']
            )
            count += 1
            
        except Exception as e:
            logger.debug(f"Erro em {ticker} @ {current_date}: {e}")
            continue
    
    logger.info(f"{ticker}: {count} features calculadas")
    return count


def main():
    """Função principal."""
    print("=" * 60)
    print("Recalculando Features Históricas")
    print("=" * 60)
    
    db = Database()
    
    # Buscar tickers com dados históricos
    tickers_result = db.fetch_all("""
        SELECT DISTINCT ticker 
        FROM prices 
        WHERE source = 'brapi'
        ORDER BY ticker
    """)
    
    tickers = [r['ticker'] for r in tickers_result]
    
    print(f"Ativos para processar: {len(tickers)}")
    print()
    
    total = 0
    for i, ticker in enumerate(tickers, 1):
        print(f"[{i}/{len(tickers)}] {ticker}...", end=" ")
        count = calculate_rolling_features(db, ticker)
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
        print(f"\nPeríodo coberto:")
        print(f"  De: {check['start']}")
        print(f"  Até: {check['end']}")
        print(f"  Total: {check['n']} registros")
    
    print("\nAgora você pode rodar:")
    print("  python scripts/run_backtest.py")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
