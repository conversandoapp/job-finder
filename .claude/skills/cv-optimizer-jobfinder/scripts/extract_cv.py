#!/usr/bin/env python3
"""
Extractor de texto plano de un CV (PDF o DOCX), para el skill
cv-optimizer-jobfinder. El texto extraído es la única fuente de verdad
para el resto del proceso -- no se debe inventar ni inferir nada que no
esté en este texto.

Uso:
    python3 extract_cv.py /ruta/al/cv.pdf
    python3 extract_cv.py /ruta/al/cv.docx
"""
import subprocess
import sys
from pathlib import Path


def extract_pdf(path: Path) -> str:
    import pdfplumber

    parts = []
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            parts.append(page.extract_text() or "")
    return "\n".join(parts)


def extract_docx(path: Path) -> str:
    result = subprocess.run(
        ["pandoc", str(path), "-t", "plain"],
        capture_output=True, text=True, check=True,
    )
    return result.stdout


def main() -> None:
    if len(sys.argv) != 2:
        print("Uso: python3 extract_cv.py <ruta-al-cv.pdf|.docx>", file=sys.stderr)
        sys.exit(1)

    path = Path(sys.argv[1])
    if not path.exists():
        print(f"No se encontró el archivo: {path}", file=sys.stderr)
        sys.exit(1)

    ext = path.suffix.lower()
    if ext == ".pdf":
        text = extract_pdf(path)
    elif ext in (".docx", ".doc"):
        text = extract_docx(path)
    else:
        print(f"Formato no soportado: {ext}. Usa PDF o DOCX.", file=sys.stderr)
        sys.exit(1)

    if not text.strip():
        print(
            "ADVERTENCIA: no se extrajo texto (¿PDF escaneado como imagen?). "
            "Pedí una versión en texto o el .docx original.",
            file=sys.stderr,
        )

    print(text)


if __name__ == "__main__":
    main()
