async function init() {
  const who = await JFAuth.requireAdmin();
  if (!who) return; // requireAdmin ya redirige o muestra "acceso denegado"
  JFAuth.renderUserBar("user-bar", "/admin-login");
  loadRequests();
  setInterval(() => loadRequests(false), 15000);
}

// Fichas expandidas por el admin (colapsadas por defecto). Se mantiene en
// memoria para que no se cierren solas en cada auto-refresh de 15s.
const expandedIds = new Set();

function applyCollapseBehavior(cardEl, sessionId) {
  if (!expandedIds.has(sessionId)) {
    cardEl.classList.add("collapsed");
  }
  cardEl.querySelector(".req-header").addEventListener("click", () => {
    cardEl.classList.toggle("collapsed");
    if (cardEl.classList.contains("collapsed")) {
      expandedIds.delete(sessionId);
    } else {
      expandedIds.add(sessionId);
    }
  });
}

document.querySelectorAll(".tab-btn").forEach(btn => {
  btn.addEventListener("click", () => {
    document.querySelectorAll(".tab-btn").forEach(b => b.classList.remove("active"));
    btn.classList.add("active");
    document.getElementById("tab-requests").style.display = btn.dataset.tab === "requests" ? "block" : "none";
    document.getElementById("tab-past").style.display = btn.dataset.tab === "past" ? "block" : "none";
    document.getElementById("tab-notifications").style.display = btn.dataset.tab === "notifications" ? "block" : "none";
    document.getElementById("tab-users").style.display = btn.dataset.tab === "users" ? "block" : "none";
    if (btn.dataset.tab === "notifications") loadNotifications();
    if (btn.dataset.tab === "users") loadUsers();
  });
});

const STATUS_LABEL = {
  pending: "⏳ Pendiente",
  pending_review: "🕵️ En revisión",
  ready: "✅ Listo",
  error: "❌ Error",
  not_requested: "— No pedido",
};

function statusPill(status) {
  return `<span class="pill-status ${status}">${STATUS_LABEL[status] || status}</span>`;
}

function hasUnsavedInput() {
  const listEls = [document.getElementById("requests-list"), document.getElementById("past-requests-list")];
  const active = document.activeElement;
  for (const listEl of listEls) {
    const fields = listEl.querySelectorAll(".cv-upload-form input, .cv-upload-form textarea, .vacantes-upload-form input");
    for (const el of fields) {
      if (el.type === "file") {
        if (el.files && el.files.length) return true;
      } else if (el.value && el.value.trim() !== "") {
        return true;
      }
    }
    // También pausamos si el foco está en algún campo (por si el navegador
    // no reporta el value todavía, ej. justo al empezar a tipear).
    if (active && listEl.contains(active) && (active.tagName === "INPUT" || active.tagName === "TEXTAREA")) {
      return true;
    }
  }
  return false;
}

function isCompletedRequest(req) {
  return req.cv_status === "ready" && req.jobs_status === "ready";
}

async function loadRequests(force = false) {
  if (!force && hasUnsavedInput()) {
    return; // no pisamos lo que el admin está llenando en algún formulario
  }
  const res = await JFAuth.authFetch("/api/admin/requests");
  const requests = await res.json();

  if (window.location.hash) {
    expandedIds.add(window.location.hash.slice(1));
  }

  const pendingListEl = document.getElementById("requests-list");
  const pastListEl = document.getElementById("past-requests-list");
  pendingListEl.innerHTML = "";
  pastListEl.innerHTML = "";

  const pending = requests.filter(req => !isCompletedRequest(req));
  const past = requests.filter(isCompletedRequest);

  if (!pending.length) {
    pendingListEl.innerHTML = "<div class='card'>No hay solicitudes pendientes. Cuando alguien suba un CV o pida vacantes aparecerá aquí.</div>";
  } else {
    pending.forEach(req => pendingListEl.appendChild(buildRequestCard(req)));
  }

  if (!past.length) {
    pastListEl.innerHTML = "<div class='card'>Todavía no hay solicitudes completadas.</div>";
  } else {
    past.forEach(req => pastListEl.appendChild(buildRequestCard(req)));
  }

  if (window.location.hash) {
    const target = document.getElementById(window.location.hash.slice(1));
    if (target) target.scrollIntoView({ behavior: "smooth" });
  }
}

function buildRequestCard(req) {
  const template = document.getElementById("request-card-template");
  const node = template.content.cloneNode(true);
  const cardEl = node.querySelector(".request-card");
  cardEl.id = req.session_id;
  applyCollapseBehavior(cardEl, req.session_id);

  node.querySelector(".req-name").textContent = req.candidate_name || "(sin nombre)";
  node.querySelector(".req-meta").textContent =
    `${req.session_id} · ${req.pais || ""} · creado ${formatDate(req.created_at)}`;

  node.querySelector(".req-status-pills").innerHTML =
    `CV: ${statusPill(req.cv_status)}  Vacantes: ${statusPill(req.jobs_status)}`;

  const linksEl = node.querySelector(".req-links");
  let linksHtml = `<a href="#" class="download-original">📄 Descargar CV original</a>`;
  if (req.cv_zip_path) {
    linksHtml += ` <a href="#" class="download-zip">📦 Descargar CV + puestos (.zip)</a>`;
  }
  if (req.cv_drive_link) {
    linksHtml += ` <a href="${req.cv_drive_link}" target="_blank">☁️ Ver en Drive</a>`;
  }
  if (req.linkedin_url) {
    linksHtml += ` <a href="${req.linkedin_url}" target="_blank">🔗 LinkedIn del candidato</a>`;
  }
  if (req.user_email) {
    linksHtml += ` <span style="color:#5b6b76;">👤 ${req.user_email}</span>`;
  }
  if (req.cv_status === "ready") {
    linksHtml += ` <a href="/resultado.html?session=${req.session_id}" target="_blank">👁️ Ver análisis de CV</a>`;
  }
  if (req.jobs_status === "ready") {
    linksHtml += ` <a href="/vacantes.html?session=${req.session_id}" target="_blank">👁️ Ver vacantes</a>`;
  }
  linksEl.innerHTML = linksHtml;
  linksEl.querySelector(".download-original").addEventListener("click", (ev) => {
    ev.preventDefault();
    downloadOriginal(req.session_id);
  });
  const zipLink = linksEl.querySelector(".download-zip");
  if (zipLink) {
    zipLink.addEventListener("click", (ev) => {
      ev.preventDefault();
      downloadZip(req.session_id);
    });
  }

  const rolesElegidosEl = node.querySelector(".req-roles-elegidos");
  if (req.roles_modo === "candidato" && (req.roles_elegidos || []).length) {
    const items = req.roles_elegidos.map((r, i) => `${i + 1}. ${r}`).join(" · ");
    rolesElegidosEl.innerHTML = `<p class="subtitle" style="margin:0 0 10px;">🎯 <strong>Puestos elegidos por el candidato</strong> (prioridad): ${items}</p>`;
  } else if (req.roles_modo === "admin") {
    rolesElegidosEl.innerHTML = `<p class="subtitle" style="margin:0 0 10px;">🎯 El candidato prefiere que elijamos el puesto según su CV.</p>`;
  } else {
    rolesElegidosEl.innerHTML = "";
  }

  const rolesWrap = node.querySelector(".req-roles-sugeridos");
  const rolesListEl = node.querySelector(".roles-sugeridos-list");
  const rolesSugeridos = req.roles_sugeridos || [];
  if (!rolesSugeridos.length) {
    rolesWrap.style.display = "none";
  } else {
    rolesSugeridos.forEach(r => {
      const div = document.createElement("div");
      div.className = "role-card";
      const kws = (r.keywords_encontrados || []).join(", ");
      div.innerHTML = `
        <div>
          <div class="title">${r.titulo}</div>
          ${kws ? `<div class="just">Coincidencias: ${kws}</div>` : ""}
        </div>
        <span class="badge blue">${r.match_porcentaje}% match</span>
      `;
      rolesListEl.appendChild(div);
    });
  }

  const cvFormWrap = node.querySelector(".req-cv-form");
  const cvForm = node.querySelector(".cv-upload-form");
  const deleteCvBtn = node.querySelector(".btn-delete-cv");
  if (req.cv_status === "pending_review") {
    const notice = document.createElement("p");
    notice.className = "subtitle";
    notice.style.marginBottom = "8px";
    notice.textContent = "✅ Enviado — esperando aprobación de backoffice.";
    cvFormWrap.insertBefore(notice, cvForm);
  } else if (req.cv_review_note) {
    const notice = document.createElement("p");
    notice.className = "subtitle";
    notice.style.marginBottom = "8px";
    notice.style.color = "#b8511a";
    notice.textContent = `⚠️ Rechazado por backoffice: ${req.cv_review_note}`;
    cvFormWrap.insertBefore(notice, cvForm);
  }
  if (req.cv_status === "ready" || req.cv_status === "pending_review") {
    cvFormWrap.classList.add("done");
    cvForm.querySelector("button[type=submit]").textContent = "Ya subido — volver a subir";
    deleteCvBtn.style.display = "";
  }
  const cvIsReplace = req.cv_status === "ready" || req.cv_status === "pending_review";
  cvForm.addEventListener("submit", (e) => handleCvUpload(e, req.session_id, cvIsReplace));
  deleteCvBtn.addEventListener("click", () => handleDeleteCv(req.session_id));

  const cvSeparateModal = node.querySelector(".cv-separate-modal");
  const cvSeparateForm = node.querySelector(".cv-upload-separate-form");
  node.querySelector(".cv-separate-open").addEventListener("click", () => { cvSeparateModal.hidden = false; });
  node.querySelector(".cv-separate-close").addEventListener("click", () => { cvSeparateModal.hidden = true; });
  cvSeparateModal.addEventListener("click", (e) => { if (e.target === cvSeparateModal) cvSeparateModal.hidden = true; });
  cvSeparateForm.addEventListener("submit", (e) => handleCvUpload(e, req.session_id, cvIsReplace));

  const vacFormWrap = node.querySelector(".req-vacantes-form");
  const vacForm = node.querySelector(".vacantes-upload-form");
  const deleteVacantesBtn = node.querySelector(".btn-delete-vacantes");
  if (req.jobs_status === "not_requested") {
    const notice = document.createElement("p");
    notice.className = "subtitle";
    notice.style.marginBottom = "8px";
    notice.textContent = "El usuario todavía no pidió buscar vacantes — puedes subirlo igual si quieres adelantarlo o probar cómo se ve.";
    vacFormWrap.insertBefore(notice, vacForm);
  } else if (req.jobs_status === "pending_review") {
    const notice = document.createElement("p");
    notice.className = "subtitle";
    notice.style.marginBottom = "8px";
    notice.textContent = "✅ Enviado — esperando aprobación de backoffice.";
    vacFormWrap.insertBefore(notice, vacForm);
  } else if (req.jobs_review_note) {
    const notice = document.createElement("p");
    notice.className = "subtitle";
    notice.style.marginBottom = "8px";
    notice.style.color = "#b8511a";
    notice.textContent = `⚠️ Rechazado por backoffice: ${req.jobs_review_note}`;
    vacFormWrap.insertBefore(notice, vacForm);
  }
  if (req.jobs_status === "ready" || req.jobs_status === "pending_review") {
    vacFormWrap.classList.add("done");
    vacForm.querySelector("button[type=submit]").textContent = "Ya subido — volver a subir";
    deleteVacantesBtn.style.display = "";
  }
  const vacIsReplace = req.jobs_status === "ready" || req.jobs_status === "pending_review";
  vacForm.addEventListener("submit", (e) => handleVacantesUpload(e, req.session_id, vacIsReplace));
  deleteVacantesBtn.addEventListener("click", () => handleDeleteVacantes(req.session_id));

  return node;
}

function formatDate(iso) {
  if (!iso) return "";
  try { return new Date(iso).toLocaleString(); } catch { return iso; }
}

async function downloadOriginal(sessionId) {
  try {
    const res = await JFAuth.authFetch(`/api/admin/download/original/${sessionId}`);
    if (!res.ok) throw new Error("No se pudo descargar el CV original");
    const blob = await res.blob();
    const disposition = res.headers.get("content-disposition") || "";
    const match = disposition.match(/filename="?([^"]+)"?/);
    const filename = match ? match[1] : "cv_original";

    const url = window.URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    a.remove();
    window.URL.revokeObjectURL(url);
  } catch (err) {
    alert(err.message);
  }
}

async function downloadZip(sessionId) {
  try {
    const res = await JFAuth.authFetch(`/api/admin/download/zip/${sessionId}`);
    if (!res.ok) throw new Error("No se pudo descargar el paquete CV + puestos");
    const blob = await res.blob();
    const disposition = res.headers.get("content-disposition") || "";
    const match = disposition.match(/filename="?([^"]+)"?/);
    const filename = match ? match[1] : "postulacion.zip";

    const url = window.URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    a.remove();
    window.URL.revokeObjectURL(url);
  } catch (err) {
    alert(err.message);
  }
}

async function handleCvUpload(e, sessionId, isReplace) {
  e.preventDefault();
  if (isReplace && !confirm("Esto reemplazará el análisis de CV actual de este candidato. ¿Continuar?")) {
    return;
  }
  const form = e.target;
  const msgEl = form.querySelector(".form-msg");
  msgEl.textContent = "";
  msgEl.className = "form-msg";

  const fd = new FormData();
  fd.append("file", form.file.files[0]);
  if (form.scores_file && form.scores_file.files[0]) {
    fd.append("scores_file", form.scores_file.files[0]);
  }

  try {
    const res = await JFAuth.authFetch(`/api/admin/${sessionId}/cv`, { method: "POST", body: fd });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || "Error al subir");
    }
    msgEl.textContent = "✅ Subido. El usuario ya puede ver su resultado.";
    msgEl.className = "form-msg ok";
    const modal = form.closest(".cv-separate-modal");
    if (modal) modal.hidden = true;
    setTimeout(() => loadRequests(true), 1200);
  } catch (err) {
    msgEl.textContent = "❌ " + err.message;
    msgEl.className = "form-msg err";
  }
}

async function handleVacantesUpload(e, sessionId, isReplace) {
  e.preventDefault();
  if (isReplace && !confirm("Esto reemplazará las vacantes actuales de este candidato. ¿Continuar?")) {
    return;
  }
  const form = e.target;
  const msgEl = form.querySelector(".form-msg");
  msgEl.textContent = "";
  msgEl.className = "form-msg";

  const fd = new FormData();
  fd.append("file", form.file.files[0]);

  try {
    const res = await JFAuth.authFetch(`/api/admin/${sessionId}/vacantes`, { method: "POST", body: fd });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || "Error al subir");
    }
    msgEl.textContent = "✅ Subido. El usuario ya puede ver sus vacantes.";
    msgEl.className = "form-msg ok";
    setTimeout(() => loadRequests(true), 1200);
  } catch (err) {
    msgEl.textContent = "❌ " + err.message;
    msgEl.className = "form-msg err";
  }
}

async function handleDeleteCv(sessionId) {
  if (!confirm("¿Borrar el análisis de CV de este candidato? Esta acción no se puede deshacer.")) {
    return;
  }
  try {
    const res = await JFAuth.authFetch(`/api/admin/${sessionId}/cv`, { method: "DELETE" });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || "Error al borrar");
    }
    loadRequests(true);
  } catch (err) {
    alert("❌ " + err.message);
  }
}

async function handleDeleteVacantes(sessionId) {
  if (!confirm("¿Borrar las vacantes de este candidato? Esta acción no se puede deshacer.")) {
    return;
  }
  try {
    const res = await JFAuth.authFetch(`/api/admin/${sessionId}/vacantes`, { method: "DELETE" });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || "Error al borrar");
    }
    loadRequests(true);
  } catch (err) {
    alert("❌ " + err.message);
  }
}

async function loadNotifications() {
  const res = await JFAuth.authFetch("/api/admin/notifications");
  const notifs = await res.json();
  const listEl = document.getElementById("notifications-list");
  if (!notifs.length) {
    listEl.innerHTML = "<div class='card'>Todavía no hay notificaciones.</div>";
    return;
  }
  listEl.innerHTML = notifs.map(n => `
    <div class="notif-item">
      <div class="subj">${n.subject}</div>
      <div class="ts">${formatDate(n.ts)}</div>
      <pre>${n.body}</pre>
    </div>
  `).join("");
}

document.getElementById("refresh-btn").addEventListener("click", () => loadRequests(true));
document.getElementById("refresh-past-btn").addEventListener("click", () => loadRequests(true));

document.getElementById("connect-drive-btn").addEventListener("click", async () => {
  try {
    const res = await JFAuth.authFetch("/api/admin/drive/authorize");
    if (!res.ok) throw new Error((await res.json()).detail || "No se pudo conectar Drive");
    const { authorize_url } = await res.json();
    window.location.href = authorize_url;
  } catch (err) {
    alert("❌ " + err.message);
  }
});

// ---------------------------------------------------------------------------
// Pestaña "Usuarios": rol de cada usuario y asignación a backoffice.
// ---------------------------------------------------------------------------

const ROLE_LABEL = { usuario: "Usuario", backoffice: "Backoffice", admin: "Admin" };

async function loadUsers() {
  const [usersRes] = await Promise.all([
    JFAuth.authFetch("/api/admin/users"),
    loadAssignmentDropdowns(),
  ]);
  const users = await usersRes.json();
  renderUsersTable(users);
}

function renderUsersTable(users) {
  const listEl = document.getElementById("users-list");
  if (!users.length) {
    listEl.innerHTML = "<div class='card'>Todavía no hay usuarios con solicitudes creadas.</div>";
    return;
  }

  const table = document.createElement("table");
  table.className = "users-table";
  table.innerHTML = `
    <thead>
      <tr>
        <th>Usuario</th>
        <th>Rol</th>
        <th>Backoffice asignado</th>
        <th></th>
      </tr>
    </thead>
    <tbody></tbody>
  `;
  const tbody = table.querySelector("tbody");

  users.forEach(u => {
    const tr = document.createElement("tr");

    const nameTd = document.createElement("td");
    const nameDiv = document.createElement("div");
    nameDiv.textContent = u.candidate_name || "(sin nombre)";
    nameDiv.style.fontWeight = "600";
    const emailDiv = document.createElement("div");
    emailDiv.textContent = u.email || "";
    emailDiv.className = "req-meta";
    nameTd.appendChild(nameDiv);
    nameTd.appendChild(emailDiv);
    tr.appendChild(nameTd);

    const roleTd = document.createElement("td");
    const roleSelect = document.createElement("select");
    ["usuario", "backoffice", "admin"].forEach(role => {
      const opt = document.createElement("option");
      opt.value = role;
      opt.textContent = ROLE_LABEL[role];
      if (role === u.role) opt.selected = true;
      roleSelect.appendChild(opt);
    });
    if (u.is_permanent_admin) {
      roleSelect.disabled = true;
      roleSelect.title = "Admin permanente (ADMIN_EMAIL) — no se puede cambiar desde acá.";
    } else {
      roleSelect.addEventListener("change", () => handleRoleChange(u, roleSelect));
    }
    roleTd.appendChild(roleSelect);
    tr.appendChild(roleTd);

    const assignedTd = document.createElement("td");
    assignedTd.textContent = u.backoffice_email || "— Sin asignar (directo con admin)";
    tr.appendChild(assignedTd);

    const actionsTd = document.createElement("td");
    if (u.backoffice_user_id) {
      const unassignBtn = document.createElement("button");
      unassignBtn.type = "button";
      unassignBtn.className = "btn-link";
      unassignBtn.textContent = "Quitar asignación";
      if (u.has_pending_process) {
        unassignBtn.disabled = true;
        unassignBtn.title = "Tiene un proceso en revisión pendiente; no se puede quitar la asignación todavía.";
      } else {
        unassignBtn.addEventListener("click", () => handleUnassign(u));
      }
      actionsTd.appendChild(unassignBtn);
    }
    tr.appendChild(actionsTd);

    tbody.appendChild(tr);
  });

  listEl.innerHTML = "";
  listEl.appendChild(table);
}

async function handleRoleChange(user, selectEl) {
  const newRole = selectEl.value;
  const previousRole = user.role;
  try {
    const res = await JFAuth.authFetch(`/api/admin/users/${user.user_id}/role`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ role: newRole, email: user.email }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || "No se pudo cambiar el rol");
    }
    loadUsers();
  } catch (err) {
    alert("❌ " + err.message);
    selectEl.value = previousRole;
  }
}

async function handleUnassign(user) {
  if (!confirm(`¿Quitar la asignación de backoffice de ${user.email}?`)) return;
  try {
    const res = await JFAuth.authFetch(`/api/admin/assignments/${user.user_id}`, { method: "DELETE" });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || "No se pudo quitar la asignación");
    }
    loadUsers();
  } catch (err) {
    alert("❌ " + err.message);
  }
}

async function loadAssignmentDropdowns() {
  const [backofficeRes, unassignedRes] = await Promise.all([
    JFAuth.authFetch("/api/admin/backoffice-users"),
    JFAuth.authFetch("/api/admin/unassigned-users"),
  ]);
  const backofficeUsers = await backofficeRes.json();
  const unassignedUsers = await unassignedRes.json();

  const backofficeSelect = document.getElementById("assign-backoffice-select");
  const userSelect = document.getElementById("assign-user-select");

  backofficeSelect.innerHTML = '<option value="">Elige un backoffice…</option>';
  backofficeUsers.forEach(u => {
    const opt = document.createElement("option");
    opt.value = u.user_id;
    opt.textContent = `${u.candidate_name || u.email} (${u.email})`;
    backofficeSelect.appendChild(opt);
  });

  userSelect.innerHTML = '<option value="">Elige un usuario…</option>';
  unassignedUsers.forEach(u => {
    const opt = document.createElement("option");
    opt.value = u.user_id;
    opt.textContent = `${u.candidate_name || u.email} (${u.email})`;
    userSelect.appendChild(opt);
  });
}

document.getElementById("assign-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const msgEl = document.getElementById("assign-form-msg");
  msgEl.textContent = "";
  msgEl.className = "form-msg";

  const backofficeUserId = document.getElementById("assign-backoffice-select").value;
  const userId = document.getElementById("assign-user-select").value;

  try {
    const res = await JFAuth.authFetch("/api/admin/assignments", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ user_id: userId, backoffice_user_id: backofficeUserId }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || "No se pudo asignar");
    }
    msgEl.textContent = "✅ Asignado.";
    msgEl.className = "form-msg ok";
    document.getElementById("assign-form").reset();
    loadUsers();
  } catch (err) {
    msgEl.textContent = "❌ " + err.message;
    msgEl.className = "form-msg err";
  }
});

init();
