#!/usr/bin/python3
from __future__ import annotations
import importlib.util
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CORE = ROOT / "build/rootfs/usr/share/limad-save/core.py"
VERSION = ROOT / "build/rootfs/usr/share/limad-save/VERSION"
DETECTOR = ROOT / "build/rootfs/usr/local/bin/limad-save-first-login-detect"

if VERSION.read_text(encoding="utf-8").strip() != "1.0.1":
    raise AssertionError("LiSave portable ZIP regression must use current 1.0.1 system version")
source = CORE.read_text(encoding="utf-8")
for needle in (
    'VERSION = "1.0.1"',
    'def write_backup_archive(',
    'def extract_backup_archive(',
    'def opened_backup(',
    'restic(bundle, password, ["check"]',
    '"container": "zip"',
    'shutil.rmtree(legacy, ignore_errors=False)',
):
    if needle not in source:
        raise AssertionError(f"LiSave portable ZIP implementation missing: {needle}")
detector = DETECTOR.read_text(encoding="utf-8")
for needle in ("*.lisavebackup.zip", "zipfile.ZipFile", "/repository/config", "/lisave.json"):
    if needle not in detector:
        raise AssertionError(f"LiSave first-login ZIP detection missing: {needle}")

spec = importlib.util.spec_from_file_location("limad_save_v32", CORE)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

with tempfile.TemporaryDirectory(prefix="limad-v32-lisave-") as temporary:
    root = Path(temporary)
    bundle = root / "test.lisavebackup"
    files = {
        "repository/config": b"config\n",
        "repository/keys/key": b"key\n",
        "repository/index/index": b"index\n",
        "repository/snapshots/snapshot": b"snapshot\n",
        "repository/data/aa/data": b"data\n",
        "lisave.json": b'{"format":2,"container":"zip"}\n',
    }
    for relative, data in files.items():
        target = bundle / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    archive = root / "test.lisavebackup.zip"
    module.write_backup_archive(bundle, archive)
    if not archive.is_file() or archive.stat().st_size <= 0:
        raise AssertionError("LiSave did not create a non-empty portable ZIP")
    with zipfile.ZipFile(archive) as zf:
        if zf.testzip() is not None:
            raise AssertionError("LiSave portable ZIP CRC validation failed")
        if not any(info.filename.endswith("/repository/config") and info.file_size > 0 for info in zf.infolist()):
            raise AssertionError("LiSave portable ZIP repository config is missing/empty")
    extract_root = root / "extract"
    extract_root.mkdir()
    extracted = module.extract_backup_archive(archive, extract_root)
    module.validate_bundle_files(extracted)

    broken = root / "broken.lisavebackup.zip"
    with zipfile.ZipFile(broken, "w") as zf:
        zf.writestr("broken.lisavebackup/repository/config", b"")
        zf.writestr("broken.lisavebackup/lisave.json", b"")
    try:
        bad_root = root / "bad"
        bad_root.mkdir()
        module.extract_backup_archive(broken, bad_root)
    except module.LiSaveError:
        pass
    else:
        raise AssertionError("LiSave accepted an invalid 0-byte backup archive")

print("V31 LISAVE PORTABLE ZIP TEST: PASS")
