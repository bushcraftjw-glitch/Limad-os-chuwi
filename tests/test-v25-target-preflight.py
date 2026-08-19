#!/usr/bin/python3
from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
state_path = ROOT / "build/prepare-ubuntu-target-state.sh"
preflight_path = ROOT / "build/preflight-target-install.sh"
stack_tool = ROOT / "tools/install-source-stack.py"
build_iso = (ROOT / "build/build-iso.sh").read_text()
workflow = (ROOT / ".github/workflows/build-iso.yml").read_text()
state = state_path.read_text()
preflight = preflight_path.read_text()

for path in (state_path, preflight_path, stack_tool):
    if not path.is_file():
        raise AssertionError(f"target preflight component missing: {path.name}")

if (ROOT / "build/preflight-target-container.sh").exists():
    raise AssertionError("obsolete Docker target preflight helper remains")

for needle in [
    "/casper/install-sources.yaml",
    'tools/install-source-stack.py',
    'sudo mount -t squashfs -o loop,ro',
    'sudo mount -t overlay overlay',
    'var/lib/dpkg/status',
    'Ubuntu desktop target state: PASS',
]:
    if needle not in state:
        raise AssertionError(f"Ubuntu target-state preparation missing marker: {needle}")

for needle in [
    'sudo cp -a "$PAYLOAD/rootfs/." "$TARGET/"',
    'sudo chroot "$TARGET"',
    'run_stage LiView /usr/local/bin/limad-liview-deps',
    'run_stage Gaming /usr/local/bin/limad-gaming-deps',
    'run_stage GRUBENVOLK /usr/local/bin/limad-grubenvolk-deps',
    "run_stage full-install-target '/usr/bin/bash /tmp/limad-install-target.sh'",
    '/usr/bin/apt-get check',
    'TARGET PREFLIGHT: PASS',
]:
    if needle not in preflight:
        raise AssertionError(f"real target preflight missing marker: {needle}")

if "docker " in preflight or "ubuntu:26.04" in preflight:
    raise AssertionError("target preflight still uses a generic Docker image")

for repo_script in [
    ROOT / "build/prepare-liview-offline-repo.sh",
    ROOT / "build/prepare-gaming-offline-repo.sh",
    ROOT / "build/prepare-grubenvolk-offline-repo.sh",
]:
    text = repo_script.read_text()
    if 'ubuntu-target-state/dpkg-status' not in text:
        raise AssertionError(f"{repo_script.name} does not resolve against Ubuntu desktop target state")
    if ': > "$APT_ROOT/var/lib/dpkg/status"' in text:
        raise AssertionError(f"{repo_script.name} still resolves against an empty dpkg status")
    if 'install -m 0644 "$TARGET_STATUS" "$APT_ROOT/var/lib/dpkg/status"' not in text:
        raise AssertionError(f"{repo_script.name} does not install the target dpkg status into the APT sandbox")
    if 'target_package_installed()' not in text:
        raise AssertionError(f"{repo_script.name} does not accept packages already present in the Ubuntu target")
    if 'offline repository contains no DEB packages' in text:
        raise AssertionError(f"{repo_script.name} still rejects a target that already contains all requested packages")
    if 'CHECKSUM_FILES=(./*.deb Packages Packages.gz REQUESTED-PACKAGES.txt)' not in text:
        raise AssertionError(f"{repo_script.name} does not support an empty but valid offline repository")

prepare_state = build_iso.index('"$ROOT/build/prepare-ubuntu-target-state.sh" "$ISO"')
prepare_payload = build_iso.index('"$ROOT/build/prepare-payload.sh"')
validate_payload = build_iso.index('"$ROOT/tests/validate-payload.sh"')
preflight_call = build_iso.index('"$ROOT/build/preflight-target-install.sh"')
xorriso = build_iso.index('xorriso \\\n    -indev "$ISO"')
if not prepare_state < prepare_payload < validate_payload < preflight_call < xorriso:
    raise AssertionError("target state and real target preflight are not ordered before ISO generation")

if "docker info >/dev/null" in workflow:
    raise AssertionError("workflow still requires Docker for target preflight")
if "mount mountpoint" not in workflow:
    raise AssertionError("workflow does not verify mount helpers for real target preflight")
if "python3 -B tests/test-v25-target-preflight.py" not in workflow:
    raise AssertionError("workflow does not run target preflight regression test")

catalog = {
    "version": 1,
    "kernel": {"default": "linux-generic"},
    "sources": [
        {
            "id": "ubuntu-desktop",
            "variant": "desktop",
            "name": {"en": "Ubuntu Desktop"},
            "description": {"en": "Desktop"},
            "path": "minimal.standard.live.ubuntu-desktop.squashfs",
            "size": 1,
            "type": "fsimage-layered",
            "default": True,
        }
    ],
}
with tempfile.TemporaryDirectory() as directory:
    path = Path(directory) / "install-sources.yaml"
    path.write_text(yaml.safe_dump(catalog), encoding="utf-8")
    result = subprocess.run(
        ["python3", "-B", str(stack_tool), str(path), "--source-id", "ubuntu-desktop"],
        check=True,
        capture_output=True,
        text=True,
    )

expected = [
    "minimal.squashfs",
    "minimal.standard.squashfs",
    "minimal.standard.live.squashfs",
    "minimal.standard.live.ubuntu-desktop.squashfs",
]
if result.stdout.splitlines() != expected:
    raise AssertionError(f"layered source stack mismatch: {result.stdout.splitlines()!r}")

print("V25 REAL TARGET PREFLIGHT TEST: PASS")
