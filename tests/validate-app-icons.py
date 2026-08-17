#!/usr/bin/python3
import configparser
import pathlib
import tempfile
import zipfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
PROGRAM_ZIP = ROOT / ".cache/vendor/LiMaD-Programme-BASE1B-EXTRAKT.zip"
ICON_ZIP = ROOT / ".cache/vendor/LiMaD-OS-MASTER-ICON-THEME-V3.2-BUILD-READY.zip"

with tempfile.TemporaryDirectory() as temp:
    temp_path = pathlib.Path(temp)
    with zipfile.ZipFile(PROGRAM_ZIP) as archive:
        archive.extractall(temp_path / "programs")
    with zipfile.ZipFile(ICON_ZIP) as archive:
        archive.extractall(temp_path / "icons")

    applications = next((temp_path / "programs").glob("*/filesystem/usr/share/applications"))
    icon_root = next((temp_path / "icons").glob("*/assets/system_files/usr/share/icons/LiMaD"))
    icon_names = {path.stem for path in icon_root.rglob("*") if path.is_file()}

    missing = []
    checked = []
    for desktop in sorted(applications.glob("de.limad.*.desktop")):
        parser = configparser.ConfigParser(interpolation=None, strict=False)
        parser.optionxform = str
        parser.read(desktop, encoding="utf-8")
        icon = parser.get("Desktop Entry", "Icon", fallback="").strip()
        if icon.startswith("de.limad.") or icon.startswith("limad-"):
            checked.append((desktop.name, icon))
            if icon not in icon_names:
                missing.append((desktop.name, icon))

    if missing:
        raise SystemExit(f"ERROR: missing LiMaD icons: {missing}")
    if not checked:
        raise SystemExit("ERROR: no LiMaD application icons were checked")

print(f"APP ICON VALIDATION: PASS ({len(checked)} launchers)")
