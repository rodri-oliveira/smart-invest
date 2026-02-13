# Smart Invest - Modelagem de Dados e Banco de Dados

## 1. Visão Geral da Modelagem

### 1.1 Princípios de Design

1. **Determinismo**: Mesmos inputs → mesmos outputs (reprodutibilidade)
2. **Auditabilidade**: Toda decisão pode ser rastreada aos dados brutos
3. **Eficiência**: Consultas rápidas para análise em tempo real
4. **Extensibilidade**: Fácil adicionar novos indicadores/fatores
5. **Integridade**: Constraints e validações em todos os níveis

### 1.2 Tipos de Dados

- **Dados de Mercado**: Preços, volume, OHLCV
- **Dados Fundamentalistas**: BP, DRE, DFC, indicadores
- **Dados Macroeconômicos**: Selic, IPCA, Dólar, curva de juros
- **Dados Calculados**: Scores, rankings, sinais
- **Dados de Execução**: Ordens simuladas/reais, backtests

---

## 2. Diagrama Entidade-Relacionamento (ER)

```
┌──────────────────┐     ┌──────────────────┐     ┌──────────────────┐
│     ASSETS       │     │    PRICES        │     │   FUNDAMENTALS   │
├──────────────────┤     ├──────────────────┤     ├──────────────────┤
│ PK ticker        │────<│ PK (ticker, date)│     │ PK (ticker,     │
│    name          │     │ FK ticker >──────┼───────│    date, type)  │
│    sector        │     │    open          │     │ FK ticker >──────┤
│    segment       │     │    high          │     │    p_l           │
│    market_cap    │     │    low           │     │    p_vp          │
│    created_at    │     │    close         │     │    dy            │
│    updated_at    │     │    volume        │     │    roe           │
└──────────────────┘     │    adjusted_close│     │    margem_liq    │
                         │    source        │     │    div_patrimonio│
                         └──────────────────┘     │    lucro_liq     │
                                                  │    receita       │
                                                  │    divida_total  │
                                                  │    patrimonio_liq│
                                                  │    ebitda        │
                                                  └──────────────────┘

┌──────────────────┐     ┌──────────────────┐     ┌──────────────────┐
│  MACRO_INDICATORS│     │    SIGNALS       │     │    PORTFOLIOS    │
├──────────────────┤     ├──────────────────┤     ├──────────────────┤
│ PK (date,        │     │ PK (date, ticker)│     │ PK portfolio_id  │
│    indicator)    │     │ FK ticker >──────┼──────┤    name          │
│    value         │     │    momentum_3m   │     │    strategy      │
│    source        │     │    momentum_6m   │     │    regime        │
│    created_at    │     │    momentum_12m  │     │    created_at    │
└──────────────────┘     │    vol_21d       │     │    updated_at    │
                         │    vol_63d       │     └──────────────────┘
                         │    score_momentum│               │
┌──────────────────┐     │    score_quality │               │
│   REGIME_STATE   │     │    score_value   │     ┌──────────────────┐
├──────────────────┤     │    score_vol     │     │ PORTFOLIO_HOLDINGS│
│ PK date          │     │    score_liquid  │     ├──────────────────┤
│    regime        │     │    score_final   │     │ PK (portfolio_id,│
│    score_total   │     │    rank_universe │     │    ticker, date) │
│    yield_curve   │     │    regime_at_date│     │ FK portfolio_id >─┤
│    risk_spread   │     │    created_at    │     │ FK ticker >──────┤
│    ibov_trend    │     └──────────────────┘     │    weight        │
│    capital_flow  │                               │    price_entry   │
│    liquidity     │     ┌──────────────────┐     │    stop_loss     │
│    created_at    │     │    BACKTESTS     │     │    target_price  │
└──────────────────┘     ├──────────────────┤     │    status        │
                         │ PK backtest_id   │     └──────────────────┘
                         │    name          │
                         │    strategy      │     ┌──────────────────┐
                         │    start_date    │     │     ORDERS       │
                         │    end_date      │     ├──────────────────┤
                         │    cagr          │     │ PK order_id      │
                         │    sharpe        │     │ FK portfolio_id >─┤
                         │    max_drawdown  │     │ FK ticker >──────┤
                         │    alpha         │     │    side          │
                         │    beta          │     │    quantity      │
                         │    win_rate      │     │    price         │
                         │    created_at    │     │    order_type    │
                         └──────────────────┘     │    status        │
                                                  │    executed_at │
                                                  │    created_at    │
                                                  └──────────────────┘
```

---

## 3. Modelo Lógico - Tabelas Detalhadas

### 3.1 assets (Universo de Ativos)

```sql
CREATE TABLE assets (
    ticker VARCHAR(10) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    sector VARCHAR(100),
    segment VARCHAR(100),
    market_cap_category VARCHAR(20), -- 'LARGE', 'MID', 'SMALL'
    is_index BOOLEAN DEFAULT FALSE,    -- TRUE para Ibovespa, etc.
    is_active BOOLEAN DEFAULT TRUE,
    listed_date DATE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Índices
CREATE INDEX idx_assets_sector ON assets(sector);
CREATE INDEX idx_assets_active ON assets(is_active);
```

**Descrição**: Cadastro mestre de todos os ativos do universo de investimento (ações, índices, ETFs). Mantém informações estáticas que raramente mudam.

**Dados iniciais**: Top 100 ações B3 + Ibovespa + alguns ETFs.

---

### 3.2 prices (Preços Históricos)

```sql
CREATE TABLE prices (
    ticker VARCHAR(10) NOT NULL,
    date DATE NOT NULL,
    open DECIMAL(12, 4),
    high DECIMAL(12, 4),
    low DECIMAL(12, 4),
    close DECIMAL(12, 4),
    volume BIGINT,
    adjusted_close DECIMAL(12, 4),  -- Ajustado por splits/dividendos
    source VARCHAR(50),             -- 'brapi', 'yfinance', 'manual'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    PRIMARY KEY (ticker, date),
    FOREIGN KEY (ticker) REFERENCES assets(ticker)
);

-- Índices
CREATE INDEX idx_prices_date ON prices(date);
CREATE INDEX idx_prices_ticker_date ON prices(ticker, date DESC);
```

**Descrição**: Série temporal de preços OHLCV para todos os ativos. Usa chave composta (ticker, date) para eficiência. O campo `adjusted_close` é crucial para cálculos de retorno precisos.

**Volume esperado**: ~100 ativos × 252 dias × 5 anos = 126.000 registros (crescendo)

---

### 3.3 fundamentals (Dados Fundamentalistas)

```sql
CREATE TABLE fundamentals (
    ticker VARCHAR(10) NOT NULL,
    reference_date DATE NOT NULL,    -- Data do balanço (trimestral/anual)
    report_type VARCHAR(10) NOT NULL, -- 'ANUAL', 'TRIMESTRAL'
    
    -- Valuation
    p_l DECIMAL(10, 2),
    p_vp DECIMAL(10, 2),
    dividend_yield DECIMAL(5, 2),    -- Percentual (ex: 8.50 = 8.5%)
    ev_ebitda DECIMAL(10, 2),
    
    -- Rentabilidade
    roe DECIMAL(5, 2),                -- Percentual
    roa DECIMAL(5, 2),
    roic DECIMAL(5, 2),
    margem_liquida DECIMAL(5, 2),    -- Percentual
    margem_ebitda DECIMAL(5, 2),
    
    -- Endividamento
    divida_patrimonio DECIMAL(10, 2),
    divida_ebitda DECIMAL(10, 2),
    
    -- Eficiência
    giro_ativo DECIMAL(10, 2),
    
    -- DRE Sintética
    receita_liq BIGINT,
    lucro_liq BIGINT,
    ebitda BIGINT,
    divida_total BIGINT,
    patrimonio_liq BIGINT,
    ativo_total BIGINT,
    
    -- Dividendos
    dividendos_pagos BIGINT,
    payout DECIMAL(5, 2),            -- Percentual
    
    source VARCHAR(50),              -- 'brapi', 'fundamentus'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    PRIMARY KEY (ticker, reference_date, report_type),
    FOREIGN KEY (ticker) REFERENCES assets(ticker)
);

-- Índices
CREATE INDEX idx_fundamentals_ticker_date ON fundamentals(ticker, reference_date DESC);
CREATE INDEX idx_fundamentals_p_l ON fundamentals(p_l) WHERE p_l > 0;
```

**Descrição**: Dados fundamentalistas dos demonstrativos contábeis. Chave composta inclui tipo de relatório (anual/trimestral) pois uma empresa pode ter múltiplos relatórios na mesma data.

---

### 3.4 macro_indicators (Indicadores Macroeconômicos)

```sql
CREATE TABLE macro_indicators (
    date DATE NOT NULL,
    indicator VARCHAR(50) NOT NULL,
    value DECIMAL(15, 6),
    unit VARCHAR(20),                -- 'percent', 'index', 'rate'
    frequency VARCHAR(20),           -- 'DAILY', 'MONTHLY'
    source VARCHAR(50),              -- 'BCB', 'IBGE', 'brapi'
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    PRIMARY KEY (date, indicator)
);

-- Índices
CREATE INDEX idx_macro_indicator_date ON macro_indicators(indicator, date DESC);
```

**Indicadores suportados**:
- `SELIC`: Taxa Selic meta (% ao ano)
- `CDI`: Taxa CDI acumulada (%)
- `IPCA`: Índice de inflação (%)
- `USD_BRL`: Taxa de câmbio (R$/US$)
- `IBOVESPA`: Fechamento do índice
- `PRE_1Y`: Pré-diário 1 ano (%)
- `PRE_5Y`: Pré-diário 5 anos (%)
- `PRE_10Y`: Pré-diário 10 anos (%)
- `CDS_BRAZIL`: Spread de risco (pontos base)
- `FOCUS_IPCA`: Expectativa mercado para IPCA

---

### 3.5 regime_state (Estado de Regime de Mercado)

```sql
CREATE TABLE regime_state (
    date DATE PRIMARY KEY,
    regime VARCHAR(20) NOT NULL,       -- 'RISK_ON', 'RISK_OFF', 'TRANSITION', etc.
    score_total DECIMAL(5, 2),         -- Score final (-20 a +20)
    
    -- Componentes do score
    score_yield_curve DECIMAL(3, 1),   -- (-2 a +2)
    score_risk_spread DECIMAL(3, 1),
    score_ibov_trend DECIMAL(3, 1),
    score_capital_flow DECIMAL(3, 1),
    score_liquidity DECIMAL(3, 1),
    
    -- Dados brutos usados
    yield_curve_value DECIMAL(10, 4),
    risk_spread_value DECIMAL(10, 4),
    ibov_trend_value DECIMAL(10, 4),
    capital_flow_value DECIMAL(10, 4),
    liquidity_value DECIMAL(10, 4),
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Índices
CREATE INDEX idx_regime_state_date ON regime_state(date DESC);
CREATE INDEX idx_regime_state_regime ON regime_state(regime);
```

**Descrição**: Snapshot diário da classificação de regime de mercado. Armazena tanto o resultado final quanto os componentes individuais para auditoria e debugging.

---

### 3.6 signals (Sinais e Scores de Ativos)

```sql
CREATE TABLE signals (
    date DATE NOT NULL,
    ticker VARCHAR(10) NOT NULL,
    
    -- Fatores Brutos (não normalizados)
    momentum_3m DECIMAL(10, 4),       -- Retorno 63 dias
    momentum_6m DECIMAL(10, 4),       -- Retorno 126 dias
    momentum_12m DECIMAL(10, 4),      -- Retorno 252 dias
    
    vol_21d DECIMAL(10, 4),          -- Volatilidade anualizada 21 dias
    vol_63d DECIMAL(10, 4),          -- Volatilidade anualizada 63 dias
    
    -- Scores Normalizados (Z-score -3 a +3)
    score_momentum DECIMAL(5, 2),
    score_quality DECIMAL(5, 2),
    score_value DECIMAL(5, 2),
    score_volatility DECIMAL(5, 2),    -- Inverso: menor vol = maior score
    score_liquidity DECIMAL(5, 2),
    
    -- Score Final (0 a 10)
    score_final DECIMAL(5, 2),
    rank_universe INTEGER,            -- Posição no ranking (1 = melhor)
    
    -- Contexto
    regime_at_date VARCHAR(20),
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    PRIMARY KEY (date, ticker),
    FOREIGN KEY (ticker) REFERENCES assets(ticker)
);

-- Índices
CREATE INDEX idx_signals_date_rank ON signals(date, rank_universe);
CREATE INDEX idx_signals_ticker_date ON signals(ticker, date DESC);
CREATE INDEX idx_signals_high_score ON signals(date, score_final DESC) WHERE score_final > 7;
```

**Descrição**: Tabela central do sistema. Armazena todos os cálculos quantitativos para cada ativo em cada dia. Permite análise histórica, backtesting e auditoria.

---

### 3.7 portfolios (Carteiras)

```sql
CREATE TABLE portfolios (
    portfolio_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    strategy VARCHAR(50),              -- 'MOMENTUM', 'VALUE', 'MULTI_FACTOR'
    regime_filter VARCHAR(20),         -- 'ALL', 'RISK_ON_ONLY', etc.
    
    -- Parâmetros da estratégia
    max_positions INTEGER DEFAULT 10,
    max_position_size DECIMAL(5, 2) DEFAULT 0.15,  -- 15%
    min_position_size DECIMAL(5, 2) DEFAULT 0.01,  -- 1%
    rebalance_frequency VARCHAR(20) DEFAULT 'MONTHLY',
    
    -- Status
    is_active BOOLEAN DEFAULT TRUE,
    is_simulated BOOLEAN DEFAULT TRUE, -- TRUE = backtest, FALSE = real
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**Descrição**: Configuração de carteiras/stratégias. Pode representar uma estratégia de backtest ou uma carteira real de investimento.

---

### 3.8 portfolio_holdings (Posições das Carteiras)

```sql
CREATE TABLE portfolio_holdings (
    portfolio_id INTEGER NOT NULL,
    ticker VARCHAR(10) NOT NULL,
    date DATE NOT NULL,
    
    weight DECIMAL(5, 4),            -- 0.15 = 15% da carteira
    shares INTEGER,                    -- Quantidade (se real)
    price_entry DECIMAL(12, 4),
    stop_loss DECIMAL(12, 4),
    target_price DECIMAL(12, 4),
    
    -- Status
    status VARCHAR(20),                -- 'OPEN', 'CLOSED', 'PENDING'
    exit_price DECIMAL(12, 4),
    exit_date DATE,
    return_pct DECIMAL(10, 4),         -- Retorno da operação
    
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    PRIMARY KEY (portfolio_id, ticker, date),
    FOREIGN KEY (portfolio_id) REFERENCES portfolios(portfolio_id),
    FOREIGN KEY (ticker) REFERENCES assets(ticker)
);

-- Índices
CREATE INDEX idx_holdings_portfolio_date ON portfolio_holdings(portfolio_id, date DESC);
CREATE INDEX idx_holdings_active ON portfolio_holdings(status) WHERE status = 'OPEN';
```

**Descrição**: Registro histórico de todas as posções de todas as carteiras. Permite rastrear evolução, calcular performance, e auditar decisões.

---

### 3.9 backtests (Resultados de Backtests)

```sql
CREATE TABLE backtests (
    backtest_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    
    -- Configuração
    strategy VARCHAR(50),
    universe TEXT,                     -- JSON: ['PETR4', 'VALE3', ...]
    start_date DATE,
    end_date DATE,
    initial_capital DECIMAL(15, 2),
    
    -- Resultados
    final_capital DECIMAL(15, 2),
    total_return DECIMAL(10, 4),       -- Percentual total
    cagr DECIMAL(10, 4),               -- CAGR anualizado
    volatility DECIMAL(10, 4),           -- Volatilidade anualizada
    sharpe_ratio DECIMAL(10, 4),
    sortino_ratio DECIMAL(10, 4),
    max_drawdown DECIMAL(10, 4),        -- Percentual negativo
    calmar_ratio DECIMAL(10, 4),
    
    -- Benchmark
    benchmark VARCHAR(10) DEFAULT 'IBOVESPA',
    benchmark_return DECIMAL(10, 4),
    alpha DECIMAL(10, 4),
    beta DECIMAL(10, 4),
    
    -- Estatísticas operacionais
    total_trades INTEGER,
    winning_trades INTEGER,
    losing_trades INTEGER,
    win_rate DECIMAL(5, 2),
    avg_return_per_trade DECIMAL(10, 4),
    
    -- Parâmetros (para reprodução)
    parameters JSON,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**Descrição**: Armazena resultados completos de backtests para comparação e análise de estratégias.

---

### 3.10 dividends (Histórico de Dividendos)

```sql
CREATE TABLE dividends (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ticker VARCHAR(10) NOT NULL,
    
    dividend_type VARCHAR(20),         -- 'DIVIDENDO', 'JCP', 'BONIFICACAO'
    value_per_share DECIMAL(10, 4),
    
    -- Datas importantes
    announcement_date DATE,
    ex_date DATE,                     -- Data "com"
    record_date DATE,                 -- Data de registro
    payment_date DATE,                -- Data de pagamento
    
    -- Contexto
    yield_on_cost DECIMAL(10, 4),      -- Yield baseado no preço da ação
    price_on_ex_date DECIMAL(12, 4),   -- Preço de fechamento na data ex
    
    source VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (ticker) REFERENCES assets(ticker)
);

-- Índices
CREATE INDEX idx_dividends_ticker ON dividends(ticker, payment_date DESC);
CREATE INDEX idx_dividends_ex_date ON dividends(ex_date);
CREATE INDEX idx_dividends_payment ON dividends(payment_date);
```

**Descrição**: Histórico completo de dividendos e eventos corporativos. Essencial para análise de renda passiva e backtests precisos.

---

## 4. Views (Visões)

### 4.1 vw_latest_prices (Últimos Preços)

```sql
CREATE VIEW vw_latest_prices AS
SELECT p.*, a.name, a.sector
FROM prices p
INNER JOIN assets a ON p.ticker = a.ticker
WHERE (p.ticker, p.date) IN (
    SELECT ticker, MAX(date)
    FROM prices
    GROUP BY ticker
);
```

### 4.2 vw_latest_signals (Últimos Sinais Calculados)

```sql
CREATE VIEW vw_latest_signals AS
SELECT s.*, a.name, a.sector, p.close as latest_price
FROM signals s
INNER JOIN assets a ON s.ticker = a.ticker
LEFT JOIN vw_latest_prices p ON s.ticker = p.ticker
WHERE (s.ticker, s.date) IN (
    SELECT ticker, MAX(date)
    FROM signals
    GROUP BY ticker
)
ORDER BY s.score_final DESC;
```

### 4.3 vw_current_portfolio (Carteira Atual)

```sql
CREATE VIEW vw_current_portfolio AS
SELECT 
    h.*,
    a.name,
    p.close as current_price,
    (p.close - h.price_entry) / h.price_entry as unrealized_return
FROM portfolio_holdings h
INNER JOIN assets a ON h.ticker = a.ticker
LEFT JOIN vw_latest_prices p ON h.ticker = p.ticker
WHERE h.status = 'OPEN'
AND (h.portfolio_id, h.ticker, h.date) IN (
    SELECT portfolio_id, ticker, MAX(date)
    FROM portfolio_holdings
    WHERE status = 'OPEN'
    GROUP BY portfolio_id, ticker
);
```

---

## 5. Triggers (Gatilhos)

### 5.1 Atualizar updated_at em assets

```sql
CREATE TRIGGER trg_assets_updated
AFTER UPDATE ON assets
BEGIN
    UPDATE assets SET updated_at = CURRENT_TIMESTAMP
    WHERE ticker = NEW.ticker;
END;
```

### 5.2 Validar preços positivos

```sql
CREATE TRIGGER trg_prices_validation
BEFORE INSERT ON prices
BEGIN
    SELECT CASE
        WHEN NEW.open <= 0 OR NEW.high <= 0 OR NEW.low <= 0 OR NEW.close <= 0
        THEN RAISE(ABORT, 'Preços devem ser positivos')
    END;
    
    SELECT CASE
        WHEN NEW.low > NEW.high
        THEN RAISE(ABORT, 'Low não pode ser maior que High')
    END;
    
    SELECT CASE
        WHEN NEW.low > NEW.open OR NEW.low > NEW.close
        THEN RAISE(ABORT, 'Low deve ser o menor valor')
    END;
    
    SELECT CASE
        WHEN NEW.high < NEW.open OR NEW.high < NEW.close
        THEN RAISE(ABORT, 'High deve ser o maior valor')
    END;
END;
```

---

## 6. Estratégia de Backup e Manutenção

### 6.1 Backup Diário

```bash
#!/bin/bash
# backup.sh
DATE=$(date +%Y%m%d)
sqlite3 smart_invest.db ".backup 'backups/smart_invest_${DATE}.db'"
gzip "backups/smart_invest_${DATE}.db"
# Manter apenas últimos 30 dias
find backups/ -name "*.gz" -mtime +30 -delete
```

### 6.2 Vacuum Semanal

```sql
-- Remove espaço não utilizado
VACUUM;

-- Otimiza índices
REINDEX;

-- Analisa tabelas para query planner
ANALYZE;
```

---

## 7. Migrações (Versionamento)

### Versão 1.0 - Estrutura Inicial
- Criação de todas as tabelas acima
- Inserção de assets (top 100 B3)

### Versão 1.1 - Índices de Performance
- Adição de índices adicionais conforme necessidade

### Versão 1.2 - Particionamento (Futuro)
- Se crescer muito: particionar prices por ano

---

**Versão**: 1.0  
**Criado em**: Fevereiro 2026  
**Próxima revisão**: Após implementação do Data Layer
