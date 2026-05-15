@echo off
cd /d "%~dp0"
echo BANCARIBE C2P
start python scripts/run_server.py
timeout 3
start python scripts/run_dashboard.py
timeout 2
start python sim.py
