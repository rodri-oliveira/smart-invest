#!/usr/bin/env python3
"""Verificar dados macro e testar sentiment scorer."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from aim.data_layer.database import Database
from aim.sentiment.scorer import SentimentScorer

if __name__ == "__main__":
    db = Database()
    
    print("DADOS MACRO DISPONÍVEIS:")
    print("=" * 60)
    
    macro = db.fetch_all(
        "SELECT indicator, COUNT(*) as n, MIN(date) as start, MAX(date) as end "
        "FROM macro_indicators GROUP BY indicator ORDER BY n DESC"
    )
    
    for row in macro:
        print(f"  {row['indicator']}: {row['n']} registros ({row['start']} a {row['end']})")
    
    print("\n" + "=" * 60)
    print("TESTE SENTIMENT SCORER:")
    print("=" * 60)
    
    scorer = SentimentScorer(db)
    
    for date in ['2025-01-15', '2024-06-15', '2024-01-15']:
        print(f"\nData: {date}")
        sentiment = scorer.calculate_daily_sentiment(date, lookback_days=30)
        print(f"  Score: {sentiment['score']:+.2f}")
        print(f"  Sentimento: {sentiment['sentiment']}")
        print(f"  Confiança: {sentiment['confidence']:.0%}")
        
        for comp, data in sentiment['components'].items():
            factors = data.get('factors', [])
            score = data.get('score', 0)
            available = data.get('data_available', False)
            print(f"  {comp}: {score:+.2f} (dados: {available}, fatores: {factors})")
