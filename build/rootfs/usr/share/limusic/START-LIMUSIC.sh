#!/usr/bin/bash
set -euo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
STATE_DIR="${XDG_STATE_HOME:-$HOME/.local/state}/limusic"
LOG_FILE="$STATE_DIR/launcher.log"
mkdir -p "$STATE_DIR"

check_namespace() {
    local namespace="$1"
    local version="$2"
    python3 - "$namespace" "$version" <<'PY'
import gi
import sys

gi.require_version(sys.argv[1], sys.argv[2])
module = __import__("gi.repository", fromlist=[sys.argv[1]])
getattr(module, sys.argv[1])
PY
}

missing=0

if ! command -v python3 >/dev/null 2>&1; then
    echo "ERROR: python3 is missing."
    missing=1
fi

if (( missing == 0 )); then
    for spec in "Gtk:4.0" "Gdk:4.0" "Gst:1.0" "WebKit:6.0" "Pango:1.0"; do
        namespace="${spec%%:*}"
        version="${spec##*:}"
        if ! check_namespace "$namespace" "$version" >/dev/null 2>&1; then
            echo "ERROR: GI namespace ${namespace} ${version} is not available."
            missing=1
        fi
    done
fi

if (( missing != 0 )); then
    echo
    echo "LiMusic cannot start because required native runtime components are missing."
    echo "Run: ./diagnose.sh"
    exit 1
fi

if command -v gst-inspect-1.0 >/dev/null 2>&1; then
    if ! gst-inspect-1.0 playbin3 >/dev/null 2>&1 && ! gst-inspect-1.0 playbin >/dev/null 2>&1; then
        echo "ERROR: GStreamer playbin3/playbin is not available."
        echo "Run: ./diagnose.sh"
        exit 1
    fi
    if ! gst-inspect-1.0 gtk4paintablesink >/dev/null 2>&1; then
        echo "WARNING: gtk4paintablesink is missing. Audio can work, native in-window video cannot be rendered by this preview."
    fi
fi

export PYTHONPATH="$ROOT/src${PYTHONPATH:+:$PYTHONPATH}"

echo "LiMusic 0.3.22 Native Preview"
echo "Runtime: GTK4 + WebKitGTK 6 + GStreamer"
echo "Log: $LOG_FILE"
echo

set +e
python3 -m limusic 2>&1 | tee -a "$LOG_FILE"
status=${PIPESTATUS[0]}
set -e

if (( status != 0 )); then
    echo
    echo "ERROR: LiMusic exited with status $status."
    echo "Diagnostics: $ROOT/diagnose.sh"
    if [[ -t 0 ]]; then
        read -r -p "Press Enter to close..." _
    fi
fi

exit "$status"
