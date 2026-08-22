#!/usr/bin/python3
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

SHELL_FILES: list[Path] = []
for path in ROOT.rglob('*'):
    if not path.is_file():
        continue
    rel = path.relative_to(ROOT)
    if '.cache' in rel.parts:
        continue
    if path.suffix == '.sh' or path.name == 'START-RC1-GITHUB-BUILD-LINUX.sh':
        SHELL_FILES.append(path)
        continue
    if rel.parts[:2] == ('build', 'casper-bottom'):
        SHELL_FILES.append(path)
        continue
    if rel.parts[:5] == ('build', 'rootfs', 'usr', 'local', 'bin') and (path.name.startswith('limad-') or path.name == 'liview'):
        SHELL_FILES.append(path)
        continue
    if rel == Path('build/rootfs/usr/bin/anycubicslicernext'):
        SHELL_FILES.append(path)

# A single-quoted fixed-string grep containing a shell expansion is the exact
# pattern that repeatedly triggered SC2016 in our validation scripts.
sc2016_grep = re.compile(r"\bgrep\b[^\n]*-Fq[^\n]*'[^']*\$\{?[A-Za-z_][A-Za-z0-9_]*(?::[^}]*)?\}?[^']*'")

# The project intentionally avoids A && B || C as pseudo if/else because this
# repeatedly triggered SC2015 and can execute C when B fails.
sc2015_chain = re.compile(r'&&[^#\n]*\|\|')

problems: list[str] = []
for path in SHELL_FILES:
    for lineno, line in enumerate(path.read_text(errors='strict').splitlines(), 1):
        stripped = line.strip()
        if not stripped or stripped.startswith('#'):
            continue
        if sc2016_grep.search(line):
            problems.append(f'{path.relative_to(ROOT)}:{lineno}: SC2016-prone single-quoted grep literal')
        if sc2015_chain.search(line):
            problems.append(f'{path.relative_to(ROOT)}:{lineno}: SC2015-prone A && B || C chain')

# Protect the GTK4 user configuration against destructive older patterns.
sync = (ROOT / 'build/rootfs/usr/local/bin/limad-sync-gtk4-theme').read_text()
for forbidden in (
    'rm -rf -- "${DEST:?}/assets"',
    'rm -rf "$HOME/.config/gtk-4.0"',
    'rm -rf "${HOME:?}/.config/gtk-4.0"',
):
    if forbidden in sync:
        problems.append(f'limad-sync-gtk4-theme: destructive pattern present: {forbidden}')

if problems:
    raise AssertionError('\n'.join(problems))

print(f'SHELL REGRESSION TEST: PASS ({len(SHELL_FILES)} shell targets)')
