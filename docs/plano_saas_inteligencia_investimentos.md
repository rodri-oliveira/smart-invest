# SaaS de Inteligência Estratégica para Investimentos

## Visão do Produto

Sistema inteligente de decisão de investimentos com:

-   Motor quantitativo determinístico (cérebro real)
-   Camada conversacional com IA (interface inteligente)
-   Capacidade de gerar ordens práticas estruturadas

Objetivo: Analisar cenário + ativos e entregar recomendações claras com
justificativa técnica.

------------------------------------------------------------------------

# Arquitetura Conceitual

## Camada 0 -- Coleta de Dados

-   Dados macroeconômicos (juros, inflação, dólar, etc.)
-   Dados de mercado (preços, volume, histórico)
-   Dados fundamentalistas (lucro, dívida, dividendos)
-   Dados de renda fixa

Fontes via APIs confiáveis (gratuitas ou pagas).

------------------------------------------------------------------------

## Camada 1 -- Banco de Dados Estruturado

-   Base histórica própria
-   Tabelas normalizadas
-   Atualização automática diária
-   Independência de consulta direta em tempo real

------------------------------------------------------------------------

## Camada 2 -- Motor Quantitativo (Cérebro do Sistema)

### 2.1 Motor de Regime de Mercado

Define: - Risk ON - Risk OFF - Transição

Entrega: - Score de ambiente macro

------------------------------------------------------------------------

### 2.2 Motor de Score de Ativos

Para cada ativo calcula:

-   Valuation Score
-   Dividend Score
-   Qualidade Score
-   Tendência Score
-   Volatilidade Score

Entrega: - Score Final Ponderado

------------------------------------------------------------------------

### 2.3 Motor de Alocação

Considera: - Regime de mercado - Score do ativo - Risco - Modo
estratégico escolhido

Entrega: - Percentual sugerido de alocação

------------------------------------------------------------------------

### 2.4 Motor de Risco

Calcula: - Volatilidade - Correlação - Drawdown histórico - Exposição
máxima permitida

------------------------------------------------------------------------

## Camada 3 -- Gerador de Plano Estruturado

Entrega obrigatória:

-   Ativo recomendado
-   Percentual sugerido
-   Preço ideal
-   Horizonte de tempo
-   Stop sugerido
-   Tese estruturada
-   Grau de convicção
-   Cenário de invalidação

------------------------------------------------------------------------

## Camada 4 -- Camada Conversacional (IA)

Função: - Interpretar perguntas - Consultar os motores internos -
Explicar decisões - Permitir interação natural

Importante: A IA NÃO decide. O motor quantitativo decide.

------------------------------------------------------------------------

# Modos Estratégicos

O sistema terá múltiplos modos:

## Conservador

-   Foco em proteção de capital
-   Redução rápida de risco
-   Alta exigência de convicção

## Balanceado

-   Crescimento consistente
-   Ajuste dinâmico conforme cenário
-   Controle de risco estruturado

## Agressivo

-   Busca de alfa
-   Maior tolerância à volatilidade
-   Possibilidade de maior concentração

------------------------------------------------------------------------

# Ordem Correta de Desenvolvimento

## Fase 1 -- Definição Matemática do Motor

-   Variáveis
-   Pesos
-   Fórmulas
-   Critérios de decisão

## Fase 2 -- Construção do Motor Macro

## Fase 3 -- Construção do Score de Ativos

## Fase 4 -- Motor de Alocação

## Fase 5 -- Gerador de Plano Estruturado

## Fase 6 -- Integração com IA Conversacional

------------------------------------------------------------------------

# Stack Técnica Recomendada

Backend: Python\
Banco de Dados: PostgreSQL\
API: FastAPI\
Jobs: Scheduler diário\
Deploy: VPS ou Cloud leve\
IA: LLM via API integrada ao backend

------------------------------------------------------------------------

# Objetivo do MVP 1.0

-   Identificar regime de mercado
-   Classificar 10--20 ativos
-   Gerar recomendação objetiva
-   Entregar plano estruturado profissional
