#!/usr/bin/python3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VERSION = 'V23'
TAG = 'base1-ubuntu2604-full-whitesur-v23'
ISO = 'LiMaD-OS-3.0-RC1-BASE1-UBUNTU-26.04-FULL-WHITESUR-V23-amd64.iso'

checks = [
    (ROOT / 'VERSION', VERSION),
    (ROOT / 'README-DE.md', VERSION),
    (ROOT / 'config/build.env', ISO),
    (ROOT / 'config/build.env', TAG),
    (ROOT / 'build/rootfs/etc/limad-release', TAG),
    (ROOT / 'tests/validate-source.sh', ISO),
    (ROOT / 'tests/validate-source.sh', TAG),
    (ROOT / 'tests/validate-payload.sh', TAG),
    (ROOT / 'tests/verify-built-iso.sh', TAG),
]
for path, needle in checks:
    text = path.read_text(encoding='utf-8')
    if needle not in text:
        raise AssertionError(f'{path.relative_to(ROOT)} missing {needle!r}')

for path in (
    ROOT / 'config/build.env',
    ROOT / 'build/rootfs/etc/limad-release',
    ROOT / 'build/install-target.sh',
    ROOT / 'build/prepare-payload.sh',
    ROOT / 'build/build-iso.sh',
):
    text = path.read_text(encoding='utf-8')
    if 'base1-ubuntu2604-full-whitesur-v22' in text or 'FULL-WHITESUR-V22-amd64.iso' in text:
        raise AssertionError(f'stale V22 release identifier in {path.relative_to(ROOT)}')

print('VERSION CONSISTENCY TEST: PASS')
