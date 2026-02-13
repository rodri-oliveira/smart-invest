# AIM -- Próxima Fase: Execução do MVP Quantitativo

## Contexto Atual

Neste ponto do projeto, já foram definidos:

-   Visão estratégica do produto
-   Arquitetura técnica do sistema
-   Estrutura modular do motor quantitativo
-   Filosofia de construção (provar → refinar → escalar)

O próximo passo não é mais conceitual, e sim **execução prática**.

------------------------------------------------------------------------

## Objetivo da Fase Atual

Construir o **Core Quantitativo v0.1**, um MVP funcional capaz de:

1.  Coletar dados reais de mercado
2.  Calcular indicadores básicos
3.  Classificar o regime de mercado
4.  Gerar ranking de ativos
5.  Montar uma carteira simples
6.  Rodar backtests históricos
7.  Comparar performance com benchmark (Ibovespa)

Mesmo simples, o sistema deve ser **executável, mensurável e
validável**.

------------------------------------------------------------------------

## Ordem de Implementação Recomendada

### 1. Data Layer (Prioridade Máxima)

Sem dados confiáveis, o sistema não existe.

Implementações: - Ingestão de dados históricos (ações + índice) -
Persistência local (SQLite) - Função padrão de acesso aos dados

Entrega esperada: - Banco de dados populado - Função `get_prices()`
funcional

------------------------------------------------------------------------

### 2. Feature Engineering

Indicadores iniciais:

-   Momentum de 6 meses
-   Volatilidade rolling de 63 dias

Características: - Funções puras - Totalmente testáveis - Sem
dependência de estado

------------------------------------------------------------------------

### 3. Classificação de Regime (Determinística)

Regra simples:

-   Ibovespa acima da média móvel de 200 dias → Risk On
-   Ibovespa abaixo da média móvel de 200 dias → Risk Off

Sem Machine Learning nesta fase.

------------------------------------------------------------------------

### 4. Score Engine

Modelo inicial:

Score Final = - (0.7 × Momentum normalizado) - (0.3 × Volatilidade
normalizada)

Objetivo: - Rankear ativos de forma consistente

------------------------------------------------------------------------

### 5. Allocation Engine

Regras do MVP:

-   Selecionar Top 5 ativos
-   Pesos iguais
-   Rebalanceamento mensal

------------------------------------------------------------------------

### 6. Backtester

Simulação histórica:

-   Janela: últimos 10 anos
-   Frequência: mensal
-   Métricas:
    -   CAGR
    -   Sharpe Ratio
    -   Max Drawdown
    -   Comparação com Ibovespa

------------------------------------------------------------------------

## Justificativa Estratégica

-   Documentação não gera alpha
-   Código executável gera aprendizado
-   Backtest gera vantagem competitiva

Esta fase valida se o modelo **merece ser refinado**.

------------------------------------------------------------------------

## Decisões Estratégicas Abertas

Próximo passo de implementação:

A)  Criar o esqueleto completo do projeto em Python\
B)  Implementar diretamente o Data Layer\
C)  Começar pelo Backtester

Recomendação arquitetural: ➡️ **Começar pelo Data Layer**

------------------------------------------------------------------------

## Encerramento da Fase

Esta etapa encerra o planejamento macro e inicia a fase de execução
técnica.

Próxima retomada: Implementação prática do Core Quantitativo v0.1.
