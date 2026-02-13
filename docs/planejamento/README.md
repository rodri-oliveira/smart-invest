# Smart Invest - Documentação de Planejamento

## Índice de Documentos

Esta pasta contém a documentação completa de planejamento do projeto Smart Invest - Sistema de Inteligência Estratégica para Investimentos.

### Ordem de Leitura Recomendada

1. **[01-modelagem-negocio.md](./01-modelagem-negocio.md)**
   - Visão do produto e proposta de valor
   - Análise de mercado e concorrência
   - Modelo de receita (freemium)
   - Canvas de negócio
   - Métricas de sucesso

2. **[02-modelagem-dados.md](./02-modelagem-dados.md)**
   - Diagrama ER completo
   - Esquema de banco de dados (SQLite/PostgreSQL)
   - Tabelas: assets, prices, fundamentals, macro_indicators
   - Tabelas: regime_state, signals, portfolios, backtests
   - Views e triggers
   - Estratégia de backup

3. **[03-stack-arquitetura.md](./03-stack-arquitetura.md)**
   - Stack tecnológica detalhada
   - Estrutura de pastas do projeto
   - Fluxo de dados e pipeline
   - Padrões de código
   - Considerações de performance

4. **[04-processo-desenvolvimento.md](./04-processo-desenvolvimento.md)**
   - Metodologia: Evidence-Based Development
   - Fases de desenvolvimento (16 semanas)
   - Git workflow e convenções
   - CI/CD com GitHub Actions
   - Checklist de qualidade

5. **[05-deploy-operacoes.md](./05-deploy-operacoes.md)**
   - Estratégia de deploy (local → staging → produção)
   - Configuração de VPS (Hetzner/DigitalOcean)
   - Operações diárias automatizadas
   - Monitoramento e alertas
   - Backup e recuperação

---

## Resumo Executivo

### O Que é o Smart Invest?

Sistema quantitativo determinístico para investimentos no Brasil (B3) que:
- **Analisa** ativos por múltiplos fatores (momentum, valor, qualidade, risco)
- **Classifica** o regime de mercado (Risk ON/Risk OFF/Transição)
- **Gera** recomendações estruturadas com stops e horizonte
- **Backtesta** estratégias para validação
- **Responde** em linguagem natural via IA

### Diferencial

Diferente de dashboards e "robôs simplistas", o Smart Invest é um **sistema disciplinado de tomada de decisão quantitativa** baseado em pesquisa acadêmica:
- Jim Simons (Renaissance): Padrões matemáticos
- Cliff Asness (AQR): Factor investing
- Gary Antonacci: Dual momentum
- Meb Faber: Tactical allocation

### Status Atual

- ✅ Documentação completa de planejamento
- ✅ Skill de investimentos quantitativos criada
- ✅ Agente especialista configurado
- ⏳ Fase 1: Data Layer (próximo passo)

### Próximos Passos Imediatos

1. **Criar estrutura de pastas** do projeto Python
2. **Implementar Data Layer** com brapi.dev e SQLite
3. **Popular banco** com 5 anos de dados históricos
4. **Validar qualidade** dos dados
5. **Implementar primeiro indicador** (momentum 6 meses)

---

## Referências Rápidas

### Fontes de Dados
- **brapi.dev**: OHLCV, dividendos, fundamentos (100 req/dia grátis)
- **BCB API**: Selic, IPCA, câmbio (ilimitado grátis)
- **yfinance**: Fallback para dados

### Stack Tecnológica
- **Backend**: Python 3.11 + FastAPI
- **Banco**: SQLite (MVP) → PostgreSQL (escala)
- **Processamento**: pandas, numpy, scipy
- **Deploy**: Render/Railway (free) → VPS (R$ 30-50/mês)
- **Scheduler**: GitHub Actions + APScheduler

### Métricas-Alvo
- Alpha vs Ibovespa: > 3% ao ano
- Sharpe Ratio: > 0.8
- Max Drawdown: < 25%
- Custo mensal: R$ 0 (fase inicial)

---

## Timeline de 16 Semanas

| Semanas | Fase | Entregável | Status |
|---------|------|-----------|--------|
| 1-2 | Data Layer | SQLite + brapi integrado | ⏳ Pendente |
| 3-4 | Features | Momentum, vol, liquidez | ⏳ Pendente |
| 5-6 | Regime | Classificador Risk ON/OFF | ⏳ Pendente |
| 7-8 | Scoring | Ranking multi-fator | ⏳ Pendente |
| 9-10 | Risk/Alloc | Position sizing, stops | ⏳ Pendente |
| 11-12 | Backtest | Métricas, relatórios | ⏳ Pendente |
| 13-14 | API | FastAPI + endpoints | ⏳ Pendente |
| 15-16 | IA | Chat conversacional | ⏳ Pendente |

---

## Custo Zero Inicial

| Componente | Solução | Custo |
|-----------|---------|-------|
| Banco de dados | SQLite local | R$ 0 |
| Dados de mercado | brapi.dev (free tier) | R$ 0 |
| Dados macro | BCB API | R$ 0 |
| Scheduler | GitHub Actions | R$ 0 |
| Deploy inicial | Render/Railway free | R$ 0 |
| **TOTAL** | | **R$ 0** |

---

## Contato e Recursos

- **Projeto**: `C:\projetos\smart-invest`
- **Docs**: `C:\projetos\smart-invest\docs\planejamento\`
- **Skill**: `C:\projetos\smart-invest\.agent\skills\quantitative-investing\`
- **Agent**: `C:\projetos\smart-invest\.agent\agents\investment-specialist.md`

---

**Última atualização**: Fevereiro 2026  
**Versão**: 1.0  
**Status do projeto**: Planejamento completo - Pronto para execução
