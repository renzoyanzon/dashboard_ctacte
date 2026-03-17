"""
Consultas SQL parametrizadas a la base de datos.
Todas las funciones retornan DataFrames de pandas.
"""
import pandas as pd
from db.connection import get_connection
from config import get_nombre_entidad, TIPOS_LIQUIDACION_REAL, TIPOS_COBRANZA_REAL


def _build_or_entidades(entidades, params, alias="c"):
    """
    Construye condición OR para filtrar por múltiples entidades (idtrabajo, envio).
    Devuelve string SQL y agrega parámetros a `params`.
    """
    if not entidades:
        return None
    condiciones = []
    for idtrabajo, idenvio in entidades:
        condiciones.append(f"({alias}.idtrabajo = %s AND {alias}.envio = %s)")
        params.extend([int(idtrabajo), int(idenvio)])
    return f"({' OR '.join(condiciones)})" if condiciones else None


def _build_in_placeholders(values):
    """Devuelve placeholders %s,%s,... para un IN."""
    return ", ".join(["%s"] * len(values))


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
        cuota: Mes del período 1-12 (opcional, debe ser entero)
    
    Returns:
        DataFrame con columnas: entidad, idtrabajo, envio, total_debe, total_haber, saldo_neto
    """
    conditions = []
    params = []
    
    if anio is not None:
        conditions.append("c.anio = %s")
        params.append(int(anio))
    
    if cuota is not None:
        conditions.append("c.cuota = %s")
        params.append(int(cuota))
        print(f"[DEBUG] Filtro cuota aplicado: {int(cuota)} (tipo: {type(int(cuota))})")
    
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
        print(f"[DEBUG] Query get_saldo_por_entidad - Parámetros: anio={anio}, cuota={cuota}, params={params}")
        df = pd.read_sql(sql, conn, params=params if params else None)
        print(f"[DEBUG] Query retornó {len(df)} filas")
        
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


def get_totales_liquidado_cobrado(anio=None, cuota=None, entidades=None, clases_liquidacion=None):
    """
    KPIs globales: total liquidado (debe) y total cobrado (haber).

    - Liquidado: suma debe de TIPOS_LIQUIDACION_REAL y (opcionalmente) filtrado por clases.
    - Cobrado:  suma haber de TIPOS_COBRANZA_REAL.

    Args:
        anio: int opcional
        cuota: int opcional
        entidades: lista de tuplas (idtrabajo, envio) opcional
        clases_liquidacion: lista de clases (ej: ["M","CS","SS","SF"]) opcional

    Returns:
        DataFrame con columnas: liquidado, cobrado
    """
    conditions = []
    params = []

    if anio is not None:
        conditions.append("c.anio = %s")
        params.append(int(anio))
    if cuota is not None:
        conditions.append("c.cuota = %s")
        params.append(int(cuota))

    ent_cond = _build_or_entidades(entidades, params, alias="c")
    if ent_cond:
        conditions.append(ent_cond)

    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

    # IN placeholders (no concatenar valores en SQL)
    liq_tipos_ph = _build_in_placeholders(TIPOS_LIQUIDACION_REAL)
    cob_tipos_ph = _build_in_placeholders(TIPOS_COBRANZA_REAL)
    params_liq = [*params, *TIPOS_LIQUIDACION_REAL]
    params_cob = [*params, *TIPOS_COBRANZA_REAL]

    clase_filter_sql = ""
    if clases_liquidacion:
        clase_ph = _build_in_placeholders(clases_liquidacion)
        clase_filter_sql = f" AND c.clase IN ({clase_ph})"
        params_liq.extend(clases_liquidacion)

    sql_liq = f"""
        SELECT COALESCE(SUM(c.debe), 0) AS liquidado
        FROM ctactetrabajo c
        {where_clause}
          AND c.tipo IN ({liq_tipos_ph})
          {clase_filter_sql}
    """

    sql_cob = f"""
        SELECT COALESCE(SUM(c.haber), 0) AS cobrado
        FROM ctactetrabajo c
        {where_clause}
          AND c.tipo IN ({cob_tipos_ph})
    """

    conn = None
    try:
        conn = get_connection()
        df_liq = pd.read_sql(sql_liq, conn, params=params_liq)
        df_cob = pd.read_sql(sql_cob, conn, params=params_cob)
        liquidado = float(df_liq.iloc[0]["liquidado"]) if not df_liq.empty else 0.0
        cobrado = float(df_cob.iloc[0]["cobrado"]) if not df_cob.empty else 0.0
        # Siempre retornar DataFrame con al menos una fila
        return pd.DataFrame([{"liquidado": liquidado, "cobrado": cobrado}])
    except Exception as e:
        print(f"Error en get_totales_liquidado_cobrado(): {e}")
        import traceback
        traceback.print_exc()
        # Retornar DataFrame con valores en 0 en caso de error
        return pd.DataFrame([{"liquidado": 0.0, "cobrado": 0.0}])
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


def get_liquidado_cobrado_por_periodo(anio=None, entidades=None):
    """
    Obtiene el total liquidado y cobrado agrupado por período (anio, cuota).
    Solo incluye tipos de liquidación real (IM, MI, IS) y cobranza real (IT, IA, IC, IE).
    
    Args:
        anio: Año del período (opcional)
        entidades: Lista de tuplas (idtrabajo, idenvio) para filtrar (opcional)
    
    Returns:
        DataFrame con columnas: anio, cuota, liquidado, cobrado
    """
    conditions = []
    params = []
    
    if anio is not None:
        conditions.append("c.anio = %s")
        params.append(int(anio))
    
    # Filtrar por entidades si se proporcionan
    if entidades and len(entidades) > 0:
        # Crear condición IN para las entidades
        placeholders = ','.join(['%s'] * len(entidades) * 2)  # 2 por cada tupla (idtrabajo, idenvio)
        condiciones_entidades = []
        for idtrabajo, idenvio in entidades:
            condiciones_entidades.append(f"(c.idtrabajo = %s AND c.envio = %s)")
            params.append(int(idtrabajo))
            params.append(int(idenvio))
        
        if condiciones_entidades:
            conditions.append(f"({' OR '.join(condiciones_entidades)})")
    
    where_clause = ""
    if conditions:
        where_clause = "WHERE " + " AND ".join(conditions)
    
    # Crear lista de tipos para la query (escapar comillas correctamente)
    tipos_liq_str = "', '".join(TIPOS_LIQUIDACION_REAL)
    tipos_cob_str = "', '".join(TIPOS_COBRANZA_REAL)
    
    sql = f"""
        SELECT 
            c.anio,
            c.cuota,
            SUM(CASE WHEN c.tipo IN ('{tipos_liq_str}') THEN c.debe ELSE 0 END) AS liquidado,
            SUM(CASE WHEN c.tipo IN ('{tipos_cob_str}') THEN c.haber ELSE 0 END) AS cobrado
        FROM ctactetrabajo c
        {where_clause}
        GROUP BY c.anio, c.cuota
        ORDER BY c.anio DESC, c.cuota DESC
    """
    
    conn = None
    try:
        conn = get_connection()
        df = pd.read_sql(sql, conn, params=params if params else None)
        return df
    except Exception as e:
        print(f"Error en get_liquidado_cobrado_por_periodo(): {e}")
        import traceback
        traceback.print_exc()
        return pd.DataFrame()
    finally:
        if conn:
            conn.close()


def get_saldo_acumulado_por_periodo(anio=None, entidades=None):
    """
    Obtiene el saldo acumulado total por período, calculado como suma acumulativa
    de (debe - haber) ordenado por anio y cuota.
    
    Args:
        anio: Año del período (opcional)
        entidades: Lista de tuplas (idtrabajo, idenvio) para filtrar (opcional)
    
    Returns:
        DataFrame con columnas: anio, cuota, saldo_acumulado
    """
    conditions = []
    params = []
    
    if anio is not None:
        conditions.append("c.anio = %s")
        params.append(int(anio))
    
    # Filtrar por entidades si se proporcionan
    if entidades and len(entidades) > 0:
        # Crear condición OR para las entidades
        condiciones_entidades = []
        for idtrabajo, idenvio in entidades:
            condiciones_entidades.append(f"(c.idtrabajo = %s AND c.envio = %s)")
            params.append(int(idtrabajo))
            params.append(int(idenvio))
        
        if condiciones_entidades:
            conditions.append(f"({' OR '.join(condiciones_entidades)})")
    
    where_clause = ""
    if conditions:
        where_clause = "WHERE " + " AND ".join(conditions)
    
    sql = f"""
        SELECT 
            c.anio,
            c.cuota,
            SUM(c.debe - c.haber) AS saldo_periodo
        FROM ctactetrabajo c
        {where_clause}
        GROUP BY c.anio, c.cuota
        ORDER BY c.anio ASC, c.cuota ASC
    """
    
    conn = None
    try:
        conn = get_connection()
        df = pd.read_sql(sql, conn, params=params if params else None)
        
        # Calcular saldo acumulado
        if not df.empty:
            df['saldo_acumulado'] = df['saldo_periodo'].cumsum()
        else:
            df['saldo_acumulado'] = 0
        
        return df
    except Exception as e:
        print(f"Error en get_saldo_acumulado_por_periodo(): {e}")
        return pd.DataFrame()
    finally:
        if conn:
            conn.close()
