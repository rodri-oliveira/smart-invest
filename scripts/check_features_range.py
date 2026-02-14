#!/usr/bin/env python3
"""Verificar features calculadas."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from aim.data_layer.database import Database

db = Database()

# Verificar features
features = db.fetch_one("SELECT COUNT(*) as n, MIN(date) as start, MAX(date) as end FROM features")
print(f"Features: {features['n']} registros")
print(f"  Período: {features['start']} a {features['end']}")

# Verificar se cobre dados históricos
prices = db.fetch_one("SELECT MIN(date) as start FROM prices WHERE source = 'brapi'")
print(f"\nDados BRAPI desde: {prices['start']}")

if features['start'] != prices['start']:
    print("\n⚠️ Features NÃO cobrem período histórico completo!")
    print("Precisa recalcular features para todos os dados históricos.")
else:
    print("\n✓ Features cobrem período histórico!")
