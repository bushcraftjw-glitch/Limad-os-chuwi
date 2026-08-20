#!/usr/bin/python3
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUILDER = ROOT / "build/prepare-heroic-offline-repo.sh"
DEPS = ROOT / "build/rootfs/usr/local/bin/limad-heroic-deps"
PAYLOAD = ROOT / "build/prepare-payload.sh"
INSTALLER = ROOT / "build/install-target.sh"
PREFLIGHT = ROOT / "build/preflight-target-install.sh"
WORKFLOW = ROOT / ".github/workflows/build-iso.yml"

for path in (BUILDER, DEPS, PAYLOAD, INSTALLER, PREFLIGHT):
    if not path.is_file() or path.stat().st_size == 0:
        raise AssertionError(f"Heroic integration file missing: {path.relative_to(ROOT)}")

builder = BUILDER.read_text(encoding="utf-8")
for needle in (
    'HEROIC_VERSION="2.22.0"',
    'Heroic-${HEROIC_VERSION}-linux-amd64.deb',
    'https://github.com/Heroic-Games-Launcher/HeroicGamesLauncher/releases/download/v${HEROIC_VERSION}/${HEROIC_DEB}',
    'HEROIC_SHA256="4c8585ad7c7a76bd3c8058aa995b9064f457603f3b6afbd9114433cf4af7ecd2"',
    'ubuntu-target-state/dpkg-status',
    'install -m 0644 "$TARGET_STATUS" "$APT_ROOT/var/lib/dpkg/status"',
    '--download-only',
    '--no-install-recommends',
    'PACKAGE-NAME.txt',
    'PACKAGE-VERSION.txt',
    'dpkg-scanpackages --multiversion',
    'sha256sum -c SHA256SUMS.txt',
):
    if needle not in builder:
        raise AssertionError(f"Heroic offline builder missing: {needle}")

if ': > "$APT_ROOT/var/lib/dpkg/status"' in builder:
    raise AssertionError("Heroic dependency resolution uses an empty target dpkg status")

deps = DEPS.read_text(encoding="utf-8")
for needle in (
    'OFFLINE_REPO="/usr/share/limad/offline/heroic"',
    'sha256sum -c SHA256SUMS.txt',
    'Dir::Etc::sourcelist=$TEMP_SOURCE',
    'install "$package_name"',
    "dpkg-query -W -f='${Version}'",
    'Heroic Games Launcher: PASS',
):
    if needle not in deps:
        raise AssertionError(f"Heroic target helper missing: {needle}")

payload = PAYLOAD.read_text(encoding="utf-8")
if 'prepare-heroic-offline-repo.sh" "$PAYLOAD/rootfs/usr/share/limad/offline/heroic"' not in payload:
    raise AssertionError("Heroic offline repository is not embedded into the payload")

installer = INSTALLER.read_text(encoding="utf-8")
if "/usr/local/bin/limad-heroic-deps" not in installer:
    raise AssertionError("Heroic target helper is not called during installation")
for line in installer.splitlines():
    if "/usr/local/bin/limad-heroic-deps" in line and "|| true" in line:
        raise AssertionError("Heroic installation must be install-critical")

preflight = PREFLIGHT.read_text(encoding="utf-8")
if "run_stage Heroic /usr/local/bin/limad-heroic-deps" not in preflight:
    raise AssertionError("real target preflight does not validate Heroic")

workflow = WORKFLOW.read_text(encoding="utf-8")
if "python3 -B tests/test-v26-heroic.py" not in workflow:
    raise AssertionError("GitHub build workflow does not run the V26 Heroic regression test")
if "build/rootfs/usr/local/bin/limad-heroic-deps" not in workflow:
    raise AssertionError("GitHub build workflow does not ShellCheck the Heroic target helper")

print("V26 HEROIC TEST: PASS")
