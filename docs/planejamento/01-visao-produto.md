# Visao do Produto

Atualizado em: 2026-02-21

## Proposta de Valor

**Para quem:** Investidores individuais no Brasil (incluindo adolescentes, idosos e iniciantes)
que querem tomar decisoes baseadas em dados sem depender de achismos.

**Problema:** Falta de analise quantitativa acessivel, sobrecarga de informacoes, ausencia de
sistema disciplinado de decisao, e linguagem tecnica que afasta leigos.

**Solucao:** Motor quantitativo (momentum + valor + qualidade + risco) com regime de mercado,
simulador educacional e interface em linguagem natural com orientacao didatica.

## Diferenciais Competitivos

| Aspecto | Smart Invest | Concorrencia (Status Invest, Gorila, Corretoras) |
|---------|-------------|--------------------------------------------------|
| Multi-fator quantitativo | Sim | Nao ou parcial |
| Regime-aware (Risk ON/OFF) | Sim | Nao |
| Backtest | Sim | Nao |
| Linguagem natural | Sim | Nao |
| Didatica para leigos | Sim (padrao fixo) | Nao |
| Custo | Gratis/baixo custo | Gratis a R$300+/mes |

## Principios de UX Didatica

### Formato padrao obrigatorio em toda tela

```
O que aconteceu → Por que importa → O que fazer agora → Qual risco
```

### Regras de linguagem

1. Frases curtas, sem jargao tecnico sem explicacao.
2. Toda recomendacao precisa de motivo e risco em texto humano.
3. Antes de compra/venda, mostrar impacto estimado (consequencia da acao).
4. Checklist pos-acao para reforcar transparencia.

### Funcionalidades didaticas implementadas

- [x] Plano diario da carteira (1 acao + 1 alerta + explicacao).
- [x] Modal didatico de operacao (substitui prompt/alert/confirm).
- [x] Checklist pos-acao no simulador.
- [x] Consequencia da acao antes de compra/venda.
- [x] Bloco didatico fixo no dashboard (4 passos).
- [x] Atalhos guiados para prompt fora de escopo.
- [x] Botao de atualizacao manual com status real do job.

### Funcionalidades didaticas pendentes

- [ ] Padronizar formato em TODAS as telas (algumas ainda nao seguem o padrao).
- [ ] Trilha de onboarding educacional (primeiro uso + primeiros movimentos).
- [ ] Trilha de decisao: `Objetivo → Plano → Risco → Proximo passo`.
- [ ] Simulacao de cenarios: `Base`, `Conservador`, `Estressado` (30 dias).
- [ ] Dicionario didatico de ativos/setores no backend (sem hardcode).
- [ ] Feedback comportamental (giro, concentracao, aderencia ao objetivo).
- [ ] Painel "Aprendizado da semana" (acerto, melhoria, proximo treino).

## Multitenancy

### Estado atual (implementado)

- `tenant_id` em `users` e nas tabelas de simulacao.
- JWT inclui `tenant_id`.
- Todas as rotas de simulacao filtram por `tenant_id + user_id`.
- Planos por tenant: `free`, `edu`, `pro` com feature flags e limites.
- Enforcement de plano: bloqueio de carteira real no `free`, limite de ativos simulados.
- Sidebar com abas dinamicas por capacidade do plano.

### Proximo passo (pendente)

- [ ] Gestao de plano pela interface admin (visualizar, alternar, feature flags, limites).
- [ ] Planejamento de billing simples (limite por plano, sem gateway no primeiro passo).
- [ ] Validacao com banco de producao (isolamento real com multiplos tenants).

## Modelo de Receita

### Fase atual: Uso pessoal

- Validar sistema investindo capital proprio.
- Custo: R$ 0 (desenvolvimento + infra minima).

### Fase futura: Freemium

| Plano | Preco | Acesso |
|-------|-------|--------|
| Free | R$ 0 | Analise basica, simulador com limite |
| Edu | R$ 29/mes | Simulador completo, historico, trilha didatica |
| Pro | R$ 49-149/mes | Carteira real, backtest, alertas, API |

> Billing e gateway de pagamento nao serao implementados no v1.

## Metricas de Sucesso

### Motor quantitativo

- Alpha vs Ibovespa: > 3% ao ano.
- Sharpe Ratio: > 0.8.
- Max Drawdown: < 25%.

### Produto didatico

- 90% das mensagens com formato padrao simples.
- 100% das operacoes com contexto de risco exibido.
- Cobertura minima de universo de ativos definida.
- 100% dos dados sensiveis filtrados por usuario/tenant.
