#!/usr/bin/python3
from __future__ import annotations

import contextlib
import importlib.util
import json
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CORE = ROOT / "build/rootfs/usr/share/limad-save/core.py"
APP = ROOT / "build/rootfs/usr/share/limad-save/app.py"
VERSION = ROOT / "build/rootfs/usr/share/limad-save/VERSION"
VERIFY = ROOT / "tests/verify-built-iso.sh"

if VERSION.read_text(encoding="utf-8").strip() != "1.0.2":
    raise AssertionError("LiSave V33 system version must be 1.0.2")

core_source = CORE.read_text(encoding="utf-8")
app_source = APP.read_text(encoding="utf-8")
verify_source = VERIFY.read_text(encoding="utf-8")

for needle in (
    'VERSION = "1.0.2"',
    'phase="restore-snapshot"',
    'message.get("bytes_restored")',
    'message.get("files_restored")',
    '"--json", "--verbose=2"',
    'def restore_item_stats(',
    'def copy_item_with_progress(',
    'phase="restore-copy"',
    'phase_index=8, phase_total=phase_total',
):
    if needle not in core_source:
        raise AssertionError(f"LiSave V33 restore progress core missing: {needle}")

for needle in (
    'self.progress_pending_lock = threading.Lock()',
    'self.progress_pending = message',
    'pending = self.progress_pending',
):
    if needle not in app_source:
        raise AssertionError(f"LiSave V33 GTK progress coalescing missing: {needle}")

if verify_source.count('[ "$(cat "$TMP/lisave-version")" = "1.0.2" ]') < 2:
    raise AssertionError("Built ISO validator must require LiSave 1.0.2 at both validation points")
if '1.0.0-preview' in verify_source:
    raise AssertionError("Built ISO validator still contains a preview LiSave version")

spec = importlib.util.spec_from_file_location("limad_save_v33_restore", CORE)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

with tempfile.TemporaryDirectory(prefix="limad-v33-restore-") as temporary:
    base = Path(temporary)
    bundle = base / "backup.lisavebackup"
    repo = bundle / "repository"
    for relative, data in {
        "config": b"config\n",
        "keys/key": b"key\n",
        "index/index": b"index\n",
        "snapshots/snapshot": b"snapshot\n",
        "data/aa/data": b"data\n",
    }.items():
        path = repo / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    (bundle / "lisave.json").write_text('{"format":2,"container":"zip"}\n', encoding="utf-8")

    new_home = base / "new-home"
    new_home.mkdir()
    old_home = Path("/home/olduser")
    module.HOME = new_home
    module.CONFIG_HOME = new_home / ".config"
    module.DATA_HOME = new_home / ".local/share"
    module.STATE_HOME = new_home / ".local/state"
    module.STATE_DIR = module.STATE_HOME / "limad-save"
    module.REPORT_DIR = module.STATE_DIR / "reports"
    module.RESTORE_WORK_DIR = module.STATE_DIR / "restore-work"

    module.ensure_dependencies = lambda: None
    def fake_restic(*args, **kwargs):
        arguments = args[2] if len(args) > 2 else []
        if arguments and arguments[0] == "stats":
            return subprocess.CompletedProcess(args=[], returncode=0, stdout='{"total_size":1048600,"total_file_count":3}\n', stderr=None)
        return subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr=None)
    module.restic = fake_restic
    module.latest_snapshot = lambda *args, **kwargs: {"id": "snapshot-123", "time": "2026-08-21T20:00:00Z"}
    module.install_flatpaks = lambda apps, progress=None: []
    module.stop_apps = lambda: None
    module.restore_dconf = lambda stage: []

    @contextlib.contextmanager
    def fake_opened_backup(target, progress=None, **kwargs):
        yield bundle
    module.opened_backup = fake_opened_backup

    def fake_stream(bundle_arg, password, arguments, on_message, **kwargs):
        restore_root = Path(arguments[arguments.index("--target") + 1])
        restored_home = restore_root / "home/olduser"
        docs = restored_home / "Documents"
        docs.mkdir(parents=True, exist_ok=True)
        (docs / "test.txt").write_text("LiSave restore test\n", encoding="utf-8")
        (docs / "sub").mkdir()
        (docs / "sub/data.bin").write_bytes(b"x" * 1024 * 1024)
        (docs / "link").symlink_to("test.txt")
        stage = restored_home / ".local/state/limad-save/snapshots/test-stage"
        stage.mkdir(parents=True, exist_ok=True)
        (stage / "manifest.json").write_text(json.dumps({
            "home": str(old_home),
            "sources": {"documents": [str(old_home / "Documents")]},
            "flatpaks": [],
        }), encoding="utf-8")
        (stage / "dconf.json").write_text("[]\n", encoding="utf-8")
        on_message({"message_type":"status","seconds_elapsed":1,"percent_done":0.5,"total_files":3,"files_restored":1,"total_bytes":1048600,"bytes_restored":524300})
        on_message({"message_type":"verbose_status","action":"restored","item":"/home/olduser/Documents/test.txt","size":20})
        on_message({"message_type":"status","seconds_elapsed":2,"percent_done":1.0,"total_files":3,"files_restored":3,"total_bytes":1048600,"bytes_restored":1048600})
        return subprocess.CompletedProcess(args=arguments, returncode=0, stdout="", stderr=None)
    module.restic_json_stream = fake_stream

    events = []
    categories = {key: False for key in module.DEFAULT_CATEGORIES}
    categories["documents"] = True
    result = module.restore(bundle, "1234567890", categories, events.append)
    if not result.get("ok"):
        raise AssertionError("LiSave V33 restore did not complete")
    if (new_home / "Documents/test.txt").read_text(encoding="utf-8") != "LiSave restore test\n":
        raise AssertionError("LiSave V33 restore did not copy restored file")
    if (new_home / "Documents/sub/data.bin").stat().st_size != 1024 * 1024:
        raise AssertionError("LiSave V33 restore did not copy binary data")
    if not (new_home / "Documents/link").is_symlink():
        raise AssertionError("LiSave V33 restore did not preserve symlink")
    snapshot_events = [event for event in events if event.get("phase") == "restore-snapshot"]
    copy_events = [event for event in events if event.get("phase") == "restore-copy"]
    if not snapshot_events or not any(float(event.get("fraction") or 0) >= 1.0 for event in snapshot_events):
        raise AssertionError("LiSave V33 temporary restore has no determinate completion progress")
    if not copy_events or float(copy_events[-1].get("fraction") or 0) != 1.0:
        raise AssertionError("LiSave V33 home copy did not finish at 100 percent")
    if not any(float(event.get("speed_bps") or 0) > 0 for event in copy_events):
        raise AssertionError("LiSave V33 home copy has no measured speed")
    if not any(event.get("current") for event in snapshot_events + copy_events):
        raise AssertionError("LiSave V33 restore does not report current item")

print("V33 LISAVE RESTORE PROGRESS TEST: PASS")
