import json
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Iterable

from .paths import LIBRARY_FILE

AUDIO_EXTENSIONS = {
    ".mp3", ".flac", ".wav", ".m4a", ".aac", ".ogg", ".oga", ".opus", ".alac",
    ".aiff", ".aif", ".ape", ".wma", ".ac3", ".dts", ".mka", ".mpc"
}
VIDEO_EXTENSIONS = {
    ".mp4", ".mkv", ".webm", ".mov", ".avi", ".mpeg", ".mpg", ".m4v", ".ts",
    ".m2ts", ".mts", ".flv", ".wmv", ".ogv", ".3gp", ".3g2", ".vob"
}
MEDIA_EXTENSIONS = AUDIO_EXTENSIONS | VIDEO_EXTENSIONS


@dataclass
class MediaItem:
    path: str
    title: str
    media_type: str

    @classmethod
    def from_path(cls, path: Path):
        resolved = path.expanduser().resolve()
        suffix = resolved.suffix.lower()
        media_type = "video" if suffix in VIDEO_EXTENSIONS else "audio"
        return cls(str(resolved), resolved.stem, media_type)


class LibraryStore:
    def __init__(self):
        self.items: list[MediaItem] = []
        self.load()

    def load(self):
        self.items = []
        if not LIBRARY_FILE.exists():
            return
        try:
            raw = json.loads(LIBRARY_FILE.read_text(encoding="utf-8"))
            for item in raw.get("items", []):
                path = Path(item.get("path", ""))
                if path.is_file():
                    self.items.append(MediaItem.from_path(path))
        except (OSError, ValueError, TypeError):
            self.items = []

    def save(self):
        payload = {"version": 1, "items": [asdict(item) for item in self.items]}
        temp = LIBRARY_FILE.with_suffix(".tmp")
        temp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        temp.replace(LIBRARY_FILE)

    def add_paths(self, paths: Iterable[Path]):
        existing = {item.path for item in self.items}
        added = []
        for path in paths:
            resolved = path.expanduser().resolve()
            if not resolved.is_file() or resolved.suffix.lower() not in MEDIA_EXTENSIONS:
                continue
            item = MediaItem.from_path(resolved)
            if item.path in existing:
                continue
            existing.add(item.path)
            self.items.append(item)
            added.append(item)
        if added:
            self.save()
        return added

    def scan_folder(self, folder: Path):
        candidates = []
        for path in folder.expanduser().resolve().rglob("*"):
            if path.is_file() and path.suffix.lower() in MEDIA_EXTENSIONS:
                candidates.append(path)
        candidates.sort(key=lambda item: item.name.casefold())
        return self.add_paths(candidates)

    def remove(self, path: str):
        before = len(self.items)
        self.items = [item for item in self.items if item.path != path]
        if len(self.items) != before:
            self.save()
            return True
        return False
