"""
Componentes de gráficos Plotly para el dashboard.
"""
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
from config import (
    CLASES_COMISION,
    COLOR_AZUL,
    COLOR_ROJO,
    COLOR_VERDE,
    MESES,
    TIPOS_COBRANZA_REAL,
    TIPOS_LIQUIDACION_REAL,
    COLOR_AMBAR,
)


def formatear_moneda(valor):
    """
    Formatea un valor numérico como moneda argentina.
    Separador de miles: punto, decimales: coma.
    
    Args:
        valor: Valor numérico
    
    Returns:
        str: Valor formateado (ej: "1.234,56")
    """
    if pd.isna(valor) or valor == 0:
        return "0,00"
    
    # Separar parte entera y decimal
    parte_entera = int(abs(valor))
    parte_decimal = abs(valor) - parte_entera
    
    # Formatear parte entera con puntos como separador de miles
    parte_entera_str = f"{parte_entera:,}".replace(",", ".")
    
    # Formatear parte decimal con coma
    parte_decimal_str = f"{parte_decimal:.2f}".split(".")[1]
    
    signo = "-" if valor < 0 else ""
    return f"{signo}{parte_entera_str},{parte_decimal_str}"


def build_ranking_saldo(df):
    """
    Construye gráfico de barras horizontales con ranking de entidades por saldo.
    
    Args:
        df: DataFrame con columnas: entidad, saldo_neto, idtrabajo, envio
    
    Returns:
        go.Figure: Gráfico de barras horizontales
    """
    try:
        if df.empty:
            fig = go.Figure()
            fig.add_annotation(
                text="No hay datos disponibles",
                xref="paper", yref="paper",
                x=0.5, y=0.5, showarrow=False
            )
            fig.update_layout(
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                height=400
            )
            return fig
        
        # Ordenar por saldo descendente
        df_sorted = df.sort_values('saldo_neto', ascending=True).tail(20)  # Top 20
        
        # Determinar colores según saldo
        colores = [
            '#E24B4A' if saldo > 0 else '#1D9E75'
            for saldo in df_sorted['saldo_neto']
        ]
        
        # Crear el gráfico
        fig = go.Figure()
        
        fig.add_trace(go.Bar(
            y=df_sorted['entidad'],
            x=df_sorted['saldo_neto'],
            orientation='h',
            marker=dict(color=colores),
            text=[f"${formatear_moneda(s):>15}" for s in df_sorted['saldo_neto']],
            textposition='outside',
            customdata=df_sorted[['idtrabajo', 'envio']].values,
            hovertemplate='<b>%{y}</b><br>Saldo: $%{text}<extra></extra>'
        ))
        
        # Línea de referencia en 0
        fig.add_shape(
            type="line",
            x0=0, x1=0,
            y0=-0.5, y1=len(df_sorted) - 0.5,
            line=dict(color="gray", width=2, dash="dash")
        )
        
        fig.update_layout(
            title="Ranking de Entidades por Saldo",
            xaxis_title="Saldo Neto ($)",
            yaxis_title="",
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            height=max(400, len(df_sorted) * 30),
            margin=dict(l=150, r=50, t=50, b=50),
            showlegend=False
        )
        
        return fig
        
    except Exception as e:
        print(f"Error en build_ranking_saldo(): {e}")
        fig = go.Figure()
        fig.add_annotation(
            text=f"Error al generar gráfico: {str(e)}",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False
        )
        fig.update_layout(
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            height=400
        )
        return fig


def build_cobrado_vs_liquidado_global(df):
    """
    Construye gráfico de barras agrupadas: liquidado vs cobrado por período.
    
    Args:
        df: DataFrame con columnas: anio, cuota, liquidado, cobrado
    
    Returns:
        go.Figure: Gráfico de barras agrupadas
    """
    try:
        if df.empty:
            fig = go.Figure()
            fig.add_annotation(
                text="No hay datos disponibles",
                xref="paper", yref="paper",
                x=0.5, y=0.5, showarrow=False
            )
            fig.update_layout(
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                height=400
            )
            return fig
        
        # Ordenar por año y cuota
        df_sorted = df.sort_values(['anio', 'cuota']).copy()
        
        # Crear etiquetas de período
        df_sorted['periodo'] = df_sorted.apply(
            lambda row: f"{MESES.get(row['cuota'], str(row['cuota']))} {int(row['anio'])}",
            axis=1
        )
        
        # Crear el gráfico
        fig = go.Figure()
        
        # Barra de liquidado (azul)
        fig.add_trace(go.Bar(
            name='Liquidado',
            x=df_sorted['periodo'],
            y=df_sorted['liquidado'],
            marker_color='#378ADD',
            hovertemplate='<b>%{x}</b><br>Liquidado: $%{y:,.2f}<extra></extra>'
        ))
        
        # Barra de cobrado (verde)
        fig.add_trace(go.Bar(
            name='Cobrado',
            x=df_sorted['periodo'],
            y=df_sorted['cobrado'],
            marker_color='#1D9E75',
            hovertemplate='<b>%{x}</b><br>Cobrado: $%{y:,.2f}<extra></extra>'
        ))
        
        fig.update_layout(
            title="Evolución Mensual - Cobrado vs Liquidado",
            xaxis_title="Período",
            yaxis_title="Monto ($)",
            barmode='group',
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            height=400,
            margin=dict(l=50, r=50, t=50, b=100),
            xaxis=dict(tickangle=-45),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )
        
        return fig
        
    except Exception as e:
        print(f"Error en build_cobrado_vs_liquidado_global(): {e}")
        fig = go.Figure()
        fig.add_annotation(
            text=f"Error al generar gráfico: {str(e)}",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False
        )
        fig.update_layout(
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            height=400
        )
        return fig


def build_cobranza_neta_por_entidad(df: pd.DataFrame, top_n: int = 10) -> go.Figure:
    """
    Barras horizontales: cobranza neta por entidad y % sobre el total.
    Muestra las top_n entidades y agrupa el resto en «Resto».
    """
    try:
        if df is None or df.empty:
            fig = go.Figure()
            fig.add_annotation(
                text="Sin datos",
                xref="paper",
                yref="paper",
                x=0.5,
                y=0.5,
                showarrow=False,
            )
            fig.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                height=380,
            )
            return fig

        d = df.copy()
        d = d.sort_values("cobranza_neta", ascending=False)
        top = d.head(top_n).copy()
        rest_sum = float(d.iloc[top_n:]["cobranza_neta"].sum()) if len(d) > top_n else 0.0
        if rest_sum > 1e-6:
            top = pd.concat(
                [top, pd.DataFrame([{"nombre": "Resto", "cobranza_neta": rest_sum}])],
                ignore_index=True,
            )

        total = float(top["cobranza_neta"].sum())
        if total <= 0:
            fig = go.Figure()
            fig.add_annotation(
                text="Sin datos",
                xref="paper",
                yref="paper",
                x=0.5,
                y=0.5,
                showarrow=False,
            )
            fig.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                height=380,
            )
            return fig

        top["pct"] = top["cobranza_neta"] / total * 100.0
        plot_df = top.sort_values("cobranza_neta", ascending=True)

        textos = [
            f"{formatear_moneda(v)} ({f'{p:.1f}'.replace('.', ',')}%)"
            for v, p in zip(plot_df["cobranza_neta"], plot_df["pct"])
        ]

        fig = go.Figure(
            go.Bar(
                x=plot_df["cobranza_neta"],
                y=plot_df["nombre"],
                orientation="h",
                text=textos,
                textposition="outside",
                marker_color=COLOR_AZUL,
                hovertemplate="<b>%{y}</b><br>Neto: $%{x:,.2f}<br>%{customdata:.1f}% del total<extra></extra>",
                customdata=plot_df["pct"],
            )
        )
        n_bars = len(plot_df)
        fig.update_layout(
            title="Cobranza neta por entidad (% del total)",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            height=max(380, min(560, 44 * n_bars + 120)),
            margin=dict(l=160, r=120, t=50, b=40),
            xaxis_title="Cobranza neta ($)",
            yaxis_title="",
            showlegend=False,
        )
        fig.update_yaxes(automargin=True)
        return fig
    except Exception as e:
        print(f"Error en build_cobranza_neta_por_entidad(): {e}")
        fig = go.Figure()
        fig.add_annotation(
            text=f"Error: {str(e)}",
            xref="paper",
            yref="paper",
            x=0.5,
            y=0.5,
            showarrow=False,
        )
        fig.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            height=400,
        )
        return fig


def build_evolucion_saldo(df):
    """
    Construye gráfico de línea con área rellena del saldo acumulado total.
    
    Args:
        df: DataFrame con columnas: anio, cuota, saldo_acumulado
    
    Returns:
        go.Figure: Gráfico de línea con área
    """
    try:
        if df.empty:
            fig = go.Figure()
            fig.add_annotation(
                text="No hay datos disponibles",
                xref="paper", yref="paper",
                x=0.5, y=0.5, showarrow=False
            )
            fig.update_layout(
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                height=400
            )
            return fig
        
        # Ordenar por año y cuota
        df_sorted = df.sort_values(['anio', 'cuota']).copy()
        
        # Crear etiquetas de período
        df_sorted['periodo'] = df_sorted.apply(
            lambda row: f"{MESES.get(row['cuota'], str(row['cuota']))} {int(row['anio'])}",
            axis=1
        )
        
        y = pd.to_numeric(df_sorted["saldo_acumulado"], errors="coerce").fillna(0.0)

        # Área por signo:
        # - rojo cuando saldo > 0 (entidad debe a la mutual)
        # - verde cuando saldo <= 0 (mutual debe a la entidad)
        y_pos = y.where(y > 0, 0.0)
        y_neg = y.where(y <= 0, 0.0)

        fig = go.Figure()

        fig.add_trace(
            go.Scatter(
                x=df_sorted["periodo"],
                y=y_pos,
                fill="tozeroy",
                mode="lines",
                name="Saldo > 0",
                line=dict(color="rgba(0,0,0,0)"),
                fillcolor=COLOR_ROJO,
                hovertemplate="<b>%{x}</b><br>Saldo: $%{customdata:,.2f}<extra></extra>",
                customdata=y,
                showlegend=False,
            )
        )
        fig.add_trace(
            go.Scatter(
                x=df_sorted["periodo"],
                y=y_neg,
                fill="tozeroy",
                mode="lines",
                name="Saldo ≤ 0",
                line=dict(color="rgba(0,0,0,0)"),
                fillcolor=COLOR_VERDE,
                hovertemplate="<b>%{x}</b><br>Saldo: $%{customdata:,.2f}<extra></extra>",
                customdata=y,
                showlegend=False,
            )
        )

        # Línea del saldo acumulado
        fig.add_trace(
            go.Scatter(
                x=df_sorted["periodo"],
                y=y,
                mode="lines",
                name="Saldo acumulado",
                line=dict(color=COLOR_AZUL, width=2),
                hovertemplate="<b>%{x}</b><br>Saldo: $%{y:,.2f}<extra></extra>",
                showlegend=False,
            )
        )
        
        # Línea de referencia en 0
        fig.add_hline(
            y=0,
            line_dash="dash",
            line_color="gray",
            annotation_text="Línea de referencia (0)"
        )
        
        fig.update_layout(
            title="Evolución Temporal del Saldo Total",
            xaxis_title="Período",
            yaxis_title="Saldo Acumulado ($)",
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            height=400,
            margin=dict(l=50, r=50, t=50, b=100),
            xaxis=dict(tickangle=-45),
            showlegend=False,
            hovermode='x unified'
        )
        
        return fig
        
    except Exception as e:
        print(f"Error en build_evolucion_saldo(): {e}")
        fig = go.Figure()
        fig.add_annotation(
            text=f"Error al generar gráfico: {str(e)}",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False
        )
        fig.update_layout(
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            height=400
        )
        return fig


def build_liquidaciones_vs_cobros(df: pd.DataFrame, con_devoluciones: bool = False) -> go.Figure:
    """
    Barras agrupadas por período para una entidad (Liquidado vs Cobrado).

    Sin devoluciones: columnas anio, cuota, liquidado, cobrado.
    Con devoluciones: anio, cuota, liquidado, cobrado_neta, devoluciones, cobranza_bruta.
    """
    try:
        if not con_devoluciones:
            return build_cobrado_vs_liquidado_global(df)

        if df is None or df.empty:
            return build_cobrado_vs_liquidado_global(pd.DataFrame())

        req = {"anio", "cuota", "liquidado", "cobrado_neta", "devoluciones", "cobranza_bruta"}
        if not req.issubset(set(df.columns)):
            return build_cobrado_vs_liquidado_global(df)

        df_sorted = df.sort_values(["anio", "cuota"]).copy()
        df_sorted["periodo"] = df_sorted.apply(
            lambda row: f"{MESES.get(int(row['cuota']), str(row['cuota']))} {int(row['anio'])}",
            axis=1,
        )

        cd = df_sorted[
            ["cobranza_bruta", "devoluciones", "cobrado_neta"]
        ].to_numpy()

        fig = go.Figure()

        fig.add_trace(
            go.Bar(
                name="Liquidado",
                x=df_sorted["periodo"],
                y=df_sorted["liquidado"],
                marker_color="#378ADD",
                offsetgroup=0,
                hovertemplate="<b>%{x}</b><br>Liquidado: $%{y:,.2f}<extra></extra>",
            )
        )

        fig.add_trace(
            go.Bar(
                name="Cobrado",
                x=df_sorted["periodo"],
                y=df_sorted["cobrado_neta"],
                marker_color="#1D9E75",
                offsetgroup=1,
                customdata=cd,
                hovertemplate=(
                    "<b>%{x}</b><br>Cobranza bruta: $%{customdata[0]:,.2f}<br>"
                    "Devoluciones: $%{customdata[1]:,.2f}<br>Cobranza neta: $%{customdata[2]:,.2f}<extra></extra>"
                ),
            )
        )

        fig.add_trace(
            go.Bar(
                name="Devoluciones",
                x=df_sorted["periodo"],
                y=df_sorted["devoluciones"],
                base=df_sorted["cobrado_neta"],
                marker_color=COLOR_AMBAR,
                offsetgroup=1,
                customdata=cd,
                hovertemplate=(
                    "<b>%{x}</b><br>Cobranza bruta: $%{customdata[0]:,.2f}<br>"
                    "Devoluciones: $%{customdata[1]:,.2f}<br>Cobranza neta: $%{customdata[2]:,.2f}<extra></extra>"
                ),
            )
        )

        fig.update_layout(
            title="Evolución Mensual - Cobrado vs Liquidado",
            xaxis_title="Período",
            yaxis_title="Monto ($)",
            barmode="group",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            height=400,
            margin=dict(l=50, r=50, t=50, b=100),
            xaxis=dict(tickangle=-45),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        )
        return fig
    except Exception as e:
        print(f"Error en build_liquidaciones_vs_cobros(): {e}")
        return build_cobrado_vs_liquidado_global(df if df is not None else pd.DataFrame())


def build_torta_subgrupos(df: pd.DataFrame, anio: int | None) -> go.Figure:
    """
    Donut de liquidaciones por subgrupo/clase (solo TIPOS_LIQUIDACION_REAL).

    - Agrupa por `clase`
    - Suma `debe`
    """
    try:
        if df is None or df.empty:
            fig = go.Figure()
            fig.add_annotation(text="No hay datos disponibles", xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False)
            fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", height=360)
            return fig

        dff = df.copy()
        if anio is not None:
            dff = dff[dff["anio"] == int(anio)]

        dff = dff[dff["tipo"].isin(TIPOS_LIQUIDACION_REAL)].copy()
        if dff.empty:
            fig = go.Figure()
            fig.add_annotation(text="No hay liquidaciones", xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False)
            fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", height=360)
            return fig

        grp = dff.groupby("clase", dropna=False)["debe"].sum().reset_index()
        grp["clase"] = grp["clase"].fillna("Sin clase")

        fig = px.pie(
            grp,
            names="clase",
            values="debe",
            hole=0.55,
        )
        fig.update_traces(textposition="inside", textinfo="percent+label")
        fig.update_layout(
            title="Liquidaciones por subgrupo",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            height=360,
            margin=dict(l=10, r=10, t=50, b=10),
            legend=dict(orientation="h", yanchor="top", y=-0.05, xanchor="left", x=0),
        )
        return fig
    except Exception as e:
        print(f"Error en build_torta_subgrupos(): {e}")
        fig = go.Figure()
        fig.add_annotation(text=f"Error: {str(e)}", xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False)
        fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", height=360)
        return fig


def build_torta_formas_pago(df: pd.DataFrame, anio: int | None) -> go.Figure:
    """
    Donut de cobranzas por forma de pago (solo TIPOS_COBRANZA_REAL).

    Mapeo:
      - IT: Transferencia
      - IA: FDC
      - IC: Cheque
      - IE: Efectivo

    Agrupa por `tipo` y suma `haber`.
    """
    try:
        if df is None or df.empty:
            fig = go.Figure()
            fig.add_annotation(text="No hay datos disponibles", xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False)
            fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", height=360)
            return fig

        dff = df.copy()
        if anio is not None:
            dff = dff[dff["anio"] == int(anio)]

        dff = dff[dff["tipo"].isin(TIPOS_COBRANZA_REAL)].copy()
        if dff.empty:
            fig = go.Figure()
            fig.add_annotation(text="No hay cobranzas", xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False)
            fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", height=360)
            return fig

        mapa = {"IT": "Transferencia", "IA": "FDC", "IC": "Cheque", "IE": "Efectivo"}
        grp = dff.groupby("tipo")["haber"].sum().reset_index()
        grp["forma"] = grp["tipo"].map(mapa).fillna(grp["tipo"])

        fig = px.pie(grp, names="forma", values="haber", hole=0.55)
        fig.update_traces(textposition="inside", textinfo="percent+label")
        fig.update_layout(
            title="Cobranzas por forma de pago",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            height=360,
            margin=dict(l=10, r=10, t=50, b=10),
            legend=dict(orientation="h", yanchor="top", y=-0.05, xanchor="left", x=0),
        )
        return fig
    except Exception as e:
        print(f"Error en build_torta_formas_pago(): {e}")
        fig = go.Figure()
        fig.add_annotation(text=f"Error: {str(e)}", xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False)
        fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", height=360)
        return fig


def build_barras_comisiones(df: pd.DataFrame, anio: int | None) -> go.Figure:
    """
    Barras de comisiones (clases GC/CO) por período.

    Suma `debe` para filas donde `clase` está en CLASES_COMISION.
    """
    try:
        if df is None or df.empty:
            fig = go.Figure()
            fig.add_annotation(text="No hay datos disponibles", xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False)
            fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", height=360)
            return fig

        dff = df.copy()
        if anio is not None:
            dff = dff[dff["anio"] == int(anio)]

        dff = dff[dff["clase"].isin(CLASES_COMISION)].copy()
        if dff.empty:
            fig = go.Figure()
            fig.add_annotation(text="No hay comisiones", xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False)
            fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", height=360)
            return fig

        grp = (
            dff.groupby(["anio", "cuota"], as_index=False)["debe"]
            .sum()
            .sort_values(["anio", "cuota"])
        )
        grp["periodo"] = grp.apply(lambda r: f"{MESES.get(int(r['cuota']), r['cuota'])} {int(r['anio'])}", axis=1)

        fig = go.Figure()
        fig.add_trace(
            go.Bar(
                x=grp["periodo"],
                y=grp["debe"],
                name="Comisiones",
                marker_color="#EF9F27",
                hovertemplate="<b>%{x}</b><br>Comisiones: $%{y:,.2f}<extra></extra>",
            )
        )
        fig.update_layout(
            title="Comisiones por período",
            xaxis_title="Período",
            yaxis_title="Monto ($)",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            height=360,
            margin=dict(l=30, r=10, t=50, b=90),
            xaxis=dict(tickangle=-45),
            showlegend=False,
        )
        return fig
    except Exception as e:
        print(f"Error en build_barras_comisiones(): {e}")
        fig = go.Figure()
        fig.add_annotation(text=f"Error: {str(e)}", xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False)
        fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", height=360)
        return fig


def build_heatmap_cobertura(df: pd.DataFrame, anio: int | None = None) -> go.Figure:
    """
    Heatmap de cobertura para Control de carga.

    Espera df con columnas:
      - envio_nombre (str)
      - cuota (1..12)
      - estado_num (0 ok, 1 pendiente, 2 vencido, 3 sin_config/sin_datos)
      - opcional: fecha_venc (date/str), estado (str), entidad_nombre (str),
                 tiene_liquidacion (bool), tiene_cobranza (bool)
    """
    try:
        if df is None or df.empty:
            fig = go.Figure()
            fig.add_annotation(text="No hay datos para mostrar", xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False)
            fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", height=420)
            return fig

        dff = df.copy()
        if anio is not None and "anio" in dff.columns:
            dff = dff[dff["anio"] == int(anio)].copy()

        # Ejes
        meses = list(range(1, 13))
        x_labels = [MESES[m] for m in meses]

        # Y: envíos ordenados alfabéticamente
        y_envios = sorted([e for e in dff["envio_nombre"].dropna().unique().tolist()])
        if not y_envios:
            y_envios = ["(sin envío)"]

        # Matriz z inicial gris (3)
        z = [[3 for _ in meses] for _ in y_envios]
        custom = [[{} for _ in meses] for _ in y_envios]

        # index helpers
        y_idx = {name: i for i, name in enumerate(y_envios)}
        x_idx = {m: j for j, m in enumerate(meses)}

        # llenar
        for _, r in dff.iterrows():
            envio = r.get("envio_nombre") or "(sin envío)"
            cuota = int(r.get("cuota")) if pd.notna(r.get("cuota")) else None
            if envio not in y_idx or cuota not in x_idx:
                continue
            i = y_idx[envio]
            j = x_idx[cuota]
            estado_num = int(r.get("estado_num", 3))
            z[i][j] = estado_num
            custom[i][j] = {
                "envio_nombre": envio,
                "entidad_nombre": r.get("entidad_nombre"),
                "anio": int(r.get("anio")) if pd.notna(r.get("anio")) else None,
                "cuota": cuota,
                "estado": r.get("estado"),
                "fecha_venc": str(r.get("fecha_venc")) if r.get("fecha_venc") is not None else None,
                "dias_vencido": int(r.get("dias_vencido")) if pd.notna(r.get("dias_vencido")) else None,
                "tiene_liquidacion": bool(r.get("tiene_liquidacion")) if "tiene_liquidacion" in r else None,
                "tiene_cobranza": bool(r.get("tiene_cobranza")) if "tiene_cobranza" in r else None,
            }

        # Colorscale discreta (0..3)
        colorscale = [
            [0.0, "#1D9E75"],   # 0 ok
            [0.3333, "#1D9E75"],
            [0.3334, "#EF9F27"],  # 1 pendiente
            [0.6666, "#EF9F27"],
            [0.6667, "#E24B4A"],  # 2 vencido
            [0.9999, "#E24B4A"],
            [1.0, "#B4B2A9"],     # 3 sin_config/sin_datos (pero queda fuera del rango con zmax=3)
        ]

        # Plotly colorscale necesita mapear bien hasta 3 → usamos zmin=0 zmax=3 y definimos escala por tramos:
        colorscale = [
            [0 / 3, "#1D9E75"],
            [0.24 / 3, "#1D9E75"],
            [1 / 3, "#EF9F27"],
            [1.24 / 3, "#EF9F27"],
            [2 / 3, "#E24B4A"],
            [2.24 / 3, "#E24B4A"],
            [3 / 3, "#B4B2A9"],
            [1.0, "#B4B2A9"],
        ]

        fig = go.Figure(
            go.Heatmap(
                z=z,
                x=x_labels,
                y=y_envios,
                zmin=0,
                zmax=3,
                colorscale=colorscale,
                showscale=False,
                customdata=custom,
                hovertemplate="<b>%{y}</b><br>Mes: %{x}<br>Estado: %{z}<extra></extra>",
            )
        )
        fig.update_layout(
            title="Cobertura de cobranzas por envío",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            height=max(420, 26 * len(y_envios) + 120),
            margin=dict(l=140, r=20, t=50, b=40),
        )
        return fig
    except Exception as e:
        print(f"Error en build_heatmap_cobertura(): {e}")
        fig = go.Figure()
        fig.add_annotation(text=f"Error: {str(e)}", xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False)
        fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", height=420)
        return fig
