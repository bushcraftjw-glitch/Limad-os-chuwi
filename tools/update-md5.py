#!/usr/bin/python3
import hashlib
import pathlib
import sys

if len(sys.argv) != 5:
    raise SystemExit("usage: update-md5.py ORIGINAL_MD5 MODIFIED_FILE ISO_PATH OUTPUT_MD5")

source_md5 = pathlib.Path(sys.argv[1])
modified = pathlib.Path(sys.argv[2])
iso_path = sys.argv[3].lstrip("./")
output_md5 = pathlib.Path(sys.argv[4])

new_hash = hashlib.md5(modified.read_bytes()).hexdigest()
lines = source_md5.read_text(encoding="utf-8", errors="replace").splitlines()
result = []
replaced = False

for line in lines:
    if "  " not in line:
        result.append(line)
        continue
    _digest, path = line.split("  ", 1)
    normalized = path.lstrip("./")
    if normalized == iso_path:
        result.append(f"{new_hash}  ./{iso_path}")
        replaced = True
    else:
        result.append(line)

if not replaced:
    result.append(f"{new_hash}  ./{iso_path}")

output_md5.parent.mkdir(parents=True, exist_ok=True)
output_md5.write_text("\n".join(result) + "\n", encoding="utf-8")
output_md5.chmod(0o644)
