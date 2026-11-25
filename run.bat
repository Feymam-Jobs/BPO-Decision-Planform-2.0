@echo off
rem Ejecuta el reporte. Úsalo también para programarlo en el Programador de tareas de Windows.
cd /d "%~dp0"
set "BPO_ENV=%LOCALAPPDATA%\BPO_Decision_Platform_2.0_fixed\venv"
if not exist "%BPO_ENV%\Scripts\python.exe" (
  echo No se encontro el entorno Python fuera del proyecto.
  echo Consulta la seccion de instalacion en README.md.
  exit /b 1
)
"%BPO_ENV%\Scripts\python.exe" -m bpo_automation %*
exit /b %errorlevel%
