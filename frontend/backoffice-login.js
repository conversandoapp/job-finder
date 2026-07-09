async function init() {
  const session = await JFAuth.getSession();
  if (session) {
    const res = await JFAuth.authFetch("/api/whoami");
    if (res.ok) {
      const who = await res.json();
      if (who.is_backoffice) {
        window.location.href = "/backoffice";
        return;
      }
    }
  }
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

  const res = await JFAuth.authFetch("/api/whoami");
  const who = await res.json();
  if (!who.is_backoffice) {
    msgEl.textContent = "❌ Esta cuenta no tiene permisos de backoffice.";
    msgEl.className = "form-msg err";
    await client.auth.signOut();
    return;
  }

  window.location.href = "/backoffice";
});
