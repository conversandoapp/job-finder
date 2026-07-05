# Deploy — GitHub + Google Cloud Run

Esta guía asume que ya tenés el proyecto corriendo local (ver `README.md`) y
Supabase configurado. Cubre: subir el código a GitHub, y desplegar el
backend (que también sirve el frontend) en Cloud Run.

**Por qué Cloud Run:** es la forma más simple de correr un contenedor sin
gestionar servidores, escala a cero cuando nadie lo usa (barato para un
MVP) y `gcloud run deploy --source` te construye la imagen automáticamente
sin que tengas que manejar Docker a mano.

**Importante — almacenamiento persistente:** el sistema actual guarda los
CVs y el estado de cada sesión como archivos en `backend/storage/`. En
Cloud Run el filesystem del contenedor es efímero (se borra en cada nuevo
despliegue o reinicio) y pueden correr varias instancias en paralelo. Para
que `backend/storage/` persista igual que en tu máquina, esta guía monta un
bucket de Cloud Storage ahí — el código no cambia, Cloud Run hace que el
bucket se vea como una carpeta local.

---

## 1. Subir el proyecto a GitHub

Desde `job-finder/` (la raíz del proyecto, no `backend/`):

```bash
cd "C:\dev\MVP Job finder\job-finder"
git init
git add .
git commit -m "Job Finder MVP"
```

Creá el repo en GitHub (desde la web, botón "New repository", sin
inicializarlo con README) y conectalo:

```bash
git remote add origin https://github.com/TU-USUARIO/job-finder.git
git branch -M main
git push -u origin main
```

Con el `.gitignore` que ya tiene el proyecto, no se suben `backend/.env`,
`backend/storage/` (donde vive `drive_token.json` una vez que conectás
Drive) ni `venv/` — así que tus credenciales reales nunca llegan a GitHub.
Antes de pushear, confirmá con `git status` que ninguno de esos archivos
aparece en el commit.

---

## 2. Preparar Google Cloud

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
     artifactregistry.googleapis.com storage.googleapis.com
   ```
4. Elegí una región (ejemplo: `us-central1`, o `southamerica-east1` si
   preferís algo más cerca de LATAM):
   ```bash
   gcloud config set run/region us-central1
   ```

---

## 3. Crear el bucket para almacenamiento persistente

```bash
gcloud storage buckets create gs://job-finder-mvp-storage --location=us-central1
```

(El nombre del bucket tiene que ser único a nivel global en GCS — si
`job-finder-mvp-storage` ya está tomado, agregale algo distintivo, ej.
`job-finder-mvp-storage-tunombre`.)

---

## 4. Primer deploy a Cloud Run

Desde `job-finder/` (donde está el `Dockerfile`):

```bash
gcloud run deploy job-finder `
  --source . `
  --allow-unauthenticated `
  --max-instances=1 `
  --set-env-vars="SUPABASE_URL=https://tu-project-ref.supabase.co,SUPABASE_ANON_KEY=sb_publishable_xxx,ADMIN_EMAIL=conversandoapp@gmail.com,NOTIFY_EMAIL_ENABLED=false,DRIVE_ENABLED=false"
```

(En PowerShell el salto de línea es con `` ` ``; en bash/Mac/Linux usá `\`
en su lugar.)

Notas sobre estas flags:
- `--allow-unauthenticated`: para que cualquiera pueda entrar a la app
  desde el navegador (la seguridad real la da el login de Supabase, no
  IAM de GCP).
- `--max-instances=1`: importante para este MVP. Como el estado de las
  sesiones vive en archivos (no en una base de datos), correr más de una
  instancia en paralelo podría hacer que dos requests pisen el mismo
  archivo. Con una sola instancia evitás ese problema. Si más adelante
  necesitás más tráfico, hay que migrar `sessions.py` a una base de datos
  real (Postgres de Supabase, por ejemplo) para poder escalar sin este límite.
- No incluí `NOTIFY_EMAIL_APP_PASSWORD` ni las variables de Drive en el
  primer deploy — las agregamos en el paso 6 si las vas a usar.

Cuando termine, te da una URL pública tipo
`https://job-finder-xxxxx-uc.a.run.app`. Abrila y probá `/index.html`.

---

## 5. Montar el bucket como almacenamiento persistente

El primer deploy ya funciona, pero `backend/storage/` vive en el disco
efímero del contenedor. Para que persista entre despliegues, montá el
bucket del paso 3:

```bash
gcloud beta run services update job-finder `
  --add-volume=name=storage-vol,type=cloud-storage,bucket=job-finder-mvp-storage `
  --add-volume-mount=volume=storage-vol,mount-path=/app/backend/storage
```

A partir de ahora, todo lo que el backend escriba en
`backend/storage/` (CVs, `request.json`, `vacantes.json`, el log de
notificaciones) queda guardado en el bucket, visible incluso si Cloud Run
reinicia el contenedor o hacés un nuevo deploy.

**Limitación a tener en cuenta:** el bucket montado como filesystem no
soporta escrituras concurrentes seguras al mismo archivo (gana la última
escritura). Con `--max-instances=1` y el volumen de tráfico esperado para
este MVP no debería ser un problema — es algo a revisar solo si el proyecto
crece mucho.

---

## 6. Activar email y Drive en producción (opcional)

Mismos valores que usás local, seteados como variables de entorno del
servicio:

```bash
gcloud run services update job-finder `
  --set-env-vars="NOTIFY_EMAIL_ENABLED=true,NOTIFY_EMAIL_APP_PASSWORD=xxxx xxxx xxxx xxxx"
```

Para Drive, ya no se usa una cuenta de servicio (ver README.md — no tienen
cuota de almacenamiento propia). En vez de eso, el admin conecta su propia
cuenta de Google por OAuth desde `/admin.html`, así que solo hace falta
configurar las variables del cliente OAuth (creado como tipo "Aplicación
web" en Google Cloud Console, con redirect URI apuntando a tu URL de
Cloud Run + `/api/admin/drive/oauth2callback`):

```bash
gcloud run services update job-finder `
  --set-env-vars="DRIVE_ENABLED=true,DRIVE_OAUTH_CLIENT_ID=xxx.apps.googleusercontent.com,DRIVE_OAUTH_REDIRECT_URI=https://job-finder-xxxxx-uc.a.run.app/api/admin/drive/oauth2callback" `
  --set-secrets="DRIVE_OAUTH_CLIENT_SECRET=drive-oauth-client-secret:latest"
```

(El client secret sí conviene guardarlo en Secret Manager en vez de pasarlo
en texto plano, igual que `NOTIFY_EMAIL_APP_PASSWORD`:
`gcloud secrets create drive-oauth-client-secret --data-file=-` y pegar el
valor, o `echo -n "el-secret" | gcloud secrets create drive-oauth-client-secret --data-file=-`.)

Después de desplegar, entrá a `/admin.html` logueado como admin y hacé
click en "☁️ Conectar Google Drive" una sola vez — el token queda guardado
en `backend/storage/drive_token.json`, que ya persiste en el bucket montado
en el paso 5 (se refresca solo de ahí en adelante, sin volver a pedir
consentimiento salvo que revoques el acceso desde tu cuenta de Google).

`DRIVE_FOLDER_ID` es opcional: si no lo seteás, la app busca o crea sola
una carpeta "Job Finder - CVs recibidos" en tu Drive la primera vez que
sube un CV.

---

## 7. Actualizar el deploy cuando cambies código

Cada vez que quieras subir cambios:

```bash
git add .
git commit -m "descripción del cambio"
git push

gcloud run deploy job-finder --source .
```

**Opcional — deploy automático al hacer push a GitHub:** se puede conectar
un trigger de Cloud Build al repo de GitHub (Cloud Console → Cloud Build →
Triggers → Connect Repository) para que cada `git push` a `main` dispare un
deploy solo. Para un MVP donde el deploy manual es cada tanto, no es
necesario — pero está la opción si te resulta más cómodo.

---

## Resumen de variables de entorno en Cloud Run

Las mismas que en `backend/.env.example`, seteadas como env vars (o
secretos para las sensibles) del servicio en vez de un archivo:

| Variable | Obligatoria | Notas |
|---|---|---|
| `SUPABASE_URL` | Sí | |
| `SUPABASE_ANON_KEY` | Sí | |
| `SUPABASE_JWT_SECRET` | No | vacío en proyectos nuevos de Supabase |
| `ADMIN_EMAIL` | Sí | |
| `NOTIFY_EMAIL_ENABLED` | No | `false` si no configurás email |
| `NOTIFY_EMAIL_APP_PASSWORD` | No | mejor como Secret Manager |
| `DRIVE_ENABLED` | No | `false` si no configurás Drive |
| `DRIVE_OAUTH_CLIENT_ID` | No | del cliente OAuth tipo "Aplicación web" |
| `DRIVE_OAUTH_CLIENT_SECRET` | No | mejor como Secret Manager |
| `DRIVE_OAUTH_REDIRECT_URI` | No | tu URL de Cloud Run + `/api/admin/drive/oauth2callback` |
| `DRIVE_TOKEN_PATH` | No | default `backend/storage/drive_token.json`, ya persiste solo |
| `DRIVE_FOLDER_ID` | No | opcional, se autodetecta/crea si se deja vacío |
