"""
Componentes de gráficos Plotly para el dashboard.
"""
import plotly.graph_objects as go
import pandas as pd
from config import MESES


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
            paper_bgcolor='transparent',
            plot_bgcolor='transparent',
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
            paper_bgcolor='transparent',
            plot_bgcolor='transparent',
            height=400
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
        
        # Determinar colores según saldo
        colores_linea = ['#E24B4A' if s > 0 else '#1D9E75' for s in df_sorted['saldo_acumulado']]
        colores_area = ['rgba(226, 75, 74, 0.3)' if s > 0 else 'rgba(29, 158, 117, 0.3)' 
                       for s in df_sorted['saldo_acumulado']]
        
        # Crear el gráfico
        fig = go.Figure()
        
        # Área rellena
        fig.add_trace(go.Scatter(
            x=df_sorted['periodo'],
            y=df_sorted['saldo_acumulado'],
            fill='tozeroy',
            mode='lines',
            name='Saldo Acumulado',
            line=dict(color='#378ADD', width=2),
            fillcolor='rgba(55, 138, 221, 0.2)',
            hovertemplate='<b>%{x}</b><br>Saldo: $%{y:,.2f}<extra></extra>'
        ))
        
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
            paper_bgcolor='transparent',
            plot_bgcolor='transparent',
            height=400
        )
        return fig
