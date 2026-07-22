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
from typing import Optional

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles

from services import auth, db, drive_oauth, notifications, packaging, role_matcher, roles, sessions, storage_drive

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
    return {
        "id": user["id"],
        "email": user["email"],
        "is_admin": auth.is_admin(user),
        "is_backoffice": auth.is_backoffice(user),
    }


# ---------------------------------------------------------------------------
# Endpoints de usuario (requieren estar logueado)
# ---------------------------------------------------------------------------

@app.post("/api/suggest-roles")
async def suggest_roles(file: UploadFile = File(...), user: dict = Depends(auth.get_current_user)):
    """Filtro rápido (sin guardar nada) para sugerirle al candidato hasta 3
    puestos que hacen match con su CV, antes de que confirme la subida."""
    ext = Path(file.filename or "").suffix.lower()
    if ext not in ALLOWED_CV_EXTENSIONS:
        raise HTTPException(400, f"Formato no soportado ({ext}). Usa PDF, DOCX o TXT.")

    content = await file.read()
    try:
        roles_sugeridos = role_matcher.suggest_roles_from_cv(content, ext, top_n=3)
    except Exception as e:  # noqa: BLE001
        print(f"[suggest-roles] ERROR sugiriendo roles desde CV: {e}")
        roles_sugeridos = []

    return {"roles_sugeridos": roles_sugeridos}


@app.post("/api/analyze")
async def analyze(
    file: UploadFile = File(...),
    linkedin_url: str = Form(None),
    pais: str = Form("Peru"),
    roles_candidato: str = Form("[]"),
    dejar_eleccion: str = Form("false"),
    user: dict = Depends(auth.get_current_user),
):
    ext = Path(file.filename or "").suffix.lower()
    if ext not in ALLOWED_CV_EXTENSIONS:
        raise HTTPException(400, f"Formato no soportado ({ext}). Usa PDF, DOCX o TXT.")

    dejar = dejar_eleccion.strip().lower() in ("true", "1", "yes")
    try:
        roles_parsed = json.loads(roles_candidato) if roles_candidato else []
    except json.JSONDecodeError:
        roles_parsed = []
    roles_elegidos = [] if dejar else [
        r.strip() for r in roles_parsed if isinstance(r, str) and r.strip()
    ][:3]
    roles_modo = "admin" if dejar else "candidato"

    candidate_name = Path(file.filename or "cv").stem
    session_id = sessions.create_session(
        candidate_name, linkedin_url, pais, user_id=user["id"], user_email=user["email"]
    )

    content = await file.read()
    original_path = f"{session_id}/cv_original{ext}"
    db.upload_file(original_path, content, file.content_type or "application/octet-stream")
    sessions.update_session(
        session_id,
        cv_original_path=original_path,
        roles_elegidos=roles_elegidos,
        roles_modo=roles_modo,
    )

    drive_link = storage_drive.upload_cv_to_drive(content, session_id, file.filename or "cv")
    if drive_link:
        sessions.update_session(session_id, cv_drive_link=drive_link)

    zip_bytes = None
    try:
        zip_bytes = packaging.build_postulacion_zip(content, f"cv_original{ext}", roles_modo, roles_elegidos)
        zip_path = f"{session_id}/postulacion.zip"
        db.upload_file(zip_path, zip_bytes, "application/zip")
        sessions.update_session(session_id, cv_zip_path=zip_path)
    except Exception as e:  # noqa: BLE001
        print(f"[analyze] ERROR empaquetando CV + puestos en zip: {e}")

    try:
        attachment = (zip_bytes, f"postulacion_{session_id[:8]}.zip") if zip_bytes else None
        notifications.notify_cv_uploaded(
            session_id, candidate_name, pais, linkedin_url, drive_link,
            roles_modo=roles_modo, roles_elegidos=roles_elegidos, attachment=attachment,
        )
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
    auth.ensure_owner_or_backoffice(data, user)
    return data


@app.get("/api/result/{session_id}")
async def result(session_id: str, user: dict = Depends(auth.get_current_user)):
    data = sessions.load_session(session_id)
    if data is None:
        raise HTTPException(404, "Sesión no encontrada")
    auth.ensure_owner_or_backoffice(data, user)

    is_reviewer_preview = auth.is_backoffice(user) and data["cv_status"] == "pending_review"
    if data["cv_status"] != "ready" and not is_reviewer_preview:
        return JSONResponse({"cv_status": data["cv_status"]}, status_code=202)

    scores = data.get("cv_scores") or {}

    return {"cv_status": data["cv_status"], "session": data, "scores": scores}


@app.get("/api/download/cv/{session_id}")
async def download_cv(session_id: str, user: dict = Depends(auth.get_current_user)):
    data = sessions.load_session(session_id)
    if data is None:
        raise HTTPException(404, "Sesión no encontrada")
    auth.ensure_owner_or_backoffice(data, user)

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
    auth.ensure_owner_or_backoffice(data, user)

    is_reviewer_preview = auth.is_backoffice(user) and data["jobs_status"] == "pending_review"
    if data["jobs_status"] != "ready" and not is_reviewer_preview:
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


@app.get("/api/admin/download/zip/{session_id}")
async def admin_download_zip(session_id: str, user: dict = Depends(auth.require_admin)):
    """CV original + puestos_candidato.json comprimidos (ver services/packaging.py)."""
    data = sessions.load_session(session_id)
    if data is None:
        raise HTTPException(404, "Sesión no encontrada")

    path = data.get("cv_zip_path")
    if not path:
        raise HTTPException(404, "No se encontró el paquete CV + puestos")

    content = db.download_file(path)
    return Response(
        content,
        media_type="application/zip",
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


CV_ANALYSIS_REQUIRED_KEYS = {"ats_score_original", "ats_score_optimizado", "roles_objetivo",
                             "keywords_agregados", "debilidades"}


def _validate_cv_analysis(scores: dict) -> dict:
    if not isinstance(scores, dict):
        raise HTTPException(400, "El análisis debe ser un objeto JSON.")
    missing = CV_ANALYSIS_REQUIRED_KEYS - scores.keys()
    if missing:
        raise HTTPException(400, f"Al análisis le faltan estas claves: {', '.join(sorted(missing))}")
    for key in ("roles_objetivo", "keywords_agregados", "debilidades"):
        if not isinstance(scores.get(key), list):
            raise HTTPException(400, f"'{key}' debe ser una lista.")
    for key in ("ats_score_original", "ats_score_optimizado"):
        if not isinstance(scores.get(key), (int, float)):
            raise HTTPException(400, f"'{key}' debe ser un número.")
    return scores


def _parse_cv_analysis_json(raw: bytes) -> dict:
    try:
        scores = json.loads(raw.decode("utf-8"))
    except json.JSONDecodeError as e:
        raise HTTPException(400, f"cv_analysis.json no es JSON válido: {e}")
    return _validate_cv_analysis(scores)


def _store_cv_bytes(session_id: str, content: bytes, ext: str, content_type: str = "application/octet-stream") -> str:
    path = f"{session_id}/cv_optimizado{ext or '.docx'}"
    db.upload_file(path, content, content_type)
    return path


async def _store_cv_optimizado(session_id: str, file: UploadFile) -> str:
    ext = Path(file.filename or "cv.docx").suffix or ".docx"
    content = await file.read()
    return _store_cv_bytes(session_id, content, ext, file.content_type or "application/octet-stream")


async def _parse_vacantes_json(file: UploadFile) -> dict:
    raw = await file.read()
    try:
        parsed = json.loads(raw.decode("utf-8"))
    except json.JSONDecodeError as e:
        raise HTTPException(400, f"El archivo no es JSON válido: {e}")
    if "vacantes" not in parsed:
        raise HTTPException(400, "El JSON debe tener una clave 'vacantes' con la lista de ofertas.")
    return parsed


@app.post("/api/admin/{session_id}/cv")
async def admin_upload_cv(
    session_id: str,
    file: UploadFile = File(...),
    scores_file: Optional[UploadFile] = File(None),
    user: dict = Depends(auth.require_admin),
):
    """Sube el CV optimizado (.docx/.pdf) + un único cv_analysis.json generado
    con Claude (ver backend/schemas/prompt_para_claude_cv_analysis.md). También
    acepta el cv_optimizado_{nombre}.zip con ambos archivos juntos (generado
    por el skill cv-optimizer-jobfinder) en el campo `file`, sin `scores_file`.
    Queda en pending_review hasta que backoffice lo apruebe, rechace o
    reemplace."""
    data = sessions.load_session(session_id)
    if data is None:
        raise HTTPException(404, "Sesión no encontrada")

    if (file.filename or "").lower().endswith(".zip"):
        content = await file.read()
        try:
            cv_bytes, cv_ext, analysis_bytes = packaging.extract_cv_optimizado_zip(content)
        except ValueError as e:
            raise HTTPException(400, str(e))
        scores = _parse_cv_analysis_json(analysis_bytes)
        optimizado_path = _store_cv_bytes(session_id, cv_bytes, cv_ext)
    else:
        if scores_file is None:
            raise HTTPException(400, "Falta cv_analysis.json (o subí el .zip que contiene ambos archivos).")
        scores = _parse_cv_analysis_json(await scores_file.read())
        optimizado_path = await _store_cv_optimizado(session_id, file)

    sessions.update_session(
        session_id,
        cv_optimizado_path=optimizado_path,
        cv_scores=scores,
        cv_status="pending_review",
        cv_ready_at=None,
        cv_review_note=None,
    )
    try:
        notifications.notify_pending_review(session_id, data.get("candidate_name"), "cv")
    except Exception as e:  # noqa: BLE001
        print(f"[admin] ERROR notificando CV pendiente de revisión: {e}")
    return {"status": "ok"}


@app.post("/api/admin/{session_id}/vacantes")
async def admin_upload_vacantes(
    session_id: str, file: UploadFile = File(...), user: dict = Depends(auth.require_admin)
):
    data = sessions.load_session(session_id)
    if data is None:
        raise HTTPException(404, "Sesión no encontrada")

    parsed = await _parse_vacantes_json(file)

    sessions.update_session(
        session_id,
        vacantes=parsed,
        jobs_status="pending_review",
        jobs_ready_at=None,
        jobs_review_note=None,
    )
    try:
        notifications.notify_pending_review(session_id, data.get("candidate_name"), "vacantes")
    except Exception as e:  # noqa: BLE001
        print(f"[admin] ERROR notificando vacantes pendientes de revisión: {e}")
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
        cv_review_note=None,
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
        jobs_review_note=None,
    )
    return {"status": "ok"}


# ---------------------------------------------------------------------------
# Endpoints de admin: gestión de usuarios, roles y asignación a backoffice.
# Solo se listan usuarios que ya tienen al menos una sesión creada.
# ---------------------------------------------------------------------------

@app.get("/api/admin/users")
async def admin_list_users(user: dict = Depends(auth.require_admin)):
    return roles.list_users_with_sessions()


@app.post("/api/admin/users/{user_id}/role")
async def admin_set_user_role(user_id: str, payload: dict, user: dict = Depends(auth.require_admin)):
    role = (payload.get("role") or "").strip().lower()
    email = (payload.get("email") or "").strip().lower()
    if not email:
        raise HTTPException(400, "Falta email")
    try:
        return roles.set_role(user_id=user_id, email=email, role=role, actor_user_id=user["id"])
    except roles.PendingProcessError as e:
        raise HTTPException(409, str(e))
    except ValueError as e:
        raise HTTPException(400, str(e))


@app.get("/api/admin/backoffice-users")
async def admin_backoffice_users(user: dict = Depends(auth.require_admin)):
    return roles.list_backoffice_options()


@app.get("/api/admin/unassigned-users")
async def admin_unassigned_users(user: dict = Depends(auth.require_admin)):
    return roles.list_unassigned_users()


@app.post("/api/admin/assignments")
async def admin_create_assignment(payload: dict, user: dict = Depends(auth.require_admin)):
    try:
        return roles.assign_user_to_backoffice(
            user_id=payload.get("user_id"),
            backoffice_user_id=payload.get("backoffice_user_id"),
        )
    except roles.PendingProcessError as e:
        raise HTTPException(409, str(e))
    except ValueError as e:
        raise HTTPException(400, str(e))


@app.delete("/api/admin/assignments/{user_id}")
async def admin_delete_assignment(user_id: str, user: dict = Depends(auth.require_admin)):
    try:
        roles.unassign_user(user_id)
    except roles.PendingProcessError as e:
        raise HTTPException(409, str(e))
    return {"status": "ok"}


# ---------------------------------------------------------------------------
# Endpoints de backoffice (revisa lo que sube el admin antes de que llegue al
# candidato) — requieren permisos de backoffice (o admin, que los incluye).
# Un backoffice normal solo ve las solicitudes de los usuarios que el admin
# le asignó; el admin (que hereda permisos de backoffice) sigue viendo todo.
# ---------------------------------------------------------------------------

@app.get("/api/backoffice/requests")
async def backoffice_requests(user: dict = Depends(auth.require_backoffice)):
    if auth.is_admin(user):
        return sessions.list_sessions()
    assigned_user_ids = list(roles.list_assigned_user_ids(user["id"]))
    return sessions.list_sessions_for_users(assigned_user_ids)


@app.post("/api/backoffice/{session_id}/cv/approve")
async def backoffice_approve_cv(session_id: str, user: dict = Depends(auth.require_backoffice)):
    data = sessions.load_session(session_id)
    if data is None:
        raise HTTPException(404, "Sesión no encontrada")
    if data.get("cv_status") != "pending_review":
        raise HTTPException(400, "El CV de esta sesión no está esperando revisión.")

    sessions.update_session(
        session_id,
        cv_status="ready",
        cv_ready_at=datetime.now(timezone.utc).isoformat(),
        cv_review_note=None,
    )
    return {"status": "ok"}


@app.post("/api/backoffice/{session_id}/cv/reject")
async def backoffice_reject_cv(
    session_id: str, note: str = Form(""), user: dict = Depends(auth.require_backoffice)
):
    data = sessions.load_session(session_id)
    if data is None:
        raise HTTPException(404, "Sesión no encontrada")
    if data.get("cv_status") != "pending_review":
        raise HTTPException(400, "El CV de esta sesión no está esperando revisión.")

    if data.get("cv_optimizado_path"):
        try:
            db.delete_file(data["cv_optimizado_path"])
        except Exception:
            pass  # no bloquear el rechazo si falla el storage

    sessions.update_session(
        session_id,
        cv_optimizado_path=None,
        cv_scores=None,
        cv_status="pending",
        cv_ready_at=None,
        cv_review_note=note.strip() or None,
    )
    try:
        notifications.notify_cv_rejected(session_id, data.get("candidate_name"), note.strip())
    except Exception as e:  # noqa: BLE001
        print(f"[backoffice] ERROR notificando rechazo de CV: {e}")
    return {"status": "ok"}


@app.post("/api/backoffice/{session_id}/cv/replace")
async def backoffice_replace_cv(
    session_id: str,
    file: UploadFile = File(...),
    scores_file: Optional[UploadFile] = File(None),
    user: dict = Depends(auth.require_backoffice),
):
    data = sessions.load_session(session_id)
    if data is None:
        raise HTTPException(404, "Sesión no encontrada")
    if data.get("cv_status") != "pending_review":
        raise HTTPException(400, "El CV de esta sesión no está esperando revisión.")

    if (file.filename or "").lower().endswith(".zip"):
        content = await file.read()
        try:
            cv_bytes, cv_ext, analysis_bytes = packaging.extract_cv_optimizado_zip(content)
        except ValueError as e:
            raise HTTPException(400, str(e))
        scores = _parse_cv_analysis_json(analysis_bytes)
        optimizado_path = _store_cv_bytes(session_id, cv_bytes, cv_ext)
    else:
        # scores_file es opcional acá: si el backoffice solo quiere corregir
        # el Word, se mantiene el análisis que ya estaba guardado.
        scores = _parse_cv_analysis_json(await scores_file.read()) if scores_file is not None else data.get("cv_scores")
        optimizado_path = await _store_cv_optimizado(session_id, file)

    sessions.update_session(
        session_id,
        cv_optimizado_path=optimizado_path,
        cv_scores=scores,
        cv_status="ready",
        cv_ready_at=datetime.now(timezone.utc).isoformat(),
        cv_review_note=None,
    )
    return {"status": "ok"}


@app.post("/api/backoffice/{session_id}/cv/analysis")
async def backoffice_update_cv_analysis(
    session_id: str, payload: dict, user: dict = Depends(auth.require_backoffice)
):
    """Guarda ediciones del análisis (keywords, roles objetivo, debilidades,
    puntajes ATS) hechas a mano desde el formulario visual del backoffice.
    No aprueba ni cambia el estado -- la solicitud sigue en pending_review
    hasta que el backoffice presione "Aprobar" por separado."""
    data = sessions.load_session(session_id)
    if data is None:
        raise HTTPException(404, "Sesión no encontrada")
    if data.get("cv_status") != "pending_review":
        raise HTTPException(400, "El CV de esta sesión no está esperando revisión.")

    scores = _validate_cv_analysis(payload)
    sessions.update_session(session_id, cv_scores=scores)
    return {"status": "ok"}


@app.post("/api/backoffice/{session_id}/vacantes/approve")
async def backoffice_approve_vacantes(session_id: str, user: dict = Depends(auth.require_backoffice)):
    data = sessions.load_session(session_id)
    if data is None:
        raise HTTPException(404, "Sesión no encontrada")
    if data.get("jobs_status") != "pending_review":
        raise HTTPException(400, "Las vacantes de esta sesión no están esperando revisión.")

    sessions.update_session(
        session_id,
        jobs_status="ready",
        jobs_ready_at=datetime.now(timezone.utc).isoformat(),
        jobs_review_note=None,
    )
    return {"status": "ok"}


@app.post("/api/backoffice/{session_id}/vacantes/reject")
async def backoffice_reject_vacantes(
    session_id: str, note: str = Form(""), user: dict = Depends(auth.require_backoffice)
):
    data = sessions.load_session(session_id)
    if data is None:
        raise HTTPException(404, "Sesión no encontrada")
    if data.get("jobs_status") != "pending_review":
        raise HTTPException(400, "Las vacantes de esta sesión no están esperando revisión.")

    sessions.update_session(
        session_id,
        vacantes=None,
        jobs_status="pending",
        jobs_ready_at=None,
        jobs_review_note=note.strip() or None,
    )
    try:
        notifications.notify_vacantes_rejected(session_id, data.get("candidate_name"), note.strip())
    except Exception as e:  # noqa: BLE001
        print(f"[backoffice] ERROR notificando rechazo de vacantes: {e}")
    return {"status": "ok"}


@app.post("/api/backoffice/{session_id}/vacantes/replace")
async def backoffice_replace_vacantes(
    session_id: str, file: UploadFile = File(...), user: dict = Depends(auth.require_backoffice)
):
    data = sessions.load_session(session_id)
    if data is None:
        raise HTTPException(404, "Sesión no encontrada")
    if data.get("jobs_status") != "pending_review":
        raise HTTPException(400, "Las vacantes de esta sesión no están esperando revisión.")

    parsed = await _parse_vacantes_json(file)

    sessions.update_session(
        session_id,
        vacantes=parsed,
        jobs_status="ready",
        jobs_ready_at=datetime.now(timezone.utc).isoformat(),
        jobs_review_note=None,
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


@app.get("/backoffice")
async def backoffice_panel():
    return FileResponse(FRONTEND_DIR / "backoffice.html")


@app.get("/backoffice-login")
async def backoffice_login_page():
    return FileResponse(FRONTEND_DIR / "backoffice-login.html")


app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")
