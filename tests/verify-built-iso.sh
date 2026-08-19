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
CURRENT_STAGE="initialization"
trap 'rc=$?; echo "ERROR: ISO static validation failed in stage: $CURRENT_STAGE (line $LINENO, exit $rc)" >&2; exit $rc' ERR

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
xorriso -osirrox on -indev "$ISO" -extract /limad/rootfs/usr/local/bin/limad-required-user-apps "$TMP/required-user-apps" >/dev/null 2>&1
xorriso -osirrox on -indev "$ISO" -extract /limad/rootfs/usr/local/bin/limad-titlebuttons-ensure "$TMP/titlebuttons-ensure" >/dev/null 2>&1
xorriso -osirrox on -indev "$ISO" -extract /limad/rootfs/usr/local/bin/limusic "$TMP/limusic" >/dev/null 2>&1
xorriso -osirrox on -indev "$ISO" -extract /limad/rootfs/usr/share/limusic/VERSION "$TMP/limusic-version" >/dev/null 2>&1
xorriso -osirrox on -indev "$ISO" -extract /limad/rootfs/usr/share/limusic/src/limusic/adblock_engine.py "$TMP/limusic-adblock-engine.py" >/dev/null 2>&1
xorriso -osirrox on -indev "$ISO" -extract /limad/rootfs/usr/share/limusic/data/adblock-scriptlet-rules.json "$TMP/limusic-adblock-rules.json" >/dev/null 2>&1
xorriso -osirrox on -indev "$ISO" -extract /limad/rootfs/usr/share/limad-updater/apps.json "$TMP/updater-apps.json" >/dev/null 2>&1
xorriso -osirrox on -indev "$ISO" -extract /limad/rootfs/usr/local/libexec/limad-select-app-root "$TMP/select-app-root" >/dev/null 2>&1
xorriso -osirrox on -indev "$ISO" -extract /limad/rootfs/usr/local/bin/liview "$TMP/liview" >/dev/null 2>&1
xorriso -osirrox on -indev "$ISO" -extract /limad/rootfs/usr/local/bin/limad-liview-deps "$TMP/limad-liview-deps" >/dev/null 2>&1
xorriso -osirrox on -indev "$ISO" -extract /limad/rootfs/usr/share/liview/VERSION "$TMP/liview-version" >/dev/null 2>&1
xorriso -osirrox on -indev "$ISO" -extract /limad/rootfs/usr/share/applications/de.limad.LiView.desktop "$TMP/liview.desktop" >/dev/null 2>&1
xorriso -osirrox on -indev "$ISO" -extract /limad/rootfs/etc/xdg/mimeapps.list "$TMP/mimeapps.list" >/dev/null 2>&1
xorriso -osirrox on -indev "$ISO" -extract /limad/rootfs/usr/share/mime/packages/de.limad.LiView.xml "$TMP/liview-mime.xml" >/dev/null 2>&1
xorriso -osirrox on -indev "$ISO" -extract /limad/rootfs/usr/share/icons/hicolor/256x256/apps/de.limad.LiView.png "$TMP/liview-icon.png" >/dev/null 2>&1
xorriso -osirrox on -indev "$ISO" -extract /limad/rootfs/usr/share/limad/offline/liview/Packages.gz "$TMP/liview-Packages.gz" >/dev/null 2>&1
xorriso -osirrox on -indev "$ISO" -extract /limad/rootfs/usr/share/limad/offline/liview/SHA256SUMS.txt "$TMP/liview-SHA256SUMS.txt" >/dev/null 2>&1
xorriso -osirrox on -indev "$ISO" -extract /limad/rootfs/usr/local/bin/limad-gaming-deps "$TMP/limad-gaming-deps" >/dev/null 2>&1
xorriso -osirrox on -indev "$ISO" -extract /limad/rootfs/usr/share/limad/gaming/REQUIRED-PACKAGES.txt "$TMP/gaming-packages.txt" >/dev/null 2>&1
xorriso -osirrox on -indev "$ISO" -extract /limad/rootfs/usr/share/limad/offline/gaming/Packages.gz "$TMP/gaming-Packages.gz" >/dev/null 2>&1
xorriso -osirrox on -indev "$ISO" -extract /limad/rootfs/usr/share/limad/offline/gaming/SHA256SUMS.txt "$TMP/gaming-SHA256SUMS.txt" >/dev/null 2>&1
xorriso -osirrox on -indev "$ISO" -extract /limad/rootfs/usr/share/limad-notes/app.py "$TMP/linotes-app.py" >/dev/null 2>&1
xorriso -osirrox on -indev "$ISO" -extract /limad/rootfs/usr/share/limad-windows/installer.py "$TMP/windows-installer.py" >/dev/null 2>&1
xorriso -osirrox on -indev "$ISO" -extract /limad/rootfs/usr/share/gnome-shell/extensions/lilink@limad.local/metadata.json "$TMP/lilink-metadata.json" >/dev/null 2>&1
xorriso -osirrox on -indev "$ISO" -extract /limad/rootfs/usr/share/gnome-shell/extensions/lilink@limad.local/extension.js "$TMP/lilink-extension.js" >/dev/null 2>&1
xorriso -osirrox on -indev "$ISO" -extract /limad/rootfs/usr/share/gnome-shell/extensions/lidrop@limad.local/metadata.json "$TMP/lidrop-metadata.json" >/dev/null 2>&1
xorriso -osirrox on -indev "$ISO" -extract /limad/rootfs/usr/share/gnome-shell/extensions/lidrop@limad.local/extension.js "$TMP/lidrop-extension.js" >/dev/null 2>&1
xorriso -osirrox on -indev "$ISO" -extract /limad/rootfs/usr/share/gnome-shell/extensions/limad-menu@limad.local/metadata.json "$TMP/limad-menu-metadata.json" >/dev/null 2>&1
xorriso -osirrox on -indev "$ISO" -extract /limad/rootfs/usr/share/gnome-shell/extensions/limad-menu@limad.local/extension.js "$TMP/limad-menu-extension.js" >/dev/null 2>&1
xorriso -osirrox on -indev "$ISO" -extract /limad/rootfs/usr/share/icons/hicolor/256x256/apps/de.limad.Study.png "$TMP/hicolor-study.png" >/dev/null 2>&1
xorriso -osirrox on -indev "$ISO" -extract /limad/rootfs/usr/lib/systemd/user/limad-link.service "$TMP/limad-link.service" >/dev/null 2>&1
xorriso -osirrox on -indev "$ISO" -extract /limad/rootfs/usr/lib/systemd/user/limad-drop.service "$TMP/limad-drop.service" >/dev/null 2>&1
xorriso -osirrox on -indev "$ISO" -extract /limad/rootfs/usr/local/bin/limad-lidrop-status-ensure "$TMP/limad-lidrop-status-ensure" >/dev/null 2>&1
xorriso -osirrox on -indev "$ISO" -extract /limad/rootfs/usr/local/bin/limad-link-health-check "$TMP/limad-link-health-check" >/dev/null 2>&1
xorriso -osirrox on -indev "$ISO" -extract /limad/rootfs/usr/share/limad-drop/web/app.js "$TMP/lidrop-app.js" >/dev/null 2>&1
xorriso -osirrox on -indev "$ISO" -extract /limad/rootfs/usr/share/limad-drop/limad_dropd.py "$TMP/lidrop-daemon.py" >/dev/null 2>&1
xorriso -osirrox on -indev "$ISO" -extract /limad/rootfs/usr/lib/firmware/radeon/BONAIRE_uvd.bin "$TMP/BONAIRE_uvd.bin" >/dev/null 2>&1
xorriso -osirrox on -indev "$ISO" -extract /limad/rootfs/usr/share/doc/limad-os-base1/firmware/LICENSE.radeon "$TMP/LICENSE.radeon" >/dev/null 2>&1

CURRENT_STAGE="autoinstall and install sources"
grep -Fq 'id: ubuntu-desktop' "$TMP/autoinstall.yaml"
grep -Fq 'search_drivers: true' "$TMP/autoinstall.yaml"
python3 -B "$ROOT/tools/validate-install-sources.py" "$TMP/install-sources.yaml"
echo "ISO VALIDATION: autoinstall/install sources PASS"

CURRENT_STAGE="ISO md5 manifest"
INSTALL_SOURCES_MD5="$(md5sum "$TMP/install-sources.yaml" | awk '{print $1}')"
INITRD_MD5="$(md5sum "$TMP/initrd" | awk '{print $1}')"
GRUB_MD5="$(md5sum "$TMP/grub.cfg" | awk '{print $1}')"
manifest_md5() {
    local target="$1"
    awk -v target="./$target" '{ path=$2; sub(/^\*/, "", path); if (path == target) { print $1; exit } }' "$TMP/md5sum.txt"
}
[ "$(manifest_md5 casper/install-sources.yaml)" = "$INSTALL_SOURCES_MD5" ]
[ "$(manifest_md5 casper/initrd)" = "$INITRD_MD5" ]
[ "$(manifest_md5 boot/grub/grub.cfg)" = "$GRUB_MD5" ]
echo "ISO VALIDATION: md5 overlay PASS"

CURRENT_STAGE="GRUB and release marker"
grep -Fq 'LiMaD OS' "$TMP/grub.cfg"
grep -Fq 'iMac17,1' "$TMP/grub.cfg"
grep -Fq 'radeon.cik_support=1 amdgpu.cik_support=0' "$TMP/grub.cfg"
grep -Fq 'smbios --type 1 --get-string 5 --set limad_system_product' "$TMP/grub.cfg"
EXPECTED_BUILD_MARKER='BUILD="base1-ubuntu2604-full-whitesur-v24"'
if ! grep -Fxq "$EXPECTED_BUILD_MARKER" "$TMP/limad-release"; then
    echo "ERROR: Built ISO release marker mismatch." >&2
    echo "Expected: $EXPECTED_BUILD_MARKER" >&2
    echo "Found:" >&2
    cat "$TMP/limad-release" >&2
    exit 1
fi
echo "ISO VALIDATION: GRUB/release marker PASS"
CURRENT_STAGE="desktop and LiMaD services"
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
grep -Fq 'ExecStart=/usr/local/bin/limad-dropd' "$TMP/limad-drop.service"
grep -Fq 'WantedBy=default.target' "$TMP/limad-drop.service"
grep -Fq 'systemctl --user enable --now limad-drop.service' "$TMP/limad-lidrop-status-ensure"
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
grep -Fq "favorite-apps=['app.zen_browser.zen.desktop'" "$TMP/desktop-core-system"
if grep -Fq 'firefox_firefox.desktop' "$TMP/desktop-core-system"; then
    echo 'ERROR: Firefox remains in V22 Dock defaults' >&2
    exit 1
fi
grep -Fq 'app.zen_browser.zen' "$TMP/required-user-apps"
grep -Fq 'com.github.wwmm.easyeffects' "$TMP/required-user-apps"
grep -Fq 'net.davidotek.pupgui2' "$TMP/required-user-apps"
grep -Fq 'limad-sync-gtk4-theme' "$TMP/titlebuttons-ensure"
echo "ISO VALIDATION: desktop/services PASS"
CURRENT_STAGE="LiMusic LiView and gaming payload"
grep -Fq 'de.limad.LiMusic' "$TMP/updater-apps.json"
grep -Fq 'de.limad.LiView' "$TMP/updater-apps.json"
[ "$(cat "$TMP/liview-version")" = "1.0.0" ]
grep -Fq '/usr/local/libexec/limad-select-app-root' "$TMP/liview"
grep -Fq 'Exec=/usr/local/bin/liview %F' "$TMP/liview.desktop"
grep -Fq 'application/pdf=de.limad.LiView.desktop' "$TMP/mimeapps.list"
grep -Fq 'video/x-liview-raw=de.limad.LiView.desktop' "$TMP/mimeapps.list"
grep -Fq 'video/x-liview-mpeg=de.limad.LiView.desktop' "$TMP/mimeapps.list"
grep -Fq 'image/svg+xml-compressed=de.limad.LiView.desktop' "$TMP/mimeapps.list"
test -s "$TMP/select-app-root"
test -s "$TMP/liview-mime.xml"
test -s "$TMP/liview-icon.png"
test -s "$TMP/liview-Packages.gz"
test -s "$TMP/liview-SHA256SUMS.txt"
grep -Fq '/usr/share/limad/offline/liview' "$TMP/limad-liview-deps"
test -s "$TMP/limad-gaming-deps"
test -s "$TMP/gaming-packages.txt"
test -s "$TMP/gaming-Packages.gz"
test -s "$TMP/gaming-SHA256SUMS.txt"
grep -Fq '/usr/share/limad/offline/gaming' "$TMP/limad-gaming-deps"
grep -Fq 'dpkg --add-architecture i386' "$TMP/limad-gaming-deps"
for package in steam-installer steam-devices lutris protontricks wine wine32:i386 winetricks gamemode mangohud gamescope vulkan-tools mesa-vulkan-drivers:i386 libvulkan1:i386 libglx-mesa0:i386; do
    grep -Fxq "$package" "$TMP/gaming-packages.txt"
done
[ "$(cat "$TMP/limusic-version")" = "0.3.22" ]
grep -Fq 'ENGINE_BOOTSTRAP_SCRIPT' "$TMP/limusic-adblock-engine.py"
grep -Fq 'trusted-replace-fetch-response' "$TMP/limusic-adblock-rules.json"
grep -Fq 'header.set_show_title_buttons(True)' "$TMP/linotes-app.py"
grep -Fq 'header.set_show_start_title_buttons(True)' "$TMP/windows-installer.py"
grep -Fq "'de.limad.Mail.desktop'" "$TMP/desktop-core-system"
grep -Fq "'de.limad.Drop.desktop'" "$TMP/desktop-core-system"
grep -Fq "'de.limad.Link.desktop'" "$TMP/desktop-core-system"
grep -Fq 'iMac17,1' "$TMP/install-target.sh"
grep -Fq 'options radeon cik_support=1' "$TMP/install-target.sh"
grep -Fq 'options amdgpu cik_support=0' "$TMP/install-target.sh"
echo "ISO VALIDATION: LiMusic/LiView/gaming PASS"
CURRENT_STAGE="initrd firmware and wallpaper"

# The first uncompressed initramfs CPIO contains early Radeon firmware and the
# casper-bottom hook that installs Canonical's whitelabel files into live root.
for marker in \
    'usr/lib/firmware/radeon/BONAIRE_uvd.bin' \
    'scripts/casper-bottom/62limad-branding' \
    'limad-installer/whitelabel.yaml' \
    'LiMaD OS Installer' \
    'Willkommen bei LiMaD OS 3.0'; do
    if ! grep -aFq "$marker" "$TMP/initrd"; then
        echo "ERROR: V22 initrd marker missing: $marker" >&2
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

echo "ISO VALIDATION: initrd/firmware/wallpaper PASS"
CURRENT_STAGE="El Torito and ISO volume metadata"
EL_TORITO_REPORT="$TMP/el-torito.txt"
PVD_REPORT="$TMP/pvd-info.txt"
xorriso -indev "$ISO" -report_el_torito plain >"$EL_TORITO_REPORT" 2>&1
grep -Eiq 'EFI|UEFI' "$EL_TORITO_REPORT"
xorriso -indev "$ISO" -pvd_info >"$PVD_REPORT" 2>&1
grep -Eiq 'Volume [Ii]d.*LIMAD_OS_3_0_RC1' "$PVD_REPORT"
echo "ISO VALIDATION: boot metadata/volume ID PASS"
CURRENT_STAGE="complete"
trap - ERR
echo "ISO STATIC VALIDATION: PASS"
