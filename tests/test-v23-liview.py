#!/usr/bin/python3
import ast
import configparser
import json
import struct
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ROOTFS = ROOT / 'build/rootfs'
LIVIEW = ROOTFS / 'usr/share/liview'
DESKTOP = ROOTFS / 'usr/share/applications/de.limad.LiView.desktop'
PACKAGES = ROOT / 'config/liview-packages.txt'
MIMES = ROOT / 'config/liview-mime-types.txt'
MIME_XML = ROOTFS / 'usr/share/mime/packages/de.limad.LiView.xml'

required_files = [
    ROOTFS / 'usr/bin/liview',
    DESKTOP,
    ROOTFS / 'usr/share/metainfo/de.limad.LiView.metainfo.xml',
    MIME_XML,
    LIVIEW / 'VERSION',
    LIVIEW / 'dependencies.txt',
    LIVIEW / 'liview/__main__.py',
    LIVIEW / 'liview/app.py',
    LIVIEW / 'liview/documents.py',
    LIVIEW / 'liview/inspector.py',
    LIVIEW / 'liview/ocr.py',
    LIVIEW / 'liview/stl.py',
    LIVIEW / 'liview/video.py',
    LIVIEW / 'selftest/TEST-PDF.pdf',
    LIVIEW / 'selftest/TEST-FORMULAR.pdf',
    LIVIEW / 'selftest/TEST-BILD.png',
    LIVIEW / 'selftest/TEST-STL.stl',
    LIVIEW / 'selftest/TEST-VIDEO.mp4',
    ROOTFS / 'usr/local/bin/limad-install-offline-packages',
    ROOTFS / 'usr/local/bin/limad-liview-mime-defaults',
    ROOTFS / 'usr/local/bin/limad-liview-selftest',
    ROOT / 'tools/prepare-offline-packages.sh',
]
for path in required_files:
    if not path.is_file() or path.stat().st_size == 0:
        raise AssertionError(f'missing LiView V23 file: {path.relative_to(ROOT)}')

if (LIVIEW / 'VERSION').read_text().strip() != '1.0.0':
    raise AssertionError('LiView version is not 1.0.0')

for path in (LIVIEW / 'liview').glob('*.py'):
    ast.parse(path.read_text(encoding='utf-8'), filename=str(path))

config = configparser.ConfigParser(interpolation=None, strict=False)
config.optionxform = str
config.read(DESKTOP, encoding='utf-8')
entry = config['Desktop Entry']
if entry.get('Exec') != '/usr/bin/liview %F':
    raise AssertionError('LiView desktop Exec mismatch')
if entry.get('TryExec') != '/usr/bin/liview':
    raise AssertionError('LiView desktop TryExec mismatch')
if entry.get('Icon') != 'de.limad.LiView':
    raise AssertionError('LiView desktop icon mismatch')
if entry.get('StartupWMClass') != 'de.limad.LiView':
    raise AssertionError('LiView StartupWMClass mismatch')
if entry.get('X-LiMaD-Version') != '1.0.0':
    raise AssertionError('LiView desktop version mismatch')

declared_mimes = {item for item in entry.get('MimeType', '').split(';') if item}
expected_mimes = {line.strip() for line in MIMES.read_text().splitlines() if line.strip() and not line.lstrip().startswith('#')}
if declared_mimes != expected_mimes:
    missing = sorted(expected_mimes - declared_mimes)
    extra = sorted(declared_mimes - expected_mimes)
    raise AssertionError(f'LiView MIME mismatch: missing={missing} extra={extra}')

ET.parse(MIME_XML)
xml_text = MIME_XML.read_text(encoding='utf-8')
expected_extensions = {
    '.pdf', '.png', '.jpg', '.jpeg', '.webp', '.tif', '.tiff', '.bmp', '.gif', '.ico', '.avif', '.heic', '.heif', '.svg', '.svgz',
    '.stl', '.obj', '.3mf',
    '.mp4', '.m4v', '.mov', '.qt', '.mkv', '.mk3d', '.webm', '.avi', '.wmv', '.asf', '.flv', '.f4v', '.mpg', '.mpeg', '.mpe',
    '.m1v', '.m2v', '.m2p', '.m2t', '.ts', '.mts', '.m2ts', '.vob', '.ogv', '.ogm', '.3gp', '.3g2', '.rm', '.rmvb', '.divx',
    '.dv', '.mxf', '.nut', '.y4m', '.h264', '.264', '.h265', '.265', '.hevc', '.vp8', '.vp9', '.av1',
}
for extension in sorted(expected_extensions):
    if f'*{extension}' not in xml_text:
        raise AssertionError(f'LiView MIME glob missing: {extension}')

documents_ast = ast.parse((LIVIEW / 'liview/documents.py').read_text(encoding='utf-8'))
video_ast = ast.parse((LIVIEW / 'liview/video.py').read_text(encoding='utf-8'))
def literal_set_from_class(tree, class_name, variable):
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            for item in node.body:
                if isinstance(item, ast.Assign) and any(isinstance(t, ast.Name) and t.id == variable for t in item.targets):
                    return set(ast.literal_eval(item.value))
    raise AssertionError(f'cannot resolve {class_name}.{variable}')
image_extensions = literal_set_from_class(documents_ast, 'ImageDocument', 'pillow_extensions')
image_extensions |= literal_set_from_class(documents_ast, 'ImageDocument', 'heif_extensions')
image_extensions |= literal_set_from_class(documents_ast, 'ImageDocument', 'svg_extensions')
video_extensions = literal_set_from_class(video_ast, 'VideoDocument', 'supported_extensions')
code_extensions = {'.pdf', '.stl', '.obj', '.3mf'} | image_extensions | video_extensions
if code_extensions != expected_extensions:
    raise AssertionError(f'LiView code/MIME extension coverage differs: code-only={sorted(code_extensions-expected_extensions)} mime-only={sorted(expected_extensions-code_extensions)}')

package_set = {line.strip() for line in PACKAGES.read_text().splitlines() if line.strip() and not line.lstrip().startswith('#')}
dependency_set = {line.strip() for line in (LIVIEW / 'dependencies.txt').read_text().splitlines() if line.strip() and not line.lstrip().startswith('#')}
if package_set != dependency_set:
    raise AssertionError('LiView source and installed dependency lists differ')
for package in (
    'python3', 'python3-gi', 'python3-cairo', 'python3-pikepdf', 'python3-pil',
    'gir1.2-gtk-4.0', 'gir1.2-poppler-0.18', 'libgtk-4-1',
    'gstreamer1.0-gtk4', 'gstreamer1.0-libav', 'gstreamer1.0-plugins-base',
    'gstreamer1.0-plugins-good', 'gstreamer1.0-plugins-bad', 'gstreamer1.0-plugins-ugly',
    'libheif-examples', 'libheif-plugin-aomdec', 'libheif-plugin-libde265', 'librsvg2-bin',
    'tesseract-ocr', 'tesseract-ocr-deu', 'tesseract-ocr-eng', 'ffmpeg', 'ghostscript',
):
    if package not in package_set:
        raise AssertionError(f'critical LiView package missing: {package}')
if 'libgtk-4-media-gstreamer' in package_set:
    raise AssertionError('virtual/obsolete GTK media package must not be used')

prepare = (ROOT / 'tools/prepare-offline-packages.sh').read_text()
for token in (
    'resolute main restricted universe multiverse',
    'resolute-updates main restricted universe multiverse',
    'resolute-security main restricted universe multiverse',
    '--download-only', '--no-install-recommends', 'dpkg-scanpackages', 'SHA256SUMS.txt',
):
    if token not in prepare:
        raise AssertionError(f'offline repository builder missing token: {token}')

installer = (ROOTFS / 'usr/local/bin/limad-install-offline-packages').read_text()
for token in ('file:%s', '--no-download', 'SHA256SUMS.txt', 'DIRECT-PACKAGES.txt'):
    if token not in installer:
        raise AssertionError(f'offline installer missing token: {token}')

install_target = (ROOT / 'build/install-target.sh').read_text()
offline_pos = install_target.find('/usr/local/bin/limad-install-offline-packages')
mime_pos = install_target.find('/usr/local/bin/limad-liview-mime-defaults')
selftest_pos = install_target.find('/usr/local/bin/limad-liview-selftest')
if min(offline_pos, mime_pos, selftest_pos) < 0 or not (offline_pos < mime_pos < selftest_pos):
    raise AssertionError('LiView target install order is not offline packages -> MIME defaults -> selftest')

selftest = (ROOTFS / 'usr/local/bin/limad-liview-selftest').read_text()
for token in (
    'tesseract --list-langs', 'gst-inspect-1.0 avdec_h264', 'rsvg-convert', 'format="AVIF"',
    'PdfPasswordRequired', 'protect_copy', 'compress_copy', 'secure_redact', 'form_fields',
    'add_signature', 'StlDocument', 'VideoDocument',
):
    if token not in selftest:
        raise AssertionError(f'LiView selftest missing coverage: {token}')

mime_helper = (ROOTFS / 'usr/local/bin/limad-liview-mime-defaults').read_text()
for token in ('/etc/xdg/mimeapps.list', 'Default Applications', 'Added Associations'):
    if token not in mime_helper:
        raise AssertionError(f'MIME default helper missing token: {token}')

autoinstall = (ROOT / 'config/autoinstall.yaml').read_text()
if '/cdrom/limad/offline-packages/.' not in autoinstall:
    raise AssertionError('autoinstall does not copy offline dependency repository')
prepare_payload = (ROOT / 'build/prepare-payload.sh').read_text()
if 'prepare-offline-packages.sh' not in prepare_payload or 'liview-offline-repo/' not in prepare_payload:
    raise AssertionError('payload preparation does not embed LiView offline repository')
build_iso = (ROOT / 'build/build-iso.sh').read_text()
if 'payload/offline-packages/' not in build_iso or 'limad/offline-packages/' not in build_iso:
    raise AssertionError('ISO build does not overlay LiView offline repository')

for theme in ('LiMaD', 'hicolor'):
    for size in (64, 128, 256, 512):
        icon = ROOTFS / f'usr/share/icons/{theme}/{size}x{size}/apps/de.limad.LiView.png'
        data = icon.read_bytes()
        if data[:8] != b'\x89PNG\r\n\x1a\n':
            raise AssertionError(f'invalid LiView PNG: {icon.relative_to(ROOT)}')
        width, height = struct.unpack('>II', data[16:24])
        if (width, height) != (size, size):
            raise AssertionError(f'wrong LiView icon size: {icon.relative_to(ROOT)} => {(width, height)}')

apps = json.loads((ROOTFS / 'usr/share/limad-updater/apps.json').read_text(encoding='utf-8'))['apps']
liview_entries = [app for app in apps if app.get('app_id') == 'de.limad.LiView']
if len(liview_entries) != 1:
    raise AssertionError('LiView updater registration missing or duplicated')
entry = liview_entries[0]
if entry.get('launcher') != '/usr/bin/liview' or entry.get('system_version_file') != '/usr/share/liview/VERSION':
    raise AssertionError('LiView updater registration is invalid')

print('V23 LIVIEW OFFLINE + MIME + INTEGRATION TEST: PASS')
