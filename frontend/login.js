const params = new URLSearchParams(window.location.search);
const redirectTo = params.get("redirect") || "/index.html";

function showPanel(panel) {
  document.getElementById("signin-form").style.display = panel === "signin" ? "block" : "none";
  document.getElementById("signup-form").style.display = panel === "signup" ? "block" : "none";
  document.getElementById("forgot-form").style.display = panel === "forgot" ? "block" : "none";
  document.querySelectorAll(".tab-btn").forEach((b) => {
    b.classList.toggle("active", b.dataset.tab === panel);
  });
}

document.querySelectorAll(".tab-btn").forEach((btn) => {
  btn.addEventListener("click", () => showPanel(btn.dataset.tab));
});

document.getElementById("forgot-link").addEventListener("click", (e) => {
  e.preventDefault();
  showPanel("forgot");
});

document.getElementById("back-to-signin").addEventListener("click", (e) => {
  e.preventDefault();
  showPanel("signin");
});

async function init() {
  const session = await JFAuth.getSession();
  if (session) window.location.href = redirectTo;
}
init();

document.getElementById("signin-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const form = e.target;
  const msgEl = form.querySelector(".form-msg");
  msgEl.textContent = "";
  msgEl.className = "form-msg";

  const client = await JFAuth.initSupabase();
  const { error } = await client.auth.signInWithPassword({
    email: form.email.value,
    password: form.password.value,
  });

  if (error) {
    msgEl.textContent = "❌ " + error.message;
    msgEl.className = "form-msg err";
    return;
  }
  window.location.href = redirectTo;
});

document.getElementById("signup-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const form = e.target;
  const msgEl = form.querySelector(".form-msg");
  msgEl.textContent = "";
  msgEl.className = "form-msg";

  const client = await JFAuth.initSupabase();
  const { data, error } = await client.auth.signUp({
    email: form.email.value,
    password: form.password.value,
  });

  if (error) {
    msgEl.textContent = "❌ " + error.message;
    msgEl.className = "form-msg err";
    return;
  }

  if (data.session) {
    window.location.href = redirectTo;
    return;
  }

  msgEl.textContent = "✅ Cuenta creada. Si tu proyecto de Supabase pide confirmar el email, revisa tu correo antes de ingresar.";
  msgEl.className = "form-msg ok";
});

document.getElementById("forgot-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const form = e.target;
  const msgEl = form.querySelector(".form-msg");
  msgEl.textContent = "";
  msgEl.className = "form-msg";

  const client = await JFAuth.initSupabase();
  const resetUrl = `${window.location.origin}/reset-password.html`;
  const { error } = await client.auth.resetPasswordForEmail(form.email.value, {
    redirectTo: resetUrl,
  });

  if (error) {
    msgEl.textContent = "❌ " + error.message;
    msgEl.className = "form-msg err";
    return;
  }

  msgEl.textContent = "✅ Si ese email tiene una cuenta, recibirás un link para restablecer tu contraseña. Revisa también la carpeta de spam.";
  msgEl.className = "form-msg ok";
  form.querySelector("input").value = "";
});
