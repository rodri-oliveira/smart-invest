@echo off
echo Ativando venv...
call .\venv\Scripts\activate.bat
echo.
echo Verificando jwt...
python -c "import jwt; print('jwt OK:', jwt.__version__)"
echo.
echo Iniciando servidor...
python -m uvicorn api.main:app --reload --port 8000
pause
