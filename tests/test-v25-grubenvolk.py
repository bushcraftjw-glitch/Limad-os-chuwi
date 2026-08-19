#!/usr/bin/python3
from __future__ import annotations

import ast
import json
import struct
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ROOTFS = ROOT / "build/rootfs"
APP_ROOT = ROOTFS / "usr/share/limad-grubenvolk"
APP_ID = "de.limad.Grubenvolk"
DESKTOP_ID = f"{APP_ID}.desktop"
VERSION = "3.6.7"

required_paths = [
    APP_ROOT / "VERSION",
    APP_ROOT / "web/index.html",
    APP_ROOT / "src/limad_grubenvolk/__init__.py",
    APP_ROOT / "src/limad_grubenvolk/__main__.py",
    APP_ROOT / "src/limad_grubenvolk/shell.py",
    APP_ROOT / "de.limad.Grubenvolk.png",
    APP_ROOT / "de.limad.Grubenvolk.svg",
    ROOTFS / "usr/local/bin/limad-grubenvolk",
    ROOTFS / "usr/local/bin/limad-grubenvolk-deps",
    ROOTFS / "usr/share/applications/de.limad.Grubenvolk.desktop",
    ROOT / "build/grubenvolk-packages.txt",
    ROOT / "build/prepare-grubenvolk-offline-repo.sh",
]
for path in required_paths:
    if not path.is_file() or path.stat().st_size == 0:
        raise AssertionError(f"GRUBENVOLK required file missing or empty: {path.relative_to(ROOT)}")

if (APP_ROOT / "VERSION").read_text().strip() != VERSION:
    raise AssertionError("GRUBENVOLK system version mismatch")

for rel in (
    "src/limad_grubenvolk/__init__.py",
    "src/limad_grubenvolk/__main__.py",
    "src/limad_grubenvolk/shell.py",
):
    ast.parse((APP_ROOT / rel).read_text(encoding="utf-8"), filename=rel)

web = (APP_ROOT / "web/index.html").read_text(encoding="utf-8", errors="strict")
if "http://" in web or "https://" in web:
    raise AssertionError("GRUBENVOLK V25 system payload must not depend on remote web assets")

launcher = (ROOTFS / "usr/local/bin/limad-grubenvolk").read_text()
for needle in (
    "/usr/local/libexec/limad-select-app-root",
    "/usr/share/limad-grubenvolk",
    "de.limad.Grubenvolk/current/payload",
    "src/limad_grubenvolk/__main__.py",
    "PYTHONPATH=\"$APP_ROOT/src",
    "python3 -m limad_grubenvolk",
):
    if needle not in launcher:
        raise AssertionError(f"GRUBENVOLK updater-aware launcher missing {needle!r}")

config = json.loads((ROOTFS / "usr/share/limad-updater/apps.json").read_text())
matches = [item for item in config.get("apps", []) if item.get("app_id") == APP_ID]
if len(matches) != 1:
    raise AssertionError(f"expected exactly one GRUBENVOLK updater entry, got {len(matches)}")
app = matches[0]
if app.get("launcher") != "/usr/local/bin/limad-grubenvolk":
    raise AssertionError("GRUBENVOLK updater launcher mismatch")
if app.get("system_root") != "/usr/share/limad-grubenvolk":
    raise AssertionError("GRUBENVOLK updater system_root mismatch")
for rel in (
    "VERSION",
    "web/index.html",
    "src/limad_grubenvolk/__init__.py",
    "src/limad_grubenvolk/__main__.py",
    "src/limad_grubenvolk/shell.py",
    "limad-grubenvolk",
    "pyproject.toml",
    "de.limad.Grubenvolk.desktop",
    "de.limad.Grubenvolk.png",
    "de.limad.Grubenvolk.svg",
):
    if rel not in app.get("required", []):
        raise AssertionError(f"GRUBENVOLK updater required file missing: {rel}")
if app.get("executables") != ["limad-grubenvolk"]:
    raise AssertionError("GRUBENVOLK updater executable registration mismatch")

desktop = (ROOTFS / "usr/share/applications/de.limad.Grubenvolk.desktop").read_text()
for needle in (
    "Name=GRUBENVOLK",
    "Exec=/usr/local/bin/limad-grubenvolk",
    "TryExec=/usr/local/bin/limad-grubenvolk",
    "Icon=de.limad.Grubenvolk",
    "StartupWMClass=de.limad.Grubenvolk",
    "X-LiMaD-Version=3.6.7",
    "Actions=Update;",
    "Exec=/usr/local/bin/limad-updater --app de.limad.Grubenvolk",
):
    if needle not in desktop:
        raise AssertionError(f"GRUBENVOLK desktop entry missing {needle!r}")

# Validate the original 512 icon and every generated LiMaD/hicolor PNG size
# without adding Pillow to the GitHub build test environment.
def png_size(path: Path) -> tuple[int, int]:
    data = path.read_bytes()[:24]
    if data[:8] != b"\x89PNG\r\n\x1a\n" or data[12:16] != b"IHDR":
        raise AssertionError(f"invalid PNG: {path.relative_to(ROOT)}")
    return struct.unpack(">II", data[16:24])

for theme in ("LiMaD", "hicolor"):
    for size in (16, 22, 24, 32, 48, 64, 96, 128, 256, 512):
        icon = ROOTFS / f"usr/share/icons/{theme}/{size}x{size}/apps/de.limad.Grubenvolk.png"
        if not icon.is_file():
            raise AssertionError(f"GRUBENVOLK icon missing: {icon.relative_to(ROOT)}")
        if png_size(icon) != (size, size):
            raise AssertionError(f"GRUBENVOLK icon has wrong size: {icon.relative_to(ROOT)}")
    svg = ROOTFS / f"usr/share/icons/{theme}/scalable/apps/de.limad.Grubenvolk.svg"
    if not svg.is_file() or svg.stat().st_size == 0:
        raise AssertionError(f"GRUBENVOLK scalable icon missing: {svg.relative_to(ROOT)}")

packages = [
    line.strip()
    for line in (ROOT / "build/grubenvolk-packages.txt").read_text().splitlines()
    if line.strip() and not line.lstrip().startswith("#")
]
for package in ("python3", "python3-gi", "gir1.2-gtk-4.0", "gir1.2-webkit-6.0"):
    if package not in packages:
        raise AssertionError(f"GRUBENVOLK offline package missing: {package}")

repo = (ROOT / "build/prepare-grubenvolk-offline-repo.sh").read_text()
for needle in (
    "resolute main restricted universe multiverse",
    "--download-only",
    "--no-install-recommends",
    "dpkg-scanpackages --multiversion",
    "GRUBENVOLK offline repository: PASS",
):
    if needle not in repo:
        raise AssertionError(f"GRUBENVOLK offline repo builder missing {needle!r}")
if "< <(find" in repo:
    raise AssertionError("GRUBENVOLK repo builder must not use early-closing find process substitutions")

deps = (ROOTFS / "usr/local/bin/limad-grubenvolk-deps").read_text()
for needle in (
    "/usr/share/limad/offline/grubenvolk",
    'gi.require_version("Gtk", "4.0")',
    'gi.require_version("WebKit", "6.0")',
    'APP_ID == "de.limad.Grubenvolk"',
    'VERSION == "3.6.7"',
    "GRUBENVOLK dependencies: PASS",
):
    if needle not in deps:
        raise AssertionError(f"GRUBENVOLK dependency helper missing {needle!r}")

payload = (ROOT / "build/prepare-payload.sh").read_text()
if "prepare-grubenvolk-offline-repo.sh" not in payload:
    raise AssertionError("GRUBENVOLK offline repository is not added to payload")

installer = (ROOT / "build/install-target.sh").read_text()
if "/usr/local/bin/limad-grubenvolk-deps" not in installer:
    raise AssertionError("GRUBENVOLK dependency helper is not called by target installer")
for line in installer.splitlines():
    if "/usr/local/bin/limad-grubenvolk-deps" in line and "|| true" in line:
        raise AssertionError("GRUBENVOLK dependency installation must be install-critical")

expected_favorites = "['app.zen_browser.zen.desktop', 'de.limad.Mail.desktop', 'de.limad.Cut.desktop', 'de.limad.Study.desktop', 'de.limad.Notes.desktop', 'de.limad.Drop.desktop', 'de.limad.Link.desktop', 'de.limad.Save.desktop', 'de.limad.WindowsApps.desktop', 'de.limad.Updater.desktop', 'de.limad.Klang.desktop', 'de.limad.Terminal.desktop', 'org.gnome.Nautilus.desktop', 'libreoffice-startcenter.desktop', 'de.limad.SystemInfo.desktop', 'de.limad.SystemUpdate.desktop', 'de.limad.Welcome.desktop', 'de.limad.Grubenvolk.desktop']"
for rel in (
    "usr/local/bin/limad-desktop-core-system",
    "usr/local/bin/limad-required-user-apps",
):
    text = (ROOTFS / rel).read_text()
    if expected_favorites not in text:
        raise AssertionError(f"V25 Dock list missing GRUBENVOLK in {rel}")
first_login = (ROOTFS / "usr/local/bin/limad-base1-first-login").read_text()
if "de.limad.Grubenvolk.desktop" not in first_login:
    raise AssertionError("V25 first-login Dock list missing GRUBENVOLK")
if "required-user-apps-v25.done" not in (ROOTFS / "usr/local/bin/limad-required-user-apps").read_text():
    raise AssertionError("V25 required-user-apps state marker missing")

print("V25 GRUBENVOLK TEST: PASS")
