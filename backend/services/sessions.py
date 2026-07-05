"""
Manejo de sesiones respaldado por la tabla `sessions` de Supabase Postgres
(antes: una carpeta + request.json por sesión en el filesystem local --
se migró porque el filesystem del contenedor en Render es efímero).
"""
import uuid
from datetime import datetime, timezone

from services import db

TABLE = "sessions"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def create_session(
    candidate_name: str | None,
    linkedin_url: str | None,
    pais: str,
    user_id: str | None = None,
    user_email: str | None = None,
) -> str:
    session_id = str(uuid.uuid4())
    row = {
        "session_id": session_id,
        "candidate_name": candidate_name,
        "linkedin_url": linkedin_url,
        "pais": pais or "Peru",
        "user_id": user_id,
        "user_email": user_email,
        "cv_status": "pending",  # pending | ready | error
        "jobs_status": "not_requested",  # not_requested | pending | ready | error
        "cv_requested_at": _now_iso(),
    }
    db.get_client().table(TABLE).insert(row).execute()
    return session_id


def list_sessions_for_user(user_id: str) -> list[dict]:
    res = (
        db.get_client()
        .table(TABLE)
        .select("*")
        .eq("user_id", user_id)
        .order("created_at", desc=True)
        .execute()
    )
    return res.data


def save_session(session_id: str, data: dict) -> None:
    db.get_client().table(TABLE).update(data).eq("session_id", session_id).execute()


def load_session(session_id: str) -> dict | None:
    res = db.get_client().table(TABLE).select("*").eq("session_id", session_id).execute()
    return res.data[0] if res.data else None


def update_session(session_id: str, **kwargs) -> dict:
    res = db.get_client().table(TABLE).update(kwargs).eq("session_id", session_id).execute()
    if not res.data:
        raise FileNotFoundError(f"session {session_id} not found")
    return res.data[0]


def list_sessions() -> list[dict]:
    res = db.get_client().table(TABLE).select("*").order("created_at", desc=True).execute()
    return res.data
