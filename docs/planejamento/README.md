# Smart Invest - Documentacao de Planejamento

Atualizado em: 2026-02-21

## O Que e o Smart Invest

Sistema quantitativo para investimentos no Brasil (B3) com foco didatico para leigos.

**Diferencial:** Nao e dashboard nem robo simplista. E um sistema disciplinado de decisao quantitativa
baseado em pesquisa academica (AQR, Antonacci, Faber, Simons) com interface em linguagem natural
e orientacao didatica em cada etapa.

**Motor:** Analisa ativos por multiplos fatores (momentum, valor, qualidade, risco), classifica regime
de mercado (Risk ON/OFF), gera recomendacoes com stops e horizonte, e responde em linguagem natural.

## Status Atual

- Backend (FastAPI + SQLite) operacional com motor quantitativo completo.
- Frontend (Next.js) com UX didatica parcialmente padronizada.
- Multitenancy logico implementado (tenant_id + JWT).
- Simulador, recomendacao, historico e plano diario funcionando.
- Seguranca basica aplicada (JWT, rate limit login, CORS, auditoria).
- Deploy: rodando em maquina local (VPS pendente).

## Indice de Documentos

| Arquivo | Conteudo |
|---------|----------|
| [01-visao-produto.md](./01-visao-produto.md) | Proposta de valor, UX didatica, multitenancy, modelo de receita |
| [02-arquitetura-dados.md](./02-arquitetura-dados.md) | Stack real, estrutura do projeto, schema do banco, pipeline de dados |
| [03-seguranca-operacao.md](./03-seguranca-operacao.md) | Estado de seguranca, lacunas, operacao VPS, cron e backup |
| [04-todo-v1.md](./04-todo-v1.md) | TODO de conclusao do v1 com prioridade por sprint |

## Stack

| Camada | Tecnologia |
|--------|-----------|
| Backend | Python 3.11 + FastAPI + Pydantic |
| Banco | SQLite (producao planejada: PostgreSQL) |
| Motor Quant | pandas, numpy, scipy |
| Frontend | Next.js + React + TypeScript |
| Autenticacao | JWT + cookie HttpOnly |
| Deploy atual | Local (VPS Hetzner planejado) |
| Dados | brapi.dev + BCB API + yfinance (fallback) |
