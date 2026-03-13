"""
Configuración del dashboard - constantes y variables de entorno
"""
import os
from dotenv import load_dotenv

# Cargar variables de entorno desde .env
load_dotenv()

# Configuración de base de datos MySQL
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", "3306"))
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")

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

# Parámetros por entidad/envío
# Clave: (idtrabajo, idenvio)
# Valor: {"proc": % esperado procesamiento, "com": % esperado comisión o None}
PARAMETROS_ENTIDAD = {
    (25, 17): {"proc": 20.0, "com": None},
    (6, 13): {"proc": 8.0, "com": 6.0},
    (7, 15): {"proc": 1.0, "com": 10.0},
    (14, 10): {"proc": 10.0, "com": None},
    (9, 14): {"proc": 1.0, "com": 9.0},
    (13, 11): {"proc": 0.0, "com": 8.0},
    (21, 8): {"proc": 0.0, "com": 7.0},
    (8, 12): {"proc": 3.0, "com": 4.0},
    (34, 33): {"proc": 6.0, "com": None},
    (2, 18): {"proc": 6.0, "com": None},
    (20, 7): {"proc": 5.0, "com": None},
    (20, 23): {"proc": 5.0, "com": None},
    (22, 29): {"proc": 0.0, "com": 5.0},
    (30, 26): {"proc": 4.0, "com": None},
    (11, 24): {"proc": 4.0, "com": None},
    (8, 23): {"proc": 3.0, "com": None},
    (17, 5): {"proc": 3.0, "com": None},
    (12, 22): {"proc": 3.0, "com": None},
    (47, 45): {"proc": 2.0, "com": None},
    (7, 24): {"proc": 2.0, "com": None},
    (46, 44): {"proc": 2.0, "com": None},
    (18, 9): {"proc": 2.0, "com": None},
    (5, 21): {"proc": 2.0, "com": None},
    (5, 20): {"proc": 2.0, "com": None},
    (16, 23): {"proc": 1.0, "com": None},
    (10, 24): {"proc": 1.0, "com": None},
    (24, 16): {"proc": 0.0, "com": None},
    (39, 37): {"proc": 0.0, "com": None},
    (3, 24): {"proc": 0.0, "com": None},
    (4, 24): {"proc": 0.0, "com": None},
    (49, 46): {"proc": 0.0, "com": None},
}
