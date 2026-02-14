# Smart Invest - Manifesto Técnico v1.0

## Definição do Produto

**Smart Invest** é um motor quantitativo adaptativo orientado por intenção, regime e risco.

> Ele não decide o objetivo. Ele executa o objetivo de forma disciplinada.

---

## 1. Arquitetura do Sistema

### 1.1 Fluxo Obrigatório de Decisão

```
┌─────────────────────────────────────────────────────────────┐
│  ETAPA 1: Análise de Cenário Macro                        │
│  ├── Classificar regime de mercado                          │
│  ├── Identificar nível de risco sistêmico                 │
│  └── Detectar tendência dominante                         │
│                                                             │
│  [SEM ISSO, NENHUMA RECOMENDAÇÃO É FEITA]                 │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│  ETAPA 2: Parser de Intenção                              │
│  ├── Converter prompt em parâmetros quantitativos         │
│  ├── Definir peso de risco permitido                      │
│  └── Estabelecer fatores prioritários                   │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│  ETAPA 3: Risk-First Engine                               │
│  ├── Calcular risco ANTES de retorno                      │
│  ├── Validar limites da intenção do usuário               │
│  └── Se risco > limite: REJEITAR recomendação           │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│  ETAPA 4: Modelo Quantitativo Dinâmico                    │
│  ├── Aplicar pesos adaptativos (intenção + regime)      │
│  ├── Calcular scores fatoriais                            │
│  └── Otimizar relação risco/retorno                       │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│  ETAPA 5: Output Enricher                                 │
│  ├── Gerar justificativa técnica completa                 │
│  ├── Calcular probabilidade histórica                     │
│  └── Criar cenários de invalidação                        │
└─────────────────────────────────────────────────────────────┘
```

---

## 2. Componentes Core

### 2.1 Intent Parser (`aim.intent.parser`)

**Responsabilidade:** Converter linguagem natural em parâmetros estruturados

**Inputs:**
- Prompt do usuário (ex: "Quero alto retorno em 30 dias")

**Outputs:**
- `InvestmentIntent` com:
  - `objective`: RETURN | PROTECTION | INCOME | SPECULATION | BALANCED
  - `horizon`: SHORT_TERM | MEDIUM_TERM | LONG_TERM
  - `risk_tolerance`: CONSERVATIVE | MODERATE | AGGRESSIVE | SPECULATIVE
  - `max_volatility`: Volatilidade máxima aceitável (0.10 a 0.50)
  - `max_drawdown`: Drawdown máximo aceitável (0.05 a 0.40)
  - `priority_factors`: Lista de fatores prioritários
  - `min_liquidity`: Score mínimo de liquidez
  - `confidence`: Confiança da interpretação (0-1)

**Regras de Negócio:**
- Se objetivo = RETURN + horizonte = SHORT → Volatilidade até 50%, stop loss obrigatório
- Se objetivo = PROTECTION → Qualidade > Momentum, volatilidade < 15%
- Se risco não explicitado → Inferir do objetivo

---

### 2.2 Dynamic Scoring Engine (`aim.scoring.dynamic`)

**Responsabilidade:** Calcular scores com pesos adaptativos

**Inputs:**
- `InvestmentIntent`
- Features técnicas (momentum, volatilidade, liquidez)
- Dados fundamentalistas (P/L, ROE, etc.)
- Regime de mercado atual

**Logic:**
```python
# Pesos base por objetivo
INTENT_WEIGHTS = {
    ObjectiveType.RETURN: {
        'momentum': 0.35, 'value': 0.20, 'quality': 0.15,
        'volatility': 0.15, 'liquidity': 0.15,
    },
    ObjectiveType.PROTECTION: {
        'momentum': 0.10, 'value': 0.25, 'quality': 0.35,
        'volatility': 0.10, 'liquidity': 0.20,
    },
    # ...
}

# Multiplicadores por tolerância de risco
RISK_MULTIPLIERS = {
    RiskTolerance.AGGRESSIVE: {
        'momentum': 1.3, 'value': 0.9, 'quality': 0.8,
        'volatility': 1.2, 'liquidity': 0.9,
    },
    # ...
}

# Ajustes por regime
REGIME_ADJUSTMENTS = {
    "BULL": {'momentum': 1.2, 'value': 0.9},
    "BEAR": {'momentum': 0.7, 'value': 1.1, 'quality': 1.2},
}
```

**Output:** DataFrame com scores individuais e score final ponderado

---

### 2.3 Risk-First Engine (`aim.risk.first`)

**Responsabilidade:** Calcular e validar risco ANTES de otimizar retorno

**Princípio Fundamental:**
> Risco é calculado primeiro. Se risco > limite da intenção, não há recomendação.

**Métricas Calculadas:**
- `portfolio_volatility`: Volatilidade anualizada esperada
- `expected_max_drawdown`: Estimado como vol * multiplicador (1.5 a 3.0)
- `var_95` / `var_99`: Value at Risk paramétrico
- `concentration_score`: Índice HHI normalizado
- `avg_liquidity` / `avg_quality`: Qualidade média da carteira

**Validação:**
```python
if portfolio_vol > intent.max_volatility * 1.2:
    REJEITAR("Volatilidade excede limite")

if expected_dd > intent.max_drawdown * 1.2:
    REJEITAR("Drawdown esperado excede limite")
```

---

### 2.4 Output Enricher (`aim.enrichment.output`)

**Responsabilidade:** Gerar output estruturado completo

**Output Obrigatório:**
```
┌─────────────────────────────────────────────────────────────┐
│  ALLOCATION                                                 │
│  ├── Ativos e pesos                                         │
│  └── Justificativa por ativo                              │
├─────────────────────────────────────────────────────────────┤
│  TECHNICAL RATIONALE                                        │
│  ├── Objetivo do usuário                                   │
│  ├── Fatores prioritários                                   │
│  └── Adaptação ao regime                                    │
├─────────────────────────────────────────────────────────────┤
│  RISK SUMMARY                                               │
│  ├── Volatilidade esperada vs limite                       │
│  ├── Drawdown esperado vs limite                           │
│  └── VaR 95% e 99%                                         │
├─────────────────────────────────────────────────────────────┤
│  HISTORICAL PROBABILITY                                     │
│  ├── Taxa de sucesso histórica                            │
│  └── Período de análise                                     │
├─────────────────────────────────────────────────────────────┤
│  INVALIDATION SCENARIOS                                     │
│  ├── Quando sair (risco, regime, queda individual)       │
│  └── Triggers específicos                                  │
├─────────────────────────────────────────────────────────────┤
│  SCENARIOS                                                  │
│  ├── Best case (20-30% probabilidade)                      │
│  └── Worst case (15-25% probabilidade)                     │
└─────────────────────────────────────────────────────────────┘
```

---

## 3. Princípios Obrigatórios

### 3.1 Nunca Ignorar Regime de Mercado
- Regime é classificado antes de qualquer recomendação
- Pesos dos fatores são ajustados pelo regime
- Transição de regime = maior cautela

### 3.2 Nunca Sugerir Ativo Sem Score Quantitativo
- Todo ativo recomendado deve ter score_final calculado
- Ranking no universo é obrigatório
- Justificativa técnica por ativo

### 3.3 Sempre Calcular Risco Antes de Retorno
- Risk-First Engine roda antes de otimização
- Se risco excede limites: REJEIÇÃO
- Não há exceções

### 3.4 Sempre Adaptar Modelo ao Objetivo do Usuário
- Pesos fixos são proibidos
- Cada intenção gera pesos diferentes
- Personalização é obrigatória

### 3.5 Sempre Justificar a Decisão
- Nunca entregar apenas "compre X"
- Justificativa técnica completa
- Cenários de invalidação claros

---

## 4. O que o Sistema NÃO Faz

| Proibição | Razão |
|-----------|-------|
| NÃO prever preço | Impossível prever futuro |
| NÃO agir por emoção/notícia isolada | Dados quantitativos apenas |
| NÃO operar sem controle de risco | Risk-First é obrigatório |
| NÃO fixar perfil padrão | Cada usuário é único |
| NÃO engessar estratégia | Adaptação contínua |

---

## 5. Estrutura de Dados

### 5.1 Banco de Dados (SQLite)

**Tabelas Principais:**
- `assets`: Universo de investimento
- `prices`: Preços históricos OHLCV
- `features`: Indicadores técnicos calculados
- `fundamentals`: Dados fundamentalistas
- `fundamentals` (atualizado): P/L, ROE, margens, etc.
- `signals`: Scores e rankings
- `backtests`: Resultados históricos

**Volume Atual:**
- 127,141 preços históricos
- 119,201 features calculadas
- 35 ativos com fundamentos
- Período: 2008-2024

### 5.2 APIs Externas

- **BRAPI**: Dados de mercado brasileiro (preços, fundamentos)
- **BCB**: Dados macroeconômicos (Selic, IPCA, CDI)

---

## 6. Testes e Validação

### 6.1 Testes Automatizados
- **44 testes** implementados
- Cobertura: Scoring, Features, Database
- Status: ✅ Todos passando

### 6.2 Backtest Walk-Forward
- Período: 2008-2024
- Janelas: 72 períodos de teste
- Retorno: +49.96%
- Sharpe: 0.06 (melhorar)
- Max DD: 60% (aceitável para beta)

### 6.3 Stress Tests
- 5 crises históricas testadas
- Resultado: 4/5 passaram
- Falha: COVID Crash (mercado caiu 50%)

---

## 7. Roadmap

### Concluído ✅
- [x] Sistema base com dados reais
- [x] Scoring multifatorial adaptativo
- [x] Regime detection
- [x] Stress tests
- [x] Testes automatizados (44)
- [x] Intent Parser
- [x] Dynamic Scoring
- [x] Risk-First Engine
- [x] Output Enricher

### Próximos Passos ⏳
- [ ] Popular dados macro (Selic, IPCA, CDI)
- [ ] Paper trading em tempo real
- [ ] Deploy em cloud (24/7)
- [ ] Melhorar Sharpe ratio (> 0.5)
- [ ] Reduzir Max DD (< 30%)

---

## 8. Contato e Repositório

- **Repositório**: https://github.com/rodri-oliveira/smart-invest
- **Versão**: 1.0.0
- **Data**: 2026-02-13

---

**Smart Invest - Disciplina Quantitativa Adaptativa**
