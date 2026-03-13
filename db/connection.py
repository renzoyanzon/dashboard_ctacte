"""
Pool de conexiones MySQL usando mysql.connector
"""
import mysql.connector
from mysql.connector import pooling
from config import DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD

# Crear pool de conexiones
connection_pool = pooling.MySQLConnectionPool(
    pool_name="mutual_pool",
    pool_size=5,
    host=DB_HOST,
    port=DB_PORT,
    database=DB_NAME,
    user=DB_USER,
    password=DB_PASSWORD,
    autocommit=False
)


def get_connection():
    """
    Obtiene una conexión del pool.
    
    Returns:
        MySQLConnection: Conexión a la base de datos
    """
    return connection_pool.get_connection()
