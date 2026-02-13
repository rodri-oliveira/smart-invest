#!/usr/bin/env python3
"""
Importador de dados via CSV.
Alternativa robusta quando APIs (brapi/yfinance) falham.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import logging
import pandas as pd
from datetime import datetime

from aim.data_layer.database import Database

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def import_prices_from_csv(
    csv_path: str,
    ticker: str,
    db: Database,
) -> int:
    """
    Importa preços de arquivo CSV.
    
    Formato esperado do CSV:
    date,open,high,low,close,volume
    2020-01-02,25.50,26.00,25.20,25.80,15000000
    ...
    
    Args:
        csv_path: Caminho para o arquivo CSV
        ticker: Código do ativo
        db: Conexão com banco
    
    Returns:
        Número de registros inseridos
    """
    try:
        df = pd.read_csv(csv_path)
        
        # Normalizar colunas
        df.columns = df.columns.str.lower().str.strip()
        
        # Verificar colunas obrigatórias
        required = ['date', 'close']
        missing = [c for c in required if c not in df.columns]
        if missing:
            logger.error(f"Colunas obrigatórias ausentes: {missing}")
            return 0
        
        count = 0
        for _, row in df.iterrows():
            try:
                record = {
                    'ticker': ticker,
                    'date': str(row['date'])[:10],
                    'open': float(row.get('open', row['close'])),
                    'high': float(row.get('high', row['close'])),
                    'low': float(row.get('low', row['close'])),
                    'close': float(row['close']),
                    'volume': int(row.get('volume', 0)),
                    'adjusted_close': float(row['close']),
                    'source': 'csv_import',
                }
                
                db.upsert(
                    'prices',
                    record,
                    conflict_columns=['ticker', 'date']
                )
                count += 1
                
            except Exception as e:
                logger.warning(f"Erro na linha: {e}")
                continue
        
        logger.info(f"✓ {ticker}: {count} registros importados de {csv_path}")
        return count
        
    except Exception as e:
        logger.error(f"Erro ao importar {csv_path}: {e}")
        return 0


def import_from_yahoo_csv(
    csv_path: str,
    ticker: str,
    db: Database,
) -> int:
    """
    Importa CSV exportado do Yahoo Finance.
    
    Yahoo exporta com colunas: Date, Open, High, Low, Close, Adj Close, Volume
    """
    try:
        df = pd.read_csv(csv_path)
        
        # Renomear colunas do Yahoo
        column_map = {
            'Date': 'date',
            'Open': 'open',
            'High': 'high',
            'Low': 'low',
            'Close': 'close',
            'Adj Close': 'adjusted_close',
            'Volume': 'volume',
        }
        
        df = df.rename(columns=column_map)
        
        count = 0
        for _, row in df.iterrows():
            try:
                record = {
                    'ticker': ticker,
                    'date': str(row['date'])[:10],
                    'open': float(row['open']),
                    'high': float(row['high']),
                    'low': float(row['low']),
                    'close': float(row['close']),
                    'volume': int(row['volume']),
                    'adjusted_close': float(row.get('adjusted_close', row['close'])),
                    'source': 'yahoo_csv',
                }
                
                db.upsert('prices', record, conflict_columns=['ticker', 'date'])
                count += 1
                
            except Exception as e:
                continue
        
        logger.info(f"✓ {ticker}: {count} registros do Yahoo CSV")
        return count
        
    except Exception as e:
        logger.error(f"Erro: {e}")
        return 0


def main():
    """Função principal."""
    print("=" * 60)
    print("Importador de Dados via CSV")
    print("=" * 60)
    print("\nOpções para obter dados reais:")
    print("1. BRAPI (API): https://brapi.dev - obter token gratuito")
    print("2. Yahoo Finance: https://finance.yahoo.com")
    print("   - Buscar ticker (ex: PETR4.SA)")
    print("   - Historical Data → Download")
    print("3. Investing.com: exportar dados históricos")
    print()
    
    db = Database()
    
    # Diretório para CSVs
    csv_dir = Path("data/csv_imports")
    csv_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"Coloque seus arquivos CSV em: {csv_dir}")
    print("\nFormatos suportados:")
    print("  - CSV simples: date,open,high,low,close,volume")
    print("  - Yahoo Finance: Date,Open,High,Low,Close,Adj Close,Volume")
    print()
    
    # Verificar se há CSVs
    csv_files = list(csv_dir.glob("*.csv"))
    
    if not csv_files:
        print("✗ Nenhum arquivo CSV encontrado")
        print(f"\nInstruções:")
        print(f"1. Acesse https://finance.yahoo.com/quote/PETR4.SA/history")
        print(f"2. Clique em 'Download' para obter dados históricos")
        print(f"3. Salve em: {csv_dir}/PETR4.csv")
        print(f"4. Repita para outros ativos (VALE3, ITUB4, etc)")
        print(f"5. Rode novamente: python scripts/import_csv.py")
        return 1
    
    print(f"Arquivos encontrados: {len(csv_files)}")
    print()
    
    total = 0
    for csv_file in csv_files:
        # Extrair ticker do nome do arquivo
        ticker = csv_file.stem.upper()
        
        print(f"Importando: {csv_file.name} → {ticker}")
        
        # Tentar formato Yahoo primeiro
        count = import_from_yahoo_csv(str(csv_file), ticker, db)
        
        if count == 0:
            # Tentar formato simples
            count = import_prices_from_csv(str(csv_file), ticker, db)
        
        total += count
    
    print("\n" + "=" * 60)
    print(f"✓ Total importado: {total} registros")
    print("=" * 60)
    
    if total > 0:
        print("\nPróximo passo:")
        print("  python scripts/daily_update.py --offline")
        print("  python scripts/run_backtest.py")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
