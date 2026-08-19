from __future__ import annotations

import os
import shutil
from pathlib import Path

import cairo

from .documents import BaseDocument, DocumentError


class VideoDocument(BaseDocument):
    kind = "video"
    supported_extensions = {
        ".mp4",
        ".m4v",
        ".mov",
        ".qt",
        ".mkv",
        ".mk3d",
        ".webm",
        ".avi",
        ".wmv",
        ".asf",
        ".flv",
        ".f4v",
        ".mpg",
        ".mpeg",
        ".mpe",
        ".m1v",
        ".m2v",
        ".m2p",
        ".m2t",
        ".ts",
        ".mts",
        ".m2ts",
        ".vob",
        ".ogv",
        ".ogm",
        ".3gp",
        ".3g2",
        ".rm",
        ".rmvb",
        ".divx",
        ".dv",
        ".mxf",
        ".nut",
        ".y4m",
        ".h264",
        ".264",
        ".h265",
        ".265",
        ".hevc",
        ".vp8",
        ".vp9",
        ".av1",
    }

    def __init__(self, path: str):
        super().__init__(path)
        if not os.path.isfile(self.path):
            raise DocumentError("Videodatei wurde nicht gefunden.")
        self.source_suffix = Path(self.path).suffix.lower()

    @property
    def page_count(self) -> int:
        return 1

    def page_size(self, index: int) -> tuple[float, float]:
        return 1280.0, 720.0

    def render_page(self, index: int, cr: cairo.Context, scale: float) -> None:
        raise DocumentError("Video wird über die native GTK-Medienwiedergabe dargestellt.")

    def render_thumbnail(self, index: int, max_width: int = 132, max_height: int = 176):
        raise DocumentError("Für Video wird in dieser Version keine Miniatur erzeugt.")

    def save(self) -> None:
        self.dirty = False

    def save_as(self, target: str) -> None:
        target = os.path.abspath(target)
        if Path(target).suffix.lower() != self.source_suffix:
            raise DocumentError(f"Das Video muss als {self.source_suffix} gespeichert werden.")
        shutil.copy2(self.path, target)
        self.path = target
        self.dirty = False

    def export(self, target: str, page_index: int) -> None:
        raise DocumentError("Video-Transkodierung ist in dieser LiView-Version noch nicht vorgesehen.")

    def print_page(self, page_index: int, cr: cairo.Context, width: float, height: float) -> None:
        raise DocumentError("Videos können nicht gedruckt werden.")
