"""
Empaqueta el CV original + los puestos de interés del candidato en un único
.zip, para que le lleguen juntos al admin (ver notifications.notify_cv_uploaded
y el endpoint GET /api/admin/download/zip/{session_id}).
"""
import io
import json
import zipfile
from pathlib import Path


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


CV_DOC_EXTENSIONS = (".docx", ".doc", ".pdf")


def extract_cv_optimizado_zip(content: bytes) -> tuple[bytes, str, bytes]:
    """Extrae el CV optimizado (.docx/.doc/.pdf) y el analysis.json de un
    cv_optimizado_{nombre}.zip generado por el skill cv-optimizer-jobfinder.
    Devuelve (cv_bytes, cv_ext, analysis_bytes). Levanta ValueError si el
    zip es inválido o le falta alguno de los dos archivos."""
    try:
        zf = zipfile.ZipFile(io.BytesIO(content))
    except zipfile.BadZipFile as e:
        raise ValueError("El .zip no es válido") from e

    with zf:
        cv_name = next((n for n in zf.namelist() if n.lower().endswith(CV_DOC_EXTENSIONS)), None)
        json_name = next((n for n in zf.namelist() if n.lower().endswith(".json")), None)
        if not cv_name or not json_name:
            raise ValueError("El .zip debe contener un .docx/.doc/.pdf y un .json")
        cv_bytes = zf.read(cv_name)
        analysis_bytes = zf.read(json_name)

    cv_ext = Path(cv_name).suffix
    return cv_bytes, cv_ext, analysis_bytes
