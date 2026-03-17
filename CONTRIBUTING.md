# Contribuir al Dashboard Ctacte

Este repo contiene un dashboard en **Python + Dash + Plotly** conectado a **MySQL**.

## Flujo de trabajo

- Crear una rama desde `main`:
  - `feat/<descripcion>` para features
  - `fix/<descripcion>` para bugs
- Hacer commits chicos y descriptivos.
- Abrir Pull Request (PR) hacia `main`.

## Setup local rápido

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item env.example .env
python app.py
```

## Convenciones del proyecto

- **DB**: usamos `mysql-connector-python` + `pandas.read_sql()` con placeholders **`%s`** (nunca concatenar strings con inputs).
- **Manejo de errores**: todos los callbacks deben tener `try/except` y devolver UI “vacía” con mensaje (no crashear).
- **Estilo visual**: colores y consistencia desde `assets/style.css` (`:root`).
- **Nomenclatura**:
  - IDs Dash claros (`filtro-anio`, `control-heatmap`, etc.).
  - Funciones de gráficos en `components/charts.py`.
  - Transformaciones en `data/transformations.py`.

## Checklist antes de abrir PR

- La app levanta con `python app.py` en tu venv.
- Probaste los flujos principales:
  - `Inicio` (filtros + charts)
  - `Por entidad` (tabs + export)
  - `Control de carga` (heatmap + tabla + export)
- No se suben credenciales: `.env` siempre debe quedar ignorado por git.

