const API = "/api";
const state = { products: [], locations: [], currentPage: "dashboard" };

const pageMeta = {
  dashboard: ["Dashboard", "Resumen operativo del inventario"],
  products: ["Productos", "Administración del catálogo"],
  locations: ["Ubicaciones", "Depósitos, tiendas y puntos de stock"],
  inventory: ["Inventario", "Existencias por producto y ubicación"],
  movements: ["Movimientos", "Trazabilidad de todas las operaciones"],
};

const movementLabels = {
  ENTRY: "Entrada",
  EXIT: "Salida",
  TRANSFER: "Transferencia",
  ADJUSTMENT: "Ajuste",
};

const escapeHTML = (value) => String(value ?? "")
  .replaceAll("&", "&amp;").replaceAll("<", "&lt;")
  .replaceAll(">", "&gt;").replaceAll('"', "&quot;").replaceAll("'", "&#039;");

const quantity = (value) => new Intl.NumberFormat("es-UY", {
  maximumFractionDigits: 3,
}).format(Number(value || 0));

const dateTime = (value) => new Intl.DateTimeFormat("es-UY", {
  dateStyle: "short", timeStyle: "short",
}).format(new Date(value));

async function api(path, options = {}) {
  const response = await fetch(`${API}${path}`, {
    ...options,
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
  });
  if (!response.ok) {
    let body = {};
    try { body = await response.json(); } catch (_) { /* response without JSON */ }
    let message = body.detail || "No fue posible completar la operación.";
    if (Array.isArray(message)) {
      message = message.map((item) => item.msg?.replace("Value error, ", "") || "Dato inválido").join(" · ");
    }
    throw new Error(message);
  }
  return response.status === 204 ? null : response.json();
}

function showToast(message, type = "success") {
  const toast = document.createElement("div");
  toast.className = `toast ${type}`;
  toast.textContent = message;
  document.querySelector("#toast-region").append(toast);
  setTimeout(() => toast.remove(), 4200);
}

const emptyState = (icon, title, text) => `
  <div class="empty-state"><div class="empty-icon">${icon}</div><h3>${escapeHTML(title)}</h3><p>${escapeHTML(text)}</p></div>`;

const loadingState = () => `<div class="loading-state"><span class="spinner"></span><p>Cargando información…</p></div>`;

function movementBadge(type) {
  return `<span class="badge ${type.toLowerCase()}">${movementLabels[type]}</span>`;
}

function movementRoute(item) {
  if (item.movement_type === "ENTRY") return `→ ${escapeHTML(item.destination_location_name)}`;
  if (item.movement_type === "EXIT") return `${escapeHTML(item.source_location_name)} →`;
  if (item.movement_type === "TRANSFER") return `${escapeHTML(item.source_location_name)} → ${escapeHTML(item.destination_location_name)}`;
  return `Ajuste en ${escapeHTML(item.destination_location_name)}`;
}

async function refreshReferences() {
  [state.products, state.locations] = await Promise.all([
    api("/products"), api("/locations"),
  ]);
}

async function renderDashboard() {
  const data = await api("/dashboard");
  const maxLocationStock = Math.max(...data.stock_by_location.map((item) => Number(item.total_quantity)), 1);
  const movementRows = data.recent_movements.map((item) => `
    <tr>
      <td><span class="cell-title">${escapeHTML(item.product_name)}</span><span class="cell-subtitle mono">${escapeHTML(item.product_sku)}</span></td>
      <td>${movementBadge(item.movement_type)}</td>
      <td><span class="cell-title">${movementRoute(item)}</span><span class="cell-subtitle">${escapeHTML(item.notes || "Sin notas")}</span></td>
      <td class="number align-right">${item.quantity > 0 && item.movement_type !== "EXIT" ? "+" : ""}${quantity(item.quantity)}</td>
      <td class="align-right"><span class="cell-subtitle">${dateTime(item.timestamp)}</span></td>
    </tr>`).join("");
  const locationBars = data.stock_by_location.map((item) => `
    <div class="bar-item"><div class="bar-label"><span>${escapeHTML(item.location_name)}</span><span>${quantity(item.total_quantity)}</span></div>
      <div class="bar-track"><div class="bar-fill" style="width:${Math.max(3, Number(item.total_quantity) / maxLocationStock * 100)}%"></div></div></div>`).join("");
  const lowStockRows = data.low_stock_products.map((item) => `
    <div class="low-stock-item"><span><strong>${escapeHTML(item.name)}</strong><small>${escapeHTML(item.sku)} · mínimo ${quantity(item.minimum_stock)} ${escapeHTML(item.unit)}</small></span>
      <span class="stock-gap">${quantity(item.total_quantity)} ${escapeHTML(item.unit)}</span></div>`).join("");

  return `
    <div class="page-heading"><div><h2>Vista general</h2><p>Indicadores actualizados con todos los movimientos registrados.</p></div>
      <button class="button primary" data-new-movement>＋ Registrar movimiento</button></div>
    <section class="metric-grid">
      <article class="metric-card"><span class="metric-icon">□</span><span><small class="metric-label">PRODUCTOS ACTIVOS</small><strong class="metric-value">${data.active_products}</strong><small class="metric-meta">Referencias disponibles</small></span></article>
      <article class="metric-card"><span class="metric-icon teal">▦</span><span><small class="metric-label">UNIDADES EN INVENTARIO</small><strong class="metric-value">${quantity(data.total_inventory_units)}</strong><small class="metric-meta">Suma en todas las ubicaciones</small></span></article>
      <article class="metric-card"><span class="metric-icon amber">!</span><span><small class="metric-label">BAJO STOCK MÍNIMO</small><strong class="metric-value">${data.low_stock_count}</strong><small class="metric-meta">Productos que requieren atención</small></span></article>
    </section>
    <div class="dashboard-grid">
      <div><section class="panel"><div class="panel-header"><div><h3>Movimientos recientes</h3><p>Últimas operaciones registradas</p></div><a class="panel-link" href="#movements">Ver historial →</a></div>
        ${movementRows ? `<div class="table-wrap"><table><thead><tr><th>Producto</th><th>Tipo</th><th>Ruta</th><th class="align-right">Cantidad</th><th class="align-right">Fecha</th></tr></thead><tbody>${movementRows}</tbody></table></div>` : emptyState("⇄", "Sin movimientos", "Registra una entrada para comenzar a construir el historial.")}
      </section></div>
      <div><section class="panel"><div class="panel-header"><div><h3>Stock por ubicación</h3><p>Unidades totales almacenadas</p></div></div>
        ${locationBars ? `<div class="bar-list">${locationBars}</div>` : emptyState("⌖", "Sin ubicaciones", "Agrega un depósito o tienda para operar.")}
      </section>
      <section class="panel"><div class="panel-header"><div><h3>Alertas de stock</h3><p>Comparación con el mínimo global</p></div></div>
        ${lowStockRows ? `<div class="low-stock-list">${lowStockRows}</div>` : emptyState("✓", "Todo en orden", "No hay productos por debajo de su stock mínimo.")}
      </section></div>
    </div>`;
}

async function renderProducts() {
  state.products = await api("/products");
  return `
    <div class="page-heading"><div><h2>Catálogo de productos</h2><p>${state.products.length} referencias registradas.</p></div><button class="button primary" data-new-product>＋ Nuevo producto</button></div>
    <section class="panel"><div class="toolbar"><div class="search-control"><input id="product-search" type="search" placeholder="Buscar por nombre o SKU…"></div>
      <select id="product-status" class="filter-select" aria-label="Filtrar estado"><option value="all">Todos los estados</option><option value="active">Activos</option><option value="inactive">Inactivos</option></select></div>
      <div id="products-table">${productsTable(state.products)}</div></section>`;
}

function productsTable(items) {
  if (!items.length) return emptyState("□", "No hay productos", "Crea el primer producto para comenzar a controlar sus existencias.");
  return `<div class="table-wrap"><table><thead><tr><th>Producto</th><th>Categoría</th><th>Unidad</th><th class="align-right">Stock mínimo</th><th>Estado</th><th class="align-right">Acciones</th></tr></thead><tbody>${items.map((item) => `
    <tr><td><span class="cell-title">${escapeHTML(item.name)}</span><span class="cell-subtitle mono">${escapeHTML(item.sku)}</span></td><td>${escapeHTML(item.category)}</td><td>${escapeHTML(item.unit)}</td>
      <td class="number align-right">${quantity(item.minimum_stock)}</td><td><span class="badge ${item.is_active ? "active" : "inactive"}">${item.is_active ? "Activo" : "Inactivo"}</span></td>
      <td class="align-right"><button class="action-button" data-edit-product="${item.id}">Editar</button>${item.is_active ? `<button class="action-button danger" data-deactivate-product="${item.id}">Desactivar</button>` : ""}</td></tr>`).join("")}</tbody></table></div>`;
}

async function renderLocations() {
  state.locations = await api("/locations");
  return `<div class="page-heading"><div><h2>Ubicaciones</h2><p>Administra cada depósito, tienda o punto de almacenamiento.</p></div><button class="button primary" data-new-location>＋ Nueva ubicación</button></div>
    <section class="panel"><div class="toolbar"><div class="search-control"><input id="location-search" type="search" placeholder="Buscar ubicación…"></div></div>
      <div id="locations-table">${state.locations.length ? locationsTable(state.locations) : emptyState("⌖", "No hay ubicaciones", "Agrega una ubicación para comenzar a recibir stock.")}</div></section>`;
}

function locationsTable(items) {
  if (!items.length) return emptyState("⌖", "Sin coincidencias", "No encontramos ubicaciones con ese texto.");
  return `<div class="table-wrap"><table><thead><tr><th>Ubicación</th><th>Estado</th><th>Creada</th><th class="align-right">Acciones</th></tr></thead><tbody>${items.map((item) => `
    <tr><td><span class="cell-title">${escapeHTML(item.name)}</span><span class="cell-subtitle">${escapeHTML(item.description || "Sin descripción")}</span></td><td><span class="badge ${item.is_active ? "active" : "inactive"}">${item.is_active ? "Activa" : "Inactiva"}</span></td>
      <td><span class="cell-subtitle">${dateTime(item.created_at)}</span></td><td class="align-right"><button class="action-button" data-edit-location="${item.id}">Editar</button>${item.is_active ? `<button class="action-button danger" data-deactivate-location="${item.id}">Desactivar</button>` : ""}</td></tr>`).join("")}</tbody></table></div>`;
}

async function renderInventory() {
  const items = await api("/inventory");
  const rows = items.map((item) => `
    <tr><td><span class="cell-title">${escapeHTML(item.product_name)}</span><span class="cell-subtitle mono">${escapeHTML(item.product_sku)}</span></td><td>${escapeHTML(item.location_name)}</td>
      <td class="number align-right">${quantity(item.quantity)} <span class="cell-subtitle" style="display:inline">${escapeHTML(item.unit)}</span></td><td class="number align-right">${quantity(item.minimum_stock)}</td>
      <td>${item.is_below_minimum ? `<span class="badge low">Stock bajo</span>` : `<span class="badge active">Normal</span>`}</td><td><span class="cell-subtitle">${dateTime(item.updated_at)}</span></td></tr>`).join("");
  return `<div class="page-heading"><div><h2>Existencias actuales</h2><p>El stock se calcula exclusivamente a partir de movimientos.</p></div><button class="button primary" data-new-movement>＋ Registrar movimiento</button></div>
    <section class="panel"><div class="toolbar"><div class="search-control"><input id="inventory-search" type="search" placeholder="Buscar producto o ubicación…"></div><select id="inventory-alert" class="filter-select"><option value="all">Todo el inventario</option><option value="low">Solo stock bajo</option></select></div>
      <div id="inventory-table">${rows ? inventoryTable(items) : emptyState("▦", "Inventario vacío", "Registra una entrada para crear las primeras existencias.")}</div></section>`;
}

function inventoryTable(items) {
  if (!items.length) return emptyState("▦", "Sin coincidencias", "No hay existencias para los filtros seleccionados.");
  return `<div class="table-wrap"><table><thead><tr><th>Producto</th><th>Ubicación</th><th class="align-right">Cantidad</th><th class="align-right">Mínimo</th><th>Estado</th><th>Actualización</th></tr></thead><tbody>${items.map((item) => `
    <tr><td><span class="cell-title">${escapeHTML(item.product_name)}</span><span class="cell-subtitle mono">${escapeHTML(item.product_sku)}</span></td><td>${escapeHTML(item.location_name)}</td><td class="number align-right">${quantity(item.quantity)} <span class="cell-subtitle" style="display:inline">${escapeHTML(item.unit)}</span></td>
      <td class="number align-right">${quantity(item.minimum_stock)}</td><td>${item.is_below_minimum ? `<span class="badge low">Stock bajo</span>` : `<span class="badge active">Normal</span>`}</td><td><span class="cell-subtitle">${dateTime(item.updated_at)}</span></td></tr>`).join("")}</tbody></table></div>`;
}

async function renderMovements() {
  const items = await api("/movements?limit=200");
  return `<div class="page-heading"><div><h2>Historial de movimientos</h2><p>Registro permanente y cronológico de las operaciones.</p></div><button class="button primary" data-new-movement>＋ Registrar movimiento</button></div>
    <section class="panel"><div class="toolbar"><div class="search-control"><input id="movement-search" type="search" placeholder="Buscar producto, SKU o ubicación…"></div><select id="movement-type-filter" class="filter-select"><option value="all">Todos los tipos</option><option value="ENTRY">Entradas</option><option value="EXIT">Salidas</option><option value="TRANSFER">Transferencias</option><option value="ADJUSTMENT">Ajustes</option></select></div>
      <div id="movements-table">${movementsTable(items)}</div></section>`;
}

function movementsTable(items) {
  if (!items.length) return emptyState("⇄", "Sin movimientos", "Registra una operación para iniciar la trazabilidad del inventario.");
  return `<div class="table-wrap"><table><thead><tr><th>Fecha</th><th>Producto</th><th>Tipo</th><th>Origen / destino</th><th class="align-right">Cantidad</th><th>Notas</th></tr></thead><tbody>${items.map((item) => `
    <tr><td><span class="cell-title">${dateTime(item.timestamp)}</span><span class="cell-subtitle">#${item.id}</span></td><td><span class="cell-title">${escapeHTML(item.product_name)}</span><span class="cell-subtitle mono">${escapeHTML(item.product_sku)}</span></td><td>${movementBadge(item.movement_type)}</td>
      <td>${movementRoute(item)}</td><td class="number align-right">${quantity(item.quantity)}</td><td><span class="cell-subtitle">${escapeHTML(item.notes || "—")}</span></td></tr>`).join("")}</tbody></table></div>`;
}

async function navigate() {
  const page = location.hash.slice(1) || "dashboard";
  state.currentPage = pageMeta[page] ? page : "dashboard";
  document.querySelectorAll(".nav-link").forEach((link) => link.classList.toggle("active", link.dataset.page === state.currentPage));
  document.querySelector("#page-title").textContent = pageMeta[state.currentPage][0];
  document.querySelector("#page-subtitle").textContent = pageMeta[state.currentPage][1];
  closeSidebar();
  const main = document.querySelector("#main-content");
  main.innerHTML = loadingState();
  try {
    const renderer = { dashboard: renderDashboard, products: renderProducts, locations: renderLocations, inventory: renderInventory, movements: renderMovements }[state.currentPage];
    main.innerHTML = await renderer();
    bindPageEvents();
  } catch (error) {
    main.innerHTML = `<div class="error-state"><div class="empty-icon">!</div><h3>No pudimos cargar la información</h3><p>${escapeHTML(error.message)}</p><button class="button secondary" id="retry-page">Reintentar</button></div>`;
    document.querySelector("#retry-page")?.addEventListener("click", navigate);
  }
}

function bindPageEvents() {
  document.querySelectorAll("[data-new-product]").forEach((button) => button.addEventListener("click", () => openProductDialog()));
  document.querySelectorAll("[data-new-location]").forEach((button) => button.addEventListener("click", () => openLocationDialog()));
  document.querySelectorAll("[data-new-movement]").forEach((button) => button.addEventListener("click", openMovementDialog));
  bindProductActions();
  bindLocationActions();

  const productFilter = () => {
    const term = document.querySelector("#product-search").value.trim().toLowerCase();
    const status = document.querySelector("#product-status").value;
    const filtered = state.products.filter((item) => (`${item.name} ${item.sku}`.toLowerCase().includes(term)) && (status === "all" || item.is_active === (status === "active")));
    document.querySelector("#products-table").innerHTML = productsTable(filtered);
    bindProductActions();
  };
  document.querySelector("#product-search")?.addEventListener("input", productFilter);
  document.querySelector("#product-status")?.addEventListener("change", productFilter);

  document.querySelector("#location-search")?.addEventListener("input", (event) => {
    const term = event.target.value.toLowerCase();
    document.querySelector("#locations-table").innerHTML = locationsTable(state.locations.filter((item) => `${item.name} ${item.description || ""}`.toLowerCase().includes(term)));
    bindLocationActions();
  });

  if (document.querySelector("#inventory-search")) {
    Promise.resolve(api("/inventory")).then((items) => {
      const apply = () => {
        const term = document.querySelector("#inventory-search").value.toLowerCase();
        const low = document.querySelector("#inventory-alert").value === "low";
        document.querySelector("#inventory-table").innerHTML = inventoryTable(items.filter((item) => `${item.product_name} ${item.product_sku} ${item.location_name}`.toLowerCase().includes(term) && (!low || item.is_below_minimum)));
      };
      document.querySelector("#inventory-search").addEventListener("input", apply);
      document.querySelector("#inventory-alert").addEventListener("change", apply);
    });
  }

  if (document.querySelector("#movement-search")) {
    api("/movements?limit=200").then((items) => {
      const apply = () => {
        const term = document.querySelector("#movement-search").value.toLowerCase();
        const type = document.querySelector("#movement-type-filter").value;
        const filtered = items.filter((item) => `${item.product_name} ${item.product_sku} ${item.source_location_name || ""} ${item.destination_location_name || ""}`.toLowerCase().includes(term) && (type === "all" || item.movement_type === type));
        document.querySelector("#movements-table").innerHTML = movementsTable(filtered);
      };
      document.querySelector("#movement-search").addEventListener("input", apply);
      document.querySelector("#movement-type-filter").addEventListener("change", apply);
    });
  }
}

function bindProductActions() {
  document.querySelectorAll("[data-edit-product]").forEach((button) => button.addEventListener("click", () => openProductDialog(Number(button.dataset.editProduct))));
  document.querySelectorAll("[data-deactivate-product]").forEach((button) => button.addEventListener("click", () => deactivateProduct(Number(button.dataset.deactivateProduct))));
}

function bindLocationActions() {
  document.querySelectorAll("[data-edit-location]").forEach((button) => button.addEventListener("click", () => openLocationDialog(Number(button.dataset.editLocation))));
  document.querySelectorAll("[data-deactivate-location]").forEach((button) => button.addEventListener("click", () => deactivateLocation(Number(button.dataset.deactivateLocation))));
}

function formJSON(form) {
  return Object.fromEntries(new FormData(form).entries());
}

function openProductDialog(id = null) {
  const form = document.querySelector("#product-form");
  form.reset();
  form.elements.is_active.checked = true;
  form.elements.id.value = "";
  document.querySelector("#product-dialog-title").textContent = id ? "Editar producto" : "Nuevo producto";
  if (id) {
    const item = state.products.find((product) => product.id === id);
    if (!item) return;
    Object.entries(item).forEach(([key, value]) => {
      if (!form.elements[key]) return;
      if (form.elements[key].type === "checkbox") form.elements[key].checked = value;
      else form.elements[key].value = value ?? "";
    });
  }
  document.querySelector("#product-dialog").showModal();
}

function openLocationDialog(id = null) {
  const form = document.querySelector("#location-form");
  form.reset(); form.elements.is_active.checked = true; form.elements.id.value = "";
  document.querySelector("#location-dialog-title").textContent = id ? "Editar ubicación" : "Nueva ubicación";
  if (id) {
    const item = state.locations.find((locationItem) => locationItem.id === id);
    if (!item) return;
    form.elements.id.value = item.id; form.elements.name.value = item.name;
    form.elements.description.value = item.description || ""; form.elements.is_active.checked = item.is_active;
  }
  document.querySelector("#location-dialog").showModal();
}

async function openMovementDialog() {
  try {
    await refreshReferences();
    const products = state.products.filter((item) => item.is_active);
    const locations = state.locations.filter((item) => item.is_active);
    if (!products.length || !locations.length) {
      showToast("Necesitas al menos un producto y una ubicación activos.", "error"); return;
    }
    const productOptions = products.map((item) => `<option value="${item.id}">${escapeHTML(item.sku)} · ${escapeHTML(item.name)}</option>`).join("");
    const locationOptions = `<option value="">Seleccionar…</option>${locations.map((item) => `<option value="${item.id}">${escapeHTML(item.name)}</option>`).join("")}`;
    const form = document.querySelector("#movement-form"); form.reset();
    form.elements.product_id.innerHTML = productOptions;
    form.elements.source_location_id.innerHTML = locationOptions;
    form.elements.destination_location_id.innerHTML = locationOptions;
    updateMovementForm();
    document.querySelector("#movement-dialog").showModal();
  } catch (error) { showToast(error.message, "error"); }
}

function updateMovementForm() {
  const form = document.querySelector("#movement-form");
  const type = form.elements.movement_type.value;
  const source = document.querySelector("#source-location-field");
  const destination = document.querySelector("#destination-location-field");
  source.hidden = !["EXIT", "TRANSFER"].includes(type);
  destination.hidden = !["ENTRY", "TRANSFER", "ADJUSTMENT"].includes(type);
  form.elements.source_location_id.required = !source.hidden;
  form.elements.destination_location_id.required = !destination.hidden;
  form.elements.quantity.min = type === "ADJUSTMENT" ? "" : "0.001";
  document.querySelector("#movement-hint").textContent = {
    ENTRY: "La entrada incrementará el stock de la ubicación seleccionada.",
    EXIT: "La salida se rechazará si no existe stock suficiente.",
    TRANSFER: "El descuento en origen y el incremento en destino se guardarán juntos.",
    ADJUSTMENT: "Usa una cantidad positiva para sumar o negativa para descontar stock.",
  }[type];
}

document.querySelector("#movement-form").elements.movement_type.addEventListener("change", updateMovementForm);

document.querySelector("#product-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const form = event.currentTarget; const values = formJSON(form); const id = values.id;
  const payload = { sku: values.sku, name: values.name, description: values.description || null, category: values.category, unit: values.unit, minimum_stock: values.minimum_stock, is_active: form.elements.is_active.checked };
  await submitForm(form, id ? `/products/${id}` : "/products", id ? "PATCH" : "POST", payload, "Producto guardado correctamente.", "product-dialog");
});

document.querySelector("#location-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const form = event.currentTarget; const values = formJSON(form); const id = values.id;
  const payload = { name: values.name, description: values.description || null, is_active: form.elements.is_active.checked };
  await submitForm(form, id ? `/locations/${id}` : "/locations", id ? "PATCH" : "POST", payload, "Ubicación guardada correctamente.", "location-dialog");
});

document.querySelector("#movement-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const form = event.currentTarget; const values = formJSON(form);
  const payload = { movement_type: values.movement_type, product_id: Number(values.product_id), quantity: values.quantity, source_location_id: values.source_location_id ? Number(values.source_location_id) : null, destination_location_id: values.destination_location_id ? Number(values.destination_location_id) : null, notes: values.notes || null };
  await submitForm(form, "/movements", "POST", payload, "Movimiento registrado correctamente.", "movement-dialog");
});

async function submitForm(form, path, method, payload, successMessage, dialogId) {
  const submit = form.querySelector('[type="submit"]'); submit.disabled = true;
  try {
    await api(path, { method, body: JSON.stringify(payload) });
    document.querySelector(`#${dialogId}`).close(); showToast(successMessage); await navigate();
  } catch (error) { showToast(error.message, "error"); }
  finally { submit.disabled = false; }
}

async function deactivateProduct(id) {
  const item = state.products.find((product) => product.id === id);
  if (!confirm(`¿Desactivar el producto “${item?.name || "seleccionado"}”? Su historial se conservará.`)) return;
  try { await api(`/products/${id}`, { method: "DELETE" }); showToast("Producto desactivado. El historial permanece intacto."); await navigate(); } catch (error) { showToast(error.message, "error"); }
}

async function deactivateLocation(id) {
  const item = state.locations.find((locationItem) => locationItem.id === id);
  if (!confirm(`¿Desactivar la ubicación “${item?.name || "seleccionada"}”?`)) return;
  try { await api(`/locations/${id}`, { method: "DELETE" }); showToast("Ubicación desactivada correctamente."); await navigate(); } catch (error) { showToast(error.message, "error"); }
}

document.querySelectorAll("[data-close]").forEach((button) => button.addEventListener("click", () => document.querySelector(`#${button.dataset.close}`).close()));
document.querySelectorAll("dialog").forEach((dialog) => dialog.addEventListener("click", (event) => { if (event.target === dialog) dialog.close(); }));

function closeSidebar() { document.querySelector("#sidebar").classList.remove("open"); document.querySelector("#sidebar-overlay").classList.remove("open"); }
document.querySelector("#menu-button").addEventListener("click", () => { document.querySelector("#sidebar").classList.add("open"); document.querySelector("#sidebar-overlay").classList.add("open"); });
document.querySelector("#sidebar-overlay").addEventListener("click", closeSidebar);
window.addEventListener("hashchange", navigate);
window.addEventListener("DOMContentLoaded", navigate);
