"""
Cliente de Supabase para el backend (Postgres + Storage).

Usa la service_role key -- privilegios completos, nunca se expone al
frontend (que solo usa la anon key, y solo para auth). La autorización
real la sigue haciendo auth.py en Python (ensure_owner_or_admin,
require_admin), no RLS: estas tablas nunca se consultan directo desde el
frontend, por eso RLS queda deshabilitado (ver backend/supabase/schema.sql).
"""
import os
from functools import lru_cache

from supabase import Client, create_client

CV_BUCKET = "cv-files"


@lru_cache
def get_client() -> Client:
    url = os.getenv("SUPABASE_URL", "")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
    if not url or not key:
        raise RuntimeError("Faltan SUPABASE_URL o SUPABASE_SERVICE_ROLE_KEY en el servidor.")
    return create_client(url, key)


# --- app_settings: almacén clave/valor (token de Drive, state de OAuth) ---

def get_setting(key: str) -> dict | None:
    res = get_client().table("app_settings").select("value").eq("key", key).execute()
    return res.data[0]["value"] if res.data else None


def set_setting(key: str, value: dict) -> None:
    get_client().table("app_settings").upsert({"key": key, "value": value}).execute()


def delete_setting(key: str) -> None:
    get_client().table("app_settings").delete().eq("key", key).execute()


# --- Storage: archivos de CV -----------------------------------------------

def upload_file(path: str, content: bytes, content_type: str) -> None:
    get_client().storage.from_(CV_BUCKET).upload(
        path, content, {"content-type": content_type, "upsert": "true"}
    )


def download_file(path: str) -> bytes:
    return get_client().storage.from_(CV_BUCKET).download(path)


def delete_file(path: str) -> None:
    get_client().storage.from_(CV_BUCKET).remove([path])
