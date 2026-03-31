"""
Página de Inicio - Resumen general del dashboard.
Muestra SOLO datos agregados generales.

Toda la cobranza agregada en esta página usa cobranza neta (devoluciones descontadas
según PARAMETROS_ENTIDAD). El detalle de devoluciones por entidad solo aplica en
«Por entidad» (Lavalle, Luján, Tupungato).
"""
import dash_bootstrap_components as dbc
from dash import html, dcc, ctx, Input, Output, State
import pandas as pd
import plotly.graph_objects as go

from components.kpis import kpi_card, formatear_importe
from components.charts import build_cobrado_vs_liquidado_global, build_cobranza_neta_por_entidad
from data.transformations import (
    calcular_cobranza_neta_global,
    cobranza_neta_por_fecha_desde_movimientos,
    tabla_cobranza_neta_por_entidad,
)
from db.queries import (
    get_totales_liquidado_cobrado,
    get_saldo_por_entidad,
    get_comisiones_por_periodo,
    get_liquidado_cobrado_por_periodo,
    get_movimientos_cobranza_global,
    get_gastos_procesamiento_global,
)
from config import MESES, COLORES_FORMAS_PAGO, COLOR_ROJO, COLOR_GRIS


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

        # Filtros (aplican a los KPIs superiores)
        dbc.Row(
            [
                dbc.Col(
                    dbc.Card(
                        [
                            dbc.CardHeader("Filtros (toda la página)"),
                            dbc.CardBody(
                                dbc.Row(
                                    [
                                        dbc.Col(
                                            [
                                                html.Label("Año", className="form-label mb-2"),
                                                dcc.Dropdown(
                                                    id="inicio-filtro-anio",
                                                    options=[],
                                                    value=None,
                                                    clearable=False,
                                                    placeholder="Año...",
                                                ),
                                            ],
                                            md=3,
                                        ),
                                        dbc.Col(
                                            [
                                                html.Label("Período (Cuota)", className="form-label mb-2"),
                                                dcc.Dropdown(
                                                    id="inicio-filtro-cuota",
                                                    options=[
                                                        {"label": "Enero", "value": 1},
                                                        {"label": "Febrero", "value": 2},
                                                        {"label": "Marzo", "value": 3},
                                                        {"label": "Abril", "value": 4},
                                                        {"label": "Mayo", "value": 5},
                                                        {"label": "Junio", "value": 6},
                                                        {"label": "Julio", "value": 7},
                                                        {"label": "Agosto", "value": 8},
                                                        {"label": "Septiembre", "value": 9},
                                                        {"label": "Octubre", "value": 10},
                                                        {"label": "Noviembre", "value": 11},
                                                        {"label": "Diciembre", "value": 12},
                                                    ],
                                                    placeholder="Mes(es)...",
                                                    multi=True,
                                                ),
                                            ],
                                            md=6,
                                        ),
                                        dbc.Col(
                                            dbc.Button(
                                                "Actualizar",
                                                id="inicio-btn-actualizar",
                                                color="primary",
                                                className="w-100",
                                            ),
                                            md=3,
                                            className="d-flex align-items-end",
                                        ),
                                    ],
                                    className="g-2",
                                )
                            ),
                        ]
                    ),
                    md=12,
                )
            ],
            className="mb-3",
        ),

        # Store de filtros aplicados (solo cambia al apretar "Actualizar")
        dcc.Store(id="inicio-filtros-aplicados"),
        
        # SECCIÓN 1: KPIs generales (solo agregados)
        dbc.Row([
            dbc.Col([
                html.Div(id="kpi-total-liquidado", children=kpi_card("Total liquidado", "$ 0", "primary"))
            ], md=3),
            dbc.Col([
                html.Div(id="kpi-total-cobrado", children=kpi_card("Total cobrado", "$ 0", "success"))
            ], md=3),
            dbc.Col([
                html.Div(
                    id="kpi-gastos-procesamiento",
                    children=kpi_card("Gastos de procesamiento", "$ 0", "warning"),
                )
            ], md=3),
            dbc.Col([
                html.Div(id="kpi-entidades-activas", children=kpi_card("Entidades activas", "0", "secondary"))
            ], md=3),
        ], className="mb-4"),

        # SECCIÓN 2: Cobrado vs Liquidado por período (global)
        dbc.Row(
            [
                dbc.Col(
                    dbc.Card(
                        [
                            dbc.CardHeader("Cobrado vs Liquidado por período (global)"),
                            dbc.CardBody([dcc.Graph(id="inicio-fig-cobrado-vs-liquidado", figure={})]),
                        ]
                    ),
                    md=12,
                )
            ],
            className="mb-4",
        ),

        # SECCIÓN 3: Evolución de cobranza (año = filtro principal; variación sin filtro de mes)
        dbc.Row(
            [
                dbc.Col(
                    dbc.Card(
                        [
                            dbc.CardHeader(
                                dbc.Row(
                                    [
                                        dbc.Col(html.Div("Evolución de cobranza", className="mb-0"), md=6),
                                        dbc.Col(
                                            dbc.RadioItems(
                                                id="inicio-cobranza-modo",
                                                options=[
                                                    {"label": "Por período", "value": "periodo"},
                                                    {"label": "Por fecha", "value": "fecha"},
                                                ],
                                                value="periodo",
                                                inline=True,
                                                inputClassName="btn-check",
                                                labelClassName="btn btn-outline-primary",
                                                labelCheckedClassName="active",
                                            ),
                                            md=6,
                                            className="text-end",
                                        ),
                                    ],
                                    align="center",
                                )
                            ),
                            dbc.CardBody(
                                [
                                    html.Small(
                                        "Usa el año del filtro superior (sin mes): permite ver la evolución y la variación mes a mes.",
                                        className="text-muted d-block mb-2",
                                    ),
                                    dcc.Graph(id="inicio-fig-cobranza", figure={}),
                                ]
                            ),
                        ]
                    ),
                    md=12,
                )
            ],
            className="mb-2",
        ),

        # SECCIÓN 4: KPIs de variación porcentual (12 períodos con paginación)
        dbc.Row(
            [
                dbc.Col(
                    [
                        dbc.Row(
                            [
                                dbc.Col(html.Div("Variación de cobranza", className="text-muted"), md=6),
                                dbc.Col(
                                    dbc.RadioItems(
                                        id="inicio-kpis-compare",
                                        options=[
                                            {"label": "vs mes anterior", "value": "prev"},
                                            {"label": "vs mismo mes año anterior", "value": "yoy"},
                                        ],
                                        value="prev",
                                        inline=True,
                                        inputClassName="btn-check",
                                        labelClassName="btn btn-outline-secondary",
                                        labelCheckedClassName="active",
                                    ),
                                    md=6,
                                    className="text-end",
                                ),
                            ],
                            align="center",
                            className="mb-2",
                        ),
                        dcc.Store(id="inicio-kpis-page", data=0),
                        dbc.Row(
                            [
                                dbc.Col(
                                    dbc.ButtonGroup(
                                        [
                                            dbc.Button(
                                                "◀",
                                                id="inicio-kpis-prev",
                                                outline=True,
                                                color="secondary",
                                                size="sm",
                                            ),
                                            dbc.Button(
                                                "▶",
                                                id="inicio-kpis-next",
                                                outline=True,
                                                color="secondary",
                                                size="sm",
                                            ),
                                        ]
                                    ),
                                    md=12,
                                    className="text-end mb-2",
                                ),
                            ]
                        ),
                        html.Div(id="inicio-kpis-variacion"),
                    ]
                )
            ],
            className="mb-4",
        ),

        # SECCIÓN 5: Cobranza neta por entidad (% del total)
        dbc.Row(
            [
                dbc.Col(
                    dbc.Card(
                        [
                            dbc.CardHeader("Cobranza neta por entidad (% del total)"),
                            dbc.CardBody([dcc.Graph(id="inicio-fig-cobranza-por-entidad", figure={})]),
                        ]
                    ),
                    md=12,
                )
            ],
            className="mb-4",
        ),

        # SECCIÓN 6: Comisiones totales por período (siempre por anio+cuota)
        dbc.Row(
            [
                dbc.Col(
                    dbc.Card(
                        [
                            dbc.CardHeader("Comisiones totales por período"),
                            dbc.CardBody([dcc.Graph(id="inicio-fig-comisiones", figure={})]),
                        ]
                    ),
                    md=12,
                )
            ],
            className="mb-4",
        ),
        
    ], fluid=True)


def register_callbacks(app):
    """
    Registra todos los callbacks de la página de inicio.
    """

    def _fmt_pesos(valor: float) -> str:
        try:
            v = float(valor)
        except Exception:
            return "$ 0"
        return f"$ {v:,.0f}".replace(",", "X").replace(".", ",").replace("X", ".")

    def _kpi_variacion_card(periodo_label: str, total: float, variacion):
        """
        variacion: None (sin dato), o float porcentaje
        """
        if variacion is None:
            delta_txt = "—"
            color = "secondary"
        else:
            try:
                v = float(variacion)
            except Exception:
                v = None
            if v is None:
                delta_txt = "—"
                color = "secondary"
            else:
                if v > 0:
                    delta_txt = f"▲ {v:.1f}%".replace(".", ",")
                    color = "success"
                elif v < 0:
                    delta_txt = f"▼ {abs(v):.1f}%".replace(".", ",")
                    color = "danger"
                else:
                    delta_txt = "— 0,0%"
                    color = "secondary"

        return dbc.Card(
            dbc.CardBody(
                [
                    html.Div(periodo_label, className="text-muted", style={"fontSize": "12px"}),
                    html.Div(_fmt_pesos(total), className="kpi-value", style={"fontSize": "20px"}),
                    html.Div(delta_txt, className=f"text-{color}", style={"fontWeight": 600}),
                ]
            ),
            className="kpi-card",
        )

    def _empty_fig(msg: str):
        fig = go.Figure()
        fig.add_annotation(text=msg, xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False)
        fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", height=360)
        return fig

    @app.callback(
        Output("inicio-kpis-page", "data"),
        [Input("inicio-kpis-prev", "n_clicks"), Input("inicio-kpis-next", "n_clicks")],
        [State("inicio-kpis-page", "data")],
        prevent_initial_call=True,
    )
    def inicio_kpis_paginar(n_prev, n_next, page):
        try:
            page = int(page or 0)
            trig = ctx.triggered_id
            if trig == "inicio-kpis-prev":
                return page + 1
            if trig == "inicio-kpis-next":
                return max(0, page - 1)
            return page
        except Exception:
            return 0

    @app.callback(
        [Output("inicio-filtro-anio", "options"), Output("inicio-filtro-anio", "value")],
        [Input("inicio-btn-actualizar", "n_clicks")],
        [State("inicio-filtro-anio", "value")],
        prevent_initial_call=False,
    )
    def inicio_filtros_anio(_n, current_value):
        try:
            df = get_movimientos_cobranza_global(anio=None)
            years = (
                pd.to_numeric(df.get("anio"), errors="coerce").dropna().astype(int).unique().tolist()
                if df is not None and not df.empty
                else []
            )
            years = sorted(set(years))
            opts = [{"label": str(y), "value": int(y)} for y in years]
            if current_value is not None and int(current_value) in years:
                val = int(current_value)
            else:
                val = int(years[-1]) if years else None
            return opts, val
        except Exception:
            return [], None

    @app.callback(
        Output("inicio-filtros-aplicados", "data"),
        [Input("inicio-btn-actualizar", "n_clicks")],
        [State("inicio-filtro-anio", "value"), State("inicio-filtro-cuota", "value")],
        prevent_initial_call=False,
    )
    def aplicar_filtros_kpi(_n, anio_val, cuota_vals):
        try:
            return {"anio": anio_val, "cuotas": cuota_vals}
        except Exception:
            return {"anio": None, "cuotas": None}

    @app.callback(
        [
            Output("kpi-total-liquidado", "children"),
            Output("kpi-total-cobrado", "children"),
            Output("kpi-gastos-procesamiento", "children"),
            Output("kpi-entidades-activas", "children"),
            Output("inicio-fig-cobrado-vs-liquidado", "figure"),
            Output("inicio-fig-cobranza", "figure"),
            Output("inicio-kpis-variacion", "children"),
            Output("inicio-fig-cobranza-por-entidad", "figure"),
            Output("inicio-fig-comisiones", "figure"),
        ],
        [
            Input("inicio-filtros-aplicados", "data"),
            Input("inicio-cobranza-modo", "value"),
            Input("inicio-kpis-compare", "value"),
            Input("inicio-kpis-page", "data"),
        ]
    )
    def actualizar_inicio(filtros_aplicados, modo_cobranza, modo_compare, kpis_page):
        try:
            anio = (filtros_aplicados or {}).get("anio")
            cuotas_seleccionadas = (filtros_aplicados or {}).get("cuotas")

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

            # Dataset auxiliar para KPIs (incluye año anterior para YOY y para mes anterior en Enero)
            dff_prev = pd.DataFrame()

            # KPI: Total liquidación / Total cobrado (neto) / diferencia (agregado global)
            clases_liq_kpi = ["M", "CS", "SS", "SV", "SF"]
            df_tot = get_totales_liquidado_cobrado(anio=anio, cuota=cuota, entidades=None, clases_liquidacion=clases_liq_kpi)
            if df_tot is not None and not df_tot.empty:
                liquidado = float(df_tot.iloc[0]["liquidado"])
            else:
                liquidado = 0.0

            df_kpi_mov = get_movimientos_cobranza_global(anio=anio, cuota=cuota)
            df_kpi_net = calcular_cobranza_neta_global(df_kpi_mov)
            if df_kpi_net is not None and not df_kpi_net.empty:
                cobrado = float(df_kpi_net["cobranza_neta"].sum())
            else:
                cobrado = 0.0

            df_gp = get_gastos_procesamiento_global(anio=anio, cuota=cuota)
            if df_gp is not None and not df_gp.empty:
                gastos_proc = float(df_gp.iloc[0]["gastos_procesamiento"])
            else:
                gastos_proc = 0.0

            # Entidades activas (conteo agregado)
            df_act = get_saldo_por_entidad(anio=anio, cuota=cuota)
            entidades_activas = int(len(df_act)) if df_act is not None and not df_act.empty else 0

            kpi_liq = kpi_card("Total liquidado", formatear_importe(liquidado), "primary")
            kpi_cob = kpi_card("Total cobrado", formatear_importe(cobrado), "success")
            kpi_gastos = kpi_card("Gastos de procesamiento", formatear_importe(gastos_proc), "warning")
            kpi_ent = kpi_card("Entidades activas", str(entidades_activas), "secondary")

            tabla_ent = tabla_cobranza_neta_por_entidad(df_kpi_mov)
            fig_ent = build_cobranza_neta_por_entidad(tabla_ent)

            # Evolución + KPIs de variación: año del filtro principal, sin mes/cuota (comparación mes a mes).
            df_raw_evol = get_movimientos_cobranza_global(anio=anio, cuota=None)
            df_net_evol = calcular_cobranza_neta_global(df_raw_evol)

            if modo_cobranza == "fecha":
                dff = cobranza_neta_por_fecha_desde_movimientos(df_raw_evol)
                if not dff.empty:
                    dff = dff.rename(columns={"anio_fecha": "anio", "mes_fecha": "mes"}).copy()
                    dff["anio"] = pd.to_numeric(dff["anio"], errors="coerce").fillna(0).astype(int)
                    dff["mes"] = pd.to_numeric(dff["mes"], errors="coerce").fillna(0).astype(int)
                    dff["total_haber"] = pd.to_numeric(dff["total_haber"], errors="coerce").fillna(0.0)
                    dff = dff[dff["mes"].between(1, 12)].copy()
                    dff["periodo_key"] = dff["anio"] * 100 + dff["mes"]
                    dff = dff.sort_values(["periodo_key"])
                    dff["periodo"] = dff.apply(
                        lambda r: f"{MESES.get(int(r['mes']), r['mes'])} {int(r['anio'])}", axis=1
                    )
                if anio is not None:
                    df_prev_raw = get_movimientos_cobranza_global(anio=anio - 1, cuota=None)
                    dff_prev = cobranza_neta_por_fecha_desde_movimientos(df_prev_raw)
                    if not dff_prev.empty:
                        dff_prev = dff_prev.rename(columns={"anio_fecha": "anio", "mes_fecha": "mes"}).copy()
                        dff_prev["anio"] = pd.to_numeric(dff_prev["anio"], errors="coerce").fillna(0).astype(int)
                        dff_prev["mes"] = pd.to_numeric(dff_prev["mes"], errors="coerce").fillna(0).astype(int)
                        dff_prev["total_haber"] = pd.to_numeric(dff_prev["total_haber"], errors="coerce").fillna(0.0)
                        dff_prev = dff_prev[dff_prev["mes"].between(1, 12)].copy()
                        dff_prev["periodo_key"] = dff_prev["anio"] * 100 + dff_prev["mes"]
                        dff_prev = dff_prev.sort_values(["periodo_key"])
                        dff_prev["periodo"] = dff_prev.apply(
                            lambda r: f"{MESES.get(int(r['mes']), r['mes'])} {int(r['anio'])}", axis=1
                        )
            else:
                df_net = df_net_evol
                if not df_net.empty:
                    dff = df_net.rename(columns={"cobranza_neta": "total_haber"}).copy()
                    dff["mes"] = pd.to_numeric(dff["cuota"], errors="coerce").fillna(0).astype(int)
                    dff["anio"] = pd.to_numeric(dff["anio"], errors="coerce").fillna(0).astype(int)
                    dff["total_haber"] = pd.to_numeric(dff["total_haber"], errors="coerce").fillna(0.0)
                    dff = dff[dff["mes"].between(1, 12)].copy()
                    dff["periodo_key"] = dff["anio"] * 100 + dff["mes"]
                    dff = dff.sort_values(["periodo_key"])
                    dff["periodo"] = dff.apply(
                        lambda r: f"{MESES.get(int(r['mes']), r['mes'])} {int(r['anio'])}", axis=1
                    )
                else:
                    dff = pd.DataFrame()
                if anio is not None:
                    df_prev_raw = get_movimientos_cobranza_global(anio=anio - 1, cuota=None)
                    dff_prev = calcular_cobranza_neta_global(df_prev_raw)
                    if not dff_prev.empty:
                        dff_prev = dff_prev.rename(columns={"cobranza_neta": "total_haber"}).copy()
                        dff_prev["mes"] = pd.to_numeric(dff_prev["cuota"], errors="coerce").fillna(0).astype(int)
                        dff_prev["anio"] = pd.to_numeric(dff_prev["anio"], errors="coerce").fillna(0).astype(int)
                        dff_prev["total_haber"] = pd.to_numeric(dff_prev["total_haber"], errors="coerce").fillna(0.0)
                        dff_prev = dff_prev[dff_prev["mes"].between(1, 12)].copy()
                        dff_prev["periodo_key"] = dff_prev["anio"] * 100 + dff_prev["mes"]
                        dff_prev = dff_prev.sort_values(["periodo_key"])
                        dff_prev["periodo"] = dff_prev.apply(
                            lambda r: f"{MESES.get(int(r['mes']), r['mes'])} {int(r['anio'])}", axis=1
                        )

            if dff is None or dff.empty:
                fig_cob = _empty_fig("Sin datos")
                kpis_variacion = html.Div()
            else:
                # Pivot por tipo (traza por forma de pago)
                pivot = (
                    dff.pivot_table(index=["periodo_key", "periodo"], columns="tipo", values="total_haber", aggfunc="sum")
                    .fillna(0.0)
                    .reset_index()
                    .sort_values("periodo_key")
                )
                fig_cob = go.Figure()
                for tipo in ["IT", "IA", "IC", "IE"]:
                    fig_cob.add_trace(
                        go.Bar(
                            name=tipo,
                            x=pivot["periodo"],
                            y=pivot.get(tipo, pd.Series([0.0] * len(pivot))),
                            marker_color=COLORES_FORMAS_PAGO.get(tipo, COLOR_GRIS),
                            hovertemplate="<b>%{x}</b><br>Tipo: " + tipo + "<br>$%{y:,.2f}<extra></extra>",
                        )
                    )
                fig_cob.update_layout(
                    barmode="stack",
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)",
                    height=420,
                    margin=dict(l=30, r=10, t=10, b=80),
                    xaxis=dict(tickangle=-45),
                    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
                    yaxis_title="Monto cobrado ($)",
                )

                # KPIs de variación:
                # - Los períodos mostrados salen SOLO del dataset actual del gráfico (dff).
                # - Para comparar YOY usamos el dataset previo (dff_prev) pero NO lo mostramos.
                totales_actual = (
                    dff.groupby(["periodo_key", "periodo"], as_index=False)["total_haber"]
                    .sum()
                    .sort_values("periodo_key")
                )
                totales_prev = (
                    dff_prev.groupby(["periodo_key", "periodo"], as_index=False)["total_haber"]
                    .sum()
                    .sort_values("periodo_key")
                    if dff_prev is not None and not dff_prev.empty
                    else pd.DataFrame(columns=["periodo_key", "periodo", "total_haber"])
                )

                keys_sorted_actual = totales_actual["periodo_key"].astype(int).tolist()
                mapa_prev = {int(r["periodo_key"]): float(r["total_haber"]) for _, r in totales_prev.iterrows()}

                page = int(kpis_page or 0)
                end = len(totales_actual) - (page * 6)
                start = max(0, end - 12)
                ventana = (
                    totales_actual.iloc[start:end].reset_index(drop=True)
                    if end > 0
                    else pd.DataFrame(columns=totales_actual.columns)
                )

                cards = []
                for _, r in ventana.iterrows():
                    key = int(r["periodo_key"])
                    actual = float(r["total_haber"])

                    if modo_compare == "yoy":
                        an = key // 100
                        mes = key % 100
                        comp_key = (an - 1) * 100 + mes
                        anterior = mapa_prev.get(comp_key)
                    else:
                        # vs mes anterior: comparación contra el período inmediatamente anterior visible
                        idx = keys_sorted_actual.index(key) if key in keys_sorted_actual else -1
                        comp_key = keys_sorted_actual[idx - 1] if idx > 0 else None
                        anterior = float(totales_actual.iloc[idx - 1]["total_haber"]) if comp_key is not None else None

                    if anterior is None or anterior == 0:
                        var = None
                    else:
                        var = ((actual - anterior) / anterior) * 100.0

                    cards.append(_kpi_variacion_card(str(r["periodo"]), actual, var))

                kpis_variacion = dbc.Row([dbc.Col(c, md=2) for c in cards], className="g-2")

            # Comisiones: mismo año/período que filtros principales
            df_com = get_comisiones_por_periodo(anio=anio)
            if df_com is None or df_com.empty:
                fig_com = _empty_fig("Sin datos")
            else:
                com = df_com.copy()
                com["anio"] = pd.to_numeric(com["anio"], errors="coerce").fillna(0).astype(int)
                com["cuota"] = pd.to_numeric(com["cuota"], errors="coerce").fillna(0).astype(int)
                com["total_comisiones"] = pd.to_numeric(com["total_comisiones"], errors="coerce").fillna(0.0)
                if cuota is not None:
                    com = com[com["cuota"] == int(cuota)]
                com = com[com["cuota"].between(1, 12)].sort_values(["anio", "cuota"])
                if com.empty:
                    fig_com = _empty_fig("Sin datos")
                else:
                    com["periodo"] = com.apply(
                        lambda r: f"{MESES.get(int(r['cuota']), r['cuota'])} {int(r['anio'])}", axis=1
                    )

                    fig_com = go.Figure()
                    fig_com.add_trace(
                        go.Scatter(
                            x=com["periodo"],
                            y=com["total_comisiones"],
                            mode="lines+markers",
                            line=dict(color=COLOR_ROJO, width=2),
                            marker=dict(color=COLOR_ROJO),
                            hovertemplate="<b>%{x}</b><br>Comisiones: $%{y:,.2f}<extra></extra>",
                            name="Comisiones",
                        )
                    )
                    fig_com.update_layout(
                        paper_bgcolor="rgba(0,0,0,0)",
                        plot_bgcolor="rgba(0,0,0,0)",
                        height=360,
                        margin=dict(l=30, r=10, t=10, b=80),
                        xaxis=dict(tickangle=-45),
                        yaxis_title="Monto ($)",
                        showlegend=False,
                    )

            # Cobrado vs Liquidado (global): cobranza neta = mismo alcance que KPIs (año + cuota si aplica)
            df_li = get_liquidado_cobrado_por_periodo(anio=anio, entidades=None)
            if df_kpi_net is not None and not df_kpi_net.empty:
                cob_neta_periodo = df_kpi_net.groupby(["anio", "cuota"], as_index=False)["cobranza_neta"].sum()
            else:
                cob_neta_periodo = pd.DataFrame(columns=["anio", "cuota", "cobranza_neta"])

            if df_li is not None and not df_li.empty:
                df_li = df_li.drop(columns=["cobrado"], errors="ignore")
                df_lc = df_li.merge(cob_neta_periodo, on=["anio", "cuota"], how="outer")
                df_lc["liquidado"] = pd.to_numeric(df_lc.get("liquidado"), errors="coerce").fillna(0.0)
                df_lc["cobrado"] = pd.to_numeric(df_lc.get("cobranza_neta"), errors="coerce").fillna(0.0)
                df_lc = df_lc.drop(columns=["cobranza_neta"], errors="ignore")
                df_lc = df_lc.sort_values(["anio", "cuota"])
            elif not cob_neta_periodo.empty:
                df_lc = cob_neta_periodo.rename(columns={"cobranza_neta": "cobrado"}).copy()
                df_lc["liquidado"] = 0.0
            else:
                df_lc = pd.DataFrame()

            if cuota is not None and not df_lc.empty:
                df_lc = df_lc[df_lc["cuota"] == int(cuota)].copy()

            fig_lc = build_cobrado_vs_liquidado_global(df_lc) if not df_lc.empty else _empty_fig("Sin datos")

            return (
                kpi_liq,
                kpi_cob,
                kpi_gastos,
                kpi_ent,
                fig_lc,
                fig_cob,
                kpis_variacion,
                fig_ent,
                fig_com,
            )

        except Exception as e:
            return (
                kpi_card("Total liquidado", "Error", "secondary"),
                kpi_card("Total cobrado", "Error", "secondary"),
                kpi_card("Gastos de procesamiento", "Error", "secondary"),
                kpi_card("Entidades activas", "Error", "secondary"),
                _empty_fig(f"Error: {str(e)}"),
                _empty_fig("Error"),
                html.Div(),
                _empty_fig("Error"),
                _empty_fig("Error"),
            )
