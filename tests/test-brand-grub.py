#!/usr/bin/python3
import pathlib
import subprocess
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "brand-grub.py"

sample = '''set timeout=30\nmenuentry "Try or Install Ubuntu" --class ubuntu {\n    linux /casper/vmlinuz quiet splash ---\n    initrd /casper/initrd\n}\nmenuentry 'Ubuntu (safe graphics)' --class ubuntu {\n    linux /casper/vmlinuz nomodeset ---\n}\n'''

with tempfile.TemporaryDirectory() as temp:
    temp = pathlib.Path(temp)
    src = temp / "grub.cfg"
    dst = temp / "branded.cfg"
    src.write_text(sample, encoding="utf-8")
    subprocess.run(["python3", "-B", str(TOOL), str(src), str(dst)], check=True)
    result = dst.read_text(encoding="utf-8")

checks = {
    "primary GRUB title": "Try or Install LiMaD OS",
    "safe graphics GRUB title": "LiMaD OS (safe graphics)",
    "SMBIOS model query": "smbios --type 1 --get-string 5 --set limad_system_product",
    "iMac17,1 model guard": 'if [ "$limad_system_product" = "iMac17,1" ]; then',
    "targeted Radeon parameters": 'set limad_hw_quirks="radeon.cik_support=1 amdgpu.cik_support=0"',
    "normal live boot variable": "linux /casper/vmlinuz quiet splash $limad_hw_quirks ---",
    "safe live boot variable": "linux /casper/vmlinuz nomodeset $limad_hw_quirks ---",
    "original initrd command": "initrd /casper/initrd",
}
for label, needle in checks.items():
    if needle not in result:
        raise SystemExit(f"ERROR: {label} missing")

if 'set limad_hw_quirks=""' not in result:
    raise SystemExit("ERROR: non-iMac default must keep graphics quirks empty")

print("GRUB BRANDING + IMAC17 TEST: PASS")
