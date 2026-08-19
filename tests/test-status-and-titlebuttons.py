#!/usr/bin/python3
import json
import pathlib
import re
import subprocess
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
GTK4 = ROOT / 'build/rootfs/usr/share/limad/gtk4'
css = (GTK4 / 'gtk.css').read_text(encoding='utf-8')
for token in (
    'windowcontrols button.close',
    'windowcontrols button.minimize',
    'windowcontrols button.maximize',
    'url("limad-assets/close.svg")',
    'url("limad-assets/minimize.svg")',
    'url("limad-assets/maximize.svg")',
    'background-size: 12px 12px',
):
    if token not in css:
        raise SystemExit(f'ERROR: GTK4 titlebutton token missing: {token}')

for forbidden in ('padding:', 'margin:', 'border:', 'box-shadow:', 'background-color:'):
    if forbidden in css:
        raise SystemExit(f'ERROR: GTK4 titlebutton override changes native geometry/style: {forbidden}')
sync = (ROOT / 'build/rootfs/usr/local/bin/limad-sync-gtk4-theme').read_text(encoding='utf-8')
if 'rm -rf -- "${DEST:?}/assets"' in sync or '"$DEST/gtk.css"' in sync and 'rm -rf' in sync:
    raise SystemExit('ERROR: GTK4 sync still deletes user GTK4 configuration')
for token in ('limad-titlebuttons.css', '@import url("limad-titlebuttons.css");'):
    if token not in sync:
        raise SystemExit(f'ERROR: non-destructive GTK4 import missing: {token}')

for asset in ('close.svg', 'minimize.svg', 'maximize.svg'):
    path = GTK4 / 'limad-assets' / asset
    if not path.is_file() or path.stat().st_size < 100:
        raise SystemExit(f'ERROR: GTK4 traffic-light asset missing: {asset}')

prepare = (ROOT / 'build/prepare-payload.sh').read_text(encoding='utf-8')
if '--libadwaita' in prepare:
    raise SystemExit('ERROR: full WhiteSur libadwaita injection is still enabled')
if 'HICOLOR_ROOT="$PAYLOAD/rootfs/usr/share/icons/hicolor"' not in prepare:
    raise SystemExit('ERROR: hicolor LiMaD icon fallback is missing')

for uuid, icon, command in (
    ('lilink@limad.local', 'lilink.svg', '/usr/local/bin/lilink'),
    ('lidrop@limad.local', 'lidrop.svg', '/usr/local/bin/limad-drop'),
):
    base = ROOT / 'build/rootfs/usr/share/gnome-shell/extensions' / uuid
    metadata = json.loads((base / 'metadata.json').read_text(encoding='utf-8'))
    if metadata.get('uuid') != uuid or '50' not in metadata.get('shell-version', []):
        raise SystemExit(f'ERROR: invalid GNOME 50 metadata for {uuid}')
    js = (base / 'extension.js').read_text(encoding='utf-8')
    if 'Main.panel.addToStatusArea(this.uuid, this._indicator);' not in js:
        raise SystemExit(f'ERROR: status-area integration missing for {uuid}')
    if command not in js:
        raise SystemExit(f'ERROR: launcher command missing for {uuid}')
    if not (base / icon).is_file() or (base / icon).stat().st_size < 100:
        raise SystemExit(f'ERROR: icon missing for {uuid}')

menu = ROOT / 'build/rootfs/usr/share/gnome-shell/extensions/limad-menu@limad.local'
metadata = json.loads((menu / 'metadata.json').read_text(encoding='utf-8'))
if metadata.get('uuid') != 'limad-menu@limad.local' or '50' not in metadata.get('shell-version', []):
    raise SystemExit('ERROR: invalid GNOME 50 metadata for LiMaD menu')
menu_js = (menu / 'extension.js').read_text(encoding='utf-8')
for token in (
    "Main.panel.addToStatusArea(this.uuid, this._indicator, 0, 'left');",
    'this._activities?.hide();',
    "'Über LiMaD OS'",
    "'Einstellungen'",
    "'Neustart'",
    "'Ausschalten'",
):
    if token not in menu_js:
        raise SystemExit(f'ERROR: LiMaD menu token missing: {token}')

first_login = (ROOT / 'build/rootfs/usr/local/bin/limad-base1-first-login').read_text(encoding='utf-8')
for token in (
    'CORE_MARKER=', 'AUX_MARKER=', 'sleep 3',
    "dock-position \"'BOTTOM'\"", 'extend-height false',
    "icon-theme \"'LiMaD'\"", 'enable_extension_reliably limad-menu@limad.local',
    'always-center-icons true', 'show-apps-always-in-the-edge false', 'verify_favorites',
):
    if token not in first_login:
        raise SystemExit(f'ERROR: first-login core token missing: {token}')
if 'LiLink status extension could not be enabled' in first_login:
    raise SystemExit('ERROR: old coupled LiLink/core failure path remains')

system = (ROOT / 'build/rootfs/usr/local/bin/limad-desktop-core-system').read_text(encoding='utf-8')
match = re.search(r"cat > /etc/dconf/db/local\.d/10-limad-desktop <<'EOF'\n(.*?)\nEOF", system, re.S)
if not match:
    raise SystemExit('ERROR: LiMaD dconf defaults block missing')
keyfile = match.group(1)
for token in (
    "icon-theme='LiMaD'", "gtk-theme='WhiteSur-Dark'",
    "button-layout='close,minimize,maximize:'", "dock-position='BOTTOM'",
    'extend-height=false', 'dash-max-icon-size=60',
    "[org/gnome/shell]", "favorite-apps=['app.zen_browser.zen.desktop'",
    "'de.limad.Mail.desktop'", "'de.limad.Cut.desktop'",
    "'de.limad.Study.desktop'", "'de.limad.Drop.desktop'",
    "'de.limad.Link.desktop'", "'de.limad.Welcome.desktop'",
):
    if token not in keyfile:
        raise SystemExit(f'ERROR: dconf default missing: {token}')
with tempfile.TemporaryDirectory() as tmp:
    keydir = pathlib.Path(tmp) / 'local.d'
    keydir.mkdir()
    (keydir / '10-limad-desktop').write_text(keyfile + '\n', encoding='utf-8')
    subprocess.run(['dconf', 'compile', str(pathlib.Path(tmp) / 'local'), str(keydir)], check=True)

print('STATUS + TITLEBUTTON + DESKTOP CORE TEST: PASS')
