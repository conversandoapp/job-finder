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
    ".cv-reject-form textarea, .cv-replace-form input, .cv-replace-separate-form input, .jobs-reject-form textarea, .jobs-replace-form input, .cv-analysis-edit-form input, .cv-analysis-edit-form textarea"
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
    wireCvExtras(cvBlock, req);
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

  async function submitReplace(e, form, closeModal) {
    e.preventDefault();
    if (!confirm(`Esto reemplaza ${label} del admin con lo tuyo y lo aprueba directo. ¿Continuar?`)) return;
    const msgEl = form.querySelector(".form-msg");
    msgEl.textContent = "";
    msgEl.className = "form-msg";
    const fd = new FormData();
    fd.append("file", form.file.files[0]);
    if (form.scores_file && form.scores_file.files[0]) {
      fd.append("scores_file", form.scores_file.files[0]);
    }
    try {
      const res = await JFAuth.authFetch(`/api/backoffice/${req.session_id}/${apiPath}/replace`, { method: "POST", body: fd });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || "Error al reemplazar");
      }
      msgEl.textContent = "✅ Reemplazado y aprobado.";
      msgEl.className = "form-msg ok";
      if (closeModal) closeModal.hidden = true;
      setTimeout(() => loadAll(true), 800);
    } catch (err) {
      msgEl.textContent = "❌ " + err.message;
      msgEl.className = "form-msg err";
    }
  }

  replaceForm.addEventListener("submit", (e) => submitReplace(e, replaceForm, null));

  const separateModal = block.querySelector(`.${cssPrefix}-replace-separate-modal`);
  if (separateModal) {
    const separateForm = block.querySelector(`.${cssPrefix}-replace-separate-form`);
    block.querySelector(`.${cssPrefix}-replace-separate-open`).addEventListener("click", () => { separateModal.hidden = false; });
    block.querySelector(`.${cssPrefix}-replace-separate-close`).addEventListener("click", () => { separateModal.hidden = true; });
    separateModal.addEventListener("click", (e) => { if (e.target === separateModal) separateModal.hidden = true; });
    separateForm.addEventListener("submit", (e) => submitReplace(e, separateForm, separateModal));
  }
}

function escapeHtml(str) {
  const div = document.createElement("div");
  div.textContent = str ?? "";
  return div.innerHTML;
}

function renderCvPreview(block, scores) {
  block.querySelector(".cv-preview-score-before").textContent = scores.ats_score_original ?? "–";
  block.querySelector(".cv-preview-score-after").textContent = scores.ats_score_optimizado ?? "–";

  const kwList = block.querySelector(".cv-preview-keywords");
  kwList.innerHTML = "";
  (scores.keywords_agregados || []).forEach((k) => {
    const el = document.createElement("span");
    el.className = "badge green";
    el.textContent = k;
    kwList.appendChild(el);
  });

  const weakList = block.querySelector(".cv-preview-weaknesses");
  weakList.innerHTML = "";
  (scores.debilidades || []).forEach((w) => {
    const li = document.createElement("li");
    li.textContent = "⚠ " + w;
    weakList.appendChild(li);
  });
  if (!(scores.debilidades || []).length) {
    weakList.innerHTML = "<li>Sin debilidades registradas.</li>";
  }

  const rolesList = block.querySelector(".cv-preview-roles");
  rolesList.innerHTML = "";
  (scores.roles_objetivo || []).forEach((r) => {
    const div = document.createElement("div");
    div.className = "role-card";
    div.innerHTML = `
      <div>
        <div class="title">${escapeHtml(r.titulo || "")}</div>
        ${r.justificacion ? `<div class="just">${escapeHtml(r.justificacion)}</div>` : ""}
      </div>
      ${r.match_porcentaje ? `<span class="badge blue">${r.match_porcentaje}% match</span>` : ""}
    `;
    rolesList.appendChild(div);
  });
  if (!(scores.roles_objetivo || []).length) {
    rolesList.innerHTML = "<p class='subtitle'>Aún no hay roles registrados.</p>";
  }
}

function renderKeywordChips(container, keywords) {
  container.innerHTML = "";
  keywords.forEach((kw, idx) => {
    const chip = document.createElement("span");
    chip.className = "badge green";
    chip.style.display = "inline-flex";
    chip.style.alignItems = "center";
    chip.style.gap = "6px";
    chip.textContent = kw;
    const rm = document.createElement("button");
    rm.type = "button";
    rm.className = "chip-remove-btn";
    rm.textContent = "✕";
    rm.addEventListener("click", () => {
      keywords.splice(idx, 1);
      renderKeywordChips(container, keywords);
    });
    chip.appendChild(rm);
    container.appendChild(chip);
  });
}

function renderWeaknessRows(container, weaknesses) {
  container.innerHTML = "";
  weaknesses.forEach((w, idx) => {
    const row = document.createElement("div");
    row.className = "cv-edit-row";
    const ta = document.createElement("textarea");
    ta.rows = 2;
    ta.value = w;
    ta.addEventListener("input", () => { weaknesses[idx] = ta.value; });
    const rm = document.createElement("button");
    rm.type = "button";
    rm.className = "btn-link";
    rm.textContent = "Quitar";
    rm.addEventListener("click", () => {
      weaknesses.splice(idx, 1);
      renderWeaknessRows(container, weaknesses);
    });
    row.appendChild(ta);
    row.appendChild(rm);
    container.appendChild(row);
  });
}

function renderRoleRows(container, roles) {
  container.innerHTML = "";
  roles.forEach((r, idx) => {
    const card = document.createElement("div");
    card.className = "cv-edit-role-card";

    const titleInput = document.createElement("input");
    titleInput.type = "text";
    titleInput.placeholder = "Título del rol";
    titleInput.value = r.titulo || "";
    titleInput.addEventListener("input", () => { r.titulo = titleInput.value; });

    const justTa = document.createElement("textarea");
    justTa.rows = 2;
    justTa.placeholder = "Justificación";
    justTa.value = r.justificacion || "";
    justTa.addEventListener("input", () => { r.justificacion = justTa.value; });

    const matchInput = document.createElement("input");
    matchInput.type = "number";
    matchInput.min = "0";
    matchInput.max = "100";
    matchInput.placeholder = "% match";
    matchInput.value = r.match_porcentaje ?? "";
    matchInput.addEventListener("input", () => {
      r.match_porcentaje = matchInput.value ? Number(matchInput.value) : undefined;
    });

    const rm = document.createElement("button");
    rm.type = "button";
    rm.className = "btn-link";
    rm.textContent = "Quitar rol";
    rm.addEventListener("click", () => {
      roles.splice(idx, 1);
      renderRoleRows(container, roles);
    });

    card.appendChild(titleInput);
    card.appendChild(justTa);
    card.appendChild(matchInput);
    card.appendChild(rm);
    container.appendChild(card);
  });
}

function wireCvExtras(block, req) {
  const downloadBtn = block.querySelector(".cv-download-word-btn");
  const previewToggleBtn = block.querySelector(".cv-preview-toggle-btn");
  const editToggleBtn = block.querySelector(".cv-edit-toggle-btn");
  const previewBox = block.querySelector(".cv-preview-box");
  const previewLoading = block.querySelector(".cv-preview-loading");
  const previewContent = block.querySelector(".cv-preview-content");
  const editForm = block.querySelector(".cv-analysis-edit-form");

  let cachedScores = null;
  let editPopulated = false;
  let keywordsState = [];
  let weaknessesState = [];
  let rolesState = [];

  downloadBtn.addEventListener("click", async () => {
    downloadBtn.disabled = true;
    const originalText = downloadBtn.textContent;
    downloadBtn.textContent = "Descargando...";
    try {
      const res = await JFAuth.authFetch(`/api/download/cv/${req.session_id}`);
      if (!res.ok) throw new Error("No se pudo descargar el CV optimizado");
      const blob = await res.blob();
      const disposition = res.headers.get("content-disposition") || "";
      const match = disposition.match(/filename="?([^"]+)"?/);
      const filename = match ? match[1] : "cv_optimizado.docx";

      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      alert("❌ " + err.message);
    } finally {
      downloadBtn.disabled = false;
      downloadBtn.textContent = originalText;
    }
  });

  async function ensureScoresLoaded() {
    if (cachedScores) return cachedScores;
    const res = await JFAuth.authFetch(`/api/result/${req.session_id}`);
    const data = await res.json();
    cachedScores = data.scores || {};
    return cachedScores;
  }

  previewToggleBtn.addEventListener("click", async () => {
    const isOpen = previewBox.style.display !== "none";
    if (isOpen) {
      previewBox.style.display = "none";
      return;
    }
    previewBox.style.display = "block";
    previewLoading.style.display = "block";
    previewContent.style.display = "none";
    try {
      const scores = await ensureScoresLoaded();
      renderCvPreview(previewBox, scores);
      previewLoading.style.display = "none";
      previewContent.style.display = "block";
    } catch (err) {
      previewLoading.textContent = "No se pudo cargar la vista previa.";
    }
  });

  function populateEditForm(scores) {
    editForm.ats_before.value = scores.ats_score_original ?? "";
    editForm.ats_after.value = scores.ats_score_optimizado ?? "";
    editForm.resumen.value = scores.resumen || "";
    keywordsState = [...(scores.keywords_agregados || [])];
    weaknessesState = [...(scores.debilidades || [])];
    rolesState = (scores.roles_objetivo || []).map((r) => ({ ...r }));
    renderKeywordChips(editForm.querySelector(".cv-edit-keywords-list"), keywordsState);
    renderWeaknessRows(editForm.querySelector(".cv-edit-weaknesses-list"), weaknessesState);
    renderRoleRows(editForm.querySelector(".cv-edit-roles-list"), rolesState);
  }

  editToggleBtn.addEventListener("click", async () => {
    const isOpen = editForm.style.display !== "none";
    if (isOpen) {
      editForm.style.display = "none";
      return;
    }
    editForm.style.display = "block";
    if (!editPopulated) {
      const scores = await ensureScoresLoaded();
      populateEditForm(scores);
      editPopulated = true;
    }
  });

  editForm.querySelector(".cv-edit-keyword-add").addEventListener("click", () => {
    const input = editForm.querySelector(".cv-edit-keyword-input");
    const val = input.value.trim();
    if (!val) return;
    keywordsState.push(val);
    input.value = "";
    renderKeywordChips(editForm.querySelector(".cv-edit-keywords-list"), keywordsState);
  });

  editForm.querySelector(".cv-edit-weakness-add").addEventListener("click", () => {
    weaknessesState.push("");
    renderWeaknessRows(editForm.querySelector(".cv-edit-weaknesses-list"), weaknessesState);
  });

  editForm.querySelector(".cv-edit-role-add").addEventListener("click", () => {
    rolesState.push({ titulo: "", justificacion: "", match_porcentaje: undefined });
    renderRoleRows(editForm.querySelector(".cv-edit-roles-list"), rolesState);
  });

  editForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    const msgEl = editForm.querySelector(".form-msg");
    msgEl.textContent = "";
    msgEl.className = "form-msg";

    const payload = {
      ats_score_original: Number(editForm.ats_before.value) || 0,
      ats_score_optimizado: Number(editForm.ats_after.value) || 0,
      resumen: editForm.resumen.value.trim() || undefined,
      keywords_agregados: keywordsState.map((k) => k.trim()).filter((k) => k !== ""),
      debilidades: weaknessesState.map((w) => w.trim()).filter((w) => w !== ""),
      roles_objetivo: rolesState
        .filter((r) => (r.titulo || "").trim() !== "")
        .map((r) => ({
          titulo: r.titulo.trim(),
          justificacion: (r.justificacion || "").trim(),
          match_porcentaje: r.match_porcentaje ? Number(r.match_porcentaje) : undefined,
        })),
    };

    try {
      const res = await JFAuth.authFetch(`/api/backoffice/${req.session_id}/cv/analysis`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || "Error al guardar el análisis");
      }
      cachedScores = payload;
      msgEl.textContent = "✅ Cambios guardados. La solicitud sigue en revisión.";
      msgEl.className = "form-msg ok";
      if (previewBox.style.display !== "none") {
        renderCvPreview(previewBox, payload);
      }
    } catch (err) {
      msgEl.textContent = "❌ " + err.message;
      msgEl.className = "form-msg err";
    }
  });
}

document.getElementById("refresh-review-btn").addEventListener("click", () => loadAll(true));
document.getElementById("refresh-all-btn").addEventListener("click", () => loadAll(true));

init();
