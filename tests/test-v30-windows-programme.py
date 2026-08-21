#!/usr/bin/python3
from hashlib import sha256
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP_ROOT = ROOT / "build/rootfs/usr/share/limad-windows"
EXPECTED_HASHES = {
    "installer.py": "db18f329e71811994d03517d055347d3c9c9e7cc854dd7905c3caea574c02e2a",
    "recipe_engine.py": "7fc66a51125f6a97a91159c38a9c98af4143720ef095165902797488f0e9d494",
    "wine-env.sh": "20819c088c63ce47e692c02d953b8d1bd8330613c47481866c30a0d4ff23ca46",
}

if (APP_ROOT / "VERSION").read_text(encoding="utf-8").strip() != "2.2.8":
    raise AssertionError("Windows-Programme system version must be 2.2.8")

installer = (APP_ROOT / "installer.py").read_text(encoding="utf-8")
if 'APP_VERSION = "2.2.8"' not in installer:
    raise AssertionError("Windows-Programme installer must report 2.2.8")
if 'header.set_decoration_layout("close,maximize,minimize:")' not in installer:
    raise AssertionError("Windows-Programme must retain V29 titlebutton order")
if 'header.set_decoration_layout("close,minimize,maximize:")' in installer:
    raise AssertionError("Windows-Programme contains the old titlebutton order")

for name, expected in EXPECTED_HASHES.items():
    actual = sha256((APP_ROOT / name).read_bytes()).hexdigest()
    if actual != expected:
        raise AssertionError(f"Windows-Programme 2.2.8 payload hash mismatch: {name}")

print("V30 WINDOWS-PROGRAMME 2.2.8 TEST: PASS")
