#!/usr/bin/python3
import json
import os
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HELPER = ROOT / "build/rootfs/usr/local/bin/limad-zen-voltroute-bookmark"
REQUIRED_APPS = ROOT / "build/rootfs/usr/local/bin/limad-required-user-apps"

required_apps = REQUIRED_APPS.read_text(encoding="utf-8")
for token in (
    'ZEN_BOOKMARK_HELPER="${LIMAD_ZEN_BOOKMARK_HELPER:-/usr/local/bin/limad-zen-voltroute-bookmark}"',
    '"$ZEN_BOOKMARK_HELPER"',
):
    if token not in required_apps:
        raise AssertionError(f"Zen bookmark integration token missing: {token}")

with tempfile.TemporaryDirectory() as tmp:
    base = Path(tmp)
    fake_bin = base / "bin"
    fake_bin.mkdir()
    flatpak = fake_bin / "flatpak"
    flatpak.write_text(
        "#!/usr/bin/bash\n"
        "set -euo pipefail\n"
        "if [[ \"$*\" == \"info --user --show-ref app.zen_browser.zen\" ]]; then\n"
        "    printf '%s\\n' 'app/app.zen_browser.zen/x86_64/stable'\n"
        "    exit 0\n"
        "fi\n"
        "exit 1\n",
        encoding="utf-8",
    )
    flatpak.chmod(0o755)
    home = base / "home"
    data = base / "data"
    home.mkdir()
    data.mkdir()
    env = os.environ.copy()
    env["HOME"] = str(home)
    env["XDG_DATA_HOME"] = str(data)
    env["PATH"] = f"{fake_bin}:/usr/bin:/bin"
    subprocess.run([str(HELPER)], check=True, env=env)
    policy_file = data / "flatpak/extension/app.zen_browser.zen.systemconfig/x86_64/stable/policies/policies.json"
    policies = json.loads(policy_file.read_text(encoding="utf-8"))["policies"]
    if policies.get("DisableAppUpdate") is not True:
        raise AssertionError("Zen Flatpak DisableAppUpdate policy must be preserved")
    if policies.get("DontCheckDefaultBrowser") is not True:
        raise AssertionError("Zen Flatpak DontCheckDefaultBrowser policy must be preserved")
    expected = [{"Title": "Voltroute", "URL": "https://volteroute.netlify.app/", "Placement": "toolbar"}]
    if policies.get("Bookmarks") != expected:
        raise AssertionError("Voltroute Zen bookmark policy mismatch")

print("V30 ZEN VOLTROUTE BOOKMARK TEST: PASS")
