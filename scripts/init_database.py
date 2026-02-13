#!/usr/bin/env python3
"""
Script de inicialização do banco de dados.
Cria todas as tabelas necessárias.
"""

import logging
import sys
from pathlib import Path

# Adicionar root ao path
sys.path.insert(0, str(Path(__file__).parent.parent))

from aim.data_layer.database import Database
from aim.config.settings import get_settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


# SQL para criação de tabelas
CREATE_TABLES_SQL = """
-- Ativos (universo de investimento)
CREATE TABLE IF NOT EXISTS assets (
    ticker VARCHAR(10) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    sector VARCHAR(100),
    segment VARCHAR(100),
    market_cap_category VARCHAR(20),
    is_index BOOLEAN DEFAULT FALSE,
    is_active BOOLEAN DEFAULT TRUE,
    listed_date DATE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Preços históricos OHLCV
CREATE TABLE IF NOT EXISTS prices (
    ticker VARCHAR(10) NOT NULL,
    date DATE NOT NULL,
    open DECIMAL(12, 4),
    high DECIMAL(12, 4),
    low DECIMAL(12, 4),
    close DECIMAL(12, 4),
    volume BIGINT,
    adjusted_close DECIMAL(12, 4),
    source VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (ticker, date),
    FOREIGN KEY (ticker) REFERENCES assets(ticker)
);

-- Dados fundamentalistas
CREATE TABLE IF NOT EXISTS fundamentals (
    ticker VARCHAR(10) NOT NULL,
    reference_date DATE NOT NULL,
    report_type VARCHAR(10) NOT NULL,
    p_l DECIMAL(10, 2),
    p_vp DECIMAL(10, 2),
    dividend_yield DECIMAL(5, 2),
    ev_ebitda DECIMAL(10, 2),
    roe DECIMAL(5, 2),
    roa DECIMAL(5, 2),
    roic DECIMAL(5, 2),
    margem_liquida DECIMAL(5, 2),
    margem_ebitda DECIMAL(5, 2),
    divida_patrimonio DECIMAL(10, 2),
    divida_ebitda DECIMAL(10, 2),
    giro_ativo DECIMAL(10, 2),
    receita_liq BIGINT,
    lucro_liq BIGINT,
    ebitda BIGINT,
    divida_total BIGINT,
    patrimonio_liq BIGINT,
    ativo_total BIGINT,
    dividendos_pagos BIGINT,
    payout DECIMAL(5, 2),
    source VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (ticker, reference_date, report_type),
    FOREIGN KEY (ticker) REFERENCES assets(ticker)
);

-- Indicadores macroeconômicos
CREATE TABLE IF NOT EXISTS macro_indicators (
    date DATE NOT NULL,
    indicator VARCHAR(50) NOT NULL,
    value DECIMAL(15, 6),
    unit VARCHAR(20),
    frequency VARCHAR(20),
    source VARCHAR(50),
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (date, indicator)
);

-- Estado de regime de mercado
CREATE TABLE IF NOT EXISTS regime_state (
    date DATE PRIMARY KEY,
    regime VARCHAR(20) NOT NULL,
    score_total DECIMAL(5, 2),
    score_yield_curve DECIMAL(3, 1),
    score_risk_spread DECIMAL(3, 1),
    score_ibov_trend DECIMAL(3, 1),
    score_capital_flow DECIMAL(3, 1),
    score_liquidity DECIMAL(3, 1),
    yield_curve_value DECIMAL(10, 4),
    risk_spread_value DECIMAL(10, 4),
    ibov_trend_value DECIMAL(10, 4),
    capital_flow_value DECIMAL(10, 4),
    liquidity_value DECIMAL(10, 4),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Features calculadas (momentum, volatilidade, liquidez)
CREATE TABLE IF NOT EXISTS features (
    ticker VARCHAR(10) NOT NULL,
    date DATE NOT NULL,
    momentum_3m DECIMAL(10, 4),
    momentum_6m DECIMAL(10, 4),
    momentum_12m DECIMAL(10, 4),
    momentum_composite DECIMAL(10, 4),
    vol_21d DECIMAL(10, 4),
    vol_63d DECIMAL(10, 4),
    vol_126d DECIMAL(10, 4),
    avg_volume BIGINT,
    avg_dollar_volume DECIMAL(15, 2),
    liquidity_score DECIMAL(5, 4),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (ticker, date),
    FOREIGN KEY (ticker) REFERENCES assets(ticker)
);

-- Sinais e scores de ativos
CREATE TABLE IF NOT EXISTS signals (
    date DATE NOT NULL,
    ticker VARCHAR(10) NOT NULL,
    momentum_3m DECIMAL(10, 4),
    momentum_6m DECIMAL(10, 4),
    momentum_12m DECIMAL(10, 4),
    vol_21d DECIMAL(10, 4),
    vol_63d DECIMAL(10, 4),
    score_momentum DECIMAL(5, 2),
    score_quality DECIMAL(5, 2),
    score_value DECIMAL(5, 2),
    score_volatility DECIMAL(5, 2),
    score_liquidity DECIMAL(5, 2),
    score_final DECIMAL(5, 2),
    rank_universe INTEGER,
    regime_at_date VARCHAR(20),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (date, ticker),
    FOREIGN KEY (ticker) REFERENCES assets(ticker)
);

-- Carteiras (configurações)
CREATE TABLE IF NOT EXISTS portfolios (
    portfolio_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    strategy VARCHAR(50),
    regime_filter VARCHAR(20),
    max_positions INTEGER DEFAULT 10,
    max_position_size DECIMAL(5, 4) DEFAULT 0.15,
    min_position_size DECIMAL(5, 4) DEFAULT 0.01,
    rebalance_frequency VARCHAR(20) DEFAULT 'MONTHLY',
    is_active BOOLEAN DEFAULT TRUE,
    is_simulated BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Posições das carteiras
CREATE TABLE IF NOT EXISTS portfolio_holdings (
    portfolio_id INTEGER NOT NULL,
    ticker VARCHAR(10) NOT NULL,
    date DATE NOT NULL,
    weight DECIMAL(5, 4),
    shares INTEGER,
    price_entry DECIMAL(12, 4),
    stop_loss DECIMAL(12, 4),
    target_price DECIMAL(12, 4),
    status VARCHAR(20),
    exit_price DECIMAL(12, 4),
    exit_date DATE,
    return_pct DECIMAL(10, 4),
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (portfolio_id, ticker, date),
    FOREIGN KEY (portfolio_id) REFERENCES portfolios(portfolio_id),
    FOREIGN KEY (ticker) REFERENCES assets(ticker)
);

-- Resultados de backtests
CREATE TABLE IF NOT EXISTS backtests (
    backtest_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    strategy VARCHAR(50),
    universe TEXT,
    start_date DATE,
    end_date DATE,
    initial_capital DECIMAL(15, 2),
    final_capital DECIMAL(15, 2),
    total_return DECIMAL(10, 4),
    cagr DECIMAL(10, 4),
    volatility DECIMAL(10, 4),
    sharpe_ratio DECIMAL(10, 4),
    sortino_ratio DECIMAL(10, 4),
    max_drawdown DECIMAL(10, 4),
    calmar_ratio DECIMAL(10, 4),
    benchmark VARCHAR(10),
    benchmark_return DECIMAL(10, 4),
    alpha DECIMAL(10, 4),
    beta DECIMAL(10, 4),
    total_trades INTEGER,
    winning_trades INTEGER,
    losing_trades INTEGER,
    win_rate DECIMAL(5, 2),
    avg_return_per_trade DECIMAL(10, 4),
    parameters TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Histórico de dividendos
CREATE TABLE IF NOT EXISTS dividends (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ticker VARCHAR(10) NOT NULL,
    dividend_type VARCHAR(20),
    value_per_share DECIMAL(10, 4),
    announcement_date DATE,
    ex_date DATE,
    record_date DATE,
    payment_date DATE,
    yield_on_cost DECIMAL(10, 4),
    price_on_ex_date DECIMAL(12, 4),
    source VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (ticker) REFERENCES assets(ticker)
);
"""

# Índices para performance
CREATE_INDEXES_SQL = """
-- Índices de preços
CREATE INDEX IF NOT EXISTS idx_prices_date ON prices(date);
CREATE INDEX IF NOT EXISTS idx_prices_ticker_date ON prices(ticker, date DESC);

-- Índices de sinais
CREATE INDEX IF NOT EXISTS idx_signals_date_rank ON signals(date, rank_universe);
CREATE INDEX IF NOT EXISTS idx_signals_ticker_date ON signals(ticker, date DESC);
CREATE INDEX IF NOT EXISTS idx_signals_high_score ON signals(date, score_final DESC);

-- Índices de fundamentos
CREATE INDEX IF NOT EXISTS idx_fundamentals_ticker_date ON fundamentals(ticker, reference_date DESC);

-- Índices de macro
CREATE INDEX IF NOT EXISTS idx_macro_indicator_date ON macro_indicators(indicator, date DESC);

-- Índices de regime
CREATE INDEX IF NOT EXISTS idx_regime_state_date ON regime_state(date DESC);
CREATE INDEX IF NOT EXISTS idx_regime_state_regime ON regime_state(regime);

-- Índices de features
CREATE INDEX IF NOT EXISTS idx_features_ticker_date ON features(ticker, date DESC);
CREATE INDEX IF NOT EXISTS idx_features_date ON features(date);

-- Índices de dividendos
CREATE INDEX IF NOT EXISTS idx_dividends_ticker ON dividends(ticker, payment_date DESC);
CREATE INDEX IF NOT EXISTS idx_dividends_ex_date ON dividends(ex_date);

-- Índices de carteiras
CREATE INDEX IF NOT EXISTS idx_holdings_portfolio_date ON portfolio_holdings(portfolio_id, date DESC);
"""


# Dados iniciais: Top ativos B3
DEFAULT_ASSETS = [
    ("PETR4", "Petrobras PN", "Petróleo", "Exploração", "LARGE", False, True),
    ("PETR3", "Petrobras ON", "Petróleo", "Exploração", "LARGE", False, True),
    ("VALE3", "Vale ON", "Mineração", "Ferrosos", "LARGE", False, True),
    ("ITUB4", "Itaú Unibanco PN", "Financeiro", "Bancos", "LARGE", False, True),
    ("BBDC4", "Bradesco PN", "Financeiro", "Bancos", "LARGE", False, True),
    ("BBAS3", "Banco do Brasil ON", "Financeiro", "Bancos", "LARGE", False, True),
    ("MGLU3", "Magazine Luiza ON", "Varejo", "Eletrodomésticos", "LARGE", False, True),
    ("WEGE3", "WEG ON", "Indústria", "Máquinas", "LARGE", False, True),
    ("LREN3", "Lojas Renner ON", "Varejo", "Vestuário", "LARGE", False, True),
    ("ABEV3", "Ambev ON", "Bebidas", "Cervejas", "LARGE", False, True),
    ("JBSS3", "JBS ON", "Alimentos", "Carnes", "LARGE", False, True),
    ("ELET3", "Eletrobras ON", "Energia", "Elétricas", "LARGE", False, True),
    ("ELET6", "Eletrobras PNB", "Energia", "Elétricas", "LARGE", False, True),
    ("RENT3", "Localiza ON", "Locação", "Veículos", "LARGE", False, True),
    ("B3SA3", "B3 ON", "Financeiro", "Bolsas", "LARGE", False, True),
    ("SUZB3", "Suzano ON", "Papel", "Celulose", "LARGE", False, True),
    ("RAIL3", "Rumo ON", "Logística", "Ferrovias", "LARGE", False, True),
    ("VBBR3", "Vibra Energia ON", "Combustíveis", "Distribuição", "LARGE", False, True),
    ("PRIO3", "PetroRio ON", "Petróleo", "Exploração", "LARGE", False, True),
    ("BBSE3", "BB Seguridade ON", "Financeiro", "Seguros", "LARGE", False, True),
    ("ITSA4", "Itaúsa PN", "Holdings", "Financeiras", "LARGE", False, True),
    ("GGBR4", "Gerdau PN", "Siderurgia", "Aços", "LARGE", False, True),
    ("CSNA3", "CSN ON", "Siderurgia", "Aços", "LARGE", False, True),
    ("USIM5", "Usiminas PNA", "Siderurgia", "Aços", "MID", False, True),
    ("SANB11", "Santander BR Unit", "Financeiro", "Bancos", "LARGE", False, True),
    ("BPAC11", "BTG Pactual Unit", "Financeiro", "Bancos", "LARGE", False, True),
    ("EGIE3", "Engie Brasil ON", "Energia", "Elétricas", "LARGE", False, True),
    ("CPFE3", "CPFL Energia ON", "Energia", "Elétricas", "LARGE", False, True),
    ("ENGI11", "Energisa Unit", "Energia", "Elétricas", "LARGE", False, True),
    ("RAIZ4", "Raízen PN", "Combustíveis", "Etanol", "LARGE", False, True),
    ("BRFS3", "BRF ON", "Alimentos", "Processados", "LARGE", False, True),
    ("CCRO3", "CCR ON", "Logística", "Rodovias", "LARGE", False, True),
    ("RDOR3", "Rede D'Or ON", "Saúde", "Hospitais", "LARGE", False, True),
    ("HAPV3", "Hapvida ON", "Saúde", "Hospitais", "LARGE", False, True),
    ("EQTL3", "Equatorial ON", "Energia", "Elétricas", "LARGE", False, True),
    ("TOTS3", "Totvs ON", "Tecnologia", "Software", "LARGE", False, True),
    ("FLRY3", "Fleury ON", "Saúde", "Laboratórios", "LARGE", False, True),
    ("KLBN11", "Klabin Unit", "Papel", "Embalagens", "LARGE", False, True),
    ("SBSP3", "Sabesp ON", "Saneamento", "Água", "LARGE", False, True),
    ("CMIG4", "Cemig PN", "Energia", "Elétricas", "LARGE", False, True),
    ("IBOVESPA", "Índice Ibovespa", "Índice", "Benchmark", "LARGE", True, True),
]


def create_tables() -> None:
    """Cria todas as tabelas do banco (um statement por vez para SQLite)."""
    db = Database()
    
    logger.info("Criando tabelas...")
    
    # Dividir SQL em statements individuais (separados por ;)
    statements = [s.strip() for s in CREATE_TABLES_SQL.split(';') if s.strip()]
    
    for i, sql in enumerate(statements, 1):
        try:
            # Remover comentários do SQL
            clean_sql = '\n'.join(line for line in sql.split('\n') if not line.strip().startswith('--'))
            if clean_sql.strip():
                db.execute(clean_sql)
                logger.info(f"  ✓ Tabela {i}/{len(statements)}")
        except Exception as e:
            logger.error(f"  ✗ Erro no statement {i}: {e}")
            logger.error(f"     SQL: {sql[:100]}...")
            raise
    
    logger.info("✓ Tabelas criadas")


def create_indexes() -> None:
    """Cria índices para performance (um por vez)."""
    db = Database()

    logger.info("Criando índices...")
    
    # Dividir em statements individuais
    statements = [s.strip() for s in CREATE_INDEXES_SQL.split(';') if s.strip()]

    for i, sql in enumerate(statements, 1):
        try:
            clean_sql = '\n'.join(line for line in sql.split('\n') if not line.strip().startswith('--'))
            if clean_sql.strip():
                db.execute(clean_sql)
        except Exception as e:
            logger.warning(f"  ⚠ Erro no índice {i}: {e}")
            # Índices são opcionais, continuar mesmo se falhar
    
    logger.info(f"✓ {len(statements)} índices processados")


def seed_initial_data() -> None:
    """Insere dados iniciais (ativos do universo)."""
    db = Database()

    logger.info("Inserindo ativos iniciais...")

    query = """
        INSERT OR IGNORE INTO assets (ticker, name, sector, segment, market_cap_category, is_index, is_active)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """

    db.execute_many(query, DEFAULT_ASSETS)

    logger.info(f"✓ {len(DEFAULT_ASSETS)} ativos inseridos")


def validate_database() -> bool:
    """Valida se banco foi criado corretamente."""
    db = Database()

    required_tables = [
        "assets",
        "prices",
        "fundamentals",
        "macro_indicators",
        "regime_state",
        "features",
        "signals",
        "portfolios",
        "portfolio_holdings",
        "backtests",
        "dividends",
    ]

    for table in required_tables:
        if not db.table_exists(table):
            logger.error(f"✗ Tabela {table} não existe!")
            return False

    logger.info(f"✓ Todas as {len(required_tables)} tabelas validadas")
    return True


def main() -> int:
    """Função principal de inicialização."""
    try:
        logger.info("=" * 60)
        logger.info("Inicializando banco de dados Smart Invest")
        logger.info("=" * 60)

        # Criar diretório de dados se necessário
        settings = get_settings()
        settings.db_path.parent.mkdir(parents=True, exist_ok=True)

        # Criar tabelas
        create_tables()

        # Criar índices
        create_indexes()

        # Inserir dados iniciais
        seed_initial_data()

        # Validar
        if validate_database():
            logger.info("=" * 60)
            logger.info("✓ Banco de dados inicializado com sucesso!")
            logger.info(f"Local: {settings.db_path}")
            logger.info("=" * 60)
            return 0
        else:
            logger.error("✗ Validação falhou")
            return 1

    except Exception as e:
        logger.error(f"✗ Erro na inicialização: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
