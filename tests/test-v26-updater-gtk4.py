#!/usr/bin/python3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
UPDATER = ROOT / "build/rootfs/usr/share/limad-updater/updater.py"
text = UPDATER.read_text(encoding="utf-8")

if ".set_message_type(" in text:
    raise AssertionError("LiMaD Updater still uses removed GTK4 MessageDialog.set_message_type()")
needle = 'dialog.set_property("message-type", Gtk.MessageType.ERROR if error else Gtk.MessageType.INFO)'
if needle not in text:
    raise AssertionError("LiMaD Updater GTK4 message-type property fix is missing")

compile(text, str(UPDATER), "exec")
print("V26 UPDATER GTK4 TEST: PASS")
