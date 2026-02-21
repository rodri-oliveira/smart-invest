# Arquitetura e Dados

Atualizado em: 2026-02-21

## Arquitetura de Alto Nivel

```
Client Layer (Next.js)
    |
API Layer (FastAPI)
    |
    ├── Routers: auth, recommendation, simulation, data-update, health
    ├── Middleware: CORS, error handling
    └── Models: Pydantic schemas
    |
Application Layer (aim/)
    |
    ├── intent/        → Parser de intencao (NLU sem LLM)
    ├── enrichment/    → Enriquecimento de dados para resposta
    ├── scoring/       → Motor de scoring multi-fator
    ├── regime/        → Classificador de regime de mercado
    ├── features/      → Calculo de momentum, volatilidade, qualidade, valor
    ├── risk/          → Gestao de risco, position sizing, stops
    ├── allocation/    → Alocacao e rebalanceamento
    ├── backtest/      → Motor de backtest
    ├── sentiment/     → Analise de sentimento
    ├── data_layer/    → Pipeline de ingestao + providers
    ├── auth/          → Autenticacao e multitenancy
    ├── security/      → Auditoria e rate limiting
    ├── config/        → Parametros, universo, settings
    └── utils/         → Utilitarios e helpers
    |
Data Layer
    |
    ├── SQLite (data/smart_invest.db)
    └── Providers: brapi.dev, BCB API, yfinance (fallback), stooq (pendente)
```

## Estrutura Real do Projeto

```
smart-invest/
├── aim/                    # Motor quantitativo (core)
│   ├── config/             # Parametros, universo, settings
│   ├── data_layer/         # Database, ingestao, cache, providers
│   │   └── providers/      # brapi, bcb, yfinance, stooq (WIP)
│   ├── features/           # Momentum, quality, value, volatility
│   ├── regime/             # Classificador de regime Risk ON/OFF
│   ├── scoring/            # Engine, factors, normalizer
│   ├── risk/               # Engine, position sizing, stops
│   ├── allocation/         # Engine de alocacao
│   ├── backtest/           # Engine de backtest
│   ├── intent/             # Parser de intencao NLU
│   ├── enrichment/         # Enriquecimento de respostas
│   ├── sentiment/          # Analise de sentimento
│   ├── auth/               # Autenticacao, JWT, multitenancy
│   ├── security/           # Auditoria, rate limit
│   ├── portfolio/          # Gestao de carteira
│   ├── execution/          # Orquestrador de pipeline
│   └── utils/              # Helpers
│
├── api/                    # FastAPI
│   ├── main.py             # Entry point
│   ├── middleware/          # CORS, error handling
│   ├── routers/            # Endpoints (auth, recommendation, simulation, etc)
│   └── models/             # Pydantic schemas
│
├── frontend/               # Next.js + React + TypeScript
│   ├── src/
│   │   ├── app/            # Pages e routing
│   │   ├── components/     # Componentes React
│   │   └── services/       # API client
│   └── e2e/                # Testes Playwright
│
├── scripts/                # Scripts utilitarios e pipeline
├── tests/                  # Testes backend (pytest)
├── data/                   # Banco SQLite + backups
├── docs/                   # Documentacao
└── notebooks/              # Jupyter notebooks de exploracao
```

## Stack Tecnologica

| Componente | Tecnologia | Justificativa |
|-----------|-----------|---------------|
| Backend | Python 3.11 + FastAPI | Ecosistema quant maduro + async + auto-docs |
| Validacao | Pydantic 2.0+ | Type safety + serialização |
| Processamento | pandas + numpy + scipy | Padrao para dados financeiros |
| Banco (atual) | SQLite | Zero config, portabilidade, single-user |
| Banco (futuro) | PostgreSQL | Concorrencia, replicacao, escala |
| Frontend | Next.js + React + TypeScript | SSR, routing, type safety |
| Testes backend | pytest | Padrao Python |
| Testes frontend | Playwright | E2E confiavel |
| Scheduler | APScheduler (interno) | Simples, integrado ao Python |

## Schema do Banco (Tabelas Principais)

### assets — Universo de ativos

```sql
CREATE TABLE assets (
    ticker VARCHAR(10) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    sector VARCHAR(100),
    segment VARCHAR(100),
    market_cap_category VARCHAR(20),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### prices — Precos historicos OHLCV

```sql
CREATE TABLE prices (
    ticker VARCHAR(10) NOT NULL,
    date DATE NOT NULL,
    open DECIMAL(12,4), high DECIMAL(12,4),
    low DECIMAL(12,4), close DECIMAL(12,4),
    volume BIGINT,
    adjusted_close DECIMAL(12,4),
    source VARCHAR(50),
    PRIMARY KEY (ticker, date),
    FOREIGN KEY (ticker) REFERENCES assets(ticker)
);
```

### fundamentals — Dados fundamentalistas

```sql
CREATE TABLE fundamentals (
    ticker VARCHAR(10) NOT NULL,
    reference_date DATE NOT NULL,
    report_type VARCHAR(10) NOT NULL,
    p_l DECIMAL(10,2), p_vp DECIMAL(10,2),
    dividend_yield DECIMAL(5,2), roe DECIMAL(5,2),
    margem_liquida DECIMAL(5,2), divida_patrimonio DECIMAL(10,2),
    lucro_liq BIGINT, receita_liq BIGINT, ebitda BIGINT,
    source VARCHAR(50),
    PRIMARY KEY (ticker, reference_date, report_type)
);
```

### macro_indicators — Indicadores macroeconomicos

```sql
CREATE TABLE macro_indicators (
    date DATE NOT NULL,
    indicator VARCHAR(50) NOT NULL,  -- SELIC, CDI, IPCA, USD_BRL, IBOVESPA, etc
    value DECIMAL(15,6),
    source VARCHAR(50),
    PRIMARY KEY (date, indicator)
);
```

### signals — Scores e ranking de ativos

```sql
CREATE TABLE signals (
    date DATE NOT NULL,
    ticker VARCHAR(10) NOT NULL,
    momentum_3m DECIMAL(10,4), momentum_6m DECIMAL(10,4), momentum_12m DECIMAL(10,4),
    vol_21d DECIMAL(10,4), vol_63d DECIMAL(10,4),
    score_momentum DECIMAL(5,2), score_quality DECIMAL(5,2),
    score_value DECIMAL(5,2), score_volatility DECIMAL(5,2),
    score_liquidity DECIMAL(5,2), score_final DECIMAL(5,2),
    rank_universe INTEGER,
    regime_at_date VARCHAR(20),
    PRIMARY KEY (date, ticker)
);
```

### regime_state — Regime de mercado diario

```sql
CREATE TABLE regime_state (
    date DATE PRIMARY KEY,
    regime VARCHAR(20) NOT NULL,  -- RISK_ON, RISK_OFF, TRANSITION, etc
    score_total DECIMAL(5,2),
    score_yield_curve DECIMAL(3,1), score_risk_spread DECIMAL(3,1),
    score_ibov_trend DECIMAL(3,1), score_capital_flow DECIMAL(3,1),
    score_liquidity DECIMAL(3,1)
);
```

### Tabelas de simulacao e autenticacao

- `users` — Usuarios com `tenant_id`, email, hash de senha.
- `simulated_positions` — Posicoes simuladas por `user_id + tenant_id + ticker`.
- `simulated_orders` — Historico de ordens simuladas.
- `simulated_alerts` — Alertas operacionais por usuario.
- `audit_events` — Trilha de auditoria (login, ordens, erros).

## Pipeline de Dados Diario

```
1. Coleta de precos de mercado (brapi.dev → yfinance fallback)
2. Coleta de indicadores macro (BCB API)
3. Validacao (precos positivos, volume > 0, continuidade)
4. Calculo de features (momentum, vol, liquidez)
5. Classificacao de regime (5 indicadores → score → Risk ON/OFF)
6. Scoring de ativos (z-score por fator → score final 0-10 → ranking)
7. Geracao de alertas
8. Backup do banco
```

## Fontes de Dados

| Prioridade | Fonte | Dados | Limite |
|-----------|-------|-------|--------|
| 1 | brapi.dev | OHLCV, fundamentos, dividendos | 100 req/dia (free) |
| 2 | BCB API | Selic, IPCA, cambio | Ilimitado |
| 3 | yfinance | Fallback OHLCV | Sem limite formal |
| 4 | Stooq | Fallback OHLCV (WIP) | A validar |

**Risco atual:** brapi.dev como fonte unica de precos. Stooq criado como base de fallback
(`aim/data_layer/providers/stooq.py`) mas ainda nao integrado ao pipeline.
