#!/usr/bin/bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DESTINATION="${1:-$ROOT/.cache/heroic-offline-repo}"
CACHE_ROOT="$ROOT/.cache/heroic"
APT_ROOT="$ROOT/.cache/heroic-apt"
TARGET_STATUS="${LIMAD_TARGET_DPKG_STATUS:-$ROOT/.cache/ubuntu-target-state/dpkg-status}"
KEYRING="/usr/share/keyrings/ubuntu-archive-keyring.gpg"
HEROIC_VERSION="2.22.0"
HEROIC_DEB="Heroic-${HEROIC_VERSION}-linux-amd64.deb"
HEROIC_URL="https://github.com/Heroic-Games-Launcher/HeroicGamesLauncher/releases/download/v${HEROIC_VERSION}/${HEROIC_DEB}"
HEROIC_SHA256="4c8585ad7c7a76bd3c8058aa995b9064f457603f3b6afbd9114433cf4af7ecd2"
DEB_PATH="$CACHE_ROOT/$HEROIC_DEB"

for command in apt-get curl dpkg-deb dpkg-query dpkg-scanpackages gzip sha256sum; do
    if ! command -v "$command" >/dev/null 2>&1; then
        echo "ERROR: Required Heroic offline-repo command missing: $command" >&2
        exit 1
    fi
done

if [ ! -r "$KEYRING" ]; then
    echo "ERROR: Ubuntu archive keyring missing: $KEYRING" >&2
    exit 1
fi

if [ ! -r "$TARGET_STATUS" ]; then
    echo "ERROR: Ubuntu desktop target dpkg status missing: $TARGET_STATUS" >&2
    exit 1
fi

mkdir -p "$CACHE_ROOT"
if [ ! -f "$DEB_PATH" ] || ! printf '%s  %s\n' "$HEROIC_SHA256" "$DEB_PATH" | sha256sum -c - >/dev/null 2>&1; then
    temp="$DEB_PATH.part"
    rm -f "$temp"
    curl --fail --location --retry 5 --retry-delay 3 --output "$temp" "$HEROIC_URL"
    printf '%s  %s\n' "$HEROIC_SHA256" "$temp" | sha256sum -c - >/dev/null
    mv "$temp" "$DEB_PATH"
fi
printf '%s  %s\n' "$HEROIC_SHA256" "$DEB_PATH" | sha256sum -c - >/dev/null

package_name="$(dpkg-deb -f "$DEB_PATH" Package)"
package_version="$(dpkg-deb -f "$DEB_PATH" Version)"
package_arch="$(dpkg-deb -f "$DEB_PATH" Architecture)"
if [ -z "$package_name" ] || [ "$package_version" != "$HEROIC_VERSION" ] || [ "$package_arch" != "amd64" ]; then
    echo "ERROR: Heroic package metadata mismatch: package=$package_name version=$package_version arch=$package_arch" >&2
    exit 1
fi

rm -rf "$APT_ROOT" "$DESTINATION"
mkdir -p \
    "$APT_ROOT/etc/apt" \
    "$APT_ROOT/var/lib/apt/lists/partial" \
    "$APT_ROOT/var/lib/dpkg" \
    "$APT_ROOT/var/cache/apt/archives/partial" \
    "$DESTINATION"
install -m 0644 "$TARGET_STATUS" "$APT_ROOT/var/lib/dpkg/status"

cat > "$APT_ROOT/etc/apt/sources.list" <<EOF_SOURCES
deb [arch=amd64 signed-by=$KEYRING] http://archive.ubuntu.com/ubuntu resolute main restricted universe multiverse
deb [arch=amd64 signed-by=$KEYRING] http://archive.ubuntu.com/ubuntu resolute-updates main restricted universe multiverse
deb [arch=amd64 signed-by=$KEYRING] http://security.ubuntu.com/ubuntu resolute-security main restricted universe multiverse
EOF_SOURCES

APT_OPTIONS=(
    -o "Dir::Etc::sourcelist=$APT_ROOT/etc/apt/sources.list"
    -o "Dir::Etc::sourceparts=-"
    -o "Dir::State=$APT_ROOT/var/lib/apt"
    -o "Dir::State::status=$APT_ROOT/var/lib/dpkg/status"
    -o "Dir::State::lists=$APT_ROOT/var/lib/apt/lists"
    -o "Dir::Cache=$APT_ROOT/var/cache/apt"
    -o "Dir::Cache::archives=$APT_ROOT/var/cache/apt/archives"
    -o "APT::Architecture=amd64"
    -o "APT::Architectures::=amd64"
    -o "Acquire::Languages=none"
    -o "APT::Get::AllowUnauthenticated=false"
)

apt-get "${APT_OPTIONS[@]}" update
DEBIAN_FRONTEND=noninteractive apt-get \
    "${APT_OPTIONS[@]}" \
    --download-only \
    --no-install-recommends \
    --yes \
    install "$DEB_PATH"

install -m 0644 "$DEB_PATH" "$DESTINATION/$HEROIC_DEB"
find "$APT_ROOT/var/cache/apt/archives" -maxdepth 1 -type f -name '*.deb' -exec cp -a {} "$DESTINATION/" \;
printf '%s\n' "$package_name" > "$DESTINATION/PACKAGE-NAME.txt"
printf '%s\n' "$package_version" > "$DESTINATION/PACKAGE-VERSION.txt"
printf '%s\n' "$HEROIC_URL" > "$DESTINATION/SOURCE.txt"

(
    cd "$DESTINATION"
    SCAN_LOG="$(mktemp)"
    if ! dpkg-scanpackages --multiversion . /dev/null > Packages 2>"$SCAN_LOG"; then
        cat "$SCAN_LOG" >&2
        rm -f "$SCAN_LOG"
        exit 1
    fi
    rm -f "$SCAN_LOG"
    gzip -9c Packages > Packages.gz
    shopt -s nullglob
    CHECKSUM_FILES=(./*.deb Packages Packages.gz PACKAGE-NAME.txt PACKAGE-VERSION.txt SOURCE.txt)
    shopt -u nullglob
    sha256sum "${CHECKSUM_FILES[@]}" > SHA256SUMS.txt
    sha256sum -c SHA256SUMS.txt >/dev/null
)

rm -rf "$APT_ROOT"
echo "Heroic offline repository: PASS ($package_name $package_version)"
