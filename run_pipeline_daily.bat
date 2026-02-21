@echo off
:: Smart Invest - Pipeline Diário Automático
:: Horário: 19:00 (após fechamento da B3)
:: Frequência: Segunda a Sexta-feira (dias úteis)

echo ==========================================
echo  SMART INVEST - Pipeline Diario
echo  %date% %time%
echo ==========================================
echo.

:: Navegar para pasta do projeto
cd /d "C:\projetos\smart-invest"

:: Ativar ambiente virtual
call .\venv\Scripts\activate.bat

:: Verificar se ambiente foi ativado
python -c "import sys; print('Python:', sys.executable)"
echo.

:: Executar pipeline completo
echo [1/4] Atualizando dados de mercado...
python scripts/daily_update.py
if %errorlevel% neq 0 (
    echo ERRO no pipeline! Verifique logs.
    pause
    exit /b 1
)

echo.
echo [2/4] Pipeline concluido!
echo.

:: Opcional: Compactar logs antigos (manter ultimos 7 dias)
echo [3/4] Limpando logs antigos...
forfiles /p "logs" /s /m "*.log" /d -7 /c "cmd /c del @path" 2>nul
echo.

echo [4/4] Status do sistema:
python -c "from aim.data_layer.database import Database; db = Database(); r = db.fetch_one('SELECT COUNT(*) as c FROM prices WHERE date = date(\"now\")'); print(f'  Precos de hoje: {r[\"c\"]} registros')" 2>nul || echo "  (verificacao manual necessaria)"

echo.
echo ==========================================
echo  Pipeline finalizado: %date% %time%
echo ==========================================
echo.

:: Nao fechar automaticamente (para ver resultado)
timeout /t 30 /nobreak >nul
