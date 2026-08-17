#!/usr/bin/python3
import pathlib
import struct

ROOT = pathlib.Path(__file__).resolve().parents[1]
for rel, size in [
    ("build/branding/limad-logo-192.png", (192, 192)),
    ("build/branding/limad-logo-256.png", (256, 256)),
]:
    path = ROOT / rel
    data = path.read_bytes()
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        raise SystemExit(f"ERROR: {rel} is not PNG")
    if struct.unpack(">II", data[16:24]) != size:
        raise SystemExit(f"ERROR: {rel} has wrong size")
print("DESIGN ASSET TEST: PASS")
