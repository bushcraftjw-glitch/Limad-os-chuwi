#!/usr/bin/bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DESTINATION="${1:-$ROOT/.cache/gaming-offline-repo}"
PACKAGE_FILE="$ROOT/build/gaming-packages.txt"
APT_ROOT="$ROOT/.cache/gaming-apt"
KEYRING="/usr/share/keyrings/ubuntu-archive-keyring.gpg"

for command in apt-get dpkg-deb dpkg-scanpackages gzip sha256sum; do
    if ! command -v "$command" >/dev/null 2>&1; then
        echo "ERROR: Required gaming offline-repo command missing: $command" >&2
        exit 1
    fi
done

if [ ! -r "$KEYRING" ]; then
    echo "ERROR: Ubuntu archive keyring missing: $KEYRING" >&2
    exit 1
fi

mapfile -t PACKAGES < <(grep -Ev '^[[:space:]]*(#|$)' "$PACKAGE_FILE")
if [ "${#PACKAGES[@]}" -eq 0 ]; then
    echo "ERROR: Gaming package list is empty." >&2
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
deb [arch=amd64,i386 signed-by=$KEYRING] http://archive.ubuntu.com/ubuntu resolute main restricted universe multiverse
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
    -o "APT::Architectures::=i386"
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
if ! find "$DESTINATION" -maxdepth 1 -type f -name '*.deb' -print -quit | grep -q .; then
    echo "ERROR: Gaming offline repository contains no DEB packages." >&2
    exit 1
fi

package_present() {
    local requested="$1"
    local base="${requested%%:*}"
    local requested_arch=""
    local deb
    local deb_package
    local deb_arch

    if [[ "$requested" == *:* ]]; then
        requested_arch="${requested##*:}"
    fi

    while IFS= read -r deb; do
        deb_package="$(dpkg-deb -f "$deb" Package)"
        [ "$deb_package" = "$base" ] || continue
        if [ -z "$requested_arch" ]; then
            return 0
        fi
        deb_arch="$(dpkg-deb -f "$deb" Architecture)"
        if [ "$deb_arch" = "$requested_arch" ] || [ "$deb_arch" = "all" ]; then
            return 0
        fi
    done < <(find "$DESTINATION" -maxdepth 1 -type f -name '*.deb' -print)
    return 1
}

for package in "${PACKAGES[@]}"; do
    if ! package_present "$package"; then
        echo "ERROR: Requested gaming package missing from offline repository: $package" >&2
        exit 1
    fi
done

for required_i386 in steam-libs-i386 mesa-vulkan-drivers libvulkan1 libglx-mesa0; do
    found=0
    while IFS= read -r deb; do
        if [ "$(dpkg-deb -f "$deb" Package)" = "$required_i386" ] \
            && [ "$(dpkg-deb -f "$deb" Architecture)" = "i386" ]; then
            found=1
            break
        fi
    done < <(find "$DESTINATION" -maxdepth 1 -type f -name '*.deb' -print)
    if [ "$found" -ne 1 ]; then
        echo "ERROR: Required 32-bit gaming runtime missing: ${required_i386}:i386" >&2
        exit 1
    fi
done

(
    cd "$DESTINATION"
    dpkg-scanpackages --multiversion . /dev/null > Packages
    gzip -9c Packages > Packages.gz
    printf '%s\n' "${PACKAGES[@]}" > REQUESTED-PACKAGES.txt
    sha256sum ./*.deb Packages Packages.gz REQUESTED-PACKAGES.txt > SHA256SUMS.txt
    sha256sum -c SHA256SUMS.txt >/dev/null
)

rm -rf "$APT_ROOT"
echo "Gaming offline repository: PASS"
