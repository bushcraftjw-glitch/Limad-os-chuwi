from __future__ import annotations

import os
import shutil
import subprocess
import tempfile

from .documents import DocumentError, ImageDocument, PdfDocument


def recognize_text(document, page_index: int = 0) -> str:
    if shutil.which("tesseract") is None:
        raise DocumentError("OCR ist nicht installiert. Paket: tesseract-ocr")
    with tempfile.TemporaryDirectory(prefix="liview-ocr-") as tmp:
        image_path = os.path.join(tmp, "seite.png")
        if isinstance(document, PdfDocument):
            document._render_to_pillow(page_index, scale=2.5).convert("RGB").save(image_path, "PNG")
        elif isinstance(document, ImageDocument):
            document._image.convert("RGB").save(image_path, "PNG")
        else:
            raise DocumentError("OCR ist für PDF- und Bilddateien verfügbar.")
        languages = "deu+eng"
        result = subprocess.run(
            ["tesseract", image_path, "stdout", "-l", languages, "--psm", "6"],
            check=False, capture_output=True, text=True, timeout=45,
        )
        if result.returncode != 0:
            raise DocumentError(result.stderr.strip() or "OCR konnte nicht ausgeführt werden.")
        return result.stdout.strip()
