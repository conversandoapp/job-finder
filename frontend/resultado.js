const params = new URLSearchParams(window.location.search);
const sessionId = params.get("session");

const pendingView = document.getElementById("pending-view");
const errorView = document.getElementById("error-view");
const readyView = document.getElementById("ready-view");

let pollTimer = null;

async function init() {
  const session = await JFAuth.requireAuth();
  if (!session) return;
  JFAuth.renderUserBar("user-bar");

  if (!sessionId) {
    errorView.style.display = "block";
    return;
  }
  await refresh();
}

async function refresh() {
  try {
    const res = await JFAuth.authFetch(`/api/status/${sessionId}`);
    if (!res.ok) {
      errorView.style.display = "block";
      return;
    }
    const data = await res.json();

    if (data.cv_status !== "ready") {
      pendingView.style.display = "block";
      readyView.style.display = "none";
      if (!pollTimer) pollTimer = setInterval(refresh, 10000);
      return;
    }

    if (pollTimer) { clearInterval(pollTimer); pollTimer = null; }
    pendingView.style.display = "none";
    await renderReady(data);
  } catch (e) {
    errorView.style.display = "block";
  }
}

async function renderReady(sessionData) {
  readyView.style.display = "block";

  const resultRes = await JFAuth.authFetch(`/api/result/${sessionId}`);
  const result = await resultRes.json();
  const scores = result.scores || {};

  document.getElementById("candidate-name").textContent = sessionData.candidate_name || "Tu análisis";
  document.getElementById("candidate-meta").textContent =
    `${sessionData.pais || ""}${sessionData.linkedin_url ? " · " + sessionData.linkedin_url : ""}`;

  document.getElementById("score-before").textContent = scores.ats_score_original ?? "–";
  document.getElementById("score-after").textContent = scores.ats_score_optimizado ?? "–";

  const kwList = document.getElementById("keywords-list");
  kwList.innerHTML = "";
  (scores.keywords_agregados || []).forEach((k) => {
    const el = document.createElement("span");
    el.className = "badge green";
    el.textContent = k;
    kwList.appendChild(el);
  });

  const weakList = document.getElementById("weaknesses-list");
  weakList.innerHTML = "";
  (scores.debilidades || []).forEach((w) => {
    const li = document.createElement("li");
    li.textContent = "⚠ " + w;
    weakList.appendChild(li);
  });
  if (!(scores.debilidades || []).length) {
    weakList.innerHTML = "<li>Sin debilidades registradas.</li>";
  }

  const rolesList = document.getElementById("roles-list");
  rolesList.innerHTML = "";
  (scores.roles_objetivo || []).forEach((r) => {
    const div = document.createElement("div");
    div.className = "role-card";
    div.innerHTML = `
      <div>
        <div class="title">${r.titulo || r}</div>
        ${r.justificacion ? `<div class="just">${r.justificacion}</div>` : ""}
      </div>
      ${r.match_porcentaje ? `<span class="badge blue">${r.match_porcentaje}% match</span>` : ""}
    `;
    rolesList.appendChild(div);
  });
  if (!(scores.roles_objetivo || []).length) {
    rolesList.innerHTML = "<p class='subtitle'>Aún no hay roles registrados.</p>";
  }

  setupDownloadLink();
  setupJobsCta(sessionData);
}

function setupDownloadLink() {
  const link = document.getElementById("download-link");
  link.href = "#";
  link.addEventListener("click", async (e) => {
    e.preventDefault();
    const originalText = link.textContent;
    link.textContent = "Descargando...";
    try {
      const res = await JFAuth.authFetch(`/api/download/cv/${sessionId}`);
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
      alert(err.message);
    } finally {
      link.textContent = originalText;
    }
  });
}

function setupJobsCta(sessionData) {
  const jobsBtn = document.getElementById("jobs-btn");
  const jobsPendingView = document.getElementById("jobs-pending-view");
  const jobsReadyView = document.getElementById("jobs-ready-view");
  const jobsLink = document.getElementById("jobs-link");
  jobsLink.href = `/vacantes.html?session=${sessionId}`;

  if (sessionData.jobs_status === "ready") {
    jobsBtn.parentElement.style.display = "none";
    jobsReadyView.style.display = "block";
    return;
  }
  if (sessionData.jobs_status === "pending") {
    jobsBtn.parentElement.style.display = "none";
    jobsPendingView.style.display = "block";
    pollJobs();
    return;
  }

  jobsBtn.addEventListener("click", async () => {
    jobsBtn.disabled = true;
    jobsBtn.textContent = "Enviando solicitud...";
    try {
      const res = await JFAuth.authFetch("/api/jobs", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ session_id: sessionId }),
      });
      if (!res.ok) throw new Error("No se pudo iniciar la búsqueda");
      jobsBtn.parentElement.style.display = "none";
      jobsPendingView.style.display = "block";
      pollJobs();
    } catch (e) {
      jobsBtn.disabled = false;
      jobsBtn.textContent = "Buscar vacantes en LinkedIn para mi perfil →";
      alert(e.message);
    }
  });
}

function pollJobs() {
  const jobsPendingView = document.getElementById("jobs-pending-view");
  const jobsReadyView = document.getElementById("jobs-ready-view");
  const timer = setInterval(async () => {
    const res = await JFAuth.authFetch(`/api/status/${sessionId}`);
    const data = await res.json();
    if (data.jobs_status === "ready") {
      clearInterval(timer);
      jobsPendingView.style.display = "none";
      jobsReadyView.style.display = "block";
    }
  }, 10000);
}

init();
