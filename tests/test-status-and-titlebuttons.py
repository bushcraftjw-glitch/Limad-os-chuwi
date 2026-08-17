#!/usr/bin/python3
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
css = (ROOT / 'build/rootfs/usr/share/limad/gtk4/gtk.css').read_text()
for token in (
    'windowcontrols button.close',
    'windowcontrols button.minimize',
    'windowcontrols button.maximize',
    '#ff5f57', '#febc2e', '#28c840',
):
    if token not in css:
        raise SystemExit(f'ERROR: GTK4 titlebutton token missing: {token}')

prepare = (ROOT / 'build/prepare-payload.sh').read_text()
if '--libadwaita' in prepare:
    raise SystemExit('ERROR: full WhiteSur libadwaita injection is still enabled')

for uuid, icon, command in (
    ('lilink@limad.local', 'lilink.svg', '/usr/local/bin/lilink'),
    ('lidrop@limad.local', 'lidrop.svg', '/usr/local/bin/limad-drop'),
):
    base = ROOT / 'build/rootfs/usr/share/gnome-shell/extensions' / uuid
    metadata = json.loads((base / 'metadata.json').read_text())
    if metadata.get('uuid') != uuid or '50' not in metadata.get('shell-version', []):
        raise SystemExit(f'ERROR: invalid GNOME 50 metadata for {uuid}')
    js = (base / 'extension.js').read_text()
    if 'Main.panel.addToStatusArea(this.uuid, this._indicator);' not in js:
        raise SystemExit(f'ERROR: status-area integration missing for {uuid}')
    if command not in js:
        raise SystemExit(f'ERROR: launcher command missing for {uuid}')
    if not (base / icon).is_file() or (base / icon).stat().st_size < 100:
        raise SystemExit(f'ERROR: icon missing for {uuid}')

first_login = (ROOT / 'build/rootfs/usr/local/bin/limad-base1-first-login').read_text()
for helper in ('limad-link-status-ensure', 'limad-lidrop-status-ensure'):
    if helper not in first_login:
        raise SystemExit(f'ERROR: first-login status helper missing: {helper}')

print('STATUS + TITLEBUTTON REGRESSION TEST: PASS')
