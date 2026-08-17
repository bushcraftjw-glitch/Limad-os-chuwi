#!/usr/bin/python3
import hashlib
import pathlib
import stat
import subprocess
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "update-md5.py"

with tempfile.TemporaryDirectory() as tmpdir:
    tmp = pathlib.Path(tmpdir)
    source = tmp / "md5sum.original.txt"
    modified = tmp / "install-sources.yaml"
    output = tmp / "md5sum.txt"

    source_content = "d41d8cd98f00b204e9800998ecf8427e  ./casper/install-sources.yaml\n"
    source.write_text(source_content, encoding="utf-8")
    source.chmod(0o444)
    modified.write_text("sources:\n  - id: ubuntu-desktop\n", encoding="utf-8")

    subprocess.run(
        ["python3", "-B", str(TOOL), str(source), str(modified), "casper/install-sources.yaml", str(output)],
        check=True,
    )

    if source.read_text(encoding="utf-8") != source_content:
        raise SystemExit("ERROR: read-only source md5 file was modified")

    expected = hashlib.md5(modified.read_bytes()).hexdigest()
    text = output.read_text(encoding="utf-8")
    if f"{expected}  ./casper/install-sources.yaml" not in text:
        raise SystemExit("ERROR: output md5 does not contain updated install-sources hash")

    mode = stat.S_IMODE(output.stat().st_mode)
    if mode != 0o644:
        raise SystemExit(f"ERROR: output md5 mode is {oct(mode)}, expected 0o644")

print("MD5 OVERLAY TEST: PASS")
