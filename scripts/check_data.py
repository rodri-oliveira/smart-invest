#!/usr/bin/env python3
"""Verificar dados disponíveis e rodar validação."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from aim.data_layer.database import Database

db = Database()

# Verificar dados
prices = db.fetch_one("SELECT COUNT(*) as n, MIN(date) as start, MAX(date) as end FROM prices")
print(f"Dados de preços: {prices['n']} registros")
print(f"  Período: {prices['start']} a {prices['end']}")

# Verificar ativos
assets = db.fetch_one("SELECT COUNT(DISTINCT ticker) as n FROM prices")
print(f"  Ativos: {assets['n']}")

# Verificar se há dados suficientes para backtest
if prices['n'] >= 1000 and assets['n'] >= 5:
    print("\n✓ Dados suficientes para backtest")
else:
    print("\n✗ Dados insuficientes. Rode: python scripts/seed_demo.py")
