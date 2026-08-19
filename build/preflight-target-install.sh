#!/usr/bin/bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PAYLOAD="$ROOT/.cache/payload"
STATE_ROOT="$ROOT/.cache/ubuntu-target-state"
CATALOG="$STATE_ROOT/install-sources.yaml"
LAYER_DIR="$STATE_ROOT/layers"
PREFLIGHT_ROOT="$ROOT/.cache/target-preflight"
MOUNT_DIR="$PREFLIGHT_ROOT/mounts"
TARGET="$PREFLIGHT_ROOT/target"
UPPER="$PREFLIGHT_ROOT/upper"
WORK="$PREFLIGHT_ROOT/work"

for command in chroot mount mountpoint python3 sudo umount; do
    if ! command -v "$command" >/dev/null 2>&1; then
        echo "ERROR: Required target-preflight command missing: $command" >&2
        exit 1
    fi
done

if [ ! -d "$PAYLOAD/rootfs" ] || [ ! -x "$PAYLOAD/install-target.sh" ]; then
    echo "ERROR: Prepared LiMaD payload is missing." >&2
    exit 1
fi
if [ ! -r "$CATALOG" ] || [ ! -s "$STATE_ROOT/dpkg-status" ]; then
    echo "ERROR: Prepared Ubuntu desktop target state is missing." >&2
    exit 1
fi

mapfile -t LAYERS < <(python3 -B "$ROOT/tools/install-source-stack.py" "$CATALOG" --source-id ubuntu-desktop)
if [ "${#LAYERS[@]}" -eq 0 ]; then
    echo "ERROR: Ubuntu desktop target source has no filesystem layers." >&2
    exit 1
fi

rm -rf "$PREFLIGHT_ROOT"
mkdir -p "$MOUNT_DIR" "$TARGET" "$UPPER" "$WORK"

LAYER_MOUNTS=()
BIND_MOUNTS=()
cleanup() {
    local index
    for ((index=${#BIND_MOUNTS[@]}-1; index>=0; index--)); do
        if mountpoint -q "${BIND_MOUNTS[$index]}"; then
            sudo umount "${BIND_MOUNTS[$index]}"
        fi
    done
    if mountpoint -q "$TARGET"; then
        sudo umount "$TARGET"
    fi
    for ((index=${#LAYER_MOUNTS[@]}-1; index>=0; index--)); do
        if mountpoint -q "${LAYER_MOUNTS[$index]}"; then
            sudo umount "${LAYER_MOUNTS[$index]}"
        fi
    done
    sudo rm -rf "$PREFLIGHT_ROOT"
}
trap cleanup EXIT

for index in "${!LAYERS[@]}"; do
    image="$LAYER_DIR/$(basename "${LAYERS[$index]}")"
    mount_dir="$MOUNT_DIR/$index"
    if [ ! -s "$image" ]; then
        echo "ERROR: Prepared Ubuntu target layer is missing: $image" >&2
        exit 1
    fi
    mkdir -p "$mount_dir"
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
sudo mount -t overlay overlay -o "lowerdir=$LOWERDIR,upperdir=$UPPER,workdir=$WORK" "$TARGET"

sudo cp -a "$PAYLOAD/rootfs/." "$TARGET/"
sudo install -m 0755 "$PAYLOAD/install-target.sh" "$TARGET/tmp/limad-install-target.sh"

sudo mkdir -p "$TARGET/dev" "$TARGET/proc" "$TARGET/sys" "$TARGET/run"
sudo mount --bind /dev "$TARGET/dev"
BIND_MOUNTS+=("$TARGET/dev")
sudo mount -t proc proc "$TARGET/proc"
BIND_MOUNTS+=("$TARGET/proc")
sudo mount --bind /sys "$TARGET/sys"
BIND_MOUNTS+=("$TARGET/sys")
sudo mount --bind /run "$TARGET/run"
BIND_MOUNTS+=("$TARGET/run")

if [ -f "$TARGET/etc/apt/sources.list" ]; then
    sudo mv "$TARGET/etc/apt/sources.list" "$TARGET/etc/apt/sources.list.limad-preflight-disabled"
fi
sudo install -m 0644 /dev/null "$TARGET/etc/apt/sources.list"
if [ -d "$TARGET/etc/apt/sources.list.d" ]; then
    while IFS= read -r source_file; do
        sudo mv "$source_file" "$source_file.limad-preflight-disabled"
    done < <(find "$TARGET/etc/apt/sources.list.d" -maxdepth 1 -type f \( -name '*.list' -o -name '*.sources' \) -print)
fi

sudo tee "$TARGET/usr/sbin/policy-rc.d" >/dev/null <<'POLICY'
#!/bin/sh
exit 101
POLICY
sudo chmod 0755 "$TARGET/usr/sbin/policy-rc.d"

run_stage() {
    local stage="$1"
    local command="$2"

    echo "TARGET PREFLIGHT: $stage START"
    if ! sudo chroot "$TARGET" /usr/bin/bash -c "$command"; then
        echo "ERROR: TARGET PREFLIGHT failed in $stage" >&2
        return 1
    fi
    if ! sudo chroot "$TARGET" /usr/bin/apt-get check; then
        echo "ERROR: TARGET PREFLIGHT dependency check failed after $stage" >&2
        return 1
    fi
    echo "TARGET PREFLIGHT: $stage PASS"
}

run_stage LiView /usr/local/bin/limad-liview-deps
run_stage Gaming /usr/local/bin/limad-gaming-deps
run_stage GRUBENVOLK /usr/local/bin/limad-grubenvolk-deps
run_stage full-install-target '/usr/bin/bash /tmp/limad-install-target.sh'

echo "TARGET PREFLIGHT: PASS"
