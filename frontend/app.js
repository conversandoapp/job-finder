const dropzone = document.getElementById("dropzone");
const fileInput = document.getElementById("file-input");
const filenameLabel = document.getElementById("filename-label");
const form = document.getElementById("upload-form");
const errorBox = document.getElementById("error-box");
const submitBtn = document.getElementById("submit-btn");

const formView = document.getElementById("form-view");
const rolesView = document.getElementById("roles-view");
const rolesSubtitle = document.getElementById("roles-subtitle");
const roleInputs = [0, 1, 2].map((i) => document.getElementById(`role-input-${i}`));
const dejarEleccionCheckbox = document.getElementById("dejar-eleccion");
const rolesBackBtn = document.getElementById("roles-back-btn");
const rolesSubmitBtn = document.getElementById("roles-submit-btn");
const rolesErrorBox = document.getElementById("roles-error-box");

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

function setRoleInputsDisabled(disabled) {
  roleInputs.forEach((input) => { input.disabled = disabled; });
}

dejarEleccionCheckbox.addEventListener("change", () => {
  setRoleInputsDisabled(dejarEleccionCheckbox.checked);
});

form.addEventListener("submit", async (e) => {
  e.preventDefault();
  errorBox.style.display = "none";

  if (!fileInput.files.length) {
    errorBox.textContent = "Por favor selecciona un archivo (PDF, DOCX o TXT).";
    errorBox.style.display = "block";
    return;
  }

  submitBtn.disabled = true;
  submitBtn.textContent = "Analizando...";

  let rolesSugeridos = [];
  try {
    const fd = new FormData();
    fd.append("file", fileInput.files[0]);
    const res = await JFAuth.authFetch("/api/suggest-roles", { method: "POST", body: fd });
    if (res.ok) {
      const data = await res.json();
      rolesSugeridos = data.roles_sugeridos || [];
    }
  } catch (err) {
    rolesSugeridos = []; // seguimos igual, con los 3 campos vacíos y editables
  }

  submitBtn.disabled = false;
  submitBtn.textContent = "Continuar";

  roleInputs.forEach((input, i) => {
    input.value = rolesSugeridos[i] ? rolesSugeridos[i].titulo : "";
  });
  rolesSubtitle.textContent = rolesSugeridos.length
    ? "Aquí unas opciones:"
    : "Puedes incluir hasta 3 puestos que te interesen:";
  dejarEleccionCheckbox.checked = false;
  setRoleInputsDisabled(false);
  rolesErrorBox.style.display = "none";

  formView.style.display = "none";
  rolesView.style.display = "block";
});

rolesBackBtn.addEventListener("click", () => {
  rolesView.style.display = "none";
  formView.style.display = "block";
});

rolesSubmitBtn.addEventListener("click", async () => {
  rolesErrorBox.style.display = "none";

  const dejarEleccion = dejarEleccionCheckbox.checked;
  const roles = dejarEleccion
    ? []
    : roleInputs.map((i) => i.value.trim()).filter((v) => v.length > 0);

  if (!dejarEleccion && roles.length === 0) {
    rolesErrorBox.textContent = "Ingresa al menos un puesto de tu interés, o marca la casilla para que elijamos nosotros.";
    rolesErrorBox.style.display = "block";
    return;
  }

  rolesSubmitBtn.disabled = true;
  rolesSubmitBtn.textContent = "Enviando...";

  const fd = new FormData();
  fd.append("file", fileInput.files[0]);
  fd.append("linkedin_url", document.getElementById("linkedin_url").value);
  fd.append("pais", document.getElementById("pais").value);
  fd.append("roles_candidato", JSON.stringify(roles));
  fd.append("dejar_eleccion", dejarEleccion ? "true" : "false");

  try {
    const res = await JFAuth.authFetch("/api/analyze", { method: "POST", body: fd });
    if (!res.ok) {
      const errData = await res.json().catch(() => ({}));
      throw new Error(errData.detail || "Error al subir el CV");
    }
    const data = await res.json();
    const resultUrl = `${window.location.origin}/resultado.html?session=${data.session_id}`;

    rolesView.style.display = "none";
    document.getElementById("loading-view").style.display = "block";
    const link = document.getElementById("result-link");
    link.href = resultUrl;
    link.textContent = resultUrl;

    setTimeout(() => { window.location.href = resultUrl; }, 3500);
  } catch (err) {
    rolesErrorBox.textContent = err.message;
    rolesErrorBox.style.display = "block";
    rolesSubmitBtn.disabled = false;
    rolesSubmitBtn.textContent = "Enviar CV";
  }
});
