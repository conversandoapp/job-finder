const params = new URLSearchParams(window.location.search);
const sessionId = params.get("session");

const CATEGORY_META = {
  alta_relevancia: { label: "🔴 Alta relevancia", color: "#c0392b" },
  remoto_latam: { label: "🟢 Remoto LATAM", color: "#1a7f4b" },
  media: { label: "🟡 Media", color: "#b8960c" },
  especializado: { label: "🔵 Especializado", color: "#0077b5" },
};

const pendingView = document.getElementById("pending-view");
const errorView = document.getElementById("error-view");
const platform = document.getElementById("platform");

let allJobs = [];
let activeFilter = { type: "all" };

async function init() {
  const session = await JFAuth.requireAuth();
  if (!session) return;
  JFAuth.renderUserBar("user-bar");

  if (!sessionId) { errorView.style.display = "block"; return; }
  document.getElementById("vh-resultado-link").href = `/resultado.html?session=${sessionId}`;
  await refresh();
}

async function refresh() {
  const res = await JFAuth.authFetch(`/api/vacantes/${sessionId}`);
  if (res.status === 404) { errorView.style.display = "block"; return; }

  const data = await res.json();
  if (res.status === 202 || !data.vacantes) {
    pendingView.style.display = "block";
    platform.style.display = "none";
    setTimeout(refresh, 10000);
    return;
  }

  pendingView.style.display = "none";
  render(data);
}

function render(data) {
  platform.style.display = "block";
  allJobs = data.vacantes || [];

  document.getElementById("vh-candidate-name").textContent = data.candidato?.nombre || "ti";

  const badgesEl = document.getElementById("vh-stats-badges");
  const stats = data.stats || {};
  badgesEl.innerHTML = `
    <span class="b">${stats.total_vacantes ?? allJobs.length} vacantes</span>
    <span class="b">${stats.publicadas_hoy ?? 0} publicadas hoy</span>
    <span class="b">${stats.remotas ?? 0} remotas</span>
  `;

  renderStatsGrid(stats);
  renderNav();
  renderTop5(data);
  renderSections();
  renderNotes(data);
  setupFilters();
}

function renderStatsGrid(stats) {
  const grid = document.getElementById("vh-stats-grid");
  const items = [
    { num: stats.total_vacantes ?? allJobs.length, lbl: "Total vacantes" },
    { num: stats.publicadas_hoy ?? 0, lbl: "Publicadas hoy" },
    { num: stats.remotas ?? 0, lbl: "Remotas" },
    { num: stats.solicitud_sencilla ?? 0, lbl: "Solicitud sencilla" },
  ];
  grid.innerHTML = items.map(i => `
    <div class="vh-stat-card"><div class="num">${i.num}</div><div class="lbl">${i.lbl}</div></div>
  `).join("");
}

function renderNav() {
  const nav = document.getElementById("vh-nav");
  const cats = Object.keys(CATEGORY_META).filter(c => allJobs.some(j => j.categoria === c));
  nav.innerHTML = `<a href="#vh-top5-section">🏆 Top 5</a>` + cats.map(c => `
    <a href="#sec-${c}"><span class="dot" style="background:${CATEGORY_META[c].color}"></span> ${CATEGORY_META[c].label}</a>
  `).join("") + `<a href="#vh-notes-section">📌 Estrategia</a>`;
}

function renderTop5(data) {
  const ids = data.top5_ids && data.top5_ids.length
    ? data.top5_ids
    : [...allJobs].sort((a, b) => (b.match_porcentaje || 0) - (a.match_porcentaje || 0)).slice(0, 5).map(j => j.id);

  const body = document.getElementById("vh-top5-body");
  body.innerHTML = ids.map(id => {
    const j = allJobs.find(x => x.id === id);
    if (!j) return "";
    return `
      <tr>
        <td>${j.titulo}</td>
        <td>${j.empresa}</td>
        <td>${j.modalidad || "—"}</td>
        <td>${j.match_porcentaje ? j.match_porcentaje + "%" : "—"}</td>
        <td><a class="apply" href="${j.url}" target="_blank" rel="noopener">Ver vacante →</a></td>
      </tr>
    `;
  }).join("");
}

function renderSections() {
  const container = document.getElementById("vh-sections");
  const cats = Object.keys(CATEGORY_META).filter(c => allJobs.some(j => j.categoria === c));
  container.innerHTML = cats.map(c => `
    <div id="sec-${c}">
      <h2 class="vh-section-title">${CATEGORY_META[c].label}</h2>
      <div class="job-cards" data-cat="${c}"></div>
    </div>
  `).join("");
  cats.forEach(c => renderCardsForCategory(c, allJobs.filter(j => j.categoria === c)));
}

function renderCardsForCategory(cat, jobs) {
  const holder = document.querySelector(`.job-cards[data-cat="${cat}"]`);
  holder.innerHTML = jobs.map(jobCardHtml).join("") || "<p style='color:#5b6b76; font-size:13px;'>Sin vacantes en esta categoría.</p>";
}

function jobCardHtml(j) {
  const isNew = j.es_nuevo_24h;
  return `
    <div class="job-card cat-${j.categoria}"
         data-modalidad="${j.modalidad || ""}"
         data-nuevo="${isNew ? "true" : "false"}"
         data-sencilla="${j.solicitud_sencilla ? "true" : "false"}">
      <div>
        <div class="title">${j.titulo}</div>
        <div class="empresa">${j.empresa} · ${j.ubicacion || ""}</div>
        <div class="meta">
          ${j.modalidad ? `<span>${j.modalidad}</span>` : ""}
          ${j.fecha_publicacion ? `<span>${j.fecha_publicacion}</span>` : ""}
          ${j.num_solicitudes != null ? `<span>${j.num_solicitudes} solicitantes</span>` : ""}
          ${j.solicitud_sencilla ? `<span>Solicitud sencilla</span>` : ""}
          ${isNew ? `<span class="badge-new">HOY ⚡</span>` : ""}
        </div>
        ${j.descripcion_corta ? `<div class="desc">${j.descripcion_corta}</div>` : ""}
      </div>
      <div class="actions">
        ${j.match_porcentaje ? `<span class="match">${j.match_porcentaje}% match</span>` : ""}
        <a class="btn" href="${j.url}" target="_blank" rel="noopener">Ver vacante →</a>
      </div>
    </div>
  `;
}

function renderNotes(data) {
  if (!data.notas_estrategia) return;
  document.getElementById("vh-notes-section").style.display = "block";
  document.getElementById("vh-notes-text").textContent = data.notas_estrategia;
}

function setupFilters() {
  document.querySelectorAll(".filter-btn").forEach(btn => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".filter-btn").forEach(b => b.classList.remove("active"));
      btn.classList.add("active");

      if (btn.dataset.filter === "all") activeFilter = { type: "all" };
      else if (btn.dataset.filterModalidad) activeFilter = { type: "modalidad", value: btn.dataset.filterModalidad };
      else if (btn.dataset.filterNuevo) activeFilter = { type: "nuevo" };
      else if (btn.dataset.filterSencilla) activeFilter = { type: "sencilla" };

      applyFilter();
    });
  });
}

function applyFilter() {
  document.querySelectorAll(".job-card").forEach(card => {
    let show = true;
    if (activeFilter.type === "modalidad") show = card.dataset.modalidad === activeFilter.value;
    else if (activeFilter.type === "nuevo") show = card.dataset.nuevo === "true";
    else if (activeFilter.type === "sencilla") show = card.dataset.sencilla === "true";
    card.style.display = show ? "flex" : "none";
  });
}

init();
