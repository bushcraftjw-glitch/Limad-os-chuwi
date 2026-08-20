#!/usr/bin/python3
from __future__ import annotations

import hashlib
import json
import pathlib
import shutil
import subprocess
import tempfile
import zipfile

ROOT = pathlib.Path(__file__).resolve().parents[1]

core = (ROOT / "build/rootfs/usr/local/bin/limad-desktop-core-system").read_text(encoding="utf-8")
if "favorite-apps=['app.zen_browser.zen.desktop'" not in core:
    raise SystemExit("ERROR: Zen Browser is not the first V22 Dock favorite")
if "firefox_firefox.desktop" in core:
    raise SystemExit("ERROR: Firefox remains in V22 Dock defaults")

runtime = (ROOT / "build/rootfs/usr/local/bin/limad-runtime-deps").read_text(encoding="utf-8")
for package in (
    "flatpak",
    "gir1.2-webkit-6.0",
    "gstreamer1.0-gtk4",
    "gstreamer1.0-libav",
    "gstreamer1.0-plugins-bad",
    "gstreamer1.0-plugins-base",
    "gstreamer1.0-plugins-good",
    "gstreamer1.0-plugins-ugly",
    "gstreamer1.0-tools",
):
    if f"    {package}\n" not in runtime:
        raise SystemExit(f"ERROR: V22 runtime dependency missing: {package}")

required_apps = (ROOT / "build/rootfs/usr/local/bin/limad-required-user-apps").read_text(encoding="utf-8")
for token in (
    'ZEN_ID="app.zen_browser.zen"',
    'EASYEFFECTS_ID="com.github.wwmm.easyeffects"',
    'limad-zen-deutsch-setup',
    'limad-install-klang-preset',
    'app.zen_browser.zen.desktop',
):
    if token not in required_apps:
        raise SystemExit(f"ERROR: V22 required-app token missing: {token}")

ensure = (ROOT / "build/rootfs/usr/local/bin/limad-titlebuttons-ensure").read_text(encoding="utf-8")
for token in ("close,minimize,maximize:", "limad-sync-gtk4-theme"):
    if token not in ensure:
        raise SystemExit(f"ERROR: titlebutton ensure token missing: {token}")

program_zip = ROOT / ".cache/vendor/LiMaD-Programme-BASE1B-EXTRAKT.zip"
if not program_zip.is_file():
    subprocess.run([str(ROOT / "tools/reassemble-vendor.sh")], check=True)
with tempfile.TemporaryDirectory() as tmp:
    tmp_root = pathlib.Path(tmp)
    with zipfile.ZipFile(program_zip) as archive:
        for member, target in (
            ("LiMaD-Programme-BASE1B-EXTRAKT/filesystem/usr/share/limad-notes/app.py", "usr/share/limad-notes/app.py"),
            ("LiMaD-Programme-BASE1B-EXTRAKT/filesystem/usr/share/limad-windows/installer.py", "usr/share/limad-windows/installer.py"),
        ):
            destination = tmp_root / target
            destination.parent.mkdir(parents=True, exist_ok=True)
            with archive.open(member) as source, destination.open("wb") as output:
                shutil.copyfileobj(source, output)
    subprocess.run([str(ROOT / "tools/patch-v22-titlebars.py"), str(tmp_root)], check=True)
    notes = (tmp_root / "usr/share/limad-notes/app.py").read_text(encoding="utf-8")
    windows_apps = (tmp_root / "usr/share/limad-windows/installer.py").read_text(encoding="utf-8")
    for token in ('header.set_show_title_buttons(True)', 'header.set_decoration_layout("close,minimize,maximize:")'):
        if token not in notes:
            raise SystemExit(f"ERROR: LiNotes titlebar patch missing: {token}")
    for token in (
        'header.set_decoration_layout("close,minimize,maximize:")',
        'header.set_show_start_title_buttons(True)',
        'header.set_show_end_title_buttons(False)',
    ):
        if token not in windows_apps:
            raise SystemExit(f"ERROR: Windows-Programme titlebar patch missing: {token}")

checksum_file = ROOT / "assets/limusic/LiMusic-0.3.27-SHA256SUMS.txt"
for line in checksum_file.read_text(encoding="utf-8").splitlines():
    digest, relative = line.split("  ", 1)
    if not relative.startswith("payload/"):
        raise SystemExit(f"ERROR: invalid LiMusic checksum path: {relative}")
    target = ROOT / "build/rootfs/usr/share/limusic" / relative.removeprefix("payload/")
    if not target.is_file():
        raise SystemExit(f"ERROR: LiMusic system file missing: {target}")
    actual = hashlib.sha256(target.read_bytes()).hexdigest()
    if actual != digest:
        raise SystemExit(f"ERROR: LiMusic payload hash mismatch: {target}")

registry = json.loads((ROOT / "build/rootfs/usr/share/limad-updater/apps.json").read_text(encoding="utf-8"))
matches = [app for app in registry.get("apps", []) if app.get("app_id") == "de.limad.LiMusic"]
if len(matches) != 1:
    raise SystemExit("ERROR: LiMusic updater registry entry is missing or duplicated")
entry = matches[0]
for key, expected in (
    ("launcher", "/usr/local/bin/limusic"),
    ("system_root", "/usr/share/limusic"),
    ("system_version_file", "/usr/share/limusic/VERSION"),
):
    if entry.get(key) != expected:
        raise SystemExit(f"ERROR: LiMusic updater registry mismatch for {key}")

for required in (
    "data/adblock-scriptlet-rules.json",
    "data/youtube-adblock-webkit.json",
    "src/limusic/adblock_engine.py",
):
    if required not in entry.get("required", []):
        raise SystemExit(f"ERROR: LiMusic 0.3.27 updater required file missing: {required}")

print("V22 APPS + TITLEBUTTONS + LIMUSIC TEST: PASS")
