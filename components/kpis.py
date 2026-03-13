"""
Componentes de tarjetas KPI (Key Performance Indicators).
"""
import dash_bootstrap_components as dbc
from dash import html


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
    
    valor_str = f"{prefijo}${abs(saldo_valor):,.2f}"
    return kpi_card('Saldo neto', valor_str, color)
