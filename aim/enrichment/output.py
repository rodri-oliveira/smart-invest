"""Output Enricher - Enriquece recomendação com justificativa técnica."""

import logging
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from datetime import datetime

import pandas as pd
import numpy as np

from aim.data_layer.database import Database
from aim.intent.parser import InvestmentIntent
from aim.risk.first import RiskAssessment

logger = logging.getLogger(__name__)


@dataclass
class EnrichedRecommendation:
    """Recomendação enriquecida com justificativa completa."""
    
    # Dados básicos
    tickers: List[str]
    weights: List[float]
    allocation_pct: List[float]  # Pesos em percentual
    
    # Justificativa técnica
    technical_rationale: str       # Explicação detalhada da lógica
    factor_breakdown: Dict[str, float]  # Contribuição de cada fator
    
    # Métricas de risco
    risk_assessment: RiskAssessment
    risk_summary: str              # Resumo em linguagem natural
    
    # Probabilidade histórica
    historical_success_rate: Optional[float]  # Taxa de sucesso histórica
    historical_avg_return: Optional[float]   # Retorno médio histórico
    historical_backtest_period: str         # Período do backtest
    
    # Cenários
    invalidation_scenarios: List[Dict[str, Any]]  # Quando invalidar a recomendação
    best_case_scenario: Dict[str, Any]           # Cenário otimista
    worst_case_scenario: Dict[str, Any]         # Cenário pessimista
    
    # Metadados
    timestamp: str
    confidence_score: float       # 0-1, confiança geral da recomendação
    
    def to_dict(self) -> Dict[str, Any]:
        """Converte para dicionário para serialização."""
        return {
            'tickers': self.tickers,
            'weights': self.weights,
            'allocation_pct': self.allocation_pct,
            'technical_rationale': self.technical_rationale,
            'factor_breakdown': self.factor_breakdown,
            'risk_summary': self.risk_summary,
            'historical_success_rate': self.historical_success_rate,
            'historical_avg_return': self.historical_avg_return,
            'invalidation_scenarios': self.invalidation_scenarios,
            'best_case_scenario': self.best_case_scenario,
            'worst_case_scenario': self.worst_case_scenario,
            'timestamp': self.timestamp,
            'confidence_score': self.confidence_score,
        }


class OutputEnricher:
    """
    Enriquece a saída do sistema com explicações completas.
    
    Princípio: Nunca entregar apenas "compre X". Sempre justificar.
    """
    
    def __init__(self, db: Database):
        self.db = db
    
    def enrich_recommendation(
        self,
        tickers: List[str],
        weights: List[float],
        intent: InvestmentIntent,
        risk_assessment: RiskAssessment,
        scores_df: pd.DataFrame,
        date: Optional[str] = None,
    ) -> EnrichedRecommendation:
        """
        Cria recomendação enriquecida com todas as informações.
        
        Args:
            tickers: Ativos selecionados
            weights: Pesos na carteira
            intent: Intenção do usuário
            risk_assessment: Avaliação de risco
            scores_df: DataFrame com scores calculados
            date: Data da recomendação
            
        Returns:
            EnrichedRecommendation completa
        """
        if date is None:
            date = datetime.now().strftime("%Y-%m-%d")
        
        logger.info("Enriquecendo recomendação...")
        
        # 1. Criar justificativa técnica
        rationale = self._create_technical_rationale(
            tickers, weights, intent, scores_df
        )
        
        # 2. Calcular breakdown de fatores
        factor_breakdown = self._calculate_factor_breakdown(
            tickers, weights, scores_df
        )
        
        # 3. Criar resumo de risco
        risk_summary = self._create_risk_summary(risk_assessment, intent)
        
        # 4. Buscar probabilidade histórica
        hist_success, hist_return, hist_period = self._calculate_historical_probability(
            tickers, weights, date
        )
        
        # 5. Criar cenários de invalidação
        invalidation = self._create_invalidation_scenarios(
            tickers, risk_assessment, intent
        )
        
        # 6. Criar cenários otimista/pessimista
        best_case = self._create_best_case_scenario(tickers, weights)
        worst_case = self._create_worst_case_scenario(tickers, weights, risk_assessment)
        
        # 7. Calcular confiança geral
        confidence = self._calculate_confidence(
            intent, risk_assessment, hist_success
        )
        
        return EnrichedRecommendation(
            tickers=tickers,
            weights=weights,
            allocation_pct=[w * 100 for w in weights],
            technical_rationale=rationale,
            factor_breakdown=factor_breakdown,
            risk_assessment=risk_assessment,
            risk_summary=risk_summary,
            historical_success_rate=hist_success,
            historical_avg_return=hist_return,
            historical_backtest_period=hist_period,
            invalidation_scenarios=invalidation,
            best_case_scenario=best_case,
            worst_case_scenario=worst_case,
            timestamp=date,
            confidence_score=confidence,
        )
    
    def _create_technical_rationale(
        self,
        tickers: List[str],
        weights: List[float],
        intent: InvestmentIntent,
        scores_df: pd.DataFrame,
    ) -> str:
        """Cria explicação técnica da recomendação."""
        lines = []
        
        # Introdução
        lines.append(f"RECOMENDAÇÃO BASEADA EM INTENÇÃO: {intent.objective.value.upper()}")
        lines.append("=" * 60)
        lines.append("")
        
        # Contexto
        lines.append(f"OBJETIVO DO INVESTIDOR:")
        lines.append(f"  - Tipo: {intent.objective.value}")
        lines.append(f"  - Horizonte: {intent.horizon.value}")
        lines.append(f"  - Tolerância ao risco: {intent.risk_tolerance.value}")
        lines.append(f"  - Limite de volatilidade: {intent.max_volatility:.1%}")
        lines.append(f"  - Limite de drawdown: {intent.max_drawdown:.1%}")
        lines.append("")
        
        # Alocação
        lines.append(f"ALOCAÇÃO SUGERIDA ({len(tickers)} ativos):")
        for ticker, weight in zip(tickers, weights):
            lines.append(f"  - {ticker}: {weight:.1%}")
        lines.append("")
        
        # Lógica de seleção
        lines.append("LÓGICA DE SELEÇÃO:")
        lines.append(f"  1. Filtro de liquidez mínima: {intent.min_liquidity:.0%}")
        lines.append(f"  2. Filtro de volatilidade máxima: {intent.max_volatility:.1%}")
        lines.append(f"  3. Scoring baseado em: {', '.join(intent.priority_factors)}")
        
        # Top ativos e porquê
        if not scores_df.empty:
            lines.append("")
            lines.append("TOP ATIVOS E RAZÕES:")
            
            for ticker in tickers[:5]:
                row = scores_df[scores_df['ticker'] == ticker]
                if not row.empty:
                    row = row.iloc[0]
                    lines.append(f"  {ticker}:")
                    lines.append(f"    - Score final: {row.get('score_final', 0):.2f}")
                    lines.append(f"    - Momentum: {row.get('score_momentum', 0):.2f}")
                    if 'score_value' in row:
                        lines.append(f"    - Valor: {row.get('score_value', 0):.2f}")
                    if 'score_quality' in row:
                        lines.append(f"    - Qualidade: {row.get('score_quality', 0):.2f}")
        
        lines.append("")
        lines.append("ADAPTAÇÃO AO REGIME:")
        lines.append(f"  - Pesos dos fatores ajustados para {intent.objective.value}")
        lines.append(f"  - Fatores prioritários: {', '.join(intent.priority_factors[:2])}")
        
        return "\n".join(lines)
    
    def _calculate_factor_breakdown(
        self,
        tickers: List[str],
        weights: List[float],
        scores_df: pd.DataFrame,
    ) -> Dict[str, float]:
        """Calcula contribuição de cada fator ao score da carteira."""
        breakdown = {
            'momentum': 0.0,
            'value': 0.0,
            'quality': 0.0,
            'volatility': 0.0,
            'liquidity': 0.0,
        }
        
        if scores_df.empty:
            return breakdown
        
        for ticker, weight in zip(tickers, weights):
            row = scores_df[scores_df['ticker'] == ticker]
            if not row.empty:
                row = row.iloc[0]
                breakdown['momentum'] += row.get('score_momentum', 0) * weight
                breakdown['value'] += row.get('score_value', 0) * weight
                breakdown['quality'] += row.get('score_quality', 0) * weight
                breakdown['volatility'] += row.get('score_volatility', 0) * weight
                breakdown['liquidity'] += row.get('score_liquidity', 0) * weight
        
        return breakdown
    
    def _create_risk_summary(
        self,
        risk_assessment: RiskAssessment,
        intent: InvestmentIntent,
    ) -> str:
        """Cria resumo de risco em linguagem natural."""
        lines = []
        
        lines.append("AVALIAÇÃO DE RISCO:")
        lines.append("")
        
        # Volatilidade
        vol_status = "✅ Aceitável" if risk_assessment.portfolio_volatility <= intent.max_volatility else "⚠️  Elevada"
        lines.append(f"  Volatilidade Esperada: {risk_assessment.portfolio_volatility:.1%} (Limite: {intent.max_volatility:.1%}) {vol_status}")
        
        # Drawdown
        dd_status = "✅ Aceitável" if risk_assessment.expected_max_drawdown <= intent.max_drawdown else "⚠️  Elevado"
        lines.append(f"  Drawdown Esperado: {risk_assessment.expected_max_drawdown:.1%} (Limite: {intent.max_drawdown:.1%}) {dd_status}")
        
        # VaR
        lines.append(f"  Value at Risk (95%): {risk_assessment.var_95:.1%}")
        lines.append(f"  Value at Risk (99%): {risk_assessment.var_99:.1%}")
        
        # Concentração
        lines.append(f"  Concentração: {risk_assessment.concentration_score:.1%}")
        lines.append(f"  Top 5 concentração: {risk_assessment.top_5_weight:.1%}")
        
        # Qualidade
        lines.append(f"  Liquidez Média: {risk_assessment.avg_liquidity:.2f}")
        lines.append(f"  Qualidade Média: {risk_assessment.avg_quality:.2f}")
        
        if risk_assessment.risk_warnings:
            lines.append("")
            lines.append("⚠️  AVISOS DE RISCO:")
            for warning in risk_assessment.risk_warnings:
                lines.append(f"    - {warning}")
        
        return "\n".join(lines)
    
    def _calculate_historical_probability(
        self,
        tickers: List[str],
        weights: List[float],
        date: str,
    ) -> Tuple[Optional[float], Optional[float], str]:
        """Busca probabilidade histórica de sucesso da estratégia."""
        try:
            # Buscar dados de backtest de carteiras similares
            # Simplificação: usar performance do último ano
            query = """
                SELECT 
                    AVG(total_return) as avg_return,
                    COUNT(*) as count,
                    SUM(CASE WHEN total_return > 0 THEN 1 ELSE 0 END) as positive_count
                FROM backtests
                WHERE end_date >= date('now', '-1 year')
            """
            
            result = self.db.fetch_one(query)
            
            if result and result['count'] > 0:
                success_rate = result['positive_count'] / result['count']
                avg_return = result['avg_return']
                period = "Último ano"
                return success_rate, avg_return, period
            
        except Exception as e:
            logger.warning(f"Não foi possível calcular probabilidade histórica: {e}")
        
        return None, None, "N/A"
    
    def _create_invalidation_scenarios(
        self,
        tickers: List[str],
        risk_assessment: RiskAssessment,
        intent: InvestmentIntent,
    ) -> List[Dict[str, Any]]:
        """Cria cenários que invalidariam a recomendação."""
        scenarios = []
        
        # Cenário 1: Risco excede limite
        scenarios.append({
            'name': 'Risco Excede Limite',
            'trigger': f'Volatilidade > {intent.max_volatility:.1%} ou Drawdown > {intent.max_drawdown:.1%}',
            'action': 'Rebalancear imediatamente ou sair das posições',
            'probability': 'Média',
        })
        
        # Cenário 2: Mudança de regime
        scenarios.append({
            'name': 'Mudança de Regime',
            'trigger': 'Mercado muda de BULL para BEAR ou alta volatilidade',
            'action': 'Reavaliar alocação e considerar redução de exposição',
            'probability': 'Baixa a Média',
        })
        
        # Cenário 3: Ação específica cai muito
        scenarios.append({
            'name': 'Queda Individual',
            'trigger': 'Qualquer ativo cai > 15% em relação ao ponto de entrada',
            'action': f"{'Stop loss ativado' if intent.use_stop_loss else 'Avaliar saída manual'}",
            'probability': 'Média',
        })
        
        # Cenário 4: Correlação aumenta
        scenarios.append({
            'name': 'Aumento de Correlação',
            'trigger': 'Correlação entre ativos aumenta > 0.8',
            'action': 'Diversificação comprometida - considerar novos ativos',
            'probability': 'Baixa',
        })
        
        return scenarios
    
    def _create_best_case_scenario(
        self,
        tickers: List[str],
        weights: List[float],
    ) -> Dict[str, Any]:
        """Cria cenário otimista."""
        return {
            'description': 'Mercado em tendência de alta, fundamentos melhoram',
            'expected_return_3m': '15-25%',
            'expected_return_12m': '30-50%',
            'probability': '20-30%',
            'conditions': [
                'Regime de mercado: BULL confirmado',
                'Momentum continua positivo',
                'Fundamentos melhores que esperado',
            ],
        }
    
    def _create_worst_case_scenario(
        self,
        tickers: List[str],
        weights: List[float],
        risk_assessment: RiskAssessment,
    ) -> Dict[str, Any]:
        """Cria cenário pessimista."""
        max_loss = min(risk_assessment.expected_max_drawdown * 100, 50)
        
        return {
            'description': 'Mercado em queda, aumento de volatilidade',
            'expected_return_3m': f'-{max_loss/2:.0f}% a -{max_loss:.0f}%',
            'expected_return_12m': f'Recuperação gradual',
            'probability': '15-25%',
            'conditions': [
                'Regime de mercado: BEAR',
                'Volatilidade > 30%',
                'Correlação aumenta (diversificação falha)',
            ],
        }
    
    def _calculate_confidence(
        self,
        intent: InvestmentIntent,
        risk_assessment: RiskAssessment,
        hist_success: Optional[float],
    ) -> float:
        """Calcula score de confiança geral da recomendação."""
        confidence = 0.5  # Base
        
        # +0.2 se risco dentro dos limites
        if risk_assessment.within_risk_limits:
            confidence += 0.2
        
        # +0.1 se confiança da intenção for alta
        if intent.confidence > 0.8:
            confidence += 0.1
        
        # +0.1 se tem dados históricos positivos
        if hist_success and hist_success > 0.6:
            confidence += 0.1
        
        # +0.1 se liquidez média é boa
        if risk_assessment.avg_liquidity > 0.7:
            confidence += 0.1
        
        return min(1.0, confidence)


def enrich_recommendation(
    db: Database,
    tickers: List[str],
    weights: List[float],
    intent: InvestmentIntent,
    risk_assessment: RiskAssessment,
    scores_df: pd.DataFrame,
    date: Optional[str] = None,
) -> EnrichedRecommendation:
    """Função conveniência para enriquecer recomendação."""
    enricher = OutputEnricher(db)
    return enricher.enrich_recommendation(
        tickers, weights, intent, risk_assessment, scores_df, date
    )
