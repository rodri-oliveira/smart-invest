# Smart Invest - Stack Tecnológica e Arquitetura

## 1. Visão Geral da Arquitetura

### 1.1 Princípios Arquiteturais

1. **Modularidade**: Componentes independentes e testáveis
2. **Determinismo**: Mesmos inputs → mesmos outputs (ciência reproduzível)
3. **Separação de Responsabilidades**: Dados → Features → Regime → Scores → Alocação
4. **Custo Zero Inicial**: Usar apenas recursos gratuitos no início
5. **Escalabilidade Horizontal**: Preparado para crescer sem reescrita
6. **Auditabilidade**: Todo cálculo pode ser rastreado

### 1.2 Diagrama de Arquitetura de Alto Nível

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           CLIENT LAYER                                      │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐           │
│  │   Web Interface │  │  Mobile (futuro)│  │  API Clients    │           │
│  │   (React/Vue)   │  │                 │  │  (Python/JS)    │           │
│  └────────┬────────┘  └────────┬────────┘  └────────┬────────┘           │
│           │                    │                    │                    │
└───────────┼────────────────────┼────────────────────┼────────────────────┘
            │                    │                    │
            ▼                    ▼                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           API LAYER (FastAPI)                               │
│  ┌───────────────────────────────────────────────────────────────────────┐ │
│  │  /analysis/recommendations  /analysis/stock/{ticker}                   │ │
│  │  /portfolio/current         /portfolio/backtest                         │ │
│  │  /regime/current            /dividends/calendar                         │ │
│  │  /health                    /metrics                                  │ │
│  └───────────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         APPLICATION LAYER                                 │
│                                                                             │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐              │
│  │   Analysis      │  │   Portfolio     │  │   Backtest      │              │
│  │   Service       │  │   Service       │  │   Service       │              │
│  │                 │  │                 │  │                 │              │
│  │ • Ranking       │  │ • Allocation    │  │ • Simulation    │              │
│  │ • Scoring       │  │ • Rebalancing   │  │ • Metrics       │              │
│  │ • Signals       │  │ • Risk Control  │  │ • Reporting     │              │
│  └────────┬────────┘  └────────┬────────┘  └────────┬────────┘              │
│           │                    │                    │                       │
└───────────┼────────────────────┼────────────────────┼───────────────────────┘
            │                    │                    │
            ▼                    ▼                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         DOMAIN LAYER (Core Quant)                           │
│                                                                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐    │
│  │   Regime     │  │   Scoring    │  │   Risk       │  │   Allocation │    │
│  │   Engine     │  │   Engine     │  │   Engine     │  │   Engine     │    │
│  │              │  │              │  │              │  │              │    │
│  │ • Macro      │  │ • Momentum   │  │ • Volatility │  │ • Position   │    │
│  │   Analysis   │  │ • Quality    │  │ • Drawdown   │  │   Sizing     │    │
│  │ • Regime     │  │ • Value      │  │ • Correlation│  │ • Rebalance  │    │
│  │   Classifier │  │ • Composite  │  │ • Stops      │  │   Logic      │    │
│  └──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘    │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
            │
            ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         DATA LAYER                                        │
│                                                                             │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐              │
│  │   Ingestion     │  │   Database      │  │   Cache         │              │
│  │                 │  │                 │  │                 │              │
│  │ • brapi.dev     │  │ • SQLite        │  │ • Memory        │              │
│  │ • BCB API       │  │   (local)       │  │ • Disk          │              │
│  │ • yfinance      │  │ • PostgreSQL    │  │ • Redis         │              │
│  │   (fallback)    │  │   (escala)      │  │   (futuro)      │              │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘              │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
            │
            ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                      EXTERNAL DATA SOURCES                                  │
│                                                                             │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐      │
│  │  brapi.dev  │  │  BCB API    │  │  yfinance   │  │  GitHub     │      │
│  │  (B3 data)  │  │  (Macro)    │  │  (Fallback) │  │  (Actions)  │      │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘      │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Stack Tecnológica Detalhada

### 2.1 Backend Core

| Componente | Tecnologia | Versão | Justificativa |
|------------|-----------|--------|---------------|
| **Linguagem** | Python | 3.11+ | Ecosistema quant/financeiro maduro |
| **Web Framework** | FastAPI | 0.100+ | Performance, async, auto-docs OpenAPI |
| **Validação** | Pydantic | 2.0+ | Type safety, serialização, validação |
| **Processamento** | pandas | 2.0+ | Análise de dados financeiros padrão |
| **Cálculos Numéricos** | numpy | 1.24+ | Performance em arrays |
| **Estatística** | scipy | 1.11+ | Métricas estatísticas avançadas |

**Por que não Django/Flask?**
- FastAPI é mais rápido (async)
- Gera documentação automaticamente
- Melhor integração com Pydantic para dados financeiros
- Menor overhead para API-only

### 2.2 Banco de Dados

| Fase | Tecnologia | Justificativa |
|------|-----------|---------------|
| **MVP (atual)** | SQLite | Zero config, portátil, suficiente para 1 usuário |
| **Beta** | SQLite + backup | Manter SQLite, adicionar backup automático |
| **Produção** | PostgreSQL | Concorrência, replicação, backups robustos |

**SQLite é suficiente porque:**
- Operações predominantemente leitura
- Single-user no MVP
- Portabilidade total (arquivo único)
- Zero custo de infra

**Migração para PostgreSQL quando:**
- Múltiplos usuários simultâneos
- Necessidade de replicação
- Volume > 1GB de dados

### 2.3 Orquestração e Jobs

| Componente | Tecnologia | Justificativa |
|------------|-----------|---------------|
| **Scheduler** | APScheduler | Simples, integrado ao Python |
| **Background** | FastAPI BackgroundTasks | Para tarefas leves |
| **Heavy Jobs** | Celery (futuro) | Quando precisar de filas robustas |
| **CI/CD** | GitHub Actions | Gratuito, integrado ao Git |

### 2.4 Fontes de Dados

| Prioridade | Fonte | Dados | Custo | Limitações |
|------------|-------|-------|-------|------------|
| **1** | brapi.dev | OHLCV, fundament., dividendos | Grátis (100 req/dia) | Limitado requests |
| **2** | BCB API | Selic, IPCA, câmbio | Grátis (ilimitado) | Apenas macro BR |
| **3** | yfinance | Fallback OHLCV | Grátis | Pode ter delays |
| **4** | Alpha Vantage | Internacional | Grátis (25 req/dia) | Limitado |

### 2.5 IA/LLM (Camada Conversacional)

| Componente | Tecnologia | Uso | Custo Estimado |
|------------|-----------|-----|----------------|
| **LLM API** | Claude 3.5 Sonnet | Interpretação de perguntas | ~$0.003/input token |
| **Embeddings** | OpenAI/text-embedding | Busca semântica (futuro) | ~$0.10/1M tokens |
| **Vector DB** | pgvector (PostgreSQL) | Busca em documentos (futuro) | Incluso no PG |

### 2.6 Infraestrutura e Deploy

| Fase | Plataforma | Custo | Quando Usar |
|------|-----------|-------|-------------|
| **Desenvolvimento** | Local/SQLite | R$ 0 | Todo desenvolvimento |
| **MVP Deploy** | Render/Railway free | R$ 0 | Primeira versão pública |
| **Produção** | VPS (Hetzner/DO) | R$ 30-50/mês | Quando necessitar performance |
| **Escala** | AWS/GCP/Azure | R$ 200+/mês | Milhares de usuários |

### 2.7 Ferramentas de Desenvolvimento

| Categoria | Ferramenta | Uso |
|-----------|-----------|-----|
| **IDE** | VS Code + Python ext. | Desenvolvimento |
| **Versionamento** | Git + GitHub | Controle de código |
| **Ambiente** | venv / conda | Isolamento de dependências |
| **Linting** | ruff | Linting rápido |
| **Formatação** | black | Código padronizado |
| **Type Check** | mypy | Verificação de tipos |
| **Testes** | pytest | Testes unitários/integração |
| **CI** | GitHub Actions | Automatização de checks |

---

## 3. Estrutura de Pastas do Projeto

```
smart-invest/
├── .agent/                          # IA Skills e Agents
│   ├── agents/
│   │   ├── investment-specialist.md
│   │   └── backend-specialist.md
│   ├── skills/
│   │   └── quantitative-investing/
│   │       └── SKILL.md
│   └── ARCHITECTURE.md
│
├── docs/                           # Documentação
│   ├── planejamento/               # Plano de desenvolvimento
│   │   ├── 01-modelagem-negocio.md
│   │   ├── 02-modelagem-dados.md
│   │   ├── 03-stack-arquitetura.md  # Este arquivo
│   │   ├── 04-processo-desenvolvimento.md
│   │   └── 05-deploy-operacoes.md
│   └── docs originais de visão...
│
├── data/                           # Dados locais (SQLite)
│   ├── smart_invest.db            # Banco principal
│   ├── backups/                   # Backups diários
│   └── raw/                       # Dados brutos importados
│
├── aim/                           # Motor Quantitativo (Core)
│   ├── __init__.py
│   ├── config/
│   │   ├── __init__.py
│   │   ├── parameters.py          # Parâmetros centralizados
│   │   ├── universe.py            # Definição do universo de ativos
│   │   └── settings.py            # Configurações gerais
│   │
│   ├── data_layer/
│   │   ├── __init__.py
│   │   ├── database.py            # Acesso ao SQLite/PostgreSQL
│   │   ├── ingestion.py           # Pipeline de coleta de dados
│   │   ├── cache.py               # Sistema de cache
│   │   └── providers/
│   │       ├── __init__.py
│   │       ├── brapi.py           # Cliente brapi.dev
│   │       ├── bcb_api.py         # Cliente Banco Central
│   │       ├── yfinance_client.py # Cliente Yahoo Finance
│   │       └── base.py            # Interface base
│   │
│   ├── features/
│   │   ├── __init__.py
│   │   ├── momentum.py            # Cálculos de momentum
│   │   ├── quality.py             # Métricas de qualidade
│   │   ├── value.py               # Métricas de valor
│   │   ├── volatility.py          # Cálculos de volatilidade
│   │   ├── liquidity.py           # Métricas de liquidez
│   │   └── macro.py               # Indicadores macro
│   │
│   ├── regime/
│   │   ├── __init__.py
│   │   ├── classifier.py          # Classificador de regime
│   │   ├── indicators.py          # Cálculo de indicadores macro
│   │   └── rules.py               # Regras de classificação
│   │
│   ├── scoring/
│   │   ├── __init__.py
│   │   ├── engine.py              # Motor de scoring
│   │   ├── factors.py             # Cálculo de fatores
│   │   └── normalizer.py          # Normalização z-score
│   │
│   ├── risk/
│   │   ├── __init__.py
│   │   ├── engine.py              # Gestão de risco
│   │   ├── position_sizing.py     # Dimensionamento de posições
│   │   ├── drawdown.py            # Controle de drawdown
│   │   └── stops.py               # Cálculos de stop loss
│   │
│   ├── allocation/
│   │   ├── __init__.py
│   │   ├── engine.py              # Motor de alocação
│   │   ├── portfolio.py           # Construção de carteira
│   │   └── rebalancing.py         # Lógica de rebalanceamento
│   │
│   ├── backtest/
│   │   ├── __init__.py
│   │   ├── engine.py              # Motor de backtest
│   │   ├── metrics.py             # Cálculo de métricas
│   │   ├── simulation.py          # Simulação de execução
│   │   └── report.py              # Geração de relatórios
│   │
│   ├── execution/
│   │   ├── __init__.py
│   │   ├── orchestrator.py        # Orquestrador principal
│   │   └── pipeline.py            # Pipeline de execução
│   │
│   └── utils/
│       ├── __init__.py
│       ├── dates.py               # Utilitários de datas
│       ├── math.py                # Funções matemáticas
│       ├── validators.py          # Validações
│       └── logger.py              # Logging configurado
│
├── api/                           # API FastAPI
│   ├── __init__.py
│   ├── main.py                    # Entry point
│   ├── dependencies.py            # Injeção de dependências
│   ├── middleware/
│   │   ├── __init__.py
│   │   ├── error_handling.py
│   │   └── logging.py
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── analysis.py            # Endpoints de análise
│   │   ├── portfolio.py           # Endpoints de carteira
│   │   ├── backtest.py            # Endpoints de backtest
│   │   ├── regime.py              # Endpoints de regime
│   │   ├── dividends.py           # Endpoints de dividendos
│   │   └── health.py              # Health checks
│   └── models/
│       ├── __init__.py
│       ├── requests.py            # Schemas de request
│       └── responses.py           # Schemas de response
│
├── web/                           # Interface Web (futuro)
│   └── ...
│
├── scripts/                       # Scripts utilitários
│   ├── daily_update.py            # Atualização diária de dados
│   ├── backtest_historical.py     # Backtest histórico completo
│   ├── generate_report.py         # Geração de relatório
│   ├── init_database.py           # Inicialização do banco
│   └── backup.py                  # Script de backup
│
├── notebooks/                     # Jupyter notebooks
│   ├── 01_data_exploration.ipynb
│   ├── 02_feature_analysis.ipynb
│   ├── 03_backtest_validation.ipynb
│   └── 04_model_optimization.ipynb
│
├── tests/                         # Testes
│   ├── __init__.py
│   ├── conftest.py                # Configuração pytest
│   ├── unit/
│   │   ├── test_features.py
│   │   ├── test_scoring.py
│   │   └── test_regime.py
│   ├── integration/
│   │   ├── test_api.py
│   │   └── test_data_providers.py
│   └── fixtures/                  # Dados de teste
│
├── .github/
│   └── workflows/
│       ├── ci.yml                 # CI: lint, test, type-check
│       └── daily_data_update.yml  # Job diário de dados
│
├── requirements.txt               # Dependências
├── requirements-dev.txt           # Dependências de dev
├── pyproject.toml                 # Configuração do projeto
├── .env.example                   # Template de variáveis
├── .gitignore
└── README.md
```

---

## 4. Fluxo de Dados

### 4.1 Pipeline de Ingestão Diária

```
┌─────────────────────────────────────────────────────────┐
│                    DAILY UPDATE PIPELINE                  │
│                    (GitHub Actions / Cron)              │
└─────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────┐
│ 1. COLETA DE DADOS DE MERCADO                           │
│    ┌─────────────────┐  ┌─────────────────┐             │
│    │ brapi.dev       │  │ yfinance        │             │
│    │ • Preços OHLCV  │  │ (fallback)      │             │
│    │ • Volume        │  │                 │             │
│    └────────┬────────┘  └─────────────────┘             │
│             │                                           │
│             ▼                                           │
│    ┌──────────────────────────────────────────┐        │
│    │ Validação:                             │        │
│    │ • Preços positivos                     │        │
│    │ • Volume > 0                           │        │
│    │ • Continuidade (gap < 5 dias)          │        │
│    └──────────────────────────────────────────┘        │
└─────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────┐
│ 2. COLETA DE DADOS MACROECONÔMICOS                      │
│    ┌─────────────────┐                                   │
│    │ BCB API         │                                   │
│    │ • Selic/CDI     │                                   │
│    │ • IPCA/IGPM     │                                   │
│    │ • Câmbio        │                                   │
│    └────────┬────────┘                                   │
│             │                                           │
│             ▼                                           │
│    ┌──────────────────────────────────────────┐        │
│    │ Validação:                             │        │
│    │ • Valores dentro de ranges esperados   │        │
│    │ • Timestamps válidos                   │        │
│    └──────────────────────────────────────────┘        │
└─────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────┐
│ 3. PERSISTÊNCIA NO BANCO                                │
│    ┌──────────────────────────────────────────┐        │
│    │ SQLite/PostgreSQL:                       │        │
│    │ • INSERT/UPDATE prices                 │        │
│    │ • INSERT/UPDATE macro_indicators       │        │
│    │ • INSERT/UPDATE fundamentals (se novo)  │        │
│    └──────────────────────────────────────────┘        │
└─────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────┐
│ 4. CÁLCULO DE FEATURES                                  │
│    ┌──────────────────────────────────────────┐        │
│    │ Para cada ativo:                         │        │
│    │ • momentum_3m, 6m, 12m                 │        │
│    │ • vol_21d, 63d                         │        │
│    │ • médias móveis                        │        │
│    └──────────────────────────────────────────┘        │
└─────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────┐
│ 5. CLASSIFICAÇÃO DE REGIME                              │
│    ┌──────────────────────────────────────────┐        │
│    │ • Calcular 5 indicadores macro           │        │
│    │ • Score ponderado (-20 a +20)          │        │
│    │ • Classificar regime                     │        │
│    │ • Persistir regime_state               │        │
│    └──────────────────────────────────────────┘        │
└─────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────┐
│ 6. SCORING DE ATIVOS                                    │
│    ┌──────────────────────────────────────────┐        │
│    │ Para cada ativo:                         │        │
│    │ • Score por fator (z-score)            │        │
│    │ • Score final ponderado (0-10)         │        │
│    │ • Ranking no universo                  │        │
│    │ • Persistir signals                    │        │
│    └──────────────────────────────────────────┘        │
└─────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────┐
│ 7. GERAÇÃO DE ALERTAS E RELATÓRIOS                      │
│    ┌──────────────────────────────────────────┐        │
│    │ • Top 10 recomendações                   │        │
│    │ • Mudança de regime (se ocorreu)         │        │
│    │ • Dividendos próximos                    │        │
│    │ • Enviar notificações (futuro)         │        │
│    └──────────────────────────────────────────┘        │
└─────────────────────────────────────────────────────────┘
                           │
                           ▼
                    ┌──────────────┐
                    │  BACKUP      │
                    │  DIÁRIO      │
                    └──────────────┘
```

---

## 5. Padrões de Código

### 5.1 Estrutura de Módulos

```python
# aim/features/momentum.py
"""Cálculos de momentum para ativos."""

from typing import Dict, List
import pandas as pd
import numpy as np
from aim.config.parameters import MOMENTUM_WINDOWS


def calculate_absolute_momentum(
    prices: pd.Series,
    window: int = 126
) -> float:
    """
    Calcula momentum absoluto (retorno no período).
    
    Args:
        prices: Série de preços ajustados
        window: Dias de lookback (padrão: 126 = 6 meses)
    
    Returns:
        Retorno percentual (ex: 0.15 = 15%)
    """
    if len(prices) < window:
        return np.nan
    
    return (prices.iloc[-1] / prices.iloc[-window]) - 1


def calculate_composite_momentum(
    prices: pd.Series,
    windows: Dict[str, int] = None
) -> Dict[str, float]:
    """
    Calcula momentum composto com múltiplos períodos.
    
    Fórmula: 0.4 × 3m + 0.3 × 6m + 0.3 × 12m
    
    Args:
        prices: Série de preços
        windows: Dict com {'short': 63, 'medium': 126, 'long': 252}
    
    Returns:
        Dict com scores individuais e final
    """
    if windows is None:
        windows = MOMENTUM_WINDOWS
    
    mom_short = calculate_absolute_momentum(prices, windows['short'])
    mom_medium = calculate_absolute_momentum(prices, windows['medium'])
    mom_long = calculate_absolute_momentum(prices, windows['long'])
    
    composite = (
        0.4 * mom_short +
        0.3 * mom_medium +
        0.3 * mom_long
    )
    
    return {
        'momentum_3m': mom_short,
        'momentum_6m': mom_medium,
        'momentum_12m': mom_long,
        'momentum_composite': composite
    }
```

### 5.2 Configuração Centralizada

```python
# aim/config/parameters.py
"""Parâmetros centralizados do sistema."""

from dataclasses import dataclass
from typing import Dict

# Janelas de cálculo
MOMENTUM_WINDOWS = {
    'short': 63,      # 3 meses
    'medium': 126,    # 6 meses
    'long': 252       # 12 meses
}

VOLATILITY_WINDOW = 63  # 3 meses
LIQUIDITY_WINDOW = 20   # 1 mês

# Pesos dos fatores por regime
FACTOR_WEIGHTS = {
    'RISK_ON_STRONG': {
        'momentum': 0.40,
        'quality': 0.20,
        'value': 0.15,
        'volatility': 0.15,
        'liquidity': 0.10
    },
    'RISK_ON': {
        'momentum': 0.35,
        'quality': 0.25,
        'value': 0.20,
        'volatility': 0.10,
        'liquidity': 0.10
    },
    # ... etc
}

# Limites de alocação
MAX_POSITION_SIZE = {
    'RISK_ON_STRONG': 0.15,
    'RISK_ON': 0.12,
    'TRANSITION': 0.08,
    'RISK_OFF': 0.05,
    'RISK_OFF_STRONG': 0.0
}

# Parâmetros de regime
REGIME_THRESHOLDS = {
    'risk_on_strong': 8,   # Score >= +8
    'risk_on': 4,          # Score >= +4
    'risk_off': -4,        # Score <= -4
    'risk_off_strong': -8  # Score <= -8
}

REGIME_VARIABLE_WEIGHTS = {
    'yield_curve': 2.5,
    'risk_spread': 2.0,
    'ibov_trend': 2.5,
    'capital_flow': 1.5,
    'liquidity_sentiment': 1.5
}

@dataclass
class BacktestConfig:
    """Configuração de backtest."""
    initial_capital: float = 100000.0
    transaction_cost: float = 0.001  # 0.1%
    rebalance_frequency: str = 'M'   # Monthly
    max_positions: int = 10
```

### 5.3 API Endpoints

```python
# api/routers/analysis.py
"""Endpoints de análise de ativos."""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Optional

from aim.scoring.engine import get_latest_scores
from aim.data_layer.database import get_db

router = APIRouter(prefix="/analysis", tags=["analysis"])


class StockAnalysisRequest(BaseModel):
    ticker: str
    include_history: bool = False


class StockAnalysisResponse(BaseModel):
    ticker: str
    name: str
    current_price: float
    regime: str
    scores: dict
    recommendation: str
    conviction: str


@router.get("/stock/{ticker}", response_model=StockAnalysisResponse)
async def analyze_stock(
    ticker: str,
    db = Depends(get_db)
):
    """
    Retorna análise completa de um ativo.
    
    Inclui:
    - Scores de momentum, qualidade, valor, risco
    - Classificação de regime atual
    - Recomendação com grau de convicção
    """
    try:
        analysis = await get_latest_scores(db, ticker.upper())
        return StockAnalysisResponse(**analysis)
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Ativo não encontrado: {ticker}")


@router.get("/recommendations")
async def get_recommendations(
    limit: int = 10,
    regime: Optional[str] = None,
    db = Depends(get_db)
):
    """
    Retorna top recomendações baseadas no regime atual.
    
    Args:
        limit: Quantidade de ativos (max 20)
        regime: Filtrar por regime específico (opcional)
    """
    recommendations = await get_top_recommendations(
        db, 
        limit=min(limit, 20),
        regime_filter=regime
    )
    return recommendations
```

---

## 6. Considerações de Performance

### 6.1 Cache Strategy

```python
# aim/data_layer/cache.py
"""Sistema de cache para dados frequentemente acessados."""

import functools
from datetime import datetime, timedelta
import pickle
from pathlib import Path

CACHE_DIR = Path("data/cache")
CACHE_DIR.mkdir(parents=True, exist_ok=True)


def disk_cache(ttl_hours: int = 1):
    """Decorator para cache em disco."""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Gerar chave do cache
            cache_key = f"{func.__name__}_{hash(str(args))}_{hash(str(kwargs))}"
            cache_file = CACHE_DIR / f"{cache_key}.pkl"
            
            # Verificar se cache existe e é válido
            if cache_file.exists():
                modified = datetime.fromtimestamp(cache_file.stat().st_mtime)
                if datetime.now() - modified < timedelta(hours=ttl_hours):
                    with open(cache_file, 'rb') as f:
                        return pickle.load(f)
            
            # Executar função e salvar cache
            result = func(*args, **kwargs)
            with open(cache_file, 'wb') as f:
                pickle.dump(result, f)
            
            return result
        return wrapper
    return decorator
```

### 6.2 Consultas Otimizadas

```sql
-- Índices críticos para performance
CREATE INDEX idx_prices_ticker_date_desc ON prices(ticker, date DESC);
CREATE INDEX idx_signals_date_score ON signals(date, score_final DESC);
CREATE INDEX idx_signals_ticker_date ON signals(ticker, date DESC);
CREATE INDEX idx_fundamentals_ticker_date ON fundamentals(ticker, reference_date DESC);
```

---

## 7. Segurança

### 7.1 Variáveis de Ambiente

```bash
# .env.example
# Copiar para .env e preencher valores reais

# Database
DATABASE_URL=sqlite:///data/smart_invest.db

# API Keys (preencher com valores reais)
BRAPI_TOKEN=sua_chave_aqui
OPENAI_API_KEY=sua_chave_aqui
ANTHROPIC_API_KEY=sua_chave_aqui

# Configurações
ENVIRONMENT=development  # development, staging, production
LOG_LEVEL=INFO
CACHE_TTL_HOURS=1

# Segurança
SECRET_KEY=chave_secreta_para_jwt
ALLOWED_ORIGINS=http://localhost:3000,https://seudominio.com
```

### 7.2 Nunca Commitar

- Arquivos `.env` com chaves reais
- Banco de dados SQLite com dados reais
- Arquivos de cache grandes
- Notebooks com outputs de dados sensíveis

---

**Versão**: 1.0  
**Criado em**: Fevereiro 2026  
**Próxima revisão**: Após implementação do Core
