# -*- coding: utf-8 -*-
"""
init_db.py
----------
Datos de ejemplo de la "Librería El Saber": categorias, libros, paleta de
colores y generacion de portadas SVG.

NOTA: el proyecto ya no usa SQLite. Este archivo se conserva como *fuente* de
los datos de ejemplo y de las portadas; `crear_tablas.py` lo importa para
cargar las 10 categorias y los 29 libros en MySQL.

    - CATEGORIAS : (nombre, slug, descripcion, color, icono)
    - LIBROS     : (titulo, autor, slug_categoria, editorial, anio, isbn,
                    precio, destacado, descripcion)
    - crear_portada(...) : genera una portada .svg en static/img/<categoria>/

La funcion `crear_base_datos()` al final del archivo solo sirve para recrear la
antigua base SQLite y ya no se utiliza desde la web.

Las imagenes se guardan como rutas URL relativas (ej: /static/img/literatura/xxx.svg)
para poder reemplazarlas luego por fotos reales (.jpg / .png) manteniendo el mismo nombre.
"""

import os
import re
import sqlite3
import unicodedata

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "libreria.db")
IMG_DIR = os.path.join(BASE_DIR, "static", "img")

# ---------------------------------------------------------------------------
# Categorias: (nombre, slug, descripcion, color, icono)
# Cada slug corresponde a una subcarpeta dentro de static/img/
# ---------------------------------------------------------------------------
CATEGORIAS = [
    ("Literatura",        "literatura",       "Novelas, cuentos, poesia y clasicos universales", "#6d28d9", "book"),
    ("Ciencia Ficcion",   "ciencia-ficcion",  "Futurismo, espacio, tecnologia y distopias",       "#0e7490", "rocket"),
    ("Infantil",          "infantil",         "Cuentos y lecturas para los mas pequenos",         "#b45309", "teddy"),
    ("Educativos",        "educativos",       "Textos escolares, academicos y de repaso",         "#2563eb", "school"),
    ("Historia",          "historia",         "Historia universal, del Peru y biografias",        "#92400e", "landmark"),
    ("Autoayuda",         "autoayuda",        "Desarrollo personal, motivacion y bienestar",      "#047857", "heart"),
    ("Negocios",          "negocios",         "Emprendimiento, finanzas y liderazgo",             "#4f46e5", "briefcase"),
    ("Cocina",            "cocina",           "Recetarios, reposteria y gastronomia",             "#dc2626", "chef"),
    ("Arte",              "arte",             "Dibujo, pintura, musica y fotografia",             "#db2777", "palette"),
    ("Religion",          "religion",         "Espiritualidad, teologia y fe",                    "#0369a1", "church"),
]

# Colores de la portada generada por categoria: (color_inicio, color_fin)
PALETA = {
    "literatura":      ("#7c3aed", "#4c1d95"),
    "ciencia-ficcion": ("#06b6d4", "#0e7490"),
    "infantil":        ("#fbbf24", "#d97706"),
    "educativos":      ("#3b82f6", "#1d4ed8"),
    "historia":        ("#b45309", "#78350f"),
    "autoayuda":       ("#10b981", "#047857"),
    "negocios":        ("#6366f1", "#4338ca"),
    "cocina":          ("#f87171", "#b91c1c"),
    "arte":            ("#f472b6", "#be185d"),
    "religion":        ("#38bdf8", "#075985"),
}

# ---------------------------------------------------------------------------
# Libros de ejemplo
# (titulo, autor, slug_categoria, editorial, anio, isbn, precio, destacado, descripcion)
# ---------------------------------------------------------------------------
LIBROS = [
    # -- Literatura --
    ("Cien Años de Soledad", "Gabriel Garcia Marquez", "literatura", "Sudamericana", 1967, "978-0307474728", 59.90, 1,
     "La obra cumbre del realismo magico. La historia de la familia Buendia en el mitico pueblo de Macondo."),
    ("La Ciudad y los Perros", "Mario Vargas Llosa", "literatura", "Seix Barral", 1963, "978-8420471839", 54.90, 1,
     "Novela ambientada en el Colegio Militar Leoncio Prado de Lima, una critica a la disciplina militar."),
    ("Los Rios Profundos", "Jose Maria Arguedas", "literatura", "Losada", 1958, "978-9500396141", 39.90, 0,
     "El clasico indigenista peruano que retrata el conflicto entre dos mundos en el internado de Abancay."),
    ("Don Quijote de la Mancha", "Miguel de Cervantes", "literatura", "Espasa", 1605, "978-8467033144", 45.00, 0,
     "La novela mas influyente de la literatura universal. Las aventuras del ingenioso hidalgo y su escudero."),

    # -- Ciencia Ficcion --
    ("1984", "George Orwell", "ciencia-ficcion", "Debolsillo", 1949, "978-8499890944", 49.90, 1,
     "La distopia definitiva sobre la vigilancia total y el control del pensamiento. El Gran Hermano te observa."),
    ("Dune", "Frank Herbert", "ciencia-ficcion", "Debolsillo", 1965, "978-8466361019", 69.90, 0,
     "La epica saga del desierto de Arrakis: politica, religion y ecologia en una de las mejores novelas de ciencia ficcion."),
    ("Fahrenheit 451", "Ray Bradbury", "ciencia-ficcion", "Minotauro", 1953, "978-8445077528", 47.50, 0,
     "Una sociedad donde los bomberos queman libros. Una defensa apasionada de la lectura y la libertad."),
    ("El Problema de los Tres Cuerpos", "Cixin Liu", "ciencia-ficcion", "Nova", 2008, "978-8466663946", 62.00, 1,
     "Primer contacto, fisica avanzada y una civilizacion al borde de la invasion. Ganadora del premio Hugo."),

    # -- Infantil --
    ("El Principito", "Antoine de Saint-Exupery", "infantil", "Salamandra", 1943, "978-8478886296", 35.00, 1,
     "Un piloto perdido en el desierto conoce a un pequeno principe venido de otro planeta. Un clasico para toda edad."),
    ("Charlie y la Fabrica de Chocolate", "Roald Dahl", "infantil", "Alfaguara", 1964, "978-8420446691", 38.50, 0,
     "Charlie Bucket gana un billete dorado y vive una aventura inolvidable en la fabrica de Willy Wonka."),
    ("Cuentos de la Selva", "Horacio Quiroga", "infantil", "Losada", 1918, "978-9500396110", 29.90, 0,
     "Relatos ambientados en la selva misionera con animales que hablan y un profundo amor por la naturaleza."),

    # -- Educativos --
    ("Algebra de Baldor", "Aurelio Baldor", "educativos", "Patria", 1941, "978-9708176358", 65.00, 1,
     "El clasico texto de algebra que ha acompanado a generaciones de estudiantes. Teoria y miles de ejercicios."),
    ("Fisica Conceptual", "Paul Hewitt", "educativos", "Pearson", 1999, "978-6073221904", 89.90, 0,
     "Aprende fisica comprendiendo los conceptos fundamentales, con ejemplos claros de la vida cotidiana."),
    ("Historia del Peru Republicano", "Jorge Basadre", "educativos", "Universitaria", 1968, "978-9972462645", 55.00, 0,
     "Obra fundamental para entender la historia republicana del Peru desde la independencia hasta el siglo XX."),

    # -- Historia --
    ("Sapiens: De Animales a Dioses", "Yuval Noah Harari", "historia", "Debate", 2011, "978-8499926223", 79.90, 1,
     "Un recorrido fascinante por la historia de la humanidad: de cazadores a amos del planeta."),
    ("Tradiciones Peruanas", "Ricardo Palma", "historia", "Aguilar", 1872, "978-9587041310", 42.00, 0,
     "Las mejores tradiciones que rescatan la historia y las costumbres del Peru colonial y republicano."),
    ("La Conquista del Peru", "William H. Prescott", "historia", "Editores del Sur", 1847, "978-9872280134", 48.00, 0,
     "Relato clasico de la caida del Imperio Inca y la llegada de los conquistadores espanoles."),

    # -- Autoayuda --
    ("Habitos Atomicos", "James Clear", "autoayuda", "Paidos", 2018, "978-6077476614", 64.90, 1,
     "Un metodo probado para construir buenos habitos y romper los malos, con cambios pequenos y resultados grandes."),
    ("El Poder del Ahora", "Eckhart Tolle", "autoayuda", "Gaia", 1997, "978-8484451686", 52.00, 0,
     "Una guia hacia la iluminacion espiritual y a vivir plenamente el momento presente."),
    ("Los 7 Habitos de la Gente Altamente Efectiva", "Stephen Covey", "autoayuda", "Paidos", 1989, "978-8449319303", 58.00, 1,
     "El clasico de la efectividad personal basado en principios y valores atemporales."),

    # -- Negocios --
    ("Padre Rico Padre Pobre", "Robert Kiyosaki", "negocios", "Aguilar", 1997, "978-9707704972", 55.90, 1,
     "Lo que los ricos ensenan a sus hijos sobre el dinero y que la clase media y pobre no ensenan."),
    ("El Arte de Empezar", "Guy Kawasaki", "negocios", "Ilustrae", 2004, "978-8493592134", 60.00, 0,
     "Una guia practica con 10 lecciones de emprendimiento de uno de los mayores inversores de Silicon Valley."),
    ("Piense y Hagase Rico", "Napoleon Hill", "negocios", "Obelisco", 1937, "978-8497771368", 45.50, 0,
     "El libro de autoayuda financiera mas vendido de todos los tiempos, basado en 13 principios del exito."),

    # -- Cocina --
    ("Recetas Peruanas de la Abuela", "Gloria Hinostroza", "cocina", "Cocina Peruana", 2010, "978-6124582503", 49.90, 0,
     "Lo mejor de la gastronomia peruana en recetas criollas, caseras y llenas de sabor."),
    ("El Arte de la Cocina Francesa", "Julia Child", "cocina", "Knopf", 1961, "978-0375413400", 95.00, 1,
     "El libro que revoluciono la cocina casera con tecnicas clasicas francesas explicadas paso a paso."),

    # -- Arte --
    ("Dibujo Artistico Paso a Paso", "Jose M. Parramon", "arte", "Parramon", 2005, "978-8434225565", 58.00, 0,
     "Aprende a dominar el dibujo desde el boceto inicial hasta la obra acabada, con ejercicios guiados."),
    ("Historia del Arte", "Ernst H. Gombrich", "arte", "Phaidon", 1950, "978-0714898707", 110.00, 1,
     "La introduccion al arte mas celebre del mundo: una guia clara y amena por toda la historia artistica."),

    # -- Religion --
    ("El Poder de la Oracion", "Varios Autores", "religion", "San Pablo", 2015, "978-8428536394", 39.90, 0,
     "Una guia espiritual para fortalecer la fe y encontrar consuelo y esperanza a traves de la oracion."),
    ("Confesiones", "San Agustin", "religion", "Gredos", 397, "978-8424932692", 44.00, 0,
     "La obra autobiografica mas influyente de la Antiguedad: la busqueda de Dios y del sentido de la vida."),
]


def slugify(texto):
    """Convierte un texto en un slug ASCII: 'Cien Años' -> 'cien-años'."""
    texto = unicodedata.normalize("NFKD", texto)
    texto = texto.encode("ascii", "ignore").decode("ascii")
    texto = texto.lower()
    texto = re.sub(r"[^a-z0-9]+", "-", texto)
    return texto.strip("-") or "libro"


def _escapar_xml(texto):
    return (texto.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def _envolver(texto, ancho):
    """Divide el texto en lineas de como maximo 'ancho' caracteres."""
    palabras, lineas, actual = texto.split(), [], ""
    for p in palabras:
        if not actual:
            actual = p
        elif len(actual) + 1 + len(p) <= ancho:
            actual += " " + p
        else:
            lineas.append(actual)
            actual = p
    if actual:
        lineas.append(actual)
    return lineas


def crear_portada(titulo, autor, categoria_slug, categoria_nombre, ruta_destino):
    """Genera una portada SVG de ejemplo para un libro."""
    c1, c2 = PALETA.get(categoria_slug, ("#4338ca", "#312e81"))
    lineas = _envolver(titulo, 16)[:4]
    y_inicio = 210 - (len(lineas) - 1) * 24

    tspans = []
    for i, linea in enumerate(lineas):
        tspans.append(
            '<tspan x="200" y="{}">{}</tspan>'.format(y_inicio + i * 48, _escapar_xml(linea))
        )
    titulo_svg = "".join(tspans)

    svg = """<svg xmlns="http://www.w3.org/2000/svg" width="400" height="600" viewBox="0 0 400 600">
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="{c1}"/>
      <stop offset="1" stop-color="{c2}"/>
    </linearGradient>
  </defs>
  <rect width="400" height="600" fill="url(#bg)"/>
  <rect x="0" y="0" width="16" height="600" fill="#000000" opacity="0.22"/>
  <rect x="16" y="0" width="4" height="600" fill="#ffffff" opacity="0.15"/>
  <rect x="46" y="46" width="308" height="508" fill="none" stroke="#ffffff" stroke-opacity="0.35" stroke-width="1.5" rx="6"/>
  <text x="200" y="120" text-anchor="middle" font-family="Segoe UI, Arial, sans-serif" font-size="15" letter-spacing="4" fill="#ffffff" fill-opacity="0.75">{categoria}</text>
  <text text-anchor="middle" font-family="Georgia, Times New Roman, serif" font-size="40" font-weight="bold" fill="#ffffff">{titulo}</text>
  <line x1="140" y1="{linea_y}" x2="260" y2="{linea_y}" stroke="#ffffff" stroke-opacity="0.6" stroke-width="2"/>
  <text x="200" y="500" text-anchor="middle" font-family="Segoe UI, Arial, sans-serif" font-size="18" fill="#ffffff" fill-opacity="0.9">{autor}</text>
  <text x="200" y="540" text-anchor="middle" font-family="Segoe UI, Arial, sans-serif" font-size="12" letter-spacing="3" fill="#ffffff" fill-opacity="0.6">LIBRERIA EL SABER</text>
</svg>
""".format(
        c1=c1, c2=c2,
        categoria=_escapar_xml(categoria_nombre.upper()),
        titulo=titulo_svg,
        linea_y=y_inicio + (len(lineas) - 1) * 48 + 34,
        autor=_escapar_xml(autor),
    )

    with open(ruta_destino, "w", encoding="utf-8") as fh:
        fh.write(svg)


def crear_base_datos():
    """Crea las tablas y carga los datos de ejemplo. Devuelve el total de libros."""
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)

    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()

    cur.executescript("""
        CREATE TABLE categorias (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre      TEXT NOT NULL UNIQUE,
            slug        TEXT NOT NULL UNIQUE,
            descripcion TEXT,
            color       TEXT DEFAULT '#4338ca',
            icono       TEXT DEFAULT 'book'
        );

        CREATE TABLE libros (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            titulo         TEXT NOT NULL,
            autor          TEXT NOT NULL,
            categoria_id   INTEGER NOT NULL,
            editorial      TEXT,
            anio           INTEGER,
            isbn           TEXT,
            precio         REAL NOT NULL DEFAULT 0,
            destacado      INTEGER NOT NULL DEFAULT 0,
            descripcion    TEXT,
            imagen         TEXT,
            fecha_creacion TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (categoria_id) REFERENCES categorias (id)
        );

        CREATE TABLE consultas (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            libro_id   INTEGER,
            cliente    TEXT,
            mensaje    TEXT,
            fecha      TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (libro_id) REFERENCES libros (id)
        );
    """)

    # Categorias
    cat_id = {}
    for nombre, slug, descripcion, color, icono in CATEGORIAS:
        cur.execute(
            "INSERT INTO categorias (nombre, slug, descripcion, color, icono) VALUES (?,?,?,?,?)",
            (nombre, slug, descripcion, color, icono),
        )
        cat_id[slug] = cur.lastrowid

    # Carpetas de imagenes por categoria
    for _, slug, _, _, _ in CATEGORIAS:
        os.makedirs(os.path.join(IMG_DIR, slug), exist_ok=True)

    # Libros + portadas
    usados = set()
    for (titulo, autor, slug_cat, editorial, anio, isbn, precio, destacado, descripcion) in LIBROS:
        base = slugify(titulo)
        nombre_archivo = base
        contador = 2
        while nombre_archivo in usados:
            nombre_archivo = "{}-{}".format(base, contador)
            contador += 1
        usados.add(nombre_archivo)

        ruta_fisica = os.path.join(IMG_DIR, slug_cat, nombre_archivo + ".svg")
        cat_nombre = next(c[0] for c in CATEGORIAS if c[1] == slug_cat)
        crear_portada(titulo, autor, slug_cat, cat_nombre, ruta_fisica)

        url_imagen = "/static/img/{}/{}.svg".format(slug_cat, nombre_archivo)
        cur.execute(
            """INSERT INTO libros
               (titulo, autor, categoria_id, editorial, anio, isbn, precio, destacado, descripcion, imagen)
               VALUES (?,?,?,?,?,?,?,?,?,?)""",
            (titulo, autor, cat_id[slug_cat], editorial, anio, isbn, precio, destacado, descripcion, url_imagen),
        )

    con.commit()
    total = cur.execute("SELECT COUNT(*) FROM libros").fetchone()[0]
    con.close()
    return total


if __name__ == "__main__":
    n = crear_base_datos()
    print("[OK] Base de datos creada:", DB_PATH)
    print("[OK] Libros cargados:", n)
    print("[OK] Imagenes en:", IMG_DIR)
