# Guía de Implementación — Instrucciones para Cursor

## Contexto para el asistente de código

Estás desarrollando un dashboard interactivo con **Python + Dash + Plotly** para una mutual de crédito. El sistema visualiza el estado de cuenta de entidades (municipalidades) que pagan descuentos de empleados públicos. La fuente de datos es una base de datos SQL Server con una tabla principal llamada `ctactetrabajo`.

Lee los archivos `01_contexto_proyecto.md`, `02_modelo_datos.md` y `03_especificacion_dashboard.md` antes de generar código. Úsalos como fuente de verdad para nombres de campos, lógica de negocio y estructura del proyecto.

---

## Reglas estrictas de desarrollo

### Base de datos
- Usar **SQLAlchemy** con `create_engine`. El connection string viene de variable de entorno `DATABASE_URL` en `config.py`.
- **Nunca** concatenar strings para construir queries SQL. Usar siempre `text()` con parámetros nombrados (`:param`).
- Todas las queries van en `db/queries.py` como funciones que reciben parámetros y retornan DataFrames de pandas.
- Usar `pd.read_sql(query, engine, params={...})` para obtener DataFrames.

### Dash / Callbacks
- Cada callback debe tener un único propósito claro.
- Los IDs de componentes deben ser descriptivos: `filtro-entidad`, `grafico-saldo-entidad`, `tabla-movimientos`, etc.
- Usar `Input`, `Output`, `State` de `dash.dependencies`.
- Para inputs que no deben disparar el callback al cargar, usar `prevent_initial_call=True`.
- Implementar `dcc.Loading` wrapper en todos los gráficos para mostrar spinner mientras cargan.

### Estructura de archivos
```
Seguir exactamente la estructura definida en 01_contexto_proyecto.md.
No crear archivos fuera de esa estructura sin justificación.
```

### Manejo de errores
- Todos los callbacks deben tener try/except.
- Si la DB no responde, mostrar mensaje de error en el dashboard, no crashear.
- Validar que los filtros tengan valores antes de ejecutar queries.

---

## Orden de implementación sugerido

### Fase 1 — Base del sistema
1. `config.py` — Leer `DATABASE_URL` desde `.env` con `python-dotenv`
2. `db/connection.py` — Crear y exportar el engine de SQLAlchemy
3. `db/queries.py` — Implementar estas queries primero:
   - `get_entidades()` → lista de todas las entidades para el dropdown
   - `get_saldo_por_entidad(anio=None, cuota=None)` → DataFrame con debe/haber/saldo por entidad
   - `get_movimientos_entidad(idtrabajo, anio=None, cuota=None)` → detalle completo

### Fase 2 — Layout base y navegación
4. `app.py` — Inicializar Dash con Bootstrap, sidebar lateral con links a las 3 páginas
5. `components/filters.py` — Filtros globales (dropdowns de entidad, año)
6. `components/kpis.py` — Tarjetas KPI con valor y color dinámico
7. `pages/inicio.py` — Layout de Página 1 con placeholders

### Fase 3 — Gráficos de la página de inicio
8. `components/charts.py` — Implementar en orden:
   - `build_ranking_saldo(df)` → barras horizontales por saldo (rojo/verde)
   - `build_cobrado_vs_liquidado_global(df)` → barras agrupadas todas las entidades por mes
   - `build_evolucion_saldo(df)` → línea de saldo total acumulado

### Fase 4 — Página Por entidad
9. `pages/entidad.py` — 4 pestañas con dbc.Tabs:
   - Pestaña Resumen: KPIs + barras liquidado vs cobrado + saldo acumulado
   - Pestaña Cuadro de control: cuadro pivote con % diferencia (usar `build_pivot_entidad`)
   - Pestaña Movimientos: tabla detalle exportable
   - Pestaña Análisis: torta por subgrupo + torta por forma de pago + barras comisiones
10. Agregar a `components/charts.py`:
    - `build_torta_subgrupos(df, anio)` → donut de liquidaciones por subgrupo
    - `build_torta_formas_pago(df, anio)` → donut de cobranzas por forma de pago
    - `build_barras_comisiones(df, anio)` → barras de comisiones por período

### Fase 5 — Página Control de carga
11. `data/transformations.py` — `detectar_faltantes(df)`
12. `pages/control.py` — heatmap + tabla de faltantes exportable

### Fase 6 — Polish
13. Exportación a Excel en tablas (Movimientos y faltantes)
14. `assets/style.css` — Ajustes visuales
15. Caché con `diskcache` (opcional)

---

## Snippets de referencia

### Conexión a DB
```python
# config.py
import os
from dotenv import load_dotenv

load_dotenv()

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "3306")
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")

# Umbral de diferencia razonable entre liquidado y cobrado (gastos de procesamiento implícitos)
# Si el % de diferencia supera este valor, el dashboard resalta la celda en rojo
UMBRAL_DIFERENCIA_PCT = 10  # Ajustar según experiencia con las entidades

# Grupos tipo/clase (valores fijos del negocio - no van en .env)
TIPOS_LIQUIDACION_REAL = ["IM", "MI", "IS"]
TIPOS_COBRANZA_REAL    = ["IT", "IA", "IC", "IE"]
TIPOS_LIQUIDACION      = ["IM", "MI", "IS", "CP"]
TIPOS_INGRESOS         = ["IT", "IA", "IC", "IE"]
TIPOS_EGRESOS          = ["ET", "EC", "EE"]
TIPOS_AJUSTES          = ["AN", "AP"]
```

```python
# db/connection.py
import mysql.connector
from mysql.connector import pooling
from config import DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD

connection_pool = pooling.MySQLConnectionPool(
    pool_name="mutual_pool",
    pool_size=5,
    host=DB_HOST,
    port=int(DB_PORT),
    database=DB_NAME,
    user=DB_USER,
    password=DB_PASSWORD
)

def get_connection():
    return connection_pool.get_connection()
```

### Query parametrizada
```python
# db/queries.py
import pandas as pd
from db.connection import get_connection

def _query(sql, params=None):
    """Helper: ejecuta una query y retorna DataFrame. Cierra la conexión siempre."""
    conn = get_connection()
    try:
        df = pd.read_sql(sql, conn, params=params)
        return df
    except Exception as e:
        print(f"Error en query: {e}")
        return pd.DataFrame()
    finally:
        conn.close()

def get_saldo_por_entidad(anio=None, cuota=None):
    """Retorna debe/haber/saldo agrupado por entidad. Filtra por anio y cuota si se pasan."""
    conditions = "WHERE 1=1"
    params = []
    if anio:
        conditions += " AND c.anio = %s"
        params.append(anio)
    if cuota:
        conditions += " AND c.cuota = %s"
        params.append(cuota)
    sql = f"""
        SELECT 
            t.nombre AS entidad,
            c.idtrabajo,
            SUM(c.debe) AS total_debe,
            SUM(c.haber) AS total_haber,
            SUM(c.debe) - SUM(c.haber) AS saldo_neto
        FROM ctactetrabajo c
        JOIN trabajo t ON c.idtrabajo = t.idtrabajo
        {conditions}
        GROUP BY t.nombre, c.idtrabajo
        ORDER BY saldo_neto DESC
    """
    return _query(sql, params or None)
```

### Detección de faltantes
```python
# data/transformations.py
import pandas as pd
from config import TIPOS_LIQUIDACION_REAL, TIPOS_COBRANZA_REAL

def detectar_faltantes(df):
    """
    df: DataFrame completo de ctactetrabajo con columnas idtrabajo, anio, cuota, tipo, clase.
    
    Liquidaciones reales: tipos IM, MI, IS (excluye CP=cierre período, AN/AP=ajustes).
    Cobranzas reales: tipos IT, IA, IC, IE (todos los ingresos por forma de pago).
    
    Retorna DataFrame con columnas:
        idtrabajo, anio, cuota, tiene_liquidacion, tiene_cobranza
    Solo filas donde alguna de las dos es False.
    """
    liquidaciones = df[
        df['tipo'].isin(TIPOS_LIQUIDACION_REAL)
    ][['idtrabajo', 'anio', 'cuota']].drop_duplicates()
    liquidaciones['tiene_liquidacion'] = True

    cobranzas = df[
        df['tipo'].isin(TIPOS_COBRANZA_REAL)
    ][['idtrabajo', 'anio', 'cuota']].drop_duplicates()
    cobranzas['tiene_cobranza'] = True

    todos_periodos = df[
        df['tipo'].isin(TIPOS_LIQUIDACION_REAL + TIPOS_COBRANZA_REAL)
    ][['idtrabajo', 'anio', 'cuota']].drop_duplicates()

    result = todos_periodos \
        .merge(liquidaciones, on=['idtrabajo', 'anio', 'cuota'], how='left') \
        .merge(cobranzas, on=['idtrabajo', 'anio', 'cuota'], how='left')

    result['tiene_liquidacion'] = result['tiene_liquidacion'].fillna(False)
    result['tiene_cobranza'] = result['tiene_cobranza'].fillna(False)

    faltantes = result[~(result['tiene_liquidacion'] & result['tiene_cobranza'])]
    return faltantes
```

### Heatmap de cobertura
```python
# components/charts.py
import plotly.graph_objects as go
import pandas as pd

def build_heatmap_cobertura(df_faltantes, df_entidades):
    """
    df_faltantes: resultado de detectar_faltantes()
    """
    # 0 = completo, 1 = falta cobranza, 2 = falta todo
    def estado(row):
        if not row['tiene_liquidacion'] and not row['tiene_cobranza']:
            return 2
        elif row['tiene_liquidacion'] and not row['tiene_cobranza']:
            return 1
        return 0

    df_faltantes['estado'] = df_faltantes.apply(estado, axis=1)
    df_faltantes['periodo'] = df_faltantes['cuota'].astype(str) + '/' + df_faltantes['anio'].astype(str)

    pivot = df_faltantes.pivot_table(
        index='idtrabajo', columns='periodo', values='estado', aggfunc='max', fill_value=0
    )

    fig = go.Figure(go.Heatmap(
        z=pivot.values,
        x=pivot.columns.tolist(),
        y=pivot.index.tolist(),
        colorscale=[
            [0, '#1D9E75'],   # Verde: todo OK
            [0.5, '#EF9F27'], # Ámbar: falta cobranza
            [1, '#E24B4A'],   # Rojo: falta todo
        ],
        zmin=0, zmax=2,
        showscale=True,
        hovertemplate='Entidad: %{y}<br>Período: %{x}<br>Estado: %{z}<extra></extra>'
    ))

    fig.update_layout(
        title='Cobertura de liquidaciones y cobranzas',
        xaxis_title='Período',
        yaxis_title='Entidad',
        height=max(300, len(pivot.index) * 30),
        margin=dict(l=150, r=20, t=50, b=80),
        paper_bgcolor='white',
        plot_bgcolor='white',
    )
    return fig
```


### Cuadro pivote por entidad (liquidado / cobrado / diferencia / % vs esperado)
```python
# data/transformations.py
import pandas as pd
from config import (TIPOS_LIQUIDACION_REAL, TIPOS_COBRANZA_REAL,
                    PARAMETROS_ENTIDAD, TOLERANCIA_PCT)

MESES = {1:"Ene",2:"Feb",3:"Mar",4:"Abr",5:"May",6:"Jun",
         7:"Jul",8:"Ago",9:"Sep",10:"Oct",11:"Nov",12:"Dic"}

CLASES_COMISION = ["GC", "CO"]

def build_pivot_entidad(df, idtrabajo, idenvio, anio):
    """
    df       : DataFrame de ctactetrabajo filtrado por idtrabajo + idenvio.
    idtrabajo: int — para buscar parámetros esperados en PARAMETROS_ENTIDAD.
    idenvio  : int — ídem.
    anio     : int — año a mostrar en columnas.

    Retorna:
        pivot_df -> DataFrame con filas:
                    Liquidado / Cobrado / Diferencia
                    % Proc. real  / % Proc. esperado
                    % Com. real   / % Com. esperado  (solo si com_esp no es None)
                    Columnas: Ene..Dic
        styles   -> style_data_conditional para dash.DataTable
                    Verde si real está dentro de esperado ± TOLERANCIA_PCT
                    Rojo si está fuera del rango
                    Amarillo si hay cobro sin liquidación
                    Gris si sin actividad
    """
    params   = PARAMETROS_ENTIDAD.get((idtrabajo, idenvio), {"proc": None, "com": None})
    proc_esp = params["proc"]
    com_esp  = params["com"]

    df_anio = df[df["anio"] == anio].copy()

    liq = df_anio[df_anio["tipo"].isin(TIPOS_LIQUIDACION_REAL)].groupby("cuota")["debe"].sum()
    cob = df_anio[df_anio["tipo"].isin(TIPOS_COBRANZA_REAL)].groupby("cuota")["haber"].sum()
    com = df_anio[df_anio["clase"].isin(CLASES_COMISION)].groupby("cuota")["debe"].sum()

    meses_cols = list(range(1, 13))
    liq = liq.reindex(meses_cols, fill_value=0)
    cob = cob.reindex(meses_cols, fill_value=0)
    com = com.reindex(meses_cols, fill_value=0)
    dif      = liq - cob
    pct_proc = (dif / liq.replace(0, float("nan")) * 100).round(1)
    pct_com  = (com / liq.replace(0, float("nan")) * 100).round(1)

    filas = ["Liquidado", "Cobrado", "Diferencia", "% Proc. real"]
    if proc_esp is not None:
        filas.append("% Proc. esperado")
    if com_esp is not None:
        filas += ["% Com. real", "% Com. esperado"]

    pivot = pd.DataFrame({"Concepto": filas})

    for m in meses_cols:
        col   = MESES[m]
        l_val = liq[m]
        c_val = cob[m]
        sin   = (l_val == 0 and c_val == 0)

        vals = [
            f"${l_val:,.0f}" if l_val != 0 else "-",
            f"${c_val:,.0f}" if c_val != 0 else "-",
            f"${dif[m]:,.0f}" if not sin else "-",
            f"{pct_proc[m]:.1f}%" if pd.notna(pct_proc[m]) else ("-" if sin else "100%"),
        ]
        if proc_esp is not None:
            vals.append(f"{proc_esp:.1f}%")
        if com_esp is not None:
            vals.append(f"{pct_com[m]:.1f}%" if pd.notna(pct_com[m]) else "-")
            vals.append(f"{com_esp:.1f}%")
        pivot[col] = vals

    def _color(p_real, p_esp, l_val, c_val):
        if l_val == 0 and c_val == 0:
            return "#E9ECEF"   # gris — sin actividad
        if l_val == 0 and c_val > 0:
            return "#FFF3CD"   # amarillo — cobro sin liquidación cargada
        if p_esp is None or pd.isna(p_real):
            return "#F8D7DA"   # rojo — sin referencia para comparar
        if (p_esp - TOLERANCIA_PCT) <= p_real <= (p_esp + TOLERANCIA_PCT):
            return "#D4EDDA"   # verde — dentro del rango esperado
        return "#F8D7DA"       # rojo — fuera del rango

    styles = []
    for m in meses_cols:
        col = MESES[m]
        styles.append({
            "if": {"filter_query": "{Concepto} = '% Proc. real'", "column_id": col},
            "backgroundColor": _color(pct_proc[m], proc_esp, liq[m], cob[m]),
            "fontWeight": "bold",
        })
        if com_esp is not None:
            styles.append({
                "if": {"filter_query": "{Concepto} = '% Com. real'", "column_id": col},
                "backgroundColor": _color(pct_com[m], com_esp, liq[m], cob[m]),
                "fontWeight": "bold",
            })

    return pivot, styles
```

### KPI con color dinámico
```python
# components/kpis.py
import dash_bootstrap_components as dbc
from dash import html

def kpi_card(titulo, valor, color='primary', icono=None):
    """
    color: 'success' (verde), 'danger' (rojo), 'warning' (ámbar), 'primary' (azul)
    """
    return dbc.Card([
        dbc.CardBody([
            html.P(titulo, className='text-muted mb-1', style={'fontSize': '0.85rem'}),
            html.H4(valor, className=f'text-{color} mb-0 fw-bold'),
        ])
    ], className='shadow-sm mb-3')

def kpi_saldo(saldo_valor):
    """Genera KPI de saldo con color automático según valor"""
    if saldo_valor > 0:
        color = 'danger'
        prefijo = '▲ Deuda: '
    elif saldo_valor < 0:
        color = 'success'
        prefijo = '▼ A favor: '
    else:
        color = 'secondary'
        prefijo = '= Sin saldo: '
    
    valor_str = f"{prefijo}${abs(saldo_valor):,.2f}"
    return kpi_card('Saldo neto', valor_str, color)
```

---

## Variables de entorno requeridas (.env)

```
DATABASE_URL=mssql+pyodbc://usuario:contraseña@servidor/nombre_bd?driver=ODBC+Driver+17+for+SQL+Server
DEBUG=True
PORT=8050
```

> Los grupos tipo/clase no van en `.env` porque son valores fijos del negocio. Van directo en `config.py` como constantes (ver sección Notas importantes).

---

## Requirements.txt

```
dash==2.17.0
dash-bootstrap-components==1.6.0
plotly==5.22.0
pandas==2.2.0
sqlalchemy==2.0.30
pyodbc==5.1.0          # Para SQL Server
python-dotenv==1.0.1
dash-ag-grid==31.2.0   # Para tablas avanzadas
openpyxl==3.1.2        # Para exportar Excel
diskcache==5.6.3       # Para caché opcional
```

---

## Notas importantes para Cursor

- El campo `saldo` en la tabla puede estar desactualizado; **siempre calcular** `SUM(debe) - SUM(haber)` en la query.
- El `idtrabajo` es el identificador de la entidad; unir con tabla `trabajo` para obtener el nombre legible.
- Los valores de `tipo` y `clase` están definidos en `02_modelo_datos.md`. Usar estas constantes directamente en `config.py` (no como variables de entorno, son fijas del negocio):
  ```python
  # Grupos lógicos para filtros y detección de faltantes
  TIPOS_LIQUIDACION = ['IM', 'MI', 'IS', 'CP']
  TIPOS_INGRESOS    = ['IT', 'IA', 'IC', 'IE']   # cobranzas recibidas
  TIPOS_EGRESOS     = ['ET', 'EC', 'EE']           # devoluciones y comisiones
  TIPOS_AJUSTES     = ['AN', 'AP']

  # Para detección de faltantes usar solo estos (excluir CP, AN, AP)
  TIPOS_LIQUIDACION_REAL = ['IM', 'MI', 'IS']
  TIPOS_COBRANZA_REAL    = ['IT', 'IA', 'IC', 'IE']
  ```
- La detección de faltantes es la funcionalidad más crítica del sistema. Tratar con especial cuidado la lógica de comparación de períodos.
