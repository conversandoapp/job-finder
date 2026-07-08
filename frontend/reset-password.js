async function init() {
  const client = await JFAuth.initSupabase();

  // Supabase envía el token de recovery en el hash de la URL.
  // Al cargar la página, el SDK lo detecta automáticamente y establece la sesión.
  const { data: { session }, error } = await client.auth.getSession();

  const loadingEl = document.getElementById("loading-state");
  const formEl = document.getElementById("reset-form");
  const errorEl = document.getElementById("error-state");
  const errorMsg = document.getElementById("error-msg");

  // Supabase también emite el evento PASSWORD_RECOVERY cuando detecta el token en el hash.
  client.auth.onAuthStateChange((event) => {
    if (event === "PASSWORD_RECOVERY") {
      loadingEl.style.display = "none";
      formEl.style.display = "block";
    }
  });

  // Si ya hay sesión activa con tipo recovery, mostramos el form directamente.
  if (session) {
    loadingEl.style.display = "none";
    formEl.style.display = "block";
  } else if (error || !window.location.hash.includes("access_token")) {
    loadingEl.style.display = "none";
    errorEl.style.display = "block";
  }

  // Timeout: si en 3 segundos no se detectó recovery, mostramos error.
  setTimeout(() => {
    if (loadingEl.style.display !== "none") {
      loadingEl.style.display = "none";
      errorEl.style.display = "block";
    }
  }, 3000);
}

init();

document.getElementById("reset-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const form = e.target;
  const msgEl = form.querySelector(".form-msg");
  msgEl.textContent = "";
  msgEl.className = "form-msg";

  const password = form.password.value;
  const password2 = form.password2.value;

  if (password !== password2) {
    msgEl.textContent = "❌ Las contraseñas no coinciden.";
    msgEl.className = "form-msg err";
    return;
  }

  const client = await JFAuth.initSupabase();
  const { error } = await client.auth.updateUser({ password });

  if (error) {
    msgEl.textContent = "❌ " + error.message;
    msgEl.className = "form-msg err";
    return;
  }

  msgEl.textContent = "✅ Contraseña actualizada. Redirigiendo…";
  msgEl.className = "form-msg ok";
  form.querySelector("button").disabled = true;

  setTimeout(() => {
    window.location.href = "/index.html";
  }, 1500);
});
