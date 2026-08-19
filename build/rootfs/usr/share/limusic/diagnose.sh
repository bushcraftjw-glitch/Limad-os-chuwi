#!/usr/bin/bash
set -euo pipefail

STATE_DIR="${XDG_STATE_HOME:-$HOME/.local/state}/limusic"

echo "=== LiMusic ==="
echo "Version: 0.3.22"
echo

echo "=== OS ==="
cat /etc/os-release 2>/dev/null || true
rpm-ostree status 2>/dev/null || true

echo
echo "=== Python / GI ==="
python3 --version 2>&1 || true
python3 - <<'PY' 2>&1 || true
import gi
for namespace, version in (("Gtk", "4.0"), ("Gdk", "4.0"), ("Gst", "1.0"), ("WebKit", "6.0")):
    try:
        gi.require_version(namespace, version)
        module = __import__("gi.repository", fromlist=[namespace])
        getattr(module, namespace)
        print(f"{namespace} {version}: OK")
    except Exception as exc:
        print(f"{namespace} {version}: ERROR: {exc}")
PY

echo
echo "=== GStreamer ==="
gst-inspect-1.0 --version 2>&1 || true
if gst-inspect-1.0 playbin3 >/dev/null 2>&1; then
    echo "playbin3: OK"
else
    echo "playbin3: MISSING"
fi
if gst-inspect-1.0 playbin >/dev/null 2>&1; then
    echo "playbin: OK"
else
    echo "playbin: MISSING"
fi
if gst-inspect-1.0 gtk4paintablesink >/dev/null 2>&1; then
    echo "gtk4paintablesink: OK"
else
    echo "gtk4paintablesink: MISSING"
fi

echo
echo "=== Display ==="
echo "XDG_SESSION_TYPE=${XDG_SESSION_TYPE:-}"
echo "WAYLAND_DISPLAY=${WAYLAND_DISPLAY:-}"
echo "DISPLAY=${DISPLAY:-}"

echo
echo "=== Security ==="
getenforce 2>/dev/null || true
ausearch -m avc -ts recent 2>/dev/null | tail -n 80 || true

echo
echo "=== User services ==="
systemctl --user status xdg-desktop-portal.service --no-pager 2>/dev/null || true

echo
echo "=== Journal ==="
journalctl --user -b --no-pager -n 120 2>/dev/null || true

echo
echo "=== LiMusic logs ==="
tail -n 160 "$STATE_DIR/launcher.log" 2>/dev/null || true
tail -n 160 "$STATE_DIR/limusic.log" 2>/dev/null || true
