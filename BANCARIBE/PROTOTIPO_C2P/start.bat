@echo off
cd /d "%~dp0"
echo ========================================
echo BANCARIBE C2P - SISTEMA COMPLETO
echo ========================================
echo.
echo [1/4] Iniciando API Server...
start "Bancaribe API" cmd /k "python scripts/run_server.py"
timeout /t 3 /nobreak > nul
echo [2/4] Iniciando Dashboard...
start "Bancaribe Dashboard" cmd /k "python scripts/run_dashboard.py"
timeout /t 2 /nobreak > nul
echo [3/4] Iniciando App Movil...
start "Bancaribe Mobile" cmd /k "python scripts/run_mobile.py"
timeout /t 2 /nobreak > nul
echo [4/4] Iniciando Simulador...
start "Bancaribe Simulador" cmd /k "python sim.py"
echo.
echo ========================================
echo SISTEMA INICIADO
echo ========================================
echo API: http://localhost:8000
echo Dashboard: http://localhost:8080
echo App Movil: http://localhost:8081
echo Docs: http://localhost:8000/docs
echo ========================================
echo.
echo Presiona cualquier tecla para cerrar esta ventana...
pause > nul
