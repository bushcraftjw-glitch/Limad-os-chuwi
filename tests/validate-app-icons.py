#!/usr/bin/python3
import configparser
import pathlib
import struct
import tempfile
import zipfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
PROGRAM_ZIP = ROOT / '.cache/vendor/LiMaD-Programme-BASE1B-EXTRAKT.zip'
ICON_ZIP = ROOT / '.cache/vendor/LiMaD-OS-MASTER-ICON-THEME-V3.2-BUILD-READY.zip'
REQUIRED_SIZES = (64, 128, 256)


def png_size(path: pathlib.Path) -> tuple[int, int]:
    data = path.read_bytes()
    if data[:8] != b'\x89PNG\r\n\x1a\n':
        raise ValueError(f'not PNG: {path}')
    return struct.unpack('>II', data[16:24])


with tempfile.TemporaryDirectory() as temp:
    temp_path = pathlib.Path(temp)
    with zipfile.ZipFile(PROGRAM_ZIP) as archive:
        archive.extractall(temp_path / 'programs')
    with zipfile.ZipFile(ICON_ZIP) as archive:
        archive.extractall(temp_path / 'icons')

    applications = next((temp_path / 'programs').glob('*/filesystem/usr/share/applications'))
    icon_root = next((temp_path / 'icons').glob('*/assets/system_files/usr/share/icons/LiMaD'))

    missing = []
    checked = []
    for desktop in sorted(applications.glob('de.limad.*.desktop')):
        parser = configparser.ConfigParser(interpolation=None, strict=False)
        parser.optionxform = str
        parser.read(desktop, encoding='utf-8')
        icon = parser.get('Desktop Entry', 'Icon', fallback='').strip()
        if not icon or icon.startswith('/'):
            continue
        checked.append((desktop.name, icon))
        for size in REQUIRED_SIZES:
            path = icon_root / f'{size}x{size}' / 'apps' / f'{icon}.png'
            if not path.is_file():
                missing.append((desktop.name, icon, size, 'missing'))
                continue
            try:
                dimensions = png_size(path)
            except ValueError:
                missing.append((desktop.name, icon, size, 'invalid-png'))
                continue
            if dimensions != (size, size):
                missing.append((desktop.name, icon, size, f'wrong-size:{dimensions}'))

    if missing:
        raise SystemExit(f'ERROR: invalid or missing LiMaD launcher icons: {missing}')
    if len(checked) != 17:
        raise SystemExit(f'ERROR: expected 17 LiMaD launchers, checked {len(checked)}')

print(f'APP ICON VALIDATION: PASS ({len(checked)} launchers, sizes 64/128/256)')
