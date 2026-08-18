#!/usr/bin/python3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
service = (ROOT / "build/rootfs/usr/lib/systemd/user/limad-drop.service").read_text(encoding="utf-8")
for token in ("ExecStart=/usr/local/bin/limad-dropd", "WantedBy=default.target", "Restart=on-failure"):
    if token not in service:
        raise SystemExit(f"ERROR: LiDrop service token missing: {token}")
status = (ROOT / "build/rootfs/usr/local/bin/limad-lidrop-status-ensure").read_text(encoding="utf-8")
for token in ("systemctl --user daemon-reload", "systemctl --user enable --now limad-drop.service", "systemctl --user is-active --quiet limad-drop.service"):
    if token not in status:
        raise SystemExit(f"ERROR: LiDrop status helper token missing: {token}")
install = (ROOT / "build/install-target.sh").read_text(encoding="utf-8")
if "systemctl --global enable limad-drop.service" not in install:
    raise SystemExit("ERROR: LiDrop service is not globally enabled")
first_login = (ROOT / "build/rootfs/usr/local/bin/limad-base1-first-login").read_text(encoding="utf-8")
for token in ("enable_extension_reliably()", "enable_extension_reliably limad-menu@limad.local", "gsettings get org.gnome.shell enabled-extensions"):
    if token not in first_login:
        raise SystemExit(f"ERROR: LiMaD menu activation token missing: {token}")
menu = (ROOT / "build/rootfs/usr/share/gnome-shell/extensions/limad-menu@limad.local/extension.js").read_text(encoding="utf-8")
for token in ("Gio.File.new_for_path", "text: 'L'", "Main.panel.addToStatusArea(this.uuid, this._indicator, 0, 'left')", "this._activities?.hide()"):
    if token not in menu:
        raise SystemExit(f"ERROR: LiMaD menu runtime token missing: {token}")
sync = (ROOT / "build/rootfs/usr/local/bin/limad-sync-gtk4-theme").read_text(encoding="utf-8")
for token in ("grep -Fvx", "head -n1", "limad-titlebuttons.css"):
    if token not in sync:
        raise SystemExit(f"ERROR: GTK4 import-order token missing: {token}")
workflow = (ROOT / ".github/workflows/build-iso.yml").read_text(encoding="utf-8")
for token in ("dconf-cli", "dconf help compile", "tests/test-v20-menu-lidrop.py"):
    if token not in workflow:
        raise SystemExit(f"ERROR: V20 workflow token missing: {token}")
print("V20 MENU + LIDROP + GTK4 TEST: PASS")
