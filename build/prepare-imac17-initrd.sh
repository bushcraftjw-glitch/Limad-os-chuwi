#!/usr/bin/bash
set -euo pipefail

if [ "$#" -ne 2 ]; then
    echo "usage: prepare-imac17-initrd.sh ORIGINAL_INITRD OUTPUT_INITRD" >&2
    exit 2
fi

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ORIGINAL_INITRD="$1"
OUTPUT_INITRD="$2"
FIRMWARE_SOURCE="$ROOT/assets/firmware"
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

for command in cpio sha256sum; do
    if ! command -v "$command" >/dev/null 2>&1; then
        echo "ERROR: Required command not found: $command" >&2
        exit 1
    fi
done

if [ ! -s "$ORIGINAL_INITRD" ]; then
    echo "ERROR: Original initrd is missing or empty" >&2
    exit 1
fi

(
    cd "$FIRMWARE_SOURCE"
    sha256sum -c SHA256SUMS.txt
)

# Firmware needed before the live root is available.
mkdir -p "$WORK/usr/lib/firmware/radeon"
install -m 0644 "$FIRMWARE_SOURCE"/radeon/BONAIRE_*.bin "$WORK/usr/lib/firmware/radeon/"

# Canonical's installer reads whitelabel data from the live root. Inject it
# through a casper-bottom hook so the signed installer snap itself stays intact.
mkdir -p "$WORK/scripts/casper-bottom" \
    "$WORK/limad-installer/images" \
    "$WORK/limad-installer/slides"
install -m 0755 "$ROOT/build/casper-bottom/62limad-branding" \
    "$WORK/scripts/casper-bottom/62limad-branding"
install -m 0644 "$ROOT/build/installer-whitelabel.yaml" \
    "$WORK/limad-installer/whitelabel.yaml"
install -m 0644 "$ROOT/build/branding/limad-logo-192.png" \
    "$WORK/limad-installer/images/limad-logo-192.png"
install -m 0644 "$ROOT/build/branding/limad-logo-256.png" \
    "$WORK/limad-installer/images/limad-logo-256.png"
rsync -a "$ROOT/build/installer-slides/" "$WORK/limad-installer/slides/"

(
    cd "$WORK"
    find usr scripts limad-installer -print0 \
        | LC_ALL=C sort -z \
        | cpio --null --quiet -o -H newc > "$WORK/limad-v22-early.cpio"
)

cat "$WORK/limad-v22-early.cpio" "$ORIGINAL_INITRD" > "$OUTPUT_INITRD"
chmod 0644 "$OUTPUT_INITRD"

if [ "$(stat -c %s "$OUTPUT_INITRD")" -le "$(stat -c %s "$ORIGINAL_INITRD")" ]; then
    echo "ERROR: LiMaD V22 initrd prefix was not added" >&2
    exit 1
fi

for marker in \
    'usr/lib/firmware/radeon/BONAIRE_uvd.bin' \
    'scripts/casper-bottom/62limad-branding' \
    'limad-installer/whitelabel.yaml' \
    'limad-installer/slides/1/slide_de_DE.html'; do
    if ! grep -aFq "$marker" "$OUTPUT_INITRD"; then
        echo "ERROR: Initrd prefix marker missing: $marker" >&2
        exit 1
    fi
done

echo "V22 INITRD FIRMWARE + LIVE BRANDING: PASS"
