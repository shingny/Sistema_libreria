# Librería El Saber — Catálogo web

Sitio web de catálogo de libros con filtros por categoría, buscador y consultas
por WhatsApp. Construido con **Python (Flask) + MySQL + HTML + CSS + JavaScript**.
La base de datos vive en **MySQL de Alwaysdata**; las credenciales se guardan en
el archivo `.env`.

> Este proyecto está en la carpeta **`web libreria/`** del repositorio.

---

## Características

- **Catálogo visual** de libros con portada, título, autor, categoría y precio.
- **Filtro por categorías** (10 categorías) con contador de libros.
- **Buscador** por título, autor, editorial o categoría (con retardo anti-saturación).
- **Ordenamiento** por recientes, título, autor o precio.
- **Ficha de detalle** (modal) con editorial, año, ISBN y descripción.
- **Call to Action a WhatsApp:** abre WhatsApp con un mensaje de **solo texto**
  que lleva el **título en negrita y el precio**. Ver
  [Enviar el libro por WhatsApp](#enviar-el-libro-por-whatsapp).
- **Botón flotante** de WhatsApp y sección de contacto.
- **Dirección de la librería** con referencia y botón **"Cómo llegar"** (Google Maps).
- **Redes sociales** (Facebook, Instagram, TikTok, YouTube, WhatsApp) en contacto y pie.
- **Registro de consultas** en la base de datos (`/api/consultas`).
- **Diseño adaptable (móvil primero):** menú hamburguesa, categorías deslizables,
  ficha de libro como "hoja inferior" (bottom sheet), botones táctiles de 44 px y
  respeto de las *safe areas* de los teléfonos con notch.
- **Accesible:** navegación por teclado, `aria`, `prefers-reduced-motion` y
  contraste AA. Lighthouse: **100/100** en Accesibilidad, Buenas prácticas y SEO.
- **Seguridad:** cabeceras HTTP, CSP, validación de entradas, límite de peticiones
  por IP y errores sin datos internos. Ver [Seguridad](#seguridad).

**WhatsApp configurado:** `+51 943 846 909` → `https://wa.me/51943846909`

---

## Estructura del proyecto

```
web libreria/
├── app.py                 # Servidor Flask y API (backend)
├── db.py                  # Conexión a MySQL leyendo el archivo .env
├── crear_tablas.py        # Crea las tablas de MySQL (y carga datos con --datos)
├── seguridad.py           # Cabeceras de seguridad, rate limiting y validación
├── init_db.py             # Datos de ejemplo, categorías y portadas SVG
├── .env                   # Credenciales de MySQL (privado, NO se sube)
├── .env.example           # Plantilla de .env para compartir
├── requirements.txt       # Dependencias (Flask, PyMySQL, python-dotenv)
├── iniciar.bat            # Arranque rápido en Windows
├── venv/                  # Entorno virtual de Python
├── templates/
│   ├── index.html         # Página principal (catálogo)
│   ├── libro.html         # Ficha pública de cada libro (/libro/...)
│   ├── error.html         # Página de error (404, 500, ...)
│   ├── _header.html       # Cabecera compartida
│   ├── _footer.html       # Pie compartido
│   └── _sprite.html       # Iconos SVG compartidos
└── static/
    ├── css/styles.css     # Estilos (UX/UI)
    ├── js/main.js         # Lógica del catálogo y WhatsApp
    └── img/               # Carpeta de fotos (base de datos de imágenes)
        ├── og-default.png # Imagen de vista previa al compartir
        ├── literatura/
        ├── ciencia-ficcion/
        ├── infantil/
        ├── educativos/
        ├── historia/
        ├── autoayuda/
        ├── negocios/
        ├── cocina/
        ├── arte/
        └── religion/
```

---

## Base de datos (MySQL en Alwaysdata)

### 1. Crear la base de datos en el panel de Alwaysdata

1. Entra en <https://admin.alwaysdata.com> y abre **Bases de datos → MySQL**.
2. Crea una base de datos. Alwaysdata te dará estos datos:

   | Dato en el panel | Variable en `.env` | Ejemplo |
   | ---------------- | ------------------ | ------- |
   | Servidor / Host | `DB_HOST` | `mysql-TUCUENTA.alwaysdata.net` |
   | Puerto | `DB_PORT` | `3306` |
   | Base de datos | `DB_NAME` | `TUCUENTA_libreria` |
   | Usuario | `DB_USER` | `TUCUENTA_libreria` |
   | Contraseña | `DB_PASSWORD` | (la que elegiste) |

3. En **Acceso remoto** (Remote access) de esa base de datos, añade la IP desde
   la que te conectas. Sin esto, MySQL rechaza la conexión desde tu PC.

> Copia los valores **exactamente** como los muestra el panel: el formato del
> host cambia según el servidor que te toque.

### 2. Rellenar el archivo `.env`

Abre `.env` y cambia los valores de ejemplo:

```ini
DB_HOST=mysql-TUCUENTA.alwaysdata.net
DB_PORT=3306
DB_NAME=TUCUENTA_libreria
DB_USER=TUCUENTA_libreria
DB_PASSWORD=tu_contrasena_real
DB_CHARSET=utf8mb4
```

`.env` está en `.gitignore`: nunca se sube al repositorio. `.env.example` es la
plantilla que sí puedes compartir.

### 3. Crear las tablas con Python

```powershell
venv\Scripts\python.exe crear_tablas.py --datos
```

El script crea las tablas **en orden** (por las claves foráneas) e informa de
cada paso:

1. `categorias` — 10 categorías.
2. `libros` — depende de `categorias` (FK `categoria_id`).
3. `consultas` — depende de `libros` (FK `libro_id`).

Opciones:

| Comando | Qué hace |
| ------- | -------- |
| `python crear_tablas.py` | Crea las tablas que falten. No toca los datos. |
| `python crear_tablas.py --datos` | Crea las tablas y carga 10 categorías + 29 libros con portadas. |
| `python crear_tablas.py --recrear` | **Borra** las tablas y las vuelve a crear. Pide escribir `SI`. |

El script se puede ejecutar varias veces sin problema (`CREATE TABLE IF NOT
EXISTS`); si ya hay categorías cargadas, `--datos` no duplica nada.

---

## Instalación y ejecución

### Windows (rápido)
Doble clic en **`iniciar.bat`**.

### Manual
```powershell
cd "web libreria"

# 1) Crear el entorno virtual
python -m venv venv

# 2) Activar el entorno virtual
venv\Scripts\activate          # Windows

# 3) Instalar dependencias
pip install -r requirements.txt

# 4) Configurar .env y crear las tablas en MySQL
python crear_tablas.py --datos

# 5) Levantar el servidor
python app.py
```

Luego abre: <http://127.0.0.1:5000>

> Si MySQL no responde, el servidor arranca igual y muestra un mensaje claro en
> la consola; la web responde `503` con una página amigable en lugar de exponer
> el error técnico.

---

## API

| Método | Ruta | Descripción |
| ------ | ---- | ----------- |
| GET | `/` | Página del catálogo |
| GET | `/libro/<id>-<slug>` | Ficha pública del libro (HTML con SEO) |
| GET | `/libro/<id>` | Redirige (301) a la ficha con su título |
| GET | `/api/categorias` | Categorías con total de libros |
| GET | `/api/libros` | Libros. Filtros: `?q=`, `?categoria=`, `?orden=`, `?destacados=1` |
| GET | `/api/libros/<id>` | Detalle de un libro (incluye `url`) |
| POST | `/api/consultas` | Registra una consulta `{ "libro_id": 1, "mensaje": "..." }` |
| GET | `/api/consultas` | Últimas 200 consultas (requiere token de administrador) |
| GET | `/sitemap.xml` | Mapa del sitio para buscadores (generado desde MySQL) |
| GET | `/robots.txt` | Reglas de rastreo + referencia al sitemap |

---

## SEO y cómo se ve al compartir

Cada libro tiene su **URL propia y estable**:

```
https://TU-SITIO/libro/5-1984
```

Esa página llega **renderizada desde el servidor** (no depende de JavaScript),
con título, descripción, precio y portada. Incluye:

- `<title>` y `meta description` propios
- `link rel="canonical"`
- **Open Graph** (`og:title`, `og:description`, `og:image`) y Twitter Card
- **JSON-LD** `Book` + `Offer` (precio en `PEN`) y `BookStore` en la portada
- Enlaces a otros libros de la misma categoría

### La imagen que aparece al pegar el enlace

`static/img/og-default.png` (1200×630) es la tarjeta que muestra WhatsApp al
compartir la web. **WhatsApp y Facebook no muestran SVG**, así que las portadas
generadas (`.svg`) no sirven como vista previa: si reemplazas una portada por
una foto real (`.jpg`/`.png`/`.webp`), esa portada se usa automáticamente en la
vista previa de su ficha.

### `SITIO_URL`

Para que `og:image` y `canonical` sean absolutos hay que indicar la URL pública:

```ini
SITIO_URL=https://sistema42.alwaysdata.net
```

En local se detecta sola (`http://localhost:5000`), pero una vista previa con
`localhost` no funciona fuera de tu PC.

---

## Enviar el libro por WhatsApp

Cuando un cliente pulsa **"Enviar libro por WhatsApp"**, la web hace esto:

1. **Registra la consulta** en la base de datos (queda en el historial).
2. **Abre WhatsApp** con un mensaje corto y directo:

```
Hola Libreria El Saber 👋

Me interesa este libro:

📕 *Confesiones*
💰 Precio: S/ 44.00

¿Esta disponible? ¡Gracias!
```

> El título va entre `*asteriscos*`: WhatsApp lo muestra **en negrita**.

### Solo texto (sin adjuntos)

El mensaje es **únicamente texto**. Los enlaces `wa.me/...?text=` de WhatsApp no
permiten adjuntar imágenes ni archivos desde una web, así que no se envía la
portada: el cliente recibe el **título en negrita y el precio**, y nada más.

---

## Cómo agregar o cambiar libros y fotos

1. Copia la foto del libro en la carpeta de su categoría, por ejemplo:
   `static/img/literatura/mi-libro.jpg`
2. Registra el libro en la base de datos indicando la URL de la imagen
   (`/static/img/literatura/mi-libro.jpg`).

Puedes hacerlo desde MySQL (por ejemplo con phpMyAdmin o la consola de
Alwaysdata):

```sql
INSERT INTO libros (titulo, autor, categoria_id, editorial, anio, isbn, precio, destacado, descripcion, imagen)
VALUES ('Mi libro', 'Mi autor', 1, 'Mi editorial', 2024, '978-...', 49.90, 1,
        'Descripción del libro', '/static/img/literatura/mi-libro.jpg');
```

> Las imágenes de ejemplo son `.svg` generados automáticamente. Puedes
> reemplazarlas por fotos reales (`.jpg` / `.png`) manteniendo o cambiando la
> columna `imagen`.

---

## Personalización rápida

En `app.py` puedes cambiar los datos de la librería:

```python
NOMBRE_LIBRERIA  = "Libreria El Saber"
WHATSAPP_NUMERO  = "51943846909"
WHATSAPP_DISPLAY = "+51 943 846 909"

# Ubicacion
DIRECCION  = "Av. Los Libros 123, Cercado de Lima, Lima - Peru"
REFERENCIA = "A una cuadra de la Plaza Mayor"
# El enlace a Google Maps se genera solo a partir de la direccion (MAPA_URL).

CORREO  = "ventas@libreriaelsaber.pe"
HORARIO = "Lun a Sab: 9:00 am - 8:00 pm"

# Redes sociales (reemplaza los enlaces de ejemplo por los reales)
REDES = [
    {"nombre": "Facebook",  "icono": "facebook",  "url": "https://facebook.com/TU_USUARIO"},
    {"nombre": "Instagram", "icono": "instagram", "url": "https://instagram.com/TU_USUARIO"},
    {"nombre": "TikTok",    "icono": "tiktok",    "url": "https://tiktok.com/@TU_USUARIO"},
    {"nombre": "YouTube",   "icono": "youtube",   "url": "https://youtube.com/@TU_CANAL"},
    {"nombre": "WhatsApp",  "icono": "whatsapp",  "url": "https://wa.me/51943846909"},
]
```

> **Iconos disponibles:** `facebook`, `instagram`, `tiktok`, `youtube`, `whatsapp`
> (y `pin` para ubicación). Para agregar otra red social, añade su `<symbol>`
> en el sprite SVG de `templates/index.html` y su color en `static/css/styles.css`.

En `init_db.py` puedes cambiar las **categorías** (`CATEGORIAS`) y los
**libros** (`LIBROS`). Después ejecuta, para volver a crear las tablas en MySQL
y regenerar las portadas:

```powershell
venv\Scripts\python.exe crear_tablas.py --recrear --datos
```

---

## Seguridad

Toda la parte de seguridad vive en `seguridad.py` y se aplica automáticamente:

| Medida | Qué hace |
| ------ | -------- |
| **CSP** (`Content-Security-Policy`) | Solo permite recursos propios (`'self'`). No hay scripts en línea ni recursos externos. |
| **Anti-clickjacking** | `X-Frame-Options: DENY` + `frame-ancestors 'none'`: nadie puede incrustar la web. |
| **`X-Content-Type-Options: nosniff`** | Evita que el navegador "adivine" tipos de archivo. |
| **`Referrer-Policy`** | No se filtra la URL completa a sitios externos. |
| **`Permissions-Policy`** | Bloquea cámara, micrófono, ubicación, pagos y USB. |
| **Firma del servidor oculta** | No se revela que se usa Werkzeug ni la versión de Python. |
| **Consultas SQL parametrizadas** | Todas las consultas usan `%s` (MySQL); el `ORDER BY` sale de una lista blanca. |
| **Validación de entradas** | Se limitan y limpian `q`, `categoria`, `libro_id`, `cliente` y `mensaje`. |
| **Límite de tamaño** | Máximo 32 KB por petición (`MAX_CONTENT_LENGTH`). |
| **Rate limiting** | Por IP: 10 consultas/min, 90–120 lecturas/min. Al pasarse responde `429`. |
| **Endpoint de consultas protegido** | `/api/consultas` (GET) exige un token de administrador. |
| **Errores sin detalles** | En producción nunca se muestra la traza del error al usuario. |

### Cómo ver las consultas recibidas

Al arrancar, la consola imprime un **token de administrador**:

```
Token de administrador: 1PL4QcieVZG_XmW9_extanXMYQb-nyhH
```

Ábrelo así:

```
http://127.0.0.1:5000/api/consultas?token=TU_TOKEN
```

> El token cambia en cada arranque. Si quieres uno fijo, define la variable de
> entorno `ADMIN_TOKEN` antes de iniciar el servidor.

### Al publicar en internet

1. **HTTPS obligatorio.** Con HTTPS activo, arranca con `HTTPS=1` para que se
   envíen `Strict-Transport-Security` y `upgrade-insecure-requests`.
2. **No uses el servidor de desarrollo.** Emplea un servidor de producción
   (`waitress` en Windows o `gunicorn` en Linux) y un proxy con HTTPS.
3. **Cambia `SECRET_KEY`** con una cadena larga y aleatoria.
4. **Mantén `FLASK_DEBUG` apagado** (por defecto ya lo está).
5. **Haz copias de seguridad** de la base de datos MySQL (`mysqldump`) y de
   `static/img/`.

---

## Variables de entorno

### MySQL (obligatorias, en `.env`)

| Variable | Ejemplo | Para qué sirve |
| -------- | ------- | -------------- |
| `DB_HOST` | `mysql-TUCUENTA.alwaysdata.net` | Servidor MySQL |
| `DB_PORT` | `3306` | Puerto |
| `DB_NAME` | `TUCUENTA_libreria` | Nombre de la base |
| `DB_USER` | `TUCUENTA_libreria` | Usuario |
| `DB_PASSWORD` | `••••••••` | Contraseña |
| `DB_CHARSET` | `utf8mb4` | Codificación (respeta tildes y emojis) |

> Si defines estas variables en el sistema (por ejemplo en el servidor de
> producción), tienen prioridad sobre el archivo `.env`.

### Opcionales

Todas tienen un valor por defecto y se pueden sobrescribir sin tocar el código:

| Variable | Por defecto | Para qué sirve |
| -------- | ----------- | -------------- |
| `NOMBRE_LIBRERIA` | `Libreria El Saber` | Nombre mostrado |
| `SLOGAN` | `Tu proxima gran lectura esta aqui` | Lema de la cabecera |
| `WHATSAPP_NUMERO` | `51943846909` | Número de WhatsApp (sin `+`) |
| `WHATSAPP_DISPLAY` | `+51 943 846 909` | Número tal como se muestra |
| `DIRECCION` | (temporal) | Dirección de la librería |
| `REFERENCIA` | (temporal) | Referencia de ubicación |
| `CORREO` | (temporal) | Correo de contacto |
| `HORARIO` | (temporal) | Horario de atención |
| `ADMIN_TOKEN` | aleatorio | Token fijo para `/api/consultas` |
| `SECRET_KEY` | aleatorio | Clave secreta de Flask |
| `HTTPS` | `0` | `1` cuando el sitio se sirve por HTTPS |
| `SITIO_URL` | (vacío) | URL pública para `og:image`, `canonical` y sitemap |
| `HOST` | `127.0.0.1` | Dirección de escucha |
| `PORT` | `5000` | Puerto |
| `FLASK_DEBUG` | `0` | `1` para el modo depuración |

Ejemplo en PowerShell:

```powershell
$env:PORT = "8080"; $env:ADMIN_TOKEN = "miclave"; .\venv\Scripts\python.exe app.py
```

---

## Comprobar el diseño móvil

Abre <http://127.0.0.1:5000>, pulsa **F12** y activa
**"Alternar emulación de dispositivo"** (`Ctrl + Shift + M`) para ver el sitio en
versiones de móvil y tablet. También puedes abrirlo desde el propio teléfono si
está en la misma red (arranca con `HOST=0.0.0.0`).
