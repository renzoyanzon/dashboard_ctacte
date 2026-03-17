"""
Componente de lista de entidades clickeable.
"""
import dash_bootstrap_components as dbc
from dash import html, dcc
from db.queries import get_entidades


def build_entity_list():
    """
    Construye el panel de lista de entidades clickeable.
    
    Returns:
        html.Div con el panel de entidades
    """
    # Obtener entidades desde la base de datos
    df_entidades = get_entidades()
    
    # Crear lista de items de entidades
    items = []
    
    # Opción "Todas" al principio
    items.append(
        dbc.ListGroupItem(
            "Todas",
            id={"type": "entity-item", "index": "all"},
            n_clicks=0,
            className="entity-list-item active",
            action=True
        )
    )
    
    # Agregar todas las entidades ordenadas alfabéticamente
    if not df_entidades.empty:
        # Ordenar por nombre alfabéticamente
        df_entidades_sorted = df_entidades.sort_values('nombre')
        for _, row in df_entidades_sorted.iterrows():
            entity_id = f"{row['idtrabajo']}_{row['envio']}"
            items.append(
                dbc.ListGroupItem(
                    row['nombre'],
                    id={"type": "entity-item", "index": entity_id},
                    n_clicks=0,
                    className="entity-list-item",
                    action=True
                )
            )
    
    return html.Div([
        html.Div("Entidades", className="entity-list-header"),
        dbc.ListGroup(items, flush=True, className="entity-list-group"),
        # Store para guardar la entidad seleccionada
        dcc.Store(id="store-entity-selected", data="all")
    ], className="entity-list-panel")
