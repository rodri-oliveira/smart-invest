"""Debug do cálculo de pesos da carteira."""

import sys
sys.path.insert(0, r'c:\projetos\smart-invest')

from aim.data_layer.database import Database
from aim.allocation.engine import build_portfolio_from_scores
from aim.scoring.engine import get_top_ranked_assets
from aim.config.parameters import TARGET_RV_ALLOCATION, MAX_POSITION_SIZE

db = Database()

# 1. Obter top ativos
print("=== Top Ativos ===")
top_assets = get_top_ranked_assets(db, top_n=10)
print(top_assets[['ticker', 'score_final', 'sector']])

# 2. Calcular carteira com debug
print("\n=== Construindo Carteira (score_weighted) ===")
holdings = build_portfolio_from_scores(db, n_positions=10, strategy='score_weighted')

print(f"\nTotal de posições: {len(holdings)}")
total_weight = 0
for h in holdings:
    print(f"  {h['ticker']}: peso={h['weight']:.4f} ({h['weight']*100:.1f}%), score={h['score']:.4f}")
    total_weight += h['weight']

print(f"\nPeso total: {total_weight:.4f} ({total_weight*100:.1f}%)")
print(f"TARGET_RV_ALLOCATION: {TARGET_RV_ALLOCATION}")
print(f"MAX_POSITION_SIZE: {MAX_POSITION_SIZE}")
