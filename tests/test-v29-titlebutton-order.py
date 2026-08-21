#!/usr/bin/python3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXPECTED = 'close,maximize,minimize:'
OLD = 'close,minimize,maximize:'
FILES = [
    ROOT / 'build/rootfs/usr/local/bin/limad-desktop-core-system',
    ROOT / 'build/rootfs/usr/local/bin/limad-base1-first-login',
    ROOT / 'build/rootfs/usr/local/bin/limad-titlebuttons-ensure',
    ROOT / 'tools/patch-v22-titlebars.py',
]

for path in FILES:
    text = path.read_text()
    if EXPECTED not in text:
        raise AssertionError(f'{path.relative_to(ROOT)} missing {EXPECTED!r}')
    if OLD in text:
        raise AssertionError(f'{path.relative_to(ROOT)} still contains old layout {OLD!r}')

css = (ROOT / 'build/rootfs/usr/share/limad/gtk4/gtk.css').read_bytes()
if not css:
    raise AssertionError('GTK4 titlebutton CSS missing')

print('V29 TITLEBUTTON ORDER TEST: PASS')
