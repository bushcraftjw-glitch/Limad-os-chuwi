from __future__ import annotations

import mimetypes
import os
import subprocess
from datetime import datetime
from pathlib import Path

import pikepdf
from PIL import ExifTags

from .documents import ImageDocument, PdfDocument
from .stl import StlDocument
from .video import VideoDocument


def _size(value: int) -> str:
    units = ("B", "KiB", "MiB", "GiB", "TiB")
    number = float(value)
    for unit in units:
        if number < 1024.0 or unit == units[-1]:
            return f"{number:.0f} {unit}" if unit == "B" else f"{number:.2f} {unit}"
        number /= 1024.0
    return f"{value} B"


def _clean(value) -> str:
    text = str(value).strip()
    return text[:500]


def _pdf_info(document: PdfDocument) -> list[tuple[str, str]]:
    rows: list[tuple[str, str]] = [("Seiten", str(document.page_count)), ("Verschlüsselung", "Ja" if getattr(document, "source_encrypted", False) else "Nein")]
    try:
        with pikepdf.Pdf.open(document._work_path) as pdf:
            version = getattr(pdf, "pdf_version", None)
            if version:
                rows.append(("PDF-Version", _clean(version)))
            info = pdf.docinfo
            names = {
                "/Title": "Titel",
                "/Author": "Autor",
                "/Subject": "Betreff",
                "/Keywords": "Schlüsselwörter",
                "/Creator": "Ersteller",
                "/Producer": "PDF-Produzent",
                "/CreationDate": "Erstellt",
                "/ModDate": "Geändert",
            }
            for key, label in names.items():
                value = info.get(key)
                if value:
                    rows.append((label, _clean(value)))
    except Exception as exc:
        rows.append(("PDF-Information", f"Nicht lesbar: {exc}"))
    return rows


def _image_info(document: ImageDocument) -> list[tuple[str, str]]:
    width, height = document.page_size(0)
    image = document._image
    rows = [
        ("Abmessungen", f"{int(width)} × {int(height)} px"),
        ("Farbmodus", image.mode),
        ("Einzelbilder", str(document.frame_count)),
    ]
    if document._icc_profile:
        rows.append(("Farbprofil", "Eingebettetes ICC-Profil"))
    try:
        exif = image.getexif()
        wanted = {
            "Make": "Kamera-Hersteller",
            "Model": "Kamera-Modell",
            "Software": "Software",
            "DateTimeOriginal": "Aufgenommen",
            "ExposureTime": "Belichtungszeit",
            "FNumber": "Blende",
            "ISOSpeedRatings": "ISO",
            "PhotographicSensitivity": "ISO",
            "FocalLength": "Brennweite",
            "LensModel": "Objektiv",
        }
        for tag_id, value in exif.items():
            name = ExifTags.TAGS.get(tag_id, str(tag_id))
            label = wanted.get(name)
            if label and value not in (None, ""):
                rows.append((label, _clean(value)))
        gps_tag = next((tag for tag, name in ExifTags.TAGS.items() if name == "GPSInfo"), None)
        if gps_tag is not None and gps_tag in exif:
            rows.append(("GPS", "Vorhanden"))
    except Exception:
        pass
    return rows


def _video_info(document: VideoDocument) -> list[tuple[str, str]]:
    rows = [("Container", document.source_suffix.lstrip(".").upper() or "Video")]
    if not shutil_which("ffprobe"):
        return rows
    cmd = [
        "ffprobe", "-v", "error", "-select_streams", "v:0",
        "-show_entries", "stream=codec_name,width,height,r_frame_rate,bit_rate:format=duration,bit_rate,format_long_name",
        "-of", "default=noprint_wrappers=1:nokey=0", document.path,
    ]
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True, timeout=8)
    except Exception:
        return rows
    values = {}
    for line in result.stdout.splitlines():
        if "=" in line:
            key, value = line.split("=", 1)
            values[key] = value
    if values.get("format_long_name"):
        rows.append(("Format", values["format_long_name"]))
    if values.get("codec_name"):
        rows.append(("Video-Codec", values["codec_name"].upper()))
    if values.get("width") and values.get("height"):
        rows.append(("Auflösung", f"{values['width']} × {values['height']} px"))
    if values.get("duration"):
        try:
            seconds = float(values["duration"])
            rows.append(("Laufzeit", f"{int(seconds // 60):02d}:{int(seconds % 60):02d}"))
        except ValueError:
            pass
    bitrate = values.get("bit_rate")
    if bitrate and bitrate.isdigit():
        rows.append(("Bitrate", f"{int(bitrate) / 1000:.0f} kbit/s"))
    return rows


def shutil_which(name: str) -> str | None:
    from shutil import which
    return which(name)


def document_info(document) -> list[tuple[str, str]]:
    path = Path(document.path)
    stat = path.stat()
    mime, _ = mimetypes.guess_type(path.name)
    rows = [
        ("Datei", path.name),
        ("Typ", mime or path.suffix.lstrip(".").upper() or "Unbekannt"),
        ("Größe", _size(stat.st_size)),
        ("Pfad", str(path.parent)),
        ("Geändert", datetime.fromtimestamp(stat.st_mtime).strftime("%d.%m.%Y %H:%M")),
    ]
    if isinstance(document, PdfDocument):
        rows.extend(_pdf_info(document))
    elif isinstance(document, ImageDocument):
        rows.extend(_image_info(document))
    elif isinstance(document, StlDocument):
        x, y, z = document.dimensions
        rows.extend([
            ("3D-Format", document.format_name),
            ("Dreiecke", f"{document.triangle_count:,}"),
            ("Abmessungen", f"{x:.2f} × {y:.2f} × {z:.2f} mm"),
        ])
    elif isinstance(document, VideoDocument):
        rows.extend(_video_info(document))
    return rows
