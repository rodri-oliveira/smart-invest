# Modelo Macro v1.0 -- Brasil

## Motor de Regime de Mercado

Objetivo: Classificar o ambiente de mercado brasileiro em: - RISK ON -
RISK OFF - TRANSIÇÃO

O modelo é determinístico, baseado em score ponderado.

------------------------------------------------------------------------

# Estrutura Geral do Modelo

Cada variável macro recebe:

-   Direção (positiva ou negativa para risco)
-   Peso
-   Pontuação (-2 a +2)

Score Final = Soma(Variável \* Peso)

Classificação:

-   Score ≥ +4 → RISK ON
-   Score ≤ -4 → RISK OFF
-   Entre -3 e +3 → TRANSIÇÃO

------------------------------------------------------------------------

# Variáveis do Modelo

## 1. Tendência da Selic

Métrica: - Média móvel curta (ex: 3 meses) vs média longa (ex: 12 meses)

Impacto: - Juros subindo → negativo para risco - Juros caindo → positivo
para risco

Pontuação: - Forte queda → +2 - Queda leve → +1 - Estável → 0 - Alta
leve → -1 - Forte alta → -2

Peso: 2

------------------------------------------------------------------------

## 2. Inflação (IPCA) Tendência

Métrica: - Últimos 6 meses vs 12 meses

Impacto: - Inflação caindo → favorece risco - Inflação subindo →
penaliza risco

Pontuação: - Forte queda → +2 - Queda leve → +1 - Estável → 0 - Alta
leve → -1 - Forte alta → -2

Peso: 1.5

------------------------------------------------------------------------

## 3. Curva de Juros (Inclinação)

Métrica: - Diferença entre juros longos (10 anos) e curtos (2 anos)

Impacto: - Curva inclinada positivamente → crescimento → positivo -
Curva invertida → risco de desaceleração → negativo

Pontuação: - Muito inclinada → +2 - Levemente inclinada → +1 - Neutra →
0 - Levemente invertida → -1 - Fortemente invertida → -2

Peso: 2

------------------------------------------------------------------------

## 4. Tendência do Ibovespa

Métrica: - Preço vs média móvel 200 dias

Impacto: - Acima da MM200 → tendência positiva - Abaixo da MM200 →
tendência negativa

Pontuação: - Muito acima → +2 - Acima → +1 - Próximo → 0 - Abaixo → -1 -
Muito abaixo → -2

Peso: 2

------------------------------------------------------------------------

## 5. Tendência do Dólar (USD/BRL)

Impacto: - Dólar subindo forte → estresse → negativo para risco - Dólar
estável ou caindo → positivo

Pontuação: - Forte queda → +2 - Queda leve → +1 - Estável → 0 - Alta
leve → -1 - Forte alta → -2

Peso: 1.5

------------------------------------------------------------------------

# Cálculo Final

Score Final =

(Selic \* 2) + (Inflação \* 1.5) + (Curva de Juros \* 2) + (Ibovespa \*
2) + (Dólar \* 1.5)

Score máximo possível: +18 Score mínimo possível: -18

------------------------------------------------------------------------

# Interpretação Estratégica

## RISK ON

-   Aumentar exposição em renda variável
-   Permitir maior concentração
-   Reduzir caixa

## TRANSIÇÃO

-   Exposição moderada
-   Seleção criteriosa de ativos
-   Evitar alavancagem

## RISK OFF

-   Priorizar renda fixa
-   Reduzir volatilidade
-   Aumentar caixa

------------------------------------------------------------------------

# Próxima Etapa

Desenvolver:

-   Estrutura de coleta automática dessas variáveis
-   Função de cálculo do score
-   Output estruturado para o Motor de Alocação
