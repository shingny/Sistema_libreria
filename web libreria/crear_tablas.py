# -*- coding: utf-8 -*-
"""
crear_tablas.py
---------------
Crea las tablas de la "Libreria El Saber" en MySQL (Alwaysdata) usando Python.

Las credenciales se leen del archivo `.env` (ver `db.py`).

Uso:
    python crear_tablas.py              # crea las tablas (no toca los datos)
    python crear_tablas.py --datos      # crea las tablas + 10 categorias y 29 libros
    python crear_tablas.py --recrear    # borra y vuelve a crear (pide confirmacion)

El orden de creacion es importante:
    1. categorias   (no depende de nadie)
    2. libros       (depende de categorias)
    3. consultas    (depende de libros)
"""

import os
import re
import sys

import pymysql

import db as bd
from init_db import CATEGORIAS, LIBROS, IMG_DIR, crear_portada, slugify


# ---------------------------------------------------------------------------
# Definicion de las tablas, en orden de creacion.
# ---------------------------------------------------------------------------
TABLAS = [
    (
        "categorias",
        """
        CREATE TABLE IF NOT EXISTS categorias (
            id          TINYINT UNSIGNED NOT NULL AUTO_INCREMENT,
            nombre      VARCHAR(60)      NOT NULL,
            slug        VARCHAR(60)      NOT NULL,
            descripcion VARCHAR(180)     NOT NULL DEFAULT '',
            color       CHAR(7)          NOT NULL DEFAULT '#4338ca',
            icono       VARCHAR(20)      NOT NULL DEFAULT 'book',
            PRIMARY KEY (id),
            UNIQUE KEY uq_categorias_slug (slug)
        ) ENGINE=InnoDB
          DEFAULT CHARSET=utf8mb4
          COLLATE=utf8mb4_unicode_ci
        """,
    ),
    (
        "libros",
        """
        CREATE TABLE IF NOT EXISTS libros (
            id           INT UNSIGNED     NOT NULL AUTO_INCREMENT,
            titulo       VARCHAR(180)     NOT NULL,
            autor        VARCHAR(120)     NOT NULL,
            categoria_id TINYINT UNSIGNED NOT NULL,
            editorial    VARCHAR(120)     NOT NULL DEFAULT '',
            anio         SMALLINT UNSIGNED NOT NULL DEFAULT 0,
            isbn         VARCHAR(20)      NOT NULL DEFAULT '',
            precio       DECIMAL(8,2)     NOT NULL DEFAULT 0.00,
            destacado    TINYINT(1)       NOT NULL DEFAULT 0,
            descripcion  TEXT             NULL,
            imagen       VARCHAR(255)     NOT NULL DEFAULT '',
            creado_en    TIMESTAMP        NOT NULL DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (id),
            KEY idx_libros_categoria (categoria_id),
            KEY idx_libros_titulo (titulo),
            KEY idx_libros_autor (autor),
            CONSTRAINT fk_libros_categoria
                FOREIGN KEY (categoria_id) REFERENCES categorias (id)
                ON UPDATE CASCADE
                ON DELETE RESTRICT
        ) ENGINE=InnoDB
          DEFAULT CHARSET=utf8mb4
          COLLATE=utf8mb4_unicode_ci
        """,
    ),
    (
        "consultas",
        """
        CREATE TABLE IF NOT EXISTS consultas (
            id       BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
            libro_id INT UNSIGNED    NULL,
            cliente  VARCHAR(80)     NOT NULL DEFAULT '',
            mensaje  VARCHAR(1000)   NOT NULL DEFAULT '',
            fecha    TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (id),
            KEY idx_consultas_libro (libro_id),
            KEY idx_consultas_fecha (fecha),
            CONSTRAINT fk_consultas_libro
                FOREIGN KEY (libro_id) REFERENCES libros (id)
                ON UPDATE CASCADE
                ON DELETE SET NULL
        ) ENGINE=InnoDB
          DEFAULT CHARSET=utf8mb4
          COLLATE=utf8mb4_unicode_ci
        """,
    ),
]

# Para borrar hay que ir al reves (primero las que dependen de otras).
ORDEN_BORRADO = ["consultas", "libros", "categorias"]

LINEA = "=" * 64


# ---------------------------------------------------------------------------
# Utilidades de consola
# ---------------------------------------------------------------------------
def explicar_error(error):
    """Traduce los errores mas comunes de MySQL a un mensaje entendible."""
    codigo = error.args[0] if error.args else None
    textos = {
        1045: ("Usuario o contrasena incorrectos.\n"
               "       Revisa DB_USER y DB_PASSWORD en el archivo .env."),
        2003: ("No se pudo conectar al servidor.\n"
               "       Revisa DB_HOST y DB_PORT en el archivo .env.\n"
               "       En Alwaysdata activa el acceso remoto a MySQL:\n"
               "       Bases de datos -> MySQL -> tu usuario -> Acceso remoto."),
        1049: ("La base de datos no existe.\n"
               "       Creala en Alwaysdata o revisa DB_NAME."),
        1044: ("El usuario no tiene permisos sobre esa base de datos.\n"
               "       Revisa DB_NAME y DB_USER."),
        2005: "El servidor indicado en DB_HOST no existe o esta mal escrito.",
    }
    if codigo in textos:
        return textos[codigo]
    return str(error)


def confirmar(pregunta):
    """Pide confirmacion por teclado. Devuelve True solo si se escribe SI."""
    try:
        respuesta = input(pregunta + " (escribe SI para continuar): ")
    except (EOFError, KeyboardInterrupt):
        print("")
        return False
    return respuesta.strip().upper() == "SI"


# ---------------------------------------------------------------------------
# Pasos
# ---------------------------------------------------------------------------
def crear_base_si_se_puede(datos):
    """
    Intenta crear la base de datos. En Alwaysdata la base ya existe (se crea
    desde el panel), asi que un fallo de permisos aqui es normal y no detiene
    el proceso.
    """
    nombre = datos["database"]

    if not re.match(r"^[A-Za-z0-9_]+$", nombre):
        print("[ERROR] El nombre de la base (DB_NAME) solo puede tener letras,")
        print("        numeros y guion bajo. Valor recibido:", nombre)
        return False

    try:
        conexion = bd.conectar(con_base_de_datos=False)
    except pymysql.MySQLError as error:
        print("[aviso] No se pudo abrir conexion con el servidor:")
        print("        " + explicar_error(error))
        return False

    try:
        with conexion.cursor() as cursor:
            cursor.execute(
                "CREATE DATABASE IF NOT EXISTS `{}` "
                "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci".format(nombre)
            )
        conexion.commit()
        print("[1/4] Base de datos `{}` lista.".format(nombre))
        return True
    except pymysql.MySQLError as error:
        print("[aviso] No se pudo crear la base (normal si ya existe en Alwaysdata).")
        print("        " + explicar_error(error))
        return False
    finally:
        conexion.close()


def borrar_tablas(conexion):
    print("\n[!] Borrando tablas existentes...")
    with conexion.cursor() as cursor:
        cursor.execute("SET FOREIGN_KEY_CHECKS = 0")
        for nombre in ORDEN_BORRADO:
            cursor.execute("DROP TABLE IF EXISTS `{}`".format(nombre))
            print("      - `{}` borrada".format(nombre))
        cursor.execute("SET FOREIGN_KEY_CHECKS = 1")
    conexion.commit()


def crear_tablas(conexion):
    print("\n[2/4] Creando tablas (en orden)...")
    for numero, (nombre, ddl) in enumerate(TABLAS, start=1):
        with conexion.cursor() as cursor:
            cursor.execute(ddl)
        conexion.commit()
        print("      {}. {:<12} ................ OK".format(numero, nombre))


def cargar_datos(conexion):
    """Inserta las 10 categorias y los 29 libros de ejemplo (si esta vacia)."""
    print("\n[3/4] Cargando datos de ejemplo...")

    with conexion.cursor() as cursor:
        cursor.execute("SELECT COUNT(*) AS total FROM categorias")
        ya_hay = cursor.fetchone()["total"]

    if ya_hay:
        print("      Ya existen categorias cargadas. No se inserta nada.")
        print("      (usa --recrear si quieres empezar de cero)")
        return

    # --- 1) Categorias ----------------------------------------------------
    ids = {}
    with conexion.cursor() as cursor:
        for nombre, slug, descripcion, color, icono in CATEGORIAS:
            cursor.execute(
                """INSERT INTO categorias (nombre, slug, descripcion, color, icono)
                   VALUES (%s, %s, %s, %s, %s)""",
                (nombre, slug, descripcion, color, icono),
            )
            ids[slug] = cursor.lastrowid
            print("      categoria {:<18} id={}".format(nombre, cursor.lastrowid))
    conexion.commit()

    # --- 2) Portadas + libros ---------------------------------------------
    total_libros = 0
    with conexion.cursor() as cursor:
        for (titulo, autor, slug_cat, editorial, anio, isbn,
             precio, destacado, descripcion) in LIBROS:

            carpeta = os.path.join(IMG_DIR, slug_cat)
            os.makedirs(carpeta, exist_ok=True)

            nombre_archivo = slugify(titulo) + ".svg"
            ruta_fisica = os.path.join(carpeta, nombre_archivo)

            if not os.path.exists(ruta_fisica):
                nombre_cat = next(c[0] for c in CATEGORIAS if c[1] == slug_cat)
                crear_portada(titulo, autor, slug_cat, nombre_cat, ruta_fisica)

            imagen = "/static/img/{}/{}".format(slug_cat, nombre_archivo)

            cursor.execute(
                """INSERT INTO libros
                   (titulo, autor, categoria_id, editorial, anio, isbn,
                    precio, destacado, descripcion, imagen)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                (titulo, autor, ids[slug_cat], editorial, anio, isbn,
                 precio, destacado, descripcion, imagen),
            )
            total_libros += 1
    conexion.commit()
    print("      libros insertados: {}".format(total_libros))
    print("      portadas en: {}".format(IMG_DIR))


def mostrar_resumen(conexion):
    print("\n[4/4] Resumen")
    print("      {:<14} {:>10}".format("Tabla", "Registros"))
    print("      " + "-" * 26)
    with conexion.cursor() as cursor:
        for nombre, _ddl in TABLAS:
            cursor.execute("SELECT COUNT(*) AS total FROM `{}`".format(nombre))
            print("      {:<14} {:>10}".format(nombre, cursor.fetchone()["total"]))


# ---------------------------------------------------------------------------
# Principal
# ---------------------------------------------------------------------------
def main():
    argumentos = sys.argv[1:]
    recrear = "--recrear" in argumentos
    con_datos = "--datos" in argumentos
    forzar = "--forzar" in argumentos

    print(LINEA)
    print("  Libreria El Saber  -  Creacion de la base de datos MySQL")
    print(LINEA)

    try:
        datos = bd.configuracion()
    except bd.ErrorConfiguracion as error:
        print("\n[ERROR] " + str(error))
        print("\nAbre el archivo .env y completa los datos de Alwaysdata.")
        return 1

    print("  Servidor : {}:{}".format(datos["host"], datos["port"]))
    print("  Base     : {}".format(datos["database"]))
    print("  Usuario  : {}".format(datos["user"]))

    if recrear:
        print("")
        if not forzar and not confirmar(
            "\n[!] ATENCION: se borraran TODAS las tablas y sus datos."
        ):
            print("Operacion cancelada. No se cambio nada.")
            return 1

    crear_base_si_se_puede(datos)

    # Conexion a la base ya creada.
    try:
        conexion = bd.conectar()
    except pymysql.MySQLError as error:
        print("\n[ERROR] No se pudo conectar a la base de datos:")
        print("        " + explicar_error(error))
        return 1

    try:
        if recrear:
            borrar_tablas(conexion)

        crear_tablas(conexion)

        if con_datos:
            cargar_datos(conexion)
        else:
            print("\n[3/4] Datos de ejemplo: omitidos (usa --datos para cargarlos).")

        mostrar_resumen(conexion)
    except pymysql.MySQLError as error:
        conexion.rollback()
        print("\n[ERROR] " + explicar_error(error))
        return 1
    finally:
        conexion.close()

    print("\n" + LINEA)
    print("  LISTO. Ya puedes iniciar la web:  python app.py")
    print(LINEA)
    return 0


if __name__ == "__main__":
    sys.exit(main())
