"""Verificar e popular tabela signals com scores."""

import sys
sys.path.insert(0, r'c:\projetos\smart-invest')

from aim.data_layer.database import Database
from aim.scoring.engine import generate_daily_signals

db = Database()

# 1. Verificar se signals existe e tem dados
print("=== Verificando tabela signals ===")
try:
    result = db.fetch_one("SELECT COUNT(*) as c, MAX(date) as max_date, MIN(date) as min_date FROM signals")
    print(f"Total de registros: {result['c']}")
    print(f"Data mais recente: {result['max_date']}")
    print(f"Data mais antiga: {result['min_date']}")
    
    if result['c'] > 0:
        # Mostrar amostra
        sample = db.fetch_all("SELECT ticker, score_final, rank_universe FROM signals WHERE date = ? ORDER BY rank_universe LIMIT 5", 
                              (result['max_date'],))
        print(f"\nTop 5 ativos:")
        for row in sample:
            print(f"  {row['ticker']}: score={row['score_final']}, rank={row['rank_universe']}")
    else:
        print("\nTabela vazia! Executando pipeline de geração de sinais...")
        stats = generate_daily_signals(db)
        print(f"Resultado: {stats}")
        
except Exception as e:
    print(f"ERRO: {e}")
    print("Tabela signals não existe ou está corrompida")
