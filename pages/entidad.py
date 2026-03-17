"""
Página Por Entidad — detalle completo con pestañas.
"""

from __future__ import annotations

import pandas as pd
import dash_bootstrap_components as dbc
from dash import html, dcc, Input, Output, State, ctx, dash_table

from config import (
    TIPOS_LIQUIDACION_REAL,
    TIPOS_COBRANZA_REAL,
    TIPOS_LIQUIDACION,
    TIPOS_INGRESOS,
    TIPOS_EGRESOS,
    TIPOS_AJUSTES,
    get_nombre_entidad,
)

from db.queries import get_entidades, get_movimientos_entidad
from data.transformations import build_pivot_entidad
from components.charts import (
    build_liquidaciones_vs_cobros,
    build_evolucion_saldo,
    build_torta_subgrupos,
    build_torta_formas_pago,
    build_barras_comisiones,
)


# Mapeos para mostrar textos legibles (según docs/dashboard_ctacte/02_modelo_datos.md)
TIPO_TEXTO = {
    "IM": "Liquidación-manual",
    "MI": "Liquidación- migración",
    "IS": "Liquidación-sistema",
    "CP": "Cierre periodo",
    "IT": "Ingresos transferencia",
    "IA": "Ingresos FDC",
    "IC": "Ingresos cheque",
    "IE": "Ingresos efectivo",
    "ET": "Egresos transferencia",
    "EC": "Egresos cheque",
    "EE": "Egresos efectivo",
    "AN": "Ajuste (AN)",
    "AP": "Ajuste (AP)",
}

CLASE_TEXTO = {
    "M": "Mutuos",
    "CS": "Cuota Social",
    "SS": "Sepelio",
    "SF": "Fallecimiento",
    "GC": "Gastos de comisiones (GC)",
    "CO": "Comisiones (CO)",
    "GP": "Procesamiento",
    "DV": "Devoluciones",
    "TR": "Cobro de terceros",
    "RG": "Recupero de gastos",
    "GV": "Varios",
    "DI": "Falta imputación",
    "SI": "Saldo inicial",
    "CP": "Cierre período",
    "C": "Cobranza",
}


def _fmt_pesos_signed(valor: float) -> str:
    try:
        v = float(valor)
    except Exception:
        return "-"
    if v == 0:
        return "$ 0"
    s_abs = f"{abs(v):,.0f}".replace(",", "X").replace(".", ",").replace("X", ".")
    sign = "-" if v < 0 else ""
    return f"{sign}$ {s_abs}"


def _empty_fig(msg: str):
    import plotly.graph_objects as go

    fig = go.Figure()
    fig.add_annotation(text=msg, xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False)
    fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", height=360)
    return fig


def _parse_entidad_value(value: str | None):
    if not value:
        return None
    try:
        idtrabajo, idenvio = value.split("_")
        return int(idtrabajo), int(idenvio)
    except Exception:
        return None


def layout():
    df_ent = get_entidades()
    opciones = []
    if df_ent is not None and not df_ent.empty:
        for _, r in df_ent.iterrows():
            opciones.append({"label": r["nombre"], "value": f"{int(r['idtrabajo'])}_{int(r['envio'])}"})

    return dbc.Container(
        [
            dbc.Row(
                [
                    dbc.Col(
                        [
                            html.H2("Por Entidad", className="page-title"),
                            html.P(
                                "Seleccioná una entidad para ver el detalle.",
                                className="page-subtitle",
                            ),
                        ],
                        md=8,
                    ),
                    dbc.Col(
                        [
                            dcc.Dropdown(
                                id="entidad-selector",
                                options=opciones,
                                placeholder="Seleccionar entidad...",
                                clearable=True,
                            )
                        ],
                        md=4,
                    ),
                ],
                className="mb-3",
            ),
            dcc.Store(id="entidad-movimientos-store"),
            dcc.Store(id="entidad-store-selected"),
            html.Div(
                id="entidad-mensaje",
                className="mb-3",
                children=dbc.Alert("Seleccioná una entidad para comenzar.", color="info"),
            ),
            dbc.Tabs(
                [
                    dbc.Tab(label="Resumen", tab_id="tab-resumen"),
                    dbc.Tab(label="Cuadro de control", tab_id="tab-control"),
                    dbc.Tab(label="Movimientos", tab_id="tab-movimientos"),
                    dbc.Tab(label="Análisis", tab_id="tab-analisis"),
                ],
                id="entidad-tabs",
                active_tab="tab-resumen",
            ),
            html.Div(id="entidad-tab-content", className="mt-3"),
            dcc.Download(id="download-movimientos-xlsx"),
        ],
        fluid=True,
    )


def register_callbacks(app):
    # 1) Cargar movimientos al seleccionar entidad
    @app.callback(
        [
            Output("entidad-store-selected", "data"),
            Output("entidad-movimientos-store", "data"),
            Output("entidad-mensaje", "children"),
        ],
        [Input("entidad-selector", "value")],
    )
    def cargar_entidad(value):
        try:
            parsed = _parse_entidad_value(value)
            if not parsed:
                return None, None, dbc.Alert("Seleccioná una entidad para comenzar.", color="info")

            idtrabajo, idenvio = parsed
            df = get_movimientos_entidad(idtrabajo=idtrabajo, idenvio=idenvio)
            # DataTable no tolera bien Timestamps no serializables
            if df is None:
                df = pd.DataFrame()
            if "fecha" in df.columns:
                df["fecha"] = pd.to_datetime(df["fecha"], errors="coerce").dt.strftime("%Y-%m-%d")

            nombre = get_nombre_entidad(idtrabajo, idenvio) or "Entidad"
            msg = dbc.Alert(f"Mostrando: {nombre}", color="secondary")
            return {"idtrabajo": idtrabajo, "idenvio": idenvio, "nombre": nombre}, df.to_dict("records"), msg
        except Exception as e:
            return None, None, dbc.Alert(f"Error al cargar entidad: {str(e)}", color="danger")

    # 2) Render de contenido por pestaña
    @app.callback(
        Output("entidad-tab-content", "children"),
        [Input("entidad-tabs", "active_tab"), Input("entidad-store-selected", "data")],
    )
    def render_tab(active_tab, ent):
        try:
            if not ent:
                return html.Div()

            if active_tab == "tab-resumen":
                return _tab_resumen()
            if active_tab == "tab-control":
                return _tab_control()
            if active_tab == "tab-movimientos":
                return _tab_movimientos()
            if active_tab == "tab-analisis":
                return _tab_analisis()
            return html.Div()
        except Exception as e:
            return dbc.Alert(f"Error renderizando pestaña: {str(e)}", color="danger")

    # 3) Resumen: encabezado + 2 gráficos
    @app.callback(
        [
            Output("entidad-resumen-header", "children"),
            Output("entidad-fig-liquidado-cobrado", "figure"),
            Output("entidad-fig-evolucion-saldo", "figure"),
        ],
        [Input("entidad-movimientos-store", "data"), Input("entidad-store-selected", "data")],
    )
    def actualizar_resumen(mov_records, ent):
        try:
            if not ent:
                return html.Div(), _empty_fig("Seleccioná una entidad"), _empty_fig("Seleccioná una entidad")
            df = pd.DataFrame(mov_records or [])
            if df.empty:
                header = dbc.Alert("No hay movimientos para esta entidad.", color="warning")
                return header, _empty_fig("Sin datos"), _empty_fig("Sin datos")

            # normalizar numéricos
            for col in ("debe", "haber", "anio", "cuota"):
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

            saldo = float(df["debe"].sum() - df["haber"].sum())
            saldo_color = "danger" if saldo > 0 else "success"

            # últimas fechas por tipo
            df["fecha_dt"] = pd.to_datetime(df.get("fecha"), errors="coerce")
            last_cob = df[df["tipo"].isin(TIPOS_COBRANZA_REAL)].sort_values("fecha_dt", ascending=False).head(1)
            last_liq = df[df["tipo"].isin(TIPOS_LIQUIDACION_REAL)].sort_values("fecha_dt", ascending=False).head(1)
            last_cob_str = last_cob.iloc[0]["fecha"] if not last_cob.empty else "-"
            last_liq_str = last_liq.iloc[0]["fecha"] if not last_liq.empty else "-"

            header = dbc.Card(
                dbc.CardBody(
                    [
                        html.H4(ent.get("nombre", "Entidad"), className="mb-2"),
                        html.Div(
                            [
                                html.Div("Saldo actual", className="text-muted"),
                                html.Div(
                                    f"$ {saldo:,.0f}".replace(",", "X").replace(".", ",").replace("X", "."),
                                    className=f"kpi-value text-{saldo_color}",
                                    style={"fontSize": "32px"},
                                ),
                            ],
                            className="mb-2",
                        ),
                        dbc.Row(
                            [
                                dbc.Col(
                                    [html.Div("Última cobranza", className="text-muted"), html.Div(last_cob_str)],
                                    md=6,
                                ),
                                dbc.Col(
                                    [html.Div("Última liquidación", className="text-muted"), html.Div(last_liq_str)],
                                    md=6,
                                ),
                            ]
                        ),
                    ]
                ),
                className="mb-3",
            )

            # df por período para liquidado/cobrado
            dff = df.copy()
            lc = (
                dff.groupby(["anio", "cuota"], as_index=False)
                .agg(
                    liquidado=("debe", lambda s: float(s[dff.loc[s.index, "tipo"].isin(TIPOS_LIQUIDACION_REAL)].sum())),
                    cobrado=("haber", lambda s: float(s[dff.loc[s.index, "tipo"].isin(TIPOS_COBRANZA_REAL)].sum())),
                )
            )

            fig_lc = build_liquidaciones_vs_cobros(lc)

            # evolución saldo acumulado por período
            per = dff.groupby(["anio", "cuota"], as_index=False).agg(saldo_periodo=("debe", "sum"))
            per["saldo_periodo"] = dff.groupby(["anio", "cuota"])["debe"].sum().values - dff.groupby(["anio", "cuota"])["haber"].sum().values
            per = per.sort_values(["anio", "cuota"])
            per["saldo_acumulado"] = per["saldo_periodo"].cumsum()
            fig_saldo = build_evolucion_saldo(per[["anio", "cuota", "saldo_acumulado"]])

            return header, fig_lc, fig_saldo
        except Exception as e:
            return dbc.Alert(f"Error en resumen: {str(e)}", color="danger"), _empty_fig("Error"), _empty_fig("Error")

    # 4) Cuadro de control: años disponibles + pivote
    @app.callback(
        [
            Output("entidad-control-anio", "options"),
            Output("entidad-control-anio", "value"),
        ],
        [Input("entidad-movimientos-store", "data")],
    )
    def control_anios(mov_records):
        try:
            df = pd.DataFrame(mov_records or [])
            if df.empty or "anio" not in df.columns:
                return [], None
            anios = sorted(pd.to_numeric(df["anio"], errors="coerce").dropna().unique().astype(int).tolist())
            opts = [{"label": str(a), "value": a} for a in anios]
            val = anios[-1] if anios else None
            return opts, val
        except Exception:
            return [], None

    @app.callback(
        [
            Output("entidad-control-table", "data"),
            Output("entidad-control-table", "columns"),
            Output("entidad-control-table", "style_data_conditional"),
        ],
        [
            Input("entidad-movimientos-store", "data"),
            Input("entidad-store-selected", "data"),
            Input("entidad-control-anio", "value"),
        ],
    )
    def control_pivot(mov_records, ent, anio):
        try:
            if not ent or not anio:
                return [], [], []
            df = pd.DataFrame(mov_records or [])
            if df.empty:
                return [], [], []

            pivot_df, styles = build_pivot_entidad(df, ent["idtrabajo"], ent["idenvio"], int(anio))
            cols = [{"name": c, "id": c} for c in pivot_df.columns]
            return pivot_df.to_dict("records"), cols, styles
        except Exception as e:
            return [], [], []

    # 5) Movimientos: filtro checklist + export
    @app.callback(
        Output("entidad-mov-table", "data"),
        [
            Input("entidad-movimientos-store", "data"),
            Input("entidad-mov-tipos", "value"),
        ],
    )
    def movimientos_filtrados(mov_records, grupos):
        try:
            df = pd.DataFrame(mov_records or [])
            if df.empty:
                return []

            tipos = set()
            grupos = grupos or []
            if "liq" in grupos:
                tipos.update(TIPOS_LIQUIDACION)
            if "ing" in grupos:
                tipos.update(TIPOS_INGRESOS)
            if "egr" in grupos:
                tipos.update(TIPOS_EGRESOS)
            if "aju" in grupos:
                tipos.update(TIPOS_AJUSTES)

            if tipos:
                df = df[df["tipo"].isin(list(tipos))].copy()

            # columnas esperadas (si no existen, crear)
            for col in ["fecha", "cuota", "anio", "tipo", "clase", "debe", "haber", "usuario", "usuario_nombre"]:
                if col not in df.columns:
                    df[col] = ""

            # armar campos display
            df["Periodo"] = df.apply(lambda r: f"{int(r['cuota'])}/{int(r['anio'])}" if str(r["cuota"]).isdigit() and str(r["anio"]).isdigit() else "-", axis=1)
            df["Tipo"] = df["tipo"].astype(str).map(TIPO_TEXTO).fillna(df["tipo"].astype(str))
            df["Clase"] = df["clase"].astype(str).map(CLASE_TEXTO).fillna(df["clase"].astype(str))

            # importe con signo: debe - haber (convención del dashboard)
            df["debe_num"] = pd.to_numeric(df["debe"], errors="coerce").fillna(0.0)
            df["haber_num"] = pd.to_numeric(df["haber"], errors="coerce").fillna(0.0)
            df["importe_num"] = df["debe_num"] - df["haber_num"]
            df["Importe"] = df["importe_num"].apply(_fmt_pesos_signed)

            # usuario: priorizar nombre/apellido; fallback al id
            df["Usuario"] = df["usuario_nombre"].replace("", pd.NA).fillna(df["usuario"])

            out = df.rename(columns={"fecha": "Fecha"})[["Fecha", "Periodo", "Tipo", "Clase", "Importe", "Usuario"]]
            return out.to_dict("records")
        except Exception:
            return []

    @app.callback(
        Output("download-movimientos-xlsx", "data"),
        [Input("entidad-btn-export", "n_clicks")],
        [
            State("entidad-mov-table", "data"),
            State("entidad-store-selected", "data"),
        ],
        prevent_initial_call=True,
    )
    def exportar_excel(n, data, ent):
        try:
            if not n:
                return None
            df = pd.DataFrame(data or [])
            nombre = (ent or {}).get("nombre", "entidad").replace(" ", "_")
            return dcc.send_data_frame(df.to_excel, f"movimientos_{nombre}.xlsx", index=False)
        except Exception as e:
            return None

    # 6) Análisis: selector de año y figuras
    @app.callback(
        [
            Output("entidad-analisis-anio", "options"),
            Output("entidad-analisis-anio", "value"),
        ],
        [Input("entidad-movimientos-store", "data")],
    )
    def analisis_anios(mov_records):
        try:
            df = pd.DataFrame(mov_records or [])
            if df.empty or "anio" not in df.columns:
                return [], None
            anios = sorted(pd.to_numeric(df["anio"], errors="coerce").dropna().unique().astype(int).tolist())
            opts = [{"label": str(a), "value": a} for a in anios]
            val = anios[-1] if anios else None
            return opts, val
        except Exception:
            return [], None

    @app.callback(
        [
            Output("entidad-fig-torta-subgrupos", "figure"),
            Output("entidad-fig-torta-formas-pago", "figure"),
            Output("entidad-fig-barras-comisiones", "figure"),
        ],
        [
            Input("entidad-movimientos-store", "data"),
            Input("entidad-analisis-anio", "value"),
        ],
    )
    def analisis_figs(mov_records, anio):
        try:
            df = pd.DataFrame(mov_records or [])
            if df.empty:
                return _empty_fig("Sin datos"), _empty_fig("Sin datos"), _empty_fig("Sin datos")
            return (
                build_torta_subgrupos(df, anio),
                build_torta_formas_pago(df, anio),
                build_barras_comisiones(df, anio),
            )
        except Exception as e:
            return _empty_fig("Error"), _empty_fig("Error"), _empty_fig("Error")


def _tab_resumen():
    return html.Div(
        [
            html.Div(id="entidad-resumen-header"),
            dbc.Row(
                [
                    dbc.Col(
                        dbc.Card(
                            [
                                dbc.CardHeader("Liquidado vs Cobrado"),
                                dbc.CardBody(
                                    dcc.Loading(dcc.Graph(id="entidad-fig-liquidado-cobrado", figure=_empty_fig("Cargando...")))
                                ),
                            ]
                        ),
                        md=12,
                    ),
                ],
                className="mb-4",
            ),
            dbc.Row(
                [
                    dbc.Col(
                        dbc.Card(
                            [
                                dbc.CardHeader("Evolución del saldo"),
                                dbc.CardBody(
                                    dcc.Loading(dcc.Graph(id="entidad-fig-evolucion-saldo", figure=_empty_fig("Cargando...")))
                                ),
                            ]
                        ),
                        md=12,
                    )
                ]
            ),
        ]
    )


def _tab_control():
    return html.Div(
        [
            dbc.Row(
                [
                    dbc.Col(
                        dcc.Dropdown(id="entidad-control-anio", placeholder="Año..."),
                        md=3,
                    ),
                ],
                className="mb-3",
            ),
            dash_table.DataTable(
                id="entidad-control-table",
                data=[],
                columns=[],
                style_table={"overflowX": "auto"},
                style_cell={
                    "padding": "8px",
                    "fontSize": "12px",
                    "whiteSpace": "nowrap",
                    "textAlign": "center",
                },
                style_header={"fontWeight": "bold"},
            ),
        ]
    )


def _tab_movimientos():
    return html.Div(
        [
            dbc.Row(
                [
                    dbc.Col(
                        dbc.Checklist(
                            id="entidad-mov-tipos",
                            options=[
                                {"label": "Liquidaciones", "value": "liq"},
                                {"label": "Ingresos", "value": "ing"},
                                {"label": "Egresos", "value": "egr"},
                                {"label": "Ajustes", "value": "aju"},
                            ],
                            value=["liq", "ing", "egr", "aju"],
                            inline=True,
                        ),
                        md=9,
                    ),
                    dbc.Col(
                        dbc.Button("Exportar a Excel", id="entidad-btn-export", color="primary", className="w-100"),
                        md=3,
                    ),
                ],
                className="mb-3",
            ),
            dash_table.DataTable(
                id="entidad-mov-table",
                data=[],
                columns=[{"name": c, "id": c} for c in ["Fecha", "Periodo", "Tipo", "Clase", "Importe", "Usuario"]],
                page_size=20,
                sort_action="native",
                filter_action="native",
                style_table={"overflowX": "auto"},
                style_cell={
                    "padding": "8px",
                    "fontSize": "12px",
                    "maxWidth": 320,
                    "whiteSpace": "nowrap",
                    "overflow": "hidden",
                    "textOverflow": "ellipsis",
                },
                style_header={"fontWeight": "bold"},
            ),
        ]
    )


def _tab_analisis():
    return html.Div(
        [
            dbc.Row(
                [
                    dbc.Col(
                        dcc.Dropdown(id="entidad-analisis-anio", placeholder="Año..."),
                        md=3,
                    )
                ],
                className="mb-3",
            ),
            dbc.Row(
                [
                    dbc.Col(
                        dbc.Card(
                            [
                                dbc.CardHeader("Liquidaciones por subgrupo"),
                                dbc.CardBody(dcc.Loading(dcc.Graph(id="entidad-fig-torta-subgrupos", figure=_empty_fig("Cargando...")))),
                            ]
                        ),
                        md=6,
                    ),
                    dbc.Col(
                        dbc.Card(
                            [
                                dbc.CardHeader("Cobranzas por forma de pago"),
                                dbc.CardBody(dcc.Loading(dcc.Graph(id="entidad-fig-torta-formas-pago", figure=_empty_fig("Cargando...")))),
                            ]
                        ),
                        md=6,
                    ),
                ],
                className="mb-4",
            ),
            dbc.Row(
                [
                    dbc.Col(
                        dbc.Card(
                            [
                                dbc.CardHeader("Comisiones por período"),
                                dbc.CardBody(dcc.Loading(dcc.Graph(id="entidad-fig-barras-comisiones", figure=_empty_fig("Cargando...")))),
                            ]
                        ),
                        md=12,
                    ),
                ]
            ),
        ]
    )

