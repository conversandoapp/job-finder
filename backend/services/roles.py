"""
Roles de usuario y asignación usuario <-> backoffice.

ADMIN_EMAIL (variable de entorno) sigue siendo el admin permanente de
respaldo: nunca se lee su fila real de `user_roles` para decidir si es
admin, así que nunca se puede perder ese acceso desde la UI. El resto de
los roles (usuario/backoffice/admin) se gestionan desde /admin y viven en
la tabla `user_roles`. BACKOFFICE_EMAILS (env var) queda como fallback
legacy: solo se consulta si el usuario no tiene fila en `user_roles`.

La lista de "usuarios" gestionables se limita a quienes ya tienen al
menos una fila en `sessions` (no se listan todas las cuentas de Supabase
Auth) -- así lo pidió el dueño del producto.
"""
import os

from services import db, sessions

ROLES = ("usuario", "backoffice", "admin")

PENDING_REVIEW_STATUSES = ("pending_review",)


class PendingProcessError(Exception):
    """El usuario tiene una sesión en pending_review; no se puede tocar su
    asignación de backoffice ni degradarlo de rol backoffice/usuario hasta
    que ese proceso se resuelva (aprobado o rechazado)."""


def _admin_email() -> str:
    return os.getenv("ADMIN_EMAIL", "").strip().lower()


def _backoffice_emails() -> set[str]:
    raw = os.getenv("BACKOFFICE_EMAILS", "")
    # El filtro "if e.strip()" es obligatorio: sin él, con la env var vacía
    # el set quedaría en {""}, y cualquier JWT sin claim "email" calificaría
    # como backoffice por accidente.
    return {e.strip().lower() for e in raw.split(",") if e.strip()}


def is_permanent_admin_email(email: str | None) -> bool:
    admin_email = _admin_email()
    return bool(admin_email) and (email or "").strip().lower() == admin_email


def _get_role_row(user_id: str) -> dict | None:
    res = db.get_client().table("user_roles").select("*").eq("user_id", user_id).execute()
    return res.data[0] if res.data else None


def get_role(user_id: str | None, email: str | None) -> str:
    if is_permanent_admin_email(email):
        return "admin"
    if not user_id:
        return "usuario"
    row = _get_role_row(user_id)
    if row:
        return row["role"]
    if (email or "").strip().lower() in _backoffice_emails():
        return "backoffice"
    return "usuario"


def has_pending_process(user_id: str) -> bool:
    for session in sessions.list_sessions_for_user(user_id):
        if session.get("cv_status") in PENDING_REVIEW_STATUSES:
            return True
        if session.get("jobs_status") in PENDING_REVIEW_STATUSES:
            return True
    return False


def get_assignment(user_id: str) -> dict | None:
    res = (
        db.get_client()
        .table("backoffice_assignments")
        .select("*")
        .eq("user_id", user_id)
        .execute()
    )
    return res.data[0] if res.data else None


def list_assigned_user_ids(backoffice_user_id: str) -> set[str]:
    res = (
        db.get_client()
        .table("backoffice_assignments")
        .select("user_id")
        .eq("backoffice_user_id", backoffice_user_id)
        .execute()
    )
    return {row["user_id"] for row in res.data}


def _delete_assignment(user_id: str) -> None:
    db.get_client().table("backoffice_assignments").delete().eq("user_id", user_id).execute()


def _delete_assignments_for_backoffice(backoffice_user_id: str) -> None:
    (
        db.get_client()
        .table("backoffice_assignments")
        .delete()
        .eq("backoffice_user_id", backoffice_user_id)
        .execute()
    )


def set_role(*, user_id: str, email: str, role: str, actor_user_id: str) -> dict:
    if role not in ROLES:
        raise ValueError(f"Rol inválido: {role}")
    if user_id == actor_user_id:
        raise ValueError("No puedes cambiar tu propio rol")
    if is_permanent_admin_email(email):
        raise ValueError("Esta cuenta es el admin permanente y no se puede cambiar desde acá")

    previous_role = get_role(user_id, email)

    if previous_role == "usuario" and role != "usuario":
        assignment = get_assignment(user_id)
        if assignment and has_pending_process(user_id):
            raise PendingProcessError(
                "Este usuario tiene un proceso en revisión; no se puede cambiar su rol hasta que se resuelva."
            )

    row = {"user_id": user_id, "email": email, "role": role}
    res = db.get_client().table("user_roles").upsert(row).execute()

    if role != "usuario":
        _delete_assignment(user_id)
    if previous_role == "backoffice" and role != "backoffice":
        _delete_assignments_for_backoffice(user_id)

    return res.data[0] if res.data else row


def assign_user_to_backoffice(*, user_id: str, backoffice_user_id: str) -> dict:
    if not user_id or not backoffice_user_id:
        raise ValueError("Falta user_id o backoffice_user_id")

    users_by_id = {u["user_id"]: u for u in list_users_with_sessions()}
    user = users_by_id.get(user_id)
    backoffice_user = users_by_id.get(backoffice_user_id)
    if user is None:
        raise ValueError("Usuario no encontrado")
    if backoffice_user is None or backoffice_user["role"] != "backoffice":
        raise ValueError("El backoffice elegido no tiene rol de backoffice")

    existing = get_assignment(user_id)
    if existing and existing["backoffice_user_id"] != backoffice_user_id:
        if has_pending_process(user_id):
            raise PendingProcessError(
                "Este usuario tiene un proceso en revisión; no se puede reasignar hasta que se resuelva."
            )

    row = {
        "user_id": user_id,
        "user_email": user["email"],
        "backoffice_user_id": backoffice_user_id,
        "backoffice_email": backoffice_user["email"],
    }
    res = db.get_client().table("backoffice_assignments").upsert(row).execute()
    return res.data[0] if res.data else row


def unassign_user(user_id: str) -> None:
    if has_pending_process(user_id):
        raise PendingProcessError(
            "Este usuario tiene un proceso en revisión; no se puede quitar la asignación hasta que se resuelva."
        )
    _delete_assignment(user_id)


def list_backoffice_users() -> list[dict]:
    return [u for u in list_users_with_sessions() if u["role"] == "backoffice"]


def list_unassigned_users() -> list[dict]:
    return [u for u in list_users_with_sessions() if u["role"] == "usuario" and not u["backoffice_user_id"]]


def list_users_with_sessions() -> list[dict]:
    """Un usuario por fila, deduplicado desde `sessions` (solo se listan
    usuarios que ya tienen al menos una sesión creada). candidate_name sale
    de la sesión más reciente que tenga uno no vacío."""
    all_sessions = sessions.list_sessions()  # ya viene ordenado por created_at desc

    by_user: dict[str, dict] = {}
    for s in all_sessions:
        user_id = s.get("user_id")
        if not user_id:
            continue
        entry = by_user.setdefault(user_id, {
            "user_id": user_id,
            "email": s.get("user_email"),
            "candidate_name": None,
            "has_pending_process": False,
        })
        if not entry["candidate_name"] and s.get("candidate_name"):
            entry["candidate_name"] = s["candidate_name"]
        if s.get("cv_status") in PENDING_REVIEW_STATUSES or s.get("jobs_status") in PENDING_REVIEW_STATUSES:
            entry["has_pending_process"] = True

    roles_res = db.get_client().table("user_roles").select("*").execute()
    role_by_user = {row["user_id"]: row["role"] for row in roles_res.data}

    assignments_res = db.get_client().table("backoffice_assignments").select("*").execute()
    assignment_by_user = {row["user_id"]: row for row in assignments_res.data}

    backoffice_emails = _backoffice_emails()
    users = []
    for user_id, entry in by_user.items():
        if is_permanent_admin_email(entry["email"]):
            entry["role"] = "admin"
        elif user_id in role_by_user:
            entry["role"] = role_by_user[user_id]
        elif (entry["email"] or "").strip().lower() in backoffice_emails:
            entry["role"] = "backoffice"
        else:
            entry["role"] = "usuario"
        assignment = assignment_by_user.get(user_id)
        entry["backoffice_user_id"] = assignment["backoffice_user_id"] if assignment else None
        entry["backoffice_email"] = assignment["backoffice_email"] if assignment else None
        entry["is_permanent_admin"] = is_permanent_admin_email(entry["email"])
        users.append(entry)

    users.sort(key=lambda u: (u["email"] or "").lower())
    return users
