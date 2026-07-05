"""
Helpers para el flujo de autorización OAuth 2.0 de Google Drive (delegación
de usuario, ver storage_drive.py para el porqué).

No hay ejecución local en este proyecto (se despliega directo en Cloud Run),
así que la autorización de una sola vez se hace enteramente contra el
servicio ya desplegado: el admin entra a /admin.html, hace click en
"Conectar Google Drive", y dos endpoints en app.py (/api/admin/drive/authorize
y /api/admin/drive/oauth2callback) manejan el ida y vuelta con Google.

El `state` de OAuth se guarda en memoria del proceso entre esos dos
endpoints -- funciona porque el resto de la app ya requiere correr con una
sola instancia (--max-instances=1, ver DEPLOY.md, por el manejo de sesiones
en archivos).
"""
import os
from pathlib import Path

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow

SCOPES = ["https://www.googleapis.com/auth/drive.file"]

_pending_state: str | None = None


def _client_config(redirect_uri: str) -> dict:
    client_id = os.getenv("DRIVE_OAUTH_CLIENT_ID", "")
    client_secret = os.getenv("DRIVE_OAUTH_CLIENT_SECRET", "")
    return {
        "web": {
            "client_id": client_id,
            "client_secret": client_secret,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": [redirect_uri],
        }
    }


def build_flow(redirect_uri: str) -> Flow:
    return Flow.from_client_config(_client_config(redirect_uri), scopes=SCOPES, redirect_uri=redirect_uri)


def build_authorize_url(redirect_uri: str) -> str:
    """Arma la URL de consentimiento de Google y guarda el state pendiente
    para validarlo cuando Google redirija de vuelta al callback."""
    global _pending_state
    flow = build_flow(redirect_uri)
    authorize_url, state = flow.authorization_url(
        access_type="offline", prompt="consent", include_granted_scopes="true"
    )
    _pending_state = state
    return authorize_url


def exchange_code(redirect_uri: str, code: str, state: str) -> Credentials:
    """Valida el state contra el guardado en build_authorize_url y canjea el
    code por credenciales. Lanza ValueError si el state no coincide."""
    global _pending_state
    if not _pending_state or state != _pending_state:
        raise ValueError("state inválido o expirado -- volvé a iniciar la conexión con Drive desde /admin.html")
    _pending_state = None

    flow = build_flow(redirect_uri)
    flow.fetch_token(code=code)
    return flow.credentials


def save_credentials(creds: Credentials) -> None:
    token_path = os.getenv("DRIVE_TOKEN_PATH", "backend/storage/drive_token.json")
    Path(token_path).parent.mkdir(parents=True, exist_ok=True)
    Path(token_path).write_text(creds.to_json(), encoding="utf-8")
