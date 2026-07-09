async function init() {
  const who = await JFAuth.requireBackoffice();
  if (!who) return; // requireBackoffice ya redirige o muestra "acceso denegado"
  JFAuth.renderUserBar("user-bar", "/backoffice-login");
  loadAll();
  setInterval(() => loadAll(false), 15000);
}

// Fichas expandidas (colapsadas por defecto). Se mantiene en memoria para
// que no se cierren solas en cada auto-refresh de 15s. Compartido entre
// "Por revisar" y "Todas las solicitudes" (misma sesión = mismo estado).
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
    document.getElementById("tab-review").style.display = btn.dataset.tab === "review" ? "block" : "none";
    document.getElementById("tab-all").style.display = btn.dataset.tab === "all" ? "block" : "none";
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

function formatDate(iso) {
  if (!iso) return "";
  try { return new Date(iso).toLocaleString(); } catch { return iso; }
}

function hasUnsavedInput() {
  const listEl = document.getElementById("review-list");
  const fields = listEl.querySelectorAll(
    ".cv-reject-form textarea, .cv-replace-form input, .jobs-reject-form textarea, .jobs-replace-form input"
  );
  for (const el of fields) {
    if (el.type === "file") {
      if (el.files && el.files.length) return true;
    } else if (el.value && el.value.trim() !== "") {
      return true;
    }
  }
  const active = document.activeElement;
  return !!(active && listEl.contains(active) && (active.tagName === "INPUT" || active.tagName === "TEXTAREA"));
}

async function loadAll(force = false) {
  if (!force && hasUnsavedInput()) {
    return; // no pisamos una nota o archivo a medio cargar
  }
  const res = await JFAuth.authFetch("/api/backoffice/requests");
  const requests = await res.json();

  if (window.location.hash) {
    expandedIds.add(window.location.hash.slice(1));
  }

  const reviewListEl = document.getElementById("review-list");
  const allListEl = document.getElementById("all-list");
  reviewListEl.innerHTML = "";
  allListEl.innerHTML = "";

  const needsReview = (req) => req.cv_status === "pending_review" || req.jobs_status === "pending_review";
  const review = requests.filter(needsReview);

  if (!review.length) {
    reviewListEl.innerHTML = "<div class='card'>No hay nada esperando revisión por ahora.</div>";
  } else {
    review.forEach(req => reviewListEl.appendChild(buildReviewCard(req)));
  }

  if (!requests.length) {
    allListEl.innerHTML = "<div class='card'>Todavía no hay solicitudes.</div>";
  } else {
    requests.forEach(req => allListEl.appendChild(buildReadonlyCard(req)));
  }

  if (window.location.hash) {
    const target = document.getElementById(window.location.hash.slice(1));
    if (target) target.scrollIntoView({ behavior: "smooth" });
  }
}

function buildLinksHtml(req) {
  let linksHtml = "";
  if (req.cv_drive_link) {
    linksHtml += `<a href="${req.cv_drive_link}" target="_blank">☁️ Ver en Drive</a> `;
  }
  if (req.linkedin_url) {
    linksHtml += `<a href="${req.linkedin_url}" target="_blank">🔗 LinkedIn del candidato</a> `;
  }
  if (req.user_email) {
    linksHtml += `<span style="color:#5b6b76;">👤 ${req.user_email}</span> `;
  }
  if (req.cv_status === "ready" || req.cv_status === "pending_review") {
    linksHtml += `<a href="/resultado.html?session=${req.session_id}" target="_blank">👁️ Ver CV / análisis</a> `;
  }
  if (req.jobs_status === "ready" || req.jobs_status === "pending_review") {
    linksHtml += `<a href="/vacantes.html?session=${req.session_id}" target="_blank">👁️ Ver vacantes</a> `;
  }
  return linksHtml;
}

function fillHeader(node, req) {
  node.querySelector(".req-name").textContent = req.candidate_name || "(sin nombre)";
  node.querySelector(".req-meta").textContent =
    `${req.session_id} · ${req.pais || ""} · creado ${formatDate(req.created_at)}`;
  node.querySelector(".req-status-pills").innerHTML =
    `CV: ${statusPill(req.cv_status)}  Vacantes: ${statusPill(req.jobs_status)}`;
  node.querySelector(".req-links").innerHTML = buildLinksHtml(req);
}

function buildReviewCard(req) {
  const template = document.getElementById("review-card-template");
  const node = template.content.cloneNode(true);
  const cardEl = node.querySelector(".request-card");
  cardEl.id = req.session_id;
  fillHeader(node, req);
  applyCollapseBehavior(cardEl, req.session_id);

  const cvBlock = node.querySelector(".req-cv-review");
  if (req.cv_status === "pending_review") {
    cvBlock.style.display = "block";
    wireReviewBlock(cvBlock, req, "cv", "cv");
  }

  const jobsBlock = node.querySelector(".req-jobs-review");
  if (req.jobs_status === "pending_review") {
    jobsBlock.style.display = "block";
    wireReviewBlock(jobsBlock, req, "jobs", "vacantes");
  }

  return node;
}

function buildReadonlyCard(req) {
  const template = document.getElementById("readonly-card-template");
  const node = template.content.cloneNode(true);
  const cardEl = node.querySelector(".request-card");
  cardEl.id = `all-${req.session_id}`;
  fillHeader(node, req);
  applyCollapseBehavior(cardEl, req.session_id);
  return node;
}

function wireReviewBlock(block, req, cssPrefix, apiPath) {
  const approveBtn = block.querySelector(`.${cssPrefix}-approve-btn`);
  const rejectToggleBtn = block.querySelector(`.${cssPrefix}-reject-toggle-btn`);
  const replaceToggleBtn = block.querySelector(`.${cssPrefix}-replace-toggle-btn`);
  const rejectForm = block.querySelector(`.${cssPrefix}-reject-form`);
  const replaceForm = block.querySelector(`.${cssPrefix}-replace-form`);
  const label = apiPath === "cv" ? "el CV" : "las vacantes";

  approveBtn.addEventListener("click", async () => {
    if (!confirm(`¿Aprobar ${label}? El candidato podrá verlo de inmediato.`)) return;
    approveBtn.disabled = true;
    try {
      const res = await JFAuth.authFetch(`/api/backoffice/${req.session_id}/${apiPath}/approve`, { method: "POST" });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || "Error al aprobar");
      }
      loadAll(true);
    } catch (err) {
      alert("❌ " + err.message);
      approveBtn.disabled = false;
    }
  });

  rejectToggleBtn.addEventListener("click", () => {
    replaceForm.style.display = "none";
    rejectForm.style.display = rejectForm.style.display === "none" ? "block" : "none";
  });
  replaceToggleBtn.addEventListener("click", () => {
    rejectForm.style.display = "none";
    replaceForm.style.display = replaceForm.style.display === "none" ? "block" : "none";
  });

  rejectForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    const msgEl = rejectForm.querySelector(".form-msg");
    msgEl.textContent = "";
    msgEl.className = "form-msg";
    const fd = new FormData();
    fd.append("note", rejectForm.note.value);
    try {
      const res = await JFAuth.authFetch(`/api/backoffice/${req.session_id}/${apiPath}/reject`, { method: "POST", body: fd });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || "Error al rechazar");
      }
      msgEl.textContent = "✅ Rechazado.";
      msgEl.className = "form-msg ok";
      setTimeout(() => loadAll(true), 800);
    } catch (err) {
      msgEl.textContent = "❌ " + err.message;
      msgEl.className = "form-msg err";
    }
  });

  replaceForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    if (!confirm(`Esto reemplaza ${label} del admin con lo tuyo y lo aprueba directo. ¿Continuar?`)) return;
    const msgEl = replaceForm.querySelector(".form-msg");
    msgEl.textContent = "";
    msgEl.className = "form-msg";
    const fd = new FormData();
    fd.append("file", replaceForm.file.files[0]);
    if (replaceForm.scores_file) {
      fd.append("scores_file", replaceForm.scores_file.files[0]);
    }
    try {
      const res = await JFAuth.authFetch(`/api/backoffice/${req.session_id}/${apiPath}/replace`, { method: "POST", body: fd });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || "Error al reemplazar");
      }
      msgEl.textContent = "✅ Reemplazado y aprobado.";
      msgEl.className = "form-msg ok";
      setTimeout(() => loadAll(true), 800);
    } catch (err) {
      msgEl.textContent = "❌ " + err.message;
      msgEl.className = "form-msg err";
    }
  });
}

document.getElementById("refresh-review-btn").addEventListener("click", () => loadAll(true));
document.getElementById("refresh-all-btn").addEventListener("click", () => loadAll(true));

init();
