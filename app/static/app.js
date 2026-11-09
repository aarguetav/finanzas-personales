"use strict";

// Finanzas personales — lógica de la UI. Sin build: fetch + Chart.js + DOM.

const MONEDAS = { HNL: "L", USD: "$" };

function fmt(minor, moneda) {
  const simbolo = MONEDAS[moneda] || moneda;
  const valor = (minor / 100).toLocaleString("es-HN", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
  return `${simbolo} ${valor}`;
}

function escapar(texto) {
  const div = document.createElement("div");
  div.textContent = texto;
  return div.innerHTML;
}

async function api(url, opciones) {
  const respuesta = await fetch(url, opciones);
  if (!respuesta.ok) {
    let detalle = `HTTP ${respuesta.status}`;
    try {
      const datos = await respuesta.json();
      if (Array.isArray(datos.detail)) detalle = datos.detail.map((error) => error.msg).join("; ");
      else if (datos.detail) detalle = datos.detail;
    } catch {
      // sin cuerpo JSON
    }
    throw new Error(detalle);
  }
  return respuesta.json();
}

function alerta(mensaje) {
  const caja = document.getElementById("alerta");
  if (!mensaje) {
    caja.classList.add("d-none");
    return;
  }
  caja.textContent = mensaje;
  caja.classList.remove("d-none");
}

const estado = { meses: [], categorias: [], tarjetas: [], mes: null, pagina: 0, porPagina: 50, solicitud: 0 };

function colorCategoria(nombre) {
  return estado.categorias.find((categoria) => categoria.nombre === nombre)?.color || "#718096";
}

function opcionesTarjetas(select) {
  select.replaceChildren(new Option("Todas las tarjetas", ""));
  for (const tarjeta of estado.tarjetas) select.add(new Option(tarjeta.alias, tarjeta.id));
}

function actualizarOpciones(select, llenar, ...args) {
  const anterior = select.value;
  llenar(select, ...args);
  select.value = anterior;
}

function opcionesMeses(select, incluirVacio) {
  select.innerHTML = "";
  if (incluirVacio) {
    const opcion = document.createElement("option");
    opcion.value = "";
    opcion.textContent = "Todos los meses";
    select.appendChild(opcion);
  }
  for (const mes of estado.meses) {
    const opcion = document.createElement("option");
    opcion.value = mes.mes;
    opcion.textContent = `${mes.mes} · ${mes.estados} estado${mes.estados === 1 ? "" : "s"}`;
    select.appendChild(opcion);
  }
}

function opcionesCategorias(select, incluirVacio) {
  select.innerHTML = "";
  if (incluirVacio) {
    const opcion = document.createElement("option");
    opcion.value = "";
    opcion.textContent = "Todas las categorías";
    select.appendChild(opcion);
  }
  for (const categoria of estado.categorias) {
    const opcion = document.createElement("option");
    opcion.value = categoria.nombre;
    opcion.textContent = categoria.nombre;
    select.appendChild(opcion);
  }
}

async function refrescarBase() {
  const [categorias, meses, cola, tarjetas] = await Promise.all([
    api("/api/categories"),
    api("/api/months"),
    api("/api/queue"),
    api("/api/cards"),
  ]);
  estado.categorias = categorias;
  estado.meses = meses;
  estado.tarjetas = tarjetas;
  if (!estado.mes && meses.length > 0) estado.mes = meses[meses.length - 1].mes;

  const badge = document.getElementById("cola-badge");
  badge.textContent = cola.length > 0 ? cola.length : "";

  opcionesMeses(document.getElementById("mes-selector"), false);
  document.getElementById("mes-selector").value = estado.mes || "";

  actualizarOpciones(document.getElementById("f-mes"), opcionesMeses, true);
  actualizarOpciones(document.getElementById("f-categoria"), opcionesCategorias, true);
  actualizarOpciones(document.getElementById("d-categoria"), opcionesCategorias, true);
  actualizarOpciones(document.getElementById("f-tarjeta"), opcionesTarjetas);
  actualizarOpciones(document.getElementById("d-tarjeta"), opcionesTarjetas);
}

function cambiarVista(nombre) {
  for (const enlace of document.querySelectorAll(".navbar-nav .nav-link")) {
    const activa = enlace.dataset.view === nombre;
    enlace.classList.toggle("active", activa);
    if (activa) enlace.setAttribute("aria-current", "page");
    else enlace.removeAttribute("aria-current");
  }
  for (const seccion of ["dashboard", "movimientos", "tarjetas", "cola", "categorias", "cargar"]) {
    document.getElementById(`view-${seccion}`).classList.toggle("d-none", seccion !== nombre);
  }
  if (nombre === "dashboard") ejecutar(dibujarDashboard);
  if (nombre === "movimientos") ejecutar(listarMovimientos);
  if (nombre === "cola") ejecutar(listarCola);
  if (nombre === "categorias") listarCategorias();
  if (nombre === "tarjetas") listarTarjetas();
}

function listarTarjetas() {
  const lista = document.getElementById("tarjetas-lista");
  lista.replaceChildren();
  if (estado.tarjetas.length === 0) {
    const vacio = document.createElement("div");
    vacio.className = "empty-state";
    vacio.textContent = "Aún no hay tarjetas. Carga un estado de cuenta para comenzar.";
    lista.appendChild(vacio);
    return;
  }
  for (const tarjeta of estado.tarjetas) {
    const article = document.createElement("article");
    article.className = "card bank-card";
    article.setAttribute("aria-label", tarjeta.alias);
    article.innerHTML = `
      <div class="bank-card-mark" aria-hidden="true">
        <svg viewBox="0 0 24 24"><rect x="3" y="5" width="18" height="14" rx="2" />
          <path d="M3 10h18m-14 5h4" /></svg>
      </div>
      <div class="bank-card-copy">
        <h3 class="card-title"></h3>
        <p class="bank-card-bank"></p>
      </div>
      <button class="btn btn-sm bank-card-action" type="button">Ver movimientos</button>`;
    article.querySelector(".card-title").textContent = tarjeta.alias;
    article.querySelector(".bank-card-bank").textContent = tarjeta.banco;
    article.querySelector(".bank-card-action").addEventListener("click", () => {
      document.getElementById("d-tarjeta").value = tarjeta.id;
      document.getElementById("f-tarjeta").value = tarjeta.id;
      document.getElementById("f-mes").value = estado.mes || "";
      estado.pagina = 0;
      cambiarVista("movimientos");
    });
    lista.appendChild(article);
  }
}

async function ejecutar(accion) {
  try {
    await accion();
  } catch (error) {
    alerta(error.message);
  }
}

function parametrosDashboard(mes) {
  const params = new URLSearchParams({ month: mes });
  for (const [id, nombre] of [["d-tarjeta", "card"], ["d-moneda", "currency"], ["d-categoria", "category"]]) {
    const valor = document.getElementById(id).value;
    if (valor) params.set(nombre, valor);
  }
  return params;
}

function dibujarBarras(id, bloque, moneda) {
  const contenedor = document.getElementById(id);
  contenedor.replaceChildren();
  if (!bloque?.por_categoria.length) {
    contenedor.innerHTML = '<div class="empty-inline">Sin gastos para esta selección.</div>';
    return;
  }
  const maximo = Math.max(0, ...bloque.por_categoria.map((fila) => fila.total));
  for (const fila of bloque.por_categoria) {
    const elemento = document.createElement("div");
    elemento.className = "category-row";
    const label = document.createElement("div");
    label.className = "category-row-label";
    const nombre = document.createElement("button");
    nombre.type = "button";
    nombre.className = "category-link";
    const punto = document.createElement("span");
    punto.className = "category-dot";
    punto.style.backgroundColor = colorCategoria(fila.categoria);
    nombre.append(punto, document.createTextNode(fila.categoria));
    nombre.addEventListener("click", () => {
      document.getElementById("f-mes").value = estado.mes;
      document.getElementById("f-categoria").value = fila.categoria;
      document.getElementById("f-moneda").value = moneda;
      document.getElementById("f-tarjeta").value = document.getElementById("d-tarjeta").value;
      document.getElementById("f-q").value = "";
      estado.pagina = 0;
      cambiarVista("movimientos");
    });
    const valor = document.createElement("strong");
    valor.textContent = fmt(fila.total, moneda);
    label.append(nombre, valor);
    const track = document.createElement("div");
    track.className = "category-track";
    const barra = document.createElement("div");
    barra.className = "category-fill";
    barra.style.width = `${maximo ? Math.max(fila.total, 0) / maximo * 100 : 0}%`;
    barra.style.backgroundColor = colorCategoria(fila.categoria);
    track.appendChild(barra);
    elemento.append(label, track);
    contenedor.appendChild(elemento);
  }
}

function dibujarEvolucion(moneda, resultados) {
  const canvas = document.getElementById(`chart-evolucion-${moneda.toLowerCase()}`);
  const anterior = Chart.getChart(canvas);
  if (anterior) anterior.destroy();
  const porMes = new Map(resultados.map((resumen) => [resumen.mes, resumen]));
  const meses = [];
  let [ano, numero] = estado.meses[0].mes.split("-").map(Number);
  const ultimo = estado.meses[estado.meses.length - 1].mes;
  while (true) {
    const mes = `${ano}-${String(numero).padStart(2, "0")}`;
    if (mes > ultimo) break;
    meses.push(mes);
    if (mes === ultimo) break;
    if (++numero === 13) { numero = 1; ano++; }
  }
  new Chart(canvas, {
    type: "line",
    data: {
      labels: meses,
      datasets: [{
        label: moneda,
        data: meses.map((mes) => {
          const resumen = porMes.get(mes);
          return resumen?.movimientos_por_moneda[moneda]
            ? (resumen.gasto[moneda]?.total || 0) / 100 : null;
        }),
        borderColor: moneda === "HNL" ? "#0a6fff" : "#0f766e",
        backgroundColor: moneda === "HNL" ? "#0a6fff" : "#0f766e",
        borderWidth: 2,
        pointRadius: 2,
        pointHoverRadius: 5,
        tension: 0.25,
        spanGaps: false,
      }],
    },
    options: {
      maintainAspectRatio: false,
      interaction: { intersect: false, mode: "index" },
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: {
            label: (context) => fmt(Math.round(context.parsed.y * 100), moneda),
          },
        },
      },
      scales: {
        y: {
          beginAtZero: true,
          grid: { color: "#eef2f7" },
          ticks: {
            maxTicksLimit: 4,
            callback: (valor) => `${MONEDAS[moneda]} ${new Intl.NumberFormat("es-HN", {
              notation: "compact",
              maximumFractionDigits: 1,
            }).format(valor)}`,
          },
        },
        x: { grid: { display: false }, ticks: { maxRotation: 0, autoSkip: true } },
      },
    },
  });
}

function mesAnterior(mes) {
  const [ano, numero] = mes.split("-").map(Number);
  return numero === 1 ? `${ano - 1}-12` : `${ano}-${String(numero - 1).padStart(2, "0")}`;
}

async function dibujarDashboard() {
  const solicitud = ++estado.solicitud;
  alerta(null);
  const contenido = document.getElementById("dashboard-contenido");
  const mensaje = document.getElementById("dashboard-estado");
  document.getElementById("dashboard-vacio").classList.toggle("d-none", Boolean(estado.mes));
  contenido.classList.add("d-none");
  mensaje.textContent = estado.mes ? "Actualizando resumen…" : "";
  if (!estado.mes) return;
  let resultados;
  try {
    resultados = await Promise.all(estado.meses.map((mes) =>
      api(`/api/summary?${parametrosDashboard(mes.mes)}`),
    ));
  } catch (error) {
    if (solicitud !== estado.solicitud) return;
    mensaje.textContent = "";
    throw error;
  }
  if (solicitud !== estado.solicitud) return;
  mensaje.textContent = "";
  contenido.classList.remove("d-none");
  const resumen = resultados.find((item) => item.mes === estado.mes);
  const anterior = resultados.find((item) => item.mes === mesAnterior(estado.mes));
  const monedaSeleccionada = document.getElementById("d-moneda").value;
  for (const moneda of ["HNL", "USD"]) {
    const id = moneda.toLowerCase();
    const visible = !monedaSeleccionada || monedaSeleccionada === moneda;
    const tieneDatos = Boolean(resumen.movimientos_por_moneda[moneda]);
    const actual = resumen.gasto[moneda]?.total || 0;
    document.getElementById(`kpi-${id}`).textContent = visible && tieneDatos ? fmt(actual, moneda) : "—";
    const comparacion = document.getElementById(`comparacion-${id}`);
    if (!visible) comparacion.textContent = "Moneda fuera del filtro";
    else if (!tieneDatos) comparacion.textContent = "Sin movimientos para esta selección";
    else if (!anterior?.movimientos_por_moneda[moneda]) comparacion.textContent = "Sin datos del mes anterior";
    else {
      const previo = anterior.gasto[moneda]?.total || 0;
      const diferencia = actual - previo;
      comparacion.textContent = `${diferencia >= 0 ? "+" : "−"}${fmt(Math.abs(diferencia), moneda)} vs. mes anterior`;
    }
    dibujarBarras(`categorias-${id}`, resumen.gasto[moneda], moneda);
    dibujarEvolucion(moneda, resultados);
  }
  document.getElementById("kpi-movimientos").textContent = resumen.movimientos;
  document.getElementById("kpi-pendientes").textContent = resumen.sin_categorizar;
  const tbody = document.getElementById("panel-tarjeta");
  tbody.replaceChildren();
  for (const fila of resumen.excluidas) {
    const tr = document.createElement("tr");
    tr.innerHTML = `<td><span class="category-dot"></span>${escapar(fila.categoria)}</td>
      <td>${escapar(fila.moneda)}</td><td class="text-end">${escapar(fmt(fila.total, fila.moneda))}</td>`;
    tr.querySelector(".category-dot").style.backgroundColor = colorCategoria(fila.categoria);
    tbody.appendChild(tr);
  }
  if (!resumen.excluidas.length) tbody.innerHTML = '<tr><td colspan="3" class="empty-inline">Sin otros movimientos para esta selección.</td></tr>';
}

function listarCategorias() {
  const lista = document.getElementById("categorias-lista");
  lista.replaceChildren();
  if (estado.categorias.length === 0) {
    const vacio = document.createElement("p");
    vacio.className = "empty-inline";
    vacio.textContent = "Aún no hay categorías.";
    lista.appendChild(vacio);
    return;
  }
  for (const categoria of estado.categorias) {
    const fila = document.createElement("div");
    fila.className = "category-item";
    const nombre = document.createElement("span");
    const punto = document.createElement("span");
    punto.className = "category-dot";
    punto.style.backgroundColor = categoria.color;
    nombre.append(punto, document.createTextNode(categoria.nombre));
    const detalle = document.createElement("small");
    detalle.textContent = categoria.exclude_from_spend ? "Excluida del gasto" : "Incluida en gasto";
    fila.append(nombre, detalle);
    lista.appendChild(fila);
  }
}

function filaCategoria(row) {
  const select = document.createElement("select");
  select.className = "form-select form-select-sm category-select";
  select.style.setProperty("--category-color", colorCategoria(row.categoria));
  const vacia = document.createElement("option");
  vacia.value = "";
  vacia.textContent = "Sin categorizar";
  select.appendChild(vacia);
  for (const categoria of estado.categorias) {
    const opcion = document.createElement("option");
    opcion.value = categoria.nombre;
    opcion.textContent = categoria.nombre;
    select.appendChild(opcion);
  }
  if (row.categoria !== "Sin categorizar") select.value = row.categoria;
  return select;
}

async function listarMovimientos() {
  alerta(null);
  const params = new URLSearchParams();
  const mes = document.getElementById("f-mes").value;
  const categoria = document.getElementById("f-categoria").value;
  const moneda = document.getElementById("f-moneda").value;
  const tarjeta = document.getElementById("f-tarjeta").value.trim();
  const q = document.getElementById("f-q").value.trim();
  if (mes) params.set("month", mes);
  if (categoria) params.set("category", categoria);
  if (moneda) params.set("currency", moneda);
  if (tarjeta) params.set("card", tarjeta);
  if (q) params.set("q", q);
  params.set("limit", estado.porPagina);
  params.set("offset", estado.pagina * estado.porPagina);

  const movimientos = await api(`/api/transactions?${params.toString()}`);
  const haySiguiente = movimientos.length === estado.porPagina;
  const desde = movimientos.length === 0 ? 0 : estado.pagina * estado.porPagina + 1;
  const hasta = estado.pagina * estado.porPagina + movimientos.length;
  document.getElementById("pagina-info").textContent =
    movimientos.length === 0 ? "Sin movimientos" : `Movimientos ${desde}–${hasta}`;
  document.getElementById("pagina-anterior").disabled = estado.pagina === 0;
  document.getElementById("pagina-siguiente").disabled = !haySiguiente;

  const tbody = document.getElementById("tabla-movimientos");
  tbody.innerHTML = "";
  if (movimientos.length === 0) {
    const filaVacia = document.createElement("tr");
    const mensaje = document.createElement("td");
    mensaje.colSpan = 7;
    mensaje.className = "empty-inline";
    mensaje.textContent = "No encontramos movimientos con estos filtros.";
    filaVacia.appendChild(mensaje);
    tbody.appendChild(filaVacia);
  }
  for (const mov of movimientos) {
    const tr = document.createElement("tr");
    const select = filaCategoria(mov);
    select.addEventListener("change", async () => {
      if (!select.value) return;
      try {
        await api(`/api/transactions/${mov.id}/category`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ categoria: select.value }),
        });
        await refrescarBase();
        await listarMovimientos();
        await dibujarDashboard();
      } catch (error) {
        alerta(error.message);
      }
    });

    const tdFecha = document.createElement("td");
    tdFecha.textContent = mov.fecha;
    const tdDescripcion = document.createElement("td");
    tdDescripcion.textContent = mov.descripcion;
    const tdMonto = document.createElement("td");
    tdMonto.className = "text-end";
    tdMonto.textContent = fmt(mov.monto_minor, mov.moneda);
    const tdMoneda = document.createElement("td");
    tdMoneda.textContent = mov.moneda;
    const tdTarjeta = document.createElement("td");
    tdTarjeta.textContent = mov.tarjeta_alias || mov.tarjeta;
    const tdCategoria = document.createElement("td");
    tdCategoria.appendChild(select);
    const tdAccion = document.createElement("td");
    const boton = document.createElement("button");
    boton.className = "btn btn-sm";
    boton.textContent = "Editar monto";
    boton.addEventListener("click", async () => {
      const entrada = prompt("Nuevo monto (ej. 1234.56):", (mov.monto_minor / 100).toFixed(2));
      if (entrada === null) return;
      const monto = Number.parseFloat(entrada.replace(",", "."));
      if (Number.isNaN(monto)) {
        alerta("Monto inválido.");
        return;
      }
      try {
        await api(`/api/transactions/${mov.id}`, {
          method: "PATCH",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ monto_minor: Math.round(monto * 100) }),
        });
        await listarMovimientos();
        await dibujarDashboard();
      } catch (error) {
        alerta(error.message);
      }
    });
    tdAccion.appendChild(boton);
    tr.append(tdFecha, tdDescripcion, tdMonto, tdMoneda, tdTarjeta, tdCategoria, tdAccion);
    tbody.appendChild(tr);
  }
}

async function listarCola() {
  alerta(null);
  const cola = await api("/api/queue");
  const tbody = document.getElementById("tabla-cola");
  tbody.innerHTML = "";
  if (cola.length === 0) {
    const filaVacia = document.createElement("tr");
    const mensaje = document.createElement("td");
    mensaje.colSpan = 7;
    mensaje.className = "empty-inline";
    mensaje.textContent = "No hay movimientos por revisar.";
    filaVacia.appendChild(mensaje);
    tbody.appendChild(filaVacia);
  }
  for (const fila of cola) {
    const tr = document.createElement("tr");
    const select = filaCategoria(fila);
    const boton = document.createElement("button");
    boton.className = "btn btn-sm btn-primary";
    boton.textContent = "Corregir";
    boton.addEventListener("click", async () => {
      if (!select.value) {
        alerta("Elige una categoría.");
        return;
      }
      try {
        await api(`/api/transactions/${fila.id}/category`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ categoria: select.value }),
        });
        await refrescarBase();
        await listarCola();
        await dibujarDashboard();
      } catch (error) {
        alerta(error.message);
      }
    });

    tr.innerHTML = `
      <td>${escapar(fila.fecha)}</td>
      <td>${escapar(fila.descripcion)}</td>
      <td class="text-end">${escapar(fmt(fila.monto_minor, fila.moneda))}</td>
      <td>${escapar(fila.moneda)}</td>
      <td>${escapar(fila.tarjeta_alias || fila.tarjeta)}</td>`;
    const tdCategoria = document.createElement("td");
    tdCategoria.appendChild(select);
    const tdAccion = document.createElement("td");
    tdAccion.appendChild(boton);
    tr.append(tdCategoria, tdAccion);
    tbody.appendChild(tr);
  }
}

async function inicializar() {
  for (const enlace of document.querySelectorAll(".navbar-nav .nav-link")) {
    enlace.addEventListener("click", (evento) => {
      evento.preventDefault();
      cambiarVista(enlace.dataset.view);
    });
  }
  for (const enlace of document.querySelectorAll("[data-open-view], .navbar-brand [data-view]")) {
    enlace.addEventListener("click", (evento) => {
      evento.preventDefault();
      cambiarVista(enlace.dataset.openView || enlace.dataset.view);
    });
  }
  document.getElementById("mes-selector").addEventListener("change", (evento) => {
    estado.mes = evento.target.value;
    ejecutar(dibujarDashboard);
  });
  document.getElementById("dashboard-filtros").addEventListener("change", () => {
    ejecutar(dibujarDashboard);
  });
  document.getElementById("d-tarjeta").addEventListener("change", (evento) => {
    document.getElementById("f-tarjeta").value = evento.target.value;
    estado.pagina = 0;
  });
  document.getElementById("f-tarjeta").addEventListener("change", (evento) => {
    document.getElementById("d-tarjeta").value = evento.target.value;
    estado.pagina = 0;
    ejecutar(dibujarDashboard);
  });
  document.getElementById("dashboard-limpiar").addEventListener("click", () => {
    for (const id of ["d-tarjeta", "d-moneda", "d-categoria"]) document.getElementById(id).value = "";
    document.getElementById("f-tarjeta").value = "";
    estado.pagina = 0;
    ejecutar(dibujarDashboard);
  });
  document.getElementById("filtros").addEventListener("submit", (evento) => {
    evento.preventDefault();
    estado.pagina = 0;
    ejecutar(listarMovimientos);
  });
  document.getElementById("f-limpiar").addEventListener("click", () => {
    document.getElementById("filtros").reset();
    document.getElementById("d-tarjeta").value = "";
    estado.pagina = 0;
    ejecutar(dibujarDashboard);
    ejecutar(listarMovimientos);
  });
  document.getElementById("categoria-form").addEventListener("submit", async (evento) => {
    evento.preventDefault();
    const resultado = document.getElementById("categoria-resultado");
    resultado.textContent = "";
    try {
      const categoria = await api("/api/categories", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          nombre: document.getElementById("categoria-nombre").value,
          color: document.getElementById("categoria-color").value,
          exclude_from_spend: document.getElementById("categoria-excluida").checked,
        }),
      });
      await refrescarBase();
      listarCategorias();
      evento.target.reset();
      resultado.textContent = `Categoría ${categoria.nombre} agregada.`;
      resultado.className = "mt-3 text-success";
    } catch (error) {
      resultado.textContent = error.message;
      resultado.className = "mt-3 text-danger";
    }
  });
  document.getElementById("pagina-anterior").addEventListener("click", () => {
    if (estado.pagina > 0) {
      estado.pagina = estado.pagina - 1;
      ejecutar(listarMovimientos);
    }
  });
  document.getElementById("pagina-siguiente").addEventListener("click", () => {
    estado.pagina = estado.pagina + 1;
    ejecutar(listarMovimientos);
  });
  document.getElementById("pdfs").addEventListener("change", async (evento) => {
    const resultados = document.getElementById("resultados");
    resultados.innerHTML = "";
    alerta(null);
    for (const archivo of evento.target.files) {
      const datos = new FormData();
      datos.append("archivo", archivo);
      const tarjeta = document.createElement("div");
      tarjeta.className = "alert alert-secondary";
      tarjeta.textContent = `Subiendo ${archivo.name}…`;
      resultados.appendChild(tarjeta);
      try {
        const res = await api("/api/statements", { method: "POST", body: datos });
        tarjeta.className =
          res.estado === "nuevo" ? "alert alert-success" : "alert alert-warning";
        let texto = `${archivo.name}: ${res.estado === "nuevo" ? "nuevo" : "duplicado"}`;
        texto += ` · ${res.transacciones} movimiento${res.transacciones === 1 ? "" : "s"}`;
        if (res.issues.length > 0) {
          texto += ` · ${res.issues.length} issue${res.issues.length === 1 ? "" : "s"} por revisar`;
        }
        tarjeta.textContent = texto;
      } catch (error) {
        tarjeta.className = "alert alert-danger";
        tarjeta.textContent = `${archivo.name}: ${error.message}`;
      }
    }
    evento.target.value = "";
    await ejecutar(async () => {
      await refrescarBase();
      await dibujarDashboard();
    });
  });

  try {
    await refrescarBase();
  } catch (error) {
    alerta(error.message);
  }
  cambiarVista("dashboard");
}

inicializar();
