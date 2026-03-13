"""
Página de Inicio - Resumen general del dashboard.
Muestra KPIs, ranking de entidades y gráficos globales.
"""
import dash_bootstrap_components as dbc
from dash import html, dcc
from components.kpis import kpi_card


def layout():
    """
    Layout de la página de inicio.
    Por ahora solo placeholders, sin callbacks.
    
    Returns:
        dbc.Container con el layout de la página
    """
    return dbc.Container([
        dbc.Row([
            dbc.Col([
                html.H2("Dashboard Estado de Cuenta Mutual", className="page-title"),
                html.P("Resumen general de todas las entidades", className="page-subtitle")
            ])
        ]),
        
        # Panel de KPIs
        dbc.Row([
            dbc.Col([
                html.Div(id="kpi-total-debe", children=kpi_card("Total Debe", "$0.00", "primary"))
            ], md=3),
            dbc.Col([
                html.Div(id="kpi-total-haber", children=kpi_card("Total Haber", "$0.00", "success"))
            ], md=3),
            dbc.Col([
                html.Div(id="kpi-saldo-neto", children=kpi_card("Saldo Neto", "$0.00", "secondary"))
            ], md=3),
            dbc.Col([
                html.Div(id="kpi-entidades-deuda", children=kpi_card("Entidades con Deuda", "0", "danger"))
            ], md=3),
        ], className="mb-4"),
        
        dbc.Row([
            dbc.Col([
                html.Div(id="kpi-periodos-sin-cobranza", children=kpi_card("Períodos sin Cobranza", "0", "warning"))
            ], md=3),
        ], className="mb-4"),
        
        # Gráfico: Ranking de entidades por saldo
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader("Ranking de Entidades por Saldo"),
                    dbc.CardBody([
                        dcc.Graph(id="grafico-ranking-saldo", figure={})
                    ])
                ])
            ], md=12)
        ], className="mb-4"),
        
        # Gráfico: Evolución mensual - total cobrado vs liquidado
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader("Evolución Mensual - Cobrado vs Liquidado"),
                    dbc.CardBody([
                        dcc.Graph(id="grafico-cobrado-vs-liquidado", figure={})
                    ])
                ])
            ], md=12)
        ], className="mb-4"),
        
        # Gráfico: Evolución temporal del saldo total
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader("Evolución Temporal del Saldo Total"),
                    dbc.CardBody([
                        dcc.Graph(id="grafico-evolucion-saldo", figure={})
                    ])
                ])
            ], md=12)
        ], className="mb-4"),
        
        # Tabla: Resumen por entidad
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader("Resumen por Entidad"),
                    dbc.CardBody([
                        html.Div(id="tabla-resumen-entidades", children="Tabla de resumen por entidad")
                    ])
                ])
            ], md=12)
        ], className="mb-4"),
        
    ], fluid=True)
