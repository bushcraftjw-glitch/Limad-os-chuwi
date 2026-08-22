#!/usr/bin/python3
from __future__ import annotations

import hashlib
import json
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VENDOR = ROOT / 'build/vendor/anycubic'
PARTS = [
    VENDOR / 'anycubicslicernext_1.3.96_amd64.deb.part00',
    VENDOR / 'anycubicslicernext_1.3.96_amd64.deb.part01',
]
EXPECTED_SHA256 = '2c2883a9c624ab64e721a0211667852e0083d8794f7839c1d7932c9f712ed076'

for part in PARTS:
    assert part.is_file() and part.stat().st_size > 0, part

hasher = hashlib.sha256()
with tempfile.TemporaryDirectory() as tmp:
    deb = Path(tmp) / 'anycubicslicernext_1.3.96_amd64.deb'
    with deb.open('wb') as output:
        for part in PARTS:
            data = part.read_bytes()
            hasher.update(data)
            output.write(data)
    assert hasher.hexdigest() == EXPECTED_SHA256
    package = subprocess.check_output(['dpkg-deb', '-f', str(deb), 'Package'], text=True).strip()
    version = subprocess.check_output(['dpkg-deb', '-f', str(deb), 'Version'], text=True).strip()
    arch = subprocess.check_output(['dpkg-deb', '-f', str(deb), 'Architecture'], text=True).strip()
    assert (package, version, arch) == ('anycubicslicernext', '1.3.96', 'amd64')

versions = (ROOT / 'build/versions.env').read_text().splitlines()
assert 'ANYCUBIC_DEB_VERSION=1.3.96' in versions
assert 'ANYCUBIC_BUILD_VERSION=1.3.9.4' in versions
assert f'ANYCUBIC_SOURCE_SHA256={EXPECTED_SHA256}' in versions

for path in (
    ROOT / 'build/prepare-anycubic-payload.sh',
    ROOT / 'build/prepare-anycubic-offline-repo.sh',
    ROOT / 'build/rootfs/usr/local/bin/limad-anycubic-deps',
    ROOT / 'build/rootfs/usr/bin/anycubicslicernext',
    ROOT / 'build/rootfs/usr/share/applications/de.limad.AnycubicSlicerNext.desktop',
    ROOT / 'build/rootfs/usr/share/metainfo/de.limad.AnycubicSlicerNext.metainfo.xml',
    ROOT / 'build/rootfs/usr/share/icons/hicolor/64x64/apps/de.limad.AnycubicSlicerNext.png',
    ROOT / 'build/rootfs/usr/share/icons/hicolor/128x128/apps/de.limad.AnycubicSlicerNext.png',
    ROOT / 'build/rootfs/usr/share/icons/hicolor/256x256/apps/de.limad.AnycubicSlicerNext.png',
):
    assert path.is_file() and path.stat().st_size > 0, path

apps = json.loads((ROOT / 'build/rootfs/usr/share/limad-updater/apps.json').read_text())['apps']
entry = next(app for app in apps if app['app_id'] == 'de.limad.AnycubicSlicerNext')
assert entry['launcher'] == '/usr/bin/anycubicslicernext'
assert entry['system_root'] == '/usr/lib/limad/apps/anycubic-slicer-next'
assert entry['system_version'] == '1.3.96'
assert 'bin/AnycubicSlicerNext' in entry['required']
assert 'resources' in entry['required']

prepare_payload = (ROOT / 'build/prepare-payload.sh').read_text()
assert 'prepare-anycubic-payload.sh' in prepare_payload
assert 'prepare-anycubic-offline-repo.sh' in prepare_payload

preflight = (ROOT / 'build/preflight-target-install.sh').read_text()
assert 'run_stage Anycubic /usr/local/bin/limad-anycubic-deps' in preflight

install_target = (ROOT / 'build/install-target.sh').read_text()
assert '/usr/local/bin/limad-anycubic-deps' in install_target

verify_iso = (ROOT / 'tests/verify-built-iso.sh').read_text()
assert 'anycubic-package-version' in verify_iso
assert 'anycubic-Packages.gz' in verify_iso
assert '/usr/local/bin/limad-anycubic-deps' in verify_iso

launcher = (ROOT / 'build/rootfs/usr/bin/anycubicslicernext').read_text()
assert 'LD_LIBRARY_PATH=' in launcher
assert 'exec "$BINARY" "$@"' in launcher

print('V38 ANYCUBIC NATIVE PAYLOAD TEST: PASS')
