#!/usr/bin/python3
from __future__ import annotations

import pathlib
import sys


def patch_exact(path: pathlib.Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    if new in text:
        return
    if text.count(old) != 1:
        raise SystemExit(f"ERROR: V22 titlebar anchor mismatch: {path}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def main() -> int:
    if len(sys.argv) != 2:
        raise SystemExit("Usage: patch-v22-titlebars.py ROOTFS")
    rootfs = pathlib.Path(sys.argv[1])

    notes = rootfs / "usr/share/limad-notes/app.py"
    windows_apps = rootfs / "usr/share/limad-windows/installer.py"
    if not notes.is_file() or not windows_apps.is_file():
        raise SystemExit("ERROR: LiNotes or Windows-Programme source is missing")

    patch_exact(
        notes,
        "        header = Gtk.HeaderBar()\n        header.add_css_class(\"linotes-header\")\n",
        "        header = Gtk.HeaderBar()\n"
        "        header.set_show_title_buttons(True)\n"
        "        header.set_decoration_layout(\"close,maximize,minimize:\")\n"
        "        header.add_css_class(\"linotes-header\")\n",
    )
    patch_exact(
        windows_apps,
        "        header = Adw.HeaderBar()\n        self.switcher = Adw.ViewSwitcher(stack=self.stack, policy=Adw.ViewSwitcherPolicy.WIDE)\n",
        "        header = Adw.HeaderBar()\n"
        "        header.set_decoration_layout(\"close,maximize,minimize:\")\n"
        "        header.set_show_start_title_buttons(True)\n"
        "        header.set_show_end_title_buttons(False)\n"
        "        self.switcher = Adw.ViewSwitcher(stack=self.stack, policy=Adw.ViewSwitcherPolicy.WIDE)\n",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
