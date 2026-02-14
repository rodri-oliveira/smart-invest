"""Verificar estrutura do banco e executar pipeline de scores se necessário."""

import sys
sys.path.insert(0, r'c:\projetos\smart-invest')

from aim.data_layer.database import Database
import sqlite3

db = Database()

# 1. Listar todas as tabelas
print("=== Tabelas no banco ===")
tables = db.fetch_all("SELECT name FROM sqlite_master WHERE type='table'")
for t in tables:
    print(f"  - {t['name']}")

# 2. Verificar se asset_scores existe
print("\n=== Verificando asset_scores ===")
try:
    count = db.fetch_one("SELECT COUNT(*) as c FROM asset_scores")
    print(f"Registros em asset_scores: {count['c']}")
except Exception as e:
    print(f"ERRO: {e}")
    print("Tabela asset_scores não existe - precisa criar!")

# 3. Verificar features
print("\n=== Verificando features ===")
try:
    result = db.fetch_one("""
        SELECT COUNT(*) as c, MAX(date) as max_date 
        FROM market_features 
        WHERE date >= date('now', '-30 days')
    """)
    print(f"Features recentes: {result['c']} registros")
    print(f"Última data: {result['max_date']}")
except Exception as e:
    print(f"ERRO: {e}")
