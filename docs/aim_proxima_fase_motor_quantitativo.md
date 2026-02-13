# AIM -- Próxima Fase Estratégica

## Decisão do Arquiteto: Construir Primeiro o Motor Quantitativo

------------------------------------------------------------------------

# Decisão Estratégica

A próxima fase ideal NÃO é interface, nem IA explicativa.

É a construção do:

# MOTOR QUANTITATIVO DETERMINÍSTICO (Core Engine)

Sem um núcleo sólido: - Não existe consistência - Não existe backtest
confiável - Não existe validação - Não existe vantagem competitiva

A IA entra depois --- para interpretação e comunicação.

------------------------------------------------------------------------

# Ordem Correta de Desenvolvimento

## Fase 1 --- Motor Quantitativo (CORE)

Objetivo: Criar o cérebro matemático do sistema.

Entregáveis:

1.  Estrutura de Dados de Mercado
    -   Preços históricos
    -   Volume
    -   Indicadores macro
    -   Taxa Selic
    -   Dólar
    -   Curva de juros
2.  Classificador de Regime de Mercado
    -   Risk On
    -   Risk Off
    -   Transição
3.  Motor de Score de Ativos
    -   Momentum
    -   Volatilidade
    -   Liquidez
    -   Força relativa
    -   Fatores fundamentais (fase posterior)
4.  Sistema de Alocação
    -   Peso proporcional ao score
    -   Controle de risco
    -   Limite por ativo
    -   Limite por setor
5.  Camada de Controle de Risco
    -   Stop técnico
    -   Stop por volatilidade
    -   Redução de exposição por regime
6.  Estrutura de Backtesting
    -   Simulação histórica
    -   Comparação com Ibovespa
    -   Métricas: Sharpe, Sortino, Max Drawdown

------------------------------------------------------------------------

## Fase 2 --- Validação Quantitativa

-   Testes em múltiplos ciclos de mercado
-   Stress tests
-   Teste fora da amostra
-   Otimização controlada

------------------------------------------------------------------------

## Fase 3 --- Camada de Inteligência (IA)

Somente depois do núcleo validado:

-   Explicação da tese
-   Geração de relatório estruturado
-   Comunicação amigável
-   Camada SaaS

------------------------------------------------------------------------

# Arquitetura Recomendada

Data Layer → Feature Engineering → Regime Detection → Scoring Engine →
Risk Engine → Allocation Engine → Backtest Engine → API Layer →
Interface / IA

------------------------------------------------------------------------

# Por Que Essa Ordem?

Porque:

-   Edge vem do modelo
-   Produto vem depois
-   Marketing vem por último

Construímos primeiro a máquina. Depois vestimos ela.

------------------------------------------------------------------------

# Próximo Passo Concreto

Desenhar:

## Estrutura Técnica do Motor Quantitativo v1.0

Com: - Stack recomendada - Estrutura de pastas - Modelagem de dados -
Fluxo de execução - Primeira versão funcional simplificada

Esse será o próximo documento.
