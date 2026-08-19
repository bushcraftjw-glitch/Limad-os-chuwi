from pathlib import Path
import os

APP_ID = "de.limad.LiMusic"
APP_NAME = "LiMusic"
VERSION = "0.3.22"

HOME = Path.home()
XDG_DATA_HOME = Path(os.environ.get("XDG_DATA_HOME", HOME / ".local" / "share"))
XDG_CACHE_HOME = Path(os.environ.get("XDG_CACHE_HOME", HOME / ".cache"))
XDG_STATE_HOME = Path(os.environ.get("XDG_STATE_HOME", HOME / ".local" / "state"))

DATA_DIR = XDG_DATA_HOME / "limusic"
CACHE_DIR = XDG_CACHE_HOME / "limusic"
STATE_DIR = XDG_STATE_HOME / "limusic"
WEBKIT_DATA_DIR = DATA_DIR / "webkit-data"
WEBKIT_CACHE_DIR = CACHE_DIR / "webkit"
LIBRARY_FILE = DATA_DIR / "library.json"
LOG_FILE = STATE_DIR / "limusic.log"

for directory in (DATA_DIR, CACHE_DIR, STATE_DIR, WEBKIT_DATA_DIR, WEBKIT_CACHE_DIR):
    directory.mkdir(parents=True, exist_ok=True)
