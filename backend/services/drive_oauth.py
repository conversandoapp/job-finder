"""
Helpers para el flujo de autorización OAuth 2.0 de Google Drive (delegación
de usuario, ver storage_drive.py para el porqué).

No hay ejecución local en este proyecto (se despliega directo en Render),
así que la autorización de una sola vez se hace enteramente contra el
servicio ya desplegado: el admin entra a /admin.html, hace click en
"Conectar Google Drive", y dos endpoints en app.py (/api/admin/drive/authorize
y /api/admin/drive/oauth2callback) manejan el ida y vuelta con Google.

El `state` de OAuth (para validar el callback) y el token final se guardan
en la tabla `app_settings` de Supabase en vez de en memoria/disco local --
así funciona sin importar cuántas instancias corran ni si el proceso se
reinicia entre el /authorize y el /oauth2callback.
"""
import json
import os

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow

from services import db

SCOPES = ["https://www.googleapis.com/auth/drive.file"]
_PENDING_STATE_KEY = "drive_oauth_pending_state"


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
    flow = build_flow(redirect_uri)
    authorize_url, state = flow.authorization_url(
        access_type="offline", prompt="consent", include_granted_scopes="true"
    )
    db.set_setting(_PENDING_STATE_KEY, {"state": state})
    return authorize_url


def exchange_code(redirect_uri: str, code: str, state: str) -> Credentials:
    """Valida el state contra el guardado en build_authorize_url y canjea el
    code por credenciales. Lanza ValueError si el state no coincide."""
    pending = db.get_setting(_PENDING_STATE_KEY)
    if not pending or state != pending.get("state"):
        raise ValueError("state inválido o expirado -- volvé a iniciar la conexión con Drive desde /admin.html")
    db.delete_setting(_PENDING_STATE_KEY)

    flow = build_flow(redirect_uri)
    flow.fetch_token(code=code)
    return flow.credentials


def save_credentials(creds: Credentials) -> None:
    db.set_setting("drive_token", json.loads(creds.to_json()))
