# BPO Decision Platform 2.0

Aplicación local para gestión BPO, clasificación de solicitudes, medición TMO y generación de reportes. La versión 2.0 añade una interfaz web con FastAPI y conserva el motor original de Python, el dashboard exportable, el Excel de métricas y la ejecución CLI.

## Arquitectura

- **FastAPI:** API y servidor web local.
- **HTML/CSS/JavaScript:** interfaz web adaptable.
- **Excel (.xlsx):** almacenamiento inicial en las hojas `Solicitudes` y `Agentes`.
- **Pandas/openpyxl:** lectura, análisis y escritura controlada del libro.
- **Motor original:** `scoring.py`, `agents.py`, `pipeline.py`, `report.py` y `metrics_xlsx.py` se conservan.

> Excel es adecuado para desarrollo local y volúmenes pequeños. No es una base de datos multiusuario: no abras el libro en Excel mientras la aplicación esté escribiendo y no ejecutes varias instancias de la app contra el mismo archivo. Para concurrencia real, habrá que migrar la capa de repositorio a PostgreSQL.

## Requisitos

- Windows 10/11
- Python 3.11 o superior
- Visual Studio Code

## Instalación en Visual Studio Code

Abre esta carpeta en VS Code y ejecuta en la terminal PowerShell:

```powershell
$envPath = Join-Path $env:LOCALAPPDATA "BPO_Decision_Platform_2.0_fixed\venv"
$python = Join-Path $env:LOCALAPPDATA "Programs\Python\Python312\python.exe"
& $python -m venv $envPath
& "$envPath\Scripts\python.exe" -m pip install -r requirements-dev.txt
```

Si PowerShell bloquea la activación, puedes ejecutar directamente:

```powershell
& "$env:LOCALAPPDATA\BPO_Decision_Platform_2.0_fixed\venv\Scripts\python.exe" -m pip install -r requirements-dev.txt
```

## Ejecutar la aplicación web

```powershell
& "$env:LOCALAPPDATA\BPO_Decision_Platform_2.0_fixed\venv\Scripts\python.exe" -m uvicorn bpo_automation.web.app:app --reload --host 127.0.0.1 --port 8000
```

Abre en el navegador: <http://127.0.0.1:8000>

Documentación interactiva de la API: <http://127.0.0.1:8000/docs>

También puedes iniciar con doble clic en `run_web.bat` después de instalar dependencias.

## Funcionalidades web

- Dashboard con volumen y distribución de prioridades.
- Consulta y filtro de solicitudes.
- Alta de solicitudes y actualización de estado, urgencia y SLA.
- Vista de rendimiento TMO por agente.
- Registro de nuevas mediciones de agentes.
- Generación y descarga del Excel de métricas, dashboard HTML y reporte TXT.
- Envío manual de reportes por correo desde el Centro de reportes.
- API de estado en `/health`.

Las modificaciones de solicitudes y mediciones se guardan en el libro Excel configurado en `config.toml`.

## Libro Excel

El archivo de ejemplo es `data/sample_dataset.xlsx` y contiene:

- `Solicitudes`: `request_id`, `customer`, `issue`, `category`, `customer_tier`, `urgency`, `sla_hours`, `status`, `created_at`.
- `Agentes`: `agent_name`, `request_id`, `process_seconds`.

Para usar otro libro, cambia `input.dataset` en `config.toml`. Conserva los nombres de hojas y encabezados o ajusta la configuración de mapeo del motor original.

**Importante:** cierra el archivo en Excel antes de crear o modificar registros desde la web. Haz copias de seguridad periódicas.

## Reglas operativas conservadas

- Urgencia: >=9 suma 5; >=7 suma 3; >=4 suma 2; resto suma 1.
- SLA: <=2 horas suma 4; <=4 suma 3; <=8 suma 2.
- Cliente Premium suma 2.
- Prioridades: >=9 CRITICAL; >=7 HIGH; >=4 MEDIUM; resto LOW.
- Meta TMO inicial: 75 segundos. Cumple cuando el promedio del agente es menor o igual a la meta.

## Reportes CLI originales

Solo generar archivos, sin correo:

```powershell
& "$env:LOCALAPPDATA\BPO_Decision_Platform_2.0_fixed\venv\Scripts\python.exe" -m bpo_automation --no-email
```

Preparar un correo de prueba como `.eml`, sin enviarlo:

```powershell
& "$env:LOCALAPPDATA\BPO_Decision_Platform_2.0_fixed\venv\Scripts\python.exe" -m bpo_automation --dry-run
```

El envío automático por CLI requiere habilitarlo en `config.toml`; permanece desactivado por defecto.

Desde el Centro de reportes del dashboard puedes generar y enviar el correo a destinatarios escritos allí. El envío es manual y adjunta el Excel original, el dashboard y el Excel de métricas según las opciones de `[email]` en `config.toml`. Configura `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER` y `SMTP_PASSWORD` en `.env`; nunca pegues la contraseña en el dashboard ni en el chat. En Gmail utiliza una contraseña de aplicación.

## Pruebas

```powershell
pytest -q
```

## Seguridad y límites de esta versión

- La interfaz está pensada para ejecutarse localmente (`127.0.0.1`), no para exponerse directamente a Internet.
- Todavía no incorpora usuarios, roles ni autenticación.
- Excel no ofrece transacciones multiusuario ni bloqueo distribuido.
- El envío desde la interfaz solo ocurre al pulsar explícitamente **Generar y enviar reporte** y requiere credenciales SMTP locales.
- Chart.js no es requerido por la nueva interfaz; las gráficas principales se dibujan con CSS.
