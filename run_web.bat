@echo off
rem Inicia BPO Decision Platform 2.0 en modo desarrollo local.
cd /d "%~dp0"
set "BPO_ENV=%LOCALAPPDATA%\BPO_Decision_Platform_2.0_fixed\venv"
if not exist "%BPO_ENV%\Scripts\python.exe" (
  echo No se encontro el entorno Python fuera del proyecto.
  echo Consulta la seccion de instalacion en README.md.
  exit /b 1
)
"%BPO_ENV%\Scripts\python.exe" -m uvicorn bpo_automation.web.app:app --reload --host 127.0.0.1 --port 8000
