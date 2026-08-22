#!/usr/bin/bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PAYLOAD="$ROOT/.cache/payload"
ROOTFS="$PAYLOAD/rootfs"

required=(
    "$PAYLOAD/install-target.sh"
    "$ROOTFS/usr/share/icons/LiMaD/index.theme"
    "$ROOTFS/usr/share/backgrounds/limad/LiMaD-Wallpaper-01-Logo-Links-4K.png"
    "$ROOTFS/usr/share/backgrounds/limad/LiMaD-Wallpaper-02-Logo-Zentriert-4K.png"
    "$ROOTFS/usr/share/backgrounds/limad/LiMaD-Wallpaper-03-Wellen-Emblem-4K.png"
    "$ROOTFS/usr/share/gnome-background-properties/limad-wallpapers.xml"
    "$ROOTFS/usr/share/limad/gtk4/gtk.css"
    "$ROOTFS/usr/share/limad/gtk4/limad-assets/close.svg"
    "$ROOTFS/usr/share/limad/gtk4/limad-assets/minimize.svg"
    "$ROOTFS/usr/share/limad/gtk4/limad-assets/maximize.svg"
    "$ROOTFS/usr/share/limad/gtk4/limad-assets/close-hover.svg"
    "$ROOTFS/usr/share/limad/gtk4/limad-assets/minimize-hover.svg"
    "$ROOTFS/usr/share/limad/gtk4/limad-assets/maximize-hover.svg"
    "$ROOTFS/usr/share/gnome-shell/extensions/lilink@limad.local/metadata.json"
    "$ROOTFS/usr/share/gnome-shell/extensions/lilink@limad.local/extension.js"
    "$ROOTFS/usr/share/gnome-shell/extensions/lilink@limad.local/lilink.svg"
    "$ROOTFS/usr/share/gnome-shell/extensions/lidrop@limad.local/metadata.json"
    "$ROOTFS/usr/share/gnome-shell/extensions/lidrop@limad.local/extension.js"
    "$ROOTFS/usr/share/gnome-shell/extensions/lidrop@limad.local/lidrop.svg"
    "$ROOTFS/usr/share/gnome-shell/extensions/limad-menu@limad.local/metadata.json"
    "$ROOTFS/usr/share/gnome-shell/extensions/limad-menu@limad.local/extension.js"
    "$ROOTFS/usr/share/gnome-shell/extensions/limad-appgrid-labels@limad.local/metadata.json"
    "$ROOTFS/usr/share/gnome-shell/extensions/limad-appgrid-labels@limad.local/extension.js"
    "$ROOTFS/usr/share/gnome-shell/extensions/limad-appgrid-labels@limad.local/stylesheet.css"
    "$ROOTFS/usr/lib/systemd/user/limad-link.service"
    "$ROOTFS/usr/lib/systemd/user/limad-drop.service"
    "$ROOTFS/usr/local/bin/limad-lidrop-status-ensure"
    "$ROOTFS/usr/local/bin/limad-link-health-check"
    "$ROOTFS/usr/local/bin/limad-link-status-ensure"
    "$ROOTFS/usr/share/limad-link/app.py"
    "$ROOTFS/usr/share/limad-link/daemon.py"
    "$ROOTFS/usr/share/limad-link/common.py"
    "$ROOTFS/usr/share/limad-drop/limad_dropd.py"
    "$ROOTFS/usr/share/limad-drop/web/app.js"
    "$ROOTFS/usr/share/limad/branding/limad-logo-192.png"
    "$ROOTFS/usr/share/limad/branding/limad-logo-256.png"
    "$ROOTFS/usr/lib/firmware/radeon/BONAIRE_ce.bin"
    "$ROOTFS/usr/lib/firmware/radeon/BONAIRE_mc.bin"
    "$ROOTFS/usr/lib/firmware/radeon/BONAIRE_mc2.bin"
    "$ROOTFS/usr/lib/firmware/radeon/BONAIRE_me.bin"
    "$ROOTFS/usr/lib/firmware/radeon/BONAIRE_mec.bin"
    "$ROOTFS/usr/lib/firmware/radeon/BONAIRE_pfp.bin"
    "$ROOTFS/usr/lib/firmware/radeon/BONAIRE_rlc.bin"
    "$ROOTFS/usr/lib/firmware/radeon/BONAIRE_sdma.bin"
    "$ROOTFS/usr/lib/firmware/radeon/BONAIRE_smc.bin"
    "$ROOTFS/usr/lib/firmware/radeon/BONAIRE_uvd.bin"
    "$ROOTFS/usr/lib/firmware/radeon/BONAIRE_vce.bin"
    "$ROOTFS/usr/share/doc/limad-os-base1/firmware/LICENSE.radeon"
    "$ROOTFS/usr/local/bin/limad-base1-first-login"
    "$ROOTFS/usr/local/bin/limad-sync-gtk4-theme"
    "$ROOTFS/usr/local/bin/limad-titlebuttons-ensure"
    "$ROOTFS/usr/local/bin/limad-required-user-apps"
    "$ROOTFS/usr/local/bin/limad-zen-voltroute-bookmark"
    "$ROOTFS/usr/local/bin/limusic"
    "$ROOTFS/etc/xdg/autostart/limad-titlebuttons-ensure.desktop"
    "$ROOTFS/etc/xdg/autostart/limad-required-user-apps.desktop"
    "$ROOTFS/usr/share/limusic/VERSION"
    "$ROOTFS/usr/share/limad-windows/VERSION"
    "$ROOTFS/usr/share/limad-windows/installer.py"
    "$ROOTFS/usr/share/limad-windows/recipe_engine.py"
    "$ROOTFS/usr/share/limad-windows/wine-env.sh"
    "$ROOTFS/usr/share/limusic/data/adblock-scriptlet-rules.json"
    "$ROOTFS/usr/share/limusic/data/youtube-adblock-webkit.json"
    "$ROOTFS/usr/share/limusic/src/limusic/adblock_engine.py"
    "$ROOTFS/usr/share/limusic/src/limusic/app.py"
    "$ROOTFS/usr/share/limad-updater/apps.json"
    "$ROOTFS/usr/local/bin/limad-design-system"
    "$ROOTFS/usr/local/bin/limad-desktop-core-system"
    "$ROOTFS/usr/local/libexec/limad-select-app-root"
    "$ROOTFS/usr/local/bin/liview"
    "$ROOTFS/usr/local/bin/limad-liview-deps"
    "$ROOTFS/usr/share/liview/VERSION"
    "$ROOTFS/usr/share/liview/liview/__main__.py"
    "$ROOTFS/usr/share/liview/liview/app.py"
    "$ROOTFS/usr/share/liview/liview/documents.py"
    "$ROOTFS/usr/share/applications/de.limad.LiView.desktop"
    "$ROOTFS/usr/share/mime/packages/de.limad.LiView.xml"
    "$ROOTFS/etc/xdg/mimeapps.list"
    "$ROOTFS/usr/share/limad/offline/liview/Packages.gz"
    "$ROOTFS/usr/share/limad/offline/liview/SHA256SUMS.txt"
    "$ROOTFS/usr/local/bin/limad-gaming-deps"
    "$ROOTFS/usr/share/limad/gaming/REQUIRED-PACKAGES.txt"
    "$ROOTFS/usr/share/limad/offline/gaming/Packages.gz"
    "$ROOTFS/usr/share/limad/offline/gaming/SHA256SUMS.txt"
    "$ROOTFS/usr/local/bin/limad-heroic-deps"
    "$ROOTFS/usr/share/limad/offline/heroic/Packages.gz"
    "$ROOTFS/usr/share/limad/offline/heroic/SHA256SUMS.txt"
    "$ROOTFS/usr/share/limad/offline/heroic/PACKAGE-NAME.txt"
    "$ROOTFS/usr/share/limad/offline/heroic/PACKAGE-VERSION.txt"
    "$ROOTFS/usr/local/bin/limad-grubenvolk"
    "$ROOTFS/usr/local/bin/limad-grubenvolk-deps"
    "$ROOTFS/usr/share/limad-grubenvolk/VERSION"
    "$ROOTFS/usr/share/limad-grubenvolk/web/index.html"
    "$ROOTFS/usr/share/applications/de.limad.Grubenvolk.desktop"
    "$ROOTFS/usr/share/limad/offline/grubenvolk/Packages.gz"
    "$ROOTFS/usr/share/limad/offline/grubenvolk/SHA256SUMS.txt"
    "$ROOTFS/usr/bin/anycubicslicernext"
    "$ROOTFS/usr/local/bin/limad-anycubic-deps"
    "$ROOTFS/usr/lib/limad/apps/anycubic-slicer-next/bin/AnycubicSlicerNext"
    "$ROOTFS/usr/lib/limad/apps/anycubic-slicer-next/resources/build-version.txt"
    "$ROOTFS/usr/share/applications/de.limad.AnycubicSlicerNext.desktop"
    "$ROOTFS/usr/share/metainfo/de.limad.AnycubicSlicerNext.metainfo.xml"
    "$ROOTFS/usr/share/limad-anycubic/REQUIRED-PACKAGES.txt"
    "$ROOTFS/usr/share/limad/offline/anycubic/Packages.gz"
    "$ROOTFS/usr/share/limad/offline/anycubic/SHA256SUMS.txt"
    "$ROOTFS/etc/limad-release"
)

for path in "${required[@]}"; do
    if [ ! -e "$path" ]; then
        echo "ERROR: Required payload path missing: $path" >&2
        exit 1
    fi
done

applications=(
    de.limad.AnycubicSlicerNext.desktop
    de.limad.Cut.desktop
    de.limad.Drop.desktop
    de.limad.Grubenvolk.desktop
    de.limad.Klang.desktop
    de.limad.Link.desktop
    de.limad.LiMusic.desktop
    de.limad.LiView.desktop
    de.limad.Mail.desktop
    de.limad.Notes.desktop
    de.limad.Recovery.desktop
    de.limad.Save.desktop
    de.limad.ScreenShare.desktop
    de.limad.Study.desktop
    de.limad.SystemInfo.desktop
    de.limad.SystemUpdate.desktop
    de.limad.Terminal.desktop
    de.limad.Updater.desktop
    de.limad.Welcome.desktop
    de.limad.WindowsApps.desktop
    de.limad.WindowsRun.desktop
)

for desktop in "${applications[@]}"; do
    if [ ! -f "$ROOTFS/usr/share/applications/$desktop" ]; then
        echo "ERROR: LiMaD desktop launcher missing: $desktop" >&2
        exit 1
    fi
done

shopt -s nullglob
WHITESUR_DIRS=("$ROOTFS/usr/share/themes"/WhiteSur*)
shopt -u nullglob
if [ "${#WHITESUR_DIRS[@]}" -eq 0 ]; then
    echo "ERROR: WhiteSur theme missing from payload" >&2
    exit 1
fi

grep -Fq 'windowcontrols button.close' "$ROOTFS/usr/share/limad/gtk4/gtk.css"
grep -Fq 'url("limad-assets/close.svg")' "$ROOTFS/usr/share/limad/gtk4/gtk.css"
grep -Fq 'url("limad-assets/minimize.svg")' "$ROOTFS/usr/share/limad/gtk4/gtk.css"
grep -Fq 'url("limad-assets/maximize.svg")' "$ROOTFS/usr/share/limad/gtk4/gtk.css"
grep -Fq 'windowcontrols:hover button.close' "$ROOTFS/usr/share/limad/gtk4/gtk.css"
grep -Fq 'url("limad-assets/close-hover.svg")' "$ROOTFS/usr/share/limad/gtk4/gtk.css"
grep -Fq 'url("limad-assets/minimize-hover.svg")' "$ROOTFS/usr/share/limad/gtk4/gtk.css"
grep -Fq 'url("limad-assets/maximize-hover.svg")' "$ROOTFS/usr/share/limad/gtk4/gtk.css"
for uuid in lilink@limad.local lidrop@limad.local; do
    grep -Fq '"shell-version": ["50"]' "$ROOTFS/usr/share/gnome-shell/extensions/$uuid/metadata.json"
    grep -Fq 'Main.panel.addToStatusArea(this.uuid, this._indicator);' "$ROOTFS/usr/share/gnome-shell/extensions/$uuid/extension.js"
done

grep -Fq "Main.panel.addToStatusArea(this.uuid, this._indicator, 0, 'left');" "$ROOTFS/usr/share/gnome-shell/extensions/limad-menu@limad.local/extension.js"
grep -Fq '"shell-version": ["50"]' "$ROOTFS/usr/share/gnome-shell/extensions/limad-appgrid-labels@limad.local/metadata.json"
grep -Fq 'line_wrap: true' "$ROOTFS/usr/share/gnome-shell/extensions/limad-appgrid-labels@limad.local/extension.js"
grep -Fq 'max-height: 2.4em;' "$ROOTFS/usr/share/gnome-shell/extensions/limad-appgrid-labels@limad.local/stylesheet.css"

for desktop in "${applications[@]}"; do
    icon="$(awk -F= '$1 == "Icon" {print substr($0, 6); exit}' "$ROOTFS/usr/share/applications/$desktop")"
    case "$icon" in
        ''|/*) continue ;;
    esac
    for size in 64x64 128x128 256x256; do
        if [ ! -s "$ROOTFS/usr/share/icons/hicolor/$size/apps/$icon.png" ]; then
            echo "ERROR: hicolor fallback missing for $desktop ($icon, $size)" >&2
            exit 1
        fi
    done
done

for forbidden in \
    limad-default-flatpaks.desktop \
    limad-easyeffects-service.desktop \
    limad-firefox-theme.desktop \
    limad-first-login.desktop \
    limad-lidrop-status.desktop \
    limad-zen-deutsch.desktop; do
    if [ -e "$ROOTFS/etc/xdg/autostart/$forbidden" ]; then
        echo "ERROR: Forbidden BASE1B autostart remains: $forbidden" >&2
        exit 1
    fi
done

grep -Fq 'LiMaD-Wallpaper-01-Logo-Links-4K.png' "$ROOTFS/usr/local/bin/limad-base1-first-login"
grep -Fq 'extend-height false' "$ROOTFS/usr/local/bin/limad-base1-first-login"
grep -Fq 'show-apps-always-in-the-edge false' "$ROOTFS/usr/local/bin/limad-base1-first-login"
grep -Fq 'CORE_MARKER=' "$ROOTFS/usr/local/bin/limad-base1-first-login"
grep -Fq 'AUX_MARKER=' "$ROOTFS/usr/local/bin/limad-base1-first-login"
grep -Fq 'org/gnome/login-screen' "$ROOTFS/usr/local/bin/limad-design-system"
grep -Fq 'themes/spinner' "$ROOTFS/usr/local/bin/limad-design-system"
grep -Fq 'update-initramfs -u' "$ROOTFS/usr/local/bin/limad-design-system"

grep -Fq 'ExecStart=/usr/bin/python3 /usr/share/limad-link/daemon.py' "$ROOTFS/usr/lib/systemd/user/limad-link.service"
grep -Fq 'ExecStart=/usr/local/bin/limad-dropd' "$ROOTFS/usr/lib/systemd/user/limad-drop.service"
grep -Fq 'WantedBy=default.target' "$ROOTFS/usr/lib/systemd/user/limad-drop.service"
grep -Fq 'systemctl --user enable --now limad-drop.service' "$ROOTFS/usr/local/bin/limad-lidrop-status-ensure"
grep -Fq '/usr/local/bin/limad-link-health-check' "$ROOTFS/usr/local/bin/limad-link-status-ensure"
if grep -Eqi 'airdrop|opendrop|awdl|owl' "$ROOTFS/usr/share/limad-drop/web/app.js" "$ROOTFS/usr/share/limad-drop/limad_dropd.py"; then
    echo "ERROR: AirDrop compatibility code remains in active LiDrop payload" >&2
    exit 1
fi
for removed in limad-airdrop-check limad-airdrop-control limad-airdrop-session limad-airdrop-wait limad-opendrop-receive; do
    if [ -e "$ROOTFS/usr/local/bin/$removed" ]; then
        echo "ERROR: AirDrop compatibility helper remains: $removed" >&2
        exit 1
    fi
done
grep -Fq 'header.set_show_title_buttons(True)' "$ROOTFS/usr/share/limad-notes/app.py"
grep -Fq 'header.set_decoration_layout("close,maximize,minimize:")' "$ROOTFS/usr/share/limad-notes/app.py"
grep -Fq 'header.set_show_start_title_buttons(True)' "$ROOTFS/usr/share/limad-windows/installer.py"
grep -Fq 'header.set_show_end_title_buttons(False)' "$ROOTFS/usr/share/limad-windows/installer.py"
[ "$(cat "$ROOTFS/usr/share/limad-windows/VERSION")" = "2.2.8" ]
[ "$(cat "$ROOTFS/usr/share/limad-save/VERSION")" = "1.0.2" ]
grep -Fq 'write_backup_archive' "$ROOTFS/usr/share/limad-save/core.py"
grep -Fq 'opened_backup' "$ROOTFS/usr/share/limad-save/core.py"
grep -Fq 'restic_json_stream' "$ROOTFS/usr/share/limad-save/core.py"
grep -Fq 'phase="archive-write"' "$ROOTFS/usr/share/limad-save/core.py"
grep -Fq 'phase="archive-verify"' "$ROOTFS/usr/share/limad-save/core.py"
grep -Fq 'Restzeit: ca.' "$ROOTFS/usr/share/limad-save/app.py"
grep -Fq 'Ende ca.' "$ROOTFS/usr/share/limad-save/app.py"
grep -Fq 'Quelle:' "$ROOTFS/usr/share/limad-save/app.py"
grep -Fq 'Ziel:' "$ROOTFS/usr/share/limad-save/app.py"
grep -Fq '*.lisavebackup.zip' "$ROOTFS/usr/local/bin/limad-save-first-login-detect"
grep -Fq 'APP_VERSION = "2.2.8"' "$ROOTFS/usr/share/limad-windows/installer.py"
grep -Fq 'header.set_decoration_layout("close,maximize,minimize:")' "$ROOTFS/usr/share/limad-windows/installer.py"
grep -Fq 'app.zen_browser.zen' "$ROOTFS/usr/local/bin/limad-required-user-apps"
grep -Fq 'org.fedoraproject.MediaWriter' "$ROOTFS/usr/local/bin/limad-required-user-apps"
grep -Fq 'limad-zen-voltroute-bookmark' "$ROOTFS/usr/local/bin/limad-required-user-apps"
grep -Fq 'https://volteroute.netlify.app/' "$ROOTFS/usr/local/bin/limad-zen-voltroute-bookmark"
grep -Fq 'app.zen_browser.zen.systemconfig' "$ROOTFS/usr/local/bin/limad-zen-voltroute-bookmark"
grep -Fq 'com.github.wwmm.easyeffects' "$ROOTFS/usr/local/bin/limad-required-user-apps"
grep -Fq 'net.davidotek.pupgui2' "$ROOTFS/usr/local/bin/limad-required-user-apps"
grep -Fq 'de.limad.LiMusic' "$ROOTFS/usr/share/limad-updater/apps.json"
[ "$(cat "$ROOTFS/usr/share/limusic/VERSION")" = "0.3.27" ]
grep -Fq 'BUILD="base1-ubuntu2604-full-whitesur-v38"' "$ROOTFS/etc/limad-release"
grep -Fq 'iMac17,1' "$PAYLOAD/install-target.sh"
grep -Fq 'options radeon cik_support=0' "$PAYLOAD/install-target.sh"
grep -Fq 'options amdgpu cik_support=1 dc=0' "$PAYLOAD/install-target.sh"


[ "$(cat "$ROOTFS/usr/share/liview/VERSION")" = "1.1.1" ]
grep -Fq '/usr/local/libexec/limad-select-app-root' "$ROOTFS/usr/local/bin/liview"
grep -Fq 'de.limad.LiView' "$ROOTFS/usr/share/limad-updater/apps.json"
grep -Fq 'Exec=/usr/local/bin/liview %F' "$ROOTFS/usr/share/applications/de.limad.LiView.desktop"
grep -Fq 'application/pdf=de.limad.LiView.desktop' "$ROOTFS/etc/xdg/mimeapps.list"
grep -Fq 'video/x-liview-raw=de.limad.LiView.desktop' "$ROOTFS/etc/xdg/mimeapps.list"
grep -Fq 'video/x-liview-mpeg=de.limad.LiView.desktop' "$ROOTFS/etc/xdg/mimeapps.list"
grep -Fq 'image/svg+xml-compressed=de.limad.LiView.desktop' "$ROOTFS/etc/xdg/mimeapps.list"
shopt -s nullglob
LIVIEW_DEBS=("$ROOTFS/usr/share/limad/offline/liview"/*.deb)
shopt -u nullglob
[ "${#LIVIEW_DEBS[@]}" -gt 0 ]
(
    cd "$ROOTFS/usr/share/limad/offline/liview"
    sha256sum -c SHA256SUMS.txt >/dev/null
)

for package in steam-installer steam-devices lutris protontricks wine wine32:i386 winetricks gamemode mangohud gamescope vulkan-tools mesa-vulkan-drivers:i386 libvulkan1:i386 libglx-mesa0:i386; do
    grep -Fxq "$package" "$ROOTFS/usr/share/limad/gaming/REQUIRED-PACKAGES.txt"
done
shopt -s nullglob
GAMING_DEBS=("$ROOTFS/usr/share/limad/offline/gaming"/*.deb)
shopt -u nullglob
[ "${#GAMING_DEBS[@]}" -gt 0 ]
(
    cd "$ROOTFS/usr/share/limad/offline/gaming"
    sha256sum -c SHA256SUMS.txt >/dev/null
)
grep -Fq '/usr/share/limad/offline/gaming' "$ROOTFS/usr/local/bin/limad-gaming-deps"
grep -Fq 'dpkg --add-architecture i386' "$ROOTFS/usr/local/bin/limad-gaming-deps"

[ "$(cat "$ROOTFS/usr/share/limad/offline/heroic/PACKAGE-VERSION.txt")" = "2.22.0" ]
test -s "$ROOTFS/usr/share/limad/offline/heroic/PACKAGE-NAME.txt"
shopt -s nullglob
HEROIC_DEBS=("$ROOTFS/usr/share/limad/offline/heroic"/*.deb)
shopt -u nullglob
[ "${#HEROIC_DEBS[@]}" -gt 0 ]
(
    cd "$ROOTFS/usr/share/limad/offline/heroic"
    sha256sum -c SHA256SUMS.txt >/dev/null
)
grep -Fq '/usr/share/limad/offline/heroic' "$ROOTFS/usr/local/bin/limad-heroic-deps"
grep -Fq '/usr/local/bin/limad-heroic-deps' "$PAYLOAD/install-target.sh"

[ "$(cat "$ROOTFS/usr/share/limad-grubenvolk/VERSION")" = "3.6.8" ]
grep -Fq '/usr/local/libexec/limad-select-app-root' "$ROOTFS/usr/local/bin/limad-grubenvolk"
grep -Fq 'de.limad.Grubenvolk/current/payload' "$ROOTFS/usr/local/bin/limad-grubenvolk"
grep -Fq 'Exec=/usr/local/bin/limad-grubenvolk' "$ROOTFS/usr/share/applications/de.limad.Grubenvolk.desktop"
grep -Fq 'Exec=/usr/local/bin/limad-updater --app de.limad.Grubenvolk' "$ROOTFS/usr/share/applications/de.limad.Grubenvolk.desktop"
grep -Fq 'de.limad.Grubenvolk' "$ROOTFS/usr/share/limad-updater/apps.json"
grep -Fq 'de.limad.Grubenvolk.desktop' "$ROOTFS/usr/local/bin/limad-desktop-core-system"
if grep -Fq 'favorite-apps' "$ROOTFS/usr/local/bin/limad-base1-first-login"; then
    echo "ERROR: first-login must not write or validate user Dock favorites" >&2
    exit 1
fi
for package in python3 python3-gi gir1.2-gtk-4.0 gir1.2-webkit-6.0; do
    grep -Fxq "$package" "$ROOTFS/usr/share/limad-grubenvolk/REQUIRED-PACKAGES.txt"
done
shopt -s nullglob
GRUBENVOLK_DEBS=("$ROOTFS/usr/share/limad/offline/grubenvolk"/*.deb)
shopt -u nullglob
[ "${#GRUBENVOLK_DEBS[@]}" -gt 0 ]
(
    cd "$ROOTFS/usr/share/limad/offline/grubenvolk"
    sha256sum -c SHA256SUMS.txt >/dev/null
)
grep -Fq '/usr/share/limad/offline/grubenvolk' "$ROOTFS/usr/local/bin/limad-grubenvolk-deps"

[ "$(cat "$ROOTFS/usr/lib/limad/apps/anycubic-slicer-next/PACKAGE-VERSION")" = "1.3.96" ]
[ "$(cat "$ROOTFS/usr/lib/limad/apps/anycubic-slicer-next/BUILD-VERSION")" = "1.3.9.4" ]
[ "$(cat "$ROOTFS/usr/lib/limad/apps/anycubic-slicer-next/SOURCE-SHA256")" = "2c2883a9c624ab64e721a0211667852e0083d8794f7839c1d7932c9f712ed076" ]
grep -Fq 'Exec=/usr/bin/anycubicslicernext %F' "$ROOTFS/usr/share/applications/de.limad.AnycubicSlicerNext.desktop"
grep -Fq 'de.limad.AnycubicSlicerNext' "$ROOTFS/usr/share/limad-updater/apps.json"
grep -Fq '/usr/lib/limad/apps/anycubic-slicer-next' "$ROOTFS/usr/bin/anycubicslicernext"
grep -Fq '/usr/share/limad/offline/anycubic' "$ROOTFS/usr/local/bin/limad-anycubic-deps"
shopt -s nullglob
ANYCUBIC_DEBS=("$ROOTFS/usr/share/limad/offline/anycubic"/*.deb)
shopt -u nullglob
[ "${#ANYCUBIC_DEBS[@]}" -gt 0 ]
(
    cd "$ROOTFS/usr/share/limad/offline/anycubic"
    sha256sum -c SHA256SUMS.txt >/dev/null
)
for package in libglu1-mesa zlib1g libdbus-1-3 libgtk-3-bin libwayland-bin libsoup-2.4-1 libwebkit2gtk-4.1-0 libgstreamer-ocaml gstreamer1.0-libav; do
    grep -Fxq "$package" "$ROOTFS/usr/share/limad-anycubic/REQUIRED-PACKAGES.txt"
done
grep -Fq '/usr/local/bin/limad-anycubic-deps' "$PAYLOAD/install-target.sh"

echo "PAYLOAD VALIDATION: PASS"
