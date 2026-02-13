# Obter Dados Históricos Reais

Para validar o sistema com excelência (backtest, stress tests, paper trading), você precisa de dados históricos reais de 5-10 anos.

## Opção 1: BRAPI (Recomendada)

Fonte mais confiável para dados brasileiros.

1. Acesse: https://brapi.dev
2. Crie conta gratuita (100 requests/dia)
3. Copie seu token
4. Configure `.env`:
   ```
   BRAPI_TOKEN=seu_token_aqui
   ```
5. Rode:
   ```bash
   python scripts/daily_update.py
   ```

## Opção 2: Yahoo Finance + CSV

Alternativa gratuita quando BRAPI não disponível.

1. Acesse: https://finance.yahoo.com
2. Busque ticker com `.SA` (ex: `PETR4.SA`)
3. Vá em "Historical Data"
4. Selecione período máximo (5-10 anos)
5. Clique "Download"
6. Salve em `data/csv_imports/PETR4.csv`
7. Repita para outros ativos:
   - PETR4, VALE3, ITUB4, BBDC4, BBAS3
   - MGLU3, WEGE3, ABEV3, JBSS3, RENT3
8. Importe:
   ```bash
   python scripts/import_csv.py
   ```

## Opção 3: Investing.com

Dados históricos detalhados.

1. Acesse: https://www.investing.com
2. Busque ativo (ex: "Petrobras")
3. Vá em "Dados Históricos"
4. Exportar para CSV
5. Salve em `data/csv_imports/`
6. Rode:
   ```bash
   python scripts/import_csv.py
   ```

## Validação

Após obter dados:

```bash
# Verificar dados
python scripts/check_data.py

# Rodar backtest
python scripts/run_backtest.py

# Stress tests
python scripts/stress_tests.py
```

## Critérios de Excelência

Para considerar o motor pronto:

| Métrica | Target | Mínimo |
|---------|--------|--------|
| Sharpe Ratio | > 0.8 | > 0.5 |
| Max Drawdown | < 20% | < 30% |
| Stress Tests | 5/5 | 3/5 |
| Alpha vs Ibov | > 0 | > -5% |

Se atingir targets → Iniciar paper trading
Se não atingir → Ajustar pesos dos fatores
