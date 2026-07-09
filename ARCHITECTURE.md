# Arquitectura de Job Finder

Mapa técnico completo del repo: qué hace cada pieza y cómo se conectan. Para
"cómo levantar el proyecto local" ver `README.md`; para "cómo desplegarlo" ver
`DEPLOY.md`. Este documento es el que explica **cómo funciona todo junto**.

---

## 1. Qué es esto

Un MVP **sin agentes de IA corriendo en el servidor**: el "motor" de
optimización de CVs y búsqueda de vacantes es un humano (el admin, hoy una
sola persona) asistido por Claude — a mano vía copiar/pegar prompts, o de
forma semi-automatizada con los Claude Code skills en `.claude/skills/`. El
backend es solo el andamiaje: auth, estado de cada solicitud, almacenamiento
de archivos y notificaciones.

Journey de un candidato:
1. Sube su CV en `/index.html` → queda en estado `pending`.
2. El admin lo optimiza (a mano o con el skill `cv-optimizer-jobfinder`) y
   sube el `.docx` + `cv_analysis.json` desde `/admin`.
3. El candidato ve el resultado en `/resultado.html` (scores ATS, keywords,
   roles objetivo, link de descarga) y pide "buscar vacantes".
4. El admin arma la plataforma de vacantes (a mano o con el skill
   `vacantes-linkedin-jobfinder`) y sube el `vacantes.json`.
5. El candidato ve `/vacantes.html`, una plataforma tipo LinkedIn armada
   100% a partir de ese JSON (cards, filtros, top 5, stats).

No hay notificaciones push al candidato: las páginas hacen polling cada 10s
mientras están abiertas, y se puede cerrar y volver más tarde con el mismo
link.

---

## 2. Stack

| Capa | Tecnología |
|---|---|
| Backend | Python, FastAPI, servido con `uvicorn` |
| Frontend | HTML/CSS/JS plano, sin build step ni framework |
| Auth | Supabase Auth (JWT verificado en el backend vía JWKS, sin el SDK completo) |
| Datos + archivos | Supabase (Postgres + Storage) |
| CV en Drive (opcional) | Google Drive API, OAuth 2.0 delegado al usuario |
| Despliegue real | Render (Docker) |
| Despliegue alternativo | Google Cloud Run (documentado, no usado hoy) |
| Automatización de CV/vacantes | Claude Code skills (`.claude/skills/`) |

---

## 3. Estructura de carpetas

```
job-finder/
├── .claude/skills/              # skills de Claude Code (ver sección 8)
│   ├── cv-optimizer-jobfinder/
│   └── vacantes-linkedin-jobfinder/
├── backend/
│   ├── app.py                   # FastAPI: todos los endpoints + sirve el frontend
│   ├── requirements.txt
│   ├── .env.example
│   ├── services/
│   │   ├── db.py                # cliente Supabase (Postgres + Storage)
│   │   ├── sessions.py          # CRUD de la tabla `sessions`
│   │   ├── auth.py              # verifica JWT de Supabase, detecta admin
│   │   ├── notifications.py     # email real + tabla `notifications`
│   │   ├── storage_drive.py     # sube el CV original a Google Drive (opcional)
│   │   └── drive_oauth.py       # flujo OAuth de conexión con Drive
│   ├── supabase/schema.sql      # DDL a correr una vez en el proyecto de Supabase
│   └── schemas/                 # prompts manuales + JSON de ejemplo (fallback de los skills)
└── frontend/                    # una página HTML + un .js por vista, sin build step
    ├── auth.js / auth.css       — cliente Supabase compartido, guards de sesión
    ├── login.html / login.js    — signup + login de usuarios normales
    ├── admin-login.html/.js     — login exclusivo de la cuenta admin
    ├── backoffice-login.html/.js — login exclusivo de cuentas backoffice
    ├── index.html / app.js      — subir CV + ver solicitudes anteriores
    ├── resultado.html/.js       — ver análisis ATS + pedir vacantes
    ├── vacantes.html/.js/.css   — plataforma de vacantes (data-driven)
    ├── admin.html / admin.js    — panel admin
    ├── backoffice.html / backoffice.js — panel backoffice (revisa antes de que el candidato vea el CV/vacantes)
    └── styles.css               — tokens de diseño compartidos (color, tipografía, sombras)
```

---

## 4. Modelo de datos (Supabase)

Definido en `backend/supabase/schema.sql`. **RLS deshabilitado a propósito**:
el frontend solo usa Supabase para auth (nunca consulta estas tablas
directo); toda la autorización la hace el backend en Python
(`services/auth.py`) con la `service_role` key.

### Tabla `sessions`
Una fila por solicitud de un candidato. Reemplaza lo que antes era una
carpeta + `request.json` en el filesystem local.

| Columna | Qué es |
|---|---|
| `session_id` (PK, uuid) | identifica la solicitud en todas las URLs (`?session=...`) |
| `user_id`, `user_email` | dueño de la sesión (para `ensure_owner_or_backoffice`) |
| `candidate_name`, `pais`, `linkedin_url` | datos del formulario inicial |
| `cv_status` | `pending` \| `pending_review` \| `ready` \| `error` |
| `jobs_status` | `not_requested` \| `pending` \| `pending_review` \| `ready` \| `error` |
| `cv_original_path`, `cv_optimizado_path` | keys de objetos en el bucket `cv-files` |
| `cv_drive_link` | link de Drive del CV original (si `DRIVE_ENABLED=true`) |
| `cv_scores` (jsonb) | el `cv_analysis.json` que sube el admin — lo lee `resultado.js` |
| `vacantes` (jsonb) | el `vacantes.json` que sube el admin — lo lee `vacantes.js` |
| `cv_review_note`, `jobs_review_note` | nota opcional que deja backoffice al rechazar (se limpia al reintentar/aprobar) |
| `cv_requested_at/ready_at`, `jobs_requested_at/ready_at` | timestamps del flujo |

### Tabla `notifications`
Log de avisos al admin (reemplaza `notifications.log`). `id`, `created_at`,
`subject`, `body`. Se llena siempre (haya o no email real activado) —
`GET /api/admin/notifications` la lee para la pestaña "Notificaciones".

### Tabla `app_settings`
Key-value genérico. Uso actual:
- `drive_token` — credenciales OAuth de Google Drive (reemplaza un archivo local)
- `drive_oauth_pending_state` — el `state` pendiente entre `/authorize` y `/oauth2callback`

### Storage — bucket `cv-files` (privado)
Objetos en `{session_id}/cv_original{ext}` y `{session_id}/cv_optimizado{ext}`.
Privado porque el backend proxea las descargas aplicando sus propios checks
de autorización (`db.download_file` + `Response` con `content-disposition`,
nunca una URL pública directa).

---

## 5. Backend — mapa de endpoints (`backend/app.py`)

| Endpoint | Quién | Qué hace |
|---|---|---|
| `GET /api/config` | público | expone `SUPABASE_URL`/`SUPABASE_ANON_KEY` al frontend |
| `GET /api/whoami` | usuario logueado | `{id, email, is_admin, is_backoffice}` |
| `POST /api/analyze` | usuario | crea la sesión, sube el CV original a Storage (+ Drive opcional), notifica al admin |
| `POST /api/suggest-roles` | usuario | filtro rápido de puestos sugeridos, sin persistir nada |
| `GET /api/my-sessions` | usuario | lista sus propias sesiones |
| `GET /api/status/{id}` | dueño o backoffice | estado crudo de la sesión |
| `GET /api/result/{id}` | dueño o backoffice | `cv_scores` una vez `cv_status=ready` (o en `pending_review`, para que backoffice previsualice) |
| `GET /api/download/cv/{id}` | dueño o backoffice | descarga el CV optimizado desde Storage |
| `POST /api/jobs` | dueño o admin | marca `jobs_status=pending`, notifica al admin (backoffice no puede disparar esta acción) |
| `GET /api/vacantes/{id}` | dueño o backoffice | el JSON de vacantes una vez `jobs_status=ready` (o en `pending_review`, para previsualizar) |
| `GET /api/admin/requests` | admin | todas las sesiones (para `/admin`) |
| `GET /api/admin/notifications` | admin | historial de avisos |
| `GET /api/admin/download/original/{id}` | admin | descarga el CV original |
| `GET /api/admin/drive/authorize` | admin | arma la URL de consentimiento de Google (ver sección 7) |
| `GET /api/admin/drive/oauth2callback` | Google (redirect) | intercambia el `code`, guarda el token |
| `POST /api/admin/{id}/cv` | admin | sube CV optimizado + `cv_analysis.json`, marca `cv_status=pending_review` (espera aprobación de backoffice) |
| `POST /api/admin/{id}/vacantes` | admin | sube `vacantes.json`, marca `jobs_status=pending_review` |
| `GET /api/backoffice/requests` | backoffice | todas las sesiones (para `/backoffice`) |
| `POST /api/backoffice/{id}/cv/approve` \| `/reject` \| `/replace` | backoffice | aprueba (`cv_status=ready`), rechaza (vuelve a `pending`, nota opcional) o reemplaza (sube su propio archivo y aprueba) el CV pendiente de revisión |
| `POST /api/backoffice/{id}/vacantes/approve` \| `/reject` \| `/replace` | backoffice | análogo para `vacantes.json` |
| `/` (StaticFiles) | público | sirve todo `frontend/` |

### Servicios (`backend/services/`)
- **`auth.py`** — verifica el JWT de Supabase contra las JWKS del proyecto
  (asimétrico ES256/RS256, con fallback legacy HS256 vía
  `SUPABASE_JWT_SECRET`). El admin es **un solo email** (`ADMIN_EMAIL`) y
  backoffice es una **lista de emails** (`BACKOFFICE_EMAILS`), ninguno un rol
  en base de datos — `is_backoffice(user) = is_admin(user) OR email in
  BACKOFFICE_EMAILS` (el admin siempre incluye permisos de backoffice).
  Expone `get_current_user`, `require_admin`, `require_backoffice`,
  `ensure_owner_or_admin`, `ensure_owner_or_backoffice` como dependencias de
  FastAPI.
- **`sessions.py`** — CRUD de la tabla `sessions` vía `db.py`.
- **`notifications.py`** — envía email real por Gmail SMTP si
  `NOTIFY_EMAIL_ENABLED=true`, y **siempre** además inserta en la tabla
  `notifications` (para que el panel admin tenga el historial completo pase
  lo que pase con el email).
- **`db.py`** — único punto de acceso a Supabase (cliente `supabase-py` con
  la `service_role` key). Expone `get_setting`/`set_setting` (tabla
  `app_settings`) y `upload_file`/`download_file` (bucket `cv-files`).
- **`storage_drive.py`** — sube el CV **original** a Google Drive como copia
  de conveniencia para el admin, si `DRIVE_ENABLED=true`. Busca o crea sola
  una carpeta "Job Finder - CVs recibidos" (scope `drive.file`, no hace
  falta compartir nada a mano). Nunca rompe el flujo principal: cualquier
  falla cae en un `except` silencioso.
- **`drive_oauth.py`** — arma la URL de consentimiento OAuth y canjea el
  `code` por credenciales; guarda todo en `app_settings` (no en disco, ver
  sección 7).

---

## 6. Frontend — una página por vista, sin build step

Todas cargan `@supabase/supabase-js` por CDN + `auth.js` (cliente Supabase
compartido, con `requireAuth`/`requireAdmin`/`requireBackoffice`/`authFetch`/
`renderUserBar`) + su propio `.js`.

| Página | JS | Qué muestra |
|---|---|---|
| `index.html` | `app.js` | form de subida de CV (dropzone) + solicitudes anteriores |
| `resultado.html` | `resultado.js` | polling de `cv_status`; scores ATS, keywords, debilidades, roles, botón de descarga, CTA "buscar vacantes" (si es backoffice previsualizando un `pending_review`, muestra un banner y oculta la CTA) |
| `vacantes.html` | `vacantes.js` | polling de `jobs_status`; plataforma data-driven (sidebar por categoría, stats, top 5, cards, filtros) |
| `login.html` | `login.js` | signup/login de candidatos (split-screen con panel de marca) |
| `admin-login.html` | `admin-login.js` | login exclusivo del admin |
| `backoffice-login.html` | `backoffice-login.js` | login exclusivo de cuentas backoffice |
| `admin.html` | `admin.js` | solicitudes pendientes/pasadas, formularios de subida, notificaciones, botón "Conectar Google Drive" |
| `backoffice.html` | `backoffice.js` | "Por revisar" (aprobar/rechazar/reemplazar CV y vacantes en `pending_review`) + "Todas las solicitudes" (solo lectura) |

`styles.css` centraliza los tokens de diseño (paleta de azules, sombras,
tipografía Inter) — `vacantes.css`/`admin.css`/`auth.css` los reutilizan via
custom properties, no hex hardcodeado.

---

## 7. Google Drive — OAuth de usuario (no service account)

Las cuentas de servicio de Google no tienen cuota de almacenamiento propia,
así que la integración usa **OAuth delegado a la cuenta Gmail del admin**.
Como el servicio se despliega en Render sin ejecución local, la
autorización de una sola vez se hace enteramente contra el servicio ya
desplegado:

1. Admin logueado en `/admin` → click "Conectar Google Drive".
2. `GET /api/admin/drive/authorize` (protegido, requiere admin) arma la URL
   de consentimiento y guarda el `state` en `app_settings`.
3. El navegador va a Google, el admin acepta.
4. Google redirige a `GET /api/admin/drive/oauth2callback` (sin auth header
   posible — se valida el `state` en su lugar). Se canjea el `code`, se
   guarda el token en `app_settings.drive_token`.
5. `storage_drive.py` lee y refresca ese token en cada subida.

`DRIVE_ENABLED=false` (default) desactiva todo esto sin romper nada — los
CVs igual quedan en Supabase Storage.

---

## 8. Skills de Claude Code (`.claude/skills/`)

Automatizan lo que `backend/schemas/prompt_para_claude_*.md` documenta como
proceso manual (copiar/pegar prompts en el chat web de Claude). Ambos son
**project-scoped**: Claude Code los detecta solo al abrir esta carpeta.

- **`cv-optimizer-jobfinder`** — input: CV original (PDF/DOCX). Extrae texto,
  identifica roles objetivo, puntúa ATS contra el rol #1 (mejor match),
  reescribe el CV sin inventar información, genera el `.docx` optimizado +
  `cv_analysis.json` (esquema mínimo: `ats_score_original`,
  `ats_score_optimizado`, `roles_objetivo`, `keywords_agregados`,
  `debilidades`).
- **`vacantes-linkedin-jobfinder`** — input: el CV **optimizado**. Navega
  LinkedIn Jobs en Chrome (herramientas tipo claude-in-chrome), clasifica
  vacantes en 5 categorías (`alta_relevancia`, `ventaja_interna`,
  `remoto_latam`, `media`, `especializado`) y genera `vacantes.json`
  (esquema mínimo: `candidato.nombre`, `stats`, `top5_ids`,
  `notas_estrategia`, `vacantes[]`).

Ninguno de los dos sube archivos a la API directamente — el admin sigue
subiéndolos a mano desde `/admin`, solo que ya vienen listos.

---

## 9. Despliegue y entornos

Real: **Render** (Docker, auto-deploy en cada push). Alternativa
documentada pero no usada: Google Cloud Run. Ver `DEPLOY.md` para el
paso a paso completo y la tabla de variables de entorno
(`SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_ROLE_KEY`,
`ADMIN_EMAIL`, `NOTIFY_EMAIL_*`, `DRIVE_*`).

Como todo el estado vive en Supabase (no en el filesystem del contenedor),
no hace falta ningún disco persistente ni límite de instancias — a
diferencia del diseño original de este MVP, que sí dependía de un
filesystem local de una sola instancia.

---

## 10. Decisiones notables

- **Sin base de datos propia al inicio, migrada a Supabase después:** el
  diseño original guardaba todo en archivos locales (más simple para un
  MVP de una persona). Se migró a Supabase Postgres/Storage cuando se
  detectó que Render no persiste el filesystem entre despliegues.
- **El admin y el backoffice son listas de emails, no una tabla de roles:**
  alcanza para el volumen de personas administrando/revisando hoy; si crece
  mucho o hacen falta permisos más finos, conviene migrar a una tabla de
  roles en Supabase.
- **Backoffice como paso de aprobación, no como reemplazo del admin:** el
  admin sigue siendo el único que puede *iniciar* una carga de CV
  optimizado/vacantes (`POST /api/admin/*`); backoffice solo puede actuar
  sobre lo que ya está en `pending_review` (aprobar/rechazar/reemplazar).
  Por la jerarquía de permisos, el propio admin también puede aprobar sus
  propias cargas si no hay otra cuenta de backoffice — es una elección
  consciente para no bloquear el flujo con un solo operador.
- **JSON en vez de HTML para vacantes y análisis de CV:** el admin (o los
  skills) siguen usando Claude para todo el trabajo de análisis/redacción,
  pero el output es datos estructurados — las páginas ya tienen el diseño
  hecho, solo les dan de comer el JSON.
- **Sin notificación push al candidato:** decisión explícita del MVP; el
  candidato vuelve a consultar su link (o su lista de solicitudes).
