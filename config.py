"""
Configuración del dashboard - constantes y variables de entorno
"""
import os
from dotenv import load_dotenv

# Cargar variables de entorno desde .env
load_dotenv()

# Determinar el entorno (development o production)
ENVIRONMENT = os.getenv("ENVIRONMENT", "development").lower()

# Configuración de base de datos MySQL según el entorno
if ENVIRONMENT == "production":
    # Variables de producción
    DB_HOST = os.getenv("DB_HOST_PROD", "localhost")
    DB_PORT = int(os.getenv("DB_PORT_PROD", "3306"))
    DB_NAME = os.getenv("DB_NAME_PROD")
    DB_USER = os.getenv("DB_USER_PROD")
    DB_PASSWORD = os.getenv("DB_PASSWORD_PROD")
else:
    # Variables de desarrollo (por defecto)
    DB_HOST = os.getenv("DB_HOST_DEV", "localhost")
    DB_PORT = int(os.getenv("DB_PORT_DEV", "3306"))
    DB_NAME = os.getenv("DB_NAME_DEV")
    DB_USER = os.getenv("DB_USER_DEV")
    DB_PASSWORD = os.getenv("DB_PASSWORD_DEV")

# Configuración de la aplicación
DEBUG = os.getenv("DEBUG", "False").lower() == "true"
PORT = int(os.getenv("PORT", "8050"))

# Tolerancia de desvío para porcentajes de procesamiento y comisión
# El % real es aceptable si está dentro de ±TOLERANCIA_PCT puntos porcentuales del valor esperado
TOLERANCIA_PCT = 2.0

# Grupos tipo/clase (valores fijos del negocio)
TIPOS_LIQUIDACION = ["IM", "MI", "IS", "CP"]
TIPOS_INGRESOS = ["IT", "IA", "IC", "IE"]  # cobranzas recibidas
TIPOS_EGRESOS = ["ET", "EC", "EE"]  # devoluciones y comisiones
TIPOS_AJUSTES = ["AN", "AP"]

# Para detección de faltantes usar solo estos (excluir CP, AN, AP)
TIPOS_LIQUIDACION_REAL = ["IM", "MI", "IS"]
TIPOS_COBRANZA_REAL = ["IT", "IA", "IC", "IE"]

# Clases de comisión
CLASES_COMISION = ["GC", "CO"]

# Mapeo de meses
MESES = {
    1: "Ene", 2: "Feb", 3: "Mar", 4: "Abr", 5: "May", 6: "Jun",
    7: "Jul", 8: "Ago", 9: "Sep", 10: "Oct", 11: "Nov", 12: "Dic"
}

# Paleta de colores del dashboard (alineada a assets/style.css)
COLOR_AZUL = "#378ADD"
COLOR_VERDE = "#1D9E75"
COLOR_AMBAR = "#EF9F27"
COLOR_ROJO = "#E24B4A"
COLOR_GRIS = "#B4B2A9"
# Requerido para forma de pago IE (Efectivo)
COLOR_VIOLETA = "#8B5CF6"

# Colores por forma de pago (cobranzas)
COLORES_FORMAS_PAGO = {
    "IT": COLOR_AZUL,     # Transferencia
    "IA": COLOR_VERDE,    # FDC
    "IC": COLOR_AMBAR,    # Cheque
    "IE": COLOR_VIOLETA,  # Efectivo
}

# Nombres de entidades - mapeo por idtrabajo (mayoría de casos)
# Solo 4 entidades necesitan combinación idtrabajo-envio (ver NOMBRES_ENTIDADES_ENVIO)
NOMBRES_ENTIDADES = {
    2: "Bioplanta",
    3: "Diputados",
    4: "Senadores",
    6: "Ciudad de Mza",
    9: "Guaymallen",
    10: "Junin",
    11: "La paz",
    12: "Las heras-sagam",
    13: "Lujan",
    16: "Rivadavia",
    17: "San Carlos",
    18: "San Martin",
    21: "Tupungato",
    22: "Lavalle",
    24: "Correos",
    25: "Irrigacion",
    26: "Telefonicos",
    29: "UMTSA",
    30: "Escuela Avellaneda",
    34: "Naranja",
    39: "CEC",
    46: "Visa",
    47: "Mastercard",
    49: "Hotel Uspallata",
    50: "Cocheria Alarcon",
}

# Nombres de entidades que requieren combinación idtrabajo-envio (solo 4 casos)
NOMBRES_ENTIDADES_ENVIO = {
    (5, 20): "CUAD AMAS",
    (5, 21): "CUAD FATAG",
    (7, 15): "Godoy Cruz- sindicato",
    (7, 24): "Godoy Cruz- amas",
    (8, 12): "Gral Alvear-sindicato",
    (8, 23): "Gral Alvear-fatag",
    (20, 7): "Tunuyan-sindicato",
    (20, 23): "Tunuyan-fatag",
    (14,10): "Maipu SOEMM",
    (14,54):"Maipu lotes",
    (16,23):"Rivadavia FATAG",
    (16,6):"Rivadavia- sindicato",
}

# Devoluciones que se restan de la cobranza bruta (IT/IA/IC/IE en haber) solo en estas entidades.
# El importe a restar va en el campo **debe** (no en haber).
#
# Luján y Lavalle: basta con clase DV (cualquier tipo).
# Tupungato: tipo ET/EE/EC y clase CS (hay IM+CS u otros que no son devolución de cobranza).
COBRANZA_DEVOLUCIONES = {
    (13, 11): {"clase": "DV"},
    (22, 29): {"clase": "DV"},
    (21, 8): {"tipo": ["ET", "EE", "EC"], "clase": "CS"},
}


def codigos_tipo_devolucion(cfg: dict | None) -> list:
    """
    Lista de tipos a filtrar en la columna `tipo`. Lista vacía = no filtrar por tipo (solo clase).
    """
    if not cfg:
        return []
    raw = cfg.get("tipo")
    if raw is None:
        raw = cfg.get("tipos")
    if raw is None:
        return []
    if isinstance(raw, str):
        return [raw.strip().upper()]
    return [str(x).strip().upper() for x in raw]

# Parámetros por entidad/envío
# Para la mayoría: clave es solo idtrabajo (int)
# Para 4 casos especiales: clave es tupla (idtrabajo, idenvio)
# Valor: {"proc": % esperado procesamiento, "com": % esperado comisión o None}
PARAMETROS_ENTIDAD = {
    # Entidades que solo requieren idtrabajo
    2: {"proc": 6.0, "com": None},
    3: {"proc": 0.0, "com": None},
    4: {"proc": 0.0, "com": None},
    6: {"proc": 8.0, "com": 6.0},
    9: {"proc": 1.2, "com": 9.0},
    10: {"proc": 1.0, "com": None},
    11: {"proc": 4.0, "com": None},
    12: {"proc": 3.0, "com": None},
    13: {"proc": 0.0, "com": 8.0},
    17: {"proc": 3.0, "com": None},
    18: {"proc": 2.0, "com": None},
    21: {"proc": 0.0, "com": 7.0},
    22: {"proc": 0.0, "com": 5.0},
    24: {"proc": 0.0, "com": None},
    25: {"proc": 20.0, "com": None},
    30: {"proc": 4.0, "com": None},
    34: {"proc": 6.0, "com": None},
    39: {"proc": 0.0, "com": None},
    46: {"proc": 2.0, "com": None},
    47: {"proc": 2.0, "com": None},
    49: {"proc": 0.0, "com": None},
    # Entidades que requieren combinación idtrabajo-envio
    (5, 20): {"proc": 2.0, "com": None},
    (5, 21): {"proc": 2.0, "com": None},
    (7, 15): {"proc": 2.0, "com": 10.0},
    (7, 24): {"proc": 2.0, "com": None},
    (8, 12): {"proc": 3.0, "com": 4.0},
    (8, 23): {"proc": 3.0, "com": None},
    (20, 7): {"proc": 5.0, "com": None},
    (20, 23): {"proc": 5.0, "com": None},
    (14,10): {"proc": 10.0, "com": None},
    (14,54): {"proc": 10.0, "com": None},
    (16,23): {"proc": 1.0, "com": None},
}

# Parámetros de vencimiento por envío (clave: nombre del envío)
# Usado en la página "Control de carga" para determinar pendiente/vencido.
VENCIMIENTOS = {
    "CEC": {"desfasaje": 1, "dia_corte": 30},
    "Correos": {"desfasaje": 1, "dia_corte": 15},
    "Escuela Avellaneda": {"desfasaje": 2, "dia_corte": 31},
    "Hotel Uspallata": {"desfasaje": 1, "dia_corte": 20},
    "Irrigacion": {"desfasaje": 1, "dia_corte": 15},
    "Junin": {"desfasaje": 1, "dia_corte": 30},
    "La paz": {"desfasaje": 1, "dia_corte": 25},
    "Las heras-sagam": {"desfasaje": 1, "dia_corte": 15},
    "Lavalle": {"desfasaje": 2, "dia_corte": 30},
    "Lujan": {"desfasaje": 1, "dia_corte": 20},
    "Maipu SOEMM": {"desfasaje": 1, "dia_corte": 25},
    "Maipu lotes": {"desfasaje": 1, "dia_corte": 25},
    "Mastercard": {"desfasaje": 1, "dia_corte": 30},
    "Naranja": {"desfasaje": 1, "dia_corte": 20},
    "Rivadavia FATAG": {"desfasaje": 2, "dia_corte": 25},
    "Rivadavia- sindicato": {"desfasaje": 2, "dia_corte": 25},
    "San Carlos": {"desfasaje": 0, "dia_corte": 30},
    "San Martin": {"desfasaje": 1, "dia_corte": 31},
    "Tupungato": {"desfasaje": 1, "dia_corte": 30},
    "UMTSA": {"desfasaje": 1, "dia_corte": 30},
    "Visa": {"desfasaje": 1, "dia_corte": 15},
    "Bioplanta": {"desfasaje": 2, "dia_corte": 30},
    "Ciudad de Mza": {"desfasaje": 1, "dia_corte": 15},
    "Cocheria Alarcon": {"desfasaje": 1, "dia_corte": 30},
    "CUAD AMAS": {"desfasaje": 3, "dia_corte": 31},
    "CUAD FATAG": {"desfasaje": 3, "dia_corte": 31},
    "Diputados": {"desfasaje": 2, "dia_corte": 10},
    "Godoy Cruz- amas": {"desfasaje": 1, "dia_corte": 20},
    "Godoy Cruz- sindicato": {"desfasaje": 2, "dia_corte": 15},
    "Gral Alvear-fatag": {"desfasaje": 1, "dia_corte": 30},
    "Gral Alvear-sindicato": {"desfasaje": 3, "dia_corte": 30},
    "Guaymallen": {"desfasaje": 2, "dia_corte": 25},
    "Senadores": {"desfasaje": 2, "dia_corte": 15},
    "Tunuyan-fatag": {"desfasaje": 1, "dia_corte": 15},
    "Tunuyan-sindicato": {"desfasaje": 2, "dia_corte": 30},
}


def get_nombre_entidad(idtrabajo, idenvio=None):
    """
    Obtiene el nombre de una entidad.
    Primero busca en NOMBRES_ENTIDADES_ENVIO si se proporciona idenvio,
    luego en NOMBRES_ENTIDADES por idtrabajo.
    
    Args:
        idtrabajo: Identificador de la entidad
        idenvio: Identificador del envío (opcional)
    
    Returns:
        str: Nombre de la entidad o None si no se encuentra
    """
    if idenvio is not None:
        key = (idtrabajo, idenvio)
        if key in NOMBRES_ENTIDADES_ENVIO:
            return NOMBRES_ENTIDADES_ENVIO[key]
    
    return NOMBRES_ENTIDADES.get(idtrabajo)


def get_regla_devoluciones_cobranza(idtrabajo, idenvio):
    """
    Regla para restar devoluciones de la cobranza bruta, o None si no aplica.
    Clave exacta (idtrabajo, idenvio) según COBRANZA_DEVOLUCIONES.
    """
    if idenvio is None:
        return None
    return COBRANZA_DEVOLUCIONES.get((int(idtrabajo), int(idenvio)))


def get_parametros_entidad(idtrabajo, idenvio=None):
    """
    Obtiene los parámetros (procesamiento y comisión) de una entidad.
    Primero busca en combinación idtrabajo-envio si se proporciona idenvio,
    luego solo por idtrabajo.
    
    Args:
        idtrabajo: Identificador de la entidad
        idenvio: Identificador del envío (opcional)
    
    Returns:
        dict: {"proc": float o None, "com": float o None} o None si no se encuentra
    """
    if idenvio is not None:
        key = (idtrabajo, idenvio)
        if key in PARAMETROS_ENTIDAD:
            return PARAMETROS_ENTIDAD[key]
    
    return PARAMETROS_ENTIDAD.get(idtrabajo)
