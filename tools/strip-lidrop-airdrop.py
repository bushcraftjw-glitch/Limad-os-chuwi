#!/usr/bin/python3
from __future__ import annotations

import argparse
import re
from pathlib import Path


def replace_once(text: str, old: str, new: str, label: str) -> str:
    if text.count(old) != 1:
        raise RuntimeError(f"{label}: expected exactly one match, found {text.count(old)}")
    return text.replace(old, new, 1)


def replace_first(text: str, old: str, new: str, label: str) -> str:
    if old not in text:
        raise RuntimeError(f"{label}: match not found")
    return text.replace(old, new, 1)


def strip_app_js(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    text = re.sub(
        r"\n\s*<details class=\"settings-block advanced-block\"><summary>AirDrop-Kompatibilität</summary>.*?</details>",
        "",
        text,
        count=1,
    )
    block = """  $('#airdropApply').onclick = applyAirDrop;\n  $('#airdropRecheck').onclick = async () => {\n    const button = $('#airdropRecheck');\n    button.disabled = true;\n    try {\n      const result = await api('/api/admin/airdrop', { method: 'POST', json: { enabled: $('#airdropEnabled').checked, visibility: $('#airdropVisibility').value } });\n      renderAirDrop(result.airdrop);\n      toast('AirDrop wurde neu geprüft.');\n    } catch (error) { toast(error.message, true); }\n    finally { button.disabled = false; }\n  };\n"""
    text = replace_once(text, block, "", "LiDrop AirDrop event bindings")
    text, count = re.subn(
        r"\nfunction renderAirDrop\(airdrop\) \{.*?\n\}\n\nasync function applyAirDrop\(\) \{.*?\n\}\n",
        "\n",
        text,
        count=1,
        flags=re.S,
    )
    if count != 1:
        raise RuntimeError(f"LiDrop AirDrop functions: expected one block, found {count}")
    text = replace_once(text, "  renderAirDrop(current.airdrop || {});\n", "", "LiDrop AirDrop render call")
    if re.search(r"airdrop|AirDrop", text, re.I):
        raise RuntimeError("LiDrop web app still contains AirDrop references")
    path.write_text(text, encoding="utf-8")


def strip_daemon(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    text = replace_first(text, "        self._airdrop_probe_cache = None\n        self._airdrop_probe_at = 0.0\n", "", "LiDrop AirDrop cache init")
    text, count = re.subn(
        r"\n    def airdrop_config_path\(self\):.*?\n    def rotate_pairing\(self\):",
        "\n    def rotate_pairing(self):",
        text,
        count=1,
        flags=re.S,
    )
    if count != 1:
        raise RuntimeError(f"LiDrop AirDrop daemon methods: expected one block, found {count}")
    text = replace_once(
        text,
        '                return self._send(data={"ok": True, **STORE.admin_state(), "airdrop": STORE.airdrop_state()})\n',
        '                return self._send(data={"ok": True, **STORE.admin_state()})\n',
        "LiDrop admin state AirDrop field",
    )
    post_block = '''            if path == "/api/admin/airdrop":\n                if not self._admin(): return\n                result = STORE.update_airdrop(self._json_body())\n                return self._send(data={"ok": True, "airdrop": result})\n'''
    text = replace_once(text, post_block, "", "LiDrop AirDrop API")
    if re.search(r"airdrop|AirDrop|opendrop|OpenDrop|\bAWDL\b|\bOWL\b", text):
        raise RuntimeError("LiDrop daemon still contains AirDrop backend references")
    path.write_text(text, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("rootfs", type=Path)
    args = parser.parse_args()
    rootfs = args.rootfs.resolve()
    drop = rootfs / "usr/share/limad-drop"
    strip_app_js(drop / "web/app.js")
    strip_daemon(drop / "limad_dropd.py")

    remove = [
        rootfs / "usr/local/bin/limad-opendrop-receive",
        rootfs / "usr/local/bin/limad-airdrop-session",
        rootfs / "usr/local/bin/limad-airdrop-check",
        rootfs / "usr/local/bin/limad-airdrop-control",
        rootfs / "usr/local/bin/limad-airdrop-wait",
        rootfs / "usr/share/polkit-1/rules.d/49-limad-airdrop.rules",
    ]
    for path in remove:
        path.unlink(missing_ok=True)

    for path in [
        rootfs / "usr/libexec/limad-airdrop",
        rootfs / "usr/local/libexec/limad-airdrop",
        rootfs / "usr/share/limad-drop/airdrop",
    ]:
        if path.exists():
            import shutil
            shutil.rmtree(path)

    for unit_dir in [rootfs / "usr/lib/systemd/user", rootfs / "etc/systemd/user", rootfs / "etc/systemd/system"]:
        if unit_dir.exists():
            for unit in unit_dir.glob("*airdrop*"):
                if unit.is_file() or unit.is_symlink():
                    unit.unlink()

    print("LIDROP AIRDROP REMOVAL: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
