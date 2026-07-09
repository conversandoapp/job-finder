"""
Empaqueta el CV original + los puestos de interés del candidato en un único
.zip, para que le lleguen juntos al admin (ver notifications.notify_cv_uploaded
y el endpoint GET /api/admin/download/zip/{session_id}).
"""
import io
import json
import zipfile


def build_postulacion_zip(
    cv_content: bytes, cv_filename: str, roles_modo: str, roles_elegidos: list[str]
) -> bytes:
    """cv_filename debe incluir la extensión (ej. "cv_original.pdf").
    roles_modo: "candidato" (el candidato eligió los puestos) o "admin"
    (el candidato prefiere que el admin elija según su CV).
    roles_elegidos: lista de puestos en orden de prioridad (el primero es
    el más importante). Vacía si roles_modo == "admin"."""
    roles_payload = {"modo": roles_modo, "roles": roles_elegidos}

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(cv_filename, cv_content)
        zf.writestr("puestos_candidato.json", json.dumps(roles_payload, ensure_ascii=False, indent=2))
    return buf.getvalue()
