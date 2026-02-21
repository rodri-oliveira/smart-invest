# TODO de Conclusao - v1

Atualizado em: 2026-02-21

## Linha de corte

Tudo acima da linha e obrigatorio para v1 lancavel. Tudo abaixo e v1.x (melhoria iterativa pos-lancamento).

---

## Sprint 1 — Dados Confiaveis (blocker)

> Sem dados corretos, o motor inteiro perde credibilidade.

- [ ] Corrigir causa raiz de preco travado em subset de ativos (`SANB11`, `WEGE3`) com garantia de frescor por ticker.
- [ ] Integrar Stooq como fallback funcional no pipeline (`aim/data_layer/providers/stooq.py` criado mas nao integrado).
- [ ] Garantir atualizacao por ativo sem falha silenciosa (SLA por ticker).
- [ ] Validar limites diarios das fontes e aplicar throttling inteligente para nao estourar cota free.
- [ ] Mostrar "Cobertura desta atualizacao" no Simulador: `X/Y ativos atualizados`, `N com falha`, `N desatualizados`.
- [ ] Adicionar acao "Tentar novamente apenas ativos com falha".
- [ ] Exibir no frontend o status por ativo: atualizado, desatualizado ou falha na coleta.

## Sprint 2 — Infra de Producao

> Sair da maquina local. Sistema precisa rodar sozinho.

- [ ] Configurar VPS (Hetzner CX22 ou equivalente).
- [ ] Instalar cron ativo e validado (ver `03-seguranca-operacao.md`).
- [ ] Validar operacao com banco real em producao (`tenant_id`, backup/restore, rollback).
- [ ] Health check apos pipeline diario.
- [ ] Revisar copy de atualizacao para deixar explicito: rodando, concluido com sucesso, concluido parcial ou falha.

## Sprint 3 — Seguranca Minima

> Minimo para expor o sistema a outros usuarios.

- [ ] Rate limit por rota critica (nao so login).
- [ ] Headers de seguranca no proxy (CSP, HSTS, X-Frame-Options).
- [ ] Revisao de sessao/token em producao.

## Sprint 4 — Polish UX

> Fechar consistencia da experiencia didatica.

- [ ] Padronizar didatica em todas as telas: `O que aconteceu → Por que importa → O que fazer agora → Qual risco`.
- [ ] Revisar e simplificar copy final para leigo (sem jargao tecnico restante).
- [ ] Fechar consistencia de textos entre Recomendacao, Simulador, Historico e Carteira Real.
- [ ] Fluxo de ativo nao encontrado: erro didatico, sugerir tickers proximos, oferecer "Solicitar inclusao".

## Criterio de "v1 concluido"

- [ ] Atualizacao diaria automatica rodando sem maquina local.
- [ ] Fluxos principais sem `prompt/alert`, com UX didatica consistente.
- [ ] Testes backend/frontend passando + smoke test de producao.
- [ ] Seguranca minima de producao aplicada.
- [ ] Status de cobertura de ativos visivel no frontend.

---

## ✂️ LINHA DE CORTE — Abaixo e pos-lancamento (v1.x)

---

## v1.1 — Linguagem Natural Robusta

- [ ] Fechar motor de perguntas abertas (sinonimos, erros de digitacao, frases livres).
- [ ] Fortalecer fallback para ativo nao encontrado (mensagem didatica + sugestoes + solicitacao).
- [ ] Evoluir fallback de IA com guardrails estritos (quando ativar OpenAI em producao).

## v1.2 — Decisao Guiada (diferencial)

- [ ] Trilha de Decisao em toda recomendacao: `Objetivo → Plano → Risco → Proximo passo`.
- [ ] "Consequencia da acao" mais rica no modal de compra/venda.
- [ ] Simular cenarios didaticos: `Base`, `Conservador`, `Estressado` com faixa esperada (30 dias).

## v1.3 — Educacao Aplicada

- [ ] Completar trilha de onboarding educacional (primeiro uso + primeiros movimentos).
- [ ] Dicionario didatico de ativos/setores no backend (evitar hardcode no frontend).
- [ ] Feedback comportamental sem rotular usuario (giro, concentracao, aderencia ao objetivo).
- [ ] Painel "Aprendizado da semana" (acerto, melhoria, proximo treino).
- [ ] Metricas de valor didatico: entendimento, qualidade da decisao, aderencia ao plano.

## v1.4 — Dados e Operacao Avancada

- [ ] Enriquecer analise historica no simulador (60/90/180 dias + eventos relevantes).
- [ ] Reprocessamento seletivo de ativos stale (atualizar so os tickers desatualizados).
- [ ] Telemetria por ticker na pipeline (fonte usada, tentativas, erro final, duracao).
- [ ] Politica de degradacao amigavel quando houver cobertura parcial de mercado.

## v1.5 — Comercializacao

- [ ] Fechar plano de multitenancy comercial (limites por plano, isolamento logico, base de billing).
- [ ] Gestao de plano pela interface admin (feature flags, limites operacionais).
- [ ] Notificacoes operacionais (email/webhook) para alertas criticos.
- [ ] Painel de metricas de uso didatico.

---

## Itens ja concluidos (referencia)

- [x] Corrigir fluxo de erro em consulta de ativo (404 com mensagem didatica).
- [x] Fallback para ativo nao encontrado com sugestoes + CTA de inclusao.
- [x] Corrigir inconsistencias de feedback na recomendacao (sucesso local vs falha real).
- [x] Upsert por usuario+tenant+ticker na simulacao (UNIQUE constraint).
- [x] Limpeza de mensagens antigas ao trocar de aba.
- [x] Configuracao CORS estavel em dev.
- [x] Corrigir textos UTF-8 e simplificar linguagem para leigos.
- [x] Enriquecer lista de ativos com descricao didatica por ticker.
- [x] SimulatorView com bloco didatico em 4 passos.
- [x] Roteamento de contexto melhorado (saudacao, fora de escopo, reducao falso positivo).
- [x] Desambiguacao de contexto em prompt misto (ativo + carteira).
- [x] Resolucao de ambiguidade no frontend (botoes "Consultar ativo" / "Montar carteira").
- [x] Atalhos guiados para prompt fora de escopo.
- [x] Consequencia da acao no modal de compra/venda.
- [x] Botao manual de atualizacao no Simulador com feedback e status real.
- [x] UX da atualizacao manual refletindo status do job.
- [x] Historico com resumo da ultima acao em linguagem didatica.
- [x] Onboarding de primeiro uso na tela inicial.
- [x] Testes E2E Playwright (consulta → simulador, cenario vazio, alerta com acao).
- [x] Painel de auditoria com paginacao e exportacao CSV.
