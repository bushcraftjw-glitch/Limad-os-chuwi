#!/usr/bin/python3
from __future__ import annotations

import json
import os
import shutil
import ssl
import subprocess
import tempfile
import time
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VENDOR = ROOT / '.cache/vendor/LiMaD-Programme-BASE1B-EXTRAKT.zip'
STRIP = ROOT / 'tools/strip-lidrop-airdrop.py'
REASSEMBLE = ROOT / 'tools/reassemble-vendor.sh'
SERVICE = ROOT / 'build/rootfs/usr/lib/systemd/user/limad-link.service'
HEALTH = ROOT / 'build/rootfs/usr/local/bin/limad-link-health-check'
STATUS = ROOT / 'build/rootfs/usr/local/bin/limad-link-status-ensure'
EXTENSION = ROOT / 'build/rootfs/usr/share/gnome-shell/extensions/lilink@limad.local/extension.js'
RUNTIME_DEPS = ROOT / 'build/rootfs/usr/local/bin/limad-runtime-deps'


def assert_no_airdrop(text: str, label: str) -> None:
    lowered = text.casefold()
    for token in ('airdrop', 'opendrop', 'awdl', 'owl'):
        if token in lowered:
            raise AssertionError(f'{label}: forbidden AirDrop token remains: {token}')


def daemon_smoke(link_root: Path) -> None:
    with tempfile.TemporaryDirectory(prefix='lilink-smoke-') as td:
        tmp = Path(td)
        runtime = tmp / 'runtime'
        data = tmp / 'data'
        home = tmp / 'home'
        runtime.mkdir()
        data.mkdir()
        home.mkdir()
        env = os.environ.copy()
        env.update({
            'HOME': str(home),
            'XDG_RUNTIME_DIR': str(runtime),
            'XDG_DATA_HOME': str(data),
            'PYTHONPATH': str(link_root),
        })
        proc = subprocess.Popen(
            ['/usr/bin/python3', str(link_root / 'daemon.py')],
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        try:
            runtime_file = runtime / 'limad-link.json'
            deadline = time.monotonic() + 12
            info = None
            while time.monotonic() < deadline:
                if runtime_file.is_file():
                    try:
                        info = json.loads(runtime_file.read_text(encoding='utf-8'))
                        if info.get('port'):
                            break
                    except Exception:
                        pass
                if proc.poll() is not None:
                    output = proc.stdout.read() if proc.stdout else ''
                    raise AssertionError(f'LiLink daemon exited during smoke test: {output}')
                time.sleep(0.2)
            if not info:
                raise AssertionError('LiLink daemon did not create runtime state')
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            with urllib.request.urlopen(f"https://127.0.0.1:{int(info['port'])}/api/health", context=ctx, timeout=2) as response:
                value = json.loads(response.read().decode('utf-8'))
            if not value.get('ok') or value.get('version') != '1.0.0-preview3':
                raise AssertionError(f'LiLink health response invalid: {value!r}')
        finally:
            proc.terminate()
            try:
                proc.wait(timeout=4)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait(timeout=4)


def main() -> int:
    if not VENDOR.is_file():
        subprocess.run([str(REASSEMBLE)], check=True)
    if not VENDOR.is_file():
        raise AssertionError('Vendor programs ZIP could not be reassembled')
    service = SERVICE.read_text(encoding='utf-8')
    if 'ExecStart=/usr/bin/python3 /usr/share/limad-link/daemon.py' not in service or 'WantedBy=default.target' not in service:
        raise AssertionError('LiLink systemd user service is incomplete')
    if 'systemctl --user enable --now limad-link.service' not in HEALTH.read_text(encoding='utf-8'):
        raise AssertionError('LiLink health helper does not enable/start service')
    if '/usr/local/bin/limad-link-health-check' not in STATUS.read_text(encoding='utf-8'):
        raise AssertionError('LiLink status integration does not verify backend health')
    if 'systemctl --user start limad-link.service' not in EXTENSION.read_text(encoding='utf-8'):
        raise AssertionError('LiLink GNOME extension does not start backend service')
    deps = RUNTIME_DEPS.read_text(encoding='utf-8')
    for package in ('avahi-utils', 'deskflow', 'freerdp-x11', 'gnome-remote-desktop', 'openssl'):
        if package not in deps:
            raise AssertionError(f'LiLink runtime dependency missing: {package}')

    with tempfile.TemporaryDirectory(prefix='lidrop-scope-') as td:
        temp = Path(td)
        with zipfile.ZipFile(VENDOR) as archive:
            archive.extractall(temp)
        rootfs = temp / 'LiMaD-Programme-BASE1B-EXTRAKT/filesystem'
        subprocess.run(['/usr/bin/python3', '-B', str(STRIP), str(rootfs)], check=True)
        for path in (
            rootfs / 'usr/share/limad-drop/web/app.js',
            rootfs / 'usr/share/limad-drop/limad_dropd.py',
        ):
            assert_no_airdrop(path.read_text(encoding='utf-8'), str(path))
        for removed in (
            'limad-airdrop-check', 'limad-airdrop-control', 'limad-airdrop-session',
            'limad-airdrop-wait', 'limad-opendrop-receive',
        ):
            if (rootfs / 'usr/local/bin' / removed).exists():
                raise AssertionError(f'AirDrop helper remains: {removed}')
        for retained in (
            rootfs / 'usr/local/bin/limad-drop',
            rootfs / 'usr/local/bin/limad-dropd',
            rootfs / 'usr/share/limad-drop/limad_dropd.py',
            rootfs / 'usr/share/limad-drop/web/app.js',
            rootfs / 'usr/share/limad-link/app.py',
            rootfs / 'usr/share/limad-link/daemon.py',
            rootfs / 'usr/share/limad-link/common.py',
        ):
            if not retained.is_file():
                raise AssertionError(f'Required LiDrop/LiLink component missing: {retained}')
        subprocess.run(['/usr/bin/python3', '-m', 'py_compile', str(rootfs / 'usr/share/limad-drop/limad_dropd.py')], check=True)
        subprocess.run(['/usr/bin/python3', '-m', 'py_compile', str(rootfs / 'usr/share/limad-link/app.py'), str(rootfs / 'usr/share/limad-link/daemon.py'), str(rootfs / 'usr/share/limad-link/common.py')], check=True)
        daemon_smoke(rootfs / 'usr/share/limad-link')

    print('LILINK + LIDROP SCOPE TEST: PASS')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
