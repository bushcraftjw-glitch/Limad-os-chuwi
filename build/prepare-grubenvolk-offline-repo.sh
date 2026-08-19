#!/usr/bin/bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DESTINATION="${1:-$ROOT/.cache/grubenvolk-offline-repo}"
PACKAGE_FILE="$ROOT/build/grubenvolk-packages.txt"
APT_ROOT="$ROOT/.cache/grubenvolk-apt"
KEYRING="/usr/share/keyrings/ubuntu-archive-keyring.gpg"

for command in apt-get dpkg-deb dpkg-scanpackages gzip sha256sum; do
    if ! command -v "$command" >/dev/null 2>&1; then
        echo "ERROR: Required GRUBENVOLK offline-repo command missing: $command" >&2
        exit 1
    fi
done

if [ ! -r "$KEYRING" ]; then
    echo "ERROR: Ubuntu archive keyring missing: $KEYRING" >&2
    exit 1
fi

mapfile -t PACKAGES < <(grep -Ev '^[[:space:]]*(#|$)' "$PACKAGE_FILE")
if [ "${#PACKAGES[@]}" -eq 0 ]; then
    echo "ERROR: GRUBENVOLK package list is empty." >&2
    exit 1
fi

rm -rf "$APT_ROOT" "$DESTINATION"
mkdir -p \
    "$APT_ROOT/etc/apt" \
    "$APT_ROOT/var/lib/apt/lists/partial" \
    "$APT_ROOT/var/lib/dpkg" \
    "$APT_ROOT/var/cache/apt/archives/partial" \
    "$DESTINATION"
: > "$APT_ROOT/var/lib/dpkg/status"

cat > "$APT_ROOT/etc/apt/sources.list" <<EOF_SOURCES
deb [arch=amd64 signed-by=$KEYRING] http://archive.ubuntu.com/ubuntu resolute main restricted universe multiverse
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
    -o "APT::Architectures=amd64"
    -o "Acquire::Languages=none"
    -o "APT::Get::AllowUnauthenticated=false"
)

apt-get "${APT_OPTIONS[@]}" update
DEBIAN_FRONTEND=noninteractive apt-get \
    "${APT_OPTIONS[@]}" \
    --download-only \
    --no-install-recommends \
    --yes \
    install "${PACKAGES[@]}"

find "$APT_ROOT/var/cache/apt/archives" -maxdepth 1 -type f -name '*.deb' -exec cp -a {} "$DESTINATION/" \;
shopt -s nullglob
DEB_FILES=("$DESTINATION"/*.deb)
shopt -u nullglob
if [ "${#DEB_FILES[@]}" -eq 0 ]; then
    echo "ERROR: GRUBENVOLK offline repository contains no DEB packages." >&2
    exit 1
fi

for package in "${PACKAGES[@]}"; do
    found=0
    for deb in "${DEB_FILES[@]}"; do
        if [ "$(dpkg-deb -f "$deb" Package)" = "$package" ]; then
            found=1
            break
        fi
    done
    if [ "$found" -ne 1 ]; then
        echo "ERROR: Requested GRUBENVOLK package missing from offline repository: $package" >&2
        exit 1
    fi
done

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
    printf '%s\n' "${PACKAGES[@]}" > REQUESTED-PACKAGES.txt
    sha256sum ./*.deb Packages Packages.gz REQUESTED-PACKAGES.txt > SHA256SUMS.txt
    sha256sum -c SHA256SUMS.txt >/dev/null
)

rm -rf "$APT_ROOT"
echo "GRUBENVOLK offline repository: PASS"
