const params = new URLSearchParams(window.location.search);
const redirectTo = params.get("redirect") || "/index.html";

document.querySelectorAll(".tab-btn").forEach((btn) => {
  btn.addEventListener("click", () => {
    document.querySelectorAll(".tab-btn").forEach((b) => b.classList.remove("active"));
    btn.classList.add("active");
    document.getElementById("signin-form").style.display = btn.dataset.tab === "signin" ? "block" : "none";
    document.getElementById("signup-form").style.display = btn.dataset.tab === "signup" ? "block" : "none";
  });
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

  msgEl.textContent = "✅ Cuenta creada. Si tu proyecto de Supabase pide confirmar el email, revisá tu correo antes de ingresar.";
  msgEl.className = "form-msg ok";
});
