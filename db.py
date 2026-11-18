# -*- coding: utf-8 -*-
"""
db.py
-----
Conexion a la base de datos MySQL (Alwaysdata) de la "Libreria El Saber".

Las credenciales se leen del archivo `.env` que esta junto a este archivo.
Si en el servidor defines las variables de entorno directamente, esas tienen
prioridad sobre el `.env`.

Uso desde otros modulos:

    import db

    bd = db.conectar_bd()
    filas = bd.fetchall("SELECT * FROM libros WHERE precio > %s", (20,))
    bd.commit()
    bd.close()

IMPORTANTE: MySQL usa `%s` como marcador de parametros (no `?` como SQLite).
"""

import os

import pymysql
from pymysql.cursors import DictCursor

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover
    load_dotenv = None

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
RUTA_ENV = os.path.join(BASE_DIR, ".env")

# Carga el archivo .env (no sobrescribe variables ya definidas en el sistema).
if load_dotenv is not None:
    load_dotenv(RUTA_ENV)


class ErrorConfiguracion(Exception):
    """Falta algun dato de conexion en el archivo .env."""


# Variables obligatorias para poder conectar.
VARIABLES_REQUERIDAS = ("DB_HOST", "DB_NAME", "DB_USER", "DB_PASSWORD")

# Valores de ejemplo que NO deben usarse tal cual.
VALORES_DE_EJEMPLO = (
    "ESCRIBE_AQUI_TU_CONTRASENA",
    "TUCUENTA",
)


def configuracion():
    """Devuelve los datos de conexion ya validados."""
    faltan = [v for v in VARIABLES_REQUERIDAS if not os.environ.get(v)]
    if faltan:
        raise ErrorConfiguracion(
            "Faltan datos en el archivo .env: " + ", ".join(faltan)
        )

    host = os.environ["DB_HOST"].strip()
    usuario = os.environ["DB_USER"].strip()
    clave = os.environ["DB_PASSWORD"]

    if any(marca in host or marca in usuario or clave == marca
           for marca in VALORES_DE_EJEMPLO):
        raise ErrorConfiguracion(
            "El archivo .env todavia tiene valores de ejemplo.\n"
            "Abrelo y reemplaza TUCUENTA y ESCRIBE_AQUI_TU_CONTRASENA por tus "
            "datos reales de Alwaysdata."
        )

    try:
        puerto = int(os.environ.get("DB_PORT") or 3306)
    except ValueError:
        raise ErrorConfiguracion("DB_PORT debe ser un numero (por ejemplo 3306).")

    return {
        "host": host,
        "port": puerto,
        "user": usuario,
        "password": clave,
        "database": os.environ["DB_NAME"].strip(),
        "charset": os.environ.get("DB_CHARSET") or "utf8mb4",
    }


def conectar(con_base_de_datos=True, con_tiempo_limite=10):
    """
    Abre una conexion nueva con MySQL.

    Si `con_base_de_datos` es False se conecta al servidor sin seleccionar
    ninguna base (util para crearla).
    """
    datos = configuracion()

    parametros = {
        "host": datos["host"],
        "port": datos["port"],
        "user": datos["user"],
        "password": datos["password"],
        "charset": datos["charset"],
        "cursorclass": DictCursor,
        "autocommit": False,
        "connect_timeout": con_tiempo_limite,
    }
    if con_base_de_datos:
        parametros["database"] = datos["database"]

    return pymysql.connect(**parametros)


class BaseDatos:
    """Envoltorio sencillo sobre una conexion de PyMySQL."""

    def __init__(self, conexion):
        self.conexion = conexion

    # -- Consultas ---------------------------------------------------------
    def _cursor(self, sql, parametros):
        cursor = self.conexion.cursor()
        if parametros:
            cursor.execute(sql, parametros)
        else:
            cursor.execute(sql)
        return cursor

    def execute(self, sql, parametros=()):
        """Ejecuta una sentencia y devuelve el cursor (para leer .lastrowid)."""
        return self._cursor(sql, parametros)

    def fetchall(self, sql, parametros=()):
        cursor = self.conexion.cursor()
        try:
            if parametros:
                cursor.execute(sql, parametros)
            else:
                cursor.execute(sql)
            return cursor.fetchall()
        finally:
            cursor.close()

    def fetchone(self, sql, parametros=()):
        cursor = self.conexion.cursor()
        try:
            if parametros:
                cursor.execute(sql, parametros)
            else:
                cursor.execute(sql)
            return cursor.fetchone()
        finally:
            cursor.close()

    # -- Transacciones -----------------------------------------------------
    def commit(self):
        self.conexion.commit()

    def rollback(self):
        self.conexion.rollback()

    def close(self):
        try:
            self.conexion.close()
        except Exception:
            pass


def conectar_bd():
    """Conexion lista para usar, envuelta en `BaseDatos`."""
    return BaseDatos(conectar())


def describir_destino():
    """Texto corto con el servidor y la base configurados (sin la clave)."""
    datos = configuracion()
    return "{}:{}/{}".format(datos["host"], datos["port"], datos["database"])