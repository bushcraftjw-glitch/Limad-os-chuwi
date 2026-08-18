#!/usr/bin/python3
import hashlib
import pathlib
import subprocess
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
FW_ROOT = ROOT / "assets" / "firmware"
HELPER = ROOT / "build" / "prepare-imac17-initrd.sh"
EXPECTED = {
    "BONAIRE_ce.bin",
    "BONAIRE_mc.bin",
    "BONAIRE_mc2.bin",
    "BONAIRE_me.bin",
    "BONAIRE_mec.bin",
    "BONAIRE_pfp.bin",
    "BONAIRE_rlc.bin",
    "BONAIRE_sdma.bin",
    "BONAIRE_smc.bin",
    "BONAIRE_uvd.bin",
    "BONAIRE_vce.bin",
}

actual = {path.name for path in (FW_ROOT / "radeon").glob("BONAIRE_*.bin")}
if actual != EXPECTED:
    raise SystemExit(f"ERROR: Radeon Bonaire firmware set mismatch: {sorted(actual)}")

manifest = {}
for line in (FW_ROOT / "SHA256SUMS.txt").read_text(encoding="utf-8").splitlines():
    digest, rel = line.split(maxsplit=1)
    rel = rel.lstrip("*")
    manifest[rel] = digest

for name in sorted(EXPECTED):
    rel = f"radeon/{name}"
    path = FW_ROOT / rel
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    if manifest.get(rel) != digest:
        raise SystemExit(f"ERROR: firmware hash mismatch: {rel}")

license_digest = hashlib.sha256((FW_ROOT / "LICENSE.radeon").read_bytes()).hexdigest()
if manifest.get("LICENSE.radeon") != license_digest:
    raise SystemExit("ERROR: Radeon firmware license hash mismatch")

with tempfile.TemporaryDirectory() as temp:
    temp_path = pathlib.Path(temp)
    original = temp_path / "original.initrd"
    output = temp_path / "v20.initrd"
    sentinel = b"ORIGINAL_CANONICAL_INITRD_SENTINEL\n"
    original.write_bytes(sentinel)
    subprocess.run([str(HELPER), str(original), str(output)], check=True)
    data = output.read_bytes()
    if not data.endswith(sentinel):
        raise SystemExit("ERROR: original initrd was not preserved as trailing archive")
    for marker in (
        b"usr/lib/firmware/radeon/BONAIRE_uvd.bin",
        b"scripts/casper-bottom/62limad-branding",
        b"limad-installer/whitelabel.yaml",
        b"limad-installer/slides/1/slide_de_DE.html",
    ):
        if marker not in data:
            raise SystemExit(f"ERROR: initrd prefix missing {marker!r}")

print("IMAC17 FIRMWARE + INITRD TEST: PASS")
