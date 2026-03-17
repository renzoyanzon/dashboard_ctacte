# Dashboard Ctacte (AMAS) — Dash + Plotly + MySQL

Dashboard web para monitorear **estado de cuenta corriente por entidad** (liquidaciones / cobranzas / saldos) y control de carga por períodos.

La documentación funcional y de datos está en `docs/dashboard_ctacte/`.

## Requisitos

- Python 3.11 (recomendado)
- MySQL (con la tabla `ctactetrabajo`)

## Instalación (Windows / PowerShell)

Crear y activar entorno virtual:

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

Instalar dependencias:

```powershell
pip install -r requirements.txt
```

## Configuración (.env)

Copiar el template y completar credenciales:

```powershell
Copy-Item env.example .env
```

Variables (ver `env.example`):

- **`ENVIRONMENT`**: `development` o `production`
- **DB dev**: `DB_HOST_DEV`, `DB_PORT_DEV`, `DB_NAME_DEV`, `DB_USER_DEV`, `DB_PASSWORD_DEV`
- **DB prod**: `DB_HOST_PROD`, `DB_PORT_PROD`, `DB_NAME_PROD`, `DB_USER_PROD`, `DB_PASSWORD_PROD`
- **App**: `DEBUG` (`True`/`False`), `PORT` (ej. `8050`)

## Ejecutar

Con el venv activo:

```powershell
python app.py
```

Abrir en el navegador:
- `http://localhost:8050`

## Estructura del proyecto

- **`app.py`**: entrypoint Dash + routing
- **`pages/`**:
  - `inicio.py`: dashboard general
  - `entidad.py`: detalle por entidad (tabs)
  - `control.py`: control de carga (faltantes / vencimientos)
- **`components/`**: filtros, KPIs, charts, panel de entidades
- **`db/`**: conexión MySQL + queries (pandas)
- **`data/transformations.py`**: pivotes, faltantes, vencimientos
- **`assets/style.css`**: estilos + variables CSS

## Notas / Troubleshooting

- **`ModuleNotFoundError: dash` o `dash_bootstrap_components`**: asegurate de tener el venv activo y haber corrido `pip install -r requirements.txt`.
- **Control de carga**: los vencimientos se calculan con `date.today()` y `config.VENCIMIENTOS`.

## Documentación

Fuente de verdad:
- `docs/dashboard_ctacte/01_contexto_proyecto.md`
- `docs/dashboard_ctacte/02_modelo_datos.md`
- `docs/dashboard_ctacte/03_especificacion_dashboard.md`
- `docs/dashboard_ctacte/04_guia_implementacion.md`

