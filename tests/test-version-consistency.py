#!/usr/bin/python3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VERSION = 'V18'
tag = 'base1-ubuntu2604-full-whitesur-v18'
iso = 'LiMaD-OS-3.0-RC1-BASE1-UBUNTU-26.04-FULL-WHITESUR-V18-amd64.iso'

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

# Semantic text files must not contain the previous release identifier.
for path in ROOT.rglob('*'):
    if not path.is_file() or '.cache' in path.parts:
        continue
    if path.suffix.lower() in {'.png', '.jpg', '.jpeg', '.zip', '.bin', '.svg'}:
        continue
    try:
        text = path.read_text()
    except UnicodeDecodeError:
        continue
    previous_upper = 'V' + '17'
    previous_lower = 'v' + '17'
    if previous_upper in text or previous_lower in text:
        raise AssertionError(f'stale previous-version identifier in {path.relative_to(ROOT)}')

print('VERSION CONSISTENCY TEST: PASS')
