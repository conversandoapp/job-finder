"""
Sube el CV original a Google Drive para que el admin lo tenga disponible.

Modo real: usa una cuenta de servicio (service account) de Google Cloud.
  Setup (una sola vez):
  1. Ir a https://console.cloud.google.com/ → crear proyecto (o usar uno existente)
  2. Habilitar "Google Drive API"
  3. Crear credenciales → "Service Account" → crear una clave JSON
  4. Guardar ese archivo como backend/credentials/service_account.json
  5. En Google Drive, crear una carpeta (ej. "Job Finder - CVs recibidos"),
     compartirla con el email de la cuenta de servicio (algo como
     xxx@xxx.iam.gserviceaccount.com) dándole permiso de Editor
  6. Copiar el ID de esa carpeta (está en la URL de Drive) y ponerlo en
     backend/.env como DRIVE_FOLDER_ID
  7. Poner DRIVE_ENABLED=true en backend/.env

Modo simulado (default): el CV se guarda únicamente en
backend/storage/sessions/{session_id}/cv_original.* — que ya es una
carpeta local persistente. La app funciona igual, pero sin subir nada
a Drive hasta que actives el modo real.
"""
import os
from pathlib import Path


def upload_cv_to_drive(local_path: Path, session_id: str, filename: str) -> str | None:
    """Devuelve el link de Drive si se subió, o None si está en modo simulado
    o si falla la subida (nunca debe romper el flujo principal)."""
    enabled = os.getenv("DRIVE_ENABLED", "false").lower() == "true"
    if not enabled:
        return None

    try:
        from google.oauth2 import service_account
        from googleapiclient.discovery import build
        from googleapiclient.http import MediaFileUpload

        creds_path = os.getenv("DRIVE_CREDENTIALS_PATH", "backend/credentials/service_account.json")
        folder_id = os.getenv("DRIVE_FOLDER_ID", "")

        creds = service_account.Credentials.from_service_account_file(
            creds_path, scopes=["https://www.googleapis.com/auth/drive.file"]
        )
        service = build("drive", "v3", credentials=creds)

        file_metadata = {"name": f"{session_id}_{filename}", "parents": [folder_id] if folder_id else []}
        media = MediaFileUpload(str(local_path), resumable=False)
        created = service.files().create(
            body=file_metadata, media_body=media, fields="id, webViewLink"
        ).execute()

        # Hacerlo visible a cualquiera con el link (solo lectura) para poder abrirlo fácil.
        service.permissions().create(
            fileId=created["id"], body={"role": "reader", "type": "anyone"}
        ).execute()

        return created.get("webViewLink")
    except Exception as e:  # noqa: BLE001
        print(f"[storage_drive] Fallback a almacenamiento local. Motivo: {e}")
        return None
