"""Risk-First Engine - Calcula risco antes de retorno.

Princípio fundamental: Risco é calculado primeiro. Se risco > limite, não há recomendação.
"""

import logging
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta

import pandas as pd
import numpy as np

from aim.data_layer.database import Database
from aim.intent.parser import InvestmentIntent

logger = logging.getLogger(__name__)


@dataclass
class RiskAssessment:
    """Avaliação de risco de uma carteira ou ativo."""
    
    # Métricas de risco
    portfolio_volatility: float       # Volatilidade anualizada esperada
    expected_max_drawdown: float     # Drawdown máximo esperado (estimado)
    var_95: float                    # Value at Risk 95%
    var_99: float                    # Value at Risk 99%
    
    # Concentração
    concentration_score: float       # 0-1, maior = mais concentrado
    top_5_weight: float             # Peso dos top 5 ativos
    
    # Qualidade da carteira
    avg_liquidity: float             # Liquidez média
    avg_quality: float               # Score de qualidade médio
    
    # Status
    within_risk_limits: bool         # Dentro dos limites da intenção?
    risk_warnings: List[str]        # Avisos de risco
    
    # Detalhes
    asset_contributions: Dict[str, float]  # Contribuição de cada ativo ao risco


class RiskFirstEngine:
    """
    Engine que prioriza cálculo de risco antes de otimização de retorno.
    
    Regra: Se risco > limite da intenção do usuário, não há recomendação válida.
    """
    
    # Multiplicadores para estimar max drawdown baseado em volatilidade
    DD_MULTIPLIERS = {
        'conservative': 1.5,   # Vol * 1.5
        'moderate': 2.0,         # Vol * 2.0
        'aggressive': 2.5,       # Vol * 2.5
        'speculative': 3.0,      # Vol * 3.0
    }
    
    def __init__(self, db: Database):
        self.db = db
    
    def assess_portfolio_risk(
        self,
        tickers: List[str],
        weights: List[float],
        intent: InvestmentIntent,
        date: Optional[str] = None,
    ) -> RiskAssessment:
        """
        Avalia risco de uma carteira proposta.
        
        Args:
            tickers: Lista de ativos
            weights: Pesos correspondentes
            intent: Intenção do usuário (com limites de risco)
            date: Data de análise
            
        Returns:
            RiskAssessment com métricas detalhadas
        """
        if date is None:
            date = datetime.now().strftime("%Y-%m-%d")
        
        logger.info(f"Avaliando risco de carteira com {len(tickers)} ativos")
        
        # 1. Buscar dados históricos
        price_data = self._get_historical_prices(tickers, date)
        
        # 2. Calcular métricas de risco
        portfolio_vol = self._calculate_portfolio_volatility(price_data, weights)
        
        # 3. Estimar max drawdown
        expected_dd = self._estimate_max_drawdown(
            portfolio_vol,
            intent.risk_tolerance.value
        )
        
        # 4. Calcular VaR
        var_95, var_99 = self._calculate_var(portfolio_vol, weights)
        
        # 5. Avaliar concentração
        concentration, top5_weight = self._calculate_concentration(weights)
        
        # 6. Avaliar qualidade média
        avg_liquidity, avg_quality = self._calculate_portfolio_quality(
            tickers, weights, date
        )
        
        # 7. Verificar limites da intenção
        within_limits, warnings = self._check_risk_limits(
            portfolio_vol=portfolio_vol,
            expected_dd=expected_dd,
            concentration=concentration,
            intent=intent,
        )
        
        # 8. Calcular contribuições individuais
        contributions = self._calculate_risk_contributions(price_data, weights)
        
        assessment = RiskAssessment(
            portfolio_volatility=portfolio_vol,
            expected_max_drawdown=expected_dd,
            var_95=var_95,
            var_99=var_99,
            concentration_score=concentration,
            top_5_weight=top5_weight,
            avg_liquidity=avg_liquidity,
            avg_quality=avg_quality,
            within_risk_limits=within_limits,
            risk_warnings=warnings,
            asset_contributions=contributions,
        )
        
        # Log do resultado
        self._log_risk_assessment(assessment, intent)
        
        return assessment
    
    def validate_recommendation(
        self,
        tickers: List[str],
        weights: List[float],
        intent: InvestmentIntent,
        date: Optional[str] = None,
    ) -> Tuple[bool, RiskAssessment, str]:
        """
        Valida se uma recomendação está dentro dos limites de risco.
        
        Args:
            tickers: Ativos recomendados
            weights: Pesos
            intent: Intenção do usuário
            date: Data
            
        Returns:
            (is_valid, risk_assessment, reason)
        """
        assessment = self.assess_portfolio_risk(tickers, weights, intent, date)
        
        if not assessment.within_risk_limits:
            reason = f"Risco excede limites: {', '.join(assessment.risk_warnings)}"
            logger.warning(f"❌ Recomendação REJEITADA - {reason}")
            return False, assessment, reason
        
        reason = "Risco dentro dos parâmetros aceitáveis"
        logger.info(f"✅ Recomendação APROVADA - {reason}")
        return True, assessment, reason
    
    def _get_historical_prices(
        self,
        tickers: List[str],
        end_date: str,
        lookback_days: int = 126,  # ~6 meses
    ) -> pd.DataFrame:
        """Busca preços históricos para cálculo de risco."""
        start_date = (
            datetime.strptime(end_date, "%Y-%m-%d") - timedelta(days=lookback_days)
        ).strftime("%Y-%m-%d")
        
        query = """
            SELECT ticker, date, close
            FROM prices
            WHERE ticker IN ({placeholders})
            AND date BETWEEN ? AND ?
            ORDER BY ticker, date
        """.format(placeholders=','.join(['?'] * len(tickers)))
        
        results = self.db.fetch_all(query, tuple(tickers) + (start_date, end_date))
        
        if not results:
            return pd.DataFrame()
        
        df = pd.DataFrame(results)
        return df.pivot(index='date', columns='ticker', values='close')
    
    def _calculate_portfolio_volatility(
        self,
        price_data: pd.DataFrame,
        weights: List[float],
    ) -> float:
        """Calcula volatilidade anualizada da carteira."""
        if price_data.empty:
            return 0.5  # Default alto se sem dados
        
        # Calcular retornos diários
        returns = price_data.pct_change().dropna()
        
        if returns.empty:
            return 0.5
        
        # Matriz de covariância
        cov_matrix = returns.cov()
        
        # Variância do portfólio
        weights_array = np.array(weights)
        portfolio_var = np.dot(weights_array.T, np.dot(cov_matrix, weights_array))
        
        # Volatilidade diária → anualizada
        portfolio_vol = np.sqrt(portfolio_var) * np.sqrt(252)
        
        return portfolio_vol
    
    def _estimate_max_drawdown(
        self,
        volatility: float,
        risk_tolerance: str,
    ) -> float:
        """Estima drawdown máximo esperado baseado em volatilidade."""
        multiplier = self.DD_MULTIPLIERS.get(risk_tolerance, 2.0)
        return volatility * multiplier
    
    def _calculate_var(
        self,
        portfolio_vol: float,
        weights: List[float],
    ) -> Tuple[float, float]:
        """Calcula Value at Risk (paramétrico)."""
        # Assumir retorno médio = 0 para simplificação
        # VaR = Z-score * volatilidade
        
        z_95 = 1.645  # 95% confidence
        z_99 = 2.326  # 99% confidence
        
        var_95 = z_95 * portfolio_vol
        var_99 = z_99 * portfolio_vol
        
        return var_95, var_99
    
    def _calculate_concentration(
        self,
        weights: List[float],
    ) -> Tuple[float, float]:
        """Calcula métricas de concentração."""
        weights_array = np.array(weights)
        
        # HHI (Herfindahl-Hirschman Index) normalizado
        hhi = np.sum(weights_array ** 2)
        concentration = hhi  # 0 a 1, onde 1 = totalmente concentrado
        
        # Peso top 5
        sorted_weights = np.sort(weights_array)[::-1]
        top_5_weight = np.sum(sorted_weights[:5])
        
        return concentration, top_5_weight
    
    def _calculate_portfolio_quality(
        self,
        tickers: List[str],
        weights: List[float],
        date: str,
    ) -> Tuple[float, float]:
        """Calcula qualidade média da carteira."""
        placeholders = ','.join(['?'] * len(tickers))
        query = f"""
            SELECT ticker, liquidity_score
            FROM features
            WHERE ticker IN ({placeholders})
            AND date <= ?
            ORDER BY date DESC
        """
        
        results = self.db.fetch_all(query, tuple(tickers) + (date,))
        
        if not results:
            return 0.5, 0.0
        
        # Calcular média ponderada
        liquidity_scores = {r['ticker']: r['liquidity_score'] for r in results}
        
        avg_liquidity = sum(
            liquidity_scores.get(t, 0.5) * w
            for t, w in zip(tickers, weights)
        )
        
        # Buscar qualidade se disponível
        query_quality = f"""
            SELECT ticker, p_l, roe
            FROM fundamentals
            WHERE ticker IN ({placeholders})
            AND reference_date <= ?
            ORDER BY reference_date DESC
        """
        
        quality_results = self.db.fetch_all(query_quality, tuple(tickers) + (date,))
        
        if quality_results:
            # Score simples de qualidade (ROE disponível = qualidade)
            quality_scores = {
                r['ticker']: 1.0 if r['roe'] is not None else 0.5
                for r in quality_results
            }
            avg_quality = sum(
                quality_scores.get(t, 0.5) * w
                for t, w in zip(tickers, weights)
            )
        else:
            avg_quality = 0.5
        
        return avg_liquidity, avg_quality
    
    def _check_risk_limits(
        self,
        portfolio_vol: float,
        expected_dd: float,
        concentration: float,
        intent: InvestmentIntent,
    ) -> Tuple[bool, List[str]]:
        """Verifica se risco está dentro dos limites da intenção."""
        warnings = []
        
        # Verificar volatilidade
        if portfolio_vol > intent.max_volatility * 1.2:  # Tolerância de 20%
            warnings.append(
                f"Volatilidade {portfolio_vol:.1%} excede limite {intent.max_volatility:.1%}"
            )
        
        # Verificar drawdown esperado
        if expected_dd > intent.max_drawdown * 1.2:
            warnings.append(
                f"Drawdown esperado {expected_dd:.1%} excede limite {intent.max_drawdown:.1%}"
            )
        
        # Verificar concentração
        if concentration > intent.max_concentration:
            warnings.append(
                f"Concentração {concentration:.1%} excede limite {intent.max_concentration:.1%}"
            )
        
        return len(warnings) == 0, warnings
    
    def _calculate_risk_contributions(
        self,
        price_data: pd.DataFrame,
        weights: List[float],
    ) -> Dict[str, float]:
        """Calcula contribuição de cada ativo ao risco total."""
        if price_data.empty:
            return {}
        
        returns = price_data.pct_change().dropna()
        cov_matrix = returns.cov()
        
        weights_array = np.array(weights)
        portfolio_var = np.dot(weights_array.T, np.dot(cov_matrix, weights_array))
        
        if portfolio_var == 0:
            return {t: 1.0 / len(weights) for t in price_data.columns}
        
        # Marginal contribution to risk
        marginal_contrib = np.dot(cov_matrix, weights_array)
        
        # Contribution to total risk
        contributions = weights_array * marginal_contrib / portfolio_var
        
        return dict(zip(price_data.columns, contributions))
    
    def _log_risk_assessment(
        self,
        assessment: RiskAssessment,
        intent: InvestmentIntent,
    ):
        """Loga resumo da avaliação de risco."""
        logger.info("=" * 50)
        logger.info("AVALIAÇÃO DE RISCO")
        logger.info("=" * 50)
        logger.info(f"Volatilidade Esperada: {assessment.portfolio_volatility:.1%}")
        logger.info(f"Drawdown Máx Esperado: {assessment.expected_max_drawdown:.1%}")
        logger.info(f"VaR 95%: {assessment.var_95:.1%}")
        logger.info(f"Concentração: {assessment.concentration_score:.1%}")
        logger.info(f"Top 5 Peso: {assessment.top_5_weight:.1%}")
        logger.info(f"Dentro dos Limites: {'✅ SIM' if assessment.within_risk_limits else '❌ NÃO'}")
        
        if assessment.risk_warnings:
            logger.warning("Avisos:")
            for warning in assessment.risk_warnings:
                logger.warning(f"  ⚠️ {warning}")
        
        # Comparar com limites da intenção
        logger.info("-" * 50)
        logger.info(f"Limite Volatilidade: {intent.max_volatility:.1%}")
        logger.info(f"Limite Drawdown: {intent.max_drawdown:.1%}")
        logger.info(f"Limite Concentração: {intent.max_concentration:.1%}")


def validate_portfolio_recommendation(
    db: Database,
    tickers: List[str],
    weights: List[float],
    intent: InvestmentIntent,
    date: Optional[str] = None,
) -> Tuple[bool, RiskAssessment, str]:
    """Função conveniência para validar recomendação."""
    engine = RiskFirstEngine(db)
    return engine.validate_recommendation(tickers, weights, intent, date)
