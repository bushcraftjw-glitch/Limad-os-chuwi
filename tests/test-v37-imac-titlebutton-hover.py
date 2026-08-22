#!/usr/bin/python3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INSTALL = (ROOT / "build/install-target.sh").read_text(encoding="utf-8")
CSS = (ROOT / "build/rootfs/usr/share/limad/gtk4/gtk.css").read_text(encoding="utf-8")
ASSETS = ROOT / "build/rootfs/usr/share/limad/gtk4/limad-assets"
FIRST_LOGIN = (ROOT / "build/rootfs/usr/local/bin/limad-base1-first-login").read_text(encoding="utf-8")
PAYLOAD_VALIDATOR = (ROOT / "tests/validate-payload.sh").read_text(encoding="utf-8")

for token in (
    '0x1002', '0x6640', '0x106b', '0x014b',
    'options radeon cik_support=0',
    'options amdgpu cik_support=1 dc=0',
):
    if token not in INSTALL:
        raise AssertionError(f"V37 iMac R9 M380 target token missing: {token}")

if 'favorite-apps' in FIRST_LOGIN:
    raise AssertionError("V37 first-login must not touch user Dock favorites")
if "de.limad.Grubenvolk.desktop' \"$ROOTFS/usr/local/bin/limad-base1-first-login\"" in PAYLOAD_VALIDATOR:
    raise AssertionError("V37 payload validator still expects GRUBENVOLK in first-login")

for name, symbol in (
    ('close-hover.svg', 'M5.4 5.4L10.6 10.6'),
    ('minimize-hover.svg', 'M4.8 8H11.2'),
    ('maximize-hover.svg', 'M5 8V5H8M11 8V11H8'),
):
    path = ASSETS / name
    if not path.is_file() or path.stat().st_size < 150:
        raise AssertionError(f"V37 hover asset missing: {name}")
    if symbol not in path.read_text(encoding="utf-8"):
        raise AssertionError(f"V37 hover symbol missing in {name}")

for token in (
    'windowcontrols:hover button.close',
    'url("limad-assets/close-hover.svg")',
    'url("limad-assets/minimize-hover.svg")',
    'url("limad-assets/maximize-hover.svg")',
):
    if token not in CSS:
        raise AssertionError(f"V37 GTK4 hover rule missing: {token}")

for invariant in ('border-spacing: 6px;', 'min-width: 16px;', 'min-height: 16px;', 'background-size: 16px 16px;'):
    if invariant not in CSS:
        raise AssertionError(f"V37 changed titlebutton geometry invariant: {invariant}")

print("V37 IMAC + TITLEBUTTON HOVER TEST: PASS")
