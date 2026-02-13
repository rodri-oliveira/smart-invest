# Smart Invest - Sistema de Inteligência de Investimentos

Sistema quantitativo determinístico para investimentos no Brasil (B3).

## Visão Geral

O Smart Invest é um motor de análise quantitativa que:
- **Coleta** dados de mercado e macroeconômicos (brapi.dev, BCB)
- **Calcula** indicadores técnicos (momentum, volatilidade, liquidez)
- **Classifica** o regime de mercado (Risk ON/Risk OFF/Transição)
- **Pontua** ativos por múltiplos fatores (momentum, qualidade, valor, risco)
- **Constrói** carteiras otimizadas com gestão de risco
- **Expõe** tudo via API REST (FastAPI)

## Estrutura do Projeto

```
smart-invest/
├── aim/                    # Motor quantitativo (core)
│   ├── config/            # Parâmetros e settings
│   ├── data_layer/        # Banco de dados e providers
│   ├── features/          # Cálculo de indicadores
│   ├── regime/            # Classificação de regime
│   ├── scoring/           # Ranking multi-fator
│   ├── risk/              # Gestão de risco
│   └── allocation/        # Construção de carteira
├── api/                    # Interface FastAPI
│   ├── main.py            # App principal
│   └── routers/           # Endpoints
├── scripts/                # Automação
│   ├── init_database.py   # Inicializar banco
│   ├── daily_update.py    # Pipeline diário
│   └── test_pipeline.py   # Testar sistema
├── data/                   # SQLite e backups
├── docs/                   # Documentação
└── tests/                  # Testes
```

## Quick Start

### 1. Instalação

```bash
# Criar ambiente virtual
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Instalar dependências
pip install -r requirements.txt
```

### 2. Configuração

```bash
# Copiar template de configuração
cp .env.example .env

# Editar .env com suas chaves (opcional - tier gratuito disponível)
# BRAPI_TOKEN=sua_chave_aqui
```

### 3. Inicializar Banco

```bash
python scripts/init_database.py
```

Cria:
- Banco SQLite em `data/smart_invest.db`
- 10 tabelas (assets, prices, features, signals, etc.)
- 40 ativos do universo B3

### 4. Primeira Carga de Dados

```bash
python scripts/daily_update.py
```

Executa:
1. Download de preços de mercado
2. Download de dados macro (SELIC, CDI, IPCA, USD)
3. Cálculo de features
4. Classificação de regime
5. Cálculo de scores
6. Backup

### 5. Iniciar API

```bash
uvicorn api.main:app --reload --port 8000
```

Acesse: http://localhost:8000/docs

## API Endpoints

### Health
- `GET /health/` - Health check completo
- `GET /health/simple` - Health check simples

### Assets
- `GET /assets/` - Listar todos os ativos
- `GET /assets/{ticker}` - Detalhes de um ativo
- `GET /assets/{ticker}/prices` - Preços históricos

### Signals
- `GET /signals/regime/current` - Regime de mercado atual
- `GET /signals/regime/history` - Histórico de regimes
- `GET /signals/ranking` - Top ativos ranqueados
- `GET /signals/ranking/{ticker}` - Score de ativo específico

### Portfolio
- `POST /portfolio/build` - Construir carteira otimizada
- `GET /portfolio/{name}` - Ver carteira existente

## Modelos Implementados

### Regime de Mercado (v2.0)

Classificação baseada em 5 variáveis:

| Variável | Peso | Descrição |
|----------|------|-----------|
| Curva de Juros | 2.5 | Tendência SELIC |
| Spread de Risco | 2.0 | Tendência USD/BRL |
| Tendência Ibov | 2.5 | MM200 + inclinação MM50 |
| Fluxo de Capitais | 1.5 | Correlação USD x Ibov |
| Liquidez/Sentimento | 1.5 | Volume + volatilidade |

**Regimes:**
- Score ≥ +8: **RISK_ON_STRONG** (100% RV)
- Score ≥ +4: **RISK_ON** (80% RV)
- Entre -4 e +4: **TRANSITION** (50% RV)
- Score ≤ -4: **RISK_OFF** (30% RV)
- Score ≤ -8: **RISK_OFF_STRONG** (0% RV)

### Scoring Multi-Fator

**Pesos dinâmicos por regime:**

| Fator | RISK_ON | TRANSITION | RISK_OFF |
|-------|---------|------------|----------|
| Momentum | 35% | 25% | 15% |
| Qualidade | 25% | 30% | 35% |
| Valor | 20% | 25% | 30% |
| Volatilidade | 10% | 10% | 15% |
| Liquidez | 10% | 10% | 5% |

**Normalização:** Z-score dentro do universo

### Gestão de Risco

- **Max posição:** 12% (RISK_ON), 8% (TRANSITION), 5% (RISK_OFF)
- **Max setor:** 30%
- **Trailing stop:** 15%
- **Drawdown warning:** 15%
- **Drawdown ação:** 25%

## Stack

- **Backend:** Python 3.11, FastAPI, Pydantic
- **Dados:** pandas, numpy, SQLite
- **Fontes:** brapi.dev (100 req/dia grátis), BCB API (ilimitado)
- **Deploy:** Uvicorn, Render/Railway (free tier)

## Custo

| Componente | Custo |
|------------|-------|
| Banco SQLite | R$ 0 |
| brapi.dev (100 req/dia) | R$ 0 |
| BCB API | R$ 0 |
| GitHub Actions | R$ 0 |
| Deploy | R$ 0 |
| **Total** | **R$ 0** |

## Documentação

- [Modelagem de Negócio](docs/planejamento/01-modelagem-negocio.md)
- [Modelagem de Dados](docs/planejamento/02-modelagem-dados.md)
- [Stack e Arquitetura](docs/planejamento/03-stack-arquitetura.md)
- [Processo de Desenvolvimento](docs/planejamento/04-processo-desenvolvimento.md)
- [Deploy e Operações](docs/planejamento/05-deploy-operacoes.md)

## Licença

Privado - Uso pessoal
