# Smart Invest - Processo de Desenvolvimento e Deploy

## 1. Metodologia de Desenvolvimento

### 1.1 Abordagem: Evidence-Based Development

> "Documentação não gera alpha. Código executável gera aprendizado."

**Princípios:**
1. **Backtest-Driven Development**: Toda feature é validada por backtest
2. **Determinismo**: Mesmos inputs → mesmos outputs (reprodutibilidade)
3. **Código Medido**: Performance medida, não assumida
4. **Iteração Rápida**: Pequenas mudanças, validação constante

### 1.2 Ciclo de Desenvolvimento

```
┌─────────────────────────────────────────────────────────────┐
│ 1. DESIGN                                                   │
│    • Definir o que será calculado                           │
│    • Especificar fórmula matemática                          │
│    • Documentar hipótese de investimento                     │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│ 2. IMPLEMENTAÇÃO                                            │
│    • Código modular e testável                               │
│    • Funções puras (sem side effects)                        │
│    • Documentação inline                                     │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│ 3. TESTE UNITÁRIO                                          │
│    • Validar cálculo com dados conhecidos                  │
│    • Testar edge cases (zeros, nulos, valores extremos)      │
│    • Verificar tipo de retorno                               │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│ 4. BACKTEST                                                │
│    • Rodar em 10+ anos de dados históricos                  │
│    • Comparar com Ibovespa                                   │
│    • Analisar métricas: Sharpe, Sortino, Max DD              │
│    • Validar em múltiplos regimes                            │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│ 5. ANÁLISE                                                 │
│    • Funcionou melhor que baseline?                          │
│    • Houve overfitting?                                      │
│    • Robustez em diferentes períodos?                        │
│    • Custo de transação considerado?                          │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
              ┌──────────────────────┐
              │  MELHOROU ALPHA?     │
              └──────────────────────┘
                     │         │
              SIM    │         │   NÃO
                     ▼         ▼
            ┌──────────┐   ┌──────────┐
            │  MERGE   │   │  REVERT  │
            │  DEPLOY  │   │  AJUSTAR │
            └──────────┘   └──────────┘
```

---

## 2. Fases de Desenvolvimento

### Fase 1: Fundação (Semanas 1-2)
**Objetivo**: Estrutura funcional de dados

**Entregáveis:**
- [ ] Estrutura de pastas do projeto
- [ ] SQLite configurado e testado
- [ ] Integração brapi.dev funcionando
- [ ] Pipeline de ingestão diária
- [ ] Dados históricos populados (5 anos)

**Critério de Sucesso:**
```bash
# Comando que deve funcionar
python scripts/daily_update.py
# Resultado: "✓ 42.350 registros atualizados em 45s"
```

**Backtest Baseline (para comparação):**
- Estratégia: Comprar e segurar Ibovespa
- CAGR: ~8% ao ano
- Sharpe: ~0.4
- Max DD: ~45%

---

### Fase 2: Feature Engineering (Semanas 3-4)
**Objetivo**: Indicadores técnicos implementados

**Entregáveis:**
- [ ] Momentum 3m, 6m, 12m calculado e validado
- [ ] Volatilidade 21d, 63d implementada
- [ ] Liquidez média calculada
- [ ] Normalização z-score funcionando

**Critério de Sucesso:**
```python
# Teste de sanidade
from aim.features.momentum import calculate_composite_momentum

prices = load_prices('PETR4')
momentum = calculate_composite_momentum(prices)

assert -1 < momentum['momentum_composite'] < 1  # Retorno percentual
assert momentum['momentum_3m'] != momentum['momentum_12m']
```

**Validação:**
- Comparar momentum com fontes externas (Investing.com, etc.)
- Correlation check: momentum positivo quando mercado sobe

---

### Fase 3: Regime Classifier (Semanas 5-6)
**Objetivo**: Classificador de regime de mercado

**Entregáveis:**
- [ ] Coleta de dados macro automática (BCB API)
- [ ] Cálculo de 5 indicadores de regime
- [ ] Score ponderado implementado
- [ ] Classificação em Risk ON/OFF/Transição

**Critério de Sucesso:**
```python
# Verificação histórica
regimes = load_regime_history()

# 2020-03 (COVID): Deve ser RISK_OFF ou RISK_OFF_STRONG
assert regimes['2020-03-15'] == 'RISK_OFF_STRONG'

# 2021-04 (Recovery): Deve ser RISK_ON
assert regimes['2021-04-15'] in ['RISK_ON', 'RISK_ON_STRONG']

# Transições devem ser raras (< 20% do tempo)
transitions = sum(1 for r in regimes if r == 'TRANSITION')
assert transitions / len(regimes) < 0.20
```

**Validação:**
- Comparar com períodos conhecidos de crise/alta
- Análise de transições: devem ser eventos, não ruído

---

### Fase 4: Scoring Engine (Semanas 7-8)
**Objetivo**: Ranking multi-fator de ativos

**Entregáveis:**
- [ ] Cálculo de 5 fatores implementado
- [ ] Normalização z-score por universo
- [ ] Score final ponderado por regime
- [ ] Ranking e persistência em signals

**Critério de Sucesso:**
```python
# Backtest simples
backtest = BacktestEngine(
    strategy='top_10_by_score',
    start_date='2019-01-01',
    end_date='2024-01-01'
)
results = backtest.run()

# Deve superar Ibovespa
assert results['cagr'] > 0.08  # CAGR > 8%
assert results['sharpe'] > 0.5  # Sharpe > 0.5
assert results['alpha_vs_ibov'] > 0.03  # Alpha > 3%
```

**Validação:**
- Análise de sensibilidade: variação de pesos
- Factor attribution: qual fator contribui mais?

---

### Fase 5: Risk & Allocation (Semanas 9-10)
**Objetivo**: Gestão de risco e alocação

**Entregáveis:**
- [ ] Position sizing por volatilidade
- [ ] Limites de exposição implementados
- [ ] Controle de drawdown automático
- [ ] Rebalanceamento mensal funcionando

**Critério de Sucesso:**
```python
# Drawdown deve ser menor que buy-and-hold
backtest_with_risk = BacktestEngine(
    strategy='multi_factor_with_risk_control',
    max_drawdown_limit=0.20,  # 20% max DD
    stop_loss=0.15            # 15% trailing stop
)
results = backtest_with_risk.run()

assert results['max_drawdown'] < -0.25  # Menor que -25%
assert results['cagr'] > 0.08  # Ainda cresce mais que Ibov
```

**Validação:**
- Stress test: performance em 2008, 2020, 2022
- Análise de stops: quantos foram acionados?

---

### Fase 6: Backtester Completo (Semanas 11-12)
**Objetivo**: Sistema de backtest robusto

**Entregáveis:**
- [ ] Simulação histórica completa (10+ anos)
- [ ] Métricas de performance: CAGR, Sharpe, Sortino, Max DD
- [ ] Análise por regime
- [ ] Transaction costs incluídos
- [ ] Reporting automatizado

**Critério de Sucesso:**
```python
# Report completo
generate_backtest_report(
    strategy='aim_v1',
    period='2014-01-01 to 2024-01-01',
    benchmark='IBOVESPA'
)

# Resultado esperado:
# CAGR: 12-15%
# Sharpe: 0.8-1.0
# Max DD: -15% a -20%
# Alpha: +4% a +6% vs Ibov
```

**Validação:**
- Walk-forward analysis
- Out-of-sample validation
- Paper trading (3 meses)

---

### Fase 7: API (Semanas 13-14)
**Objetivo**: Interface programática

**Entregáveis:**
- [ ] FastAPI endpoints implementados
- [ ] Documentação OpenAPI/Swagger
- [ ] Autenticação básica
- [ ] Health checks

**Critério de Sucesso:**
```bash
# Teste de integração
curl http://localhost:8000/health
# {"status": "healthy", "database": "connected", "last_update": "2024-02-12"}

curl http://localhost:8000/analysis/stock/PETR4
# Retorna análise completa em < 2s
```

---

### Fase 8: IA Conversacional (Semanas 15-16)
**Objetivo**: Interface em linguagem natural

**Entregáveis:**
- [ ] Integração LLM (Claude/GPT)
- [ ] Prompts especializados
- [ ] Interpretação de perguntas comuns
- [ ] Explicação de decisões

**Critério de Sucesso:**
```
Usuário: "Quais ações comprar hoje?"

IA: "Baseado no regime RISK_ON atual (score +9), as top 
     recomendações são:
     
     1. PETR4 (Score 8.7) - Momentum forte + valuation atrativo
     2. VALE3 (Score 8.2) - Qualidade alta + yield acima da média
     
     Alocação sugerida: até 12% por ativo."
```

---

## 3. Workflow de Git

### 3.1 Branch Strategy: Git Flow Simplificado

```
main                    # Produção (estável)
  │
  ├── develop           # Desenvolvimento (integração)
  │     │
  │     ├── feature/data-layer      # Fase 1
  │     ├── feature/momentum        # Fase 2
  │     ├── feature/regime          # Fase 3
  │     ├── feature/scoring         # Fase 4
  │     ├── feature/risk            # Fase 5
  │     ├── feature/backtest        # Fase 6
  │     ├── feature/api             # Fase 7
  │     └── feature/ai              # Fase 8
  │
  └── hotfix/urgent     # Correções emergenciais
```

### 3.2 Commit Conventions

```
type(scope): description

[optional body]

[optional footer]
```

**Types:**
- `feat`: Nova feature
- `fix`: Correção de bug
- `refactor`: Refatoração sem mudança de comportamento
- `test`: Adição/modificação de testes
- `docs`: Documentação
- `perf`: Melhoria de performance
- `chore`: Manutenção

**Scopes:**
- `data`: Data layer
- `features`: Cálculos de features
- `regime`: Classificador de regime
- `scoring`: Motor de scoring
- `risk`: Gestão de risco
- `backtest`: Backtesting
- `api`: API FastAPI

**Exemplos:**
```
feat(data): implement brapi.dev client with caching

- Add BrapiProvider class
- Implement retry logic with exponential backoff
- Add disk cache for 1 hour TTL

Closes #12
```

```
perf(scoring): optimize z-score calculation with vectorization

- Replace loop with numpy vectorized operation
- 10x speedup on universe of 100 assets
- Reduce backtest time from 45s to 4s
```

### 3.3 Pull Request Template

```markdown
## Descrição
[Descrever o que foi implementado]

## Tipo de Mudança
- [ ] Nova feature
- [ ] Bug fix
- [ ] Refatoração
- [ ] Performance
- [ ] Documentação

## Testes
- [ ] Testes unitários passam
- [ ] Backtest executado
- [ ] Resultados documentados

## Resultados do Backtest
```
Strategy: [nome]
Período: [início] a [fim]
CAGR: [X%]
Sharpe: [X.XX]
Max DD: [X%]
Alpha vs Ibov: [+X%]
```

## Checklist
- [ ] Código segue padrões do projeto
- [ ] Documentação atualizada
- [ ] Sem warnings do linter
- [ ] Testes cobrem nova funcionalidade
```

---

## 4. CI/CD Pipeline

### 4.1 GitHub Actions Workflow

```yaml
# .github/workflows/ci.yml
name: CI

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main, develop ]

jobs:
  test:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v4
    
    - name: Set up Python
      uses: actions/setup-python@v5
      with:
        python-version: '3.11'
    
    - name: Install dependencies
      run: |
        pip install -r requirements.txt
        pip install -r requirements-dev.txt
    
    - name: Lint with ruff
      run: ruff check aim/ api/ tests/
    
    - name: Type check with mypy
      run: mypy aim/ api/
    
    - name: Test with pytest
      run: pytest tests/ -v --cov=aim --cov-report=xml
    
    - name: Upload coverage
      uses: codecov/codecov-action@v3
      with:
        files: ./coverage.xml

  backtest:
    runs-on: ubuntu-latest
    needs: test
    if: github.ref == 'refs/heads/develop' || github.ref == 'refs/heads/main'
    
    steps:
    - uses: actions/checkout@v4
    
    - name: Set up Python
      uses: actions/setup-python@v5
      with:
        python-version: '3.11'
    
    - name: Install dependencies
      run: pip install -r requirements.txt
    
    - name: Download sample data
      run: python scripts/download_sample_data.py
    
    - name: Run backtest validation
      run: python scripts/validate_strategy.py --quick
    
    - name: Upload backtest results
      uses: actions/upload-artifact@v4
      with:
        name: backtest-results
        path: reports/backtest_latest.html
```

### 4.2 Deploy Automatizado

```yaml
# .github/workflows/deploy.yml
name: Deploy

on:
  push:
    branches: [ main ]

jobs:
  deploy:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v4
    
    - name: Deploy to Render
      env:
        RENDER_API_KEY: ${{ secrets.RENDER_API_KEY }}
      run: |
        curl -X POST \
          -H "Authorization: Bearer $RENDER_API_KEY" \
          -H "Content-Type: application/json" \
          https://api.render.com/v1/services/{service_id}/deploys
```

---

## 5. Ambientes

### 5.1 Local (Desenvolvimento)

```bash
# Setup inicial
git clone [repo]
cd smart-invest
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# Editar .env com suas chaves

# Rodar pipeline diário manualmente
python scripts/daily_update.py

# Iniciar API local
uvicorn api.main:app --reload --port 8000

# Acessar documentação
open http://localhost:8000/docs
```

### 5.2 Staging (Beta)

**Infraestrutura:**
- Plataforma: Render/Railway (free tier)
- Banco: SQLite (com backup automático)
- Dados: Delay de 15 min (brapi gratuito)
- Usuários: Beta testers (10-20 pessoas)

**Deploy:**
```bash
# Merge develop → main
git checkout main
git merge develop
git push origin main

# GitHub Actions faz deploy automático
```

### 5.3 Produção (Futuro)

**Infraestrutura:**
- VPS: Hetzner/DigitalOcean (R$ 30-50/mês)
- Banco: PostgreSQL
- Dados: Tempo real (brapi pago ou similar)
- CDN: CloudFlare (gratuito)
- Monitoramento: UptimeRobot (gratuito)

---

## 6. Monitoramento e Logging

### 6.1 Estrutura de Logs

```python
# aim/utils/logger.py
import logging
import sys
from pathlib import Path

# Criar diretório de logs
LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)

# Configurar logger
def setup_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    
    # Handler para console
    console = logging.StreamHandler(sys.stdout)
    console.setLevel(logging.INFO)
    console.setFormatter(logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    ))
    
    # Handler para arquivo
    file_handler = logging.FileHandler(
        LOG_DIR / f'{name}.log'
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s'
    ))
    
    logger.addHandler(console)
    logger.addHandler(file_handler)
    
    return logger
```

### 6.2 Métricas de Saúde

```python
# Monitorar via endpoint /health
{
    "status": "healthy",           # healthy / degraded / unhealthy
    "timestamp": "2024-02-12T15:30:00Z",
    "version": "1.0.0",
    "checks": {
        "database": {
            "status": "connected",
            "last_update": "2024-02-12",
            "records_count": 42350
        },
        "data_freshness": {
            "prices_last_update": "2024-02-12",
            "prices_age_hours": 2,
            "macro_last_update": "2024-02-12",
            "macro_age_hours": 4
        },
        "daily_job": {
            "last_run": "2024-02-12T06:00:00Z",
            "status": "success",
            "duration_seconds": 45
        }
    }
}
```

---

## 7. Checklist de Qualidade

### 7.1 Antes de Criar PR

- [ ] Código passa em `ruff check`
- [ ] Código passa em `mypy --strict`
- [ ] Testes unitários passam (`pytest`)
- [ ] Cobertura de testes > 70%
- [ ] Backtest executado (se aplicável)
- [ ] Documentação atualizada
- [ ] Sem dados sensíveis (chaves, tokens)
- [ ] `.env` não commitado

### 7.2 Antes de Deploy

- [ ] CI/CD pipeline verde
- [ ] Backtest de validação passou
- [ ] Performance aceitável (< 2s para queries)
- [ ] Backup do banco atualizado
- [ ] Rollback plan definido
- [ ] Health check endpoint funcionando

---

## 8. Documentação Contínua

### 8.1 O Que Documentar

**Obrigatório:**
- Fórmulas matemáticas de cálculos
- Decisões arquiteturais significativas
- Resultados de backtests
- Mudanças em parâmetros do modelo

**Opcional:**
- Detalhes de implementação triviais
- Documentação de bibliotecas externas

### 8.2 Formato: Decision Records

```markdown
# Decision: [Título]

## Data
2024-02-12

## Contexto
[Descrever o problema ou necessidade]

## Decisão
[O que foi decidido]

## Alternativas Consideradas
1. [Alternativa 1] - [Por que não foi escolhida]
2. [Alternativa 2] - [Por que não foi escolhida]

## Consequências
- Positivas: [lista]
- Negativas: [lista]
- Riscos: [lista]

## Validação
- Backtest: [resultados]
- Testes: [descrição]
```

---

**Versão**: 1.0  
**Criado em**: Fevereiro 2026  
**Processo em vigor a partir de**: [data de início do desenvolvimento]
