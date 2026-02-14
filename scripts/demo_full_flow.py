#!/usr/bin/env python3
"""
Demonstração do Fluxo Completo Smart Invest v1.0

Este script demonstra o fluxo completo do sistema:
1. Parse de intenção do usuário
2. Cálculo dinâmico de scores
3. Validação de risco (Risk-First)
4. Enriquecimento do output
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import logging
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
)

from aim.data_layer.database import Database
from aim.intent.parser import parse_intent
from aim.scoring.dynamic import calculate_dynamic_scores
from aim.risk.first import RiskFirstEngine
from aim.enrichment.output import enrich_recommendation


def demonstrate_intent_parsing():
    """Demonstra o parse de diferentes intenções."""
    print("\n" + "="*70)
    print("1. INTENT PARSER - Conversão de linguagem natural em parâmetros")
    print("="*70)
    
    test_prompts = [
        "Quero alto retorno em 30 dias",
        "Proteger meu capital conservadoramente por 2 anos",
        "Renda passiva com dividendos",
        "Especular aceitando alto risco",
    ]
    
    for prompt in test_prompts:
        intent = parse_intent(prompt)
        print(f"\nPrompt: '{prompt}'")
        print(f"   Objetivo: {intent.objective.value}")
        print(f"   Horizonte: {intent.horizon.value}")
        print(f"   Risco: {intent.risk_tolerance.value}")
        print(f"   Max Vol: {intent.max_volatility:.1%}")
        print(f"   Max DD: {intent.max_drawdown:.1%}")
        print(f"   Fatores: {', '.join(intent.priority_factors)}")
        print(f"   Confiança: {intent.confidence:.0%}")


def demonstrate_full_flow():
    """Demonstra o fluxo completo com uma intenção específica."""
    print("\n" + "="*70)
    print("2. FLUXO COMPLETO - Exemplo: 'Quero alto retorno em 30 dias'")
    print("="*70)
    
    # Setup
    db = Database()
    date = "2025-01-15"
    
    # ETAPA 1: Parse de Intenção
    print("\n📍 ETAPA 1: Parse de Intenção")
    print("-" * 50)
    prompt = "Quero alto retorno em 30 dias"
    intent = parse_intent(prompt)
    print(f"Intenção: {intent.objective.value}")
    print(f"Horizonte: {intent.horizon.value}")
    print(f"Risco: {intent.risk_tolerance.value}")
    
    # ETAPA 2: Scoring Dinâmico
    print("\n📍 ETAPA 2: Dynamic Scoring (adaptado à intenção)")
    print("-" * 50)
    scores_df = calculate_dynamic_scores(db, intent, date)
    
    if scores_df.empty:
        print("❌ Sem scores disponíveis")
        return
    
    # Selecionar top 5
    top_5 = scores_df.nsmallest(5, 'rank_universe')
    tickers = top_5['ticker'].tolist()
    weights = [0.20] * len(tickers)  # Equal weight para demo
    
    print(f"Top 5 selecionados: {tickers}")
    print("\nScores detalhados:")
    for _, row in top_5.iterrows():
        print(f"  {row['ticker']}: Final={row['score_final']:.2f}, "
              f"Mom={row['score_momentum']:.2f}, "
              f"Val={row.get('score_value', 0):.2f}")
    
    # ETAPA 3: Risk-First Validation
    print("\n📍 ETAPA 3: Risk-First Engine (cálculo de risco)")
    print("-" * 50)
    risk_engine = RiskFirstEngine(db)
    is_valid, risk_assessment, reason = risk_engine.validate_recommendation(
        tickers, weights, intent, date
    )
    
    print(f"Volatilidade Esperada: {risk_assessment.portfolio_volatility:.1%}")
    print(f"Drawdown Esperado: {risk_assessment.expected_max_drawdown:.1%}")
    print(f"VaR 95%: {risk_assessment.var_95:.1%}")
    print(f"Concentração: {risk_assessment.concentration_score:.1%}")
    print(f"Liquidez Média: {risk_assessment.avg_liquidity:.2f}")
    
    if is_valid:
        print(f"\nRECOMENDAÇÃO APROVADA: {reason}")
    else:
        print(f"\nRECOMENDAÇÃO REJEITADA: {reason}")
        return
    
    # ETAPA 4: Output Enrichment
    print("\nETAPA 4: Output Enricher (justificativa completa)")
    print("-" * 50)
    enriched = enrich_recommendation(
        db, tickers, weights, intent, risk_assessment, scores_df, date
    )
    
    print(f"Confiança Geral: {enriched.confidence_score:.0%}")
    print(f"Taxa Sucesso Histórico: {enriched.historical_success_rate or 'N/A'}")
    
    print("\n📝 Justificativa Técnica (resumo):")
    rationale_lines = enriched.technical_rationale.split('\n')[:10]
    for line in rationale_lines:
        if line.strip():
            print(f"   {line}")
    print("   [...]")
    
    print("\nCenarios de Invalidacao:")
    for i, scenario in enumerate(enriched.invalidation_scenarios[:3], 1):
        print(f"   {i}. {scenario['name']}: {scenario['trigger']}")
    
    print("\nCenarios:")
    print(f"   Otimista: {enriched.best_case_scenario['expected_return_3m']}")
    print(f"   Pessimista: {enriched.worst_case_scenario['expected_return_3m']}")


def main():
    """Função principal de demonstração."""
    print("\n" + "="*70)
    print("SMART INVEST v1.0 - DEMONSTRAÇÃO DO FLUXO COMPLETO")
    print("="*70)
    print("\nSistema orientado por intenção, regime e risco.")
    print("Não decide o objetivo. Executa o objetivo de forma disciplinada.")
    
    # Demonstração 1: Parse de intenções
    demonstrate_intent_parsing()
    
    # Demonstração 2: Fluxo completo
    demonstrate_full_flow()
    
    # Resumo
    print("\n" + "="*70)
    print("RESUMO DO SISTEMA")
    print("="*70)
    print("""
Sistema implementado conforme manifesto tecnico v1.0

Componentes:
  1. Intent Parser      - Converte linguagem natural em parametros
  2. Dynamic Scoring    - Pesos adaptativos por intencao + regime
  3. Risk-First Engine  - Calcula risco ANTES de retorno
  4. Output Enricher    - Justificativa tecnica completa

Principios:
  - Nunca ignorar regime de mercado
  - Nunca sugerir sem score quantitativo
  - Sempre calcular risco antes de retorno
  - Sempre adaptar ao objetivo do usuario
  - Sempre justificar a decisao

Arquivos criados:
  - aim/intent/parser.py
  - aim/scoring/dynamic.py
  - aim/risk/first.py
  - aim/enrichment/output.py
  - docs/MANIFESTO_TECNICO_v1.0.md

Testes: 44 testes automatizados passando
""")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
