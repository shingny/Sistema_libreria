/* ============================================================================
   Libreria El Saber - Logica del catalogo (frontend)
   ========================================================================== */

(function () {
  "use strict";

  // La configuracion llega en atributos data-* del <body>. Asi no hace falta
  // un script en linea y el CSP puede exigir script-src 'self'.
  var datos = (document.body && document.body.dataset) || {};
  var CFG = {
    whatsapp: datos.whatsapp || "51943846909",
    nombreLibreria: datos.nombreLibreria || "Libreria",
    whatsappDisplay: datos.whatsappDisplay || ""
  };
  var WA = CFG.whatsapp;

  // Estado del catalogo
  var estado = {
    q: "",
    categoria: "todas",
    orden: "recientes",
    libros: [],
    categorias: []
  };

  // Referencias del DOM
  var $ = function (sel) { return document.querySelector(sel); };
  var grid = $("#grid");
  var chips = $("#chips");
  var empty = $("#empty");
  var contador = $("#contador");
  var tituloCatalogo = $("#tituloCatalogo");
  var searchInput = $("#searchInput");
  var searchClear = $("#searchClear");
  var ordenSelect = $("#ordenSelect");
  var modal = $("#modal");
  var modalBody = $("#modalBody");
  var toast = $("#toast");
  var toastText = $("#toastText");
  var topbar = $("#topbar");
  var navToggle = $("#navToggle");
  var navMenu = $("#navMenu");
  var ultimoFoco = null;

  /* ------------------------------- Utilidades ------------------------------ */
  function soles(valor) {
    return "S/ " + Number(valor).toFixed(2);
  }

  function escaparHtml(texto) {
    return String(texto == null ? "" : texto)
      .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;").replace(/'/g, "&#39;");
  }

  function debounce(fn, ms) {
    var t;
    return function () {
      var args = arguments, ctx = this;
      clearTimeout(t);
      t = setTimeout(function () { fn.apply(ctx, args); }, ms);
    };
  }

  function mostrarToast(mensaje) {
    toastText.textContent = mensaje;
    toast.hidden = false;
    requestAnimationFrame(function () { toast.classList.add("is-show"); });
    clearTimeout(mostrarToast._t);
    mostrarToast._t = setTimeout(function () {
      toast.classList.remove("is-show");
      setTimeout(function () { toast.hidden = true; }, 300);
    }, 2800);
  }

  /* ---------------------------- Enlaces WhatsApp --------------------------- */
  function enlaceWhatsApp(mensaje) {
    return "https://wa.me/" + WA + "?text=" + encodeURIComponent(mensaje);
  }

  // Mensaje corto y directo: titulo en negrita y precio. Solo texto.
  function mensajeLibro(libro) {
    return [
      "Hola " + (CFG.nombreLibreria || "Libreria") + " \uD83D\uDC4B",
      "",
      "Me interesa este libro:",
      "",
      "\uD83D\uDCD5 *" + libro.titulo + "*",
      "\uD83D\uDCB0 Precio: " + soles(libro.precio),
      "",
      "\u00BFEsta disponible? \u00A1Gracias!"
    ].join("\n");
  }

  function registrarConsulta(libro) {
    // No bloquea la experiencia del usuario.
    try {
      fetch("/api/consultas", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          libro_id: libro.id,
          mensaje: mensajeLibro(libro)
        })
      }).catch(function () {});
    } catch (e) { /* ignorar */ }
  }

  // WhatsApp solo admite texto: se abre con el mensaje ya escrito.
  function consultarLibro(libro) {
    registrarConsulta(libro);
    window.open(enlaceWhatsApp(mensajeLibro(libro)), "_blank", "noopener");
    mostrarToast("Abriendo WhatsApp para: " + libro.titulo);
  }

  /* ------------------------------ Render chips ----------------------------- */
  function pintarCategorias() {
    var total = estado.categorias.reduce(function (acc, c) { return acc + c.total; }, 0);

    var html = [
      '<button class="chip is-active" data-cat="todas" style="--chip:#4338ca">',
      '  <span class="dot"></span> Todas <span class="count">' + total + "</span>",
      "</button>"
    ].join("");

    estado.categorias.forEach(function (c) {
      html += [
        '<button class="chip" data-cat="' + escaparHtml(c.slug) + '" style="--chip:' + escaparHtml(c.color) + '">',
        '  <span class="dot"></span> ' + escaparHtml(c.nombre),
        '  <span class="count">' + c.total + "</span>",
        "</button>"
      ].join("");
    });

    chips.innerHTML = html;

    chips.querySelectorAll(".chip").forEach(function (chip) {
      chip.addEventListener("click", function () {
        chips.querySelectorAll(".chip").forEach(function (c) { c.classList.remove("is-active"); });
        chip.classList.add("is-active");
        estado.categoria = chip.dataset.cat;
        actualizarTitulo();
        cargarLibros();
      });
    });
  }

  function actualizarTitulo() {
    if (estado.categoria === "todas") {
      tituloCatalogo.textContent = "Todo el catalogo";
    } else {
      var cat = estado.categorias.find(function (c) { return c.slug === estado.categoria; });
      tituloCatalogo.textContent = cat ? cat.nombre : "Catalogo";
    }
  }

  /* ------------------------------ Render libros ---------------------------- */
  function plantillaCard(libro) {
    var imagen = libro.imagen || "/static/img/placeholder.svg";
    var url = libro.url || ("/libro/" + libro.id);
    return [
      '<article class="card" data-id="' + libro.id + '" style="--card-color:' + escaparHtml(libro.categoria_color) + '">',
      '  <a class="card__link" href="' + escaparHtml(url) + '">',
      '    <div class="card__media">',
      '      <img src="' + escaparHtml(imagen) + '" alt="Portada de ' + escaparHtml(libro.titulo) + '" loading="lazy" width="400" height="600">',
      '      <span class="card__cat">' + escaparHtml(libro.categoria) + "</span>",
      (libro.destacado ? '<span class="card__fav" title="Libro destacado"><svg viewBox="0 0 24 24" fill="currentColor"><path d="m12 2 3.09 6.26L22 9.27l-5 4.87L18.18 21 12 17.77 5.82 21 7 14.14l-5-4.87 6.91-1.01L12 2z"/></svg></span>' : ""),
      "    </div>",
      '    <div class="card__body">',
      '      <h3 class="card__title">' + escaparHtml(libro.titulo) + "</h3>",
      '      <p class="card__author">' + escaparHtml(libro.autor) + "</p>",
      "    </div>",
      "  </a>",
      '  <div class="card__foot">',
      '    <div class="card__price">' + soles(libro.precio) + "<small>Precio</small></div>",
      '    <button class="card__btn" data-consultar="' + libro.id + '" aria-label="Consultar por WhatsApp">',
      '      <svg viewBox="0 0 24 24" fill="currentColor"><path d="M17.47 14.38c-.3-.15-1.76-.87-2.03-.97-.27-.1-.47-.15-.67.15-.2.3-.77.97-.94 1.17-.17.2-.35.22-.65.07-.3-.15-1.26-.46-2.4-1.48-.89-.79-1.49-1.77-1.66-2.07-.17-.3-.02-.46.13-.61.13-.13.3-.35.45-.52.15-.17.2-.3.3-.5.1-.2.05-.37-.02-.52-.08-.15-.67-1.62-.92-2.22-.24-.58-.49-.5-.67-.51h-.57c-.2 0-.52.07-.79.37-.27.3-1.04 1.02-1.04 2.48 0 1.46 1.07 2.88 1.22 3.08.15.2 2.1 3.2 5.08 4.49.71.31 1.26.49 1.69.63.71.23 1.36.19 1.87.12.57-.09 1.76-.72 2.01-1.41.25-.7.25-1.29.17-1.41-.07-.13-.27-.2-.57-.35zM12.04 2.02c-5.5 0-9.96 4.46-9.96 9.96 0 1.76.46 3.41 1.27 4.85L2 22l5.32-1.4c1.38.75 2.97 1.18 4.66 1.18h.01c5.5 0 9.96-4.46 9.96-9.96 0-2.66-1.04-5.16-2.93-7.04a9.9 9.9 0 0 0-6.98-2.9z"/></svg>',
      "    </button>",
      "  </div>",
      "</article>"
    ].join("");
  }

  function pintarLibros(libros) {
    if (!libros.length) {
      grid.innerHTML = "";
      empty.hidden = false;
      contador.textContent = "0 libros";
      return;
    }
    empty.hidden = true;
    grid.innerHTML = libros.map(plantillaCard).join("");
    contador.textContent = libros.length + (libros.length === 1 ? " libro" : " libros");
  }

  function pintarEsqueletos(n) {
    var html = "";
    for (var i = 0; i < (n || 8); i++) {
      html += '<div class="skeleton"><div class="sk-line sk-media"></div><div class="sk-body"><div class="sk-line"></div><div class="sk-line"></div><div class="sk-line"></div></div></div>';
    }
    grid.innerHTML = html;
    empty.hidden = true;
    contador.textContent = "Cargando...";
  }

  /* --------------------------------- Modal --------------------------------- */
  function abrirModal(libro) {
    var imagen = libro.imagen || "/static/img/placeholder.svg";

    modalBody.innerHTML = [
      '<div class="detail__media"><img src="' + escaparHtml(imagen) + '" alt="Portada de ' + escaparHtml(libro.titulo) + '"></div>',
      '<div class="detail__info">',
      '  <span class="detail__cat" style="background:' + escaparHtml(libro.categoria_color) + '">' + escaparHtml(libro.categoria) + "</span>",
      '  <h2 class="detail__title" id="modalTitulo">' + escaparHtml(libro.titulo) + "</h2>",
      '  <p class="detail__author">de <b>' + escaparHtml(libro.autor) + "</b></p>",
      '  <div class="detail__price"><strong>' + soles(libro.precio) + "</strong><span>Precio de venta</span></div>",
      '  <p class="detail__desc">' + escaparHtml(libro.descripcion || "Sin descripcion disponible.") + "</p>",
      '  <div class="detail__specs">',
      '    <div class="spec"><span>Autor</span><b>' + escaparHtml(libro.autor) + "</b></div>",
      '    <div class="spec"><span>Editorial</span><b>' + escaparHtml(libro.editorial || "-") + "</b></div>",
      '    <div class="spec"><span>Año</span><b>' + escaparHtml(libro.anio || "-") + "</b></div>",
      '    <div class="spec"><span>ISBN</span><b>' + escaparHtml(libro.isbn || "-") + "</b></div>",
      '    <div class="spec"><span>Categoria</span><b>' + escaparHtml(libro.categoria) + "</b></div>",
      "  </div>",
      '  <div class="detail__actions">',
      '    <button class="btn btn--wa" data-consultar="' + libro.id + '">',
      '      <svg class="ico" viewBox="0 0 24 24" fill="currentColor"><path d="M17.47 14.38c-.3-.15-1.76-.87-2.03-.97-.27-.1-.47-.15-.67.15-.2.3-.77.97-.94 1.17-.17.2-.35.22-.65.07-.3-.15-1.26-.46-2.4-1.48-.89-.79-1.49-1.77-1.66-2.07-.17-.3-.02-.46.13-.61.13-.13.3-.35.45-.52.15-.17.2-.3.3-.5.1-.2.05-.37-.02-.52-.08-.15-.67-1.62-.92-2.22-.24-.58-.49-.5-.67-.51h-.57c-.2 0-.52.07-.79.37-.27.3-1.04 1.02-1.04 2.48 0 1.46 1.07 2.88 1.22 3.08.15.2 2.1 3.2 5.08 4.49.71.31 1.26.49 1.69.63.71.23 1.36.19 1.87.12.57-.09 1.76-.72 2.01-1.41.25-.7.25-1.29.17-1.41-.07-.13-.27-.2-.57-.35zM12.04 2.02c-5.5 0-9.96 4.46-9.96 9.96 0 1.76.46 3.41 1.27 4.85L2 22l5.32-1.4c1.38.75 2.97 1.18 4.66 1.18h.01c5.5 0 9.96-4.46 9.96-9.96 0-2.66-1.04-5.16-2.93-7.04a9.9 9.9 0 0 0-6.98-2.9z"/></svg>',
      "      Enviar libro por WhatsApp",
      "    </button>",
      '    <button class="btn btn--ghost" data-close-modal>Cerrar</button>',
      "  </div>",
      "</div>"
    ].join("");

    var enlace = modalBody.querySelector("[data-consultar]");
    if (enlace) {
      enlace.href = enlaceWhatsApp(mensajeLibro(libro));
      enlace.target = "_blank";
      enlace.rel = "noopener";
    }

    ultimoFoco = document.activeElement;
    modal.hidden = false;
    document.body.style.overflow = "hidden";

    // Accesibilidad: el foco se mueve al boton de cerrar.
    var botonCerrar = modal.querySelector(".modal__close");
    if (botonCerrar) botonCerrar.focus();
  }

  function cerrarModal() {
    modal.hidden = true;
    document.body.style.overflow = "";

    // Accesibilidad: se devuelve el foco al elemento que abrio el modal.
    if (ultimoFoco && typeof ultimoFoco.focus === "function") ultimoFoco.focus();
    ultimoFoco = null;
  }

  /* --------------------------------- Datos --------------------------------- */
  function cargarCategorias() {
    return fetch("/api/categorias")
      .then(function (r) { return r.json(); })
      .then(function (data) {
        estado.categorias = data;
        pintarCategorias();
        $("#statCategorias").textContent = data.length;
        $("#statLibros").textContent = data.reduce(function (a, c) { return a + c.total; }, 0);
      })
      .catch(function () {
        chips.innerHTML = '<span class="chip">No se pudieron cargar las categorias</span>';
      });
  }

  function cargarLibros() {
    pintarEsqueletos();
    var params = new URLSearchParams({
      q: estado.q,
      categoria: estado.categoria,
      orden: estado.orden
    });

    return fetch("/api/libros?" + params.toString())
      .then(function (r) { return r.json(); })
      .then(function (data) {
        estado.libros = data.libros;
        pintarLibros(data.libros);
      })
      .catch(function () {
        grid.innerHTML = "";
        empty.hidden = false;
        contador.textContent = "Error de conexion";
      });
  }

  /* ------------------------------ Menu movil ------------------------------- */
  function abrirMenu() {
    navMenu.classList.add("is-open");
    navToggle.classList.add("is-active");
    navToggle.setAttribute("aria-expanded", "true");
    navToggle.setAttribute("aria-label", "Cerrar menu");
  }

  function cerrarMenu() {
    if (!navMenu || !navMenu.classList.contains("is-open")) return;
    navMenu.classList.remove("is-open");
    navToggle.classList.remove("is-active");
    navToggle.setAttribute("aria-expanded", "false");
    navToggle.setAttribute("aria-label", "Abrir menu");
  }

  function iniciarMenu() {
    if (!navToggle || !navMenu) return;

    navToggle.addEventListener("click", function () {
      if (navMenu.classList.contains("is-open")) cerrarMenu(); else abrirMenu();
    });

    // Al tocar un enlace del menu, se cierra.
    navMenu.querySelectorAll("a").forEach(function (a) {
      a.addEventListener("click", cerrarMenu);
    });

    // Se cierra al tocar fuera o con la tecla Escape.
    document.addEventListener("click", function (e) {
      if (!navMenu.classList.contains("is-open")) return;
      if (e.target.closest("#navMenu") || e.target.closest("#navToggle")) return;
      cerrarMenu();
    });

    document.addEventListener("keydown", function (e) {
      if (e.key === "Escape") cerrarMenu();
    });

    // Si la pantalla vuelve a ser de escritorio, se restablece.
    window.addEventListener("resize", function () {
      if (window.innerWidth > 900) cerrarMenu();
    });
  }

  /* -------------------------------- Eventos -------------------------------- */
  function iniciarCatalogo() {
    // Busqueda (con retardador para no saturar el servidor)
    var buscar = debounce(function () {
      estado.q = searchInput.value.trim();
      searchClear.hidden = !estado.q;
      cargarLibros();
    }, 320);

    searchInput.addEventListener("input", buscar);
    $("#searchForm").addEventListener("submit", function (e) {
      e.preventDefault();
      estado.q = searchInput.value.trim();
      cargarLibros();
    });
    searchClear.addEventListener("click", function () {
      searchInput.value = "";
      estado.q = "";
      searchClear.hidden = true;
      cargarLibros();
      searchInput.focus();
    });

    // Orden
    ordenSelect.addEventListener("change", function () {
      estado.orden = ordenSelect.value;
      cargarLibros();
    });

    // Reset de filtros
    $("#resetFiltros").addEventListener("click", function () {
      searchInput.value = "";
      estado.q = "";
      estado.categoria = "todas";
      searchClear.hidden = true;
      chips.querySelectorAll(".chip").forEach(function (c) {
        c.classList.toggle("is-active", c.dataset.cat === "todas");
      });
      actualizarTitulo();
      cargarLibros();
    });

    // Clic en tarjetas y botones (delegacion de eventos)
    grid.addEventListener("click", function (e) {
      var btn = e.target.closest("[data-consultar]");
      if (btn) {
        e.preventDefault();
        e.stopPropagation();
        var libro = buscarLibro(btn.dataset.consultar);
        if (libro) consultarLibro(libro);
        return;
      }

      var card = e.target.closest(".card");
      if (!card) return;

      // Ctrl/Cmd/Shift o boton central: se deja abrir la ficha real en otra pestana.
      if (e.button !== 0 || e.ctrlKey || e.metaKey || e.shiftKey || e.altKey) return;

      var l = buscarLibro(card.dataset.id);
      if (!l) return;
      e.preventDefault();
      abrirModal(l);
    });

    // Modal
    modal.addEventListener("click", function (e) {
      if (e.target.closest("[data-close-modal]")) { cerrarModal(); return; }
      var btn = e.target.closest("[data-consultar]");
      if (btn) {
        e.preventDefault();
        var libro = buscarLibro(btn.dataset.consultar);
        if (libro) consultarLibro(libro);
      }
    });
    document.addEventListener("keydown", function (e) {
      if (e.key === "Escape" && !modal.hidden) cerrarModal();
    });

  }

  // Se ejecuta en todas las paginas (inicio y ficha de libro).
  function iniciarEventos() {
    iniciarMenu();

    // Cabecera con sombra al hacer scroll
    if (topbar) {
      window.addEventListener("scroll", function () {
        topbar.classList.toggle("is-stuck", window.scrollY > 8);
      }, { passive: true });
    }

    var msgGeneral = "Hola " + (CFG.nombreLibreria || "Libreria") + " \uD83D\uDC4B, quisiera mas informacion sobre su catalogo de libros.";
    ["#waHeader", "#waMenu", "#waContacto", "#waFab"].forEach(function (sel) {
      var el = document.querySelector(sel);
      if (el) el.href = enlaceWhatsApp(msgGeneral);
    });

    // Boton de WhatsApp de la ficha del libro: registra la consulta sin
    // bloquear la navegacion (misma tabla que usa el catalogo).
    document.querySelectorAll("[data-consultar]").forEach(function (el) {
      if (el.closest("#grid") || el.closest("#modal")) return;
      el.addEventListener("click", function () {
        try {
          fetch("/api/consultas", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ libro_id: Number(el.dataset.consultar) })
          }).catch(function () {});
        } catch (e) { /* ignorar */ }
      });
    });

    var anio = $("#year");
    if (anio) anio.textContent = new Date().getFullYear();

    // La ficha de un libro no tiene catalogo: solo cabecera, menu y enlaces.
    if (!grid || !chips || !searchInput || !ordenSelect || !empty ||
        !contador || !tituloCatalogo || !searchClear) return;
    iniciarCatalogo();
  }

  function buscarLibro(id) {
    id = String(id);
    return estado.libros.find(function (l) { return String(l.id) === id; });
  }

  /* --------------------------------- Inicio -------------------------------- */
  document.addEventListener("DOMContentLoaded", function () {
    iniciarEventos();
    if (grid) cargarCategorias().then(cargarLibros);
  });
})();
