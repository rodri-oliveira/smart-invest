#!/usr/bin/env python3
"""Verificar formato das datas no banco."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from aim.data_layer.database import Database
from datetime import datetime

db = Database()

# Verificar uma amostra de dados
print("Amostra de dados PETR4:")
results = db.fetch_all("SELECT ticker, date, datetime(date, 'unixepoch') as data_formatada, close FROM prices WHERE ticker = 'PETR4' ORDER BY date DESC LIMIT 5")
for r in results:
    print(f"  {r['ticker']}: timestamp={r['date']} -> {r['data_formatada']} = R$ {r['close']}")

# Verificar se há dados a partir de 2015
start_2015 = int(datetime(2015, 1, 1).timestamp())
count = db.fetch_one("SELECT COUNT(*) as n FROM prices WHERE ticker = 'PETR4' AND date >= ?", (start_2015,))
print(f"\nDados PETR4 desde 2015: {count['n']} registros")

# Verificar range de datas para todos os ativos
print("\nRange de datas por ativo (BRAPI):")
ranges = db.fetch_all("SELECT ticker, MIN(date) as min_ts, MAX(date) as max_ts, COUNT(*) as n FROM prices WHERE source = 'brapi' GROUP BY ticker ORDER BY n DESC LIMIT 10")
for r in ranges:
    min_date = datetime.fromtimestamp(r['min_ts']).strftime('%Y-%m-%d')
    max_date = datetime.fromtimestamp(r['max_ts']).strftime('%Y-%m-%d')
    print(f"  {r['ticker']}: {min_date} a {max_date} ({r['n']} registros)")
