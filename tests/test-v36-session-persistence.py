#!/usr/bin/python3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ROOTFS = ROOT / "build/rootfs"
FIRST_LOGIN = ROOTFS / "usr/local/bin/limad-base1-first-login"
DESKTOP_CORE = ROOTFS / "usr/local/bin/limad-desktop-core-system"
WELCOME = ROOTFS / "usr/share/limad-welcome/app.py"
WELCOME_VERSION = ROOTFS / "usr/share/limad-welcome/VERSION"
WELCOME_ONCE = ROOTFS / "usr/local/bin/limad-welcome-once"

first_login = FIRST_LOGIN.read_text()
if "favorite-apps" in first_login:
    raise AssertionError("V36 first-login must not write or validate user Dock favorites")

core = DESKTOP_CORE.read_text()
if "favorite-apps=['app.zen_browser.zen.desktop'" not in core:
    raise AssertionError("V36 must retain the initial Dock list as a system default")

if WELCOME_VERSION.read_text().strip() != "1.0.1":
    raise AssertionError("V36 Welcome system version must be 1.0.1")

welcome = WELCOME.read_text()
for marker in (
    "def persist_choice():",
    "if again.get_active():",
    "os.remove(MARK)",
    "def close_request(_window):",
    "persist_choice()",
    'w.connect("close-request",close_request)',
):
    if marker not in welcome:
        raise AssertionError(f"V36 Welcome persistence marker missing: {marker}")

once = WELCOME_ONCE.read_text()
if 'MARK="${XDG_CONFIG_HOME:-$HOME/.config}/limad/welcome-3.0.done"' not in once:
    raise AssertionError("V36 Welcome autostart marker path changed unexpectedly")
if '[[ -e "$MARK" ]] && exit 0' not in once:
    raise AssertionError("V36 Welcome once helper does not honor the dismissal marker")

print("V36 SESSION PERSISTENCE TEST: PASS")
