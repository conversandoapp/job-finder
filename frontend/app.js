const dropzone = document.getElementById("dropzone");
const fileInput = document.getElementById("file-input");
const filenameLabel = document.getElementById("filename-label");
const form = document.getElementById("upload-form");
const errorBox = document.getElementById("error-box");
const submitBtn = document.getElementById("submit-btn");

async function init() {
  const session = await JFAuth.requireAuth();
  if (!session) return;
  JFAuth.renderUserBar("user-bar");
  await loadMySessions();
}

const STATUS_LABEL = {
  pending: "⏳ Pendiente",
  ready: "✅ Listo",
  error: "❌ Error",
  not_requested: "— No pedido",
};

async function loadMySessions() {
  const res = await JFAuth.authFetch("/api/my-sessions");
  if (!res.ok) return;
  const mine = await res.json();
  if (!mine.length) return;

  document.getElementById("my-sessions-card").style.display = "block";
  const listEl = document.getElementById("my-sessions-list");
  listEl.innerHTML = mine.map((s) => `
    <div class="session-row">
      <span>${s.candidate_name || "(sin nombre)"} · CV: ${STATUS_LABEL[s.cv_status] || s.cv_status} · Vacantes: ${STATUS_LABEL[s.jobs_status] || s.jobs_status}</span>
      <a class="btn secondary" style="margin:0; padding:6px 14px; font-size:13px;" href="/resultado.html?session=${s.session_id}">Ver →</a>
    </div>
  `).join("");
}

init();

dropzone.addEventListener("click", () => fileInput.click());
dropzone.addEventListener("dragover", (e) => { e.preventDefault(); dropzone.classList.add("has-file"); });
dropzone.addEventListener("drop", (e) => {
  e.preventDefault();
  if (e.dataTransfer.files.length) {
    fileInput.files = e.dataTransfer.files;
    updateFilenameLabel();
  }
});
fileInput.addEventListener("change", updateFilenameLabel);

function updateFilenameLabel() {
  if (fileInput.files.length) {
    filenameLabel.textContent = "✅ " + fileInput.files[0].name;
    dropzone.classList.add("has-file");
  }
}

form.addEventListener("submit", async (e) => {
  e.preventDefault();
  errorBox.style.display = "none";

  if (!fileInput.files.length) {
    errorBox.textContent = "Por favor selecciona un archivo (PDF, DOCX o TXT).";
    errorBox.style.display = "block";
    return;
  }

  submitBtn.disabled = true;
  submitBtn.textContent = "Enviando...";

  const fd = new FormData();
  fd.append("file", fileInput.files[0]);
  fd.append("linkedin_url", document.getElementById("linkedin_url").value);
  fd.append("pais", document.getElementById("pais").value);

  try {
    const res = await JFAuth.authFetch("/api/analyze", { method: "POST", body: fd });
    if (!res.ok) {
      const errData = await res.json().catch(() => ({}));
      throw new Error(errData.detail || "Error al subir el CV");
    }
    const data = await res.json();
    const resultUrl = `${window.location.origin}/resultado.html?session=${data.session_id}`;

    document.getElementById("form-view").style.display = "none";
    document.getElementById("loading-view").style.display = "block";
    const link = document.getElementById("result-link");
    link.href = resultUrl;
    link.textContent = resultUrl;

    setTimeout(() => { window.location.href = resultUrl; }, 3500);
  } catch (err) {
    errorBox.textContent = err.message;
    errorBox.style.display = "block";
    submitBtn.disabled = false;
    submitBtn.textContent = "Analizar CV";
  }
});
