from __future__ import annotations

import configparser
from contextlib import contextmanager
import hashlib
import json
import os
import platform
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import zipfile
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Callable

VERSION = "1.0.2"
APP_ID = "de.limad.Save"
HOME = Path.home()
CONFIG_HOME = Path(os.environ.get("XDG_CONFIG_HOME", HOME / ".config"))
DATA_HOME = Path(os.environ.get("XDG_DATA_HOME", HOME / ".local/share"))
STATE_HOME = Path(os.environ.get("XDG_STATE_HOME", HOME / ".local/state"))
CACHE_HOME = Path(os.environ.get("XDG_CACHE_HOME", HOME / ".cache"))
CONFIG_DIR = CONFIG_HOME / "limad-save"
CONFIG_FILE = CONFIG_DIR / "config.json"
STATE_DIR = STATE_HOME / "limad-save"
REPORT_DIR = STATE_DIR / "reports"
SNAPSHOT_STAGE = STATE_DIR / "snapshots"
RESTORE_WORK_DIR = STATE_DIR / "restore-work"
DEFAULT_CATEGORIES = {
    "documents": True,
    "zen": True,
    "mail": True,
    "study": True,
    "notes": True,
    "windows": True,
    "windows_full": False,
    "settings": True,
    "appsettings": True,
}


class LiSaveError(RuntimeError):
    pass


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def run(args: list[str], *, input_text: str | None = None, env: dict | None = None, check: bool = False, timeout: int | None = None) -> subprocess.CompletedProcess:
    result = subprocess.run(args, input=input_text, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, env=env, timeout=timeout, check=False)
    if check and result.returncode:
        raise LiSaveError(result.stdout.strip() or f"Befehl fehlgeschlagen: {' '.join(args)}")
    return result


def load_json(path: Path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


def save_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def load_config() -> dict:
    value = load_json(CONFIG_FILE, {})
    if not isinstance(value, dict):
        value = {}
    value.setdefault("categories", dict(DEFAULT_CATEGORIES))
    value.setdefault("automatic", False)
    value.setdefault("before_update", True)
    value.setdefault("retention", {"daily": 7, "weekly": 4, "monthly": 6})
    return value


def save_config(value: dict) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    save_json(CONFIG_FILE, value)
    os.chmod(CONFIG_FILE, 0o600)


def xdg_user_dir(key: str, fallback: str) -> Path:
    config = CONFIG_HOME / "user-dirs.dirs"
    try:
        for line in config.read_text(encoding="utf-8").splitlines():
            if line.startswith(f"XDG_{key}_DIR="):
                raw = line.split("=", 1)[1].strip().strip('"').replace("$HOME", str(HOME))
                value = Path(os.path.expandvars(os.path.expanduser(raw)))
                if value.is_absolute():
                    return value
    except OSError:
        pass
    return HOME / fallback


def backup_basename() -> str:
    name = socket.gethostname().split(".")[0] or "LiMaD"
    safe = "".join(ch if ch.isalnum() or ch in "-_" else "-" for ch in name).strip("-") or "LiMaD"
    return f"{safe}.lisavebackup"


def bundle_path(target: Path) -> Path:
    target = Path(target).expanduser().resolve()
    if target.name.endswith(".lisavebackup.zip"):
        return target.with_name(target.name[:-4])
    if target.name.endswith(".lisavebackup"):
        return target
    return target / backup_basename()


def archive_path(target: Path) -> Path:
    target = Path(target).expanduser().resolve()
    if target.name.endswith(".lisavebackup.zip"):
        return target
    if target.name.endswith(".lisavebackup"):
        return target.with_name(target.name + ".zip")
    return target / f"{backup_basename()}.zip"


def repository_path(bundle: Path) -> Path:
    return bundle / "repository"


def existing_backup_candidates(target: Path) -> list[Path]:
    target = Path(target).expanduser().resolve()
    if target.name.endswith(".lisavebackup.zip"):
        return [target]
    if target.name.endswith(".lisavebackup"):
        return [target.with_name(target.name + ".zip"), target]
    if not target.is_dir():
        return [archive_path(target), bundle_path(target)]
    preferred = [archive_path(target), bundle_path(target)]
    discovered = []
    try:
        discovered.extend(target.glob("*.lisavebackup.zip"))
        discovered.extend(target.glob("*.lisavebackup"))
    except OSError:
        pass
    ordered = []
    seen = set()
    for candidate in preferred + sorted(discovered, key=lambda path: path.stat().st_mtime if path.exists() else 0, reverse=True):
        key = str(candidate)
        if key not in seen:
            ordered.append(candidate)
            seen.add(key)
    return ordered


def resolve_existing_backup(target: Path) -> Path:
    target = Path(target).expanduser().resolve()
    explicit_archive = target.name.endswith(".lisavebackup.zip")
    archive_error = None
    for candidate in existing_backup_candidates(target):
        if candidate.is_file() and candidate.name.endswith(".lisavebackup.zip"):
            try:
                validate_backup_archive(candidate)
            except LiSaveError as exc:
                archive_error = exc
                continue
            return candidate
        if candidate.is_dir() and candidate.name.endswith(".lisavebackup"):
            return candidate
    if explicit_archive and archive_error is not None:
        raise archive_error
    raise LiSaveError("Am ausgewählten Ziel wurde kein gültiger LiSave-Backup-Container gefunden.")


def validate_bundle_files(bundle: Path) -> None:
    required = [
        repository_path(bundle) / "config",
        bundle / "lisave.json",
    ]
    for path in required:
        if not path.is_file() or path.stat().st_size <= 0:
            raise LiSaveError(f"LiSave-Backup ist unvollständig oder enthält eine 0-Byte-Datei: {path.name}")
    for folder, label in (("keys", "Schlüssel"), ("index", "Index"), ("snapshots", "Snapshot"), ("data", "Daten")):
        root = repository_path(bundle) / folder
        try:
            valid = any(path.is_file() and path.stat().st_size > 0 for path in root.rglob("*"))
        except OSError:
            valid = False
        if not valid:
            raise LiSaveError(f"LiSave-Backup enthält keine gültigen {label}-Dateien.")


def safe_zip_member(info: zipfile.ZipInfo) -> bool:
    name = info.filename
    if not name or "\x00" in name:
        return False
    path = PurePosixPath(name)
    if path.is_absolute() or ".." in path.parts or not path.parts:
        return False
    mode = (info.external_attr >> 16) & 0o170000
    return mode != 0o120000


def validate_backup_archive(archive: Path, *, check_crc: bool = True) -> None:
    try:
        with zipfile.ZipFile(archive) as zf:
            infos = zf.infolist()
            if not infos:
                raise LiSaveError("Das LiSave-ZIP ist leer.")
            if any(not safe_zip_member(info) for info in infos):
                raise LiSaveError("Das LiSave-ZIP enthält einen unsicheren Dateipfad oder symbolischen Link.")
            if check_crc:
                bad = zf.testzip()
                if bad:
                    raise LiSaveError(f"Das LiSave-ZIP ist beschädigt: {bad}")
            files = [info for info in infos if not info.is_dir()]
            if not files:
                raise LiSaveError("Das LiSave-ZIP enthält keine Dateien.")
            requirements = {
                "lisave.json": lambda name: name.endswith("/lisave.json"),
                "repository/config": lambda name: name.endswith("/repository/config"),
                "repository/keys": lambda name: "/repository/keys/" in name,
                "repository/index": lambda name: "/repository/index/" in name,
                "repository/snapshots": lambda name: "/repository/snapshots/" in name,
                "repository/data": lambda name: "/repository/data/" in name,
            }
            for label, matcher in requirements.items():
                if not any(matcher(info.filename) and info.file_size > 0 for info in files):
                    raise LiSaveError(f"LiSave-ZIP ist unvollständig oder enthält 0-Byte-Daten: {label}")
    except zipfile.BadZipFile as exc:
        raise LiSaveError("Das ausgewählte LiSave-ZIP ist beschädigt.") from exc


def emit_progress(progress, message: str, **details) -> None:
    if not progress:
        return
    event = {"message": message}
    event.update({key: value for key, value in details.items() if value is not None})
    progress(event)


def progress_metrics(started: float, done: int, total: int) -> tuple[float, int | None]:
    elapsed = max(time.monotonic() - started, 0.001)
    speed = done / elapsed if done > 0 else 0.0
    remaining = None
    if speed > 0 and total >= done:
        remaining = int((total - done) / speed)
    return speed, remaining


def source_for_item(item: str, roots: list[Path], stage: Path) -> str:
    candidate = Path(item)
    try:
        candidate.resolve().relative_to(stage.resolve())
        return "LiSave-Metadaten und Wiederherstellungsplan"
    except (OSError, ValueError):
        pass
    best = None
    for root in roots:
        try:
            candidate.resolve().relative_to(root.resolve())
        except (OSError, ValueError):
            continue
        if best is None or len(root.parts) > len(best.parts):
            best = root
    return str(best) if best else str(candidate.parent)


def extract_backup_archive(archive: Path, destination: Path, progress=None, *, phase_index: int = 1, phase_total: int = 6, target: Path | None = None) -> Path:
    validate_backup_archive(archive, check_crc=False)
    try:
        with zipfile.ZipFile(archive) as zf:
            infos = zf.infolist()
            files = [info for info in infos if not info.is_dir()]
            first_parts = {PurePosixPath(info.filename).parts[0] for info in files}
            prefixed = len(first_parts) == 1 and next(iter(first_parts)).endswith(".lisavebackup")
            root_name = next(iter(first_parts)) if prefixed else archive.name[:-4]
            if not root_name.endswith(".lisavebackup"):
                raise LiSaveError("Das ZIP besitzt keinen gültigen LiSave-Backup-Namen.")
            bundle = destination / root_name
            bundle.mkdir(parents=True, exist_ok=False)
            total_bytes = sum(info.file_size for info in files)
            total_files = len(files)
            bytes_done = 0
            files_done = 0
            started = time.monotonic()
            last_update = 0.0
            emit_progress(
                progress,
                "Vorhandenes LiSave-ZIP wird geöffnet …",
                phase="archive-open", phase_index=phase_index, phase_total=phase_total,
                source=str(archive), target=str(target or bundle), fraction=0.0,
                bytes_done=0, bytes_total=total_bytes, files_done=0, files_total=total_files,
            )
            for info in infos:
                parts = list(PurePosixPath(info.filename).parts)
                if prefixed:
                    parts = parts[1:]
                if not parts:
                    continue
                output = bundle.joinpath(*parts)
                if info.is_dir():
                    output.mkdir(parents=True, exist_ok=True)
                    continue
                output.parent.mkdir(parents=True, exist_ok=True)
                try:
                    with zf.open(info) as source, output.open("wb") as handle:
                        while True:
                            block = source.read(1024 * 1024)
                            if not block:
                                break
                            handle.write(block)
                            bytes_done += len(block)
                            now = time.monotonic()
                            if now - last_update >= 0.25:
                                speed, remaining = progress_metrics(started, bytes_done, total_bytes)
                                emit_progress(
                                    progress,
                                    "Vorhandenes Backup wird für die Verarbeitung geöffnet …",
                                    phase="archive-open", phase_index=phase_index, phase_total=phase_total,
                                    source=str(archive), target=str(bundle), current=info.filename,
                                    fraction=(bytes_done / total_bytes) if total_bytes else 1.0,
                                    bytes_done=bytes_done, bytes_total=total_bytes,
                                    files_done=files_done, files_total=total_files,
                                    speed_bps=speed, seconds_remaining=remaining,
                                )
                                last_update = now
                except zipfile.BadZipFile as exc:
                    raise LiSaveError(f"Das LiSave-ZIP ist beschädigt: {info.filename}") from exc
                files_done += 1
            validate_bundle_files(bundle)
            speed, _ = progress_metrics(started, bytes_done, total_bytes)
            emit_progress(
                progress,
                "Vorhandenes Backup wurde vollständig geöffnet.",
                phase="archive-open", phase_index=phase_index, phase_total=phase_total,
                source=str(archive), target=str(bundle), fraction=1.0,
                bytes_done=bytes_done, bytes_total=total_bytes,
                files_done=files_done, files_total=total_files, speed_bps=speed, seconds_remaining=0,
            )
            return bundle
    except zipfile.BadZipFile as exc:
        raise LiSaveError("Das ausgewählte LiSave-ZIP ist beschädigt.") from exc


def write_backup_archive(bundle: Path, archive: Path, progress=None, *, phase_index: int = 5, phase_total: int = 6) -> None:
    validate_bundle_files(bundle)
    archive.parent.mkdir(parents=True, exist_ok=True)
    files = [path for path in sorted(bundle.rglob("*")) if path.is_file()]
    total_bytes = sum(path.stat().st_size for path in files)
    total_files = len(files)
    fd, temporary_name = tempfile.mkstemp(prefix=f".{archive.name}.", suffix=".tmp", dir=archive.parent)
    os.close(fd)
    temporary = Path(temporary_name)
    bytes_done = 0
    files_done = 0
    started = time.monotonic()
    last_update = 0.0
    emit_progress(
        progress,
        "Portables LiSave-ZIP wird geschrieben …",
        phase="archive-write", phase_index=phase_index, phase_total=phase_total,
        source=str(bundle), target=str(archive), fraction=0.0,
        bytes_done=0, bytes_total=total_bytes, files_done=0, files_total=total_files,
    )
    try:
        with zipfile.ZipFile(temporary, "w", compression=zipfile.ZIP_STORED, allowZip64=True) as zf:
            for path in files:
                if path.is_symlink():
                    raise LiSaveError(f"Symbolische Links sind im LiSave-Backup nicht erlaubt: {path}")
                arcname = (PurePosixPath(bundle.name) / PurePosixPath(path.relative_to(bundle).as_posix())).as_posix()
                info = zipfile.ZipInfo.from_file(path, arcname)
                info.compress_type = zipfile.ZIP_STORED
                with path.open("rb") as source, zf.open(info, "w") as target_handle:
                    while True:
                        block = source.read(1024 * 1024)
                        if not block:
                            break
                        target_handle.write(block)
                        bytes_done += len(block)
                        now = time.monotonic()
                        if now - last_update >= 0.25:
                            speed, remaining = progress_metrics(started, bytes_done, total_bytes)
                            emit_progress(
                                progress,
                                "Backup-Dateien werden in das portable ZIP geschrieben …",
                                phase="archive-write", phase_index=phase_index, phase_total=phase_total,
                                source=str(bundle), target=str(archive),
                                current=str(path.relative_to(bundle)),
                                fraction=(bytes_done / total_bytes) if total_bytes else 1.0,
                                bytes_done=bytes_done, bytes_total=total_bytes,
                                files_done=files_done, files_total=total_files,
                                speed_bps=speed, seconds_remaining=remaining,
                            )
                            last_update = now
                files_done += 1
        with temporary.open("rb") as handle:
            os.fsync(handle.fileno())

        verify_total = total_bytes
        verify_done = 0
        verify_files = 0
        verify_started = time.monotonic()
        last_update = 0.0
        emit_progress(
            progress,
            "Erzeugtes ZIP wird vollständig geprüft …",
            phase="archive-verify", phase_index=phase_index + 1, phase_total=phase_total,
            source=str(temporary), target=str(archive), fraction=0.0,
            bytes_done=0, bytes_total=verify_total, files_done=0, files_total=total_files,
        )
        with zipfile.ZipFile(temporary) as zf:
            infos = [info for info in zf.infolist() if not info.is_dir()]
            non_empty = {info.filename: info.file_size for info in infos}
            for info in infos:
                try:
                    with zf.open(info) as source:
                        while True:
                            block = source.read(1024 * 1024)
                            if not block:
                                break
                            verify_done += len(block)
                            now = time.monotonic()
                            if now - last_update >= 0.25:
                                speed, remaining = progress_metrics(verify_started, verify_done, verify_total)
                                emit_progress(
                                    progress,
                                    "ZIP-Inhalt und CRC werden geprüft …",
                                    phase="archive-verify", phase_index=phase_index + 1, phase_total=phase_total,
                                    source=str(temporary), target=str(archive), current=info.filename,
                                    fraction=(verify_done / verify_total) if verify_total else 1.0,
                                    bytes_done=verify_done, bytes_total=verify_total,
                                    files_done=verify_files, files_total=total_files,
                                    speed_bps=speed, seconds_remaining=remaining,
                                )
                                last_update = now
                except zipfile.BadZipFile as exc:
                    raise LiSaveError(f"Die erzeugte LiSave-ZIP-Prüfung ist fehlgeschlagen: {info.filename}") from exc
                verify_files += 1
            required_suffixes = ("/lisave.json", "/repository/config")
            for suffix in required_suffixes:
                matches = [size for name, size in non_empty.items() if name.endswith(suffix)]
                if not matches or matches[0] <= 0:
                    raise LiSaveError(f"Die erzeugte LiSave-ZIP enthält eine ungültige 0-Byte-Datei: {suffix.rsplit('/', 1)[-1]}")
        os.replace(temporary, archive)
        try:
            directory_fd = os.open(archive.parent, os.O_RDONLY)
            try:
                os.fsync(directory_fd)
            finally:
                os.close(directory_fd)
        except OSError:
            pass
        speed, _ = progress_metrics(verify_started, verify_done, verify_total)
        emit_progress(
            progress,
            "Portables LiSave-ZIP wurde geschrieben und vollständig geprüft.",
            phase="archive-verify", phase_index=phase_total, phase_total=phase_total,
            source=str(bundle), target=str(archive), fraction=1.0,
            bytes_done=verify_done, bytes_total=verify_total,
            files_done=verify_files, files_total=total_files, speed_bps=speed, seconds_remaining=0,
        )
    finally:
        temporary.unlink(missing_ok=True)


def temporary_parent_for(backup: Path) -> Path:
    parent = backup.parent
    if os.access(parent, os.W_OK):
        return parent
    fallback = STATE_DIR / "archive-work"
    fallback.mkdir(parents=True, exist_ok=True)
    return fallback


@contextmanager
def opened_backup(target: Path, progress=None, *, phase_index: int = 1, phase_total: int = 6):
    selected = resolve_existing_backup(target)
    if selected.is_dir():
        validate_bundle_files(selected)
        emit_progress(
            progress,
            "LiSave-Backup-Ordner wurde geöffnet.",
            phase="archive-open", phase_index=phase_index, phase_total=phase_total,
            source=str(selected), target=str(selected), fraction=1.0,
        )
        yield selected
        return
    parent = temporary_parent_for(selected)
    with tempfile.TemporaryDirectory(prefix=".lisave-open-", dir=parent) as temporary:
        bundle = extract_backup_archive(
            selected, Path(temporary), progress,
            phase_index=phase_index, phase_total=phase_total, target=selected,
        )
        yield bundle


def ensure_external_target(bundle: Path) -> None:
    resolved_home = HOME.resolve()
    resolved_bundle = bundle.resolve()
    try:
        resolved_bundle.relative_to(resolved_home)
    except ValueError:
        return
    raise LiSaveError("Das LiSave-Ziel darf nicht im Benutzerordner liegen. Bitte ein zweites Laufwerk, eine USB-SSD oder einen USB-Stick auswählen.")


def repo_id(bundle: Path) -> str:
    return hashlib.sha256(str(bundle.resolve()).encode("utf-8")).hexdigest()


def ensure_dependencies() -> None:
    for command in ("restic", "flatpak", "dconf"):
        if not shutil.which(command):
            raise LiSaveError(f"Erforderliches Programm fehlt: {command}")


def secret_store(bundle: Path, password: str) -> None:
    tool = shutil.which("secret-tool")
    if not tool:
        raise LiSaveError("GNOME-Schlüsselbund ist nicht verfügbar; automatische Sicherung kann das Passwort nicht speichern.")
    result = run([tool, "store", "--label=LiSave Backup", "application", APP_ID, "repository", repo_id(bundle)], input_text=password)
    if result.returncode:
        raise LiSaveError(result.stdout.strip() or "Backup-Passwort konnte nicht im GNOME-Schlüsselbund gespeichert werden.")


def secret_lookup(bundle: Path) -> str:
    tool = shutil.which("secret-tool")
    if not tool:
        return ""
    result = run([tool, "lookup", "application", APP_ID, "repository", repo_id(bundle)])
    return result.stdout.rstrip("\n") if result.returncode == 0 else ""


def password_file(password: str):
    class PasswordContext:
        def __enter__(self):
            runtime = Path(os.environ.get("XDG_RUNTIME_DIR", tempfile.gettempdir()))
            runtime.mkdir(parents=True, exist_ok=True)
            fd, name = tempfile.mkstemp(prefix="lisave-password-", dir=runtime)
            os.write(fd, (password + "\n").encode("utf-8"))
            os.close(fd)
            os.chmod(name, 0o600)
            self.path = Path(name)
            return self.path

        def __exit__(self, *_):
            try:
                self.path.unlink()
            except OSError:
                pass
    return PasswordContext()


def restic(bundle: Path, password: str, arguments: list[str], *, check: bool = True, timeout: int | None = None) -> subprocess.CompletedProcess:
    repo = repository_path(bundle)
    with password_file(password) as password_path:
        args = ["restic", "-r", str(repo), "--password-file", str(password_path), *arguments]
        return run(args, check=check, timeout=timeout)


def restic_stream_error(output: str, returncode: int) -> str:
    messages = []
    plain = []
    for line in output.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        try:
            value = json.loads(stripped)
        except json.JSONDecodeError:
            plain.append(stripped)
            continue
        if not isinstance(value, dict):
            continue
        message_type = value.get("message_type")
        if message_type == "error":
            error = value.get("error")
            if isinstance(error, dict):
                detail = str(error.get("message") or "").strip()
            else:
                detail = str(error or value.get("message") or "").strip()
            item = str(value.get("item") or "").strip()
            if detail and item:
                messages.append(f"{detail} ({item})")
            elif detail:
                messages.append(detail)
        elif message_type == "exit_error":
            detail = str(value.get("message") or "").strip()
            if detail:
                messages.append(detail)
    detail = messages[-1] if messages else (plain[-1] if plain else f"Restic wurde mit Fehlercode {returncode} beendet.")
    if "no space left on device" in detail.lower():
        return "Nicht genügend Speicherplatz für die Wiederherstellung."
    return detail


def restic_json_stream(bundle: Path, password: str, arguments: list[str], on_message, *, check: bool = True, env: dict | None = None) -> subprocess.CompletedProcess:
    repo = repository_path(bundle)
    with password_file(password) as password_path:
        args = ["restic", "-r", str(repo), "--password-file", str(password_path), *arguments]
        process = subprocess.Popen(args, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, bufsize=1, env=env)
        output = []
        assert process.stdout is not None
        for line in process.stdout:
            output.append(line)
            try:
                message = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(message, dict):
                on_message(message)
        returncode = process.wait()
        result = subprocess.CompletedProcess(args=args, returncode=returncode, stdout="".join(output), stderr=None)
        if check and returncode:
            raise LiSaveError(restic_stream_error(result.stdout, returncode))
        return result


def ensure_repository(bundle: Path, password: str) -> None:
    bundle.mkdir(parents=True, exist_ok=True)
    repo = repository_path(bundle)
    if not (repo / "config").is_file():
        repo.mkdir(parents=True, exist_ok=True)
        restic(bundle, password, ["init"])
    else:
        restic(bundle, password, ["snapshots", "--json"], timeout=120)


ANALYSIS_EXCLUDED_DIR_NAMES = {
    "cache", "Cache", ".cache", "startupCache", "crashes",
    "shader-cache", "GPUCache", "Code Cache",
}
STUDY_EXCLUDED_DIR_NAMES = {"publications", "downloads", "catalog", "covers"}


def analysis_excluded_directory(path: Path, categories: dict) -> bool:
    if path.name in ANALYSIS_EXCLUDED_DIR_NAMES:
        return True
    parts = path.parts
    for index, part in enumerate(parts[:-1]):
        child = parts[index + 1]
        if part == "limad-study" and child in STUDY_EXCLUDED_DIR_NAMES:
            return True
        if part == "limad-windows":
            if child in {"prefix", "cache"} and not categories.get("windows_full", False):
                return True
            if child == "apps" and not categories.get("windows_full", False):
                tail = parts[index + 2:]
                if len(tail) >= 2 and tail[1] == "prefix":
                    return True
    if not categories.get("windows_full", False):
        marker = ("com.usebottles.bottles", "data", "bottles", "bottles")
        if any(parts[index:index + len(marker)] == marker for index in range(max(0, len(parts) - len(marker) + 1))):
            return True
    return False


def directory_size(path: Path, categories: dict | None = None) -> int:
    categories = {**DEFAULT_CATEGORIES, **(categories or {})}
    if not path.exists() or path.is_symlink():
        return 0
    if path.is_file():
        try:
            return path.stat().st_size
        except OSError:
            return 0
    total = 0
    for root, dirs, files in os.walk(path, followlinks=False):
        root_path = Path(root)
        kept = []
        for name in dirs:
            candidate = root_path / name
            if not analysis_excluded_directory(candidate, categories):
                kept.append(name)
        dirs[:] = kept
        for name in files:
            candidate = root_path / name
            if analysis_excluded_directory(candidate.parent, categories):
                continue
            try:
                total += candidate.stat().st_size
            except OSError:
                pass
    return total


def zen_roots() -> list[Path]:
    return [HOME / ".var/app/app.zen_browser.zen/zen", HOME / ".var/app/io.github.zen_browser.zen/zen", HOME / ".zen"]


def mail_roots() -> list[Path]:
    return [
        HOME / ".var/app/org.mozilla.thunderbird_esr/.thunderbird",
        HOME / ".var/app/org.mozilla.thunderbird/.thunderbird",
        HOME / ".var/app/org.mozilla.Thunderbird/.thunderbird",
        HOME / ".thunderbird",
    ]


def category_sources(categories: dict) -> dict[str, list[Path]]:
    documents = xdg_user_dir("DOCUMENTS", "Documents")
    desktop = xdg_user_dir("DESKTOP", "Desktop")
    downloads = xdg_user_dir("DOWNLOAD", "Downloads")
    sources: dict[str, list[Path]] = {key: [] for key in DEFAULT_CATEGORIES}
    if categories.get("documents", True):
        sources["documents"] = [documents, desktop, downloads / "LiDrop", documents / "LiLink Sync"]
    if categories.get("zen", True):
        sources["zen"] = zen_roots()
    if categories.get("mail", True):
        sources["mail"] = mail_roots()
    if categories.get("study", True):
        sources["study"] = [DATA_HOME / "limad-study", CONFIG_HOME / "limad-study"]
    if categories.get("notes", True):
        sources["notes"] = [DATA_HOME / "limad-notes", CONFIG_HOME / "limad-notes"]
    if categories.get("windows", True):
        sources["windows"] = [DATA_HOME / "limad-windows"]
    if categories.get("settings", True):
        sources["settings"] = [CONFIG_HOME / "limad", CONFIG_HOME / "gtk-3.0", CONFIG_HOME / "gtk-4.0", DATA_HOME / "applications", DATA_HOME / "fonts"]
    if categories.get("appsettings", True):
        sources["appsettings"] = [
            HOME / ".var/app/org.libreoffice.LibreOffice/config/libreoffice",
            HOME / ".var/app/com.github.wwmm.easyeffects/config/easyeffects",
            CONFIG_HOME / "libreoffice",
            CONFIG_HOME / "easyeffects",
            CONFIG_HOME / "autostart",
        ]
    return {key: [path for path in values if path.exists()] for key, values in sources.items()}


def analyze(categories: dict | None = None) -> dict:
    categories = {**DEFAULT_CATEGORIES, **(categories or {})}
    sources = category_sources(categories)
    sizes = {key: sum(directory_size(path, categories) for path in values) for key, values in sources.items()}
    return {
        "categories": sizes,
        "total": sum(sizes.values()),
        "sources": {key: [str(path) for path in values] for key, values in sources.items()},
        "backup_exclusions_applied": True,
    }


def command_json(args: list[str], default):
    result = run(args)
    if result.returncode:
        return default
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        return default


def flatpak_manifest() -> list[dict]:
    result = run(["flatpak", "list", "--app", "--columns=application,origin,version,installation"])
    apps = []
    if result.returncode:
        return apps
    for line in result.stdout.splitlines():
        fields = line.split("\t")
        if not fields or not fields[0].strip():
            continue
        apps.append({
            "id": fields[0].strip(),
            "origin": fields[1].strip() if len(fields) > 1 and fields[1].strip() else "flathub",
            "version": fields[2].strip() if len(fields) > 2 else "",
            "installation": fields[3].strip() if len(fields) > 3 else "user",
        })
    return apps


def dconf_exports(folder: Path) -> list[dict]:
    paths = [
        "/org/gnome/desktop/interface/",
        "/org/gnome/desktop/wm/preferences/",
        "/org/gnome/shell/",
        "/org/gnome/nautilus/preferences/",
        "/org/gnome/terminal/",
    ]
    folder.mkdir(parents=True, exist_ok=True)
    exported = []
    for index, dconf_path in enumerate(paths):
        result = run(["dconf", "dump", dconf_path])
        if result.returncode:
            continue
        target = folder / f"{index:02d}.ini"
        target.write_text(result.stdout, encoding="utf-8")
        exported.append({"path": dconf_path, "file": target.name})
    return exported


def study_root() -> Path:
    system = Path("/usr/share/limad-study")
    user = DATA_HOME / "limad-updater/apps/de.limad.Study/current/payload"
    selector = Path("/usr/local/libexec/limad-select-app-root")
    if selector.is_file():
        result = run([str(selector), str(system), str(user), "VERSION"])
        candidate = Path(result.stdout.strip()) if result.returncode == 0 else system
        if candidate.is_dir():
            return candidate
    return user if (user / "src").is_dir() else system


def export_study_backup(folder: Path) -> dict:
    folder.mkdir(parents=True, exist_ok=True)
    root = study_root()
    source = root / "src"
    if not source.is_dir():
        return {"ok": False, "error": "LiMaD-Study-Quellpfad fehlt"}
    sys.path.insert(0, str(source))
    try:
        from limad_study.backup import export_jwlibrary
        result = export_jwlibrary(folder)
        return {"ok": True, "result": result}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}
    finally:
        try:
            sys.path.remove(str(source))
        except ValueError:
            pass


def sanitize_lilink(stage: Path) -> None:
    settings = STATE_HOME / "limad-link/settings.json"
    if settings.is_file():
        value = load_json(settings, {})
        if isinstance(value, dict):
            save_json(stage / "lilink-settings.json", value)


def create_stage(categories: dict) -> tuple[Path, dict]:
    token = datetime.now().strftime("%Y%m%d-%H%M%S") + "-" + hashlib.sha256(os.urandom(32)).hexdigest()[:8]
    stage = SNAPSHOT_STAGE / token
    stage.mkdir(parents=True, exist_ok=False)
    sources = category_sources(categories)
    manifest = {
        "format": 1,
        "lisaveVersion": VERSION,
        "createdAt": now_iso(),
        "hostname": socket.gethostname(),
        "platform": platform.platform(),
        "home": str(HOME),
        "user": os.environ.get("USER", HOME.name),
        "categories": categories,
        "sources": {key: [str(path) for path in values] for key, values in sources.items()},
        "flatpaks": flatpak_manifest(),
        "aptManual": run(["apt-mark", "showmanual"]).stdout.splitlines() if shutil.which("apt-mark") else [],
        "osRelease": Path("/etc/os-release").read_text(encoding="utf-8", errors="replace") if Path("/etc/os-release").is_file() else "",
    }
    save_json(stage / "manifest.json", manifest)
    save_json(stage / "restore-plan.json", {"steps": ["system-update", "flatpaks", "user-data", "study", "settings", "verification"]})
    save_json(stage / "flatpaks.json", manifest["flatpaks"])
    dconf = dconf_exports(stage / "dconf") if categories.get("settings", True) else []
    save_json(stage / "dconf.json", dconf)
    if categories.get("study", True):
        save_json(stage / "study-export.json", export_study_backup(stage / "study"))
    if categories.get("windows", True):
        registry = DATA_HOME / "limad-windows/apps.json"
        if registry.is_file():
            (stage / "windows").mkdir(parents=True, exist_ok=True)
            shutil.copy2(registry, stage / "windows/apps.json")
    sanitize_lilink(stage)
    return stage, manifest


def exclusions(categories: dict, target: Path) -> list[str]:
    values = [
        str(target),
        "**/.cache/**",
        "**/cache/**",
        "**/Cache/**",
        "**/startupCache/**",
        "**/crashes/**",
        "**/shader-cache/**",
        "**/GPUCache/**",
        "**/Code Cache/**",
        "**/limad-study/publications/**",
        "**/limad-study/downloads/**",
        "**/limad-study/catalog/**",
        "**/limad-study/covers/**",
    ]
    if not categories.get("windows_full", False):
        values.extend([
            "**/limad-windows/prefix/**",
            "**/limad-windows/apps/*/prefix/**",
            "**/.var/app/com.usebottles.bottles/data/bottles/bottles/**",
            "**/limad-windows/cache/**",
        ])
    return values


def backup(target: Path, password: str, categories: dict | None = None, progress=None) -> dict:
    ensure_dependencies()
    if len(password) < 10:
        raise LiSaveError("Das Backup-Passwort muss mindestens zehn Zeichen lang sein.")
    categories = {**DEFAULT_CATEGORIES, **(categories or {})}
    archive = archive_path(target)
    legacy = bundle_path(target)
    ensure_external_target(archive)
    emit_progress(
        progress,
        "Backup-Ziel wird vorbereitet …",
        phase="prepare", phase_index=1, phase_total=6,
        source=str(HOME), target=str(archive),
    )

    existing_archive = archive.is_file()
    existing_legacy = legacy.is_dir()
    if existing_archive:
        workspace_parent = temporary_parent_for(archive)
        temporary_context = tempfile.TemporaryDirectory(prefix=".lisave-backup-", dir=workspace_parent)
        temporary = Path(temporary_context.__enter__())
        try:
            try:
                bundle = extract_backup_archive(archive, temporary, progress, phase_index=1, phase_total=6, target=archive)
            except LiSaveError:
                if not existing_legacy:
                    raise
                emit_progress(
                    progress,
                    "Beschädigtes ZIP wird durch den vorhandenen gültigen Backup-Ordner ersetzt …",
                    phase="prepare", phase_index=1, phase_total=6,
                    source=str(existing_legacy and legacy or archive), target=str(archive),
                )
            else:
                return _backup_into_bundle(bundle, archive, password, categories, progress)
        finally:
            temporary_context.__exit__(None, None, None)

    if existing_legacy:
        result = _backup_into_bundle(legacy, archive, password, categories, progress)
        emit_progress(
            progress,
            "Alter Backup-Ordner wurde erfolgreich in das portable ZIP-Format übernommen.",
            phase="complete", phase_index=6, phase_total=6, source=str(legacy), target=str(archive), fraction=1.0,
        )
        shutil.rmtree(legacy, ignore_errors=False)
        return result

    workspace_parent = temporary_parent_for(archive)
    with tempfile.TemporaryDirectory(prefix=".lisave-backup-", dir=workspace_parent) as temporary:
        bundle = Path(temporary) / legacy.name
        return _backup_into_bundle(bundle, archive, password, categories, progress)


def _backup_into_bundle(bundle: Path, archive: Path, password: str, categories: dict, progress=None) -> dict:
    ensure_repository(bundle, password)
    emit_progress(
        progress,
        "LiSave-Metadaten und Wiederherstellungsplan werden vorbereitet …",
        phase="prepare", phase_index=1, phase_total=6, source=str(HOME), target=str(archive),
    )
    stage, manifest = create_stage(categories)
    sources = category_sources(categories)
    all_sources = [path for values in sources.values() for path in values]
    all_sources.append(stage)
    exclude_file = stage / "exclude.txt"
    exclude_file.write_text("\n".join(exclusions(categories, archive)) + "\n", encoding="utf-8")
    source_summary = ", ".join(str(path) for path in all_sources[:3])
    if len(all_sources) > 3:
        source_summary += f" und {len(all_sources) - 3} weitere Quelle(n)"
    emit_progress(
        progress,
        "Persönliche Daten und Einstellungen werden verschlüsselt gesichert …",
        phase="backup", phase_index=2, phase_total=6,
        source=source_summary, target=str(repository_path(bundle)), fraction=0.0,
    )
    try:
        def on_backup_message(message: dict) -> None:
            message_type = message.get("message_type")
            if message_type == "status":
                done = int(message.get("bytes_done") or 0)
                total = int(message.get("total_bytes") or 0)
                seconds_elapsed = int(message.get("seconds_elapsed") or 0)
                speed = done / seconds_elapsed if done > 0 and seconds_elapsed > 0 else 0.0
                current_files = message.get("current_files") if isinstance(message.get("current_files"), list) else []
                current = str(current_files[0]) if current_files else ""
                fraction = float(message.get("percent_done") or 0.0)
                if total > 0:
                    fraction = max(0.0, min(1.0, done / total))
                emit_progress(
                    progress,
                    "Persönliche Daten und Einstellungen werden verschlüsselt gesichert …",
                    phase="backup", phase_index=2, phase_total=6,
                    source=source_for_item(current, all_sources[:-1], stage) if current else source_summary,
                    target=str(repository_path(bundle)), current=current or None, fraction=fraction,
                    bytes_done=done, bytes_total=total or None,
                    files_done=int(message.get("files_done") or 0), files_total=int(message.get("total_files") or 0) or None,
                    speed_bps=speed or None, seconds_remaining=int(message.get("seconds_remaining") or 0) if message.get("seconds_remaining") is not None else None,
                    errors=int(message.get("error_count") or 0),
                )
            elif message_type == "verbose_status":
                item = str(message.get("item") or "")
                if item:
                    emit_progress(
                        progress,
                        "Datei wird verschlüsselt gesichert …",
                        phase="backup", phase_index=2, phase_total=6,
                        source=source_for_item(item, all_sources[:-1], stage),
                        target=str(repository_path(bundle)), current=item,
                    )

        result = restic_json_stream(bundle, password, [
            "backup", "--json", "--tag", "lisave", "--tag", f"lisave-{VERSION}",
            "--exclude-file", str(exclude_file), *[str(path) for path in all_sources]
        ], on_backup_message)
        retention = load_config().get("retention", {"daily": 7, "weekly": 4, "monthly": 6})
        emit_progress(
            progress,
            "Alte Sicherungsstände werden nach der Aufbewahrungsregel bereinigt …",
            phase="retention", phase_index=3, phase_total=6,
            source=str(repository_path(bundle)), target=str(repository_path(bundle)),
        )
        restic(bundle, password, [
            "forget", "--tag", "lisave",
            "--keep-daily", str(int(retention.get("daily", 7))),
            "--keep-weekly", str(int(retention.get("weekly", 4))),
            "--keep-monthly", str(int(retention.get("monthly", 6))),
            "--prune"
        ], timeout=None)
        metadata = {
            "format": 2,
            "container": "zip",
            "name": archive.name,
            "lastBackup": now_iso(),
            "hostname": manifest["hostname"],
            "lisaveVersion": VERSION,
            "categories": categories,
        }
        save_json(bundle / "lisave.json", metadata)
        os.chmod(bundle / "lisave.json", 0o600)
        validate_bundle_files(bundle)
        emit_progress(
            progress,
            "Verschlüsseltes Repository wird geprüft …",
            phase="repository-check", phase_index=4, phase_total=6,
            source=str(repository_path(bundle)), target=str(archive),
        )
        restic(bundle, password, ["check"], timeout=None)
        write_backup_archive(bundle, archive, progress, phase_index=5, phase_total=6)
        report = {
            "ok": True,
            "bundle": str(archive),
            "createdAt": metadata["lastBackup"],
            "output": result.stdout,
            "analysis": analyze(categories),
        }
        REPORT_DIR.mkdir(parents=True, exist_ok=True)
        save_json(REPORT_DIR / f"backup-{datetime.now().strftime('%Y%m%d-%H%M%S')}.json", report)
        return report
    finally:
        shutil.rmtree(stage, ignore_errors=True)


def snapshot_list(bundle: Path, password: str) -> list[dict]:
    result = restic(bundle, password, ["snapshots", "--json", "--tag", "lisave"])
    try:
        values = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise LiSaveError("Sicherungsstände konnten nicht gelesen werden.") from exc
    return values if isinstance(values, list) else []


def latest_snapshot(bundle: Path, password: str) -> dict:
    snapshots = snapshot_list(bundle, password)
    if not snapshots:
        raise LiSaveError("Im ausgewählten LiSave-Backup wurde kein Sicherungsstand gefunden.")
    return max(snapshots, key=lambda item: item.get("time", ""))


def snapshot_restore_stats(bundle: Path, password: str, snapshot_id: str) -> tuple[int, int]:
    result = restic(bundle, password, ["stats", "--mode", "restore-size", "--json", snapshot_id], timeout=None)
    stats = None
    for line in reversed(result.stdout.splitlines()):
        try:
            value = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict) and "total_size" in value:
            stats = value
            break
    if stats is None:
        raise LiSaveError("Der Speicherbedarf des Sicherungsstands konnte nicht ermittelt werden.")
    total_size = int(stats.get("total_size") or 0)
    total_files = int(stats.get("total_file_count") or 0)
    if total_size <= 0:
        raise LiSaveError("Der Sicherungsstand meldet keine wiederherstellbaren Daten.")
    return total_size, total_files


def prepare_restore_workspace(restore_size: int) -> tuple[Path, int, int]:
    RESTORE_WORK_DIR.mkdir(parents=True, exist_ok=True)
    for candidate in RESTORE_WORK_DIR.glob("restore-*"):
        if candidate.is_dir():
            shutil.rmtree(candidate, ignore_errors=True)
    free = shutil.disk_usage(RESTORE_WORK_DIR).free
    reserve = max(1024 ** 3, restore_size // 10)
    required = restore_size * 2 + reserve
    if free < required:
        raise LiSaveError(
            "Nicht genügend freier Speicherplatz für die sichere Wiederherstellung. "
            f"Benötigt werden mindestens {required / (1024 ** 3):.1f} GB, "
            f"verfügbar sind {free / (1024 ** 3):.1f} GB."
        )
    return RESTORE_WORK_DIR, required, free


def restore_item_stats(source: Path) -> tuple[int, int]:
    if source.is_symlink():
        return 0, 1
    if source.is_file():
        try:
            return source.stat().st_size, 1
        except OSError:
            return 0, 1
    if not source.is_dir():
        return 0, 0
    total_bytes = 0
    total_files = 0
    for root, dirs, files in os.walk(source, followlinks=False):
        root_path = Path(root)
        for name in dirs:
            if (root_path / name).is_symlink():
                total_files += 1
        for name in files:
            path = root_path / name
            total_files += 1
            if path.is_symlink():
                continue
            try:
                total_bytes += path.stat().st_size
            except OSError:
                pass
    return total_bytes, total_files


def copy_item_with_progress(source: Path, destination: Path, state: dict, progress=None) -> None:
    def emit(current_source: Path, current_destination: Path, *, force: bool = False) -> None:
        now = time.monotonic()
        if not force and now - float(state.get("last_update", 0.0)) < 0.20:
            return
        done = int(state.get("bytes_done", 0))
        total = int(state.get("bytes_total", 0))
        speed, remaining = progress_metrics(float(state["started"]), done, total)
        emit_progress(
            progress,
            "Persönliche Daten werden in das neue Benutzerprofil übernommen …",
            phase="restore-copy", phase_index=6, phase_total=8,
            source=str(current_source), target=str(current_destination), current=str(current_destination),
            fraction=(done / total) if total else 1.0,
            bytes_done=done, bytes_total=total or None,
            files_done=int(state.get("files_done", 0)), files_total=int(state.get("files_total", 0)) or None,
            speed_bps=speed or None, seconds_remaining=remaining,
        )
        state["last_update"] = now

    def copy_file(src: Path, dst: Path) -> None:
        dst.parent.mkdir(parents=True, exist_ok=True)
        if dst.exists() and dst.is_dir():
            shutil.rmtree(dst)
        elif dst.exists() or dst.is_symlink():
            dst.unlink()
        if src.is_symlink():
            dst.symlink_to(os.readlink(src))
            state["files_done"] = int(state.get("files_done", 0)) + 1
            emit(src, dst)
            return
        shutil.copy2(src, dst)
        try:
            state["bytes_done"] = int(state.get("bytes_done", 0)) + src.stat().st_size
        except OSError:
            pass
        state["files_done"] = int(state.get("files_done", 0)) + 1
        emit(src, dst)

    if source.is_dir() and not source.is_symlink():
        destination.mkdir(parents=True, exist_ok=True)
        for root, dirs, files in os.walk(source, followlinks=False):
            root_path = Path(root)
            relative = root_path.relative_to(source)
            target_root = destination / relative
            target_root.mkdir(parents=True, exist_ok=True)
            kept_dirs = []
            for name in dirs:
                src_dir = root_path / name
                dst_dir = target_root / name
                if src_dir.is_symlink():
                    copy_file(src_dir, dst_dir)
                else:
                    dst_dir.mkdir(parents=True, exist_ok=True)
                    kept_dirs.append(name)
            dirs[:] = kept_dirs
            for name in files:
                copy_file(root_path / name, target_root / name)
    elif source.exists() or source.is_symlink():
        copy_file(source, destination)
    emit(source, destination, force=True)


def copy_item(source: Path, destination: Path) -> None:
    total_bytes, total_files = restore_item_stats(source)
    state = {
        "started": time.monotonic(),
        "bytes_done": 0,
        "bytes_total": total_bytes,
        "files_done": 0,
        "files_total": total_files,
        "last_update": 0.0,
    }
    copy_item_with_progress(source, destination, state, None)


def install_flatpaks(apps: list[dict], progress: Callable[[str], None] | None = None) -> list[dict]:
    failures = []
    if not shutil.which("flatpak"):
        return [{"id": item.get("id", ""), "error": "Flatpak fehlt"} for item in apps]
    remotes = run(["flatpak", "remotes", "--user", "--columns=name"]).stdout.splitlines()
    if "flathub" not in remotes:
        run(["flatpak", "remote-add", "--user", "--if-not-exists", "flathub", "https://dl.flathub.org/repo/flathub.flatpakrepo"])
    for item in apps:
        app_id = str(item.get("id") or "").strip()
        if not app_id:
            continue
        if progress:
            progress(f"Programm wird aus dem Internet installiert: {app_id}")
        if run(["flatpak", "info", "--user", app_id]).returncode == 0 or run(["flatpak", "info", "--system", app_id]).returncode == 0:
            continue
        remote = str(item.get("origin") or "flathub")
        result = run(["flatpak", "install", "--user", "--noninteractive", "-y", remote, app_id])
        if result.returncode:
            result = run(["flatpak", "install", "--user", "--noninteractive", "-y", "flathub", app_id])
        if result.returncode:
            failures.append({"id": app_id, "error": result.stdout.strip()})
    return failures


def stop_apps() -> None:
    for app_id in ("app.zen_browser.zen", "io.github.zen_browser.zen", "org.mozilla.thunderbird_esr", "org.mozilla.thunderbird", "org.mozilla.Thunderbird"):
        run(["flatpak", "kill", app_id])
    run(["pkill", "-f", "limad-study"])
    run(["pkill", "-f", "limad-notes"])


def restore_dconf(stage: Path) -> list[str]:
    failures = []
    entries = load_json(stage / "dconf.json", [])
    for item in entries if isinstance(entries, list) else []:
        path = str(item.get("path") or "")
        source = stage / str(item.get("file") or "")
        if not path.startswith("/") or not source.is_file():
            continue
        result = run(["dconf", "load", path], input_text=source.read_text(encoding="utf-8"))
        if result.returncode:
            failures.append(path)
    return failures


def find_stage(restore_root: Path) -> Path:
    matches = []
    for candidate in restore_root.rglob("manifest.json"):
        parts = candidate.parts
        marker = (".local", "state", "limad-save", "snapshots")
        if any(tuple(parts[index:index + len(marker)]) == marker for index in range(len(parts) - len(marker) + 1)):
            matches.append(candidate)
    if not matches:
        raise LiSaveError("Das LiSave-Manifest fehlt im Sicherungsstand.")
    return max(matches, key=lambda path: path.stat().st_mtime).parent


def restore(target: Path, password: str, categories: dict | None = None, progress: Callable[[str], None] | None = None) -> dict:
    ensure_dependencies()
    categories = {**DEFAULT_CATEGORIES, **(categories or {})}
    phase_total = 8
    emit_progress(
        progress,
        "Backup-Container wird geöffnet …",
        phase="restore-open", phase_index=1, phase_total=phase_total,
        source=str(target), target="Temporärer LiSave-Arbeitsbereich",
    )
    with opened_backup(target, progress, phase_index=1, phase_total=phase_total) as bundle:
        emit_progress(
            progress,
            "Verschlüsseltes Backup wird vor der Wiederherstellung geprüft …",
            phase="restore-check", phase_index=2, phase_total=phase_total,
            source=str(repository_path(bundle)), target=str(repository_path(bundle)),
        )
        restic(bundle, password, ["check"], timeout=None)
        snapshot = latest_snapshot(bundle, password)
        snapshot_id = str(snapshot.get("id") or "")
        if not snapshot_id:
            raise LiSaveError("Der Sicherungsstand besitzt keine gültige Snapshot-ID.")
        restore_size, restore_files = snapshot_restore_stats(bundle, password, snapshot_id)
        workspace_parent, required_free, available_free = prepare_restore_workspace(restore_size)
        emit_progress(
            progress,
            "Speicherplatz für die sichere Wiederherstellung wurde geprüft.",
            phase="restore-snapshot", phase_index=3, phase_total=phase_total,
            source=f"Snapshot {snapshot_id}", target=str(workspace_parent), fraction=0.0,
            bytes_done=0, bytes_total=restore_size, files_done=0, files_total=restore_files or None,
            current=f"Benötigt mindestens {required_free / (1024 ** 3):.1f} GB · verfügbar {available_free / (1024 ** 3):.1f} GB",
        )
        with tempfile.TemporaryDirectory(prefix="restore-", dir=workspace_parent) as temporary:
            restore_root = Path(temporary)
            restore_state = {
                "bytes_done": 0, "bytes_total": restore_size, "files_done": 0, "files_total": restore_files,
                "speed_bps": 0.0, "seconds_remaining": None, "current": "",
            }
            emit_progress(
                progress,
                "Sicherungsstand wird vollständig in einen temporären Bereich wiederhergestellt …",
                phase="restore-snapshot", phase_index=3, phase_total=phase_total,
                source=f"Snapshot {snapshot.get('id', '')}", target=str(restore_root), fraction=0.0,
            )

            def on_restore_message(message: dict) -> None:
                message_type = message.get("message_type")
                if message_type == "status":
                    done = int(message.get("bytes_restored") or 0)
                    total = int(message.get("total_bytes") or 0)
                    elapsed = float(message.get("seconds_elapsed") or 0)
                    speed = done / elapsed if done > 0 and elapsed > 0 else 0.0
                    remaining = int((total - done) / speed) if speed > 0 and total >= done else None
                    restore_state.update({
                        "bytes_done": done, "bytes_total": total,
                        "files_done": int(message.get("files_restored") or 0),
                        "files_total": int(message.get("total_files") or 0),
                        "speed_bps": speed, "seconds_remaining": remaining,
                    })
                elif message_type == "verbose_status":
                    item = str(message.get("item") or "")
                    if item:
                        restore_state["current"] = item
                else:
                    return
                done = int(restore_state["bytes_done"])
                total = int(restore_state["bytes_total"])
                emit_progress(
                    progress,
                    "Sicherungsstand wird vollständig in einen temporären Bereich wiederhergestellt …",
                    phase="restore-snapshot", phase_index=3, phase_total=phase_total,
                    source=f"Snapshot {snapshot.get('id', '')}", target=str(restore_root),
                    current=str(restore_state.get("current") or "") or None,
                    fraction=(done / total) if total else float(message.get("percent_done") or 0.0),
                    bytes_done=done, bytes_total=total or None,
                    files_done=int(restore_state["files_done"]), files_total=int(restore_state["files_total"]) or None,
                    speed_bps=float(restore_state["speed_bps"]) or None,
                    seconds_remaining=restore_state["seconds_remaining"],
                )

            restore_environment = os.environ.copy()
            restore_environment["TMPDIR"] = str(workspace_parent)
            restic_json_stream(
                bundle, password,
                ["restore", snapshot_id, "--target", str(restore_root), "--json", "--verbose=2"],
                on_restore_message, env=restore_environment,
            )
            emit_progress(
                progress,
                "Temporäre Wiederherstellung wird validiert und vorbereitet …",
                phase="restore-plan", phase_index=4, phase_total=phase_total,
                source=str(restore_root), target=str(HOME),
            )
            stage = find_stage(restore_root)
            manifest = load_json(stage / "manifest.json", {})
            old_home = Path(str(manifest.get("home") or ""))
            if not old_home.is_absolute() or old_home == Path("/"):
                raise LiSaveError("Ungültiger Benutzerpfad im LiSave-Manifest.")
            restored_home = restore_root / old_home.relative_to("/")
            apps = manifest.get("flatpaks", []) if isinstance(manifest, dict) else []
            emit_progress(
                progress,
                "Benötigte Programme werden geprüft und bei Bedarf installiert …",
                phase="restore-apps", phase_index=5, phase_total=phase_total,
                source="Gesicherter Programmplan", target="Benutzerinstallation",
            )
            app_progress = lambda message: emit_progress(
                progress, str(message), phase="restore-apps", phase_index=5, phase_total=phase_total,
                source="Flathub", target="Benutzerinstallation", current=str(message),
            )
            flatpak_failures = install_flatpaks(apps if isinstance(apps, list) else [], app_progress)
            stop_apps()
            restored = []
            source_map = manifest.get("sources", {}) if isinstance(manifest, dict) else {}
            restore_items = []
            for category, enabled in categories.items():
                if not enabled or category == "windows_full":
                    continue
                for original in source_map.get(category, []) if isinstance(source_map, dict) else []:
                    original_path = Path(str(original))
                    try:
                        relative = original_path.relative_to(old_home)
                    except ValueError:
                        continue
                    source = restored_home / relative
                    destination = HOME / relative
                    if source.exists() or source.is_symlink():
                        restore_items.append((source, destination))
            total_bytes = 0
            total_files = 0
            for source, _destination in restore_items:
                item_bytes, item_files = restore_item_stats(source)
                total_bytes += item_bytes
                total_files += item_files
            copy_state = {
                "started": time.monotonic(),
                "bytes_done": 0, "bytes_total": total_bytes,
                "files_done": 0, "files_total": total_files,
                "last_update": 0.0,
            }
            emit_progress(
                progress,
                "Persönliche Daten werden in das neue Benutzerprofil übernommen …",
                phase="restore-copy", phase_index=6, phase_total=phase_total,
                source=str(restored_home), target=str(HOME), fraction=0.0,
                bytes_done=0, bytes_total=total_bytes or None, files_done=0, files_total=total_files or None,
            )
            for source, destination in restore_items:
                copy_item_with_progress(source, destination, copy_state, progress)
                restored.append(str(destination))
            emit_progress(
                progress,
                "System- und App-Einstellungen werden übernommen …",
                phase="restore-settings", phase_index=7, phase_total=phase_total,
                source=str(stage), target=str(HOME),
            )
            dconf_failures = restore_dconf(stage) if categories.get("settings", True) else []
            study_import = ""
            if categories.get("study", True) and not (DATA_HOME / "limad-study/study.db").is_file():
                backups = list((stage / "study").glob("*.jwlibrary"))
                if backups:
                    result = run(["/usr/local/bin/limad-study", str(backups[-1]), "--prepare-only"], timeout=None)
                    if result.returncode:
                        study_import = result.stdout.strip()
            if Path("/usr/local/bin/limad-user-folders-setup").is_file():
                run(["/usr/local/bin/limad-user-folders-setup"])
            if Path("/usr/local/bin/limad-zen-deutsch-setup").is_file():
                run(["/usr/local/bin/limad-zen-deutsch-setup"])
            windows_pending = []
            windows_file = stage / "windows/apps.json"
            if categories.get("windows", True) and windows_file.is_file():
                values = load_json(windows_file, [])
                if isinstance(values, list):
                    windows_pending = [str(item.get("name") or item.get("exe") or "Windows-Programm") for item in values if isinstance(item, dict)]
            emit_progress(
                progress,
                "Wiederherstellung wird abgeschlossen und protokolliert …",
                phase="restore-complete", phase_index=8, phase_total=phase_total,
                source=str(HOME), target=str(REPORT_DIR), fraction=1.0,
                bytes_done=total_bytes, bytes_total=total_bytes or None,
                files_done=total_files, files_total=total_files or None, seconds_remaining=0,
            )
            report = {
                "ok": True,
                "restoredAt": now_iso(),
                "snapshot": snapshot.get("id"),
                "restored": restored,
                "flatpakFailures": flatpak_failures,
                "dconfFailures": dconf_failures,
                "studyImportError": study_import,
                "windowsProgramsPrepared": windows_pending,
            }
            REPORT_DIR.mkdir(parents=True, exist_ok=True)
            report_path = REPORT_DIR / f"restore-{datetime.now().strftime('%Y%m%d-%H%M%S')}.json"
            save_json(report_path, report)
            report["report"] = str(report_path)
            return report

def verify(target: Path, password: str, full: bool = False) -> dict:
    with opened_backup(target) as bundle:
        args = ["check"]
        if full:
            args.append("--read-data")
        result = restic(bundle, password, args, timeout=None)
        return {"ok": True, "output": result.stdout}


def configure_automatic(target: Path, password: str, categories: dict, enabled: bool, before_update: bool = True) -> dict:
    archive = archive_path(target)
    ensure_external_target(archive)
    try:
        selected = resolve_existing_backup(target)
    except LiSaveError:
        selected = None
    if selected is not None:
        with opened_backup(selected) as bundle:
            restic(bundle, password, ["snapshots", "--json"], timeout=120)
    config = load_config()
    config.update({
        "bundle": str(archive),
        "categories": {**DEFAULT_CATEGORIES, **categories},
        "automatic": bool(enabled),
        "before_update": bool(before_update),
        "updatedAt": now_iso(),
    })
    save_config(config)
    if enabled or before_update:
        secret_store(archive, password)
    if enabled:
        run(["systemctl", "--user", "daemon-reload"])
        result = run(["systemctl", "--user", "enable", "--now", "limad-save.timer"])
        if result.returncode:
            raise LiSaveError(result.stdout.strip() or "Automatische Sicherung konnte nicht aktiviert werden.")
    else:
        run(["systemctl", "--user", "disable", "--now", "limad-save.timer"])
    return config


def scheduled(mode: str = "timer", progress: Callable[[str], None] | None = None) -> dict:
    config = load_config()
    if mode == "timer" and not config.get("automatic"):
        return {"ok": True, "skipped": "automatic-disabled"}
    if mode == "pre-update" and not config.get("before_update", True):
        return {"ok": True, "skipped": "pre-update-disabled"}
    bundle_value = str(config.get("bundle") or "")
    if not bundle_value:
        return {"ok": True, "skipped": "not-configured"}
    configured = Path(bundle_value)
    parent = configured.parent
    if not parent.exists():
        return {"ok": True, "skipped": "target-not-connected"}
    password = secret_lookup(configured)
    if not password and configured.name.endswith(".lisavebackup.zip"):
        password = secret_lookup(configured.with_name(configured.name[:-4]))
    if not password:
        raise LiSaveError("Das LiSave-Passwort ist im GNOME-Schlüsselbund nicht verfügbar.")
    result = backup(configured, password, config.get("categories", {}), progress)
    active = Path(result["bundle"])
    if str(active) != bundle_value:
        config["bundle"] = str(active)
        config["updatedAt"] = now_iso()
        save_config(config)
        secret_store(active, password)
    return result
