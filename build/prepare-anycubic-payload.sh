#!/usr/bin/bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source "$ROOT/build/versions.env"

ROOTFS="${1:-$ROOT/.cache/payload/rootfs}"
VENDOR_DIR="$ROOT/build/vendor/anycubic"
DEB_NAME="anycubicslicernext_${ANYCUBIC_DEB_VERSION}_amd64.deb"
APP_ROOT="$ROOTFS/usr/lib/limad/apps/anycubic-slicer-next"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
DEB="$TMP/$DEB_NAME"
EXTRACTED="$TMP/root"

for command in dpkg-deb find sha256sum; do
    if ! command -v "$command" >/dev/null 2>&1; then
        echo "ERROR: Required Anycubic payload command missing: $command" >&2
        exit 1
    fi
done

mapfile -t PARTS < <(find "$VENDOR_DIR" -maxdepth 1 -type f -name "${DEB_NAME}.part[0-9][0-9]" -print | sort)
if [ "${#PARTS[@]}" -ne 2 ]; then
    echo "ERROR: Expected exactly two Anycubic vendor parts." >&2
    exit 1
fi
for part in "${PARTS[@]}"; do
    test -s "$part"
done
(
    cd "$VENDOR_DIR"
    sha256sum -c SHA256SUMS >/dev/null
)
cat "${PARTS[@]}" > "$DEB"
printf '%s  %s\n' "$ANYCUBIC_SOURCE_SHA256" "$DEB" | sha256sum -c - >/dev/null

package_name="$(dpkg-deb -f "$DEB" Package)"
package_version="$(dpkg-deb -f "$DEB" Version)"
package_arch="$(dpkg-deb -f "$DEB" Architecture)"
if [ "$package_name" != "anycubicslicernext" ] || [ "$package_version" != "$ANYCUBIC_DEB_VERSION" ] || [ "$package_arch" != "amd64" ]; then
    echo "ERROR: Anycubic package metadata mismatch: package=$package_name version=$package_version arch=$package_arch" >&2
    exit 1
fi

dpkg-deb -x "$DEB" "$EXTRACTED"
test -x "$EXTRACTED/usr/bin/AnycubicSlicerNext"
test -d "$EXTRACTED/usr/share/AnycubicSlicerNext/resources"
if [ "$(cat "$EXTRACTED/usr/share/AnycubicSlicerNext/resources/build-version.txt")" != "$ANYCUBIC_BUILD_VERSION" ]; then
    echo "ERROR: Anycubic embedded build version mismatch." >&2
    exit 1
fi

rm -rf "$APP_ROOT"
install -d -m 0755 "$APP_ROOT/bin" "$APP_ROOT/lib" "$APP_ROOT/resources"
install -m 0755 "$EXTRACTED/usr/bin/AnycubicSlicerNext" "$APP_ROOT/bin/AnycubicSlicerNext"
find "$EXTRACTED/usr/lib" -maxdepth 1 -type f \( -name '*.so' -o -name '*.so.*' -o -name '*.a' \) -exec install -m 0644 {} "$APP_ROOT/lib/" \;
cp -a "$EXTRACTED/usr/share/AnycubicSlicerNext/resources/." "$APP_ROOT/resources/"
printf '%s\n' "$ANYCUBIC_DEB_VERSION" > "$APP_ROOT/PACKAGE-VERSION"
printf '%s\n' "$ANYCUBIC_BUILD_VERSION" > "$APP_ROOT/BUILD-VERSION"
printf '%s\n' "$ANYCUBIC_SOURCE_SHA256" > "$APP_ROOT/SOURCE-SHA256"

install -d -m 0755 "$ROOTFS/usr/share"
rm -rf "$ROOTFS/usr/share/AnycubicSlicerNext"
ln -s /usr/lib/limad/apps/anycubic-slicer-next "$ROOTFS/usr/share/AnycubicSlicerNext"

test -x "$APP_ROOT/bin/AnycubicSlicerNext"
test -s "$APP_ROOT/resources/build-version.txt"
echo "Anycubic Slicer Next payload: PASS ($ANYCUBIC_DEB_VERSION / $ANYCUBIC_BUILD_VERSION)"
