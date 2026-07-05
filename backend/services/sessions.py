"""
Manejo de sesiones para el MVP.
Cada sesión vive como una carpeta en storage/sessions/{session_id}/
con un archivo request.json que guarda el estado.

No usamos base de datos: para un MVP manual, el filesystem es más que suficiente
y además permite que el admin inspeccione/edite archivos a mano si hace falta.
"""
import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
STORAGE_DIR = BASE_DIR / "storage" / "sessions"
STORAGE_DIR.mkdir(parents=True, exist_ok=True)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def session_dir(session_id: str) -> Path:
    d = STORAGE_DIR / session_id
    d.mkdir(parents=True, exist_ok=True)
    return d


def request_path(session_id: str) -> Path:
    return session_dir(session_id) / "request.json"


def create_session(
    candidate_name: str | None,
    linkedin_url: str | None,
    pais: str,
    user_id: str | None = None,
    user_email: str | None = None,
) -> str:
    session_id = str(uuid.uuid4())
    data = {
        "session_id": session_id,
        "created_at": _now_iso(),
        "candidate_name": candidate_name,
        "linkedin_url": linkedin_url,
        "pais": pais or "Peru",
        "user_id": user_id,
        "user_email": user_email,
        "cv_status": "pending",       # pending | ready | error
        "jobs_status": "not_requested",  # not_requested | pending | ready | error
        "cv_requested_at": _now_iso(),
        "cv_ready_at": None,
        "jobs_requested_at": None,
        "jobs_ready_at": None,
        "cv_drive_link": None,
        "notes": None,
    }
    save_session(session_id, data)
    return session_id


def list_sessions_for_user(user_id: str) -> list[dict]:
    return [s for s in list_sessions() if s.get("user_id") == user_id]


def save_session(session_id: str, data: dict) -> None:
    with open(request_path(session_id), "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def load_session(session_id: str) -> dict | None:
    p = request_path(session_id)
    if not p.exists():
        return None
    with open(p, "r", encoding="utf-8") as f:
        return json.load(f)


def update_session(session_id: str, **kwargs) -> dict:
    data = load_session(session_id)
    if data is None:
        raise FileNotFoundError(f"session {session_id} not found")
    data.update(kwargs)
    save_session(session_id, data)
    return data


def list_sessions() -> list[dict]:
    sessions = []
    if not STORAGE_DIR.exists():
        return sessions
    for d in sorted(STORAGE_DIR.iterdir(), key=lambda p: p.name, reverse=True):
        rp = d / "request.json"
        if rp.exists():
            with open(rp, "r", encoding="utf-8") as f:
                sessions.append(json.load(f))
    return sessions
