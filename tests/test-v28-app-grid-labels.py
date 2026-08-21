#!/usr/bin/python3
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXT = ROOT / 'build/rootfs/usr/share/gnome-shell/extensions/limad-appgrid-labels@limad.local'
FIRST_LOGIN = ROOT / 'build/rootfs/usr/local/bin/limad-base1-first-login'
VERIFY_ISO = ROOT / 'tests/verify-built-iso.sh'

metadata = json.loads((EXT / 'metadata.json').read_text())
if metadata.get('uuid') != 'limad-appgrid-labels@limad.local':
    raise AssertionError('unexpected extension UUID')
if metadata.get('shell-version') != ['50']:
    raise AssertionError('extension must be pinned to GNOME Shell 50')

extension = (EXT / 'extension.js').read_text()
for needle in (
    "Main.overview._overview?.controls?.appDisplay",
    "connect('view-loaded'",
    'getAllItems()',
    'item._expandTitleOnHover = false',
    'line_wrap: true',
    'Pango.WrapMode.WORD_CHAR',
    'Pango.EllipsizeMode.END',
    "add_style_class_name('limad-app-grid-two-line')",
):
    if needle not in extension:
        raise AssertionError(f'extension missing {needle!r}')

stylesheet = (EXT / 'stylesheet.css').read_text()
if '.limad-app-grid-two-line' not in stylesheet or 'max-height: 2.4em;' not in stylesheet:
    raise AssertionError('two-line label height limit missing')

for forbidden in (
    'rows_per_page',
    'columns_per_page',
    'fixed_icon_size',
    'page_padding',
    'row_spacing',
    'column_spacing',
    'dash-to-dock',
):
    if forbidden in extension or forbidden in stylesheet:
        raise AssertionError(f'unexpected app-grid geometry change: {forbidden}')

first_login = FIRST_LOGIN.read_text()
for needle in (
    'base1-ubuntu2604-full-whitesur-v28-appgrid.done',
    'enable_extension_reliably limad-appgrid-labels@limad.local',
    'LiMaD app grid labels V28: PASS',
):
    if needle not in first_login:
        raise AssertionError(f'first-login integration missing {needle!r}')

verify_iso = VERIFY_ISO.read_text()
for needle in (
    '/limad/rootfs/usr/share/gnome-shell/extensions/limad-appgrid-labels@limad.local/metadata.json',
    '/limad/rootfs/usr/share/gnome-shell/extensions/limad-appgrid-labels@limad.local/extension.js',
    '/limad/rootfs/usr/share/gnome-shell/extensions/limad-appgrid-labels@limad.local/stylesheet.css',
):
    if needle not in verify_iso:
        raise AssertionError(f'ISO validation missing {needle!r}')

print('V28 APP GRID LABELS TEST: PASS')
