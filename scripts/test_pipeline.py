#!/usr/bin/env python3
"""
Script de teste do pipeline completo.
Executa todo o fluxo: dados → features → regime → scores → carteira.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from aim.data_layer.database import Database
from aim.regime.engine import get_current_regime, update_daily_regime
from aim.scoring.engine import get_top_ranked_assets
from aim.allocation.engine import build_portfolio_from_scores, generate_portfolio_report


def test_pipeline():
    """Testa o pipeline completo."""
    print("=" * 60)
    print("Teste do Pipeline Smart Invest")
    print("=" * 60)
    
    db = Database()
    
    # 1. Verificar regime atual
    print("\n[1] Regime de Mercado:")
    regime = get_current_regime(db)
    if regime:
        print(f"  Data: {regime['date']}")
        print(f"  Regime: {regime['regime']}")
        print(f"  Score: {regime['score_total']:.2f}")
    else:
        print("  ⚠ Sem dados de regime")
    
    # 2. Verificar top ranked
    print("\n[2] Top 10 Ativos Ranqueados:")
    top_assets = get_top_ranked_assets(db, top_n=10)
    if not top_assets.empty:
        for _, row in top_assets.iterrows():
            print(f"  {row['rank_universe']:2d}. {row['ticker']:6s} "
                  f"(Score: {row['score_final']:+.2f})")
    else:
        print("  ⚠ Sem dados de ranking")
    
    # 3. Construir carteira
    print("\n[3] Carteira Recomendada (Equal Weight):")
    holdings = build_portfolio_from_scores(
        db,
        n_positions=5,
        strategy="equal_weight"
    )
    
    if holdings:
        total = sum(h["weight"] for h in holdings)
        for h in holdings:
            print(f"  {h['ticker']:6s} - {h['weight']:.1%} "
                  f"(Score: {h['score']:+.2f})")
        print(f"\n  Total alocado: {total:.1%}")
    else:
        print("  ⚠ Não foi possível construir carteira")
    
    print("\n" + "=" * 60)
    print("Teste concluído!")
    print("=" * 60)


if __name__ == "__main__":
    test_pipeline()
