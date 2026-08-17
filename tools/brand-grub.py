#!/usr/bin/python3
import pathlib
import re
import sys

if len(sys.argv) != 3:
    raise SystemExit("usage: brand-grub.py INPUT OUTPUT")

source = pathlib.Path(sys.argv[1])
output = pathlib.Path(sys.argv[2])
text = source.read_text(encoding="utf-8", errors="replace")
lines = []
changed = 0
linux_changed = 0
pattern = re.compile(r"^(\s*(?:menuentry|submenu)\s+)(['\"])(.*?)(\2)(.*)$")

compat_block = '''# LiMaD OS iMac17,1 compatibility: only this DMI model uses the legacy CIK radeon path.\nset limad_hw_quirks=""\ninsmod smbios\nsmbios --type 1 --get-string 5 --set limad_system_product\nif [ "$limad_system_product" = "iMac17,1" ]; then\n    set limad_hw_quirks="radeon.cik_support=1 amdgpu.cik_support=0"\nfi\n\n'''

for line in text.splitlines(keepends=True):
    raw = line.rstrip("\r\n")
    ending = line[len(raw):]
    match = pattern.match(raw)
    if match:
        title = match.group(3)
        branded = title.replace("Ubuntu", "LiMaD OS")
        if branded != title:
            changed += 1
        raw = f"{match.group(1)}{match.group(2)}{branded}{match.group(4)}{match.group(5)}"

    stripped = raw.lstrip()
    if stripped.startswith("linux ") and "/casper/vmlinuz" in stripped and "$limad_hw_quirks" not in raw:
        if " ---" in raw:
            raw = raw.replace(" ---", " $limad_hw_quirks ---", 1)
        else:
            raw = f"{raw} $limad_hw_quirks"
        linux_changed += 1

    lines.append(raw + ending)

if changed == 0:
    raise SystemExit("ERROR: no Ubuntu GRUB menu title was found to brand")
if linux_changed == 0:
    raise SystemExit("ERROR: no live Linux boot command was found for iMac17,1 compatibility")

output.parent.mkdir(parents=True, exist_ok=True)
output.write_text(compat_block + "".join(lines), encoding="utf-8")
output.chmod(0o644)
print(f"GRUB BRANDING: PASS ({changed} menu titles, {linux_changed} live boot commands)")
