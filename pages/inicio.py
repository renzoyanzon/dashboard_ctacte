"""
Página de Inicio - Resumen general del dashboard.
Muestra KPIs, ranking de entidades y gráficos globales.
"""
import dash_bootstrap_components as dbc
from dash import html, dcc, callback, Input, Output, ALL, MATCH, ctx
import pandas as pd
from components.kpis import kpi_card, kpi_saldo, formatear_importe
from components.charts import (
    build_ranking_saldo,
    build_cobrado_vs_liquidado_global,
    build_evolucion_saldo,
    formatear_moneda
)
from db.queries import (
    get_saldo_por_entidad,
    get_liquidado_cobrado_por_periodo,
    get_saldo_acumulado_por_periodo,
    get_totales_liquidado_cobrado,
)


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
                html.H2("Dashboard Estado de Cuenta Entidades", className="page-title"),
                html.P("Resumen general de todas las entidades", className="page-subtitle")
            ])
        ]),
        
        # Panel de KPIs
        dbc.Row([
            dbc.Col([
                html.Div(id="kpi-total-debe", children=kpi_card("Total Liquidación", "$0.00", "primary"))
            ], md=3),
            dbc.Col([
                html.Div(id="kpi-total-haber", children=kpi_card("Total Cobrado", "$0.00", "success"))
            ], md=3),
            dbc.Col([
                html.Div(id="kpi-saldo-neto", children=kpi_card("% Dif", "0,0%", "secondary"))
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


def register_callbacks(app):
    """
    Registra todos los callbacks de la página de inicio.
    """
    
    # Callback para manejar clicks en las entidades (patrón MATCH)
    @app.callback(
        [
            Output('store-entity-selected', 'data'),
            Output({"type": "entity-item", "index": ALL}, "className")
        ],
        [
            Input({"type": "entity-item", "index": ALL}, "n_clicks")
        ],
        prevent_initial_call=False
    )
    def update_selected_entity(n_clicks_list):
        """
        Maneja el click en cualquier item de entidad y actualiza el Store.
        Retorna la clase CSS actualizada para cada item.
        """
        if not ctx.triggered or not n_clicks_list:
            # Estado inicial: "Todas" seleccionada
            from db.queries import get_entidades
            df_entidades = get_entidades()
            total_items = 1 + len(df_entidades)
            classes = ["entity-list-item active"] + ["entity-list-item"] * (total_items - 1)
            return "all", classes
        
        # Obtener el id del item clickeado
        triggered_prop = ctx.triggered[0]["prop_id"]
        # El formato es: '{"type":"entity-item","index":"all"}.n_clicks'
        # Necesitamos extraer el índice
        import json
        import re
        # Buscar el JSON en el string
        match = re.search(r'\{[^}]+\}', triggered_prop)
        if match:
            entity_dict = json.loads(match.group())
            entity_index = entity_dict["index"]
        else:
            entity_index = "all"
        
        # Obtener todas las entidades para construir las clases
        from db.queries import get_entidades
        df_entidades = get_entidades()
        
        # Construir lista de clases
        classes = []
        # Primero "Todas"
        if entity_index == "all":
            classes.append("entity-list-item active")
        else:
            classes.append("entity-list-item")
        
        # Luego todas las entidades
        for _, row in df_entidades.iterrows():
            entity_id = f"{row['idtrabajo']}_{row['envio']}"
            if entity_index == entity_id:
                classes.append("entity-list-item active")
            else:
                classes.append("entity-list-item")
        
        return entity_index, classes
    
    @app.callback(
        [
            Output('kpi-total-debe', 'children'),
            Output('kpi-total-haber', 'children'),
            Output('kpi-saldo-neto', 'children'),
            Output('kpi-entidades-deuda', 'children'),
            Output('grafico-ranking-saldo', 'figure'),
            Output('grafico-cobrado-vs-liquidado', 'figure'),
            Output('grafico-evolucion-saldo', 'figure'),
        ],
        [
            Input('filtro-anio', 'value'),
            Input('store-entity-selected', 'data'),
            Input('filtro-cuota', 'value'),
            Input('btn-actualizar', 'n_clicks')
        ]
    )
    def actualizar_dashboard(anio, entity_selected, cuotas_seleccionadas, n_clicks):
        """
        Callback principal que actualiza todos los KPIs y gráficos.
        """
        try:
            # Convertir cuota a entero si hay selección (multi-select puede venir como lista)
            cuota = None
            if cuotas_seleccionadas:
                # Si es lista, tomar el primer elemento, si es un solo valor, usarlo directamente
                if isinstance(cuotas_seleccionadas, list):
                    if len(cuotas_seleccionadas) == 1:
                        cuota = int(cuotas_seleccionadas[0])
                    # Si hay múltiples cuotas, no filtrar por cuota (mostrar todas)
                else:
                    cuota = int(cuotas_seleccionadas)
            
            # Obtener datos de saldo por entidad (para ranking y entidades con deuda)
            df_saldos = get_saldo_por_entidad(anio=anio, cuota=cuota)
            
            # Inicializar entidades_filtradas antes del if
            entidades_filtradas = []
            
            # Filtrar por entidad seleccionada (desde Store)
            if entity_selected and entity_selected != "all":
                try:
                    idtrabajo, idenvio = entity_selected.split('_')
                    entidades_filtradas = [(int(idtrabajo), int(idenvio))]
                    
                    # Filtrar DataFrame
                    mask = df_saldos.apply(
                        lambda row: (row['idtrabajo'], row['envio']) in entidades_filtradas,
                        axis=1
                    )
                    df_saldos = df_saldos[mask].copy()
                except:
                    entidades_filtradas = []
            
            # KPI: Total liquidación / Total cobrado / % dif
            # Clases pedidas: M, CS, SS y SV (en datos suele ser SF; incluimos ambos por seguridad)
            clases_liq_kpi = ["M", "CS", "SS", "SV", "SF"]
            df_tot = get_totales_liquidado_cobrado(
                anio=anio,
                cuota=cuota,
                entidades=entidades_filtradas if len(entidades_filtradas) > 0 else None,
                clases_liquidacion=clases_liq_kpi,
            )
            # Obtener valores de liquidado y cobrado de forma segura
            if df_tot is not None and not df_tot.empty:
                liquidado = float(df_tot.iloc[0]["liquidado"])
                cobrado = float(df_tot.iloc[0]["cobrado"])
            else:
                liquidado = 0.0
                cobrado = 0.0

            dif_pct = 0.0
            if liquidado > 0:
                dif_pct = ((liquidado - cobrado) / liquidado) * 100.0

            # Mantener saldo_neto para KPI colorizado (se usa en kpi_saldo para el semáforo)
            saldo_neto = liquidado - cobrado
            entidades_deuda = len(df_saldos[df_saldos['saldo_neto'] > 0]) if not df_saldos.empty else 0
            
            # Crear componentes KPI (usar formatear_importe para evitar cortes)
            kpi_debe = kpi_card("Total Liquidación", formatear_importe(liquidado), "primary")
            kpi_haber = kpi_card("Total Cobrado", formatear_importe(cobrado), "success")
            # % dif con coma decimal
            dif_str = f"{dif_pct:.1f}".replace(".", ",") + "%"
            # Color: rojo si > tolerancia (simple), verde si <= 0, ámbar si >0 y <=10
            dif_color = "success" if dif_pct <= 0 else ("warning" if dif_pct <= 10 else "danger")
            kpi_saldo_comp = kpi_card("% Dif", dif_str, dif_color)
            kpi_deuda = kpi_card("Entidades con Deuda", str(entidades_deuda), "danger")
            
            # Construir gráficos
            fig_ranking = build_ranking_saldo(df_saldos)
            
            # Gráfico de liquidado vs cobrado (con filtro de entidad)
            df_liquidado_cobrado = get_liquidado_cobrado_por_periodo(
                anio=anio, 
                entidades=entidades_filtradas if entidades_filtradas else None
            )
            fig_liquidado_cobrado = build_cobrado_vs_liquidado_global(df_liquidado_cobrado)
            
            # Gráfico de evolución de saldo (con filtro de entidad)
            df_saldo_acumulado = get_saldo_acumulado_por_periodo(
                anio=anio,
                entidades=entidades_filtradas if entidades_filtradas else None
            )
            fig_evolucion = build_evolucion_saldo(df_saldo_acumulado)
            
            return (
                kpi_debe,
                kpi_haber,
                kpi_saldo_comp,
                kpi_deuda,
                fig_ranking,
                fig_liquidado_cobrado,
                fig_evolucion
            )
            
        except Exception as e:
            print(f"Error en actualizar_dashboard(): {e}")
            import traceback
            traceback.print_exc()
            
            # Retornar valores por defecto en caso de error
            error_fig = {
                'data': [],
                'layout': {
                    'annotations': [{
                        'text': f'Error: {str(e)}',
                        'xref': 'paper',
                        'yref': 'paper',
                        'x': 0.5,
                        'y': 0.5,
                        'showarrow': False
                    }],
                    'paper_bgcolor': 'transparent',
                    'plot_bgcolor': 'transparent'
                }
            }
            
            return (
                kpi_card("Total Debe", "Error", "secondary"),
                kpi_card("Total Haber", "Error", "secondary"),
                kpi_card("Saldo Neto", "Error", "secondary"),
                kpi_card("Entidades con Deuda", "Error", "secondary"),
                error_fig,
                error_fig,
                error_fig
            )
