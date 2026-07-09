"""
Job Finder MVP — backend manual.

No hay agentes automáticos de IA corriendo en el servidor. El flujo es:

  1. Usuario sube su CV -> se guarda en Supabase (+ Google Drive si está
     configurado) -> se notifica al admin (conversandoapp@gmail.com) ->
     usuario ve "estamos procesando, puede tardar hasta 24h".
  2. Admin (vos) entra a /admin, ve la solicitud, optimiza el CV a
     mano (podés usar Claude para redactarlo) y sube el .docx resultante
     + un puntaje ATS simple desde el panel.
  3. Usuario vuelve a entrar a /resultado.html?session=... y si ya está
     listo, ve el resultado y puede pedir "buscar vacantes".
  4. Ese click también notifica al admin. El admin arma un JSON de
     vacantes (con ayuda de Claude, ver backend/schemas/prompt_para_claude_vacantes.md)
     y lo sube desde el panel.
  5. Usuario vuelve a /vacantes.html?session=... y ve la plataforma de
     vacantes ya armada a partir de ese JSON.

No hay push notifications hacia el usuario: el usuario debe volver a
consultar la página periódicamente (tal como se definió para este MVP).
"""
import json
import os
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles

from services import auth, db, drive_oauth, notifications, role_matcher, sessions, storage_drive

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
FRONTEND_DIR = BASE_DIR.parent / "frontend"

app = FastAPI(title="Job Finder MVP (manual)")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

ALLOWED_CV_EXTENSIONS = {".pdf", ".docx", ".doc", ".txt"}


# ---------------------------------------------------------------------------
# Config / sesión de auth
# ---------------------------------------------------------------------------

@app.get("/api/config")
async def config():
    """Datos públicos (no secretos) que el frontend necesita para iniciar el
    cliente de Supabase. La anon key está diseñada para exponerse en el
    frontend — la seguridad real la da el JWT Secret que solo tiene el backend."""
    return {
        "supabase_url": os.getenv("SUPABASE_URL", ""),
        "supabase_anon_key": os.getenv("SUPABASE_ANON_KEY", ""),
    }


@app.get("/api/whoami")
async def whoami(user: dict = Depends(auth.get_current_user)):
    return {"id": user["id"], "email": user["email"], "is_admin": auth.is_admin(user)}


# ---------------------------------------------------------------------------
# Endpoints de usuario (requieren estar logueado)
# ---------------------------------------------------------------------------

@app.post("/api/analyze")
async def analyze(
    file: UploadFile = File(...),
    linkedin_url: str = Form(None),
    pais: str = Form("Peru"),
    user: dict = Depends(auth.get_current_user),
):
    ext = Path(file.filename or "").suffix.lower()
    if ext not in ALLOWED_CV_EXTENSIONS:
        raise HTTPException(400, f"Formato no soportado ({ext}). Usa PDF, DOCX o TXT.")

    candidate_name = Path(file.filename or "cv").stem
    session_id = sessions.create_session(
        candidate_name, linkedin_url, pais, user_id=user["id"], user_email=user["email"]
    )

    content = await file.read()
    original_path = f"{session_id}/cv_original{ext}"
    db.upload_file(original_path, content, file.content_type or "application/octet-stream")
    sessions.update_session(session_id, cv_original_path=original_path)

    drive_link = storage_drive.upload_cv_to_drive(content, session_id, file.filename or "cv")
    if drive_link:
        sessions.update_session(session_id, cv_drive_link=drive_link)

    try:
        notifications.notify_cv_uploaded(session_id, candidate_name, pais, linkedin_url, drive_link)
    except Exception as e:  # noqa: BLE001
        print(f"[analyze] ERROR notificando CV subido: {e}")

    try:
        roles_sugeridos = role_matcher.suggest_roles_from_cv(content, ext)
        sessions.update_session(session_id, roles_sugeridos=roles_sugeridos)
    except Exception as e:  # noqa: BLE001
        print(f"[analyze] ERROR sugiriendo roles desde CV: {e}")

    return {"session_id": session_id, "status": "processing"}


@app.get("/api/my-sessions")
async def my_sessions(user: dict = Depends(auth.get_current_user)):
    return sessions.list_sessions_for_user(user["id"])


@app.get("/api/status/{session_id}")
async def status(session_id: str, user: dict = Depends(auth.get_current_user)):
    data = sessions.load_session(session_id)
    if data is None:
        raise HTTPException(404, "Sesión no encontrada")
    auth.ensure_owner_or_admin(data, user)
    return data


@app.get("/api/result/{session_id}")
async def result(session_id: str, user: dict = Depends(auth.get_current_user)):
    data = sessions.load_session(session_id)
    if data is None:
        raise HTTPException(404, "Sesión no encontrada")
    auth.ensure_owner_or_admin(data, user)
    if data["cv_status"] != "ready":
        return JSONResponse({"cv_status": data["cv_status"]}, status_code=202)

    scores = data.get("cv_scores") or {}

    return {"cv_status": "ready", "session": data, "scores": scores}


@app.get("/api/download/cv/{session_id}")
async def download_cv(session_id: str, user: dict = Depends(auth.get_current_user)):
    data = sessions.load_session(session_id)
    if data is None:
        raise HTTPException(404, "Sesión no encontrada")
    auth.ensure_owner_or_admin(data, user)

    path = data.get("cv_optimizado_path")
    if not path:
        raise HTTPException(404, "El CV optimizado todavía no está listo")

    content = db.download_file(path)
    return Response(
        content,
        media_type="application/octet-stream",
        headers={"content-disposition": f'attachment; filename="{Path(path).name}"'},
    )


@app.post("/api/jobs")
async def request_jobs(payload: dict, user: dict = Depends(auth.get_current_user)):
    session_id = payload.get("session_id")
    if not session_id:
        raise HTTPException(400, "Falta session_id")

    data = sessions.load_session(session_id)
    if data is None:
        raise HTTPException(404, "Sesión no encontrada")
    auth.ensure_owner_or_admin(data, user)
    if data["cv_status"] != "ready":
        raise HTTPException(400, "El CV todavía no está listo")

    sessions.update_session(
        session_id,
        jobs_status="pending",
        jobs_requested_at=datetime.now(timezone.utc).isoformat(),
    )
    notifications.notify_jobs_requested(session_id, data.get("candidate_name"), data.get("pais"))
    return {"status": "processing"}


@app.get("/api/vacantes/{session_id}")
async def vacantes(session_id: str, user: dict = Depends(auth.get_current_user)):
    data = sessions.load_session(session_id)
    if data is None:
        raise HTTPException(404, "Sesión no encontrada")
    auth.ensure_owner_or_admin(data, user)
    if data["jobs_status"] != "ready":
        return JSONResponse({"jobs_status": data["jobs_status"]}, status_code=202)

    vacantes = data.get("vacantes")
    if not vacantes:
        return JSONResponse({"jobs_status": "pending"}, status_code=202)

    return vacantes


# ---------------------------------------------------------------------------
# Endpoints de admin (panel local /admin) — requieren la cuenta admin
# ---------------------------------------------------------------------------

@app.get("/api/admin/requests")
async def admin_requests(user: dict = Depends(auth.require_admin)):
    return sessions.list_sessions()


@app.get("/api/admin/notifications")
async def admin_notifications(user: dict = Depends(auth.require_admin)):
    return notifications.read_notifications()


@app.get("/api/admin/download/original/{session_id}")
async def admin_download_original(session_id: str, user: dict = Depends(auth.require_admin)):
    data = sessions.load_session(session_id)
    if data is None:
        raise HTTPException(404, "Sesión no encontrada")

    path = data.get("cv_original_path")
    if not path:
        raise HTTPException(404, "No se encontró el CV original")

    content = db.download_file(path)
    return Response(
        content,
        media_type="application/octet-stream",
        headers={"content-disposition": f'attachment; filename="{Path(path).name}"'},
    )


@app.get("/api/admin/drive/authorize")
async def admin_drive_authorize(user: dict = Depends(auth.require_admin)):
    """Arma la URL de consentimiento de Google para conectar Drive (ver
    backend/services/drive_oauth.py). El frontend redirige el navegador ahí."""
    redirect_uri = os.getenv("DRIVE_OAUTH_REDIRECT_URI", "")
    if not redirect_uri:
        raise HTTPException(500, "Falta DRIVE_OAUTH_REDIRECT_URI en el servidor")
    try:
        authorize_url = drive_oauth.build_authorize_url(redirect_uri)
    except Exception as e:
        raise HTTPException(500, f"No se pudo armar la URL de autorización de Drive: {e}")
    return {"authorize_url": authorize_url}


@app.get("/api/admin/drive/oauth2callback")
async def admin_drive_oauth2callback(request: Request):
    """Google redirige acá después del consentimiento. No puede protegerse
    con el login de admin (es una navegación directa desde Google, sin
    header Authorization) -- se valida el `state` en su lugar, ver
    drive_oauth.exchange_code."""
    code = request.query_params.get("code")
    state = request.query_params.get("state")
    error = request.query_params.get("error")

    if error:
        return HTMLResponse(f"<p>Google devolvió un error: {error}. Vuelve a /admin e intenta de nuevo.</p>", status_code=400)
    if not code or not state:
        return HTMLResponse("<p>Faltan parámetros en la redirección de Google.</p>", status_code=400)

    redirect_uri = os.getenv("DRIVE_OAUTH_REDIRECT_URI", "")
    try:
        creds = drive_oauth.exchange_code(redirect_uri, code, state)
        drive_oauth.save_credentials(creds)
    except Exception as e:
        return HTMLResponse(f"<p>No se pudo conectar Google Drive: {e}. Vuelve a /admin e intenta de nuevo.</p>", status_code=400)

    return HTMLResponse("<p>Google Drive conectado correctamente. Ya puedes cerrar esta pestaña.</p>")


@app.post("/api/admin/{session_id}/cv")
async def admin_upload_cv(
    session_id: str,
    file: UploadFile = File(...),
    scores_file: UploadFile = File(...),
    user: dict = Depends(auth.require_admin),
):
    """Sube el CV optimizado (.docx/.pdf) + un único cv_analysis.json generado
    con Claude (ver backend/schemas/prompt_para_claude_cv_analysis.md)."""
    data = sessions.load_session(session_id)
    if data is None:
        raise HTTPException(404, "Sesión no encontrada")

    ext = Path(file.filename or "cv.docx").suffix or ".docx"
    content = await file.read()

    raw = await scores_file.read()
    try:
        scores = json.loads(raw.decode("utf-8"))
    except json.JSONDecodeError as e:
        raise HTTPException(400, f"cv_analysis.json no es JSON válido: {e}")

    required_keys = {"ats_score_original", "ats_score_optimizado", "roles_objetivo",
                      "keywords_agregados", "debilidades"}
    missing = required_keys - scores.keys()
    if missing:
        raise HTTPException(400, f"Al JSON le faltan estas claves: {', '.join(sorted(missing))}")

    optimizado_path = f"{session_id}/cv_optimizado{ext}"
    db.upload_file(optimizado_path, content, file.content_type or "application/octet-stream")

    sessions.update_session(
        session_id,
        cv_optimizado_path=optimizado_path,
        cv_scores=scores,
        cv_status="ready",
        cv_ready_at=datetime.now(timezone.utc).isoformat(),
    )
    return {"status": "ok"}


@app.post("/api/admin/{session_id}/vacantes")
async def admin_upload_vacantes(
    session_id: str, file: UploadFile = File(...), user: dict = Depends(auth.require_admin)
):
    data = sessions.load_session(session_id)
    if data is None:
        raise HTTPException(404, "Sesión no encontrada")

    raw = await file.read()
    try:
        parsed = json.loads(raw.decode("utf-8"))
    except json.JSONDecodeError as e:
        raise HTTPException(400, f"El archivo no es JSON válido: {e}")

    if "vacantes" not in parsed:
        raise HTTPException(400, "El JSON debe tener una clave 'vacantes' con la lista de ofertas.")

    sessions.update_session(
        session_id,
        vacantes=parsed,
        jobs_status="ready",
        jobs_ready_at=datetime.now(timezone.utc).isoformat(),
    )
    return {"status": "ok"}


@app.delete("/api/admin/{session_id}/cv")
async def admin_delete_cv(session_id: str, user: dict = Depends(auth.require_admin)):
    """Borra el análisis de CV subido por el admin (deja la sesión como si
    todavía no se hubiera procesado). También borra el .docx/.pdf optimizado
    del storage si existe."""
    data = sessions.load_session(session_id)
    if data is None:
        raise HTTPException(404, "Sesión no encontrada")

    if data.get("cv_optimizado_path"):
        try:
            db.delete_file(data["cv_optimizado_path"])
        except Exception:
            pass  # no bloquear el borrado del registro si falla el storage

    sessions.update_session(
        session_id,
        cv_optimizado_path=None,
        cv_scores=None,
        cv_status="pending",
        cv_ready_at=None,
    )
    return {"status": "ok"}


@app.delete("/api/admin/{session_id}/vacantes")
async def admin_delete_vacantes(session_id: str, user: dict = Depends(auth.require_admin)):
    """Borra las vacantes subidas por el admin (vuelve a 'not_requested')."""
    data = sessions.load_session(session_id)
    if data is None:
        raise HTTPException(404, "Sesión no encontrada")

    sessions.update_session(
        session_id,
        vacantes=None,
        jobs_status="not_requested",
        jobs_ready_at=None,
    )
    return {"status": "ok"}


# ---------------------------------------------------------------------------
# Frontend estático
# ---------------------------------------------------------------------------

@app.get("/admin")
async def admin_panel_short():
    return FileResponse(FRONTEND_DIR / "admin.html")


@app.get("/admin-login")
async def admin_login_short():
    return FileResponse(FRONTEND_DIR / "admin-login.html")


app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")
