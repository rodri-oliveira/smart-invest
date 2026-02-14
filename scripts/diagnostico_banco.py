#!/usr/bin/env python3
"""Diagnóstico completo do estado do banco de dados."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from aim.data_layer.database import Database
from datetime import datetime

db = Database()

print("=" * 70)
print("DIAGNÓSTICO DO BANCO DE DADOS")
print("=" * 70)

# 1. Estrutura da tabela prices
print("\n1. ESTRUTURA DA TABELA PRICES:")
schema = db.fetch_all("PRAGMA table_info(prices)")
for col in schema:
    print(f"   {col['name']}: {col['type']} (notnull={col['notnull']})")

# 2. Amostra de dados
print("\n2. AMOSTRA DE DADOS (últimos 3 registros de cada fonte):")
for source in ['brapi', 'demo']:
    sample = db.fetch_all(
        "SELECT ticker, date, typeof(date) as tipo_date, close, source FROM prices WHERE source = ? ORDER BY date DESC LIMIT 3",
        (source,)
    )
    if sample:
        print(f"\n   Fonte: {source}")
        for row in sample:
            print(f"     {row['ticker']}: date='{row['date']}' (tipo={row['tipo_date']}), close={row['close']}")

# 3. Range de datas por fonte
print("\n3. RANGE DE DATAS POR FONTE:")
ranges = db.fetch_all("""
    SELECT 
        source,
        COUNT(*) as n,
        MIN(date) as min_date,
        MAX(date) as max_date,
        COUNT(DISTINCT ticker) as n_ativos
    FROM prices
    GROUP BY source
    ORDER BY n DESC
""")

for r in ranges:
    print(f"\n   {r['source']}:")
    print(f"     Registros: {r['n']}")
    print(f"     Ativos: {r['n_ativos']}")
    print(f"     Período: {r['min_date']} a {r['max_date']}")

# 4. Problemas identificados
print("\n4. ANÁLISE:")

# Verificar se há datas em formatos diferentes
date_types = db.fetch_all("SELECT DISTINCT typeof(date) as tipo FROM prices")
print(f"\n   Tipos de dados na coluna 'date': {[t['tipo'] for t in date_types]}")

# Verificar cobertura mínima para backtest
coverage = db.fetch_one("""
    SELECT COUNT(DISTINCT ticker) as n_ativos,
           MIN(date) as min_date,
           MAX(date) as max_date,
           julianday(MAX(date)) - julianday(MIN(date)) as dias_cobertos
    FROM prices
""")

print(f"\n   Cobertura geral:")
print(f"     Ativos: {coverage['n_ativos']}")
print(f"     Período: {coverage['min_date']} a {coverage['max_date']}")
print(f"     Dias totais: {int(coverage['dias_cobertos']) if coverage['dias_cobertos'] else 0}")

if coverage['dias_cobertos'] and coverage['dias_cobertos'] > 252 * 5:
    print("\n   ✅ SUFICIENTE para backtest (5+ anos)")
elif coverage['dias_cobertos'] and coverage['dias_cobertos'] > 252:
    print("\n   ⚠️ MÍNIMO para backtest (1+ ano)")
else:
    print("\n   ❌ INSUFICIENTE para backtest (< 1 ano)")

print("\n" + "=" * 70)
