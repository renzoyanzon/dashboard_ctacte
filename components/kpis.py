"""
Componentes de tarjetas KPI (Key Performance Indicators).
"""
import dash_bootstrap_components as dbc
from dash import html


def formatear_importe(valor):
    """
    Formatea un importe de forma abreviada para KPIs.
    Si supera 1.000.000 muestra como "2,3M", si supera 1.000 muestra como "450K".
    
    Args:
        valor: Valor numérico
    
    Returns:
        str: Valor formateado (ej: "$ 2,3M", "$ 450K", "$ 1.234")
    """
    if abs(valor) >= 1_000_000:
        return f"$ {valor/1_000_000:.1f}M"
    elif abs(valor) >= 1_000:
        return f"$ {valor/1_000:.0f}K"
    else:
        return f"$ {valor:,.0f}"


def kpi_card(titulo, valor, color='primary', icono=None):
    """
    Genera una tarjeta KPI con título y valor.
    
    Args:
        titulo: Texto del título
        valor: Valor a mostrar (string o número)
        color: Color de Bootstrap ('success', 'danger', 'warning', 'primary', 'secondary')
        icono: Icono opcional (no implementado aún)
    
    Returns:
        dbc.Card con el KPI
    """
    return dbc.Card([
        dbc.CardBody([
            html.P(titulo, className='kpi-title'),
            html.H4(valor, className=f'kpi-value text-{color}'),
        ])
    ], className='kpi-card')


def kpi_saldo(saldo_valor):
    """
    Genera KPI de saldo con color automático según valor.
    
    Args:
        saldo_valor: Valor numérico del saldo
    
    Returns:
        dbc.Card con el KPI de saldo formateado
    """
    if saldo_valor > 0:
        color = 'danger'
        prefijo = '▲ Deuda: '
    elif saldo_valor < 0:
        color = 'success'
        prefijo = '▼ A favor: '
    else:
        color = 'secondary'
        prefijo = '= Sin saldo: '
    
    valor_str = f"{prefijo}{formatear_importe(abs(saldo_valor))}"
    return kpi_card('Saldo neto', valor_str, color)
