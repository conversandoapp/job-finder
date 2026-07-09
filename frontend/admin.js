async function init() {
  const who = await JFAuth.requireAdmin();
  if (!who) return; // requireAdmin ya redirige o muestra "acceso denegado"
  JFAuth.renderUserBar("user-bar", "/admin-login");
  loadRequests();
  setInterval(() => loadRequests(false), 15000);
}

document.querySelectorAll(".tab-btn").forEach(btn => {
  btn.addEventListener("click", () => {
    document.querySelectorAll(".tab-btn").forEach(b => b.classList.remove("active"));
    btn.classList.add("active");
    document.getElementById("tab-requests").style.display = btn.dataset.tab === "requests" ? "block" : "none";
    document.getElementById("tab-notifications").style.display = btn.dataset.tab === "notifications" ? "block" : "none";
    if (btn.dataset.tab === "notifications") loadNotifications();
  });
});

const STATUS_LABEL = {
  pending: "⏳ Pendiente",
  ready: "✅ Listo",
  error: "❌ Error",
  not_requested: "— No pedido",
};

function statusPill(status) {
  return `<span class="pill-status ${status}">${STATUS_LABEL[status] || status}</span>`;
}

function hasUnsavedInput() {
  const listEl = document.getElementById("requests-list");
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
  const active = document.activeElement;
  return !!(active && listEl.contains(active) && (active.tagName === "INPUT" || active.tagName === "TEXTAREA"));
}

async function loadRequests(force = false) {
  if (!force && hasUnsavedInput()) {
    return; // no pisamos lo que el admin está llenando en algún formulario
  }
  const res = await JFAuth.authFetch("/api/admin/requests");
  const requests = await res.json();
  const listEl = document.getElementById("requests-list");
  listEl.innerHTML = "";

  if (!requests.length) {
    listEl.innerHTML = "<div class='card'>Todavía no hay solicitudes. Cuando alguien suba un CV aparecerá aquí.</div>";
    return;
  }

  const template = document.getElementById("request-card-template");

  requests.forEach(req => {
    const node = template.content.cloneNode(true);
    const cardEl = node.querySelector(".request-card");
    cardEl.id = req.session_id;

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
    if (req.cv_status === "ready") {
      cvFormWrap.classList.add("done");
      cvForm.querySelector("button[type=submit]").textContent = "Ya subido — volver a subir";
      deleteCvBtn.style.display = "";
    }
    cvForm.addEventListener("submit", (e) => handleCvUpload(e, req.session_id, req.cv_status === "ready"));
    deleteCvBtn.addEventListener("click", () => handleDeleteCv(req.session_id));

    const vacFormWrap = node.querySelector(".req-vacantes-form");
    const vacForm = node.querySelector(".vacantes-upload-form");
    const deleteVacantesBtn = node.querySelector(".btn-delete-vacantes");
    if (req.jobs_status === "not_requested") {
      const notice = document.createElement("p");
      notice.className = "subtitle";
      notice.style.marginBottom = "8px";
      notice.textContent = "El usuario todavía no pidió buscar vacantes — puedes subirlo igual si quieres adelantarlo o probar cómo se ve.";
      vacFormWrap.insertBefore(notice, vacForm);
    } else if (req.jobs_status === "ready") {
      vacFormWrap.classList.add("done");
      vacForm.querySelector("button[type=submit]").textContent = "Ya subido — volver a subir";
      deleteVacantesBtn.style.display = "";
    }
    vacForm.addEventListener("submit", (e) => handleVacantesUpload(e, req.session_id, req.jobs_status === "ready"));
    deleteVacantesBtn.addEventListener("click", () => handleDeleteVacantes(req.session_id));

    listEl.appendChild(node);
  });

  if (window.location.hash) {
    const target = document.getElementById(window.location.hash.slice(1));
    if (target) target.scrollIntoView({ behavior: "smooth" });
  }
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
  fd.append("scores_file", form.scores_file.files[0]);

  try {
    const res = await JFAuth.authFetch(`/api/admin/${sessionId}/cv`, { method: "POST", body: fd });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || "Error al subir");
    }
    msgEl.textContent = "✅ Subido. El usuario ya puede ver su resultado.";
    msgEl.className = "form-msg ok";
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

init();
