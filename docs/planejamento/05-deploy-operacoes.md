# Smart Invest - Deploy e Operações

## 1. Estratégia de Deploy

### 1.1 Filosofia: Gradual e Seguro

> "Deploy não é o fim. É o começo da responsabilidade."

**Princípios:**
1. **Zero-downtime** quando possível
2. **Rollback instantâneo** em caso de problemas
3. **Monitoramento contínuo** pós-deploy
4. **Backup antes de tudo**

### 1.2 Estágios de Deploy

```
┌─────────────────────────────────────────────────────────────┐
│ 1. LOCAL                                                    │
│    • Desenvolvimento e testes                              │
│    • SQLite local, dados de teste                          │
│    • Hot reload, debugging                                   │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼ (push to develop)
┌─────────────────────────────────────────────────────────────┐
│ 2. STAGING (Beta)                                          │
│    • Ambiente de pré-produção                                │
│    • Dados reais, delay 15min                                │
│    • 10-20 usuários beta                                     │
│    • Render/Railway free tier                               │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼ (merge to main + validação)
┌─────────────────────────────────────────────────────────────┐
│ 3. PRODUÇÃO                                                │
│    • Ambiente oficial                                        │
│    • Dados tempo real                                        │
│    • Todos os usuários                                       │
│    • VPS dedicado (Hetzner/DO)                              │
└─────────────────────────────────────────────────────────────┘
```

---

## 2. Plataformas de Deploy

### 2.1 Fase 1-2: Render/Railway (Gratuito)

**Render (recomendado):**
```yaml
# render.yaml
services:
  - type: web
    name: smart-invest-api
    runtime: python
    buildCommand: pip install -r requirements.txt
    startCommand: uvicorn api.main:app --host 0.0.0.0 --port $PORT
    envVars:
      - key: DATABASE_URL
        value: sqlite:///data/smart_invest.db
      - key: PYTHON_VERSION
        value: 3.11.0
    disk:
      name: data
      mountPath: /data
      sizeGB: 1
```

**Vantagens:**
- Deploy automático via Git
- SQLite com disco persistente
- 750h/mês grátis (suficiente)
- HTTPS automático

**Limitações:**
- Cold start (dorme após inatividade)
- Disco limitado a 1GB (free tier)
- Sem banco PostgreSQL nativo (free)

---

### 2.2 Fase 3: VPS (Produção)

**Hetzner Cloud (recomendado - melhor custo/benefício):**
- CX21: 2 vCPU, 4GB RAM, 40GB SSD = €5.35/mês (~R$ 28)
- Localização: Nuremberg (boa latência para Brasil)

**DigitalOcean (alternativa):**
- Droplet básico: $6/mês (~R$ 30)
- App Platform: $0 (static sites), $12 (containers)

**Configuração do VPS:**

```bash
#!/bin/bash
# setup-vps.sh - Script de configuração inicial

# Atualizar sistema
apt update && apt upgrade -y

# Instalar dependências
apt install -y python3.11 python3.11-venv python3-pip git nginx supervisor

# Criar usuário da aplicação
useradd -m -s /bin/bash smartinvest
usermod -aG sudo smartinvest

# Configurar diretório
mkdir -p /var/www/smart-invest
git clone https://github.com/seuuser/smart-invest.git /var/www/smart-invest
chown -R smartinvest:smartinvest /var/www/smart-invest

# Configurar ambiente Python
cd /var/www/smart-invest
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Configurar supervisor
cat > /etc/supervisor/conf.d/smart-invest.conf << EOF
[program:smart-invest]
directory=/var/www/smart-invest
command=/var/www/smart-invest/venv/bin/uvicorn api.main:app --host 127.0.0.1 --port 8000
user=smartinvest
autostart=true
autorestart=true
stderr_logfile=/var/log/smart-invest.err.log
stdout_logfile=/var/log/smart-invest.out.log
environment=DATABASE_URL="sqlite:///data/smart_invest.db",ENVIRONMENT="production"
EOF

supervisorctl reread
supervisorctl update

# Configurar Nginx como reverse proxy
cat > /etc/nginx/sites-available/smart-invest << EOF
server {
    listen 80;
    server_name api.seudominio.com;
    
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
    }
}
EOF

ln -s /etc/nginx/sites-available/smart-invest /etc/nginx/sites-enabled/
rm /etc/nginx/sites-enabled/default
nginx -t
systemctl restart nginx

# Configurar SSL (Certbot)
apt install -y certbot python3-certbot-nginx
certbot --nginx -d api.seudominio.com --non-interactive --agree-tos --email seu@email.com

echo "Setup completo!"
echo "Verificar: systemctl status supervisor"
echo "Logs: tail -f /var/log/smart-invest.out.log"
```

---

## 3. Processo de Deploy

### 3.1 Deploy Automatizado (GitHub Actions)

```yaml
# .github/workflows/deploy-staging.yml
name: Deploy to Staging

on:
  push:
    branches: [ develop ]

jobs:
  deploy:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v4
    
    - name: Deploy to Render
      env:
        RENDER_DEPLOY_HOOK: ${{ secrets.RENDER_DEPLOY_HOOK_URL }}
      run: |
        curl -X POST "$RENDER_DEPLOY_HOOK"
    
    - name: Health Check
      run: |
        sleep 30  # Aguardar cold start
        curl -f https://smart-invest-api.onrender.com/health || exit 1
```

```yaml
# .github/workflows/deploy-production.yml
name: Deploy to Production

on:
  push:
    branches: [ main ]
  workflow_dispatch:  # Manual trigger

jobs:
  deploy:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v4
    
    - name: Setup SSH
      uses: webfactory/ssh-agent@v0.8.0
      with:
        ssh-private-key: ${{ secrets.SSH_PRIVATE_KEY }}
    
    - name: Deploy to VPS
      env:
        HOST: ${{ secrets.VPS_HOST }}
        USER: ${{ secrets.VPS_USER }}
      run: |
        # Backup antes do deploy
        ssh $USER@$HOST "cd /var/www/smart-invest && cp data/smart_invest.db backups/pre-deploy-$(date +%Y%m%d-%H%M%S).db"
        
        # Pull e update
        ssh $USER@$HOST "cd /var/www/smart-invest && git pull origin main"
        ssh $USER@$HOST "cd /var/www/smart-invest && source venv/bin/activate && pip install -r requirements.txt"
        
        # Restart serviço
        ssh $USER@$HOST "sudo supervisorctl restart smart-invest"
        
        # Health check
        sleep 5
        ssh $USER@$HOST "curl -f http://localhost:8000/health || (sudo supervisorctl restart smart-invest && exit 1)"
    
    - name: Notify Success
      if: success()
      run: echo "Deploy para produção concluído com sucesso!"
```

### 3.2 Deploy Manual (Emergência)

```bash
# 1. Conectar ao servidor
ssh smartinvest@seudominio.com

# 2. Backup do banco
cd /var/www/smart-invest
cp data/smart_invest.db backups/manual-$(date +%Y%m%d-%H%M%S).db

# 3. Atualizar código
git pull origin main

# 4. Atualizar dependências
source venv/bin/activate
pip install -r requirements.txt

# 5. Rodar migrações (se houver)
python scripts/migrate.py

# 6. Testar localmente
python -m pytest tests/ -v

# 7. Restart do serviço
sudo supervisorctl restart smart-invest

# 8. Health check
curl http://localhost:8000/health

# 9. Verificar logs (em outro terminal)
tail -f /var/log/smart-invest.out.log
tail -f /var/log/smart-invest.err.log
```

---

## 4. Operações Diárias

### 4.1 Job de Atualização de Dados

```yaml
# .github/workflows/daily-data-update.yml
name: Daily Data Update

on:
  schedule:
    - cron: '0 6 * * 1-5'  # 6:00 AM, de segunda a sexta (horário de Brasília)
  workflow_dispatch:  # Permitir execução manual

jobs:
  update:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v4
    
    - name: Setup Python
      uses: actions/setup-python@v5
      with:
        python-version: '3.11'
    
    - name: Install dependencies
      run: |
        pip install -r requirements.txt
    
    - name: Download database from production
      env:
        HOST: ${{ secrets.VPS_HOST }}
        USER: ${{ secrets.VPS_USER }}
      run: |
        mkdir -p data
        scp $USER@$HOST:/var/www/smart-invest/data/smart_invest.db data/
    
    - name: Run data update
      env:
        BRAPI_TOKEN: ${{ secrets.BRAPI_TOKEN }}
      run: |
        python scripts/daily_update.py --production
    
    - name: Validate data quality
      run: |
        python scripts/validate_data.py
    
    - name: Generate signals
      run: |
        python scripts/generate_signals.py
    
    - name: Upload updated database
      env:
        HOST: ${{ secrets.VPS_HOST }}
        USER: ${{ secrets.VPS_USER }}
      run: |
        scp data/smart_invest.db $USER@$HOST:/var/www/smart-invest/data/
        ssh $USER@$HOST "sudo supervisorctl restart smart-invest"
    
    - name: Send notification (optional)
      if: failure()
      uses: slack/notify-action@v1
      with:
        status: ${{ job.status }}
        text: "⚠️ Falha na atualização diária de dados do Smart Invest"
```

### 4.2 Script de Atualização Local

```python
#!/usr/bin/env python3
# scripts/daily_update.py

import logging
import sys
from pathlib import Path
from datetime import datetime

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/daily_update.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def main():
    logger.info("=" * 60)
    logger.info(f"Iniciando atualização diária - {datetime.now()}")
    logger.info("=" * 60)
    
    try:
        # 1. Atualizar preços de mercado
        logger.info("1. Atualizando preços de mercado...")
        from aim.data_layer.ingestion import update_market_data
        stats = update_market_data()
        logger.info(f"   ✓ {stats['prices_updated']} preços atualizados")
        
        # 2. Atualizar dados macro
        logger.info("2. Atualizando dados macroeconômicos...")
        from aim.data_layer.ingestion import update_macro_data
        stats = update_macro_data()
        logger.info(f"   ✓ {stats['indicators_updated']} indicadores atualizados")
        
        # 3. Calcular features
        logger.info("3. Calculando features...")
        from aim.features.engine import calculate_all_features
        stats = calculate_all_features()
        logger.info(f"   ✓ {stats['assets_processed']} ativos processados")
        
        # 4. Classificar regime
        logger.info("4. Classificando regime de mercado...")
        from aim.regime.classifier import classify_current_regime
        regime = classify_current_regime()
        logger.info(f"   ✓ Regime atual: {regime['regime']} (score: {regime['score']})")
        
        # 5. Calcular scores
        logger.info("5. Calculando scores de ativos...")
        from aim.scoring.engine import calculate_all_scores
        stats = calculate_all_scores()
        logger.info(f"   ✓ {stats['scores_calculated']} scores calculados")
        
        # 6. Gerar relatório
        logger.info("6. Gerando relatório diário...")
        from scripts.generate_report import generate_daily_summary
        report_path = generate_daily_summary()
        logger.info(f"   ✓ Relatório salvo em: {report_path}")
        
        # 7. Backup
        logger.info("7. Realizando backup...")
        from scripts.backup import backup_database
        backup_path = backup_database()
        logger.info(f"   ✓ Backup salvo em: {backup_path}")
        
        logger.info("=" * 60)
        logger.info("✓ Atualização diária concluída com sucesso!")
        logger.info("=" * 60)
        
        return 0
        
    except Exception as e:
        logger.error(f"✗ Erro na atualização: {e}", exc_info=True)
        return 1

if __name__ == "__main__":
    sys.exit(main())
```

---

## 5. Monitoramento

### 5.1 Health Checks

```python
# api/routers/health.py
from fastapi import APIRouter, HTTPException
from datetime import datetime, timedelta
from aim.data_layer.database import get_db

router = APIRouter()

@router.get("/health")
async def health_check():
    """
    Verifica saúde do sistema.
    Retorna status detalhado de todos os componentes.
    """
    checks = {
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0",
        "status": "healthy"
    }
    
    try:
        # Check database
        db = get_db()
        last_price = db.execute(
            "SELECT MAX(date) FROM prices"
        ).fetchone()[0]
        
        price_age = datetime.now() - datetime.strptime(last_price, "%Y-%m-%d")
        
        checks["database"] = {
            "status": "connected",
            "last_update": last_price,
            "age_hours": price_age.total_seconds() / 3600
        }
        
        # Alert if data is stale
        if price_age.days > 2:
            checks["status"] = "degraded"
            checks["warnings"] = ["Dados de preços desatualizados (> 2 dias)"]
        
        # Check last daily job
        # (implementar log de jobs)
        
    except Exception as e:
        checks["status"] = "unhealthy"
        checks["error"] = str(e)
        raise HTTPException(status_code=503, detail=checks)
    
    return checks

@router.get("/health/simple")
async def simple_health():
    """Health check simples para load balancers."""
    return {"status": "ok"}
```

### 5.2 Alertas

```python
# aim/utils/alerts.py
import os
from datetime import datetime

def send_alert(message: str, level: str = "warning"):
    """Envia alerta via múltiplos canais."""
    
    timestamp = datetime.now().isoformat()
    full_message = f"[{timestamp}] [{level.upper()}] {message}"
    
    # 1. Log
    import logging
    logger = logging.getLogger("alerts")
    if level == "critical":
        logger.critical(full_message)
    elif level == "error":
        logger.error(full_message)
    else:
        logger.warning(full_message)
    
    # 2. Slack (se configurado)
    slack_webhook = os.getenv("SLACK_WEBHOOK_URL")
    if slack_webhook:
        import requests
        color = "danger" if level in ["critical", "error"] else "warning"
        requests.post(slack_webhook, json={
            "attachments": [{
                "color": color,
                "text": full_message
            }]
        })
    
    # 3. Email (se configurado)
    # Implementar com SendGrid/AWS SES se necessário

# Exemplos de uso:
# send_alert("Falha na atualização de dados", "critical")
# send_alert("API brapi.dev lenta", "warning")
```

### 5.3 Dashboard de Monitoramento (Simples)

```python
# api/routers/metrics.py
from fastapi import APIRouter
from datetime import datetime, timedelta
import json

router = APIRouter()

@router.get("/metrics/dashboard")
async def get_dashboard_metrics():
    """
    Retorna métricas para dashboard de monitoramento.
    """
    db = get_db()
    
    # Métricas de dados
    total_prices = db.execute(
        "SELECT COUNT(*) FROM prices"
    ).fetchone()[0]
    
    total_assets = db.execute(
        "SELECT COUNT(DISTINCT ticker) FROM prices"
    ).fetchone()[0]
    
    latest_signals = db.execute(
        "SELECT COUNT(*) FROM signals WHERE date = (SELECT MAX(date) FROM signals)"
    ).fetchone()[0]
    
    # Regime atual
    current_regime = db.execute(
        "SELECT regime, score_total FROM regime_state ORDER BY date DESC LIMIT 1"
    ).fetchone()
    
    # Performance (se houver backtests)
    latest_backtest = db.execute(
        """SELECT cagr, sharpe_ratio, max_drawdown, alpha 
           FROM backtests ORDER BY created_at DESC LIMIT 1"""
    ).fetchone()
    
    return {
        "data_freshness": {
            "total_prices_records": total_prices,
            "assets_covered": total_assets,
            "latest_signals_date": latest_signals
        },
        "market_regime": {
            "current": current_regime["regime"] if current_regime else None,
            "score": current_regime["score_total"] if current_regime else None
        },
        "latest_backtest": {
            "cagr": latest_backtest["cagr"] if latest_backtest else None,
            "sharpe": latest_backtest["sharpe_ratio"] if latest_backtest else None,
            "max_drawdown": latest_backtest["max_drawdown"] if latest_backtest else None,
            "alpha": latest_backtest["alpha"] if latest_backtest else None
        } if latest_backtest else None
    }
```

---

## 6. Backup e Recuperação

### 6.1 Estratégia de Backup

```python
# scripts/backup.py
import os
import gzip
import shutil
from datetime import datetime, timedelta
from pathlib import Path

def backup_database():
    """
    Cria backup comprimido do banco de dados.
    Mantém apenas últimos 30 dias.
    """
    DB_PATH = Path("data/smart_invest.db")
    BACKUP_DIR = Path("data/backups")
    BACKUP_DIR.mkdir(exist_ok=True)
    
    # Criar backup
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = BACKUP_DIR / f"smart_invest_{timestamp}.db.gz"
    
    with open(DB_PATH, 'rb') as f_in:
        with gzip.open(backup_file, 'wb') as f_out:
            shutil.copyfileobj(f_in, f_out)
    
    # Limpar backups antigos (> 30 dias)
    cutoff = datetime.now() - timedelta(days=30)
    for backup in BACKUP_DIR.glob("*.gz"):
        # Extrair data do nome
        try:
            date_str = backup.stem.split('_')[2]
            backup_date = datetime.strptime(date_str, "%Y%m%d")
            if backup_date < cutoff:
                backup.unlink()
                print(f"Removido backup antigo: {backup.name}")
        except:
            pass
    
    print(f"✓ Backup criado: {backup_file}")
    return backup_file

def restore_database(backup_file: str):
    """
    Restaura banco de dados a partir de backup.
    """
    DB_PATH = Path("data/smart_invest.db")
    BACKUP_PATH = Path(backup_file)
    
    # Backup do atual (safety)
    if DB_PATH.exists():
        safety_backup = f"{DB_PATH}.safety.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        shutil.copy(DB_PATH, safety_backup)
        print(f"✓ Backup de segurança criado: {safety_backup}")
    
    # Restaurar
    with gzip.open(BACKUP_PATH, 'rb') as f_in:
        with open(DB_PATH, 'wb') as f_out:
            shutil.copyfileobj(f_in, f_out)
    
    print(f"✓ Banco restaurado de: {backup_file}")
```

### 6.2 Backup Offsite (Git LFS ou S3)

```bash
# backup-offsite.sh - Rodar semanalmente

#!/bin/bash
DATE=$(date +%Y%m%d)

# Comprimir backup
pigz -c data/smart_invest.db > /tmp/smart_invest_${DATE}.db.gz

# Enviar para S3 (se configurado)
if [ -n "$AWS_ACCESS_KEY_ID" ]; then
    aws s3 cp /tmp/smart_invest_${DATE}.db.gz s3://smart-invest-backups/
    echo "✓ Backup enviado para S3"
fi

# Ou usar Rclone para Google Drive/Dropbox
if command -v rclone &> /dev/null; then
    rclone copy /tmp/smart_invest_${DATE}.db.gz gdrive:Backups/SmartInvest/
    echo "✓ Backup enviado para Google Drive"
fi

# Limpar temporário
rm /tmp/smart_invest_${DATE}.db.gz
```

---

## 7. Troubleshooting

### 7.1 Problemas Comuns

**API não inicia:**
```bash
# Verificar logs
sudo supervisorctl status smart-invest
sudo tail -f /var/log/smart-invest.err.log

# Problema comum: porta em uso
sudo lsof -i :8000
sudo kill -9 [PID]
sudo supervisorctl restart smart-invest
```

**Dados desatualizados:**
```bash
# Verificar última atualização
sqlite3 data/smart_invest.db "SELECT MAX(date) FROM prices;"

# Rodar atualização manual
python scripts/daily_update.py --verbose

# Verificar se brapi está respondendo
curl https://brapi.dev/api/quote/PETR4
```

**Performance lenta:**
```bash
# Verificar uso de recursos
htop

# Verificar queries lentas no SQLite
# (habilitar query log temporariamente)

# Otimizar banco
sqlite3 data/smart_invest.db "VACUUM;"
sqlite3 data/smart_invest.db "REINDEX;"
sqlite3 data/smart_invest.db "ANALYZE;"
```

**Rollback de deploy:**
```bash
# 1. Identificar último backup funcional
ls -la data/backups/ | tail -5

# 2. Restaurar
python scripts/backup.py --restore data/backups/smart_invest_20240212_060000.db.gz

# 3. Reverter código
git log --oneline -5
git revert HEAD  # ou git checkout [commit-anterior]

# 4. Restart
sudo supervisorctl restart smart-invest
```

---

## 8. Checklist de Operações

### 8.1 Diário (Automatizado)

- [ ] Atualização de dados de mercado (6:00 AM)
- [ ] Cálculo de features e signals
- [ ] Classificação de regime
- [ ] Backup do banco
- [ ] Health check da API

### 8.2 Semanal (Manual)

- [ ] Verificar logs de erro
- [ ] Analisar métricas de performance
- [ ] Validade dos dados vs fontes externas
- [ ] Limpeza de cache antigo
- [ ] Atualização de dependências (se necessário)

### 8.3 Mensal (Manual)

- [ ] Análise de custos de infraestrutura
- [ ] Revisão de métricas de backtest
- [ ] Otimização do banco (VACUUM/REINDEX)
- [ ] Teste de restore de backup
- [ ] Documentação de incidentes (se houver)

### 8.4 Anual (Manual)

- [ ] Revisão completa da arquitetura
- [ ] Avaliação de novas fontes de dados
- [ ] Rebalanceamento de parâmetros do modelo
- [ ] Plano de disaster recovery
- [ ] Preparação para escalabilidade

---

**Versão**: 1.0  
**Criado em**: Fevereiro 2026  
**Ambiente atual**: Staging (Render)
**Próxima meta**: Produção (VPS)
