#!/usr/bin/env python3
"""
Backtest Engine com Walk-Forward Analysis.
Valida estratégia em dados históricos reais.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import json

import numpy as np
import pandas as pd

from aim.data_layer.database import Database
from aim.features.engine import calculate_all_features
from aim.regime.engine import calculate_regime_for_date
from aim.scoring.engine import calculate_daily_scores

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class WalkForwardBacktest:
    """
    Backtest com walk-forward analysis.
    
    Simula operação real: treina em janela, testa em janela futura,
    depois avança no tempo.
    """
    
    def __init__(
        self,
        db: Database,
        train_window: int = 252,  # 1 ano
        test_window: int = 63,     # 3 meses
        top_n: int = 5,
        initial_capital: float = 100_000.0,
    ):
        self.db = db
        self.train_window = train_window
        self.test_window = test_window
        self.top_n = top_n
        self.initial_capital = initial_capital
        
    def get_available_dates(self) -> List[str]:
        """Retorna todas as datas disponíveis no banco."""
        query = """
            SELECT DISTINCT date 
            FROM prices 
            ORDER BY date ASC
        """
        results = self.db.fetch_all(query)
        return [r["date"] for r in results]
    
    def run_window(
        self,
        train_start: str,
        train_end: str,
        test_start: str,
        test_end: str,
    ) -> Dict:
        """
        Executa uma janela de backtest.
        
        Args:
            train_start/end: Período de treino (calibrar modelo)
            test_start/end: Período de teste (operar)
        
        Returns:
            Métricas da janela
        """
        logger.info(f"Janela: Treino {train_start} a {train_end}, Teste {test_start} a {test_end}")
        
        # 1. Calcular features para período de treino
        self._recalculate_features(train_start, train_end)
        
        # 2. Calcular scores (rebalanceamento no início do período de teste)
        scores_df = self._get_scores_for_date(test_start)
        
        if scores_df.empty:
            logger.warning("Sem scores disponíveis")
            return {"return": 0, "sharpe": 0, "max_dd": 0}
        
        # 3. Selecionar top N ativos
        top_assets = scores_df.nsmallest(self.top_n, "rank_universe")
        selected_tickers = top_assets["ticker"].tolist()
        
        logger.info(f"  Carteira: {selected_tickers}")
        
        # 4. Simular retornos no período de teste
        portfolio_value = self.initial_capital
        portfolio_values = [portfolio_value]
        
        for ticker in selected_tickers:
            weight = 1.0 / len(selected_tickers)
            
            # Buscar preços no período de teste
            query = """
                SELECT date, close
                FROM prices
                WHERE ticker = ?
                AND date BETWEEN ? AND ?
                ORDER BY date ASC
            """
            prices_df = self.db.query_to_df(query, (ticker, test_start, test_end))
            
            if not prices_df.empty and len(prices_df) > 1:
                initial_price = prices_df["close"].iloc[0]
                final_price = prices_df["close"].iloc[-1]
                ticker_return = (final_price / initial_price) - 1
                
                portfolio_value += portfolio_values[0] * weight * ticker_return
        
        period_return = (portfolio_value / self.initial_capital) - 1
        
        # 5. Calcular métricas
        metrics = {
            "train_start": train_start,
            "train_end": train_end,
            "test_start": test_start,
            "test_end": test_end,
            "selected_assets": selected_tickers,
            "initial_value": self.initial_capital,
            "final_value": portfolio_value,
            "return": period_return,
            "return_pct": period_return * 100,
        }
        
        logger.info(f"  Retorno: {period_return:+.2%}")
        
        return metrics
    
    def run_full_backtest(self) -> Dict:
        """
        Executa backtest completo com walk-forward.
        """
        dates = self.get_available_dates()
        
        if len(dates) < self.train_window + self.test_window:
            logger.error("Dados insuficientes para backtest")
            return {}
        
        logger.info(f"Iniciando backtest: {len(dates)} dias disponíveis")
        
        all_results = []
        
        # Avançar no tempo
        start_idx = self.train_window
        
        while start_idx + self.test_window < len(dates):
            train_start = dates[start_idx - self.train_window]
            train_end = dates[start_idx - 1]
            test_start = dates[start_idx]
            test_end = dates[min(start_idx + self.test_window - 1, len(dates) - 1)]
            
            result = self.run_window(train_start, train_end, test_start, test_end)
            all_results.append(result)
            
            # Avançar janela de teste
            start_idx += self.test_window
        
        # Calcular métricas agregadas
        if not all_results:
            return {}
        
        returns = [r["return"] for r in all_results if "return" in r]
        
        total_return = np.prod([1 + r for r in returns]) - 1
        avg_return = np.mean(returns)
        volatility = np.std(returns) * np.sqrt(252 / self.test_window)
        sharpe = avg_return / volatility if volatility > 0 else 0
        
        # Max drawdown
        cumulative = np.cumprod([1 + r for r in returns])
        running_max = np.maximum.accumulate(cumulative)
        drawdown = (cumulative - running_max) / running_max
        max_dd = abs(drawdown.min())
        
        summary = {
            "n_windows": len(all_results),
            "total_return": total_return,
            "avg_return_per_window": avg_return,
            "volatility": volatility,
            "sharpe_ratio": sharpe,
            "max_drawdown": max_dd,
            "calmar_ratio": avg_return / max_dd if max_dd > 0 else 0,
            "windows": all_results,
        }
        
        return summary
    
    def _recalculate_features(self, start_date: str, end_date: str):
        """Recalcula features para período."""
        # Simplificação: usar features existentes
        pass
    
    def _get_scores_for_date(self, date: str) -> pd.DataFrame:
        """Retorna scores calculados para uma data."""
        # Calcular scores com regime da data
        try:
            return calculate_daily_scores(self.db, date)
        except Exception as e:
            logger.warning(f"Erro ao calcular scores: {e}")
            return pd.DataFrame()


def main():
    """Executar backtest."""
    print("=" * 60)
    print("Backtest Walk-Forward Analysis")
    print("=" * 60)
    
    db = Database()
    
    # Verificar se há dados suficientes
    check = db.fetch_one("""
        SELECT COUNT(DISTINCT date) as n_dates, MIN(date) as start, MAX(date) as end
        FROM prices
    """)
    
    if not check or check["n_dates"] < 500:
        print("\n✗ Dados insuficientes!")
        print("Rode primeiro: python scripts/fetch_historical.py")
        return 1
    
    print(f"\nDados disponíveis:")
    print(f"  Período: {check['start']} a {check['end']}")
    print(f"  Dias: {check['n_dates']}")
    
    # Executar backtest
    backtest = WalkForwardBacktest(
        db,
        train_window=252,   # 1 ano
        test_window=63,    # 3 meses
        top_n=5,
        initial_capital=100_000.0,
    )
    
    print("\nExecutando backtest...")
    results = backtest.run_full_backtest()
    
    if not results:
        print("\n✗ Backtest falhou")
        return 1
    
    # Resultados
    print("\n" + "=" * 60)
    print("RESULTADOS DO BACKTEST")
    print("=" * 60)
    print(f"Janelas testadas: {results['n_windows']}")
    print(f"Retorno total: {results['total_return']:+.2%}")
    print(f"Retorno médio por janela: {results['avg_return_per_window']:+.2%}")
    print(f"Volatilidade: {results['volatility']:.2%}")
    print(f"Sharpe Ratio: {results['sharpe_ratio']:.2f}")
    print(f"Max Drawdown: {results['max_drawdown']:.2%}")
    print(f"Calmar Ratio: {results['calmar_ratio']:.2f}")
    print("=" * 60)
    
    # Salvar resultados
    output_file = Path("data/backtest_results.json")
    with open(output_file, "w") as f:
        json.dump(results, f, indent=2, default=str)
    
    print(f"\n✓ Resultados salvos em: {output_file}")
    
    # Verificação de qualidade
    print("\nAvaliação:")
    if results["sharpe_ratio"] > 0.8:
        print("  ✅ EXCELENTE: Sharpe > 0.8")
    elif results["sharpe_ratio"] > 0.5:
        print("  ✅ BOM: Sharpe > 0.5")
    else:
        print("  ⚠️  FRACO: Sharpe < 0.5")
    
    if results["max_drawdown"] < 0.20:
        print("  ✅ RISCO CONTROLADO: Max DD < 20%")
    elif results["max_drawdown"] < 0.30:
        print("  ⚠️  RISCO MODERADO: Max DD 20-30%")
    else:
        print("  ❌ RISCO ALTO: Max DD > 30%")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
