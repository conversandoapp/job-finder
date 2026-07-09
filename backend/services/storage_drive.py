"""
Sube el CV original a Google Drive para que el admin lo tenga disponible.

Modo real: OAuth 2.0 delegado a tu propia cuenta de Google (NO una cuenta
de servicio). Las cuentas de servicio no tienen cuota de almacenamiento
propia, así que no pueden usarse para subir archivos salvo que tengas
Google Workspace (Shared Drives / domain-wide delegation). Con una cuenta
Gmail personal, la única opción es autorizar la app una vez como tu propio
usuario y guardar un refresh token -- los archivos se suben con tu cuota
normal (15GB gratis).

  Setup (una sola vez, sin nada local -- ver README.md "Activar Google
  Drive real" para el detalle completo):
  1. Crear un proyecto en https://console.cloud.google.com/ y habilitar
     "Google Drive API".
  2. Pantalla de consentimiento OAuth: tipo External, Publishing status
     "In production" (en "Testing" el refresh token expira a los 7 días).
  3. Credenciales -> "Crear credenciales" -> "ID de cliente de OAuth" ->
     tipo "Aplicación web", con redirect URI
     "<url-del-servicio>/api/admin/drive/oauth2callback".
  4. En las variables de entorno del servicio: DRIVE_OAUTH_CLIENT_ID,
     DRIVE_OAUTH_CLIENT_SECRET, DRIVE_OAUTH_REDIRECT_URI, DRIVE_ENABLED=true.
  5. Entrar a /admin logueado como admin y hacer click en
     "Conectar Google Drive" -- eso guarda el token en la tabla
     app_settings de Supabase (ver drive_oauth.py).

La carpeta de destino se busca/crea automáticamente la primera vez que se
sube un CV (no hace falta crearla ni compartirla a mano): el scope
drive.file solo da acceso a archivos que esta app creó o abrió, por eso no
sirve compartir una carpeta ya existente como en el flujo viejo de service
account.

Modo simulado (default): el CV se guarda únicamente en Supabase Storage
(ver services/db.py). La app funciona igual, pero sin subir nada a Drive
hasta que actives el modo real -- Drive acá es solo una copia extra de
conveniencia para el admin, no el almacenamiento principal.
"""
import io
import json
import os

from services import db

DRIVE_FOLDER_NAME = "Job Finder - CVs recibidos"
SCOPES = ["https://www.googleapis.com/auth/drive.file"]

_folder_id_cache: str | None = None


def _get_credentials():
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials

    token_data = db.get_setting("drive_token")
    if not token_data:
        raise RuntimeError(
            "No hay token de Drive todavía. Entra a /admin y haz clic "
            "en 'Conectar Google Drive'."
        )

    creds = Credentials.from_authorized_user_info(token_data, scopes=SCOPES)

    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        db.set_setting("drive_token", json.loads(creds.to_json()))

    return creds


def _get_or_create_folder_id(service, folder_id_env: str) -> str | None:
    global _folder_id_cache

    if folder_id_env:
        return folder_id_env
    if _folder_id_cache:
        return _folder_id_cache

    query = (
        f"name='{DRIVE_FOLDER_NAME}' and mimeType='application/vnd.google-apps.folder' "
        "and trashed=false"
    )
    results = service.files().list(q=query, fields="files(id)", pageSize=1).execute()
    files = results.get("files", [])
    if files:
        _folder_id_cache = files[0]["id"]
        return _folder_id_cache

    created = service.files().create(
        body={"name": DRIVE_FOLDER_NAME, "mimeType": "application/vnd.google-apps.folder"},
        fields="id",
    ).execute()
    _folder_id_cache = created["id"]
    return _folder_id_cache


def upload_cv_to_drive(content: bytes, session_id: str, filename: str) -> str | None:
    """Devuelve el link de Drive si se subió, o None si está en modo simulado
    o si falla la subida (nunca debe romper el flujo principal)."""
    enabled = os.getenv("DRIVE_ENABLED", "false").lower() == "true"
    if not enabled:
        return None

    try:
        from googleapiclient.discovery import build
        from googleapiclient.http import MediaIoBaseUpload

        folder_id_env = os.getenv("DRIVE_FOLDER_ID", "")

        creds = _get_credentials()
        service = build("drive", "v3", credentials=creds)

        folder_id = _get_or_create_folder_id(service, folder_id_env)

        file_metadata = {"name": f"{session_id}_{filename}", "parents": [folder_id] if folder_id else []}
        media = MediaIoBaseUpload(io.BytesIO(content), mimetype="application/octet-stream", resumable=False)
        created = service.files().create(
            body=file_metadata, media_body=media, fields="id, webViewLink"
        ).execute()

        # Hacerlo visible a cualquiera con el link (solo lectura) para poder abrirlo fácil.
        service.permissions().create(
            fileId=created["id"], body={"role": "reader", "type": "anyone"}
        ).execute()

        return created.get("webViewLink")
    except Exception as e:  # noqa: BLE001
        print(f"[storage_drive] Fallback sin Drive. Motivo: {e}")
        return None
