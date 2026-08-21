#!/usr/bin/python3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VERSION = 'V32'
tag = 'base1-ubuntu2604-full-whitesur-v32'
iso = 'LiMaD-OS-3.0-RC1-BASE1-UBUNTU-26.04-FULL-WHITESUR-V32-amd64.iso'

pairs = [
    (ROOT / 'VERSION', VERSION),
    (ROOT / 'README-DE.md', VERSION),
    (ROOT / 'config/build.env', iso),
    (ROOT / 'config/build.env', tag),
    (ROOT / 'build/rootfs/etc/limad-release', tag),
    (ROOT / 'tests/validate-source.sh', iso),
    (ROOT / 'tests/validate-source.sh', tag),
    (ROOT / 'tests/validate-payload.sh', tag),
    (ROOT / 'tests/verify-built-iso.sh', tag),
]
for path, needle in pairs:
    text = path.read_text()
    if needle not in text:
        raise AssertionError(f'{path.relative_to(ROOT)} missing {needle!r}')

release_files = [
    ROOT / 'VERSION',
    ROOT / 'config/build.env',
    ROOT / 'build/rootfs/etc/limad-release',
]
for path in release_files:
    text = path.read_text()
    if any(marker in text for marker in ('base1-ubuntu2604-full-whitesur-v23', 'WHITESUR-V23-amd64.iso', 'base1-ubuntu2604-full-whitesur-v24', 'WHITESUR-V24-amd64.iso', 'base1-ubuntu2604-full-whitesur-v26', 'WHITESUR-V26-amd64.iso', 'base1-ubuntu2604-full-whitesur-v27', 'WHITESUR-V27-amd64.iso', 'base1-ubuntu2604-full-whitesur-v28', 'WHITESUR-V28-amd64.iso', 'base1-ubuntu2604-full-whitesur-v29', 'WHITESUR-V29-amd64.iso', 'base1-ubuntu2604-full-whitesur-v30', 'WHITESUR-V30-amd64.iso', 'base1-ubuntu2604-full-whitesur-v31', 'WHITESUR-V31-amd64.iso')):
        raise AssertionError(f'stale release marker in {path.relative_to(ROOT)}')

print('VERSION CONSISTENCY TEST: PASS')
