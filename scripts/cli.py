#!/usr/bin/env python3
"""
CLI do Smart Invest - Interface de linha de comando.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import click
from aim.data_layer.database import Database
from aim.regime.engine import get_current_regime, get_regime_history
from aim.scoring.engine import get_top_ranked_assets
from aim.allocation.engine import build_portfolio_from_scores


@click.group()
def cli():
    """Smart Invest CLI - Sistema de Inteligência de Investimentos"""
    pass


@cli.command()
def status():
    """Verifica status do sistema"""
    db = Database()
    
    # Verificar banco
    tables = ["assets", "prices", "features", "signals", "regime_state"]
    existing = sum(1 for t in tables if db.table_exists(t))
    
    click.echo(f"✓ Banco de dados: {existing}/{len(tables)} tabelas OK")
    
    # Verificar dados
    assets = db.fetch_one("SELECT COUNT(*) as n FROM assets")["n"]
    prices = db.fetch_one("SELECT COUNT(*) as n FROM prices")["n"]
    signals = db.fetch_one("SELECT COUNT(*) as n FROM signals")["n"]
    
    click.echo(f"✓ Ativos: {assets}")
    click.echo(f"✓ Preços: {prices:,}")
    click.echo(f"✓ Sinais: {signals:,}")
    
    # Regime atual
    regime = get_current_regime(db)
    if regime:
        click.echo(f"✓ Regime atual: {regime['regime']} (score: {regime['score_total']:.2f})")
    else:
        click.echo("✗ Sem dados de regime")


@cli.command()
@click.option('--top', default=10, help='Número de ativos')
def ranking(top):
    """Mostra ranking dos melhores ativos"""
    db = Database()
    
    assets = get_top_ranked_assets(db, top_n=top)
    
    if assets.empty:
        click.echo("✗ Sem dados de ranking. Rode: python scripts/daily_update.py")
        return
    
    click.echo(f"\n{'Rank':<6} {'Ticker':<8} {'Score':<8} {'Mom':<6} {'Qual':<6} {'Val':<6}")
    click.echo("-" * 50)
    
    for _, row in assets.iterrows():
        click.echo(
            f"{row['rank_universe']:<6} "
            f"{row['ticker']:<8} "
            f"{row['score_final']:>+7.2f} "
            f"{row.get('score_momentum', 0):>+5.2f} "
            f"{row.get('score_quality', 0):>+5.2f} "
            f"{row.get('score_value', 0):>+5.2f}"
        )


@cli.command()
def regime():
    """Mostra regime de mercado atual"""
    db = Database()
    
    current = get_current_regime(db)
    if not current:
        click.echo("✗ Sem dados de regime")
        return
    
    click.echo(f"\nData: {current['date']}")
    click.echo(f"Regime: {current['regime']}")
    click.echo(f"Score Total: {current['score_total']:.2f}")
    click.echo("\nComponentes:")
    click.echo(f"  Yield Curve:     {current.get('score_yield_curve', 0):>+6.2f}")
    click.echo(f"  Risk Spread:     {current.get('score_risk_spread', 0):>+6.2f}")
    click.echo(f"  Ibov Trend:      {current.get('score_ibov_trend', 0):>+6.2f}")
    click.echo(f"  Capital Flow:    {current.get('score_capital_flow', 0):>+6.2f}")
    click.echo(f"  Liquidity:       {current.get('score_liquidity', 0):>+6.2f}")


@cli.command()
@click.option('--positions', default=5, help='Número de posições')
@click.option('--strategy', default='equal_weight', 
              type=click.Choice(['equal_weight', 'score_weighted', 'risk_parity']))
def portfolio(positions, strategy):
    """Constrói carteira otimizada"""
    db = Database()
    
    click.echo(f"\nConstruindo carteira: {strategy}, {positions} posições...")
    
    holdings = build_portfolio_from_scores(
        db=db,
        n_positions=positions,
        strategy=strategy,
    )
    
    if not holdings:
        click.echo("✗ Não foi possível construir carteira")
        return
    
    click.echo(f"\n{'Ticker':<8} {'Peso':<8} {'Score':<8} {'Setor'}")
    click.echo("-" * 40)
    
    for h in holdings:
        click.echo(
            f"{h['ticker']:<8} "
            f"{h['weight']:<8.1%} "
            f"{h['score']:>+7.2f} "
            f"{h.get('sector', 'N/A')}"
        )
    
    total = sum(h["weight"] for h in holdings)
    click.echo("-" * 40)
    click.echo(f"{'Total':<8} {total:<8.1%}")


@cli.command()
def update():
    """Roda pipeline de atualização diária"""
    import subprocess
    
    click.echo("Iniciando atualização diária...")
    result = subprocess.run(
        ["python", "scripts/daily_update.py"],
        capture_output=True,
        text=True
    )
    
    click.echo(result.stdout)
    if result.returncode != 0:
        click.echo(result.stderr, err=True)
        sys.exit(1)


if __name__ == "__main__":
    cli()
