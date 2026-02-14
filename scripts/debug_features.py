#!/usr/bin/env python3
"""Debug do cálculo de features."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from aim.data_layer.database import Database
import pandas as pd
import numpy as np

db = Database()

# Testar com um ticker específico
ticker = 'PETR4'
start_date = '2015-01-01'

print(f"Testando query para {ticker}...")
print(f"Data inicial: {start_date}")

# Query simplificada
query = """
    SELECT date, close, volume
    FROM prices
    WHERE ticker = ?
    AND date >= ?
    ORDER BY date ASC
    LIMIT 5
"""

results = db.fetch_all(query, (ticker, start_date))
print(f"\nResultados encontrados: {len(results)}")

if results:
    for r in results[:3]:
        print(f"  {r['date']}: close={r['close']}, volume={r['volume']}")
else:
    # Verificar se há dados sem filtro de data
    print("\nVerificando sem filtro de data...")
    all_data = db.fetch_all("SELECT date, close FROM prices WHERE ticker = ? ORDER BY date DESC LIMIT 3", (ticker,))
    for r in all_data:
        print(f"  {r['date']}: {r['close']}")
    
    # Verificar formato da data
    print("\nVerificando formato das datas...")
    sample = db.fetch_one("SELECT date, typeof(date) as tipo FROM prices WHERE ticker = ? LIMIT 1", (ticker,))
    print(f"  Valor: {sample['date']}, Tipo: {sample['tipo']}")
