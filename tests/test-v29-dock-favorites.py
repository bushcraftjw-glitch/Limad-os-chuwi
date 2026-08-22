#!/usr/bin/python3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CORE = (ROOT / 'build/rootfs/usr/local/bin/limad-desktop-core-system').read_text()
FIRST_LOGIN = (ROOT / 'build/rootfs/usr/local/bin/limad-base1-first-login').read_text()
USER_APPS = (ROOT / 'build/rootfs/usr/local/bin/limad-required-user-apps').read_text()

if 'icon-size-fixed=true' not in CORE:
    raise AssertionError('desktop core must keep fixed-size Dock scrolling enabled')
if 'set_key org.gnome.shell.extensions.dash-to-dock icon-size-fixed true' not in FIRST_LOGIN:
    raise AssertionError('first-login must keep fixed-size Dock scrolling enabled')
if 'favorite-apps' in FIRST_LOGIN:
    raise AssertionError('first-login must never write or validate the user Dock favorites')
if 'CURRENT_FAVORITES="$(gsettings get org.gnome.shell favorite-apps' not in USER_APPS:
    raise AssertionError('required-user-apps must read the existing favorites before changing them')
if 'UPDATED_FAVORITES+="' not in USER_APPS or "'$ZEN_DESKTOP']" not in USER_APPS:
    raise AssertionError('required-user-apps must append Zen without replacing existing favorites')
hard_reset = "gsettings set org.gnome.shell favorite-apps \\\n        \"['app.zen_browser.zen.desktop', 'de.limad.Mail.desktop'"
if hard_reset in USER_APPS:
    raise AssertionError('required-user-apps still hard-resets the complete favorites list')

print('V29 DOCK FAVORITES TEST: PASS')
