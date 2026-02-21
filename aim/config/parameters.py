"""Parâmetros centralizados do sistema de investimentos."""

from dataclasses import dataclass
from typing import Dict, List

# ============================================================================
# CONFIGURAÇÕES DE JANELAS DE CÁLCULO
# ============================================================================

# Janelas de momentum (em dias úteis)
MOMENTUM_WINDOWS = {
    "short": 63,  # ~3 meses
    "medium": 126,  # ~6 meses
    "long": 252,  # ~12 meses
}

# Janelas de volatilidade
VOLATILITY_WINDOWS = {
    "short": 21,  # ~1 mês
    "medium": 63,  # ~3 meses
    "long": 126,  # ~6 meses
}

# Janelas de liquidez
LIQUIDITY_WINDOW = 20  # dias

# ============================================================================
# PESOS DOS FATORES POR REGIME
# ============================================================================

# Pesos ajustados conforme regime de mercado
# Quanto mais Risk ON, maior o peso de momentum
# Quanto mais Risk OFF, maior o peso de qualidade

FACTOR_WEIGHTS: Dict[str, Dict[str, float]] = {
    "RISK_ON_STRONG": {
        "momentum": 0.40,
        "quality": 0.20,
        "value": 0.15,
        "volatility": 0.15,
        "liquidity": 0.10,
    },
    "RISK_ON": {
        "momentum": 0.35,
        "quality": 0.25,
        "value": 0.20,
        "volatility": 0.10,
        "liquidity": 0.10,
    },
    "TRANSITION": {
        "momentum": 0.25,
        "quality": 0.30,
        "value": 0.25,
        "volatility": 0.10,
        "liquidity": 0.10,
    },
    "RISK_OFF": {
        "momentum": 0.15,
        "quality": 0.35,
        "value": 0.30,
        "volatility": 0.15,
        "liquidity": 0.05,
    },
    "RISK_OFF_STRONG": {
        "momentum": 0.0,
        "quality": 0.0,
        "value": 0.0,
        "volatility": 0.0,
        "liquidity": 0.0,
    },
}

# ============================================================================
# CONFIGURAÇÕES DE REGIME DE MERCADO
# ============================================================================

# Pesos das variáveis macro no score de regime
REGIME_VARIABLE_WEIGHTS = {
    "yield_curve": 2.5,  # Curva de juros (CDI vs pré)
    "risk_spread": 2.0,  # Spread de risco (proxy via dólar)
    "ibov_trend": 2.5,  # Tendência do Ibovespa (MM200)
    "capital_flow": 1.5,  # Fluxo de capitais (correlação dólar x ibov)
    "liquidity_sentiment": 1.5,  # Sentimento (volume + vol)
}

# Thresholds para classificação de regime
# Score máximo possível: +20 (10 × 2)
# Score mínimo possível: -20 (-10 × 2)
REGIME_THRESHOLDS = {
    "risk_on_strong": 8.0,  # Score >= +8
    "risk_on": 4.0,  # Score >= +4
    "risk_off": -4.0,  # Score <= -4
    "risk_off_strong": -8.0,  # Score <= -8
}

# ============================================================================
# LIMITES DE ALOCAÇÃO
# ============================================================================

# Alocação máxima por ativo conforme regime
MAX_POSITION_SIZE = {
    "RISK_ON_STRONG": 0.15,  # 15%
    "RISK_ON": 0.12,  # 12%
    "TRANSITION": 0.08,  # 8%
    "RISK_OFF": 0.05,  # 5%
    "RISK_OFF_STRONG": 0.0,  # 0% (100% RF)
}

# Alocação target de RV conforme regime
TARGET_RV_ALLOCATION = {
    "RISK_ON_STRONG": 0.98,  # 98% RV - máxima exposição para especulativo
    "RISK_ON": 0.95,  # 95% RV - alta exposição para agressivo
    "TRANSITION": 0.50,  # 50% RV - moderado
    "RISK_OFF": 0.20,  # 20% RV - conservador (reduzido de 30%)
    "RISK_OFF_STRONG": 0.05,  # 5% RV - muito conservador
}

# Limites dinâmicos por regime (fonte única para backend e frontend)
MAX_SECTOR_EXPOSURE_BY_REGIME = {
    "RISK_ON_STRONG": 0.40,
    "RISK_ON": 0.35,
    "TRANSITION": 0.20,
    "RISK_OFF": 0.12,
    "RISK_OFF_STRONG": 0.10,
}

# Teto operacional por ativo após seleção/ranqueamento
MAX_ASSET_EXPOSURE_BY_REGIME = {
    "RISK_ON_STRONG": 0.15,
    "RISK_ON": 0.12,
    "TRANSITION": 0.06,
    "RISK_OFF": 0.04,
    "RISK_OFF_STRONG": 0.02,
}

# Limites gerais
MIN_POSITION_SIZE = 0.01  # 1% mínimo
MAX_SECTOR_EXPOSURE = 0.30  # 30% por setor
MAX_CONCENTRATION = 0.20  # 20% em qualquer ativo (hard limit)

# ============================================================================
# PARÂMETROS DE RISCO
# ============================================================================

# Stop loss
TRAILING_STOP_PCT = 0.15  # 15% trailing stop
VOLATILITY_STOP_MULTIPLIER = 2.0  # 2x volatilidade anualizada

# Drawdown control
MAX_DRAWDOWN_WARNING = 0.15  # Alerta em 15% DD
MAX_DRAWDOWN_ACTION = 0.25  # Ação drástica em 25% DD
DRAWDOWN_REDUCTION_FACTOR = 0.5  # Reduzir exposição pela metade

# ============================================================================
# FILTROS DE UNIVERSO
# ============================================================================

MIN_LIQUIDITY_DAILY = 1_000_000  # R$ 1M volume mínimo diário
MIN_PRICE = 1.0  # Preço mínimo de R$ 1,00
MIN_HISTORY_DAYS = 252  # Mínimo 1 ano de histórico

# Top ativos B3 (inicial - pode ser expandido)
DEFAULT_UNIVERSE: List[str] = [
    # Commodities
    "PETR4",
    "PETR3",
    "VALE3",
    "GGBR4",
    "CSNA3",
    "USIM5",
    # Bancos
    "ITUB4",
    "BBDC4",
    "BBAS3",
    "SANB11",
    "BPAC11",
    # Varejo
    "MGLU3",
    "LREN3",
    "ABEV3",
    "RAIZ4",
    # Energia
    "ELET3",
    "ELET6",
    "EGIE3",
    "CPFE3",
    "ENGI11",
    # Outros
    "WEGE3",
    "JBSS3",
    "RENT3",
    "B3SA3",
    "SUZB3",
    "RAIL3",
    "VBBR3",
    "PRIO3",
    "BBSE3",
    "ITSA4",
    "BRFS3",
    "CCRO3",
    "RDOR3",
    "HAPV3",
    "EQTL3",
    "TOTS3",
    "FLRY3",
    "KLBN11",
    "SBSP3",
    "CMIG4",
]

# ============================================================================
# CONFIGURAÇÕES DE BACKTEST
# ============================================================================

DEFAULT_BACKTEST_CONFIG = {
    "initial_capital": 100_000.0,
    "transaction_cost_pct": 0.001,  # 0.1% (corretagem + spread)
    "slippage_pct": 0.001,  # 0.1% slippage estimado
    "rebalance_frequency": "M",  # Mensal
    "max_positions": 10,
    "benchmark": "IBOVESPA",
}

# ============================================================================
# CONFIGURAÇÕES DE CACHE
# ============================================================================

CACHE_TTL_HOURS = 1
CACHE_MAX_SIZE_MB = 100

# ============================================================================
# URLs DE APIs
# ============================================================================

BRAPI_BASE_URL = "https://brapi.dev/api"
BCB_API_BASE_URL = "https://api.bcb.gov.br/dados/serie/bcdata.sgs"

# IDs das séries do BCB
BCB_SERIES = {
    "SELIC": 432,  # Taxa SELIC
    "CDI": 12,  # Taxa CDI
    "IPCA": 433,  # IPCA mensal
    "IGPM": 189,  # IGP-M mensal
    "USD": 1,  # Taxa de câmbio USD/BRL
}

# ============================================================================
# DATACLASSES DE CONFIGURAÇÃO
# ============================================================================


@dataclass
class BacktestConfig:
    """Configuração de backtest."""

    initial_capital: float = 100_000.0
    transaction_cost_pct: float = 0.001
    slippage_pct: float = 0.001
    rebalance_frequency: str = "M"
    max_positions: int = 10
    benchmark: str = "IBOVESPA"
    start_date: str = ""
    end_date: str = ""


@dataclass
class RiskConfig:
    """Configuração de gestão de risco."""

    trailing_stop_pct: float = 0.15
    volatility_stop_multiplier: float = 2.0
    max_drawdown_warning: float = 0.15
    max_drawdown_action: float = 0.25
    max_position_size_pct: float = 0.15
    max_sector_exposure_pct: float = 0.30
