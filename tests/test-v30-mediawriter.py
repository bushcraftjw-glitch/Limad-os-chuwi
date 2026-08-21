#!/usr/bin/python3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
required_apps = (ROOT / "build/rootfs/usr/local/bin/limad-required-user-apps").read_text(encoding="utf-8")
core = (ROOT / "build/rootfs/usr/local/bin/limad-desktop-core-system").read_text(encoding="utf-8")
first_login = (ROOT / "build/rootfs/usr/local/bin/limad-base1-first-login").read_text(encoding="utf-8")

for token in (
    'MEDIAWRITER_ID="org.fedoraproject.MediaWriter"',
    'install_user_app "$MEDIAWRITER_ID"',
):
    if token not in required_apps:
        raise AssertionError(f"Fedora Media Writer provisioning token missing: {token}")

for path, text in (("desktop core", core), ("first login", first_login)):
    if "org.fedoraproject.MediaWriter" in text:
        raise AssertionError(f"Fedora Media Writer must not be pinned to the Dock via {path}")

print("V30 FEDORA MEDIA WRITER TEST: PASS")
