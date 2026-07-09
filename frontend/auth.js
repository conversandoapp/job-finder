/* Autenticación compartida (Supabase). Se carga después del script CDN de
   supabase-js y antes del JS propio de cada página. Expone window.JFAuth. */

let _supabaseClient = null;
let _configPromise = null;

async function _getConfig() {
  if (!_configPromise) {
    _configPromise = fetch("/api/config").then((r) => r.json());
  }
  return _configPromise;
}

async function initSupabase() {
  if (_supabaseClient) return _supabaseClient;
  const cfg = await _getConfig();
  if (!cfg.supabase_url || !cfg.supabase_anon_key) {
    throw new Error(
      "Supabase no está configurado en el servidor. Revisa SUPABASE_URL y " +
      "SUPABASE_ANON_KEY en backend/.env (ver README)."
    );
  }
  _supabaseClient = supabase.createClient(cfg.supabase_url, cfg.supabase_anon_key);
  return _supabaseClient;
}

async function getSession() {
  const client = await initSupabase();
  const { data } = await client.auth.getSession();
  return data.session || null;
}

function _redirectToLogin(loginPage) {
  const back = encodeURIComponent(window.location.pathname + window.location.search);
  window.location.href = `${loginPage}?redirect=${back}`;
}

async function requireAuth(loginPage = "/login.html") {
  const session = await getSession();
  if (!session) {
    _redirectToLogin(loginPage);
    return null;
  }
  return session;
}

async function requireAdmin() {
  const session = await requireAuth("/admin-login");
  if (!session) return null;

  const res = await authFetch("/api/whoami");
  if (!res.ok) {
    _redirectToLogin("/admin-login");
    return null;
  }
  const who = await res.json();
  if (!who.is_admin) {
    document.body.innerHTML = `
      <div style="max-width:480px;margin:80px auto;text-align:center;font-family:sans-serif;padding:0 20px;">
        <h2>Acceso denegado</h2>
        <p style="color:#5b6b76;">Esta cuenta (${who.email}) no tiene permisos de administrador.</p>
        <a href="/index.html" style="color:#0077b5;">Ir a la app</a>
      </div>`;
    return null;
  }
  return who;
}

async function authFetch(url, options = {}) {
  const session = await getSession();
  if (!session) {
    _redirectToLogin("/login.html");
    throw new Error("No autenticado");
  }
  const headers = Object.assign({}, options.headers || {}, {
    Authorization: `Bearer ${session.access_token}`,
  });
  return fetch(url, Object.assign({}, options, { headers }));
}

async function logout(redirectTo = "/login.html") {
  const client = await initSupabase();
  await client.auth.signOut();
  window.location.href = redirectTo;
}

function renderUserBar(containerId, redirectTo) {
  getSession().then((session) => {
    const el = document.getElementById(containerId);
    if (!el || !session) return;
    el.innerHTML = `
      <span class="user-email">${session.user.email}</span>
      <button type="button" class="logout-btn">Cerrar sesión</button>
    `;
    el.querySelector(".logout-btn").addEventListener("click", () => logout(redirectTo));
  });
}

window.JFAuth = {
  initSupabase,
  getSession,
  requireAuth,
  requireAdmin,
  authFetch,
  logout,
  renderUserBar,
};
