#!/usr/bin/python3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
preflight_path = ROOT / "build/preflight-target-install.sh"
container_path = ROOT / "build/preflight-target-container.sh"
preflight = preflight_path.read_text()
container = container_path.read_text()
build_iso = (ROOT / "build/build-iso.sh").read_text()
workflow = (ROOT / ".github/workflows/build-iso.yml").read_text()

for path in (preflight_path, container_path):
    if not path.is_file():
        raise AssertionError(f"target preflight script missing: {path.name}")

for needle in [
    'BASE_IMAGE="${LIMAD_PREFLIGHT_IMAGE:-ubuntu:26.04}"',
    'echo "TARGET PREFLIGHT: $stage PASS"',
    'run_dependency_stage LiView liview',
    'run_dependency_stage Gaming gaming',
    'run_dependency_stage GRUBENVOLK grubenvolk',
    'TARGET PREFLIGHT: full install-target PASS',
    '--network none',
    'docker cp "$PAYLOAD/install-target.sh"',
]:
    if needle not in preflight:
        raise AssertionError(f"target preflight missing required marker: {needle}")

for needle in [
    '/usr/local/bin/limad-liview-deps',
    '/usr/local/bin/limad-gaming-deps',
    '/usr/local/bin/limad-grubenvolk-deps',
    '/usr/bin/bash /tmp/limad-install-target.sh',
]:
    if needle not in container:
        raise AssertionError(f"target preflight container missing required execution path: {needle}")

prepare = build_iso.index('"$ROOT/build/prepare-payload.sh"')
validate = build_iso.index('"$ROOT/tests/validate-payload.sh"')
preflight_call = build_iso.index('"$ROOT/build/preflight-target-install.sh"')
xorriso = build_iso.index('xorriso \\\n    -indev "$ISO"')
if not prepare < validate < preflight_call < xorriso:
    raise AssertionError("target preflight must run after payload validation and before xorriso")

if 'for command in cpio curl dconf docker dpkg-scanpackages' not in workflow:
    raise AssertionError("workflow does not verify Docker before target preflight")
if 'docker info >/dev/null' not in workflow:
    raise AssertionError("workflow does not verify Docker daemon")
if 'python3 -B tests/test-v25-target-preflight.py' not in workflow:
    raise AssertionError("workflow does not run target preflight regression test")

print("V25 TARGET PREFLIGHT TEST: PASS")
