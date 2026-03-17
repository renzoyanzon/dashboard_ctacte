"""
Aplicación principal del Dashboard Estado de Cuenta Mutual.
Punto de entrada con Dash, Bootstrap y navegación lateral.
"""
import dash
from dash import dcc, html
import dash_bootstrap_components as dbc
from pages.inicio import layout as layout_inicio, register_callbacks as register_inicio_callbacks
from pages.entidad import layout as layout_entidad, register_callbacks as register_entidad_callbacks
from components.filters import build_filtros
from components.entity_list import build_entity_list

# Inicializar la aplicación Dash con tema Bootstrap
app = dash.Dash(
    __name__,
    external_stylesheets=[
        dbc.themes.BOOTSTRAP,
        'https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap'
    ],
    suppress_callback_exceptions=True
)

# Configurar el título de la aplicación
app.title = "Dashboard Estado de Cuenta Mutual"

# Estructura del layout principal con sidebar fijo
app.layout = dbc.Container([
    dcc.Location(id='url', refresh=False),
    
    dbc.Row([
        # Sidebar fijo a la izquierda
        dbc.Col([
            html.Div([
                html.H4("Dashboard Ctacte", className="sidebar-title"),
                html.Hr(className="sidebar-divider"),
                
                # Navegación
                dbc.Nav([
                    dbc.NavLink("Inicio", href="/", id="nav-inicio", active="exact"),
                    dbc.NavLink("Por entidad", href="/entidad", id="nav-entidad", active="exact"),
                    dbc.NavLink("Control de carga", href="/control", id="nav-control", active="exact"),
                ], vertical=True, pills=True, className="sidebar-nav"),
                
                html.Hr(className="sidebar-divider"),
                
                # Filtros globales (sin dropdown de entidades)
                html.Div(build_filtros(), className="sidebar-filters"),
                
            ], className="sidebar-container")
        ], width=2, style={'padding': 0}),
        
        # Panel de entidades (solo visible en página de inicio)
        dbc.Col([
            html.Div(id='entity-list-container', style={'display': 'none'})
        ], width=2, style={'padding': 0}),
        
        # Contenido principal a la derecha
        dbc.Col([
            html.Div(id='page-content', className="content-area")
        ], width=8, style={'padding': 0})
    ])
], fluid=True, style={'padding': 0})


# Registrar callbacks de las páginas
register_inicio_callbacks(app)
register_entidad_callbacks(app)

# Callback para cambiar el contenido según la URL y mostrar/ocultar panel de entidades
@app.callback(
    [
        dash.dependencies.Output('page-content', 'children'),
        dash.dependencies.Output('entity-list-container', 'children'),
        dash.dependencies.Output('entity-list-container', 'style')
    ],
    [dash.dependencies.Input('url', 'pathname')]
)
def display_page(pathname):
    """
    Renderiza el contenido según la ruta seleccionada.
    Muestra el panel de entidades solo en la página de inicio.
    """
    if pathname == '/entidad':
        return (
            layout_entidad(),
            None,
            {'display': 'none'}
        )
    elif pathname == '/control':
        return (
            html.Div([
                html.H2("Control de Carga"),
                html.P("Página en construcción - Control de faltantes")
            ]),
            None,
            {'display': 'none'}
        )
    else:  # pathname == '/' o cualquier otra ruta
        return (
            layout_inicio(),
            build_entity_list(),
            {'display': 'block'}
        )


if __name__ == '__main__':
    from config import PORT, DEBUG, ENVIRONMENT, DB_HOST, DB_NAME
    print(f"\n{'='*60}")
    print(f"Dashboard Estado de Cuenta Mutual")
    print(f"{'='*60}")
    print(f"Entorno: {ENVIRONMENT.upper()}")
    print(f"Base de datos: {DB_NAME} @ {DB_HOST}")
    print(f"Servidor: http://localhost:{PORT}")
    print(f"Debug: {DEBUG}")
    print(f"{'='*60}\n")
    app.run_server(debug=DEBUG, port=PORT)
