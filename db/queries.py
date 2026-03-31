"""
Consultas SQL parametrizadas a la base de datos.
Todas las funciones retornan DataFrames de pandas.
"""
import pandas as pd
from db.connection import get_connection
from config import (
    get_nombre_entidad,
    PROCESAMIENTO_USA_IM_GC_IDS,
    TIPOS_LIQUIDACION_REAL,
    TIPOS_COBRANZA_REAL,
)


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


def get_gastos_procesamiento_global(anio=None, cuota=None):
    """
    Gastos de procesamiento (reales): IM+GP en haber, salvo entidades en
    ``PROCESAMIENTO_USA_IM_GC_IDS`` que usan IM+GC en haber.

    Args:
        anio: filtro opcional por año del período
        cuota: filtro opcional por mes (1-12)

    Returns:
        DataFrame con una fila: gastos_procesamiento (float)
    """
    ids_s = ",".join(str(int(x)) for x in sorted(PROCESAMIENTO_USA_IM_GC_IDS))
    extra = []
    params = []

    if anio is not None:
        extra.append("c.anio = %s")
        params.append(int(anio))
    if cuota is not None:
        extra.append("c.cuota = %s")
        params.append(int(cuota))

    where_rest = (" AND " + " AND ".join(extra)) if extra else ""

    sql = f"""
        SELECT COALESCE(SUM(
            CASE
                WHEN c.idtrabajo IN ({ids_s}) AND c.tipo = 'IM' AND c.clase = 'GC' THEN c.haber
                WHEN c.idtrabajo NOT IN ({ids_s}) AND c.tipo = 'IM' AND c.clase = 'GP' THEN c.haber
                ELSE 0
            END
        ), 0) AS gastos_procesamiento
        FROM ctactetrabajo c
        WHERE 1=1
        {where_rest}
    """

    conn = None
    try:
        conn = get_connection()
        if params:
            df = pd.read_sql(sql, conn, params=params)
        else:
            df = pd.read_sql(sql, conn)
        val = float(df.iloc[0]["gastos_procesamiento"]) if df is not None and not df.empty else 0.0
        return pd.DataFrame([{"gastos_procesamiento": val}])
    except Exception as e:
        print(f"Error en get_gastos_procesamiento_global(): {e}")
        return pd.DataFrame([{"gastos_procesamiento": 0.0}])
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
    
    # Traer nombre completo del usuario (si existe) con LEFT JOIN
    # usuario.idus = ctactetrabajo.usuario
    sql = f"""
        SELECT 
            c.*,
            CONCAT(u.nombre, ' ', u.apellido) AS usuario_nombre
        FROM ctactetrabajo c
        LEFT JOIN usuario u
            ON u.idus = c.usuario
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


def get_envios_trabajo():
    """
    Verificación: retorna los envíos (nombres) distintos.

    Nota: en este proyecto evitamos depender de la tabla `trabajo` (puede no tener
    columnas `envio`/`nombre`). Por eso, construimos los nombres a partir de las
    combinaciones (idtrabajo, envio) existentes en `ctactetrabajo` y el mapeo
    de `config.get_nombre_entidad()`.

    Returns:
        DataFrame con columna: envio
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
        if df is None or df.empty:
            return pd.DataFrame(columns=["envio"])

        df["envio"] = df.apply(lambda r: get_nombre_entidad(r["idtrabajo"], r["envio"]), axis=1)
        df = df[df["envio"].notna()].copy()
        df = df[["envio"]].drop_duplicates().sort_values("envio").reset_index(drop=True)
        return df
    except Exception as e:
        print(f"Error en get_envios_trabajo(): {e}")
        return pd.DataFrame()
    finally:
        if conn:
            conn.close()


def get_movimientos_control(anio: int):
    """
    Obtiene movimientos necesarios para la página Control de carga en un año.

    Incluye nombre de entidad y nombre de envío desde el mapeo de config.py
    (sin depender de tabla `trabajo`).

    Returns:
        DataFrame con columnas mínimas:
          idtrabajo, idenvio, anio, cuota, tipo, clase, debe, haber, fecha,
          entidad_nombre, envio_nombre
    """
    sql = """
        SELECT
            c.idtrabajo,
            c.envio AS idenvio,
            c.anio,
            c.cuota,
            c.tipo,
            c.clase,
            c.debe,
            c.haber,
            c.fecha
        FROM ctactetrabajo c
        WHERE c.anio = %s
    """

    conn = None
    try:
        conn = get_connection()
        df = pd.read_sql(sql, conn, params=[int(anio)])
        if df is None or df.empty:
            return pd.DataFrame()

        # Mapear nombre de envío/entidad según config (compatibles con VENCIMIENTOS)
        df["envio_nombre"] = df.apply(lambda r: get_nombre_entidad(r["idtrabajo"], r["idenvio"]), axis=1)
        # Para esta página, "Entidad" y "Envío" se muestran igual (nombre configurado)
        df["entidad_nombre"] = df["envio_nombre"]
        return df
    except Exception as e:
        print(f"Error en get_movimientos_control(): {e}")
        return pd.DataFrame()
    finally:
        if conn:
            conn.close()


def get_movimientos_cobranza_global(anio=None, cuota=None):
    """
    Filas agregadas por movimiento para calcular cobranza neta (ingresos + egresos devolución).

    Returns:
        DataFrame: idtrabajo, envio, anio, cuota, tipo, clase, haber, fecha
    """
    sql = """
        SELECT
            c.idtrabajo,
            c.envio,
            c.anio,
            c.cuota,
            c.tipo,
            c.clase,
            COALESCE(c.debe, 0) AS debe,
            COALESCE(c.haber, 0) AS haber,
            c.fecha
        FROM ctactetrabajo c
        WHERE c.tipo IN ('IT','IA','IC','IE','ET','EE','EC')
          AND (%s IS NULL OR c.anio = %s)
          AND (%s IS NULL OR c.cuota = %s)
    """
    conn = None
    try:
        conn = get_connection()
        params = [anio, anio, cuota, cuota]
        df = pd.read_sql(sql, conn, params=params)
        if df is not None and not df.empty:
            # Drivers pueden devolver Tipo/tipo distinto; el código espera nombres en minúsculas
            df.columns = [str(c).strip().lower() for c in df.columns]
        return df if df is not None else pd.DataFrame()
    except Exception as e:
        print(f"Error en get_movimientos_cobranza_global(): {e}")
        return pd.DataFrame()
    finally:
        if conn:
            conn.close()


def get_cobranza_por_periodo(anio=None):
    """
    SUM(haber) agrupado por anio, cuota, tipo (formas de pago).

    Returns:
        DataFrame con columnas: anio, cuota, tipo, total_haber
    """
    sql = """
        SELECT
            c.anio,
            c.cuota,
            c.tipo,
            COALESCE(SUM(c.haber), 0) AS total_haber
        FROM ctactetrabajo c
        WHERE c.tipo IN ('IT','IA','IC','IE')
          AND (%s IS NULL OR c.anio = %s)
        GROUP BY c.anio, c.cuota, c.tipo
        ORDER BY c.anio ASC, c.cuota ASC
    """

    conn = None
    try:
        conn = get_connection()
        params = [anio, anio]
        df = pd.read_sql(sql, conn, params=params)
        return df if df is not None else pd.DataFrame(columns=["anio", "cuota", "tipo", "total_haber"])
    except Exception as e:
        print(f"Error en get_cobranza_por_periodo(): {e}")
        return pd.DataFrame(columns=["anio", "cuota", "tipo", "total_haber"])
    finally:
        if conn:
            conn.close()


def get_cobranza_por_fecha(anio=None):
    """
    SUM(haber) agrupado por YEAR(fecha), MONTH(fecha), tipo (formas de pago).

    Returns:
        DataFrame con columnas: anio_fecha, mes_fecha, tipo, total_haber
    """
    sql = """
        SELECT
            YEAR(c.fecha) AS anio_fecha,
            MONTH(c.fecha) AS mes_fecha,
            c.tipo,
            COALESCE(SUM(c.haber), 0) AS total_haber
        FROM ctactetrabajo c
        WHERE c.tipo IN ('IT','IA','IC','IE')
          AND c.fecha IS NOT NULL
          AND (%s IS NULL OR YEAR(c.fecha) = %s)
        GROUP BY YEAR(c.fecha), MONTH(c.fecha), c.tipo
        ORDER BY YEAR(c.fecha) ASC, MONTH(c.fecha) ASC
    """

    conn = None
    try:
        conn = get_connection()
        params = [anio, anio]
        df = pd.read_sql(sql, conn, params=params)
        return df if df is not None else pd.DataFrame(columns=["anio_fecha", "mes_fecha", "tipo", "total_haber"])
    except Exception as e:
        print(f"Error en get_cobranza_por_fecha(): {e}")
        return pd.DataFrame(columns=["anio_fecha", "mes_fecha", "tipo", "total_haber"])
    finally:
        if conn:
            conn.close()


def get_comisiones_por_periodo(anio=None):
    """
    SUM(haber) de comisiones (clase GC/CO). Excluye IM+GC de entidades que usan esa
    combinación solo para gasto de procesamiento.

    Returns:
        DataFrame con columnas: anio, cuota, total_comisiones
    """
    ids_s = ",".join(str(int(x)) for x in sorted(PROCESAMIENTO_USA_IM_GC_IDS))
    sql = f"""
        SELECT
            c.anio,
            c.cuota,
            COALESCE(SUM(c.haber), 0) AS total_comisiones
        FROM ctactetrabajo c
        WHERE c.clase IN ('GC','CO')
          AND NOT (c.idtrabajo IN ({ids_s}) AND c.tipo = 'IM' AND c.clase = 'GC')
          AND (%s IS NULL OR c.anio = %s)
        GROUP BY c.anio, c.cuota
        ORDER BY c.anio ASC, c.cuota ASC
    """

    conn = None
    try:
        conn = get_connection()
        params = [anio, anio]
        df = pd.read_sql(sql, conn, params=params)
        return df if df is not None else pd.DataFrame(columns=["anio", "cuota", "total_comisiones"])
    except Exception as e:
        print(f"Error en get_comisiones_por_periodo(): {e}")
        return pd.DataFrame(columns=["anio", "cuota", "total_comisiones"])
    finally:
        if conn:
            conn.close()


def get_cobranza_entidad_por_periodo(idtrabajo, idenvio, anio=None):
    """
    Igual que get_cobranza_por_periodo, filtrando por entidad y envío.

    Returns:
        DataFrame con columnas: anio, cuota, tipo, total_haber
    """
    sql = """
        SELECT
            c.anio,
            c.cuota,
            c.tipo,
            COALESCE(SUM(c.haber), 0) AS total_haber
        FROM ctactetrabajo c
        WHERE c.idtrabajo = %s
          AND c.envio = %s
          AND c.tipo IN ('IT','IA','IC','IE')
          AND (%s IS NULL OR c.anio = %s)
        GROUP BY c.anio, c.cuota, c.tipo
        ORDER BY c.anio ASC, c.cuota ASC
    """

    conn = None
    try:
        conn = get_connection()
        params = [int(idtrabajo), int(idenvio), anio, anio]
        df = pd.read_sql(sql, conn, params=params)
        return df if df is not None else pd.DataFrame(columns=["anio", "cuota", "tipo", "total_haber"])
    except Exception as e:
        print(f"Error en get_cobranza_entidad_por_periodo(): {e}")
        return pd.DataFrame(columns=["anio", "cuota", "tipo", "total_haber"])
    finally:
        if conn:
            conn.close()


def get_saldo_acumulado_entidad(idtrabajo, idenvio):
    """
    Saldo acumulado real por período para una entidad/envío.

    - saldo_periodo = SUM(debe - haber) por anio+cuota
    - saldo_acumulado = cumsum(saldo_periodo) ordenado por anio+cuota
    - NO usar el campo `saldo` de la tabla
    """
    sql = """
        SELECT
            c.anio,
            c.cuota,
            COALESCE(SUM(c.debe - c.haber), 0) AS saldo_periodo
        FROM ctactetrabajo c
        WHERE c.idtrabajo = %s
          AND c.envio = %s
          AND NOT (UPPER(c.tipo) = 'CP' AND UPPER(c.clase) = 'CP')
        GROUP BY c.anio, c.cuota
        ORDER BY c.anio ASC, c.cuota ASC
    """

    conn = None
    try:
        conn = get_connection()
        df = pd.read_sql(sql, conn, params=[int(idtrabajo), int(idenvio)])
        if df is None or df.empty:
            return pd.DataFrame(columns=["anio", "cuota", "saldo_periodo", "saldo_acumulado"])

        df["anio"] = pd.to_numeric(df["anio"], errors="coerce").fillna(0).astype(int)
        df["cuota"] = pd.to_numeric(df["cuota"], errors="coerce").fillna(0).astype(int)
        df["saldo_periodo"] = pd.to_numeric(df["saldo_periodo"], errors="coerce").fillna(0.0)
        df = df.sort_values(["anio", "cuota"]).reset_index(drop=True)
        df["saldo_acumulado"] = df["saldo_periodo"].cumsum()
        return df
    except Exception as e:
        print(f"Error en get_saldo_acumulado_entidad(): {e}")
        return pd.DataFrame(columns=["anio", "cuota", "saldo_periodo", "saldo_acumulado"])
    finally:
        if conn:
            conn.close()
