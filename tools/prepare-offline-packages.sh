#!/usr/bin/bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PACKAGE_FILE="$ROOT/config/liview-packages.txt"
WORK="$ROOT/.cache/liview-offline-apt"
REPO="$ROOT/.cache/liview-offline-repo"

for command in apt-get dpkg-scanpackages gzip sha256sum; do
    command -v "$command" >/dev/null 2>&1 || {
        echo "ERROR: Required command not found: $command" >&2
        exit 1
    }
done

test -s "$PACKAGE_FILE" || {
    echo "ERROR: Missing LiView package list: $PACKAGE_FILE" >&2
    exit 1
}

rm -rf "$WORK" "$REPO"
mkdir -p \
    "$WORK/etc/apt/apt.conf.d" \
    "$WORK/lists/partial" \
    "$WORK/archives/partial" \
    "$REPO"
: > "$WORK/status"

cat > "$WORK/sources.list" <<'SOURCES'
deb [arch=amd64] http://archive.ubuntu.com/ubuntu resolute main restricted universe multiverse
deb [arch=amd64] http://archive.ubuntu.com/ubuntu resolute-updates main restricted universe multiverse
deb [arch=amd64] http://security.ubuntu.com/ubuntu resolute-security main restricted universe multiverse
SOURCES

APT_ARGS=(
    -o "Dir::Etc::sourcelist=$WORK/sources.list"
    -o "Dir::Etc::sourceparts=-"
    -o "Dir::State::status=$WORK/status"
    -o "Dir::State::Lists=$WORK/lists"
    -o "Dir::Cache::Archives=$WORK/archives"
    -o "APT::Architecture=amd64"
    -o "Acquire::Languages=none"
    -o "Acquire::Retries=5"
    -o "APT::Get::List-Cleanup=0"
    -o "Debug::NoLocking=1"
)

mapfile -t PACKAGES < <(grep -Ev '^[[:space:]]*(#|$)' "$PACKAGE_FILE")
if [ "${#PACKAGES[@]}" -eq 0 ]; then
    echo "ERROR: LiView package list is empty" >&2
    exit 1
fi

apt-get "${APT_ARGS[@]}" update
DEBIAN_FRONTEND=noninteractive apt-get \
    "${APT_ARGS[@]}" \
    --download-only \
    --yes \
    --no-install-recommends \
    install "${PACKAGES[@]}"

find "$WORK/archives" -maxdepth 1 -type f -name '*.deb' -exec cp -a {} "$REPO/" \;
if ! find "$REPO" -maxdepth 1 -type f -name '*.deb' -print -quit | grep -q .; then
    echo "ERROR: No offline DEB packages were downloaded" >&2
    exit 1
fi

(
    cd "$REPO"
    dpkg-scanpackages --multiversion . /dev/null > Packages
    gzip -9 -c Packages > Packages.gz
    cp "$PACKAGE_FILE" DIRECT-PACKAGES.txt
    cp "$WORK/sources.list" RESOLUTE-SOURCES.txt
    find . -maxdepth 1 -type f -name '*.deb' -printf '%f\n' | LC_ALL=C sort > DEB-FILES.txt
    sha256sum -- *.deb Packages Packages.gz DIRECT-PACKAGES.txt RESOLUTE-SOURCES.txt DEB-FILES.txt > SHA256SUMS.txt
    sha256sum -c SHA256SUMS.txt >/dev/null
)

printf 'LiView offline repository: PASS (%s DEBs)\n' "$(find "$REPO" -maxdepth 1 -type f -name '*.deb' | wc -l)"
