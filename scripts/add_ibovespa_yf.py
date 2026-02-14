#!/usr/bin/env python3
"""Buscar IBOVESPA usando yfinance (^BVSP)."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from aim.data_layer.database import Database
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def add_ibovespa_yfinance():
    """Adiciona IBOVESPA usando yfinance."""
    db = Database()
    
    logger.info("Buscando IBOVESPA via yfinance...")
    
    try:
        import yfinance as yf
        
        # Download IBOVESPA (^BVSP)
        ticker = yf.Ticker("^BVSP")
        hist = ticker.history(period="max")
        
        if hist.empty:
            logger.error("Sem dados do yfinance")
            return
        
        logger.info(f"Downloaded {len(hist)} days of IBOVESPA data")
        
        # Adicionar como ativo
        db.upsert(
            "assets",
            {
                "ticker": "IBOVESPA",
                "name": "Indice Bovespa",
                "sector": "INDICE",
                "segment": "Indice de Acoes",
                "market_cap_category": "LARGE",
                "is_active": True,
                "is_index": True,
            },
            conflict_columns=["ticker"],
        )
        
        # Inserir preços
        inserted = 0
        for date, row in hist.iterrows():
            record = {
                "ticker": "IBOVESPA",
                "date": date.strftime("%Y-%m-%d"),
                "open": float(row["Open"]) if not pd.isna(row["Open"]) else None,
                "high": float(row["High"]) if not pd.isna(row["High"]) else None,
                "low": float(row["Low"]) if not pd.isna(row["Low"]) else None,
                "close": float(row["Close"]) if not pd.isna(row["Close"]) else None,
                "volume": int(row["Volume"]) if not pd.isna(row["Volume"]) else None,
                "adjusted_close": float(row["Close"]) if not pd.isna(row["Close"]) else None,
            }
            
            try:
                db.upsert("prices", record, conflict_columns=["ticker", "date"])
                inserted += 1
            except:
                pass
        
        logger.info(f"Inserted {inserted} IBOVESPA prices")
        
    except ImportError:
        logger.error("yfinance not installed. Run: pip install yfinance")
    except Exception as e:
        logger.error(f"Error: {e}")


if __name__ == "__main__":
    import pandas as pd
    add_ibovespa_yfinance()
