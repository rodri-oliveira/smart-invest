#!/usr/bin/env python3
"""Verificar cálculos de features."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from aim.data_layer.database import Database

db = Database()

# Verificar features calculadas
query = """
    SELECT ticker, momentum_3m, momentum_6m, momentum_12m, 
           vol_21d, vol_63d, liquidity_score
    FROM features 
    ORDER BY date DESC 
    LIMIT 5
"""
results = db.fetch_all(query)

print("Features Calculadas (últimos 5 ativos):")
print("=" * 70)
print(f"{'Ticker':<8} | {'Mom 3m':>10} | {'Mom 6m':>10} | {'Mom 12m':>10} | {'Vol 63d':>10} | {'Liq Score':>10}")
print("-" * 70)

for r in results:
    mom3 = f"{r['momentum_3m'] or 0:+.2%}" if r['momentum_3m'] else "N/A"
    mom6 = f"{r['momentum_6m'] or 0:+.2%}" if r['momentum_6m'] else "N/A"
    mom12 = f"{r['momentum_12m'] or 0:+.2%}" if r['momentum_12m'] else "N/A"
    vol = f"{r['vol_63d'] or 0:.2%}" if r['vol_63d'] else "N/A"
    liq = f"{r['liquidity_score'] or 0:.4f}" if r['liquidity_score'] else "N/A"
    
    print(f"{r['ticker']:<8} | {mom3:>10} | {mom6:>10} | {mom12:>10} | {vol:>10} | {liq:>10}")

print("\n" + "=" * 70)
print("Validacao:")
print("  - Momentum positivo = ativo subiu no periodo")
print("  - Volatilidade ~15-30% ao ano = normal para acoes BR")
print("  - Liquidity score 0-1 = normalizado")
