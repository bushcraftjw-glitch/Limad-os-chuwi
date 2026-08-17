#!/usr/bin/bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source "$ROOT/config/build.env"

"$ROOT/tools/reassemble-vendor.sh"

WORK="$ROOT/.cache/payload-work"
PAYLOAD="$ROOT/.cache/payload"
PROGRAM_ZIP="$ROOT/.cache/vendor/LiMaD-Programme-BASE1B-EXTRAKT.zip"
ICON_ZIP="$ROOT/.cache/vendor/LiMaD-OS-MASTER-ICON-THEME-V3.2-BUILD-READY.zip"
WALLPAPER_ZIP="$ROOT/.cache/vendor/LiMaD-4K-Hintergrundbilder-BASE1B.zip"

rm -rf "$WORK" "$PAYLOAD"
mkdir -p "$WORK/programs" "$WORK/icons" "$WORK/wallpapers" "$PAYLOAD/rootfs"

unzip -q "$PROGRAM_ZIP" -d "$WORK/programs"
unzip -q "$ICON_ZIP" -d "$WORK/icons"
unzip -q "$WALLPAPER_ZIP" -d "$WORK/wallpapers"

PROGRAM_ROOT="$WORK/programs/LiMaD-Programme-BASE1B-EXTRAKT"
ICON_ROOT="$WORK/icons/LiMaD-OS-MASTER-ICON-THEME-V3.2-BUILD-READY"

(
    cd "$PROGRAM_ROOT"
    sha256sum -c SHA256SUMS.txt >/dev/null
)
(
    cd "$ICON_ROOT"
    sha256sum -c SHA256SUMS.txt >/dev/null
)

rsync -a "$PROGRAM_ROOT/filesystem/" "$PAYLOAD/rootfs/"
python3 -B "$ROOT/tools/strip-lidrop-airdrop.py" "$PAYLOAD/rootfs"

rm -f     "$PAYLOAD/rootfs/etc/systemd/system/limad-x11-tmpfix.service"     "$PAYLOAD/rootfs/etc/xdg/autostart/limad-default-flatpaks.desktop"     "$PAYLOAD/rootfs/etc/xdg/autostart/limad-easyeffects-service.desktop"     "$PAYLOAD/rootfs/etc/xdg/autostart/limad-firefox-theme.desktop"     "$PAYLOAD/rootfs/etc/xdg/autostart/limad-first-login.desktop"     "$PAYLOAD/rootfs/etc/xdg/autostart/limad-lidrop-status.desktop"     "$PAYLOAD/rootfs/etc/xdg/autostart/limad-zen-deutsch.desktop"

rm -rf "$PAYLOAD/rootfs/usr/share/icons/LiMaD"
mkdir -p "$PAYLOAD/rootfs/usr/share/icons"
rsync -a "$ICON_ROOT/assets/system_files/usr/share/icons/LiMaD/" "$PAYLOAD/rootfs/usr/share/icons/LiMaD/"

WALLPAPER_DIR="$PAYLOAD/rootfs/usr/share/backgrounds/limad"
mkdir -p "$WALLPAPER_DIR" "$PAYLOAD/rootfs/usr/share/gnome-background-properties"
for wallpaper in \
    LiMaD-Wallpaper-01-Logo-Links-4K.png \
    LiMaD-Wallpaper-02-Logo-Zentriert-4K.png \
    LiMaD-Wallpaper-03-Wellen-Emblem-4K.png; do
    if [ ! -f "$WORK/wallpapers/$wallpaper" ]; then
        echo "ERROR: Missing LiMaD wallpaper: $wallpaper" >&2
        exit 1
    fi
    install -m 0644 "$WORK/wallpapers/$wallpaper" "$WALLPAPER_DIR/$wallpaper"
done

cat > "$PAYLOAD/rootfs/usr/share/gnome-background-properties/limad-wallpapers.xml" <<'XML'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE wallpapers SYSTEM "gnome-wp-list.dtd">
<wallpapers>
  <wallpaper deleted="false">
    <name>LiMaD Logo Links</name>
    <filename>/usr/share/backgrounds/limad/LiMaD-Wallpaper-01-Logo-Links-4K.png</filename>
    <options>zoom</options>
  </wallpaper>
  <wallpaper deleted="false">
    <name>LiMaD Logo Zentriert</name>
    <filename>/usr/share/backgrounds/limad/LiMaD-Wallpaper-02-Logo-Zentriert-4K.png</filename>
    <options>zoom</options>
  </wallpaper>
  <wallpaper deleted="false">
    <name>LiMaD Wellen Emblem</name>
    <filename>/usr/share/backgrounds/limad/LiMaD-Wallpaper-03-Wellen-Emblem-4K.png</filename>
    <options>zoom</options>
  </wallpaper>
</wallpapers>
XML

WHITESUR="$WORK/WhiteSur-gtk-theme"
git clone -q "$WHITESUR_REPOSITORY" "$WHITESUR"
git -C "$WHITESUR" checkout -q --detach "$WHITESUR_REF"
ACTUAL_REF="$(git -C "$WHITESUR" rev-parse HEAD)"
if [ "$ACTUAL_REF" != "$WHITESUR_REF" ]; then
    echo "ERROR: WhiteSur commit mismatch: $ACTUAL_REF" >&2
    exit 1
fi

mkdir -p "$PAYLOAD/rootfs/usr/share/themes"
(
    cd "$WHITESUR"
    sudo -n /usr/bin/bash ./install.sh \
        -d "$PAYLOAD/rootfs/usr/share/themes" \
        -c light \
        -c dark \
        -a normal \
        -N stable \
        --silent-mode
)
sudo -n chown -R "$(id -u):$(id -g)" "$PAYLOAD/rootfs/usr/share/themes"

# GNOME 50/libadwaita keeps its stock Ubuntu styling. LiMaD applies only a
# small GTK4 titlebutton override from build/rootfs/usr/share/limad/gtk4.

FIRMWARE_SOURCE="$ROOT/assets/firmware"
(
    cd "$FIRMWARE_SOURCE"
    sha256sum -c SHA256SUMS.txt
)
mkdir -p "$PAYLOAD/rootfs/usr/lib/firmware/radeon" "$PAYLOAD/rootfs/usr/share/doc/limad-os-base1/firmware"
install -m 0644 "$FIRMWARE_SOURCE"/radeon/BONAIRE_*.bin "$PAYLOAD/rootfs/usr/lib/firmware/radeon/"
install -m 0644 "$FIRMWARE_SOURCE/LICENSE.radeon" "$PAYLOAD/rootfs/usr/share/doc/limad-os-base1/firmware/LICENSE.radeon"

mkdir -p "$PAYLOAD/rootfs/usr/share/limad/branding"
install -m 0644 "$ROOT/build/branding/limad-logo-192.png" "$PAYLOAD/rootfs/usr/share/limad/branding/limad-logo-192.png"
install -m 0644 "$ROOT/build/branding/limad-logo-256.png" "$PAYLOAD/rootfs/usr/share/limad/branding/limad-logo-256.png"

rsync -a "$ROOT/build/rootfs/" "$PAYLOAD/rootfs/"
cp "$ROOT/build/install-target.sh" "$PAYLOAD/install-target.sh"
chmod 0755 "$PAYLOAD/install-target.sh"

mkdir -p "$PAYLOAD/rootfs/usr/share/doc/limad-os-base1"
cat > "$PAYLOAD/rootfs/usr/share/doc/limad-os-base1/BUILD-INFO.txt" <<EOF
LiMaD OS 3.0 RC1 BASE1 DESIGN V14
Base: Ubuntu 26.04 LTS Desktop FULL
Ubuntu SHA256: $UBUNTU_ISO_SHA256
WhiteSur commit: $WHITESUR_REF
LiMaD programs SHA256: $PROGRAMS_ZIP_SHA256
LiMaD icons SHA256: $ICONS_ZIP_SHA256
LiMaD wallpapers SHA256: $WALLPAPERS_ZIP_SHA256
iMac17,1 firmware source: linux-firmware tag 20250509, Radeon Bonaire firmware
GTK4: stock libadwaita with LiMaD traffic-light titlebutton override.
LiDrop: browser/local-device transfer enabled; AirDrop/OpenDrop/OWL/AWDL compatibility intentionally removed in V14.
EOF

for removed in \
    "$PAYLOAD/rootfs/usr/local/bin/limad-airdrop-check" \
    "$PAYLOAD/rootfs/usr/local/bin/limad-airdrop-control" \
    "$PAYLOAD/rootfs/usr/local/bin/limad-airdrop-session" \
    "$PAYLOAD/rootfs/usr/local/bin/limad-opendrop-receive" \
    "$PAYLOAD/rootfs/usr/share/polkit-1/rules.d/49-limad-airdrop.rules"; do
    if [ -e "$removed" ]; then
        echo "ERROR: AirDrop compatibility component remains: $removed" >&2
        exit 1
    fi
done
if grep -Eqi 'airdrop|opendrop|awdl|owl' \
    "$PAYLOAD/rootfs/usr/share/limad-drop/web/app.js" \
    "$PAYLOAD/rootfs/usr/share/limad-drop/limad_dropd.py"; then
    echo "ERROR: AirDrop compatibility code remains in active LiDrop UI/backend." >&2
    exit 1
fi
