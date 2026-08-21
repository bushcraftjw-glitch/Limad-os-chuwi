#!/usr/bin/python3
from __future__ import annotations

import importlib.util
import os
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CORE = ROOT / "build/rootfs/usr/share/limad-save/core.py"
APP = ROOT / "build/rootfs/usr/share/limad-save/app.py"
CLI = ROOT / "build/rootfs/usr/share/limad-save/cli.py"
VERSION = ROOT / "build/rootfs/usr/share/limad-save/VERSION"
VERIFY_BUILT_ISO = ROOT / "tests/verify-built-iso.sh"

if VERSION.read_text(encoding="utf-8").strip() != "1.0.1":
    raise AssertionError("LiSave current system version must be 1.0.1")

verify_source = VERIFY_BUILT_ISO.read_text(encoding="utf-8")
if '[ "$(cat "$TMP/lisave-version")" = "1.0.1" ]' not in verify_source:
    raise AssertionError("Built-ISO validator does not require current LiSave 1.0.1")
if '1.0.0-preview' in verify_source:
    raise AssertionError("Built-ISO validator still contains stale LiSave preview marker")

core_source = CORE.read_text(encoding="utf-8")
app_source = APP.read_text(encoding="utf-8")
cli_source = CLI.read_text(encoding="utf-8")

for needle in (
    'VERSION = "1.0.1"',
    "def restic_json_stream(",
    'message.get("seconds_remaining")',
    'message.get("current_files")',
    'phase="archive-write"',
    'phase="archive-verify"',
    "speed_bps=",
    "seconds_remaining=",
):
    if needle not in core_source:
        raise AssertionError(f"LiSave progress core missing: {needle}")

for needle in (
    'Gtk.Frame(label="Fortschritt")',
    'Quelle:',
    'Ziel:',
    'Aktuell:',
    'Restzeit: ca.',
    'Ende ca.',
    'self.progress.set_fraction',
    'self.progress.pulse()',
):
    if needle not in app_source:
        raise AssertionError(f"LiSave progress UI missing: {needle}")

if "isinstance(update, dict)" not in cli_source:
    raise AssertionError("LiSave CLI does not handle structured progress events")

spec = importlib.util.spec_from_file_location("limad_save_v32_progress", CORE)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

with tempfile.TemporaryDirectory(prefix="limad-v32-progress-") as temporary:
    root = Path(temporary)
    bundle = root / "test.lisavebackup"
    files = {
        "repository/config": b"config\n",
        "repository/keys/key": b"key\n",
        "repository/index/index": b"index\n",
        "repository/snapshots/snapshot": b"snapshot\n",
        "repository/data/aa/data": b"x" * (3 * 1024 * 1024 + 321),
        "lisave.json": b'{"format":2,"container":"zip"}\n',
    }
    for relative, data in files.items():
        target = bundle / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)

    archive = root / "test.lisavebackup.zip"
    events = []
    module.write_backup_archive(bundle, archive, events.append)
    if not archive.is_file() or archive.stat().st_size <= 0:
        raise AssertionError("LiSave progress ZIP was not created")
    with zipfile.ZipFile(archive) as zf:
        if zf.testzip() is not None:
            raise AssertionError("LiSave progress ZIP CRC validation failed")

    write_events = [event for event in events if event.get("phase") == "archive-write"]
    verify_events = [event for event in events if event.get("phase") == "archive-verify"]
    if not write_events or not verify_events:
        raise AssertionError("LiSave did not emit ZIP write/verify progress phases")
    if not any(isinstance(event.get("fraction"), float) and event["fraction"] > 0 for event in write_events):
        raise AssertionError("LiSave ZIP write progress has no determinate fraction")
    if verify_events[-1].get("fraction") != 1.0:
        raise AssertionError("LiSave ZIP verify progress did not finish at 100 percent")
    if not any(float(event.get("speed_bps") or 0) > 0 for event in events):
        raise AssertionError("LiSave ZIP progress has no measured transfer speed")
    if not any(event.get("seconds_remaining") is not None for event in events):
        raise AssertionError("LiSave ZIP progress has no ETA data")

with tempfile.TemporaryDirectory(prefix="limad-v32-restic-json-") as temporary:
    root = Path(temporary)
    fake_restic = root / "restic"
    fake_restic.write_text(
        "#!/usr/bin/bash\n"
        "printf '%s\\n' "
        "'{\"message_type\":\"status\",\"seconds_elapsed\":2,\"seconds_remaining\":8,\"percent_done\":0.2,\"total_files\":10,\"files_done\":2,\"total_bytes\":1000,\"bytes_done\":200,\"current_files\":[\"/home/test/Documents/a.txt\"]}' "
        "'{\"message_type\":\"summary\",\"total_files_processed\":10,\"total_bytes_processed\":1000,\"snapshot_id\":\"abc\"}'\n",
        encoding="utf-8",
    )
    fake_restic.chmod(0o755)
    old_path = os.environ.get("PATH", "")
    os.environ["PATH"] = f"{root}:{old_path}"
    try:
        bundle = root / "stream.lisavebackup"
        (bundle / "repository").mkdir(parents=True)
        messages = []
        result = module.restic_json_stream(bundle, "1234567890", ["backup", "--json", "/tmp"], messages.append)
        if result.returncode != 0 or len(messages) != 2:
            raise AssertionError("LiSave Restic JSON stream parser failed")
        if messages[0].get("bytes_done") != 200 or messages[0].get("seconds_remaining") != 8:
            raise AssertionError("LiSave Restic status metrics were not preserved")
        if messages[0].get("current_files") != ["/home/test/Documents/a.txt"]:
            raise AssertionError("LiSave Restic current-file status was not preserved")
    finally:
        os.environ["PATH"] = old_path

print("V32 LISAVE LIVE PROGRESS TEST: PASS")
