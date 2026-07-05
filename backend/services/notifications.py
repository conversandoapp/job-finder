"""
Servicio de notificaciones para el admin (Conversando / conversandoapp@gmail.com).

Modo real: envía un correo real por Gmail SMTP usando una App Password.
  Configurar en backend/.env:
    NOTIFY_EMAIL_ENABLED=true
    NOTIFY_EMAIL_FROM=conversandoapp@gmail.com
    NOTIFY_EMAIL_APP_PASSWORD=xxxx xxxx xxxx xxxx   (App Password de 16 dígitos, NO tu contraseña normal)
    NOTIFY_EMAIL_TO=conversandoapp@gmail.com

Modo simulado (default, sin configurar nada): el aviso se guarda en la
tabla `notifications` de Supabase y también queda visible en el panel
admin (GET /api/admin/notifications). Así se puede probar todo el flujo
sin necesidad de credenciales reales de email.

Para activar el modo real solo hace falta:
1. Ir a https://myaccount.google.com/apppasswords (con verificación en 2 pasos activada)
2. Generar una "App Password" para "Mail"
3. Pegarla en NOTIFY_EMAIL_APP_PASSWORD en backend/.env
4. Poner NOTIFY_EMAIL_ENABLED=true
"""
import os
import smtplib
from datetime import datetime, timezone
from email.mime.text import MIMEText

from services import db


def _append_log(subject: str, body: str) -> None:
    db.get_client().table("notifications").insert({"subject": subject, "body": body}).execute()


def read_notifications(limit: int = 50) -> list[dict]:
    res = (
        db.get_client()
        .table("notifications")
        .select("*")
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
    )
    return [{"ts": r["created_at"], "subject": r["subject"], "body": r["body"]} for r in res.data]


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

    # Siempre guardamos el registro en Supabase también, así el panel admin
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
        f"CV en Drive: {drive_link or '(no disponible, descargalo desde el panel admin)'}\n\n"
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
