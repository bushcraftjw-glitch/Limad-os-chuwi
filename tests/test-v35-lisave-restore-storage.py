#!/usr/bin/python3
from __future__ import annotations

import importlib.util
import json
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CORE = ROOT / "build/rootfs/usr/share/limad-save/core.py"
VERSION = ROOT / "build/rootfs/usr/share/limad-save/VERSION"

if VERSION.read_text(encoding="utf-8").strip() != "1.0.2":
    raise AssertionError("LiSave V35 system version must be 1.0.2")

source = CORE.read_text(encoding="utf-8")
required = [
    'VERSION = "1.0.2"',
    'RESTORE_WORK_DIR = STATE_DIR / "restore-work"',
    '["stats", "--mode", "restore-size", "--json", snapshot_id]',
    'shutil.disk_usage(RESTORE_WORK_DIR).free',
    'required = restore_size * 2 + reserve',
    'tempfile.TemporaryDirectory(prefix="restore-", dir=workspace_parent)',
    'restore_environment["TMPDIR"] = str(workspace_parent)',
    'raise LiSaveError(restic_stream_error(result.stdout, returncode))',
    'Nicht genügend freier Speicherplatz für die sichere Wiederherstellung.',
]
for marker in required:
    if marker not in source:
        raise AssertionError(f"LiSave V35 restore storage marker missing: {marker}")

if 'TemporaryDirectory(prefix="lisave-restore-")' in source:
    raise AssertionError("LiSave V35 must not restore into the system temporary directory")

spec = importlib.util.spec_from_file_location("limad_save_v35_storage", CORE)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

original_restic = module.restic
module.restic = lambda *args, **kwargs: subprocess.CompletedProcess(
    args=[], returncode=0,
    stdout='[0:00] 100.00% 1 / 1 snapshots\n{"total_size":10522669875,"total_file_count":702,"snapshots_count":1}\n',
    stderr=None,
)
size, files = module.snapshot_restore_stats(Path("/tmp/bundle"), "password", "snapshot-123")
module.restic = original_restic
if size != 10522669875 or files != 702:
    raise AssertionError("LiSave V35 does not parse restic restore-size JSON robustly")

with tempfile.TemporaryDirectory(prefix="limad-v35-workspace-test-") as temporary:
    module.RESTORE_WORK_DIR = Path(temporary) / "restore-work"
    parent, required_free, available_free = module.prepare_restore_workspace(1024 * 1024)
    if parent != module.RESTORE_WORK_DIR or not parent.is_dir():
        raise AssertionError("LiSave V35 restore workspace is not created at the configured disk-backed path")
    if required_free <= 1024 * 1024 or available_free <= 0:
        raise AssertionError("LiSave V35 restore capacity calculation is invalid")

error_line = json.dumps({
    "message_type": "error",
    "error": {"message": "write file: no space left on device"},
    "during": "restore",
    "item": "/home/olduser/Documents/example.bin",
})
message = module.restic_stream_error(error_line + "\n", 1)
if message != "Nicht genügend Speicherplatz für die Wiederherstellung.":
    raise AssertionError("LiSave V35 exposes raw restic JSON instead of a readable storage error")

print("V35 LISAVE RESTORE STORAGE TEST: PASS")
