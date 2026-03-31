"""
Página Control de carga — monitoreo de faltantes y vencimientos.
"""

from __future__ import annotations

from datetime import date

import pandas as pd
import dash_bootstrap_components as dbc
from dash import dcc, html, Input, Output, State, dash_table

from components.kpis import kpi_card
from components.charts import HOVER_HEATMAP_PROC_COM, build_heatmap_cobertura
from config import MESES, VENCIMIENTOS
from db.queries import get_envios_trabajo, get_movimientos_control
from data.transformations import (
    construir_periodos_heatmap_proc_comision,
    detectar_alertas_procesamiento_comision,
    detectar_faltantes,
    calcular_vencimiento,
    calcular_estado_vencimiento,
)


ESTADOS_OPTS = [
    {"label": "Vencidos", "value": "vencido"},
    {"label": "Pendientes", "value": "pendiente"},
    {"label": "Sin config", "value": "sin_config"},
]


def _empty_fig(msg: str):
    import plotly.graph_objects as go

    fig = go.Figure()
    fig.add_annotation(text=msg, xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False)
    fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", height=420)
    return fig


def layout():
    hoy = date.today()
    # años: actual y 4 anteriores
    anios = [hoy.year - i for i in range(5)]
    return dbc.Container(
        [
            dbc.Row(
                [
                    dbc.Col(
                        [
                            html.H2("Control de carga", className="page-title"),
                            html.P(
                                "Cobertura de cobranzas por período y vencimientos.",
                                className="page-subtitle",
                            ),
                        ],
                        md=8,
                    )
                ],
                className="mb-2",
            ),
            dcc.Store(id="control-store-data"),
            dcc.Store(id="control-store-periodos"),
            dcc.Store(id="control-store-heatmap-proc"),
            dcc.Store(id="control-store-heatmap-com"),
            dbc.Row(
                [
                    dbc.Col(html.Div(id="kpi-vencidos"), md=3),
                    dbc.Col(html.Div(id="kpi-pendientes"), md=3),
                    dbc.Col(html.Div(id="kpi-proximo"), md=3),
                    dbc.Col(html.Div(id="kpi-aldia"), md=3),
                ],
                className="mb-3",
            ),
            dbc.Row(
                [
                    dbc.Col(
                        [
                            html.Label("Año", className="form-label mb-2"),
                            dcc.Dropdown(
                                id="control-anio",
                                options=[{"label": str(a), "value": a} for a in anios],
                                value=hoy.year,
                                clearable=False,
                            ),
                        ],
                        md=3,
                    ),
                    dbc.Col(
                        [
                            html.Label("Estado", className="form-label mb-2"),
                            dbc.Checklist(
                                id="control-estados",
                                options=ESTADOS_OPTS,
                                value=["vencido", "pendiente", "sin_config"],
                                inline=True,
                            ),
                        ],
                        md=9,
                    ),
                ],
                className="mb-3",
            ),
            dbc.Row(
                [
                    dbc.Col(
                        dbc.Card(
                            [
                                dbc.CardHeader("Heatmap de cobertura"),
                                dbc.CardBody(
                                    dcc.Loading(
                                        dcc.Graph(
                                            id="control-heatmap",
                                            figure=_empty_fig("Cargando..."),
                                        )
                                    )
                                ),
                            ]
                        ),
                        md=12,
                    )
                ],
                className="mb-3",
            ),
            dbc.Row(
                [
                    dbc.Col(
                        dbc.Card(
                            [
                                dbc.CardHeader("Heatmap — registro de procesamiento"),
                                dbc.CardBody(
                                    [
                                        dcc.Loading(
                                            dcc.Graph(
                                                id="control-heatmap-proc",
                                                figure=_empty_fig("Cargando..."),
                                            )
                                        ),
                                        html.P(
                                            [
                                                html.Span("Verde: ", style={"color": "#1D9E75", "fontWeight": "bold"}),
                                                "liquidación, cobranza y registro de procesamiento. ",
                                                html.Span("Amarillo: ", style={"color": "#EF9F27", "fontWeight": "bold"}),
                                                "liquidación sin cobranza aún. ",
                                                html.Span("Rojo: ", style={"color": "#E24B4A", "fontWeight": "bold"}),
                                                "liquidación y cobranza sin registro. ",
                                                html.Span("Gris: ", style={"color": "#B4B2A9", "fontWeight": "bold"}),
                                                "sin liquidación o sin datos en el período.",
                                            ],
                                            className="small text-muted mt-2 mb-0",
                                        ),
                                    ]
                                ),
                            ]
                        ),
                        md=12,
                    )
                ],
                className="mb-3",
            ),
            dbc.Row(
                [
                    dbc.Col(
                        dbc.Card(
                            [
                                dbc.CardHeader("Heatmap — registro de comisiones liquidación (IM+GC)"),
                                dbc.CardBody(
                                    dcc.Loading(
                                        dcc.Graph(
                                            id="control-heatmap-com",
                                            figure=_empty_fig("Cargando..."),
                                        )
                                    )
                                ),
                            ]
                        ),
                        md=12,
                    )
                ],
                className="mb-3",
            ),
            dbc.Row(
                [
                    dbc.Col(
                        dbc.Card(
                            [
                                dbc.CardHeader("Detalle de celda"),
                                dbc.CardBody(html.Div(id="control-detalle-celda", children="-")),
                            ]
                        ),
                        md=12,
                    )
                ],
                className="mb-3",
            ),
            dbc.Row(
                [
                    dbc.Col(
                        dbc.Card(
                            [
                                dbc.CardHeader(
                                    dbc.Row(
                                        [
                                            dbc.Col("Tabla de faltantes", md=8),
                                            dbc.Col(
                                                dbc.Button(
                                                    "Exportar a Excel",
                                                    id="control-btn-export",
                                                    color="primary",
                                                    className="w-100",
                                                ),
                                                md=4,
                                            ),
                                        ],
                                        className="g-2",
                                    )
                                ),
                                dbc.CardBody(
                                    dash_table.DataTable(
                                        id="control-tabla",
                                        data=[],
                                        columns=[
                                            {"name": c, "id": c}
                                            for c in [
                                                "Entidad",
                                                "Período",
                                                "Liquidación",
                                                "Cobranza",
                                                "Vencimiento",
                                                "Días vencido",
                                                "Estado",
                                            ]
                                        ],
                                        page_size=20,
                                        sort_action="native",
                                        filter_action="native",
                                        style_table={"overflowX": "auto"},
                                        style_cell={
                                            "padding": "8px",
                                            "fontSize": "12px",
                                            "whiteSpace": "nowrap",
                                        },
                                        style_header={"fontWeight": "bold"},
                                        style_data_conditional=[],
                                    )
                                ),
                            ]
                        ),
                        md=12,
                    )
                ]
            ),
            dcc.Download(id="control-download-xlsx"),
            html.Div(id="control-warnings", className="mt-3"),
        ],
        fluid=True,
    )


def register_callbacks(app):
    @app.callback(
        [
            Output("control-store-data", "data"),
            Output("control-store-periodos", "data"),
            Output("control-store-heatmap-proc", "data"),
            Output("control-store-heatmap-com", "data"),
            Output("control-warnings", "children"),
        ],
        [Input("control-anio", "value")],
    )
    def cargar_datos(anio):
        """
        Carga movimientos del año y prepara dataset de períodos con estado.
        """
        try:
            if not anio:
                return None, None, None, None, None

            # Verificación de envíos en trabajo vs config.VENCIMIENTOS
            df_env = get_envios_trabajo()
            keys_db = set(df_env["envio"].dropna().astype(str).tolist()) if df_env is not None and not df_env.empty else set()
            keys_cfg = set(VENCIMIENTOS.keys())
            faltan_en_cfg = sorted(list(keys_db - keys_cfg))
            sobran_en_cfg = sorted(list(keys_cfg - keys_db))

            warns = []
            if faltan_en_cfg:
                warns.append(
                    dbc.Alert(
                        f"Envíos en DB sin config de vencimiento: {', '.join(faltan_en_cfg[:10])}"
                        + ("..." if len(faltan_en_cfg) > 10 else ""),
                        color="warning",
                    )
                )
            if sobran_en_cfg:
                warns.append(
                    dbc.Alert(
                        f"Envíos en config sin match en DB: {', '.join(sobran_en_cfg[:10])}"
                        + ("..." if len(sobran_en_cfg) > 10 else ""),
                        color="secondary",
                    )
                )

            df_mov = get_movimientos_control(int(anio))
            if df_mov is None or df_mov.empty:
                return [], [], [], [], warns

            for col in ["anio", "cuota", "idtrabajo", "idenvio", "debe", "haber"]:
                if col in df_mov.columns:
                    df_mov[col] = pd.to_numeric(df_mov[col], errors="coerce")

            df_alert_pc = detectar_alertas_procesamiento_comision(df_mov)
            if df_alert_pc is not None and not df_alert_pc.empty:
                max_items = 18

                def _fmt_grupo(sub: pd.DataFrame, titulo: str, color: str, pie: str | None = None):
                    if sub.empty:
                        return None
                    items = []
                    for _, r in sub.head(max_items).iterrows():
                        per = f"{int(r['cuota'])}/{int(r['anio'])}"
                        items.append(html.Li(f"{r['entidad_nombre']} — {per}"))
                    more = len(sub) - max_items
                    body = [html.Strong(titulo), html.Ul(items)]
                    if more > 0:
                        body.append(html.P(f"… y {more} más.", className="mb-0 small"))
                    if pie:
                        body.append(html.P(pie, className="mb-0 small text-muted mt-1"))
                    return dbc.Alert(body, color=color, className="mb-2")

                proc_df = df_alert_pc[df_alert_pc["tipo_alerta"] == "PROC"]
                gc_df = df_alert_pc[df_alert_pc["tipo_alerta"] == "GC"]
                a_proc = _fmt_grupo(
                    proc_df,
                    "Falta registro de gasto de procesamiento (IM+GP o IM+GC en haber, según entidad): "
                    "hay cobranza en el período y no hay el movimiento esperado.",
                    "warning",
                    pie="Solo entidades con porcentaje de procesamiento mayor a cero en configuración.",
                )
                a_gc = _fmt_grupo(
                    gc_df,
                    "Falta registro de comisiones liquidación (tipo IM, clase GC en haber): hay liquidación "
                    "y cobranza en el período y no hay movimiento IM+GC.",
                    "warning",
                    pie="Solo entidades con porcentaje de comisión mayor a cero (excluye IM+GC de solo procesamiento).",
                )
                if a_proc is not None:
                    warns.append(a_proc)
                if a_gc is not None:
                    warns.append(a_gc)

            # Detectar faltantes (por idtrabajo+idenvio+anio+cuota)
            df_falt = detectar_faltantes(df_mov)

            # Construir base de períodos "activos": donde hay liquidación o cobranza real
            base_cols = ["idtrabajo", "idenvio", "anio", "cuota"]
            # Flags por período (solo reales)
            from config import TIPOS_LIQUIDACION_REAL, TIPOS_COBRANZA_REAL

            liq = df_mov[df_mov["tipo"].isin(TIPOS_LIQUIDACION_REAL)][base_cols].drop_duplicates()
            liq["tiene_liquidacion"] = True
            cob = df_mov[df_mov["tipo"].isin(TIPOS_COBRANZA_REAL)][base_cols].drop_duplicates()
            cob["tiene_cobranza"] = True

            periodos = (
                df_mov[df_mov["tipo"].isin(TIPOS_LIQUIDACION_REAL + TIPOS_COBRANZA_REAL)][base_cols]
                .drop_duplicates()
                .merge(liq, on=base_cols, how="left")
                .merge(cob, on=base_cols, how="left")
            )
            periodos["tiene_liquidacion"] = periodos["tiene_liquidacion"].fillna(False)
            periodos["tiene_cobranza"] = periodos["tiene_cobranza"].fillna(False)

            # Traer nombres (envio_nombre / entidad_nombre)
            names = df_mov[base_cols + ["envio_nombre", "entidad_nombre"]].drop_duplicates()
            periodos = periodos.merge(names, on=base_cols, how="left")
            periodos["envio_nombre"] = periodos["envio_nombre"].fillna("sin_config")
            periodos["entidad_nombre"] = periodos["entidad_nombre"].fillna(periodos["envio_nombre"])

            # Calcular vencimiento / estado y días vencido
            hoy = date.today()
            fechas = []
            estados = []
            dias = []
            estados_num = []
            for _, r in periodos.iterrows():
                nombre_envio = str(r.get("envio_nombre") or "")
                tiene_cobranza = bool(r.get("tiene_cobranza"))
                estado = calcular_estado_vencimiento(int(r["anio"]), int(r["cuota"]), nombre_envio, tiene_cobranza)
                estados.append(estado)

                params = VENCIMIENTOS.get(nombre_envio)
                if params is None:
                    fechas.append(None)
                    dias.append(None)
                    estados_num.append(3)
                else:
                    fv = calcular_vencimiento(int(r["anio"]), int(r["cuota"]), int(params["desfasaje"]), int(params["dia_corte"]))
                    fechas.append(fv)
                    if estado == "vencido":
                        dias.append((hoy - fv).days)
                        estados_num.append(2)
                    elif estado == "pendiente":
                        dias.append(0)
                        estados_num.append(1)
                    else:  # ok
                        dias.append(0)
                        estados_num.append(0)

            periodos["fecha_venc"] = fechas
            periodos["estado"] = estados
            periodos["dias_vencido"] = dias
            periodos["estado_num"] = estados_num

            df_hm_proc, df_hm_com = construir_periodos_heatmap_proc_comision(df_mov, periodos)
            rec_proc = df_hm_proc.to_dict("records") if df_hm_proc is not None and not df_hm_proc.empty else []
            rec_com = df_hm_com.to_dict("records") if df_hm_com is not None and not df_hm_com.empty else []

            # Dataset para tabla: usar faltantes + estado calculado
            # Tomamos solo filas donde falta cobranza o falta liquidación (detectadas)
            if df_falt is None:
                df_falt = pd.DataFrame()
            if not df_falt.empty:
                df_falt = df_falt.merge(
                    periodos[base_cols + ["envio_nombre", "entidad_nombre", "fecha_venc", "dias_vencido", "estado"]],
                    on=base_cols,
                    how="left",
                    suffixes=("_falt", "_per"),
                )

                # Normalizar nombres para usar la misma nomenclatura que el resto del dashboard
                # (evita columnas envio_nombre_x/y quedando vacías en la tabla)
                if "envio_nombre_per" in df_falt.columns or "envio_nombre_falt" in df_falt.columns:
                    df_falt["envio_nombre"] = (
                        df_falt.get("envio_nombre_per")
                        .combine_first(df_falt.get("envio_nombre_falt"))
                        if df_falt.get("envio_nombre_per") is not None
                        else df_falt.get("envio_nombre_falt")
                    )
                if "entidad_nombre_per" in df_falt.columns or "entidad_nombre_falt" in df_falt.columns:
                    df_falt["entidad_nombre"] = (
                        df_falt.get("entidad_nombre_per")
                        .combine_first(df_falt.get("entidad_nombre_falt"))
                        if df_falt.get("entidad_nombre_per") is not None
                        else df_falt.get("entidad_nombre_falt")
                    )

            return (
                df_falt.to_dict("records"),
                periodos.to_dict("records"),
                rec_proc,
                rec_com,
                warns,
            )
        except Exception as e:
            return [], [], [], [], dbc.Alert(f"Error cargando datos: {str(e)}", color="danger")

    @app.callback(
        [
            Output("kpi-vencidos", "children"),
            Output("kpi-pendientes", "children"),
            Output("kpi-proximo", "children"),
            Output("kpi-aldia", "children"),
            Output("control-heatmap", "figure"),
            Output("control-heatmap-proc", "figure"),
            Output("control-heatmap-com", "figure"),
            Output("control-tabla", "data"),
            Output("control-tabla", "style_data_conditional"),
        ],
        [
            Input("control-store-data", "data"),
            Input("control-store-periodos", "data"),
            Input("control-store-heatmap-proc", "data"),
            Input("control-store-heatmap-com", "data"),
            Input("control-estados", "value"),
            Input("control-anio", "value"),
        ],
    )
    def actualizar_vista(
        falt_records,
        periodos_records,
        hm_proc_records,
        hm_com_records,
        estados_sel,
        anio,
    ):
        try:
            estados_sel = estados_sel or ["vencido", "pendiente", "sin_config"]
            df_falt = pd.DataFrame(falt_records or [])
            df_per = pd.DataFrame(periodos_records or [])

            if df_per.empty:
                fig = _empty_fig("No hay datos para el año seleccionado")
                return (
                    kpi_card("Total vencidos", "0", "danger"),
                    kpi_card("Total pendientes", "0", "warning"),
                    kpi_card("Próximo vencimiento", "-", "secondary"),
                    kpi_card("Porcentaje al día", "0%", "success"),
                    fig,
                    fig,
                    fig,
                    [],
                    [],
                )

            # KPIs
            total_venc = int((df_per["estado"] == "vencido").sum())
            total_pend = int((df_per["estado"] == "pendiente").sum())

            # próximo vencimiento (más cercano sin cobranza)
            df_no_cob = df_per[df_per["estado"].isin(["pendiente", "vencido"])].copy()
            df_no_cob = df_no_cob[df_no_cob["fecha_venc"].notna()].copy()
            if not df_no_cob.empty:
                df_no_cob["fecha_venc"] = pd.to_datetime(df_no_cob["fecha_venc"])
                row = df_no_cob.sort_values("fecha_venc").iloc[0]
                prox = f"{row['envio_nombre']} — {row['fecha_venc'].date().isoformat()}"
            else:
                prox = "-"

            # % al día: ok / períodos activos (excluye sin_config)
            activos = df_per[df_per["estado"] != "sin_config"]
            denom = len(activos) if len(activos) > 0 else 0
            ok = int((activos["estado"] == "ok").sum())
            pct = (ok / denom * 100.0) if denom > 0 else 0.0
            pct_str = f"{pct:.0f}%"

            k1 = kpi_card("Total vencidos", str(total_venc), "danger")
            k2 = kpi_card("Total pendientes", str(total_pend), "warning")
            k3 = kpi_card("Próximo vencimiento", prox, "primary" if prox != "-" else "secondary")
            k4 = kpi_card("Porcentaje al día", pct_str, "success")

            # Heatmaps
            fig = build_heatmap_cobertura(df_per, anio=anio)
            df_proc_hm = pd.DataFrame(hm_proc_records or [])
            df_com_hm = pd.DataFrame(hm_com_records or [])
            fig_proc = build_heatmap_cobertura(
                df_proc_hm,
                anio=anio,
                title="Procesamiento: registro esperado (IM+GP o IM+GC en haber)",
                hover_z_default=HOVER_HEATMAP_PROC_COM,
            )
            fig_com = build_heatmap_cobertura(
                df_com_hm,
                anio=anio,
                title="Comisiones: IM+GC en haber (excluye entidades con solo procesamiento IM+GC)",
                hover_z_default=HOVER_HEATMAP_PROC_COM,
            )

            # Tabla (filtro por estados checklist)
            if not df_falt.empty and "estado" in df_falt.columns:
                df_falt = df_falt[df_falt["estado"].isin(estados_sel)].copy()

            # Armar columnas solicitadas
            def _bool_txt(v):
                return "Sí" if bool(v) else "No"

            if df_falt.empty:
                tabla = []
            else:
                df_falt["Período"] = df_falt.apply(lambda r: f"{int(r['cuota'])}/{int(r['anio'])}", axis=1)
                df_falt["Liquidación"] = df_falt["tiene_liquidacion"].apply(_bool_txt)
                df_falt["Cobranza"] = df_falt["tiene_cobranza"].apply(_bool_txt)
                df_falt["Vencimiento"] = df_falt["fecha_venc"].apply(lambda v: str(v) if pd.notna(v) and v is not None else "-")
                df_falt["Días vencido"] = df_falt["dias_vencido"].apply(lambda v: int(v) if pd.notna(v) and v is not None else "-")
                df_falt["Entidad"] = df_falt.get("entidad_nombre", pd.Series(["-"] * len(df_falt))).fillna("-")
                df_falt["Estado"] = df_falt["estado"]

                # Orden: vencidos primero y luego por días vencido desc
                orden = {"vencido": 0, "pendiente": 1, "sin_config": 2}
                df_falt["_ord"] = df_falt["Estado"].map(orden).fillna(9)
                df_falt["_dias"] = pd.to_numeric(df_falt["dias_vencido"], errors="coerce").fillna(0)
                df_falt = df_falt.sort_values(["_ord", "_dias"], ascending=[True, False])

                tabla = df_falt[
                    ["Entidad", "Período", "Liquidación", "Cobranza", "Vencimiento", "Días vencido", "Estado"]
                ].to_dict("records")

            # Colorización estado
            styles = [
                {"if": {"filter_query": "{Estado} = 'vencido'", "column_id": "Estado"}, "backgroundColor": "#F8D7DA", "color": "#A32D2D", "fontWeight": "bold"},
                {"if": {"filter_query": "{Estado} = 'pendiente'", "column_id": "Estado"}, "backgroundColor": "#FFF3CD", "color": "#856404", "fontWeight": "bold"},
                {"if": {"filter_query": "{Estado} = 'sin_config'", "column_id": "Estado"}, "backgroundColor": "#E9ECEF", "color": "#5F5E5A", "fontWeight": "bold"},
            ]

            return k1, k2, k3, k4, fig, fig_proc, fig_com, tabla, styles
        except Exception as e:
            ef = _empty_fig(f"Error: {str(e)}")
            return (
                kpi_card("Total vencidos", "-", "danger"),
                kpi_card("Total pendientes", "-", "warning"),
                kpi_card("Próximo vencimiento", "-", "secondary"),
                kpi_card("Porcentaje al día", "-", "success"),
                ef,
                ef,
                ef,
                [],
                [],
            )

    @app.callback(
        Output("control-detalle-celda", "children"),
        [Input("control-heatmap", "clickData"), State("control-store-periodos", "data")],
        prevent_initial_call=True,
    )
    def detalle_celda(clickData, periodos_records):
        try:
            if not clickData or not periodos_records:
                return "-"
            cd = clickData["points"][0].get("customdata") or {}
            if not cd:
                return "-"
            entidad = cd.get("entidad_nombre", "-")
            cuota = cd.get("cuota", "-")
            anio = cd.get("anio", "-")
            venc = cd.get("fecha_venc", "-")
            dias = cd.get("dias_vencido")
            dias_txt = f"{dias} días" if dias is not None else "-"
            liq = "Sí" if cd.get("tiene_liquidacion") else "No"
            cob = "Sí" if cd.get("tiene_cobranza") else "No"
            estado = cd.get("estado", "-")

            return html.Div(
                [
                    html.Div([html.B("Entidad: "), entidad]),
                    html.Div([html.B("Período: "), f"{cuota}/{anio}"]),
                    html.Div([html.B("Vencimiento: "), venc]),
                    html.Div([html.B("Días vencido: "), dias_txt]),
                    html.Div([html.B("Liquidación cargada: "), liq]),
                    html.Div([html.B("Cobranza registrada: "), cob]),
                    html.Div([html.B("Estado: "), estado]),
                ]
            )
        except Exception as e:
            return f"Error: {str(e)}"

    @app.callback(
        Output("control-download-xlsx", "data"),
        [Input("control-btn-export", "n_clicks")],
        [State("control-tabla", "data")],
        prevent_initial_call=True,
    )
    def exportar(n, data):
        try:
            if not n:
                return None
            df = pd.DataFrame(data or [])
            fname = f"control_carga_{date.today().isoformat()}.xlsx"
            return dcc.send_data_frame(df.to_excel, fname, index=False)
        except Exception:
            return None

