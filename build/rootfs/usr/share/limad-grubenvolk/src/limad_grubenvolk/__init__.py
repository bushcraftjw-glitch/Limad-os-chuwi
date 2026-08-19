from pathlib import Path

_VERSION_FILE = Path(__file__).resolve().parents[2] / "VERSION"
try:
    VERSION = _VERSION_FILE.read_text(encoding="utf-8").strip() or "0.0.0-unknown"
except OSError:
    VERSION = "3.6.7"

APP_ID = "de.limad.Grubenvolk"
APP_NAME = "GRUBENVOLK"
