# Deploy — GitHub + Render (real) / Google Cloud Run (alternativo)

Esta guía asume que ya tenés el proyecto corriendo local (ver `README.md`) y
Supabase configurado (auth + el schema de `backend/supabase/schema.sql` +
el bucket `cv-files`, ver "Configurar Supabase" en `README.md`). El
despliegue real de este proyecto es en **Render** — la sección de Cloud Run
más abajo queda documentada como alternativa, no es la que se usa hoy.

**Importante — almacenamiento:** desde que el backend migró a Supabase
(Postgres + Storage) para sesiones, CVs, notificaciones y el token de
Drive, el filesystem del contenedor ya no guarda ningún dato de la
aplicación. Esto es justamente lo que permite desplegar en Render sin
Persistent Disk (que además requiere un plan pago) — antes de esta
migración, cualquier archivo local se perdía en cada redeploy.

---

## 1. Subir el proyecto a GitHub

Desde `job-finder/` (la raíz del proyecto, no `backend/`):

```bash
git init
git add .
git commit -m "Job Finder MVP"
git remote add origin https://github.com/TU-USUARIO/job-finder.git
git branch -M main
git push -u origin main
```

Con el `.gitignore` que ya tiene el proyecto, no se sube `backend/.env` ni
`venv/` — así que tus credenciales reales nunca llegan a GitHub. Antes de
pushear, confirmá con `git status` que ninguno de esos archivos aparece en
el commit.

---

## 2. Deploy — Render (real)

1. En [render.com](https://dashboard.render.com), creá un **Web Service**
   nuevo conectado a tu repo de GitHub. Render detecta el `Dockerfile` de la
   raíz del proyecto automáticamente (tipo de deploy "Docker").
2. En la pestaña **Environment** del servicio, cargá las variables (ver
   tabla completa al final de este documento):
   ```
   SUPABASE_URL=https://tu-project-ref.supabase.co
   SUPABASE_ANON_KEY=sb_publishable_xxx
   SUPABASE_SERVICE_ROLE_KEY=xxx   (Project Settings → API → "service_role")
   ADMIN_EMAIL=conversandoapp@gmail.com
   BACKOFFICE_EMAILS=                (opcional, lista de emails separados por coma)
   NOTIFY_EMAIL_ENABLED=false
   DRIVE_ENABLED=false
   ```
3. Desplegá. Render te da una URL pública tipo
   `https://job-finder-xxxx.onrender.com`. Abrila y probá `/index.html`.
4. Cada `git push` a la rama conectada dispara un redeploy automático (esto
   ya viene activado por default en Render, a diferencia de Cloud Run).

### Activar email y Drive en Render (opcional)

Mismas variables que local, cargadas en la pestaña **Environment**:
```
NOTIFY_EMAIL_ENABLED=true
NOTIFY_EMAIL_APP_PASSWORD=xxxx xxxx xxxx xxxx
```

Para Drive (ver "Activar Google Drive real" en `README.md` para el detalle
completo del setup en Google Cloud Console):
```
DRIVE_ENABLED=true
DRIVE_OAUTH_CLIENT_ID=xxx.apps.googleusercontent.com
DRIVE_OAUTH_CLIENT_SECRET=xxx
DRIVE_OAUTH_REDIRECT_URI=https://tu-servicio.onrender.com/api/admin/drive/oauth2callback
```

Después de desplegar, entrá a `/admin` logueado como admin y hacé
click en "☁️ Conectar Google Drive" una sola vez — el token queda guardado
en la tabla `app_settings` de Supabase (se refresca solo de ahí en
adelante, sin volver a pedir consentimiento salvo que revoques el acceso
desde tu cuenta de Google).

`DRIVE_FOLDER_ID` es opcional: si no lo seteás, la app busca o crea sola
una carpeta "Job Finder - CVs recibidos" en tu Drive la primera vez que
sube un CV.

---

## Resumen de variables de entorno

Las mismas que en `backend/.env.example`, cargadas en la pestaña
**Environment** de Render (o como secretos, para las sensibles):

| Variable | Obligatoria | Notas |
|---|---|---|
| `SUPABASE_URL` | Sí | |
| `SUPABASE_ANON_KEY` | Sí | |
| `SUPABASE_SERVICE_ROLE_KEY` | Sí | secreta — Project Settings → API → "service_role" |
| `SUPABASE_JWT_SECRET` | No | vacío en proyectos nuevos de Supabase |
| `ADMIN_EMAIL` | Sí | |
| `BACKOFFICE_EMAILS` | No | lista separada por coma; el admin ya tiene este permiso automáticamente |
| `APP_BASE_URL` | No | URL pública del servicio, usada en los links de los emails de notificación; default `https://job-finder-scwk.onrender.com` |
| `NOTIFY_EMAIL_ENABLED` | No | `false` si no configurás email |
| `NOTIFY_EMAIL_APP_PASSWORD` | No | secreta |
| `DRIVE_ENABLED` | No | `false` si no configurás Drive |
| `DRIVE_OAUTH_CLIENT_ID` | No | del cliente OAuth tipo "Aplicación web" |
| `DRIVE_OAUTH_CLIENT_SECRET` | No | secreta |
| `DRIVE_OAUTH_REDIRECT_URI` | No | tu URL de Render + `/api/admin/drive/oauth2callback` |
| `DRIVE_FOLDER_ID` | No | opcional, se autodetecta/crea si se deja vacío |

---

## Alternativa — Google Cloud Run (no usado actualmente)

Esta sección queda documentada por si en algún momento se prefiere migrar
de Render a Cloud Run, pero **no es el despliegue real del proyecto hoy**.

**Por qué Cloud Run:** es la forma más simple de correr un contenedor sin
gestionar servidores, escala a cero cuando nadie lo usa (barato para un
MVP) y `gcloud run deploy --source` te construye la imagen automáticamente
sin que tengas que manejar Docker a mano.

### A. Preparar Google Cloud

1. Instalá el [gcloud CLI](https://cloud.google.com/sdk/docs/install) si no
   lo tenés.
2. Autenticate y elegí (o creá) un proyecto de GCP:
   ```bash
   gcloud auth login
   gcloud projects create job-finder-mvp --name="Job Finder MVP"
   gcloud config set project job-finder-mvp
   ```
   (Si ya tenés un proyecto de GCP, usá su ID en vez de crear uno nuevo.)
3. Habilitá las APIs necesarias:
   ```bash
   gcloud services enable run.googleapis.com cloudbuild.googleapis.com \
     artifactregistry.googleapis.com
   ```
4. Elegí una región (ejemplo: `us-central1`, o `southamerica-east1` si
   preferís algo más cerca de LATAM):
   ```bash
   gcloud config set run/region us-central1
   ```

### B. Deploy

Desde `job-finder/` (donde está el `Dockerfile`):

```bash
gcloud run deploy job-finder `
  --source . `
  --allow-unauthenticated `
  --set-env-vars="SUPABASE_URL=https://tu-project-ref.supabase.co,SUPABASE_ANON_KEY=sb_publishable_xxx,SUPABASE_SERVICE_ROLE_KEY=xxx,ADMIN_EMAIL=conversandoapp@gmail.com,BACKOFFICE_EMAILS=,NOTIFY_EMAIL_ENABLED=false,DRIVE_ENABLED=false"
```

(En PowerShell el salto de línea es con `` ` ``; en bash/Mac/Linux usá `\`
en su lugar.)

`--allow-unauthenticated`: para que cualquiera pueda entrar a la app desde
el navegador (la seguridad real la da el login de Supabase, no IAM de
GCP). Ya no hace falta `--max-instances=1` ni montar ningún bucket como
almacenamiento persistente — desde la migración a Supabase, el filesystem
del contenedor no guarda ningún dato de la aplicación, así que Cloud Run
puede escalar a más de una instancia sin riesgo de escrituras concurrentes
pisándose (Postgres maneja eso).

Cuando termine, te da una URL pública tipo
`https://job-finder-xxxxx-uc.a.run.app`. Abrila y probá `/index.html`.

### C. Activar email y Drive (opcional)

```bash
gcloud run services update job-finder `
  --set-env-vars="NOTIFY_EMAIL_ENABLED=true,NOTIFY_EMAIL_APP_PASSWORD=xxxx xxxx xxxx xxxx"
```

```bash
gcloud run services update job-finder `
  --set-env-vars="DRIVE_ENABLED=true,DRIVE_OAUTH_CLIENT_ID=xxx.apps.googleusercontent.com,DRIVE_OAUTH_REDIRECT_URI=https://job-finder-xxxxx-uc.a.run.app/api/admin/drive/oauth2callback" `
  --set-secrets="DRIVE_OAUTH_CLIENT_SECRET=drive-oauth-client-secret:latest,SUPABASE_SERVICE_ROLE_KEY=supabase-service-role:latest"
```

(Los secretos sensibles conviene guardarlos en Secret Manager en vez de
pasarlos en texto plano: `gcloud secrets create drive-oauth-client-secret --data-file=-`
y pegar el valor, o `echo -n "el-secret" | gcloud secrets create drive-oauth-client-secret --data-file=-`.)

### D. Actualizar el deploy cuando cambies código

```bash
git add .
git commit -m "descripción del cambio"
git push
gcloud run deploy job-finder --source .
```

**Opcional — deploy automático al hacer push a GitHub:** se puede conectar
un trigger de Cloud Build al repo de GitHub (Cloud Console → Cloud Build →
Triggers → Connect Repository) para que cada `git push` a `main` dispare un
deploy solo.
