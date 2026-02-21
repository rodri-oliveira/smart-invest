#!/usr/bin/env python3
"""
Pipeline de atualizaÃ§Ã£o diÃ¡ria de dados.
Coleta dados de mercado, calcula features, atualiza sinais.
"""

import logging
import sys

# Fix UTF-8 encoding on Windows
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer)
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer)

from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Tuple

# Adicionar root ao path
sys.path.insert(0, str(Path(__file__).parent.parent))

from aim.config.settings import get_settings
from aim.data_layer.database import Database
from aim.data_layer.providers import BCBProvider, BrapiProvider, MultiSourceProvider
from aim.features.engine import calculate_all_features
from aim.regime.engine import update_daily_regime
from aim.scoring.engine import generate_daily_signals

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("logs/daily_update.log"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)


def get_universe(db: Database) -> List[str]:
    """Retorna lista de ativos ativos no universo."""
    query = "SELECT ticker FROM assets WHERE is_active = TRUE"
    results = db.fetch_all(query)
    return [r["ticker"] for r in results]


def update_market_data(
    db: Database,
    provider: MultiSourceProvider,
    historical: bool = False,
    only_tickers: list[str] | None = None,
) -> Dict[str, Any]:
    """
    Atualiza precos historicos com fallback multi-fonte e telemetria.

    Args:
        db: Conexao com banco
        provider: MultiSourceProvider com fallback automatico
        historical: Se True, busca historico completo
        only_tickers: Se fornecido, atualiza apenas esses tickers (retry parcial)

    Returns:
        Estatisticas com relatorio por ticker
    """
    logger.info("Atualizando dados de mercado (multi-fonte)...")

    universe = only_tickers or get_universe(db)
    total_prices = 0

    if historical:
        start_date = None
        end_date = None
    else:
        end_date = datetime.now().strftime("%Y-%m-%d")
        start_date = (datetime.now() - timedelta(days=5)).strftime("%Y-%m-%d")

    report = provider.fetch_universe(universe, start_date=start_date, end_date=end_date)

    for result in report.results:
        prices = provider.get_prices_data(result)
        if not prices:
            continue
        for price in prices:
            db.upsert("prices", price, conflict_columns=["ticker", "date"])
        total_prices += len(prices)

    # Salvar relatorio para consulta via API
    import json
    report_path = Path("data/last_update_report.json")
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        json.dumps(report.to_dict(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    logger.info("Relatorio salvo em %s", report_path)

    return {
        "prices_updated": total_prices,
        "assets_processed": report.total,
        "ok": report.ok,
        "failed": report.failed,
        "failed_tickers": report.failed_tickers,
        "errors": report.failed,
    }


def update_fundamentals(
    db: Database,
    provider: BrapiProvider,
) -> Dict[str, int]:
    """
    Atualiza dados fundamentalistas.
    Executa semanalmente ou quando necessÃ¡rio.
    """
    logger.info("Atualizando dados fundamentalistas...")

    universe = get_universe(db)
    total_updated = 0
    errors = 0

    for i, ticker in enumerate(universe, 1):
        try:
            logger.info(f"[{i}/{len(universe)}] Coletando fundamentos de {ticker}...")

            fundamentals = provider.get_fundamentals(ticker)

            if not fundamentals:
                continue

            # Adicionar data de referÃªncia
            fundamentals["reference_date"] = datetime.now().strftime("%Y-%m-%d")
            fundamentals["report_type"] = "TRIMESTRAL"

            # Inserir
            db.upsert(
                "fundamentals",
                fundamentals,
                conflict_columns=["ticker", "reference_date", "report_type"],
            )

            total_updated += 1

        except Exception as e:
            logger.error(f"  âœ— Erro em {ticker}: {e}")
            errors += 1

    return {
        "fundamentals_updated": total_updated,
        "errors": errors,
    }


def update_macro_data(db: Database, provider: BCBProvider) -> Dict[str, int]:
    """
    Atualiza dados macroeconÃ´micos do BCB.
    """
    logger.info("Atualizando dados macroeconÃ´micos...")

    total_inserted = 0

    try:
        # SELIC
        logger.info("  Coletando SELIC...")
        selic_data = provider.get_selic_meta(days=365)
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
            total_inserted += 1
        logger.info(f"  âœ“ {len(selic_data)} registros SELIC")

        # CDI
        logger.info("  Coletando CDI...")
        cdi_data = provider.get_cdi(days=365)
        for item in cdi_data:
            db.upsert(
                "macro_indicators",
                {
                    "date": item["date"],
                    "indicator": "CDI",
                    "value": item["value"],
                    "unit": "percent",
                    "frequency": "DAILY",
                    "source": "BCB",
                },
                conflict_columns=["date", "indicator"],
            )
            total_inserted += 1
        logger.info(f"  âœ“ {len(cdi_data)} registros CDI")

        # IPCA
        logger.info("  Coletando IPCA...")
        ipca_data = provider.get_ipca(months=24)
        for item in ipca_data:
            db.upsert(
                "macro_indicators",
                {
                    "date": item["date"],
                    "indicator": "IPCA",
                    "value": item["value"],
                    "unit": "percent",
                    "frequency": "MONTHLY",
                    "source": "BCB",
                },
                conflict_columns=["date", "indicator"],
            )
            total_inserted += 1
        logger.info(f"  âœ“ {len(ipca_data)} registros IPCA")

        # USD
        logger.info("  Coletando USD/BRL...")
        usd_data = provider.get_usd_exchange(days=365)
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
            total_inserted += 1
        logger.info(f"  âœ“ {len(usd_data)} registros USD/BRL")

    except Exception as e:
        logger.error(f"  âœ— Erro em dados macro: {e}")

    return {"macro_inserted": total_inserted}


def calculate_features(db: Database) -> Dict[str, int]:
    """
    Calcula features tÃ©cnicas (momentum, volatilidade, liquidez).
    """
    logger.info("Calculando features...")

    stats = calculate_all_features(db)

    logger.info(f"  âœ“ {stats['processed']} ativos processados")
    logger.info(f"  âœ— {stats['errors']} erros")

    return stats


def generate_signals(db: Database) -> Dict:
    """
    Gera sinais e scores para todos os ativos (Fase 4).
    """
    logger.info("Gerando sinais...")
    
    try:
        result = generate_daily_signals(db)
        return {
            "signals_generated": result.get("signals_generated", 0),
            "top_10": result.get("top_10", []),
        }
    except Exception as e:
        logger.error(f"  âœ— Erro ao gerar sinais: {e}")
        return {"signals_generated": 0, "top_10": []}


def update_regime(db: Database) -> Dict:
    """
    Atualiza classificaÃ§Ã£o de regime de mercado.
    """
    logger.info("Atualizando classificaÃ§Ã£o de regime...")
    
    try:
        regime_data = update_daily_regime(db)
        return {
            "regime": regime_data["regime"],
            "regime_score": regime_data["score_total"],
        }
    except Exception as e:
        logger.error(f"  âœ— Erro no regime: {e}")
        return {"regime": "UNKNOWN", "regime_score": 0.0}


def backup_database() -> Path:
    """Cria backup do banco de dados."""
    import gzip
    import shutil

    db_path = get_settings().db_path
    backup_dir = Path("data/backups")
    backup_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = backup_dir / f"smart_invest_{timestamp}.db.gz"

    with open(db_path, "rb") as f_in:
        with gzip.open(backup_file, "wb") as f_out:
            shutil.copyfileobj(f_in, f_out)

    logger.info(f"âœ“ Backup criado: {backup_file}")
    return backup_file


def validate_data_quality(db: Database) -> bool:
    """Valida qualidade dos dados apÃ³s atualizaÃ§Ã£o."""
    logger.info("Validando qualidade dos dados...")

    checks = []

    # 1. Verificar preÃ§os recentes
    today = datetime.now().strftime("%Y-%m-%d")
    recent = db.fetch_one(
        "SELECT MAX(date) as max_date FROM prices",
    )

    if recent and recent["max_date"] and isinstance(recent["max_date"], str):
        days_diff = (datetime.now() - datetime.strptime(recent["max_date"], "%Y-%m-%d")).days
        if days_diff > 2:
            logger.warning(f"  âš  Dados desatualizados: Ãºltima data Ã© {recent['max_date']}")
            checks.append(False)
        else:
            logger.info(f"  âœ“ Dados atualizados atÃ© {recent['max_date']}")
            checks.append(True)
    else:
        logger.warning("  âš  Sem dados de preÃ§os disponÃ­veis")
        checks.append(False)

    # 2. Verificar cobertura mÃ­nima
    count = db.fetch_one("SELECT COUNT(DISTINCT ticker) as count FROM prices")
    if count and count["count"] >= 10:
        logger.info(f"  âœ“ {count['count']} ativos com dados")
        checks.append(True)
    else:
        logger.warning(f"  âš  Apenas {count['count']} ativos com dados")
        checks.append(False)

    return all(checks)


def check_local_data(db: Database) -> bool:
    """Verifica se hÃ¡ dados locais suficientes."""
    logger.info("Verificando dados locais...")

    # Verificar se hÃ¡ dados de preÃ§os
    prices = db.fetch_one("SELECT COUNT(*) as count FROM prices")
    if prices and prices["count"] > 0:
        logger.info(f"  âœ“ {prices['count']} registros de preÃ§os")
        return True
    else:
        logger.warning("  âš  Sem dados de preÃ§os locais")
        return False


def main() -> int:
    """FunÃ§Ã£o principal do pipeline diÃ¡rio."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Pipeline diÃ¡rio de atualizaÃ§Ã£o")
    parser.add_argument("--offline", action="store_true", help="Usar apenas dados locais (nÃ£o chamar APIs externas)")
    parser.add_argument("--full-history", action="store_true", help="Busca historico completo de precos (mais lento; use para carga inicial)")
    args = parser.parse_args()
    
    try:
        logger.info("=" * 60)
        logger.info(f"Daily Update - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        if args.offline:
            logger.info("MODO OFFLINE - Usando apenas dados locais")
        logger.info("=" * 60)

        Path("logs").mkdir(exist_ok=True)

        db = Database()
        
        # Verificar se hÃ¡ dados locais suficientes
        has_local_data = check_local_data(db)
        
        if args.offline and not has_local_data:
            logger.error("âœ— MODO OFFLINE: NÃ£o hÃ¡ dados locais. Rode: python scripts/seed_demo.py")
            return 1

        stats = {}

        # 1. Atualizar dados de mercado (se nÃ£o estiver em modo offline)
        if not args.offline:
            logger.info("\n[1/7] Atualizando dados de mercado (multi-fonte)...")
            multi = MultiSourceProvider()
            market_stats = update_market_data(db, multi, historical=args.full_history)
            stats.update(market_stats)
            multi.close()
        else:
            logger.info("\n[1/6] Pulando atualizaÃ§Ã£o de mercado (modo offline)")
            stats["prices_updated"] = 0
            stats["errors"] = 0

        # 2. Atualizar fundamentos (segunda-feira, apenas se nÃ£o offline)
        if not args.offline and datetime.now().weekday() == 0:
            logger.info("\n[2/6] Atualizando dados fundamentalistas...")
            brapi_fund = BrapiProvider()
            fund_stats = update_fundamentals(db, brapi_fund)
            stats.update(fund_stats)
            brapi_fund.close()
        else:
            logger.info("\n[2/6] Pulando fundamentos (atualizaÃ§Ã£o semanal ou modo offline)")
            stats["fundamentals_updated"] = 0

        # 3. Atualizar dados macro (se nÃ£o offline)
        if not args.offline:
            logger.info("\n[3/6] Atualizando dados macroeconÃ´micos...")
            bcb = BCBProvider()
            macro_stats = update_macro_data(db, bcb)
            stats.update(macro_stats)
            bcb.close()
        else:
            logger.info("\n[3/6] Pulando dados macro (modo offline)")
            stats["macro_inserted"] = 0

        # 4. Calcular features
        logger.info("\n[4/7] Calculando features...")
        feature_stats = calculate_features(db)
        stats.update(feature_stats)

        # 5. Atualizar regime
        logger.info("\n[5/7] Atualizando regime de mercado...")
        regime_stats = update_regime(db)
        stats.update(regime_stats)

        # 6. Gerar sinais (Fase 4)
        logger.info("\n[6/7] Gerando sinais...")
        signal_stats = generate_signals(db)
        stats.update(signal_stats)

        # 7. Validar qualidade
        logger.info("\n[7/7] Validando qualidade dos dados...")
        is_valid = validate_data_quality(db)
        stats["data_valid"] = is_valid

        # 6. Backup
        logger.info("\n[Extra] Criando backup...")
        backup_path = backup_database()
        stats["backup_path"] = str(backup_path)

        # Summary
        logger.info("\n" + "=" * 60)
        logger.info("Resumo da AtualizaÃ§Ã£o")
        logger.info("=" * 60)
        logger.info(f"Precos atualizados: {stats.get('prices_updated', 0)}")
        logger.info(f"Ativos OK: {stats.get('ok', 'N/A')} | Falhas: {stats.get('failed', 0)}")
        if stats.get('failed_tickers'):
            logger.warning(f"Tickers com falha: {stats.get('failed_tickers')}")
        logger.info(f"Fundamentos atualizados: {stats.get('fundamentals_updated', 0)}")
        logger.info(f"Dados macro inseridos: {stats.get('macro_inserted', 0)}")
        logger.info(f"Sinais gerados: {stats.get('signals_generated', 0)}")
        logger.info(f"Top 10: {stats.get('top_10', [])}")
        logger.info(f"Regime: {stats.get('regime', 'N/A')} (score: {stats.get('regime_score', 0):.2f})")
        logger.info(f"Dados validos: {'Sim' if is_valid else 'Nao'}")
        logger.info(f"Backup: {backup_path.name}")
        logger.info("=" * 60)
        logger.info("Atualizacao concluida!")

        # Fechar conexoes (se existirem)
        if not args.offline and 'multi' in locals():
            multi.close()

        return 0 if is_valid else 1

    except Exception as e:
        logger.error(f"\nâœ— Erro na atualizaÃ§Ã£o: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())

