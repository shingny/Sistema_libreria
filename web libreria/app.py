# -*- coding: utf-8 -*-
"""
app.py
------
Servidor Flask de la "Libreria El Saber".

Rutas principales:
  GET  /                     -> Pagina web (catalogo).
  GET  /api/categorias       -> Lista de categorias con el total de libros.
  GET  /api/libros           -> Lista de libros. Filtros: ?q= ?categoria= ?orden= ?destacados=1
  GET  /api/libros/<id>      -> Detalle de un libro.
  POST /api/consultas        -> Registra una consulta (clic en WhatsApp).
  GET  /api/consultas        -> Ultimas consultas (requiere token de administrador).

Seguridad: ver el modulo `seguridad.py` (cabeceras HTTP, CSP, validacion de
entradas y limite de peticiones por IP).

Uso:
    python app.py
    (o)  flask --app app run

Las credenciales de MySQL se leen del archivo `.env` (ver el modulo `db.py`).

Variables de entorno opcionales:
    NOMBRE_LIBRERIA, WHATSAPP_NUMERO, WHATSAPP_DISPLAY
    DIRECCION, REFERENCIA, CORREO, HORARIO
    ADMIN_TOKEN, SECRET_KEY, HTTPS=1, HOST, PORT, FLASK_DEBUG=1
"""

import json
import os
import secrets
from datetime import datetime
from urllib.parse import quote

import pymysql
from flask import (
    Flask,
    abort,
    g,
    jsonify,
    redirect,
    render_template,
    request,
    url_for,
)

import db as bd
import seguridad
from init_db import slugify


def _env(nombre, por_defecto):
    """Lee una variable de entorno; si esta vacia usa el valor por defecto."""
    valor = os.environ.get(nombre)
    return valor if valor not in (None, "") else por_defecto


def ocultar_firma_servidor():
    """
    Evita que el servidor de desarrollo de Werkzeug anuncie su nombre y la
    version de Python (informacion util para un atacante).

    En produccion (gunicorn, waitress, nginx...) la cabecera "Server" la
    controla el servidor frontal; conviene ocultarla tambien alli.
    """
    try:
        from werkzeug.serving import BaseWSGIServer, WSGIRequestHandler
    except ImportError:  # pragma: no cover
        return

    def firma(_self):
        return "LibreriaElSaber"

    for clase in (BaseWSGIServer, WSGIRequestHandler):
        clase.server_version = "LibreriaElSaber"
        clase.sys_version = ""
        clase.version_string = firma


ocultar_firma_servidor()


# ----------------------- Configuracion de la libreria -----------------------
NOMBRE_LIBRERIA = _env("NOMBRE_LIBRERIA", "Libreria El Saber")
SLOGAN = _env("SLOGAN", "Tu proxima gran lectura esta aqui")
WHATSAPP_NUMERO = _env("WHATSAPP_NUMERO", "51943846909")   # +51 943 846 909 (Peru)
WHATSAPP_DISPLAY = _env("WHATSAPP_DISPLAY", "+51 943 846 909")

# --- Ubicacion (direccion temporal, reemplazar por la real) -----------------
DIRECCION = _env("DIRECCION", "Av. Los Libros 123, Cercado de Lima, Lima - Peru")
REFERENCIA = _env("REFERENCIA", "A una cuadra de la Plaza Mayor")
# Enlace "Como llegar" en Google Maps (no requiere API key).
MAPA_URL = "https://www.google.com/maps/search/?api=1&query=" + quote(DIRECCION)

CORREO = _env("CORREO", "ventas@libreriaelsaber.pe")
HORARIO = _env("HORARIO", "Lun a Sab: 9:00 am - 8:00 pm")

# --- Redes sociales (ejemplos; reemplazar por los reales) -------------------
REDES = [
    {"nombre": "Facebook",  "icono": "facebook",  "url": "https://facebook.com/libreriaelsaber"},
    {"nombre": "Instagram", "icono": "instagram", "url": "https://instagram.com/libreriaelsaber"},
    {"nombre": "TikTok",    "icono": "tiktok",    "url": "https://tiktok.com/@libreriaelsaber"},
    {"nombre": "YouTube",   "icono": "youtube",   "url": "https://youtube.com/@libreriaelsaber"},
    {"nombre": "WhatsApp",  "icono": "whatsapp",  "url": "https://wa.me/" + WHATSAPP_NUMERO},
]

# --- Seguridad ---------------------------------------------------------------
# Cuando el sitio se publique con HTTPS, arrancar con HTTPS=1.
SEGURO_HTTPS = os.environ.get("HTTPS") in ("1", "true", "si", "yes")

# URL publica del sitio. Se usa en og:image, canonical y sitemap. En local se
# detecta sola; al publicar conviene fijarla, por ejemplo:
#     SITIO_URL=https://sistema42.alwaysdata.net
SITIO_URL = _env("SITIO_URL", "").rstrip("/")

# Token para consultar el listado de solicitudes. Si no se define, se genera
# uno aleatorio en cada arranque y se muestra por consola.
ADMIN_TOKEN = _env("ADMIN_TOKEN", "")

app = Flask(__name__)
app.config.update(
    JSON_SORT_KEYS=False,
    # Tamano maximo de una peticion (evita envios gigantes que agoten memoria).
    MAX_CONTENT_LENGTH=32 * 1024,
    SECRET_KEY=_env("SECRET_KEY", secrets.token_hex(32)),
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=SEGURO_HTTPS,
    PREFERRED_URL_SCHEME="https" if SEGURO_HTTPS else "http",
)

if not ADMIN_TOKEN:
    ADMIN_TOKEN = secrets.token_urlsafe(24)


# ------------------------------- Base de datos -------------------------------
def get_db():
    """Conexion MySQL de la peticion actual (se cierra al terminar)."""
    conexion = getattr(g, "_database", None)
    if conexion is None:
        conexion = g._database = bd.conectar_bd()
    return conexion


@app.teardown_appcontext
def cerrar_db(_exception):
    db = getattr(g, "_database", None)
    if db is not None:
        db.close()


# ------------------------------ SEO y enlaces --------------------------------
def url_absoluta(ruta):
    """Convierte una ruta interna en URL absoluta (og:image, canonical, sitemap)."""
    return (SITIO_URL or request.url_root.rstrip("/")) + ruta


def ruta_libro(libro):
    """Ruta canonica y estable de la ficha de un libro."""
    return "/libro/{}-{}".format(libro["id"], slugify(libro["titulo"]))


def precio_soles(valor):
    return "S/ {:.2f}".format(float(valor or 0))


def mensaje_libro(libro):
    """Mismo texto que arma el JavaScript: titulo en negrita y precio."""
    return (
        "Hola {nombre} \U0001F44B\n\n"
        "Me interesa este libro:\n\n"
        "\U0001F4D5 *{titulo}*\n"
        "\U0001F4B0 Precio: {precio}\n\n"
        "\u00BFEsta disponible? \u00A1Gracias!"
    ).format(
        nombre=NOMBRE_LIBRERIA,
        titulo=libro["titulo"],
        precio=precio_soles(libro["precio"]),
    )


def enlace_whatsapp(mensaje):
    return "https://wa.me/{}?text={}".format(WHATSAPP_NUMERO, quote(mensaje))


def imagen_social(libro=None):
    """
    Imagen para las vistas previas al compartir el enlace. WhatsApp y Facebook
    no muestran SVG, asi que si la portada no es una imagen de mapa de bits se
    usa la tarjeta generica de la libreria.
    """
    if libro:
        ruta = libro.get("imagen") or ""
        if ruta.lower().endswith((".jpg", ".jpeg", ".png", ".webp")):
            return url_absoluta(ruta)
    return url_absoluta(url_for("static", filename="img/og-default.png"))


def json_ld(datos):
    """JSON-LD serializado sin permitir cerrar la etiqueta <script>."""
    return json.dumps(datos, ensure_ascii=False).replace("<", "\\u003c")


def texto_corto(texto, limite=160):
    """Resume un texto para usarlo como meta descripcion."""
    limpio = " ".join((texto or "").split())
    if len(limpio) <= limite:
        return limpio
    return limpio[:limite - 3].rstrip() + "..."


def contexto_sitio():
    """Datos de la libreria que necesitan todas las plantillas."""
    return {
        "nombre_libreria": NOMBRE_LIBRERIA,
        "slogan": SLOGAN,
        "whatsapp": WHATSAPP_NUMERO,
        "whatsapp_display": WHATSAPP_DISPLAY,
        "direccion": DIRECCION,
        "referencia": REFERENCIA,
        "mapa_url": MAPA_URL,
        "correo": CORREO,
        "horario": HORARIO,
        "redes": REDES,
    }


@app.context_processor
def inyectar_datos_comunes():
    mensaje = (
        "Hola {} \U0001F44B, quisiera mas informacion sobre su catalogo de libros."
    ).format(NOMBRE_LIBRERIA)
    return {
        "wa_general": enlace_whatsapp(mensaje),
        "anio_actual": datetime.now().year,
    }


def obtener_libro(libro_id):
    return get_db().execute(
        """
        SELECT l.*, c.nombre AS categoria, c.slug AS categoria_slug,
               c.color AS categoria_color
        FROM libros l
        JOIN categorias c ON c.id = l.categoria_id
        WHERE l.id = %s
        """,
        (libro_id,),
    ).fetchone()


# --------------------------------- Seguridad ---------------------------------
@app.after_request
def cabeceras_de_seguridad(respuesta):
    return seguridad.aplicar_cabeceras(respuesta, es_https=SEGURO_HTTPS or request.is_secure)


def _es_api():
    return request.path.startswith("/api/")


def _error(codigo, mensaje):
    """Errores en JSON para la API y pagina amigable para el resto."""
    if _es_api():
        return jsonify({"error": mensaje}), codigo
    return (
        render_template(
            "error.html",
            codigo=codigo,
            mensaje=mensaje,
            nombre_libreria=NOMBRE_LIBRERIA,
            slogan=SLOGAN,
            whatsapp=WHATSAPP_NUMERO,
        ),
        codigo,
    )


@app.errorhandler(400)
def error_400(_e):
    return _error(400, "Solicitud invalida.")


@app.errorhandler(403)
def error_403(_e):
    return _error(403, "Acceso denegado.")


@app.errorhandler(404)
def error_404(_e):
    return _error(404, "La pagina o el recurso que buscas no existe.")


@app.errorhandler(405)
def error_405(_e):
    return _error(405, "Metodo no permitido.")


@app.errorhandler(413)
def error_413(_e):
    return _error(413, "El contenido enviado es demasiado grande.")


@app.errorhandler(429)
def error_429(_e):
    return _error(429, "Demasiadas solicitudes. Intenta de nuevo en un momento.")


@app.errorhandler(500)
def error_500(_e):
    # Nunca se expone el detalle del error al usuario.
    return _error(500, "Ocurrio un error interno. Intenta de nuevo mas tarde.")


@app.errorhandler(pymysql.MySQLError)
def error_mysql(_e):
    # Nunca se muestra el detalle tecnico de la base de datos al usuario.
    return _error(503, "La base de datos no esta disponible en este momento.")


# ---------------------------------- Vistas -----------------------------------
@app.route("/")
def index():
    total = get_db().execute(
        "SELECT COUNT(*) AS total FROM libros"
    ).fetchone()["total"]

    canonical = url_absoluta("/")
    descripcion = (
        "Catalogo de libros de {}: literatura, ciencia ficcion, infantil, "
        "historia y mas. Consulta precios y disponibilidad por WhatsApp."
    ).format(NOMBRE_LIBRERIA)

    datos_ld = {
        "@context": "https://schema.org",
        "@type": "BookStore",
        "name": NOMBRE_LIBRERIA,
        "description": SLOGAN,
        "url": canonical,
        "image": imagen_social(),
        "telephone": "+" + WHATSAPP_NUMERO,
        "email": CORREO,
        "priceRange": "S/",
        "address": {
            "@type": "PostalAddress",
            "streetAddress": DIRECCION,
            "addressLocality": "Lima",
            "addressCountry": "PE",
        },
        "openingHours": HORARIO,
        "sameAs": [r["url"] for r in REDES if r["icono"] != "whatsapp"],
    }

    datos = contexto_sitio()
    datos.update({
        "total_libros": total,
        "canonical": canonical,
        "titulo_seo": "{} | Catalogo de Libros".format(NOMBRE_LIBRERIA),
        "og_descripcion": descripcion,
        "og_imagen": imagen_social(),
        "json_ld": json_ld(datos_ld),
    })
    return render_template("index.html", **datos)


# ------------------------- Ficha publica de cada libro -----------------------
@app.route("/libro/<int:libro_id>")
@seguridad.limitar(180, 60)
def libro_sin_slug(libro_id):
    """Enlace corto: /libro/7 -> /libro/7-titulo-del-libro (301 permanente)."""
    fila = obtener_libro(libro_id)
    if fila is None:
        abort(404)
    return redirect(ruta_libro(dict(fila)), code=301)


@app.route("/libro/<int:libro_id>-<slug>")
@seguridad.limitar(180, 60)
def libro(libro_id, slug):
    fila = obtener_libro(libro_id)
    if fila is None:
        abort(404)

    libro_datos = dict(fila)
    libro_datos["url"] = ruta_libro(libro_datos)
    libro_datos["precio_fmt"] = precio_soles(libro_datos["precio"])

    # Si el titulo cambio, el slug antiguo sigue funcionando: se redirige al
    # canonico para no partir el posicionamiento en buscadores.
    if "/libro/{}-{}".format(libro_id, slug) != libro_datos["url"]:
        return redirect(libro_datos["url"], code=301)

    filas_relacionados = get_db().execute(
        """
        SELECT l.id, l.titulo, l.autor, l.imagen, l.precio
        FROM libros l
        WHERE l.categoria_id = %s AND l.id <> %s
        ORDER BY l.destacado DESC, l.titulo ASC
        LIMIT 4
        """,
        (libro_datos["categoria_id"], libro_id),
    ).fetchall()

    relacionados = []
    for fila_rel in filas_relacionados:
        dato = dict(fila_rel)
        dato["url"] = ruta_libro(dato)
        dato["precio_fmt"] = precio_soles(dato["precio"])
        relacionados.append(dato)

    descripcion = texto_corto(libro_datos.get("descripcion"))
    if not descripcion:
        descripcion = "{} de {}. Disponible en {}.".format(
            libro_datos["titulo"], libro_datos["autor"], NOMBRE_LIBRERIA
        )

    canonical = url_absoluta(libro_datos["url"])

    datos_ld = {
        "@context": "https://schema.org",
        "@type": "Book",
        "name": libro_datos["titulo"],
        "author": {"@type": "Person", "name": libro_datos["autor"]},
        "inLanguage": "es",
        "url": canonical,
        "image": imagen_social(libro_datos),
        "description": descripcion,
        "offers": {
            "@type": "Offer",
            "price": "{:.2f}".format(float(libro_datos["precio"])),
            "priceCurrency": "PEN",
            "availability": "https://schema.org/InStock",
            "url": canonical,
            "seller": {"@type": "BookStore", "name": NOMBRE_LIBRERIA},
        },
    }
    if libro_datos.get("editorial"):
        datos_ld["publisher"] = {
            "@type": "Organization",
            "name": libro_datos["editorial"],
        }
    if libro_datos.get("isbn"):
        datos_ld["isbn"] = libro_datos["isbn"]
    if libro_datos.get("anio"):
        datos_ld["datePublished"] = str(libro_datos["anio"])

    datos = contexto_sitio()
    datos.update({
        "libro": libro_datos,
        "relacionados": relacionados,
        "canonical": canonical,
        "titulo_seo": "{} - {} | {}".format(
            libro_datos["titulo"], libro_datos["autor"], NOMBRE_LIBRERIA
        ),
        "og_descripcion": descripcion,
        "og_imagen": imagen_social(libro_datos),
        "json_ld": json_ld(datos_ld),
        "wa_libro": enlace_whatsapp(mensaje_libro(libro_datos)),
    })
    return render_template("libro.html", **datos)


# ------------------------------ Buscadores -----------------------------------
@app.route("/robots.txt")
def robots():
    lineas = [
        "User-agent: *",
        "Allow: /",
        "Disallow: /api/",
        "",
        "Sitemap: " + url_absoluta("/sitemap.xml"),
        "",
    ]
    return app.response_class("\n".join(lineas), mimetype="text/plain")


@app.route("/sitemap.xml")
def sitemap():
    filas = get_db().execute(
        "SELECT id, titulo, creado_en FROM libros ORDER BY id"
    ).fetchall()

    hoy = datetime.now().strftime("%Y-%m-%d")
    lineas = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
        "  <url>",
        "    <loc>{}</loc>".format(url_absoluta("/")),
        "    <lastmod>{}</lastmod>".format(hoy),
        "    <changefreq>daily</changefreq>",
        "    <priority>1.0</priority>",
        "  </url>",
    ]

    for fila in filas:
        dato = dict(fila)
        fecha = dato["creado_en"]
        lineas += [
            "  <url>",
            "    <loc>{}</loc>".format(url_absoluta(ruta_libro(dato))),
            "    <lastmod>{}</lastmod>".format(
                fecha.strftime("%Y-%m-%d") if fecha else hoy
            ),
            "    <changefreq>monthly</changefreq>",
            "    <priority>0.8</priority>",
            "  </url>",
        ]

    lineas.append("</urlset>")
    respuesta = app.response_class("\n".join(lineas), mimetype="application/xml")
    respuesta.headers["Cache-Control"] = "public, max-age=3600"
    return respuesta


# ---------------------------------- API --------------------------------------
@app.route("/api/categorias")
@seguridad.limitar(90, 60)
def api_categorias():
    filas = get_db().execute(
        """
        SELECT c.id, c.nombre, c.slug, c.descripcion, c.color,
               COUNT(l.id) AS total
        FROM categorias c
        LEFT JOIN libros l ON l.categoria_id = c.id
        GROUP BY c.id, c.nombre, c.slug, c.descripcion, c.color
        ORDER BY c.id
        """
    ).fetchall()
    return jsonify([dict(f) for f in filas])


@app.route("/api/libros")
@seguridad.limitar(120, 60)
def api_libros():
    # --- Validacion y saneado de parametros ---
    q = seguridad.texto(request.args.get("q"), seguridad.MAX_TEXTO_BUSQUEDA)
    categoria = seguridad.texto(request.args.get("categoria"), seguridad.MAX_CATEGORIA)
    orden = seguridad.texto(request.args.get("orden"), 20) or "recientes"
    solo_destacados = request.args.get("destacados") in ("1", "true", "si")

    sql = """
        SELECT l.id, l.titulo, l.autor, l.editorial, l.anio, l.isbn,
               l.precio, l.destacado, l.descripcion, l.imagen,
               c.nombre AS categoria, c.slug AS categoria_slug, c.color AS categoria_color
        FROM libros l
        JOIN categorias c ON c.id = l.categoria_id
        WHERE 1 = 1
    """
    params = []

    if q:
        sql += " AND (l.titulo LIKE %s OR l.autor LIKE %s OR l.editorial LIKE %s OR c.nombre LIKE %s)"
        like = "%{}%".format(q)
        params += [like, like, like, like]

    if categoria and categoria != "todas":
        sql += " AND c.slug = %s"
        params.append(categoria)

    if solo_destacados:
        sql += " AND l.destacado = 1"

    # El ORDER BY se elige de una lista blanca: nunca se concatena entrada del usuario.
    # La colacion utf8mb4_unicode_ci ya ignora mayusculas y tildes.
    ordenes = {
        "recientes": "l.id DESC",
        "precio_asc": "l.precio ASC",
        "precio_desc": "l.precio DESC",
        "titulo": "l.titulo ASC",
        "autor": "l.autor ASC",
    }
    sql += " ORDER BY " + ordenes.get(orden, ordenes["recientes"])

    filas = get_db().execute(sql, params).fetchall()
    libros = []
    for fila in filas:
        dato = dict(fila)
        dato["url"] = ruta_libro(dato)
        libros.append(dato)
    return jsonify({"total": len(libros), "libros": libros})


@app.route("/api/libros/<int:libro_id>")
@seguridad.limitar(120, 60)
def api_libro(libro_id):
    fila = get_db().execute(
        """
        SELECT l.*, c.nombre AS categoria, c.slug AS categoria_slug, c.color AS categoria_color
        FROM libros l
        JOIN categorias c ON c.id = l.categoria_id
        WHERE l.id = %s
        """,
        (libro_id,),
    ).fetchone()
    if fila is None:
        return jsonify({"error": "Libro no encontrado"}), 404
    dato = dict(fila)
    dato["url"] = ruta_libro(dato)
    return jsonify(dato)


@app.route("/api/consultas", methods=["POST"])
@seguridad.limitar(10, 60)
def api_registrar_consulta():
    datos = request.get_json(silent=True)
    if not isinstance(datos, dict):
        return jsonify({"error": "Formato de datos invalido."}), 400

    libro_id = seguridad.entero(datos.get("libro_id"), minimo=1)
    if libro_id is None:
        return jsonify({"error": "El libro indicado no es valido."}), 400

    db = get_db()
    existe = db.execute("SELECT 1 AS encontrado FROM libros WHERE id = %s", (libro_id,)).fetchone()
    if existe is None:
        return jsonify({"error": "El libro indicado no existe."}), 404

    cliente = seguridad.texto(datos.get("cliente"), seguridad.MAX_CLIENTE)
    mensaje = seguridad.texto(datos.get("mensaje"), seguridad.MAX_MENSAJE)

    db.execute(
        "INSERT INTO consultas (libro_id, cliente, mensaje) VALUES (%s,%s,%s)",
        (libro_id, cliente, mensaje),
    )
    db.commit()
    return jsonify({"ok": True}), 201


@app.route("/api/consultas")
@seguridad.limitar(30, 60)
def api_listar_consultas():
    """
    Ultimas consultas registradas. Requiere el token de administrador
    (cabecera X-Admin-Token o parametro ?token=). Se muestra por consola al arrancar.
    """
    recibido = request.headers.get("X-Admin-Token") or request.args.get("token")
    if not seguridad.token_valido(recibido, ADMIN_TOKEN):
        return jsonify({"error": "No autorizado."}), 401

    filas = get_db().execute(
        """
        SELECT co.id, co.cliente, co.mensaje, co.fecha, l.titulo
        FROM consultas co
        LEFT JOIN libros l ON l.id = co.libro_id
        ORDER BY co.id DESC
        LIMIT 200
        """
    ).fetchall()
    return jsonify([dict(f) for f in filas])


if __name__ == "__main__":
    host = _env("HOST", "127.0.0.1")
    puerto = seguridad.entero(_env("PORT", "5000"), minimo=1, maximo=65535) or 5000
    depurar = os.environ.get("FLASK_DEBUG") in ("1", "true", "si", "yes")

    print("=" * 64)
    print("  {}  -  http://{}:{}".format(NOMBRE_LIBRERIA, host, puerto))
    print("  Token de administrador: {}".format(ADMIN_TOKEN))
    print("  (revisa las consultas en /api/consultas?token=...)")
    print("  Modo depuracion: {}".format("ACTIVADO" if depurar else "desactivado"))

    # Comprobacion temprana de la base de datos: mejor enterarse aqui que en la
    # primera visita. El servidor arranca igual para poder mostrar un 503 claro.
    try:
        print("  Base de datos: {}".format(bd.describir_destino()))
    except bd.ErrorConfiguracion:
        print("  Base de datos: (sin configurar)")

    try:
        conexion = bd.conectar_bd()
        conexion.close()
        print("  Conexion MySQL: OK")
    except bd.ErrorConfiguracion as error:
        print("  Conexion MySQL: SIN CONFIGURAR")
        print("  -> {}".format(error))
        print("  -> Completa el archivo .env y ejecuta: python crear_tablas.py")
    except pymysql.MySQLError as error:
        print("  Conexion MySQL: ERROR")
        print("  -> {}".format(error))
        print("  -> Revisa el archivo .env y ejecuta: python crear_tablas.py")
    print("=" * 64)
    app.run(host=host, port=puerto, debug=depurar)
