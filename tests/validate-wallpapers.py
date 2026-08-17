#!/usr/bin/python3
import pathlib
import struct
import sys
import zipfile

if len(sys.argv) != 2:
    raise SystemExit("usage: validate-wallpapers.py ZIP")

expected = {
    "LiMaD-Wallpaper-01-Logo-Links-4K.png",
    "LiMaD-Wallpaper-02-Logo-Zentriert-4K.png",
    "LiMaD-Wallpaper-03-Wellen-Emblem-4K.png",
}

with zipfile.ZipFile(pathlib.Path(sys.argv[1])) as archive:
    names = {name for name in archive.namelist() if not name.endswith("/")}
    if names != expected:
        raise SystemExit(f"ERROR: unexpected wallpaper set: {sorted(names)}")
    for name in sorted(expected):
        data = archive.read(name)
        if data[:8] != b"\x89PNG\r\n\x1a\n":
            raise SystemExit(f"ERROR: {name} is not PNG")
        width, height = struct.unpack(">II", data[16:24])
        if (width, height) != (3840, 2160):
            raise SystemExit(f"ERROR: {name} is {width}x{height}, expected 3840x2160")

print("WALLPAPER VALIDATION: PASS")
