# Seguranca e Operacao

Atualizado em: 2026-02-21

## Seguranca - Estado Atual

### Implementado

- JWT com `SECRET_KEY` do ambiente (minimo 32 caracteres em producao).
- CORS com origins explicitas via `CORS_ALLOWED_ORIGINS`.
- Sessao por cookie `HttpOnly` (login/refresh/logout).
- Rate limiting de login (janela 10 min, por IP+email).
- Roteamento de prompt com guardrail sem LLM: `asset_query`, `portfolio`, `out_of_scope`.
- Trilha de auditoria (`audit_events`): login, troca de senha, ordens.
- Paginacao e filtros no endpoint de auditoria (`/auth/audit/recent`).
- Retencao automatica de auditoria configuravel (`AUDIT_RETENTION_DAYS`).
- Isolamento logico por tenant nas rotas de simulacao.
- Limites e feature flags por plano (`free`, `edu`, `pro`) com enforcement.

### Lacunas (antes de comercializacao)

- [ ] Token em `localStorage` (vulneravel a XSS). Migrar para cookie-only.
- [ ] Falta headers HTTP de seguranca no proxy (CSP, HSTS, X-Frame-Options).
- [ ] Falta rate limiting geral por rota (nao so login).
- [ ] Falta politica de rotacao/expiracao avancada de sessao.
- [ ] Falta criptografia/segredo gerenciado em producao (vault/secret manager).

### Estrategia de IA

- Motor determinístico de regras = fonte da verdade.
- Agente IA = fallback controlado para linguagem fora de contexto.
- Guardrails obrigatorios:
  - Classificador de intencao antes de chamar LLM.
  - Lista branca de acoes permitidas.
  - Saida estruturada (JSON schema) com validacao.
  - Bloqueio de operacoes sem confirmacao explicita.
  - Respostas didaticas com aviso de risco.

---

## Operacao VPS e Cron

### Objetivo

Atualizar dados e sinais diariamente sem depender de maquina local.

### Infra minima

- 1 VPS (Hetzner CX22 ou equivalente, ~R$28/mes).
- 1 servico da API via `systemd` ou `supervisor`.
- 1 job diario via `cron`.
- 1 log rotativo.

### Fluxo diario recomendado

| Horario (BRT) | Acao |
|--------------|------|
| 02:30 | Backup do banco |
| 03:00 | Atualizacao de dados de mercado/fundamentos |
| 03:20 | Recalculo de features/sinais/regime |
| 03:35 | Validacao de consistencia |
| 03:40 | Reinicio gracioso da API (se necessario) |

### Guard de duplicidade

O backend possui guard de frescor no scheduler interno.
Se o cron ja atualizou, o scheduler nao dispara nova atualizacao.
Recomendacao: manter cron no VPS como fonte principal de agenda.

### Pre-requisitos no VPS

```
/var/www/smart-invest/           # Projeto
/var/www/smart-invest/venv/      # Virtualenv
/var/www/smart-invest/data/      # Banco SQLite
```

Variaveis de ambiente: `BRAPI_TOKEN`, `SECRET_KEY`, `CORS_ALLOWED_ORIGINS`, etc.

### Script de job diario

Arquivo: `/var/www/smart-invest/scripts/run_daily_pipeline.sh`

```bash
#!/usr/bin/env bash
set -euo pipefail
cd /var/www/smart-invest
source venv/bin/activate
mkdir -p logs
STAMP="$(date +%Y-%m-%d_%H-%M-%S)"
LOG_FILE="logs/daily_pipeline_${STAMP}.log"
echo "[INFO] Inicio pipeline: $(date -Iseconds)" | tee -a "$LOG_FILE"
python scripts/daily_update.py 2>&1 | tee -a "$LOG_FILE"
python scripts/generate_signals.py 2>&1 | tee -a "$LOG_FILE"
python scripts/validate_data.py 2>&1 | tee -a "$LOG_FILE"
echo "[INFO] Fim pipeline: $(date -Iseconds)" | tee -a "$LOG_FILE"
```

### Script de backup

Arquivo: `/var/www/smart-invest/scripts/backup_db.sh`

```bash
#!/usr/bin/env bash
set -euo pipefail
cd /var/www/smart-invest
mkdir -p data/backups
STAMP="$(date +%Y-%m-%d_%H-%M-%S)"
cp data/smart_invest.db "data/backups/smart_invest_${STAMP}.db"
find data/backups -type f -name "smart_invest_*.db" -mtime +14 -delete
```

### Crontab

```cron
CRON_TZ=America/Sao_Paulo
30 2 * * 1-5 /var/www/smart-invest/scripts/backup_db.sh >> /var/www/smart-invest/logs/cron_backup.log 2>&1
0 3 * * 1-5 /var/www/smart-invest/scripts/run_daily_pipeline.sh >> /var/www/smart-invest/logs/cron_daily.log 2>&1
```

### Verificacao operacional

```bash
sqlite3 data/smart_invest.db "select max(date) from prices;"
sqlite3 data/smart_invest.db "select max(date) from signals;"
tail -n 80 logs/cron_daily.log
curl -fsS http://127.0.0.1:8000/health
```

### Falha e recuperacao

1. Se pipeline falhar, API continua no ar com ultimo estado valido.
2. Corrigir causa raiz.
3. Rodar job manual: `bash scripts/run_daily_pipeline.sh`
4. Se banco corromper, restaurar de `data/backups/`.

### Checklist de pronto VPS

- [ ] Cron instalado no VPS.
- [ ] Scripts com permissao de execucao (`chmod +x`).
- [ ] Logs sendo gerados.
- [ ] Health check passando apos job diario.
- [ ] Data de `prices` e `signals` atualizada em dia util.
