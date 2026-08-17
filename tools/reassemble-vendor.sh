#!/usr/bin/bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENDOR="$ROOT/assets/vendor"
OUT="$ROOT/.cache/vendor"
mkdir -p "$OUT"

source "$ROOT/config/build.env"

assemble() {
    local name="$1"
    local expected="$2"
    local output="$OUT/$name"
    local parts=("$VENDOR/$name.part-"*)

    if [ ! -e "${parts[0]}" ]; then
        echo "ERROR: Missing vendor parts for $name" >&2
        exit 1
    fi

    cat "${parts[@]}" > "$output"
    printf '%s  %s
' "$expected" "$output" | sha256sum -c -
}

assemble "LiMaD-Programme-BASE1B-EXTRAKT.zip" "$PROGRAMS_ZIP_SHA256"
assemble "LiMaD-OS-MASTER-ICON-THEME-V3.2-BUILD-READY.zip" "$ICONS_ZIP_SHA256"
assemble "LiMaD-4K-Hintergrundbilder-BASE1B.zip" "$WALLPAPERS_ZIP_SHA256"
