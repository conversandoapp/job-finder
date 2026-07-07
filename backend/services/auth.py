"""
Autenticación con Supabase.

No usamos el SDK de Supabase en el backend — alcanza con verificar la firma
del JWT que Supabase ya emitió cuando el usuario inició sesión en el
frontend.

Desde octubre de 2025, los proyectos NUEVOS de Supabase firman los JWT con
un esquema asimétrico (ES256 por default) en vez del secreto compartido
HS256 de antes. Por eso este módulo soporta los dos casos:

1. Asimétrico (ES256/RS256) — el caso normal para proyectos actuales: se
   verifica contra las claves públicas que Supabase publica en
   `{SUPABASE_URL}/auth/v1/.well-known/jwks.json`. No hace falta ningún
   secreto en el backend para esto, solo SUPABASE_URL.
2. Legacy (HS256) — proyectos viejos que todavía usan el JWT Secret
   compartido de Project Settings → API. Si configurás SUPABASE_JWT_SECRET,
   se usa como fallback para tokens firmados con HS256.

El admin es UNA sola cuenta: cualquier usuario autenticado cuyo email
coincida con ADMIN_EMAIL (variable de entorno) puede usar los endpoints
`/api/admin/*`. Todos los demás usuarios autenticados son "usuarios normales"
y solo pueden ver/tocar sus propias sesiones (comparando user_id).
"""
import os

import jwt
from fastapi import HTTPException, Request
from jwt import PyJWKClient

_jwks_client: PyJWKClient | None = None
_jwks_client_url: str | None = None


def _admin_email() -> str:
    return os.getenv("ADMIN_EMAIL", "").strip().lower()


def is_admin(user: dict) -> bool:
    admin_email = _admin_email()
    if not admin_email:
        return False
    return (user.get("email") or "").strip().lower() == admin_email


def _get_jwks_client() -> PyJWKClient | None:
    global _jwks_client, _jwks_client_url
    supabase_url = os.getenv("SUPABASE_URL", "").strip().rstrip("/")
    if not supabase_url:
        return None
    jwks_url = f"{supabase_url}/auth/v1/.well-known/jwks.json"
    if _jwks_client is None or _jwks_client_url != jwks_url:
        _jwks_client = PyJWKClient(jwks_url, cache_keys=True, lifespan=600)
        _jwks_client_url = jwks_url
    return _jwks_client


def _decode_token(token: str) -> dict:
    try:
        header = jwt.get_unverified_header(token)
    except jwt.InvalidTokenError as e:
        raise HTTPException(401, f"Token inválido: {e}")

    alg = header.get("alg", "HS256")

    if alg == "HS256":
        secret = os.getenv("SUPABASE_JWT_SECRET")
        if not secret:
            raise HTTPException(
                500,
                "Este token está firmado con HS256 (legacy) pero el servidor no tiene "
                "configurado SUPABASE_JWT_SECRET. Revisá backend/.env.",
            )
        return jwt.decode(token, secret, algorithms=["HS256"], audience="authenticated")

    # Asimétrico (ES256/RS256, el default actual de Supabase) — se verifica
    # contra las claves públicas publicadas en el JWKS del proyecto.
    client = _get_jwks_client()
    if client is None:
        raise HTTPException(
            500,
            "Falta SUPABASE_URL en el servidor: es necesario para verificar tokens "
            "firmados de forma asimétrica (JWKS). Revisá backend/.env.",
        )
    try:
        signing_key = client.get_signing_key_from_jwt(token)
    except jwt.PyJWKClientError as e:
        raise HTTPException(401, f"No se pudo validar la clave de firma del token: {e}")

    return jwt.decode(token, signing_key.key, algorithms=[alg], audience="authenticated")


def get_current_user(request: Request) -> dict:
    """Dependency de FastAPI: valida el header 'Authorization: Bearer <token>'
    contra las claves de Supabase (JWKS asimétrico, o HS256 legacy si está
    configurado) y devuelve {id, email} del usuario."""
    auth_header = request.headers.get("authorization")
    if not auth_header or not auth_header.lower().startswith("bearer "):
        raise HTTPException(401, "Falta iniciar sesión (no se encontró token de autenticación)")

    token = auth_header.split(" ", 1)[1].strip()

    try:
        payload = _decode_token(token)
    except jwt.ExpiredSignatureError:
        raise HTTPException(401, "Tu sesión expiró, vuelve a iniciar sesión")
    except jwt.InvalidTokenError as e:
        raise HTTPException(401, f"Token inválido: {e}")

    user_id = payload.get("sub")
    email = payload.get("email")
    if not user_id:
        raise HTTPException(401, "Token sin usuario válido")

    return {"id": user_id, "email": email}


def require_admin(request: Request) -> dict:
    """Dependency de FastAPI: exige que el usuario autenticado sea el admin."""
    user = get_current_user(request)
    if not is_admin(user):
        raise HTTPException(403, "No tienes permisos de administrador para esta acción")
    return user


def ensure_owner_or_admin(session_data: dict, user: dict) -> None:
    """Lanza 403 si el usuario no es dueño de la sesión ni es el admin."""
    if session_data.get("user_id") == user.get("id"):
        return
    if is_admin(user):
        return
    raise HTTPException(403, "No tienes acceso a esta sesión")
