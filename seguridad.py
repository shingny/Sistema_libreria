# -*- coding: utf-8 -*-
"""
seguridad.py
------------
Medidas de seguridad para la aplicacion Flask de la "Libreria El Saber".

Incluye:
  * Cabeceras HTTP de seguridad (CSP, anti-clickjacking, MIME sniffing, etc.).
  * Limitador de peticiones (rate limiting) por direccion IP.
  * Funciones de saneado y validacion de entradas.

No requiere dependencias externas.
"""

import time
from collections import defaultdict, deque
from functools import wraps

from flask import jsonify, request

# ---------------------------------------------------------------------------
# Limites de validacion de entradas
# ---------------------------------------------------------------------------
MAX_TEXTO_BUSQUEDA = 80      # longitud maxima del parametro ?q=
MAX_CATEGORIA = 40           # longitud maxima del parametro ?categoria=
MAX_CLIENTE = 80             # longitud maxima del campo "cliente"
MAX_MENSAJE = 600            # longitud maxima del campo "mensaje"

# ---------------------------------------------------------------------------
# Politica de seguridad de contenido (CSP)
#   - Todo el contenido es propio ('self'): no se cargan recursos externos.
#   - img-src incluye data: por el favicon embebido como SVG.
#   - style-src usa 'unsafe-inline' porque el catalogo aplica estilos en linea
#     (por ejemplo el color de cada categoria). Los scripts NO lo permiten.
# ---------------------------------------------------------------------------
POLITICA_CSP = "; ".join([
    "default-src 'self'",
    "base-uri 'self'",
    "object-src 'none'",
    "img-src 'self' data:",
    "style-src 'self' 'unsafe-inline'",
    "script-src 'self'",
    "font-src 'self'",
    "connect-src 'self'",
    "form-action 'self'",
    "frame-ancestors 'none'",
])

# Cabeceras que se envian en TODAS las respuestas.
CABECERAS_FIJAS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Permissions-Policy": "geolocation=(), microphone=(), camera=(), payment=(), usb=()",
    "Cross-Origin-Opener-Policy": "same-origin",
    "Cross-Origin-Resource-Policy": "same-origin",
    "X-Permitted-Cross-Domain-Policies": "none",
}
# Nota: la cabecera "Server" la controla el servidor HTTP, no la aplicacion.
# La firma de Werkzeug se oculta en app.py (funcion ocultar_firma_servidor).


def aplicar_cabeceras(respuesta, es_https=False):
    """Agrega las cabeceras de seguridad a una respuesta de Flask."""
    politica = POLITICA_CSP

    # Solo se fuerza HTTPS cuando el sitio realmente se sirve por HTTPS;
    # en local (http://127.0.0.1) romperia la carga del CSS y del JS.
    if es_https:
        politica += "; upgrade-insecure-requests"

    respuesta.headers["Content-Security-Policy"] = politica

    for nombre, valor in CABECERAS_FIJAS.items():
        respuesta.headers[nombre] = valor

    # HSTS solo tiene sentido si el sitio se sirve por HTTPS.
    if es_https:
        respuesta.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

    # Las respuestas de la API no deben guardarse en cache.
    if request.path.startswith("/api/"):
        respuesta.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        respuesta.headers["Pragma"] = "no-cache"

    return respuesta


# ---------------------------------------------------------------------------
# Limitador de peticiones (rate limiting) en memoria
# ---------------------------------------------------------------------------
class Limitador:
    """Ventana deslizante simple: como maximo N peticiones por M segundos."""

    def __init__(self, maximo, ventana_segundos):
        self.maximo = maximo
        self.ventana = ventana_segundos
        self._registro = defaultdict(deque)

    def permitido(self, clave):
        ahora = time.time()
        cola = self._registro[clave]

        # Descartamos las marcas de tiempo antiguas.
        while cola and ahora - cola[0] > self.ventana:
            cola.popleft()

        if len(cola) >= self.maximo:
            return False

        cola.append(ahora)

        # Evita que el diccionario crezca sin control.
        if len(self._registro) > 5000:
            self._limpiar(ahora)

        return True

    def _limpiar(self, ahora):
        for clave in list(self._registro.keys()):
            cola = self._registro[clave]
            if not cola or ahora - cola[-1] > self.ventana:
                del self._registro[clave]


def _cliente_ip():
    """
    Devuelve la IP del cliente.

    Se usa `remote_addr` (no se confia en X-Forwarded-For) para que nadie pueda
    falsear su identidad saltandose el limite. Si algun dia se publica detras de
    un proxy inverso de confianza, habria que usar ProxyFix de Werkzeug.
    """
    return request.remote_addr or "desconocido"


def limitar(maximo, ventana_segundos, mensaje=None):
    """
    Decorador que limita las peticiones por IP.

    Uso:
        @app.route("/api/consultas", methods=["POST"])
        @limitar(10, 60)
        def endpoint(): ...
    """
    mensaje = mensaje or "Demasiadas solicitudes. Espera un momento e intenta de nuevo."
    limitador = Limitador(maximo, ventana_segundos)

    def decorador(funcion):
        @wraps(funcion)
        def envoltura(*args, **kwargs):
            if not limitador.permitido(_cliente_ip()):
                respuesta = jsonify({"error": mensaje})
                respuesta.status_code = 429
                respuesta.headers["Retry-After"] = str(int(ventana_segundos))
                return respuesta
            return funcion(*args, **kwargs)
        return envoltura

    return decorador


# ---------------------------------------------------------------------------
# Saneado de entradas
# ---------------------------------------------------------------------------
def texto(valor, maximo):
    """
    Convierte un valor en texto seguro:
      * Descarta nulos y tipos que no sean cadena.
      * Elimina caracteres de control (excepto salto de linea y tabulador).
      * Recorta a la longitud maxima indicada.
    """
    if not isinstance(valor, str):
        return ""
    limpio = "".join(
        c for c in valor
        if c in ("\n", "\t") or ord(c) >= 32
    )
    return limpio.strip()[:maximo]


def entero(valor, minimo=None, maximo=None):
    """Convierte un valor en entero, devolviendo None si no es valido."""
    try:
        numero = int(valor)
    except (TypeError, ValueError):
        return None
    if minimo is not None and numero < minimo:
        return None
    if maximo is not None and numero > maximo:
        return None
    return numero


def token_valido(recibido, esperado):
    """Comparacion de tokens en tiempo constante (evita ataques de temporizacion)."""
    import hmac
    if not recibido or not esperado:
        return False
    return hmac.compare_digest(str(recibido), str(esperado))
