"""
Componentes de filtros globales para el dashboard.
Los filtros están en el sidebar y afectan a todas las páginas.
"""
import dash_bootstrap_components as dbc
from dash import dcc, html
from db.queries import get_entidades


def build_filtros():
    """
    Construye los filtros globales del sidebar.
    
    Returns:
        dbc.Card con los filtros: entidad (multi-select) y año
    """
    # Obtener entidades desde la base de datos
    df_entidades = get_entidades()
    
    # Crear opciones para el dropdown de entidades
    opciones_entidades = []
    if not df_entidades.empty:
        for _, row in df_entidades.iterrows():
            opciones_entidades.append({
                'label': row['nombre'],
                'value': f"{row['idtrabajo']}_{row['envio']}"
            })
    
    # Obtener años disponibles (últimos 3 años + año actual)
    from datetime import datetime
    año_actual = datetime.now().year
    años = [año_actual - i for i in range(4)]  # Año actual y 3 anteriores
    
    return dbc.Card([
        dbc.CardHeader("Filtros", className="fw-bold"),
        dbc.CardBody([
            html.Label("Entidad", className="form-label mb-2"),
            dcc.Dropdown(
                id='filtro-entidad',
                options=opciones_entidades,
                placeholder="Seleccionar entidad(es)...",
                multi=True,
                className="mb-3",
                style={
                    'color': 'white',
                    'backgroundColor': 'rgba(255, 255, 255, 0.1)'
                }
            ),
            html.Label("Año", className="form-label mb-2"),
            dcc.Dropdown(
                id='filtro-anio',
                options=[{'label': str(año), 'value': año} for año in años],
                value=año_actual,
                placeholder="Seleccionar año...",
                className="mb-3",
                style={
                    'color': 'white',
                    'backgroundColor': 'rgba(255, 255, 255, 0.1)'
                }
            ),
            html.Label("Período (Cuota)", className="form-label mb-2"),
            dcc.Dropdown(
                id='filtro-cuota',
                options=[
                    {'label': 'Enero', 'value': 1},
                    {'label': 'Febrero', 'value': 2},
                    {'label': 'Marzo', 'value': 3},
                    {'label': 'Abril', 'value': 4},
                    {'label': 'Mayo', 'value': 5},
                    {'label': 'Junio', 'value': 6},
                    {'label': 'Julio', 'value': 7},
                    {'label': 'Agosto', 'value': 8},
                    {'label': 'Septiembre', 'value': 9},
                    {'label': 'Octubre', 'value': 10},
                    {'label': 'Noviembre', 'value': 11},
                    {'label': 'Diciembre', 'value': 12},
                ],
                placeholder="Seleccionar mes(es)...",
                multi=True,
                className="mb-3",
                style={
                    'color': 'white',
                    'backgroundColor': 'rgba(255, 255, 255, 0.1)'
                }
            ),
            html.Hr(),
            dbc.Button(
                "Actualizar",
                id="btn-actualizar",
                color="primary",
                className="w-100"
            )
        ])
    ], className="mb-3")
