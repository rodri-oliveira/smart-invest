# AIM v1.0 -- Arquitetura Técnica do Motor Quantitativo

## Visão Geral

Este documento define a arquitetura técnica do núcleo determinístico do
sistema AIM. O objetivo é construir um motor quantitativo modular,
testável, escalável e preparado para backtesting robusto.

------------------------------------------------------------------------

# Stack Tecnológica Recomendada

## Linguagem

Python 3.11+

## Bibliotecas Principais

-   pandas → manipulação de dados
-   numpy → cálculos numéricos
-   scipy → métricas estatísticas
-   scikit-learn → modelos auxiliares (regime detection futuro)
-   statsmodels → análises estatísticas
-   yfinance / integração B3 (inicialmente)
-   matplotlib → visualizações de backtest

## Banco de Dados

Fase inicial: - SQLite (simples e leve)

Fase escalável: - PostgreSQL

------------------------------------------------------------------------

# Arquitetura Modular

aim/

├── data/ │ ├── ingestion.py │ ├── loaders.py │ └── database.py │ ├──
features/ │ ├── momentum.py │ ├── volatility.py │ ├── liquidity.py │ └──
macro.py │ ├── regime/ │ ├── regime_classifier.py │ └── regime_rules.py
│ ├── scoring/ │ └── scoring_engine.py │ ├── risk/ │ ├── risk_engine.py
│ └── position_sizing.py │ ├── allocation/ │ └── allocation_engine.py │
├── backtest/ │ ├── backtester.py │ └── metrics.py │ ├── config/ │ └──
parameters.py │ └── main.py

------------------------------------------------------------------------

# Fluxo de Execução do Sistema

1.  Ingestão de Dados
    -   Baixar preços históricos
    -   Atualizar base local
2.  Feature Engineering
    -   Calcular momentum (3m, 6m, 12m)
    -   Calcular volatilidade (desvio padrão rolling)
    -   Liquidez média
    -   Indicadores macro
3.  Classificação de Regime
    -   Regras determinísticas baseadas em:
        -   Tendência do Ibovespa
        -   Volatilidade implícita
        -   Curva de juros
4.  Cálculo de Score Score final = (Peso_Momentum ×
    Momentum_Normalizado)
    -   (Peso_Volatilidade × Vol_Normalizada)
    -   (Peso_Liquidez × Liquidez_Normalizada)
5.  Engine de Risco
    -   Ajustar exposição por regime
    -   Definir limites por ativo
    -   Aplicar controle de drawdown
6.  Alocação Final
    -   Ranking dos ativos
    -   Distribuição proporcional ao score
    -   Aplicação de teto máximo por ativo
7.  Backtest (modo simulação)
    -   Executar ciclo histórico
    -   Calcular:
        -   Retorno acumulado
        -   Sharpe
        -   Sortino
        -   Max Drawdown
        -   Alpha vs Ibovespa

------------------------------------------------------------------------

# Modelo de Dados Base

Tabela: prices - date - ticker - open - high - low - close - volume

Tabela: macro - date - selic - usdbrl - ibov_close - curva_juros_10y

Tabela: signals - date - ticker - momentum_score - volatility_score -
liquidity_score - final_score - regime - suggested_weight

------------------------------------------------------------------------

# Primeira Versão Funcional (MVP Quant)

Escopo reduzido para validação inicial:

-   Universo: Top 30 ações do Ibovespa
-   Indicadores:
    -   Momentum 6 meses
    -   Volatilidade 3 meses
-   Regime simples:
    -   Ibovespa acima da média de 200 dias = Risk On
    -   Abaixo = Risk Off
-   Alocação:
    -   Top 5 ativos
    -   Peso igual
-   Backtest: últimos 10 anos

Objetivo do MVP: Validar capacidade de superar o Ibovespa com controle
de drawdown.

------------------------------------------------------------------------

# Critérios de Qualidade Técnica

-   Código modular
-   Funções puras quando possível
-   Separação entre cálculo e execução
-   Parâmetros centralizados em config
-   Backtest reproduzível

------------------------------------------------------------------------

# Próxima Etapa Após Implementação

1.  Rodar backtests históricos
2.  Avaliar estabilidade do alpha
3.  Ajustar pesos com validação fora da amostra
4.  Preparar API interna
5.  Somente então construir camada de IA explicativa

------------------------------------------------------------------------

# Filosofia de Construção

Primeiro provar que funciona. Depois tornar elegante. Depois escalar.
