"""
Consultas SQL parametrizadas a la base de datos.
Todas las funciones retornan DataFrames de pandas.
"""
import pandas as pd
from db.connection import get_connection
from config import get_nombre_entidad


def get_entidades():
    """
    Obtiene la lista de todas las entidades (municipalidades/organismos).
    Obtiene las combinaciones únicas de idtrabajo y envio desde ctactetrabajo
    y agrega los nombres usando config.py.
    
    Returns:
        DataFrame con columnas: idtrabajo, envio, nombre
    """
    sql = """
        SELECT DISTINCT
            c.idtrabajo,
            c.envio
        FROM ctactetrabajo c
        ORDER BY c.idtrabajo, c.envio
    """
    
    conn = None
    try:
        conn = get_connection()
        df = pd.read_sql(sql, conn)
        
        # Agregar nombres usando config.py
        df['nombre'] = df.apply(
            lambda row: get_nombre_entidad(row['idtrabajo'], row['envio']),
            axis=1
        )
        
        # Filtrar solo las que tienen nombre (están en config)
        df = df[df['nombre'].notna()].copy()
        
        # Ordenar por nombre
        df = df.sort_values('nombre').reset_index(drop=True)
        
        return df
    except Exception as e:
        print(f"Error en get_entidades(): {e}")
        return pd.DataFrame()
    finally:
        if conn:
            conn.close()


def get_saldo_por_entidad(anio=None, cuota=None):
    """
    Obtiene el saldo (debe/haber/saldo_neto) agrupado por entidad.
    Filtra por año y cuota si se proporcionan.
    
    Args:
        anio: Año del período (opcional)
        cuota: Mes del período 1-12 (opcional)
    
    Returns:
        DataFrame con columnas: entidad, idtrabajo, envio, total_debe, total_haber, saldo_neto
    """
    conditions = []
    params = []
    
    if anio is not None:
        conditions.append("c.anio = %s")
        params.append(anio)
    
    if cuota is not None:
        conditions.append("c.cuota = %s")
        params.append(cuota)
    
    where_clause = ""
    if conditions:
        where_clause = "WHERE " + " AND ".join(conditions)
    
    sql = f"""
        SELECT 
            c.idtrabajo,
            c.envio,
            SUM(c.debe) AS total_debe,
            SUM(c.haber) AS total_haber,
            SUM(c.debe) - SUM(c.haber) AS saldo_neto
        FROM ctactetrabajo c
        {where_clause}
        GROUP BY c.idtrabajo, c.envio
        ORDER BY saldo_neto DESC
    """
    
    conn = None
    try:
        conn = get_connection()
        df = pd.read_sql(sql, conn, params=params if params else None)
        
        # Agregar nombres usando config.py
        df['entidad'] = df.apply(
            lambda row: get_nombre_entidad(row['idtrabajo'], row['envio']),
            axis=1
        )
        
        # Filtrar solo las que tienen nombre (están en config)
        df = df[df['entidad'].notna()].copy()
        
        # Reordenar columnas
        df = df[['entidad', 'idtrabajo', 'envio', 'total_debe', 'total_haber', 'saldo_neto']]
        
        return df
    except Exception as e:
        print(f"Error en get_saldo_por_entidad(): {e}")
        return pd.DataFrame()
    finally:
        if conn:
            conn.close()


def get_movimientos_entidad(idtrabajo, idenvio, anio=None, cuota=None):
    """
    Obtiene el detalle completo de movimientos para una entidad y envío específicos.
    Filtra por año y cuota si se proporcionan.
    
    Args:
        idtrabajo: Identificador de la entidad
        idenvio: Identificador del envío
        anio: Año del período (opcional)
        cuota: Mes del período 1-12 (opcional)
    
    Returns:
        DataFrame con todas las columnas de ctactetrabajo más nombre_entidad
    """
    conditions = ["c.idtrabajo = %s", "c.envio = %s"]
    params = [idtrabajo, idenvio]
    
    if anio is not None:
        conditions.append("c.anio = %s")
        params.append(anio)
    
    if cuota is not None:
        conditions.append("c.cuota = %s")
        params.append(cuota)
    
    where_clause = "WHERE " + " AND ".join(conditions)
    
    sql = f"""
        SELECT 
            c.*
        FROM ctactetrabajo c
        {where_clause}
        ORDER BY c.fecha DESC, c.id DESC
    """
    
    conn = None
    try:
        conn = get_connection()
        df = pd.read_sql(sql, conn, params=params)
        
        # Agregar nombre de entidad usando config.py
        nombre = get_nombre_entidad(idtrabajo, idenvio)
        if nombre:
            df['nombre_entidad'] = nombre
        
        return df
    except Exception as e:
        print(f"Error en get_movimientos_entidad(): {e}")
        return pd.DataFrame()
    finally:
        if conn:
            conn.close()
