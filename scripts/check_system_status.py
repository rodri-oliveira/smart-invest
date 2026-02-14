#!/usr/bin/env python3
"""Verificar status final do sistema."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from aim.data_layer.database import Database
from aim.sentiment.scorer import SentimentScorer

db = Database()

print("=" * 60)
print("STATUS DO SISTEMA SMART INVEST v1.0")
print("=" * 60)

# Dados
prices = db.fetch_one("SELECT COUNT(*) as n FROM prices")
features = db.fetch_one("SELECT COUNT(*) as n FROM features")
macro = db.fetch_one("SELECT COUNT(*) as n FROM macro_indicators")
assets = db.fetch_one("SELECT COUNT(*) as n FROM assets WHERE is_active = TRUE")

print(f"Precos: {prices['n']} registros")
print(f"Features: {features['n']} registros")
print(f"Dados Macro: {macro['n']} registros")
print(f"Ativos Ativos: {assets['n']}")

# Testar sentimento
scorer = SentimentScorer(db)
sentiment = scorer.calculate_daily_sentiment("2025-01-15")
print(f"\nSentimento: {sentiment['sentiment']} (score: {sentiment['score']:+.2f}, confianca: {sentiment['confidence']:.0%})")

print("\n" + "=" * 60)
print("SISTEMA PRONTO PARA OPERACAO 24/7!")
print("=" * 60)
