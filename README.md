# Job Finder — MVP manual

> **Mapa técnico completo del repo:** ver [`ARCHITECTURE.md`](ARCHITECTURE.md)
> (modelo de datos, endpoints, servicios, OAuth de Drive, skills de Claude Code).

MVP del flujo de "optimizar CV + encontrar vacantes", pero **manual**: no hay
agentes de IA corriendo automáticamente en el servidor. El sistema solo
recibe solicitudes, te avisa a vos (el admin) y te da un panel para subir
los resultados a mano. El usuario final nunca recibe un aviso — vuelve a
entrar a su link cuando quiere consultar si ya está listo.

## Flujo

0. El usuario se crea una cuenta él mismo en `/login.html` (email + contraseña,
   vía Supabase). Vos entrás a `/admin-login` con tu única cuenta admin.
1. Usuario entra a `/` (`index.html`), sube su CV → ve "estamos procesando,
   hasta 24h" y un link para volver más tarde.
2. Vos recibís un aviso (panel admin + email si lo activás) con el CV.
3. Entrás a `/admin`, le pegás el CV a Claude con el prompt de
   `backend/schemas/prompt_para_claude_cv_analysis.md` y te devuelve un
   `cv_analysis.json` (scores ATS, roles, keywords, debilidades) + el texto
   del CV reescrito para pegar en Word. Subís el `.docx` que armaste + ese
   JSON desde el panel — nada de campos sueltos para llenar a mano.
4. Usuario vuelve a su link (`/resultado.html?session=...`) y ve su análisis
   + descarga el CV optimizado. También ve un listado de "tus solicitudes
   anteriores" en `/index.html` por si perdió el link.
5. Usuario aprieta "Buscar vacantes" → te avisa de nuevo.
6. Armás el `vacantes.json` con ayuda de Claude (ver
   `backend/schemas/prompt_para_claude_vacantes.md`) y lo subís desde el panel.
7. Usuario vuelve a `/vacantes.html?session=...` y ve la plataforma de
   vacantes ya armada — filtros, cards, top 5, todo generado automáticamente
   a partir de ese JSON (vos nunca escribís HTML).

Cada sesión queda asociada al `user_id` de Supabase del usuario que subió el
CV. El backend verifica en cada request que quien pide un resultado sea el
dueño de esa sesión (o vos, el admin) — nadie puede ver el análisis de otra
persona solo adivinando el link.

## Configurar Supabase (obligatorio, una sola vez)

**Nota sobre las claves:** Supabase cambió su forma de firmar los tokens.
Los proyectos creados desde octubre de 2025 firman los JWT con un esquema
asimétrico (ES256) en vez del secreto compartido de antes. El backend ya
soporta ambos casos automáticamente, pero por eso **no vas a encontrar un
"JWT Secret" en un proyecto nuevo** en el lugar donde antes estaba — es
normal, no hace falta.

1. Creá un proyecto gratis en https://supabase.com/dashboard.
2. Andá a **Authentication → Sign In / Providers → Email** y por ahora dejá
   "Confirm email" DESACTIVADO — así podés probar signup/login local sin
   tener que configurar el envío de emails de confirmación. Podés activarlo
   después cuando vayas a producción.
3. Andá a **Project Settings → API Keys** y copiá:
   - **Project URL** → `SUPABASE_URL`
   - **anon public** (o **publishable key**, `sb_publishable_...`, en
     proyectos nuevos) → `SUPABASE_ANON_KEY`
4. Pegá esos dos valores en `backend/.env` (ver `.env.example`). Dejá
   `SUPABASE_JWT_SECRET` vacío — el backend verifica los tokens
   automáticamente contra las claves públicas del proyecto
   (`{SUPABASE_URL}/auth/v1/.well-known/jwks.json`), no hace falta copiar
   nada más.
   - Excepción: si tu proyecto es viejo y todavía firma con HS256 (lo ves en
     **Project Settings → JWT Keys → pestaña "Legacy JWT Secret"**, si existe
     esa opción), copiá ese secreto en `SUPABASE_JWT_SECRET` como respaldo.
5. Creá tu cuenta admin: abrí `http://localhost:8000/login.html` (la de
   usuarios normales) y registrate una vez con el email que vayas a usar
   como admin. Después poné ese mismo email en `ADMIN_EMAIL` en `backend/.env`.
   A partir de ahí, ese email entra como admin en `/admin-login` y
   como usuario normal en `/login.html` (son el mismo login de Supabase,
   lo único que cambia es qué endpoints del backend le dejamos usar).
   - Todo usuario tiene siempre un backoffice que revisa (aprueba/rechaza/
     reemplaza) el CV optimizado y las vacantes antes de que el candidato
     los vea: por defecto es el admin (podés aprobarte a vos mismo desde
     `/backoffice`, donde ya ves todas las solicitudes). Para delegarle
     esa revisión a otra persona, registrá esa cuenta en `/login.html`,
     entrá a `/admin` → pestaña "Usuarios", asignale el rol "backoffice" y
     después asignale los usuarios que va a revisar (ahí entra por
     `/backoffice-login` y solo ve a los que le asignaste). Para cambiar a
     alguien de backoffice primero hay que quitarle la asignación actual
     desde esa misma pestaña. `BACKOFFICE_EMAILS` en `backend/.env` sigue
     existiendo como fallback legacy (lista separada por coma), pero ya no
     hace falta tocarlo — se gestiona todo desde el panel admin.

Sin `SUPABASE_URL` / `SUPABASE_ANON_KEY` configurados, el login no
funciona — es la única parte no-opcional de la configuración. **La pantalla
de "Connect to your project" con "Direct connection / Transaction pooler"
es para conectarte directo a la base de datos Postgres (SQL, ORMs) — no es
lo que necesitamos acá, ignorala.**

## Cómo correrlo local

```bash
cd job-finder/backend
python -m venv venv
venv\Scripts\activate            # en Mac/Linux: source venv/bin/activate
pip install -r requirements.txt
copy .env.example .env           # en Mac/Linux: cp .env.example .env
```

Editá `backend/.env` y completá `SUPABASE_URL`, `SUPABASE_ANON_KEY`,
`SUPABASE_JWT_SECRET` y `ADMIN_EMAIL` (ver sección de arriba). Después:

```bash
uvicorn app:app --reload --port 8000
```

Abrí `http://localhost:8000/index.html` — esa es la vista del usuario
(pide login/registro). Abrí `http://localhost:8000/admin-login` para
entrar a tu panel.

Sin tocar nada más, las notificaciones y los CVs quedan guardados en tu
proyecto de Supabase (tabla `notifications` y bucket de Storage
`cv-files` — ver "Configurar Supabase" más abajo), y las notificaciones
también se ven en la pestaña "Notificaciones" del panel admin.

## Configurar Supabase (Postgres + Storage)

Además de auth, el backend usa Supabase para guardar todo (sesiones, CVs,
notificaciones, el token de Drive) — necesario porque el filesystem del
servicio desplegado (Render) es efímero. Antes de correr el backend por
primera vez:

1. En el dashboard de tu proyecto de Supabase (el mismo que ya usás para
   auth) → **SQL Editor** → pegá y corré el contenido de
   `backend/supabase/schema.sql`.
2. **Storage** → creá un bucket llamado `cv-files`, marcado como **privado**
   (el backend proxea las descargas con permisos propios, un bucket público
   dejaría cualquier CV accesible por link adivinado).
3. **Project Settings → API** → copiá la key **`service_role`** (NO la
   `anon public`) y ponela en `backend/.env` como `SUPABASE_SERVICE_ROLE_KEY`.
   Es secreta — nunca la mandes al frontend ni la subas a git.

Con eso ya podés levantar el backend normalmente.

## Activar email real (opcional)

1. Activá verificación en 2 pasos en tu cuenta de Gmail (conversandoapp@gmail.com).
2. Andá a https://myaccount.google.com/apppasswords y generá una App Password para "Mail".
3. En `backend/.env`:
   ```
   NOTIFY_EMAIL_ENABLED=true
   NOTIFY_EMAIL_APP_PASSWORD=xxxx xxxx xxxx xxxx
   ```
4. Reiniciá el servidor. A partir de ahí, cada CV subido o vacante pedida te
   manda un correo real además de quedar en el panel.

Es gratis (Gmail no cobra por esto) y no requiere ningún servicio externo.

## Activar Google Drive real (opcional)

Los CVs se pueden subir a tu propio Google Drive (15GB gratis con una
cuenta Gmail normal, sin necesitar Google Workspace). Usa OAuth 2.0
delegado a tu propia cuenta — **no** una cuenta de servicio, porque las
cuentas de servicio no tienen cuota de almacenamiento propia (por eso
antes fallaba con "Service Accounts do not have storage quota...").

Como el proyecto se despliega directo en Render (ver `DEPLOY.md`) y no hay
ejecución local, la autorización de una sola vez se hace enteramente
contra el servicio ya desplegado, desde el panel admin:

1. Andá a https://console.cloud.google.com/, creá un proyecto (o usá uno
   existente) y habilitá "Google Drive API".
2. Pantalla de consentimiento OAuth (OAuth consent screen): tipo
   "External", Publishing status **"In production"** (¡importante! en
   "Testing" el refresh token expira a los 7 días). Agregá el scope
   `https://www.googleapis.com/auth/drive.file`.
3. Credenciales → "Crear credenciales" → "ID de cliente de OAuth" → tipo
   "Aplicación web". Como redirect URI autorizado poné
   `https://TU-SERVICIO.onrender.com/api/admin/drive/oauth2callback`.
4. En las variables de entorno del servicio (ver `DEPLOY.md`):
   ```
   DRIVE_ENABLED=true
   DRIVE_OAUTH_CLIENT_ID=el-client-id
   DRIVE_OAUTH_CLIENT_SECRET=el-client-secret
   DRIVE_OAUTH_REDIRECT_URI=https://TU-SERVICIO.onrender.com/api/admin/drive/oauth2callback
   ```
5. Entrá a `/admin` logueado como admin y hacé click en "☁️ Conectar
   Google Drive". Vas a ver un aviso de "app no verificada" — es esperable
   para un uso personal de un solo usuario, click en "Avanzado" → "Ir a
   Job Finder (no seguro)". Al aceptar, queda guardado el token.

No hace falta crear ni compartir ninguna carpeta a mano: la primera vez
que se sube un CV, la app busca (o crea) una carpeta llamada
"Job Finder - CVs recibidos" en tu Drive.

Sin esto configurado, los CVs igual quedan disponibles en el bucket de
Supabase Storage — Drive es un extra (una copia de conveniencia para el
admin), no un requisito para que el sistema funcione.

## Estructura

```
job-finder/
├── backend/
│   ├── app.py                 # FastAPI: todos los endpoints + sirve el frontend
│   ├── requirements.txt
│   ├── .env.example
│   ├── services/
│   │   ├── db.py               # cliente de Supabase (Postgres + Storage)
│   │   ├── sessions.py         # estado de cada solicitud (tabla `sessions`)
│   │   ├── auth.py             # verifica JWT de Supabase, detecta admin
│   │   ├── notifications.py    # email real + tabla `notifications`
│   │   ├── storage_drive.py    # Google Drive real o fallback sin Drive
│   │   └── drive_oauth.py      # flujo OAuth de conexión con Drive
│   ├── supabase/
│   │   └── schema.sql          # correr una vez en el SQL Editor del proyecto
│   └── schemas/
│       ├── cv_analysis_ejemplo.json
│       ├── prompt_para_claude_cv_analysis.md
│       ├── vacantes_ejemplo.json
│       ├── vacantes_demo.json           # ejemplo con 10 vacantes para probar rápido
│       └── prompt_para_claude_vacantes.md
└── frontend/                   # HTML/CSS/JS plano, sin build step
    ├── auth.js / auth.css               — cliente Supabase compartido, guards de sesión
    ├── login.html / login.js            — signup + login de usuarios normales
    ├── admin-login.html / admin-login.js — login exclusivo de la cuenta admin
    ├── index.html / app.js              — subir CV + ver solicitudes anteriores
    ├── resultado.html / resultado.js    — ver análisis + pedir vacantes
    ├── vacantes.html / vacantes.js      — plataforma de vacantes (data-driven)
    └── admin.html / admin.js            — panel admin
```

## Por qué estas decisiones

- **Todo en Supabase (Postgres + Storage), sin filesystem propio:** cada
  sesión es una fila en la tabla `sessions`, los CVs van a un bucket de
  Storage. Antes era un filesystem local (una carpeta por sesión), pero el
  servicio se despliega en Render sin disco persistente — cualquier archivo
  local se pierde en cada redeploy. RLS queda deshabilitado a propósito: el
  frontend nunca toca estas tablas directo, toda la autorización la hace el
  backend en Python (`auth.py`).
- **Sin build step en el frontend:** HTML/CSS/JS plano servido directo por
  FastAPI. Menos piezas que puedan romperse mientras validás el modelo de
  negocio. Supabase se carga por CDN (`@supabase/supabase-js`), sin npm.
- **JWT verificado localmente para auth, SDK de Supabase solo para datos:**
  el frontend usa `supabase-js` para login/signup y consigue un JWT. El
  backend verifica ese token contra las JWKS del proyecto (librería `PyJWT`,
  ver `auth.py`) sin necesitar el SDK completo para eso — pero sí usa el SDK
  de Python (`supabase`, ver `services/db.py`) para leer/escribir en
  Postgres y Storage con la `service_role` key.
- **Roles gestionables desde `/admin` (tabla `user_roles`), con `ADMIN_EMAIL`
  como respaldo permanente:** el admin puede promover a cualquier usuario con
  al menos una sesión creada a `usuario`/`backoffice`/`admin` desde la
  pestaña "Usuarios". `ADMIN_EMAIL` (variable de entorno) sigue siendo admin
  sin importar lo que diga la tabla — nunca se pierde ese acceso.
  `BACKOFFICE_EMAILS` queda como fallback legacy, solo se usa si el usuario
  no tiene fila en `user_roles`. El admin siempre tiene también permisos de
  backoffice (jerarquía admin ⊇ backoffice ⊇ usuario). Todo usuario tiene
  siempre un backoffice: por defecto es el admin permanente, hasta que se
  le asigne uno específico en `backoffice_assignments` — nunca se salta la
  aprobación, solo cambia quién la hace (si es el admin, se aprueba a sí
  mismo desde `/backoffice`, donde ya ve todo). Cada backoffice no-admin
  solo ve (y revisa) los usuarios que el admin le asignó. Reasignar a
  alguien de un backoffice a otro requiere primero quitarle la asignación
  actual — recién ahí vuelve a estar disponible para asignarlo de nuevo.
- **JSON en vez de HTML para las vacantes (y ahora también para el análisis
  de CV):** vos seguís usando Claude para todo el trabajo de análisis y
  redacción, pero el output es datos estructurados. Las páginas ya tienen el
  diseño, los filtros y el layout hechos — solo les das de comer el JSON.
  Esto es más rápido y más consistente que pedirle HTML completo a Claude
  cada vez, y evita que un output raro de Claude rompa el diseño.
- **Sin notificación push al usuario:** tal como se definió, el usuario debe
  volver a consultar su link (o la lista de "solicitudes anteriores" en
  `index.html`, ahora que tiene cuenta). La página hace polling automático
  cada 10s mientras está abierta, pero no hay ningún aviso si la cierra.
