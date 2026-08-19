#!/usr/bin/python3
import ast
import configparser
import json
import struct
from pathlib import Path
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
ROOTFS = ROOT / 'build/rootfs'
APP_ROOT = ROOTFS / 'usr/share/liview'
DESKTOP = ROOTFS / 'usr/share/applications/de.limad.LiView.desktop'
MIMEAPPS = ROOTFS / 'etc/xdg/mimeapps.list'
UPDATER = ROOTFS / 'usr/share/limad-updater/apps.json'
PACKAGE_LIST = ROOT / 'build/liview-packages.txt'

assert (APP_ROOT / 'VERSION').read_text().strip() == '1.0.0'

for path in sorted((APP_ROOT / 'liview').glob('*.py')):
    ast.parse(path.read_text(), filename=str(path))

updater = json.loads(UPDATER.read_text())
apps = updater['apps']
matches = [app for app in apps if app.get('app_id') == 'de.limad.LiView']
assert len(matches) == 1, f'expected exactly one LiView updater entry, got {len(matches)}'
entry = matches[0]
assert entry['launcher'] == '/usr/local/bin/liview'
assert entry['system_root'] == '/usr/share/liview'
assert entry['system_version_file'] == '/usr/share/liview/VERSION'
assert set(entry['required']) >= {'liview/__main__.py', 'liview/app.py', 'liview/documents.py', 'liview/inspector.py', 'liview/ocr.py', 'liview/stl.py', 'liview/video.py', 'liview/style.css', 'VERSION'}

launcher = (ROOTFS / 'usr/local/bin/liview').read_text()
assert '/usr/local/libexec/limad-select-app-root' in launcher
assert 'de.limad.LiView/current/payload' in launcher
assert not (ROOTFS / 'usr/bin/liview').exists()

desktop_lines = DESKTOP.read_text().splitlines()
mime_line = next(line for line in desktop_lines if line.startswith('MimeType='))
desktop_mimes = [item for item in mime_line.removeprefix('MimeType=').split(';') if item]
assert 'application/pdf' in desktop_mimes
assert 'model/stl' in desktop_mimes
assert 'video/mp4' in desktop_mimes
assert 'video/x-liview-raw' in desktop_mimes
assert any(line == 'Exec=/usr/local/bin/liview %F' for line in desktop_lines)
assert any(line == 'Exec=/usr/local/bin/limad-updater --app de.limad.LiView' for line in desktop_lines)

cfg = configparser.ConfigParser(interpolation=None, strict=True)
cfg.read(MIMEAPPS)
defaults = cfg['Default Applications']
for mime in desktop_mimes:
    assert defaults.get(mime) == 'de.limad.LiView.desktop', f'missing LiView default for {mime}'

xml_path = ROOTFS / 'usr/share/mime/packages/de.limad.LiView.xml'
ET.parse(xml_path)
xml_text = xml_path.read_text()
for glob in ('*.h264', '*.h265', '*.hevc', '*.vp8', '*.vp9', '*.av1', '*.m1v', '*.m2v', '*.m2p', '*.nut', '*.y4m'):
    assert f'pattern="{glob}"' in xml_text

packages = [line.strip() for line in PACKAGE_LIST.read_text().splitlines() if line.strip() and not line.lstrip().startswith('#')]
assert len(packages) == len(set(packages)), 'duplicate LiView packages'
required_packages = {
    'python3', 'python3-gi', 'python3-gi-cairo', 'python3-cairo',
    'gir1.2-gtk-4.0', 'gir1.2-poppler-0.18', 'python3-pikepdf', 'python3-pil',
    'librsvg2-bin', 'libheif-examples', 'libgtk-4-1', 'gstreamer1.0-gtk4',
    'gstreamer1.0-tools', 'gstreamer1.0-plugins-base', 'gstreamer1.0-plugins-good',
    'gstreamer1.0-plugins-bad', 'gstreamer1.0-plugins-ugly', 'gstreamer1.0-libav',
    'tesseract-ocr', 'tesseract-ocr-deu', 'ffmpeg', 'ghostscript',
    'desktop-file-utils', 'shared-mime-info',
}
missing = required_packages - set(packages)
assert not missing, f'missing LiView packages: {sorted(missing)}'
assert (APP_ROOT / 'REQUIRED-PACKAGES.txt').read_text() == PACKAGE_LIST.read_text()

for theme in ('LiMaD', 'hicolor'):
    for size in (64, 128, 256, 512):
        icon = ROOTFS / f'usr/share/icons/{theme}/{size}x{size}/apps/de.limad.LiView.png'
        data = icon.read_bytes()
        assert data[:8] == b'\x89PNG\r\n\x1a\n'
        width, height = struct.unpack('>II', data[16:24])
        assert (width, height) == (size, size), f'wrong LiView icon size: {icon}: {width}x{height}'

prep = (ROOT / 'build/prepare-payload.sh').read_text()
assert 'prepare-liview-offline-repo.sh' in prep

repo_builder = (ROOT / 'build/prepare-liview-offline-repo.sh').read_text()
assert '< <(find' not in repo_builder, 'LiView repo builder must not use early-closing find process substitutions'
assert 'DEB_FILES=("$DESTINATION"/*.deb)' in repo_builder
assert 'SCAN_LOG="$(mktemp)"' in repo_builder
assert 'resolute-updates main restricted universe multiverse' in repo_builder
assert 'resolute-security main restricted universe multiverse' in repo_builder

deps = (ROOTFS / 'usr/local/bin/limad-liview-deps').read_text()
assert '/etc/apt/sources.list.d/limad-liview-offline.' in deps
assert 'LiView combined package resolution failed' in deps

installer = (ROOT / 'build/install-target.sh').read_text()
assert '/usr/local/bin/limad-liview-deps' in installer
assert '/usr/local/bin/limad-liview-deps || true' not in installer

print('V23 LIVIEW TEST: PASS')
