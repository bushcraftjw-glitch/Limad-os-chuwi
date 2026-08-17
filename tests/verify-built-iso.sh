#!/usr/bin/bash
set -euo pipefail

if [ "$#" -ne 1 ]; then
    echo "usage: verify-built-iso.sh ISO" >&2
    exit 2
fi

ISO="$1"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

xorriso -osirrox on -indev "$ISO" -extract /autoinstall.yaml "$TMP/autoinstall.yaml" >/dev/null 2>&1
xorriso -osirrox on -indev "$ISO" -extract /casper/install-sources.yaml "$TMP/install-sources.yaml" >/dev/null 2>&1
xorriso -osirrox on -indev "$ISO" -extract /casper/initrd "$TMP/initrd" >/dev/null 2>&1
xorriso -osirrox on -indev "$ISO" -extract /md5sum.txt "$TMP/md5sum.txt" >/dev/null 2>&1
xorriso -osirrox on -indev "$ISO" -extract /boot/grub/grub.cfg "$TMP/grub.cfg" >/dev/null 2>&1
xorriso -osirrox on -indev "$ISO" -extract /limad/install-target.sh "$TMP/install-target.sh" >/dev/null 2>&1
xorriso -osirrox on -indev "$ISO" -extract /limad/rootfs/etc/limad-release "$TMP/limad-release" >/dev/null 2>&1
xorriso -osirrox on -indev "$ISO" -extract /limad/rootfs/usr/share/backgrounds/limad/LiMaD-Wallpaper-01-Logo-Links-4K.png "$TMP/wallpaper.png" >/dev/null 2>&1
xorriso -osirrox on -indev "$ISO" -extract /limad/rootfs/usr/share/icons/LiMaD/index.theme "$TMP/index.theme" >/dev/null 2>&1
xorriso -osirrox on -indev "$ISO" -extract /limad/rootfs/usr/share/limad/gtk4/gtk.css "$TMP/gtk4.css" >/dev/null 2>&1
xorriso -osirrox on -indev "$ISO" -extract /limad/rootfs/usr/share/limad/gtk4/limad-assets/close.svg "$TMP/close.svg" >/dev/null 2>&1
xorriso -osirrox on -indev "$ISO" -extract /limad/rootfs/usr/local/bin/limad-design-system "$TMP/design-system" >/dev/null 2>&1
xorriso -osirrox on -indev "$ISO" -extract /limad/rootfs/usr/local/bin/limad-desktop-core-system "$TMP/desktop-core-system" >/dev/null 2>&1
xorriso -osirrox on -indev "$ISO" -extract /limad/rootfs/usr/share/gnome-shell/extensions/lilink@limad.local/metadata.json "$TMP/lilink-metadata.json" >/dev/null 2>&1
xorriso -osirrox on -indev "$ISO" -extract /limad/rootfs/usr/share/gnome-shell/extensions/lilink@limad.local/extension.js "$TMP/lilink-extension.js" >/dev/null 2>&1
xorriso -osirrox on -indev "$ISO" -extract /limad/rootfs/usr/share/gnome-shell/extensions/lidrop@limad.local/metadata.json "$TMP/lidrop-metadata.json" >/dev/null 2>&1
xorriso -osirrox on -indev "$ISO" -extract /limad/rootfs/usr/share/gnome-shell/extensions/lidrop@limad.local/extension.js "$TMP/lidrop-extension.js" >/dev/null 2>&1
xorriso -osirrox on -indev "$ISO" -extract /limad/rootfs/usr/share/gnome-shell/extensions/limad-menu@limad.local/metadata.json "$TMP/limad-menu-metadata.json" >/dev/null 2>&1
xorriso -osirrox on -indev "$ISO" -extract /limad/rootfs/usr/share/gnome-shell/extensions/limad-menu@limad.local/extension.js "$TMP/limad-menu-extension.js" >/dev/null 2>&1
xorriso -osirrox on -indev "$ISO" -extract /limad/rootfs/usr/share/icons/hicolor/256x256/apps/de.limad.Study.png "$TMP/hicolor-study.png" >/dev/null 2>&1
xorriso -osirrox on -indev "$ISO" -extract /limad/rootfs/usr/lib/systemd/user/limad-link.service "$TMP/limad-link.service" >/dev/null 2>&1
xorriso -osirrox on -indev "$ISO" -extract /limad/rootfs/usr/local/bin/limad-link-health-check "$TMP/limad-link-health-check" >/dev/null 2>&1
xorriso -osirrox on -indev "$ISO" -extract /limad/rootfs/usr/share/limad-drop/web/app.js "$TMP/lidrop-app.js" >/dev/null 2>&1
xorriso -osirrox on -indev "$ISO" -extract /limad/rootfs/usr/share/limad-drop/limad_dropd.py "$TMP/lidrop-daemon.py" >/dev/null 2>&1
xorriso -osirrox on -indev "$ISO" -extract /limad/rootfs/usr/lib/firmware/radeon/BONAIRE_uvd.bin "$TMP/BONAIRE_uvd.bin" >/dev/null 2>&1
xorriso -osirrox on -indev "$ISO" -extract /limad/rootfs/usr/share/doc/limad-os-base1/firmware/LICENSE.radeon "$TMP/LICENSE.radeon" >/dev/null 2>&1

grep -Fq 'id: ubuntu-desktop' "$TMP/autoinstall.yaml"
grep -Fq 'search_drivers: true' "$TMP/autoinstall.yaml"
python3 -B "$ROOT/tools/validate-install-sources.py" "$TMP/install-sources.yaml"

INSTALL_SOURCES_MD5="$(md5sum "$TMP/install-sources.yaml" | awk '{print $1}')"
INITRD_MD5="$(md5sum "$TMP/initrd" | awk '{print $1}')"
GRUB_MD5="$(md5sum "$TMP/grub.cfg" | awk '{print $1}')"
grep -Fq "$INSTALL_SOURCES_MD5  ./casper/install-sources.yaml" "$TMP/md5sum.txt"
grep -Fq "$INITRD_MD5  ./casper/initrd" "$TMP/md5sum.txt"
grep -Fq "$GRUB_MD5  ./boot/grub/grub.cfg" "$TMP/md5sum.txt"

grep -Fq 'LiMaD OS' "$TMP/grub.cfg"
grep -Fq 'iMac17,1' "$TMP/grub.cfg"
grep -Fq 'radeon.cik_support=1 amdgpu.cik_support=0' "$TMP/grub.cfg"
grep -Fq 'smbios --type 1 --get-string 5 --set limad_system_product' "$TMP/grub.cfg"
grep -Fq 'BUILD="base1-ubuntu2604-full-whitesur-v17"' "$TMP/limad-release"
grep -Fq '[Icon Theme]' "$TMP/index.theme"
test -s "$TMP/gtk4.css"
grep -Fq 'windowcontrols button.close' "$TMP/gtk4.css"
grep -Fq 'url("limad-assets/close.svg")' "$TMP/gtk4.css"
test -s "$TMP/close.svg"
test -s "$TMP/hicolor-study.png"
grep -Fq '"shell-version": ["50"]' "$TMP/lilink-metadata.json"
grep -Fq '"shell-version": ["50"]' "$TMP/lidrop-metadata.json"
grep -Fq '"shell-version": ["50"]' "$TMP/limad-menu-metadata.json"
grep -Fq 'Main.panel.addToStatusArea(this.uuid, this._indicator);' "$TMP/lilink-extension.js"
grep -Fq 'Main.panel.addToStatusArea(this.uuid, this._indicator);' "$TMP/lidrop-extension.js"
grep -Fq "Main.panel.addToStatusArea(this.uuid, this._indicator, 0, 'left');" "$TMP/limad-menu-extension.js"
grep -Fq 'ExecStart=/usr/bin/python3 /usr/share/limad-link/daemon.py' "$TMP/limad-link.service"
grep -Fq 'systemctl --user enable --now limad-link.service' "$TMP/limad-link-health-check"
if grep -Eqi 'airdrop|opendrop|awdl|owl' "$TMP/lidrop-app.js" "$TMP/lidrop-daemon.py"; then
    echo 'ERROR: AirDrop compatibility remains in built ISO LiDrop UI/backend' >&2
    exit 1
fi
grep -Fq 'update-initramfs -u' "$TMP/design-system"
grep -Fq "dock-position='BOTTOM'" "$TMP/desktop-core-system"
grep -Fq "icon-theme='LiMaD'" "$TMP/desktop-core-system"
grep -Fq "always-center-icons=true" "$TMP/desktop-core-system"
grep -Fq "show-apps-always-in-the-edge=false" "$TMP/desktop-core-system"
grep -Fq "[org/gnome/shell]" "$TMP/desktop-core-system"
grep -Fq "favorite-apps=['firefox_firefox.desktop'" "$TMP/desktop-core-system"
grep -Fq "'de.limad.Mail.desktop'" "$TMP/desktop-core-system"
grep -Fq "'de.limad.Drop.desktop'" "$TMP/desktop-core-system"
grep -Fq "'de.limad.Link.desktop'" "$TMP/desktop-core-system"
grep -Fq 'iMac17,1' "$TMP/install-target.sh"
grep -Fq 'options radeon cik_support=1' "$TMP/install-target.sh"
grep -Fq 'options amdgpu cik_support=0' "$TMP/install-target.sh"

# The first uncompressed initramfs CPIO contains early Radeon firmware and the
# casper-bottom hook that installs Canonical's whitelabel files into live root.
for marker in \
    'usr/lib/firmware/radeon/BONAIRE_uvd.bin' \
    'scripts/casper-bottom/62limad-branding' \
    'limad-installer/whitelabel.yaml' \
    'LiMaD OS Installer' \
    'Willkommen bei LiMaD OS 3.0'; do
    if ! grep -aFq "$marker" "$TMP/initrd"; then
        echo "ERROR: V17 initrd marker missing: $marker" >&2
        exit 1
    fi
done

EXPECTED_FW_SHA="$(awk '$2 == "radeon/BONAIRE_uvd.bin" {print $1}' "$ROOT/assets/firmware/SHA256SUMS.txt")"
ACTUAL_FW_SHA="$(sha256sum "$TMP/BONAIRE_uvd.bin" | awk '{print $1}')"
if [ "$ACTUAL_FW_SHA" != "$EXPECTED_FW_SHA" ]; then
    echo "ERROR: Installed Bonaire firmware hash mismatch" >&2
    exit 1
fi
cmp -s "$ROOT/assets/firmware/LICENSE.radeon" "$TMP/LICENSE.radeon"

python3 - "$TMP/wallpaper.png" <<'PY'
import pathlib
import struct
import sys

data = pathlib.Path(sys.argv[1]).read_bytes()
if data[:8] != b"\x89PNG\r\n\x1a\n":
    raise SystemExit("ERROR: default wallpaper in ISO is not PNG")
if struct.unpack(">II", data[16:24]) != (3840, 2160):
    raise SystemExit("ERROR: default wallpaper in ISO is not 3840x2160")
PY

xorriso -indev "$ISO" -report_el_torito plain 2>/dev/null | grep -Eiq 'EFI|UEFI'
xorriso -indev "$ISO" -pvd_info 2>/dev/null | grep -Eiq 'Volume [Ii]d.*LIMAD_OS_3_0_RC1'

echo "ISO STATIC VALIDATION: PASS"
