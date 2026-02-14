#!/usr/bin/env python3
"""Verificar dados do IBOVESPA."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from aim.data_layer.database import Database

db = Database()

print("IBOVESPA PRICES:")
prices = db.fetch_all("SELECT * FROM prices WHERE ticker = 'IBOVESPA' ORDER BY date DESC LIMIT 5")
print(f"  Total: {len(prices)} registros")
for row in prices:
    print(f"    {row['date']}: {row['close']}")

print("\nIBOVESPA FEATURES:")
features = db.fetch_all("SELECT * FROM features WHERE ticker = 'IBOVESPA' ORDER BY date DESC LIMIT 5")
print(f"  Total: {len(features)} registros")
for row in features:
    vol = row.get('vol_21d', 'N/A')
    mom = row.get('momentum_21d', 'N/A')
    print(f"    {row['date']}: vol_21d={vol}, mom_21d={mom}")
