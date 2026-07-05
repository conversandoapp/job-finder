"""
Servicio de notificaciones para el admin (Conversando / conversandoapp@gmail.com).

Modo real: envía un correo real por Gmail SMTP usando una App Password.
  Configurar en backend/.env:
    NOTIFY_EMAIL_ENABLED=true
    NOTIFY_EMAIL_FROM=conversandoapp@gmail.com
    NOTIFY_EMAIL_APP_PASSWORD=xxxx xxxx xxxx xxxx   (App Password de 16 dígitos, NO tu contraseña normal)
    NOTIFY_EMAIL_TO=conversandoapp@gmail.com

Modo simulado (default, sin configurar nada): el aviso se guarda en
backend/storage/notifications.log y también queda visible en el panel
admin (GET /api/admin/notifications). Así se puede probar todo el flujo
localmente sin necesidad de credenciales reales.

Para activar el modo real solo hace falta:
1. Ir a https://myaccount.google.com/apppasswords (con verificación en 2 pasos activada)
2. Generar una "App Password" para "Mail"
3. Pegarla en NOTIFY_EMAIL_APP_PASSWORD en backend/.env
4. Poner NOTIFY_EMAIL_ENABLED=true
"""
import os
import smtplib
import json
from datetime import datetime, timezone
from email.mime.text import MIMEText
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
LOG_PATH = BASE_DIR / "storage" / "notifications.log"
LOG_PATH.parent.mkdir(parents=True, exist_ok=True)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _append_log(subject: str, body: str) -> None:
    entry = {"ts": _now_iso(), "subject": subject, "body": body}
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def read_notifications(limit: int = 50) -> list[dict]:
    if not LOG_PATH.exists():
        return []
    lines = LOG_PATH.read_text(encoding="utf-8").strip().splitlines()
    entries = [json.loads(l) for l in lines if l.strip()]
    return list(reversed(entries))[:limit]


def send_notification(subject: str, body: str) -> dict:
    """Envía (o simula) una notificación al admin. Nunca lanza excepción hacia
    el flujo principal: si falla el email real, cae de vuelta al log local."""
    enabled = os.getenv("NOTIFY_EMAIL_ENABLED", "false").lower() == "true"
    result = {"mode": "simulated", "sent": False, "error": None}

    if enabled:
        try:
            from_addr = os.getenv("NOTIFY_EMAIL_FROM", "conversandoapp@gmail.com")
            to_addr = os.getenv("NOTIFY_EMAIL_TO", "conversandoapp@gmail.com")
            app_password = os.getenv("NOTIFY_EMAIL_APP_PASSWORD", "")

            msg = MIMEText(body, "plain", "utf-8")
            msg["Subject"] = subject
            msg["From"] = from_addr
            msg["To"] = to_addr

            with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=10) as server:
                server.login(from_addr, app_password)
                server.sendmail(from_addr, [to_addr], msg.as_string())

            result = {"mode": "email", "sent": True, "error": None}
        except Exception as e:  # noqa: BLE001
            result = {"mode": "email", "sent": False, "error": str(e)}

    # Siempre guardamos en el log local también, así el panel admin
    # siempre tiene el historial completo de avisos.
    _append_log(subject, body)
    return result


def notify_cv_uploaded(session_id: str, candidate_name: str | None, pais: str,
                        linkedin_url: str | None, drive_link: str | None) -> dict:
    subject = f"[Job Finder] Nuevo CV subido — sesión {session_id[:8]}"
    body = (
        f"Se subió un nuevo CV para optimizar.\n\n"
        f"Session ID: {session_id}\n"
        f"Nombre (según archivo): {candidate_name or '(no detectado)'}\n"
        f"País: {pais}\n"
        f"LinkedIn: {linkedin_url or '(no provisto)'}\n"
        f"CV en Drive: {drive_link or '(no disponible, revisar carpeta local backend/storage/sessions/' + session_id + '/)'}\n\n"
        f"Entra al panel admin para subir el CV optimizado cuando esté listo:\n"
        f"http://localhost:8000/admin.html#{session_id}\n"
    )
    return send_notification(subject, body)


def notify_jobs_requested(session_id: str, candidate_name: str | None, pais: str) -> dict:
    subject = f"[Job Finder] Solicitud de vacantes — sesión {session_id[:8]}"
    body = (
        f"El usuario pidió buscar vacantes de LinkedIn para su perfil.\n\n"
        f"Session ID: {session_id}\n"
        f"Nombre: {candidate_name or '(no detectado)'}\n"
        f"País: {pais}\n\n"
        f"Entra al panel admin para subir el vacantes.json cuando esté listo:\n"
        f"http://localhost:8000/admin.html#{session_id}\n"
    )
    return send_notification(subject, body)
