#!/usr/bin/bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source "$ROOT/config/build.env"

CACHE="$ROOT/.cache"
ISO="$CACHE/$UBUNTU_ISO_NAME"
OVERLAY="$CACHE/iso-overlay"
OUT="$ROOT/out"
OUTPUT="$OUT/$OUTPUT_ISO_NAME"

mkdir -p "$CACHE" "$OUT"

for command in cpio curl git python3 rsync sha256sum sudo unzip xorriso; do
    if ! command -v "$command" >/dev/null 2>&1; then
        echo "ERROR: Required command not found: $command" >&2
        exit 1
    fi
done

if ! sudo -n true >/dev/null 2>&1; then
    echo "ERROR: Passwordless sudo is required for the WhiteSur staging step." >&2
    exit 1
fi

UBUNTU_ISO_URLS=(
    "$UBUNTU_ISO_URL"
    "https://nl.releases.ubuntu.com/26.04/$UBUNTU_ISO_NAME"
    "https://ftp.fau.de/ubuntu-releases/releases/26.04/$UBUNTU_ISO_NAME"
)

select_fastest_iso_url() {
    local best_url=""
    local best_speed=0
    local url
    local speed
    local speed_int

    echo "Benchmarking Ubuntu ISO mirrors..." >&2
    for url in "${UBUNTU_ISO_URLS[@]}"; do
        speed="$(
            curl \
                --fail \
                --location \
                --silent \
                --connect-timeout 5 \
                --max-time 15 \
                --range 0-4194303 \
                --output /dev/null \
                --write-out '%{speed_download}' \
                "$url" 2>/dev/null || true
        )"
        speed_int="${speed%%.*}"
        if [[ "$speed_int" =~ ^[0-9]+$ ]] && (( speed_int > 0 )); then
            printf 'Mirror benchmark: %s bytes/s  %s\n' "$speed_int" "$url" >&2
            if (( speed_int > best_speed )); then
                best_speed="$speed_int"
                best_url="$url"
            fi
        else
            printf 'Mirror benchmark: unavailable  %s\n' "$url" >&2
        fi
    done

    if [[ -z "$best_url" ]]; then
        best_url="$UBUNTU_ISO_URL"
    fi

    printf 'Selected Ubuntu ISO mirror: %s\n' "$best_url" >&2
    printf '%s\n' "$best_url"
}

download_ubuntu_iso() {
    local selected_url
    local url
    local attempted="|"

    selected_url="$(select_fastest_iso_url)"
    for url in "$selected_url" "${UBUNTU_ISO_URLS[@]}"; do
        if [[ "$attempted" == *"|$url|"* ]]; then
            continue
        fi
        attempted+="$url|"
        rm -f "$ISO"
        echo "Downloading Ubuntu ISO from: $url"
        if curl --fail --location --retry 5 --retry-delay 3 --output "$ISO" "$url"; then
            return 0
        fi
        echo "WARNING: Ubuntu ISO download failed from $url; trying next mirror." >&2
    done

    echo "ERROR: Ubuntu ISO download failed from all configured mirrors." >&2
    return 1
}

if [ ! -f "$ISO" ] || ! printf '%s  %s\n' "$UBUNTU_ISO_SHA256" "$ISO" | sha256sum -c - >/dev/null 2>&1; then
    download_ubuntu_iso
else
    echo "Ubuntu ISO cache hit: $ISO"
fi
printf '%s  %s\n' "$UBUNTU_ISO_SHA256" "$ISO" | sha256sum -c -

"$ROOT/build/prepare-ubuntu-target-state.sh" "$ISO"
"$ROOT/build/prepare-payload.sh"
"$ROOT/tests/validate-payload.sh"
"$ROOT/build/preflight-target-install.sh"

rm -rf "$OVERLAY"
mkdir -p "$OVERLAY/casper" "$OVERLAY/limad"
cp "$ROOT/config/autoinstall.yaml" "$OVERLAY/autoinstall.yaml"
rsync -a "$CACHE/payload/rootfs/" "$OVERLAY/limad/rootfs/"
cp "$CACHE/payload/install-target.sh" "$OVERLAY/limad/install-target.sh"

INSTALL_SOURCES_ORIGINAL="$CACHE/install-sources.original.yaml"
rm -f "$INSTALL_SOURCES_ORIGINAL"
xorriso -osirrox on -indev "$ISO" -extract /casper/install-sources.yaml "$INSTALL_SOURCES_ORIGINAL" >/dev/null 2>&1
python3 -B "$ROOT/tools/filter-install-sources.py" "$INSTALL_SOURCES_ORIGINAL" "$OVERLAY/casper/install-sources.yaml"
python3 -B "$ROOT/tools/validate-install-sources.py" \
    --original "$INSTALL_SOURCES_ORIGINAL" \
    "$OVERLAY/casper/install-sources.yaml"

INITRD_ORIGINAL="$CACHE/initrd.original"
rm -f "$INITRD_ORIGINAL" "$OVERLAY/casper/initrd"
xorriso -osirrox on -indev "$ISO" -extract /casper/initrd "$INITRD_ORIGINAL" >/dev/null 2>&1
"$ROOT/build/prepare-imac17-initrd.sh" "$INITRD_ORIGINAL" "$OVERLAY/casper/initrd"

GRUB_ORIGINAL="$CACHE/grub.original.cfg"
GRUB_BRANDED="$OVERLAY/boot/grub/grub.cfg"
rm -f "$GRUB_ORIGINAL" "$GRUB_BRANDED"
mkdir -p "$OVERLAY/boot/grub"
if xorriso -osirrox on -indev "$ISO" -extract /boot/grub/grub.cfg "$GRUB_ORIGINAL" >/dev/null 2>&1; then
    python3 -B "$ROOT/tools/brand-grub.py" "$GRUB_ORIGINAL" "$GRUB_BRANDED"
fi

MD5_ORIGINAL="$CACHE/md5sum.original.txt"
MD5_CURRENT="$CACHE/md5sum.current.txt"
MD5_NEXT="$CACHE/md5sum.next.txt"
rm -f "$MD5_ORIGINAL" "$MD5_CURRENT" "$MD5_NEXT" "$OVERLAY/md5sum.txt"

update_md5_entry() {
    local file="$1"
    local iso_path="$2"
    python3 -B "$ROOT/tools/update-md5.py" "$MD5_CURRENT" "$file" "$iso_path" "$MD5_NEXT"
    mv "$MD5_NEXT" "$MD5_CURRENT"
}

if xorriso -osirrox on -indev "$ISO" -extract /md5sum.txt "$MD5_ORIGINAL" >/dev/null 2>&1; then
    install -m 0644 "$MD5_ORIGINAL" "$MD5_CURRENT"
    update_md5_entry "$OVERLAY/casper/install-sources.yaml" casper/install-sources.yaml
    update_md5_entry "$OVERLAY/casper/initrd" casper/initrd
    if [ -f "$GRUB_BRANDED" ]; then
        update_md5_entry "$GRUB_BRANDED" boot/grub/grub.cfg
    fi
    install -m 0644 "$MD5_CURRENT" "$OVERLAY/md5sum.txt"
    test -w "$OVERLAY/md5sum.txt"
fi

rm -rf "$CACHE/payload-work" "$CACHE/payload" "$CACHE/vendor"
df -h "$ROOT"

rm -f "$OUTPUT" "$OUTPUT.sha256"
xorriso \
    -indev "$ISO" \
    -outdev "$OUTPUT" \
    -map "$OVERLAY" / \
    -boot_image any replay \
    -volid LIMAD_OS_3_0_RC1 \
    -compliance no_emul_toc \
    -padding included

sha256sum "$OUTPUT" | tee "$OUTPUT.sha256"
"$ROOT/tests/verify-built-iso.sh" "$OUTPUT"

cat > "$OUT/BUILD-REPORT.txt" <<EOF_REPORT
LiMaD OS 3.0 RC1 BASE1 DESIGN V26
Base: Ubuntu 26.04 LTS Desktop FULL
Official Ubuntu ISO: $UBUNTU_ISO_NAME
Official Ubuntu SHA256: $UBUNTU_ISO_SHA256
Install source: ubuntu-desktop only
Driver search: enabled
OEM drivers: auto
Third-party drivers: enabled
WhiteSur commit: $WHITESUR_REF
LiMaD icon theme: V3.2
LiMaD wallpapers: 3 x 3840x2160, wallpaper 01 default
Installer branding: Canonical whitelabel API, LiMaD OS Installer title, LiMaD images, German/English LiMaD slide
Design V26: V25 stable base retained; LiView performance preview, confirmed LiMaD app fixes and Heroic Games Launcher offline first-install integration added
iMac17,1: DMI-targeted Radeon CIK compatibility path; upstream Radeon Bonaire firmware embedded in live initrd and installed target
Firmware source: linux-firmware tag 20250509; firmware hashes embedded and verified
Install source catalog: ubuntu-desktop only, Canonical catalog metadata preserved
LiDrop: browser/local-device transfer enabled; AirDrop/OpenDrop/OWL/AWDL compatibility removed by design
LiMusic: 0.3.22; GTK4/WebKitGTK 6/GStreamer runtime and common codec sets installed by LiMaD runtime dependency service
LiView: 1.1.1; PDF/image/video/3D preview and editing; all declared MIME types default to LiView; Ubuntu 26.04 dependency closure embedded for offline installation; LiMaD Updater registered
Gaming: Steam, Lutris, Protontricks, Wine/Winetricks, GameMode, MangoHud, Gamescope, Vulkan tools, vkBasalt and GOverlay; amd64+i386 Ubuntu 26.04 dependency closure embedded; ProtonUp-Qt provisioned through Flathub
Output: $OUTPUT_ISO_NAME
Output SHA256: $(sha256sum "$OUTPUT" | awk '{print $1}')
EOF_REPORT

find "$CACHE" -mindepth 1 -maxdepth 1 ! -name "$UBUNTU_ISO_NAME" -exec rm -rf -- {} +
