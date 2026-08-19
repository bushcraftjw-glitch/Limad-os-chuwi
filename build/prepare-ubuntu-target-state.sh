#!/usr/bin/bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ISO="${1:-}"
STATE_ROOT="$ROOT/.cache/ubuntu-target-state"
CATALOG="$STATE_ROOT/install-sources.yaml"
LAYER_DIR="$STATE_ROOT/layers"
MOUNT_DIR="$STATE_ROOT/mounts"
MERGED="$STATE_ROOT/merged"
UPPER="$STATE_ROOT/upper"
WORK="$STATE_ROOT/work"
STATUS="$STATE_ROOT/dpkg-status"

if [ -z "$ISO" ] || [ ! -f "$ISO" ]; then
    echo "ERROR: Ubuntu ISO missing for target-state preparation: $ISO" >&2
    exit 1
fi

for command in mount mountpoint python3 sudo umount xorriso; do
    if ! command -v "$command" >/dev/null 2>&1; then
        echo "ERROR: Required target-state command missing: $command" >&2
        exit 1
    fi
done

rm -rf "$STATE_ROOT"
mkdir -p "$LAYER_DIR" "$MOUNT_DIR" "$MERGED" "$UPPER" "$WORK"

xorriso -osirrox on -indev "$ISO" -extract /casper/install-sources.yaml "$CATALOG" >/dev/null 2>&1
mapfile -t LAYERS < <(python3 -B "$ROOT/tools/install-source-stack.py" "$CATALOG" --source-id ubuntu-desktop)
if [ "${#LAYERS[@]}" -eq 0 ]; then
    echo "ERROR: Ubuntu desktop install source has no filesystem layers." >&2
    exit 1
fi

LAYER_MOUNTS=()
cleanup() {
    if mountpoint -q "$MERGED"; then
        sudo umount "$MERGED"
    fi
    local index
    for ((index=${#LAYER_MOUNTS[@]}-1; index>=0; index--)); do
        if mountpoint -q "${LAYER_MOUNTS[$index]}"; then
            sudo umount "${LAYER_MOUNTS[$index]}"
        fi
    done
    sudo rm -rf "$MERGED" "$UPPER" "$WORK" "$MOUNT_DIR"
}
trap cleanup EXIT

for index in "${!LAYERS[@]}"; do
    relative="${LAYERS[$index]}"
    image="$LAYER_DIR/$(basename "$relative")"
    mount_dir="$MOUNT_DIR/$index"
    mkdir -p "$mount_dir"
    xorriso -osirrox on -indev "$ISO" -extract "/casper/$relative" "$image" >/dev/null 2>&1
    if [ ! -s "$image" ]; then
        echo "ERROR: Ubuntu target layer is missing or empty: /casper/$relative" >&2
        exit 1
    fi
    sudo mount -t squashfs -o loop,ro "$image" "$mount_dir"
    LAYER_MOUNTS+=("$mount_dir")
done

LOWERDIR=""
for ((index=${#LAYER_MOUNTS[@]}-1; index>=0; index--)); do
    if [ -n "$LOWERDIR" ]; then
        LOWERDIR+=":"
    fi
    LOWERDIR+="${LAYER_MOUNTS[$index]}"
done

sudo mount -t overlay overlay -o "lowerdir=$LOWERDIR,upperdir=$UPPER,workdir=$WORK" "$MERGED"
if [ ! -s "$MERGED/var/lib/dpkg/status" ]; then
    echo "ERROR: Ubuntu desktop target dpkg status is missing." >&2
    exit 1
fi
sudo cp "$MERGED/var/lib/dpkg/status" "$STATUS"
sudo chown "$(id -u):$(id -g)" "$STATUS"
chmod 0644 "$STATUS"

echo "Ubuntu desktop target state: PASS (${#LAYERS[@]} filesystem layers)"
