"""Verificar estado dos scores no banco de dados."""

import sys
sys.path.insert(0, r'c:\projetos\smart-invest')

from aim.data_layer.database import Database

db = Database()

# 1. Verificar se há scores calculados
result = db.fetch_one("""
    SELECT COUNT(*) as count, 
           AVG(score_final) as avg_score,
           MAX(score_final) as max_score,
           MIN(score_final) as min_score
    FROM asset_scores 
    WHERE date = (SELECT MAX(date) FROM asset_scores)
""")

print(f"=== Scores na última data ===")
print(f"Total de ativos com score: {result['count']}")
print(f"Score médio: {result['avg_score']:.4f}" if result['avg_score'] else "Score médio: NULL")
print(f"Score máximo: {result['max_score']:.4f}" if result['max_score'] else "Score máximo: NULL")
print(f"Score mínimo: {result['min_score']:.4f}" if result['min_score'] else "Score mínimo: NULL")

# 2. Verificar top ativos
print(f"\n=== Top 10 ativos por score ===")
top = db.fetch_all("""
    SELECT ticker, score_final, score_momentum, score_volatility, score_liquidity
    FROM asset_scores 
    WHERE date = (SELECT MAX(date) FROM asset_scores)
    ORDER BY score_final DESC
    LIMIT 10
""")

for row in top:
    print(f"  {row['ticker']}: final={row['score_final']:.4f}, mom={row['score_momentum']:.4f}, vol={row['score_volatility']:.4f}, liq={row['score_liquidity']:.4f}")

# 3. Verificar carteira salva
print(f"\n=== Carteira SmartPortfolio ===")
portfolio = db.fetch_all("""
    SELECT h.ticker, h.weight, h.date
    FROM portfolio_holdings h
    JOIN portfolios p ON h.portfolio_id = p.portfolio_id
    WHERE p.name = 'SmartPortfolio'
    AND h.date = (SELECT MAX(date) FROM portfolio_holdings WHERE portfolio_id = p.portfolio_id)
    ORDER BY h.weight DESC
""")

total = 0
for row in portfolio:
    print(f"  {row['ticker']}: {row['weight']:.4f} ({row['weight']*100:.1f}%)")
    total += row['weight']

print(f"\nTotal: {total:.4f} ({total*100:.1f}%)")

# 4. Verificar se há dados na tabela scores (alternativa)
print(f"\n=== Verificando tabela 'scores' ===")
try:
    scores = db.fetch_all("""
        SELECT ticker, score_value, date
        FROM scores 
        WHERE date = (SELECT MAX(date) FROM scores)
        ORDER BY score_value DESC
        LIMIT 10
    """)
    for row in scores:
        print(f"  {row['ticker']}: {row['score_value']:.4f}")
except Exception as e:
    print(f"  Erro ou tabela não existe: {e}")
