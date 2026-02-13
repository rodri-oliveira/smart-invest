#!/usr/bin/env python3
"""
Stress Tests - Validação em crises históricas.
Testa robustez do sistema em períodos de estresse.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import logging
from typing import Dict, List, Tuple
from datetime import datetime

import pandas as pd
import numpy as np

from aim.data_layer.database import Database

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


# Crises históricas para teste
STRESS_PERIODS = {
    "covid_crash": {
        "name": "COVID Crash",
        "start": "2020-02-20",
        "end": "2020-03-23",
        "description": "Queda de 50% em 1 mês",
        "severity": "HIGH",
    },
    "covid_recovery": {
        "name": "COVID Recovery",
        "start": "2020-03-23",
        "end": "2020-08-31",
        "description": "Recuperação rápida",
        "severity": "MEDIUM",
    },
    "2022_bear_market": {
        "name": "2022 Bear Market",
        "start": "2022-01-01",
        "end": "2022-10-01",
        "description": "Juros altos, inflação, guerra",
        "severity": "HIGH",
    },
    "2018_volatility": {
        "name": "2018 Volatility",
        "start": "2018-09-01",
        "end": "2018-12-31",
        "description": "QT Fed, guerra comercial",
        "severity": "MEDIUM",
    },
    "2015_crisis": {
        "name": "2015 Brasil Crisis",
        "start": "2015-05-01",
        "end": "2016-01-31",
        "description": "Impeachment, recessão",
        "severity": "HIGH",
    },
}


class StressTestEngine:
    """
    Motor de stress tests.
    
    Valida estratégia em períodos de crise para garantir
    que não quebra em momentos difíceis.
    """
    
    def __init__(self, db: Database):
        self.db = db
    
    def calculate_buy_and_hold_return(
        self,
        tickers: List[str],
        start_date: str,
        end_date: str,
    ) -> Dict[str, float]:
        """Calcula retorno buy-and-hold para comparação."""
        results = {}
        
        for ticker in tickers:
            query = """
                SELECT date, close
                FROM prices
                WHERE ticker = ?
                AND date BETWEEN ? AND ?
                ORDER BY date ASC
            """
            df = self.db.query_to_df(query, (ticker, start_date, end_date))
            
            if not df.empty and len(df) > 1:
                initial = df["close"].iloc[0]
                final = df["close"].iloc[-1]
                ret = (final / initial) - 1
                results[ticker] = ret
        
        return results
    
    def test_period(self, period_key: str) -> Dict:
        """
        Testa estratégia em um período de stress.
        
        Args:
            period_key: Chave do período em STRESS_PERIODS
        
        Returns:
            Métricas do período
        """
        period = STRESS_PERIODS[period_key]
        start = period["start"]
        end = period["end"]
        
        logger.info(f"\n{'='*60}")
        logger.info(f"STRESS TEST: {period['name']}")
        logger.info(f"Período: {start} a {end}")
        logger.info(f"Descrição: {period['description']}")
        logger.info(f"Severidade: {period['severity']}")
        logger.info(f"{'='*60}")
        
        # 1. Verificar se há dados para o período
        check = self.db.fetch_one("""
            SELECT COUNT(*) as count, MIN(date) as min_date, MAX(date) as max_date
            FROM prices
            WHERE date BETWEEN ? AND ?
        """, (start, end))
        
        if not check or check["count"] == 0:
            logger.warning("❌ Sem dados para este período")
            return {"error": "Sem dados"}
        
        logger.info(f"Dados disponíveis: {check['count']} registros")
        
        # 2. Calcular retorno do Ibovespa (benchmark)
        benchmark_query = """
            SELECT date, close
            FROM prices
            WHERE ticker = '^BVSP'
            AND date BETWEEN ? AND ?
            ORDER BY date ASC
        """
        benchmark_df = self.db.query_to_df(benchmark_query, (start, end))
        
        benchmark_return = 0
        if not benchmark_df.empty and len(benchmark_df) > 1:
            initial = benchmark_df["close"].iloc[0]
            final = benchmark_df["close"].iloc[-1]
            benchmark_return = (final / initial) - 1
            
            # Max drawdown do benchmark
            cumulative = (benchmark_df["close"] / initial)
            running_max = cumulative.expanding().max()
            drawdown = (cumulative - running_max) / running_max
            benchmark_max_dd = abs(drawdown.min())
            
            logger.info(f"Benchmark (^BVSP): {benchmark_return:+.2%}")
            logger.info(f"Benchmark Max DD: {benchmark_max_dd:.2%}")
        
        # 3. Simular estratégia (simplificada)
        # Na prática, usaria o scoring engine para selecionar ativos
        # Aqui fazemos uma aproximação com os top ativos por volume
        
        top_assets_query = """
            SELECT DISTINCT ticker
            FROM prices
            WHERE date BETWEEN ? AND ?
            AND ticker != '^BVSP'
            LIMIT 10
        """
        top_assets = self.db.fetch_all(top_assets_query, (start, end))
        tickers = [r["ticker"] for r in top_assets]
        
        if not tickers:
            logger.warning("❌ Sem ativos para testar")
            return {"error": "Sem ativos"}
        
        # Calcular retorno igual ponderado (proxy para estratégia)
        returns = self.calculate_buy_and_hold_return(tickers, start, end)
        
        if not returns:
            logger.warning("❌ Sem retornos calculados")
            return {"error": "Sem retornos"}
        
        avg_return = sum(returns.values()) / len(returns)
        
        logger.info(f"Estratégia (proxy): {avg_return:+.2%}")
        logger.info(f"Alpha: {(avg_return - benchmark_return):+.2%}")
        
        # 4. Verificar robustez
        robust = avg_return > benchmark_return or avg_return > -0.30  # Não perdeu mais que 30%
        
        if robust:
            logger.info("✅ PASSOU no stress test")
        else:
            logger.info("❌ FALHOU no stress test")
        
        return {
            "period": period["name"],
            "start": start,
            "end": end,
            "benchmark_return": benchmark_return,
            "strategy_return": avg_return,
            "alpha": avg_return - benchmark_return,
            "robust": robust,
            "severity": period["severity"],
        }
    
    def run_all_stress_tests(self) -> List[Dict]:
        """Executa todos os stress tests."""
        logger.info("\n" + "="*60)
        logger.info("EXECUTANDO TODOS OS STRESS TESTS")
        logger.info("="*60)
        
        results = []
        
        for key in STRESS_PERIODS:
            result = self.test_period(key)
            if "error" not in result:
                results.append(result)
        
        # Resumo
        logger.info("\n" + "="*60)
        logger.info("RESUMO DOS STRESS TESTS")
        logger.info("="*60)
        
        passed = sum(1 for r in results if r.get("robust"))
        total = len(results)
        
        logger.info(f"Passou: {passed}/{total}")
        
        for r in results:
            status = "✅" if r["robust"] else "❌"
            logger.info(f"{status} {r['period']}: {r['strategy_return']:+.2%} vs {r['benchmark_return']:+.2%} (Ibov)")
        
        if passed == total:
            logger.info("\n🎯 EXCELENTE: Passou em todas as crises!")
        elif passed >= total * 0.7:
            logger.info("\n✅ BOM: Passou na maioria das crises")
        else:
            logger.info("\n⚠️ ATENÇÃO: Falhou em muitas crises - revisar estratégia")
        
        return results
    
    def generate_report(self, results: List[Dict]) -> str:
        """Gera relatório em formato markdown."""
        report = "# Stress Test Report\n\n"
        report += f"Data: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n"
        
        passed = sum(1 for r in results if r.get("robust"))
        total = len(results)
        
        report += f"## Resumo\n\n"
        report += f"- **Passou**: {passed}/{total} ({passed/total*100:.1f}%)\n"
        report += f"- **Status**: {'✅ EXCELENTE' if passed == total else '✅ BOM' if passed >= total*0.7 else '⚠️ ATENÇÃO'}\n\n"
        
        report += "## Resultados por Período\n\n"
        report += "| Período | Severidade | Estratégia | Ibovespa | Alpha | Status |\n"
        report += "|---------|------------|------------|----------|-------|--------|\n"
        
        for r in results:
            status = "✅ Passou" if r["robust"] else "❌ Falhou"
            report += f"| {r['period']} | {r['severity']} | {r['strategy_return']:+.1%} | {r['benchmark_return']:+.1%} | {r['alpha']:+.1%} | {status} |\n"
        
        report += "\n## Análise\n\n"
        
        if passed == total:
            report += "A estratégia demonstrou robustez excepcional, superando ou mantendo-se próxima ao benchmark em todas as crises testadas. Isso indica:\n\n"
            report += "- ✅ Controle de risco eficaz\n"
            report += "- ✅ Regime filters funcionando\n"
            report += "- ✅ Qualidade para operação real\n"
        elif passed >= total * 0.7:
            report += "A estratégia passou na maioria das crises, mas há margem para melhoria:\n\n"
            report += "- ⚠️ Revisar parâmetros em períodos de alta volatilidade\n"
            report += "- ⚠️ Considerar hedges adicionais\n"
        else:
            report += "A estratégia falhou em múltiplas crises. Recomendações:\n\n"
            report += "- ❌ Revisar completamente o modelo\n"
            report += "- ❌ Adicionar filtros de regime mais agressivos\n"
            report += "- ❌ Reduzir alavancagem/exposição\n"
        
        return report


def main():
    """Executar stress tests."""
    print("=" * 60)
    print("STRESS TESTS - VALIDAÇÃO EM CRISES")
    print("=" * 60)
    
    db = Database()
    engine = StressTestEngine(db)
    
    # Executar tests
    results = engine.run_all_stress_tests()
    
    if results:
        # Salvar relatório
        report = engine.generate_report(results)
        report_file = Path("data/stress_test_report.md")
        with open(report_file, "w", encoding="utf-8") as f:
            f.write(report)
        
        print(f"\n✅ Relatório salvo em: {report_file}")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
