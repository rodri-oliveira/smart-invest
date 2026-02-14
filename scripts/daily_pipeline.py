#!/usr/bin/env python3
"""
Pipeline de Atualização Diária - Smart Invest v1.0

Executa automaticamente:
1. Atualização de preços de mercado
2. Cálculo de features
3. Atualização de dados macro
4. Cálculo de sentimento
5. Geração de sinais
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import logging
from datetime import datetime
import argparse

from aim.data_layer.database import Database
from aim.data_layer.providers.brapi import BrapiProvider
from aim.features.engine import calculate_all_features
from aim.sentiment.scorer import SentimentScorer
from aim.scoring.engine import generate_daily_signals

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def update_market_data(db: Database, provider: BrapiProvider) -> int:
    """Atualiza preços de mercado."""
    logger.info("=" * 60)
    logger.info("1. ATUALIZANDO DADOS DE MERCADO")
    logger.info("=" * 60)
    
    # Buscar todos os ativos ativos
    assets = db.fetch_all("SELECT ticker FROM assets WHERE is_active = TRUE")
    tickers = [a["ticker"] for a in assets]
    
    logger.info(f"Atualizando {len(tickers)} ativos...")
    
    updated = 0
    errors = 0
    
    for i, ticker in enumerate(tickers, 1):
        try:
            # Buscar últimos 5 dias (atualização incremental)
            from datetime import datetime, timedelta
            end_date = datetime.now().strftime("%Y-%m-%d")
            start_date = (datetime.now() - timedelta(days=5)).strftime("%Y-%m-%d")
            
            prices = provider.get_prices(ticker, start_date=start_date, end_date=end_date)
            
            if not prices:
                continue
            
            for price in prices:
                record = {
                    "ticker": ticker,
                    "date": price["date"],
                    "open": price.get("open"),
                    "high": price.get("high"),
                    "low": price.get("low"),
                    "close": price.get("close"),
                    "volume": price.get("volume"),
                }
                db.upsert("prices", record, conflict_columns=["ticker", "date"])
            
            updated += 1
            
            if i % 10 == 0:
                logger.info(f"  Progresso: {i}/{len(tickers)} ativos")
                
        except Exception as e:
            logger.error(f"  Erro em {ticker}: {e}")
            errors += 1
    
    logger.info(f"\n✓ {updated} ativos atualizados, {errors} erros")
    return updated


def recalculate_features(db: Database) -> int:
    """Recalcula features para dados novos."""
    logger.info("\n" + "=" * 60)
    logger.info("2. RECALCULANDO FEATURES")
    logger.info("=" * 60)
    
    # Calcular features para últimos 5 dias
    from datetime import datetime, timedelta
    
    end_date = datetime.now().strftime("%Y-%m-%d")
    start_date = (datetime.now() - timedelta(days=5)).strftime("%Y-%m-%d")
    
    try:
        count = calculate_all_features(db, start_date=start_date, end_date=end_date)
        logger.info(f"✓ {count} features calculadas")
        return count
    except Exception as e:
        logger.error(f"✗ Erro ao calcular features: {e}")
        return 0


def update_macro_data(db: Database) -> int:
    """Atualiza dados macro do BCB."""
    logger.info("\n" + "=" * 60)
    logger.info("3. ATUALIZANDO DADOS MACRO")
    logger.info("=" * 60)
    
    try:
        from aim.data_layer.providers.bcb import BCBProvider
        bcb = BCBProvider()
        
        # Buscar últimos 30 dias de dados diários
        from datetime import datetime, timedelta
        end_date = datetime.now()
        start_date = end_date - timedelta(days=30)
        
        start_str = start_date.strftime("%d/%m/%Y")
        end_str = end_date.strftime("%d/%m/%Y")
        
        total = 0
        
        # CDI (diário)
        try:
            data = bcb.get_series(12, start_str, end_str)  # CDI
            for item in data:
                db.upsert(
                    "macro_indicators",
                    {
                        "date": item["date"],
                        "indicator": "CDI",
                        "value": item["value"],
                        "unit": "% a.a.",
                        "frequency": "DAILY",
                        "source": "BCB",
                    },
                    conflict_columns=["date", "indicator"],
                )
            total += len(data)
            logger.info(f"  CDI: {len(data)} registros atualizados")
        except Exception as e:
            logger.warning(f"  CDI: erro - {e}")
        
        # USD (diário)
        try:
            data = bcb.get_series(1, start_str, end_str)  # USD PTAX
            for item in data:
                db.upsert(
                    "macro_indicators",
                    {
                        "date": item["date"],
                        "indicator": "USD",
                        "value": item["value"],
                        "unit": "BRL/USD",
                        "frequency": "DAILY",
                        "source": "BCB",
                    },
                    conflict_columns=["date", "indicator"],
                )
            total += len(data)
            logger.info(f"  USD: {len(data)} registros atualizados")
        except Exception as e:
            logger.warning(f"  USD: erro - {e}")
        
        logger.info(f"✓ {total} registros macro atualizados")
        return total
        
    except Exception as e:
        logger.error(f"✗ Erro ao atualizar macro: {e}")
        return 0


def update_sentiment(db: Database) -> bool:
    """Atualiza cálculo de sentimento."""
    logger.info("\n" + "=" * 60)
    logger.info("4. ATUALIZANDO SENTIMENTO DE MERCADO")
    logger.info("=" * 60)
    
    try:
        scorer = SentimentScorer(db)
        sentiment = scorer.calculate_daily_sentiment()
        
        logger.info(f"✓ Sentimento calculado: {sentiment['sentiment']}")
        logger.info(f"  Score: {sentiment['score']:+.2f}")
        logger.info(f"  Confiança: {sentiment['confidence']:.0%}")
        
        # Salvar no banco (opcional - criar tabela sentiment se necessário)
        # Por enquanto apenas log
        
        return True
        
    except Exception as e:
        logger.error(f"✗ Erro ao calcular sentimento: {e}")
        return False


def generate_signals(db: Database) -> dict:
    """Gera sinais diários."""
    logger.info("\n" + "=" * 60)
    logger.info("5. GERANDO SINAIS DIÁRIOS")
    logger.info("=" * 60)
    
    try:
        stats = generate_daily_signals(db)
        
        if stats["status"] == "success":
            logger.info(f"✓ {stats['signals_generated']} sinais gerados")
            logger.info(f"  Top 10: {stats['top_10']}")
            logger.info(f"  Regime: {stats['regime']}")
            logger.info(f"  Score médio: {stats['avg_score']:.2f}")
        else:
            logger.warning(f"⚠ {stats.get('message', 'Sem sinais')}")
        
        return stats
        
    except Exception as e:
        logger.error(f"✗ Erro ao gerar sinais: {e}")
        return {"status": "error", "message": str(e)}


def run_daily_update(full: bool = False):
    """
    Executa pipeline diário de atualização.
    
    Args:
        full: Se True, executa atualização completa (histórico). 
              Se False, apenas últimos 5 dias.
    """
    start_time = datetime.now()
    
    print("\n" + "=" * 70)
    print(f"SMART INVEST v1.0 - PIPELINE DE ATUALIZAÇÃO DIÁRIA")
    print(f"Início: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)
    
    db = Database()
    provider = BrapiProvider()
    
    results = {}
    
    # 1. Atualizar dados de mercado
    results["market_data"] = update_market_data(db, provider)
    
    # 2. Recalcular features
    results["features"] = recalculate_features(db)
    
    # 3. Atualizar dados macro
    results["macro"] = update_macro_data(db)
    
    # 4. Calcular sentimento
    results["sentiment"] = update_sentiment(db)
    
    # 5. Gerar sinais
    signal_stats = generate_signals(db)
    results["signals"] = signal_stats.get("signals_generated", 0)
    
    # Resumo
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    
    print("\n" + "=" * 70)
    print("RESUMO DA ATUALIZAÇÃO")
    print("=" * 70)
    print(f"Duração: {duration:.1f} segundos")
    print(f"Ativos atualizados: {results['market_data']}")
    print(f"Features calculadas: {results['features']}")
    print(f"Dados macro: {results['macro']}")
    print(f"Sentimento: {'OK' if results['sentiment'] else 'Falhou'}")
    print(f"Sinais gerados: {results['signals']}")
    print("=" * 70)
    
    # Verificar se houve erros críticos
    if results["market_data"] == 0:
        print("⚠️  ALERTA: Nenhum ativo atualizado!")
        return 1
    
    print("✅ Pipeline concluído com sucesso!")
    return 0


def main():
    """Entry point."""
    parser = argparse.ArgumentParser(
        description="Pipeline de atualização diária - Smart Invest"
    )
    parser.add_argument(
        "--full", 
        action="store_true",
        help="Executar atualização completa (histórico completo)"
    )
    parser.add_argument(
        "--market-only",
        action="store_true", 
        help="Apenas atualizar dados de mercado"
    )
    
    args = parser.parse_args()
    
    try:
        exit_code = run_daily_update(full=args.full)
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrompido pelo usuário")
        sys.exit(130)
    except Exception as e:
        logger.exception("Erro fatal no pipeline")
        print(f"\n❌ Erro fatal: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
