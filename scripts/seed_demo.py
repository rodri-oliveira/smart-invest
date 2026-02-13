#!/usr/bin/env python3
"""
Script para inserir dados de demonstração/teste.
Permite testar o pipeline sem depender da API brapi.dev.
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta
import random

sys.path.insert(0, str(Path(__file__).parent.parent))

from aim.data_layer.database import Database
from aim.data_layer.providers import BCBProvider

# Gerar preços sintéticos para teste
def generate_synthetic_prices(ticker, days=252):
    """Gera preços sintéticos para um ativo."""
    prices = []
    base_price = random.uniform(20, 100)
    
    end_date = datetime.now()
    
    for i in range(days):
        date = end_date - timedelta(days=i)
        # Random walk com drift positivo leve
        change = random.uniform(-0.03, 0.035)
        base_price = base_price * (1 + change)
        
        prices.append({
            "ticker": ticker,
            "date": date.strftime("%Y-%m-%d"),
            "open": round(base_price * (1 + random.uniform(-0.01, 0.01)), 4),
            "high": round(base_price * (1 + random.uniform(0, 0.02)), 4),
            "low": round(base_price * (1 + random.uniform(-0.02, 0)), 4),
            "close": round(base_price, 4),
            "volume": random.randint(1000000, 50000000),
            "adjusted_close": round(base_price, 4),
            "source": "demo",
        })
    
    return prices


def seed_demo_prices(db: Database, tickers=None, days=252):
    """Insere preços de demonstração para teste."""
    if tickers is None:
        # Pegar ativos do universo
        result = db.fetch_all("SELECT ticker FROM assets WHERE is_active = 1 AND is_index = 0 LIMIT 10")
        tickers = [r["ticker"] for r in result]
    
    print(f"Inserindo preços de demonstração para {len(tickers)} ativos...")
    
    total = 0
    for ticker in tickers:
        prices = generate_synthetic_prices(ticker, days)
        for price in prices:
            try:
                db.upsert("prices", price, conflict_columns=["ticker", "date"])
                total += 1
            except Exception as e:
                print(f"  Erro em {ticker}: {e}")
        print(f"  ✓ {ticker}: {len(prices)} preços")
    
    print(f"✓ Total: {total} preços inseridos")
    return total


def seed_demo_macro(db: Database):
    """Insere dados macro de demonstração."""
    print("Inserindo dados macro de demonstração...")
    
    # Usar BCBProvider para dados reais se possível
    try:
        bcb = BCBProvider()
        
        # SELIC últimos 30 dias
        selic_data = bcb.get_selic_meta(days=30)
        for item in selic_data:
            db.upsert(
                "macro_indicators",
                {
                    "date": item["date"],
                    "indicator": "SELIC",
                    "value": item["value"],
                    "unit": "percent",
                    "frequency": "DAILY",
                    "source": "BCB",
                },
                conflict_columns=["date", "indicator"],
            )
        print(f"  ✓ SELIC: {len(selic_data)} registros")
        
        # USD/BRL
        usd_data = bcb.get_usd_exchange(days=30)
        for item in usd_data:
            db.upsert(
                "macro_indicators",
                {
                    "date": item["date"],
                    "indicator": "USD_BRL",
                    "value": item["value"],
                    "unit": "rate",
                    "frequency": "DAILY",
                    "source": "BCB",
                },
                conflict_columns=["date", "indicator"],
            )
        print(f"  ✓ USD/BRL: {len(usd_data)} registros")
        
        bcb.close()
        
    except Exception as e:
        print(f"  ⚠ Usando dados sintéticos: {e}")
        # Gerar dados sintéticos
        end_date = datetime.now()
        for i in range(30):
            date = (end_date - timedelta(days=i)).strftime("%Y-%m-%d")
            db.upsert(
                "macro_indicators",
                {
                    "date": date,
                    "indicator": "SELIC",
                    "value": 11.75 + random.uniform(-0.5, 0.5),
                    "unit": "percent",
                    "frequency": "DAILY",
                    "source": "demo",
                },
                conflict_columns=["date", "indicator"],
            )
        print(f"  ✓ SELIC: 30 registros (sintético)")


def main():
    """Função principal."""
    print("=" * 60)
    print("Seed de Dados de Demonstração")
    print("=" * 60)
    
    db = Database()
    
    # 1. Inserir preços de demonstração
    seed_demo_prices(db)
    
    # 2. Inserir dados macro
    seed_demo_macro(db)
    
    print("\n" + "=" * 60)
    print("✓ Dados de demonstração inseridos!")
    print("=" * 60)
    print("\nAgora você pode rodar:")
    print("  python scripts/daily_update.py")
    print("ou")
    print("  python scripts/test_pipeline.py")


if __name__ == "__main__":
    main()
