#!/usr/bin/env python3
"""Testar sentiment scorer."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from aim.data_layer.database import Database
from aim.sentiment.scorer import SentimentScorer

if __name__ == "__main__":
    db = Database()
    scorer = SentimentScorer(db)

    sentiment = scorer.calculate_daily_sentiment('2025-01-15')

    print(f"Data: {sentiment['date']}")
    print(f"Score: {sentiment['score']:+.2f}")
    print(f"Sentimento: {sentiment['sentiment']}")
    print(f"Confiança: {sentiment['confidence']:.0%}")
    print()
    print("Componentes:")
    for comp, data in sentiment['components'].items():
        factors = data.get('factors', [])
        score = data.get('score', 0)
        print(f"  {comp}: {score:+.2f} - {factors}")
