#!/usr/bin/bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source "$ROOT/config/build.env"

[ "$UBUNTU_ISO_NAME" = "ubuntu-26.04-desktop-amd64.iso" ]
[ "$UBUNTU_ISO_SHA256" = "487f87faaf547ea30e0aba4d5b53346292571256b25333a978db1692bcee9dd2" ]
[ "$WHITESUR_REF" = "1b356fe48ad5d05fb2ca6be071efe6801df3ac72" ]
[ "$OUTPUT_ISO_NAME" = "LiMaD-OS-3.0-RC1-BASE1-UBUNTU-26.04-FULL-WHITESUR-V34-amd64.iso" ]
[ "$RELEASE_TAG" = "base1-ubuntu2604-full-whitesur-v34" ]

grep -Fq 'id: ubuntu-desktop' "$ROOT/config/autoinstall.yaml"
if grep -Fq 'ubuntu-desktop-minimal' "$ROOT/config/autoinstall.yaml"; then
    echo "ERROR: ubuntu-desktop-minimal must not be present in autoinstall.yaml" >&2
    exit 1
fi
grep -Fq 'search_drivers: true' "$ROOT/config/autoinstall.yaml"
grep -Fq 'install: true' "$ROOT/config/autoinstall.yaml"

grep -Fq 'sudo -n /usr/bin/bash ./install.sh' "$ROOT/build/prepare-payload.sh"
grep -Fq -- '--silent-mode' "$ROOT/build/prepare-payload.sh"
if grep -Fq -- '--libadwaita' "$ROOT/build/prepare-payload.sh"; then
    echo "ERROR: Full WhiteSur libadwaita injection must stay disabled" >&2
    exit 1
fi
grep -Fq 'windowcontrols button.close' "$ROOT/build/rootfs/usr/share/limad/gtk4/gtk.css"
grep -Fq 'url("limad-assets/close.svg")' "$ROOT/build/rootfs/usr/share/limad/gtk4/gtk.css"
grep -Fq 'url("limad-assets/minimize.svg")' "$ROOT/build/rootfs/usr/share/limad/gtk4/gtk.css"
grep -Fq 'url("limad-assets/maximize.svg")' "$ROOT/build/rootfs/usr/share/limad/gtk4/gtk.css"
for asset in close.svg minimize.svg maximize.svg; do
    test -s "$ROOT/build/rootfs/usr/share/limad/gtk4/limad-assets/$asset"
done
if grep -Fq "rm -rf -- \"\${DEST:?}/assets\"" "$ROOT/build/rootfs/usr/local/bin/limad-sync-gtk4-theme"; then
    echo "ERROR: GTK4 sync must not delete user configuration" >&2
    exit 1
fi
grep -Fq 'limad-titlebuttons.css' "$ROOT/build/rootfs/usr/local/bin/limad-sync-gtk4-theme"
for uuid in lilink@limad.local lidrop@limad.local limad-menu@limad.local; do
    test -s "$ROOT/build/rootfs/usr/share/gnome-shell/extensions/$uuid/metadata.json"
    test -s "$ROOT/build/rootfs/usr/share/gnome-shell/extensions/$uuid/extension.js"
done
grep -Fq '"shell-version": ["50"]' "$ROOT/build/rootfs/usr/share/gnome-shell/extensions/lilink@limad.local/metadata.json"
grep -Fq '"shell-version": ["50"]' "$ROOT/build/rootfs/usr/share/gnome-shell/extensions/lidrop@limad.local/metadata.json"
grep -Fq 'Main.panel.addToStatusArea(this.uuid, this._indicator);' "$ROOT/build/rootfs/usr/share/gnome-shell/extensions/lilink@limad.local/extension.js"
grep -Fq 'Main.panel.addToStatusArea(this.uuid, this._indicator);' "$ROOT/build/rootfs/usr/share/gnome-shell/extensions/lidrop@limad.local/extension.js"
grep -Fq 'limad-lidrop-status-ensure' "$ROOT/build/rootfs/usr/local/bin/limad-base1-first-login"
grep -Fq 'enable_extension_reliably limad-menu@limad.local' "$ROOT/build/rootfs/usr/local/bin/limad-base1-first-login"
grep -Fq 'this._activities?.hide();' "$ROOT/build/rootfs/usr/share/gnome-shell/extensions/limad-menu@limad.local/extension.js"
grep -Fq '/usr/local/bin/limad-desktop-core-system' "$ROOT/build/install-target.sh"
grep -Fq 'CORE_MARKER=' "$ROOT/build/rootfs/usr/local/bin/limad-base1-first-login"
grep -Fq 'AUX_MARKER=' "$ROOT/build/rootfs/usr/local/bin/limad-base1-first-login"
grep -Fq "python3 -B \"\$ROOT/tools/strip-lidrop-airdrop.py\" \"\$PAYLOAD/rootfs\"" "$ROOT/build/prepare-payload.sh"
grep -Fq "python3 -B \"\$ROOT/tools/patch-v22-titlebars.py\" \"\$PAYLOAD/rootfs\"" "$ROOT/build/prepare-payload.sh"
test -s "$ROOT/build/rootfs/usr/lib/systemd/user/limad-link.service"
grep -Fq 'ExecStart=/usr/bin/python3 /usr/share/limad-link/daemon.py' "$ROOT/build/rootfs/usr/lib/systemd/user/limad-link.service"
grep -Fq 'systemctl --global enable limad-link.service' "$ROOT/build/install-target.sh"
test -s "$ROOT/build/rootfs/usr/lib/systemd/user/limad-drop.service"
grep -Fq 'ExecStart=/usr/local/bin/limad-dropd' "$ROOT/build/rootfs/usr/lib/systemd/user/limad-drop.service"
grep -Fq 'WantedBy=default.target' "$ROOT/build/rootfs/usr/lib/systemd/user/limad-drop.service"
grep -Fq 'systemctl --global enable limad-drop.service' "$ROOT/build/install-target.sh"
grep -Fq 'systemctl --user enable --now limad-drop.service' "$ROOT/build/rootfs/usr/local/bin/limad-lidrop-status-ensure"
grep -Fq '/usr/local/bin/limad-link-health-check' "$ROOT/build/rootfs/usr/local/bin/limad-link-status-ensure"
for package in avahi-utils deskflow flatpak freerdp-x11 gnome-remote-desktop gstreamer1.0-gtk4 openssl qrencode; do
    grep -Fq "    $package" "$ROOT/build/rootfs/usr/local/bin/limad-runtime-deps"
done

grep -Fq 'LiMaD-Wallpaper-01-Logo-Links-4K.png' "$ROOT/build/prepare-payload.sh"
grep -Fq 'org.gnome.desktop.background picture-uri' "$ROOT/build/rootfs/usr/local/bin/limad-base1-first-login"
grep -Fq 'set_key org.gnome.shell.extensions.dash-to-dock extend-height false' "$ROOT/build/rootfs/usr/local/bin/limad-base1-first-login"
grep -Fq 'verify_key org.gnome.shell.extensions.dash-to-dock always-center-icons true' "$ROOT/build/rootfs/usr/local/bin/limad-base1-first-login"
grep -Fq 'verify_key org.gnome.shell.extensions.dash-to-dock show-apps-always-in-the-edge false' "$ROOT/build/rootfs/usr/local/bin/limad-base1-first-login"
grep -Fq 'verify_favorites' "$ROOT/build/rootfs/usr/local/bin/limad-base1-first-login"
grep -Fq "dock-position='BOTTOM'" "$ROOT/build/rootfs/usr/local/bin/limad-desktop-core-system"
grep -Fq "icon-theme='LiMaD'" "$ROOT/build/rootfs/usr/local/bin/limad-desktop-core-system"
grep -Fq "favorite-apps=['app.zen_browser.zen.desktop'" "$ROOT/build/rootfs/usr/local/bin/limad-desktop-core-system"
grep -Fq "'de.limad.Mail.desktop'" "$ROOT/build/rootfs/usr/local/bin/limad-desktop-core-system"
grep -Fq "'de.limad.Drop.desktop'" "$ROOT/build/rootfs/usr/local/bin/limad-desktop-core-system"
grep -Fq "'de.limad.Link.desktop'" "$ROOT/build/rootfs/usr/local/bin/limad-desktop-core-system"
grep -Fq 'update-initramfs -u' "$ROOT/build/rootfs/usr/local/bin/limad-design-system"
grep -Fq 'limad-desktop-core-system' "$ROOT/tests/verify-built-iso.sh"
grep -Fq 'always-center-icons=true' "$ROOT/tests/verify-built-iso.sh"
grep -Fq 'limad-desktop-core-system' "$ROOT/.github/workflows/build-iso.yml"

grep -Fq 'app-name: "LiMaD OS Installer"' "$ROOT/build/installer-whitelabel.yaml"
grep -Fq 'accent-color: "#BB7FF0"' "$ROOT/build/installer-whitelabel.yaml"
grep -Fq 'Willkommen bei LiMaD OS 3.0' "$ROOT/build/installer-slides/1/slide_de_DE.html"
grep -Fq 'Welcome to LiMaD OS 3.0' "$ROOT/build/installer-slides/1/slide_en_US.html"
grep -Fq 'LiMaD live branding: installed' "$ROOT/build/casper-bottom/62limad-branding"
grep -Fq 'scripts/casper-bottom/62limad-branding' "$ROOT/build/prepare-imac17-initrd.sh"

grep -Fq 'iMac17,1' "$ROOT/tools/brand-grub.py"
grep -Fq 'radeon.cik_support=1 amdgpu.cik_support=0' "$ROOT/tools/brand-grub.py"
grep -Fq 'options radeon cik_support=1' "$ROOT/build/install-target.sh"
grep -Fq 'options amdgpu cik_support=0' "$ROOT/build/install-target.sh"
grep -Fq 'BONAIRE_uvd.bin' "$ROOT/assets/firmware/SHA256SUMS.txt"

grep -Fq "GRUB_ORIGINAL=\"\$CACHE/grub.original.cfg\"" "$ROOT/build/build-iso.sh"
grep -Fq "python3 -B \"\$ROOT/tools/brand-grub.py\"" "$ROOT/build/build-iso.sh"
grep -Fq -- '-volid LIMAD_OS_3_0_RC1' "$ROOT/build/build-iso.sh"
grep -Fq "REPO=\"\${LIMAD_GITHUB_REPO:-bushcraftjw-glitch/Limad-os-chuwi}\"" "$ROOT/tools/github-starter.sh"
grep -Fq 'expected_sha:' "$ROOT/.github/workflows/build-iso.yml"
grep -Fq "EXPECTED_SHA: \${{ inputs.expected_sha }}" "$ROOT/.github/workflows/build-iso.yml"
grep -Fq "gh api \"repos/\$REPO/commits/main\"" "$ROOT/tools/github-starter.sh"
grep -Fq "expected_sha=\"\$COMMIT\"" "$ROOT/tools/github-starter.sh"
grep -Fq 'baseline-runs.txt' "$ROOT/tools/github-starter.sh"
grep -Fq 'Built ISO release marker mismatch.' "$ROOT/tests/verify-built-iso.sh"
grep -Fq "EL_TORITO_REPORT=\"\$TMP/el-torito.txt\"" "$ROOT/tests/verify-built-iso.sh"
grep -Fq "PVD_REPORT=\"\$TMP/pvd-info.txt\"" "$ROOT/tests/verify-built-iso.sh"
if grep -Fq 'git push --force' "$ROOT/tools/github-starter.sh"; then
    echo "ERROR: Force-push must not be used for Limad-os-chuwi build history" >&2
    exit 1
fi

grep -Fq ' cpio ' "$ROOT/.github/workflows/build-iso.yml"
grep -Fq 'build/casper-bottom/*' "$ROOT/.github/workflows/build-iso.yml"

test -x "$ROOT/tools/github-starter.sh"
test -x "$ROOT/tools/reassemble-vendor.sh"
test -x "$ROOT/tools/brand-grub.py"
test -x "$ROOT/tools/strip-lidrop-airdrop.py"
test -x "$ROOT/tools/patch-v22-titlebars.py"
test -x "$ROOT/build/rootfs/usr/local/bin/limad-required-user-apps"
test -x "$ROOT/build/rootfs/usr/local/bin/limad-zen-voltroute-bookmark"
test -x "$ROOT/build/rootfs/usr/local/bin/limad-titlebuttons-ensure"
test -x "$ROOT/build/rootfs/usr/local/bin/limusic"
test -x "$ROOT/build/build-iso.sh"
test -x "$ROOT/build/prepare-payload.sh"
test -x "$ROOT/build/prepare-imac17-initrd.sh"
test -x "$ROOT/build/casper-bottom/62limad-branding"
test -x "$ROOT/build/install-target.sh"
test -x "$ROOT/build/rootfs/usr/local/bin/limad-desktop-core-system"
test -x "$ROOT/build/rootfs/usr/local/bin/limad-link-health-check"
test -x "$ROOT/build/rootfs/usr/local/bin/limad-link-status-ensure"
test -x "$ROOT/build/rootfs/usr/local/bin/limad-lidrop-status-ensure"

test -s "$ROOT/build/rootfs/etc/xdg/autostart/limad-required-user-apps.desktop"
test -s "$ROOT/build/rootfs/etc/xdg/autostart/limad-titlebuttons-ensure.desktop"
test -s "$ROOT/build/rootfs/usr/share/applications/de.limad.LiMusic.desktop"
test -s "$ROOT/build/rootfs/usr/share/limad-updater/apps.json"
test -s "$ROOT/build/rootfs/usr/share/limusic/VERSION"
[ "$(cat "$ROOT/build/rootfs/usr/share/limusic/VERSION")" = "0.3.27" ]
test -s "$ROOT/build/rootfs/usr/share/limusic/src/limusic/adblock_engine.py"
test -s "$ROOT/build/rootfs/usr/share/limusic/data/adblock-scriptlet-rules.json"
for package in gstreamer1.0-gtk4 gstreamer1.0-libav gstreamer1.0-plugins-base gstreamer1.0-plugins-good gstreamer1.0-plugins-bad gstreamer1.0-plugins-ugly gstreamer1.0-tools gir1.2-webkit-6.0; do
    grep -Fq "    $package" "$ROOT/build/rootfs/usr/local/bin/limad-runtime-deps"
done
grep -Fq 'app.zen_browser.zen' "$ROOT/build/rootfs/usr/local/bin/limad-required-user-apps"
grep -Fq 'org.fedoraproject.MediaWriter' "$ROOT/build/rootfs/usr/local/bin/limad-required-user-apps"
grep -Fq 'limad-zen-voltroute-bookmark' "$ROOT/build/rootfs/usr/local/bin/limad-required-user-apps"
grep -Fq 'com.github.wwmm.easyeffects' "$ROOT/build/rootfs/usr/local/bin/limad-required-user-apps"
if grep -Fq 'firefox_firefox.desktop' "$ROOT/build/rootfs/usr/local/bin/limad-desktop-core-system"; then
    echo "ERROR: Firefox must not remain in V22 Dock defaults" >&2
    exit 1
fi

(
    cd "$ROOT/assets/firmware"
    sha256sum -c SHA256SUMS.txt >/dev/null
)

"$ROOT/tools/reassemble-vendor.sh"
unzip -tq "$ROOT/.cache/vendor/LiMaD-Programme-BASE1B-EXTRAKT.zip" >/dev/null
unzip -tq "$ROOT/.cache/vendor/LiMaD-OS-MASTER-ICON-THEME-V3.2-BUILD-READY.zip" >/dev/null
unzip -tq "$ROOT/.cache/vendor/LiMaD-4K-Hintergrundbilder-BASE1B.zip" >/dev/null
python3 -B "$ROOT/tests/validate-wallpapers.py" "$ROOT/.cache/vendor/LiMaD-4K-Hintergrundbilder-BASE1B.zip"
python3 -B "$ROOT/tests/validate-app-icons.py"
python3 -B "$ROOT/tests/test-filter-install-sources.py"
python3 -B "$ROOT/tests/test-update-md5.py"
python3 -B "$ROOT/tests/test-brand-grub.py"
python3 -B "$ROOT/tests/test-design-assets.py"
python3 -B "$ROOT/tests/test-shell-regressions.py"
python3 -B "$ROOT/tests/test-version-consistency.py"
python3 -B "$ROOT/tests/test-status-and-titlebuttons.py"
python3 -B "$ROOT/tests/test-installer-branding.py"
python3 -B "$ROOT/tests/test-imac17-firmware.py"
python3 -B "$ROOT/tests/test-lilink-and-lidrop-scope.py"
python3 -B "$ROOT/tests/test-v22-menu-lidrop.py"
python3 -B "$ROOT/tests/test-v22-apps-titlebuttons.py"
python3 -B "$ROOT/tests/test-v28-app-grid-labels.py"
python3 -B "$ROOT/tests/test-v29-titlebutton-order.py"
python3 -B "$ROOT/tests/test-v29-dock-favorites.py"
python3 -B "$ROOT/tests/test-v30-windows-programme.py"
python3 -B "$ROOT/tests/test-v30-mediawriter.py"
python3 -B "$ROOT/tests/test-v30-zen-bookmark.py"
python3 -B "$ROOT/tests/test-v31-lisave-portable.py"
python3 -B "$ROOT/tests/test-v32-lisave-progress.py"
python3 -B "$ROOT/tests/test-v33-lisave-restore-progress.py"
python3 -B "$ROOT/tests/test-v26-updater-gtk4.py"

grep -Fq "INSTALL_SOURCES_ORIGINAL=\"\$CACHE/install-sources.original.yaml\"" "$ROOT/build/build-iso.sh"
grep -Fq "MD5_ORIGINAL=\"\$CACHE/md5sum.original.txt\"" "$ROOT/build/build-iso.sh"
grep -Fq "rm -rf \"\$CACHE\"" "$ROOT/build/build-iso.sh"
grep -Fq "rm -f \"out/\$OUTPUT_ISO_NAME\"" "$ROOT/.github/workflows/build-iso.yml"
grep -Fq 'INSTALL_SOURCES_MD5=' "$ROOT/tests/verify-built-iso.sh"
grep -Fq 'INITRD_MD5=' "$ROOT/tests/verify-built-iso.sh"
grep -Fq 'GRUB_MD5=' "$ROOT/tests/verify-built-iso.sh"

grep -Fq ' dconf-cli ' "$ROOT/.github/workflows/build-iso.yml"
grep -Fq 'dconf help compile' "$ROOT/.github/workflows/build-iso.yml"


# V23 LiView integration retained in V25: native app, updater registration, offline runtime closure and defaults.
for path in \
    "$ROOT/build/liview-packages.txt" \
    "$ROOT/build/prepare-liview-offline-repo.sh" \
    "$ROOT/build/rootfs/usr/local/bin/liview" \
    "$ROOT/build/rootfs/usr/local/bin/limad-liview-deps" \
    "$ROOT/build/rootfs/usr/share/liview/VERSION" \
    "$ROOT/build/rootfs/usr/share/liview/liview/__main__.py" \
    "$ROOT/build/rootfs/usr/share/liview/liview/app.py" \
    "$ROOT/build/rootfs/usr/share/liview/liview/documents.py" \
    "$ROOT/build/rootfs/usr/share/applications/de.limad.LiView.desktop" \
    "$ROOT/build/rootfs/usr/share/mime/packages/de.limad.LiView.xml" \
    "$ROOT/build/rootfs/etc/xdg/mimeapps.list"; do
    test -s "$path"
done
[ "$(cat "$ROOT/build/rootfs/usr/share/liview/VERSION")" = "1.1.1" ]
test -x "$ROOT/build/prepare-liview-offline-repo.sh"
test -x "$ROOT/build/rootfs/usr/local/bin/liview"
test -x "$ROOT/build/rootfs/usr/local/bin/limad-liview-deps"
[ ! -e "$ROOT/build/rootfs/usr/bin/liview" ]
grep -Fq '/usr/local/libexec/limad-select-app-root' "$ROOT/build/rootfs/usr/local/bin/liview"
grep -Fq 'de.limad.LiView' "$ROOT/build/rootfs/usr/share/limad-updater/apps.json"
grep -Fq '"launcher": "/usr/local/bin/liview"' "$ROOT/build/rootfs/usr/share/limad-updater/apps.json"
grep -Fq 'Exec=/usr/local/bin/liview %F' "$ROOT/build/rootfs/usr/share/applications/de.limad.LiView.desktop"
grep -Fq 'Exec=/usr/local/bin/limad-updater --app de.limad.LiView' "$ROOT/build/rootfs/usr/share/applications/de.limad.LiView.desktop"
grep -Fq 'application/pdf=de.limad.LiView.desktop' "$ROOT/build/rootfs/etc/xdg/mimeapps.list"
grep -Fq 'video/x-liview-raw=de.limad.LiView.desktop' "$ROOT/build/rootfs/etc/xdg/mimeapps.list"
grep -Fq 'prepare-liview-offline-repo.sh' "$ROOT/build/prepare-payload.sh"
grep -Fq '/usr/local/bin/limad-liview-deps' "$ROOT/build/install-target.sh"
if grep -F '/usr/local/bin/limad-liview-deps' "$ROOT/build/install-target.sh" | grep -Fq '|| true'; then
    echo 'ERROR: LiView dependency installation must be install-critical' >&2
    exit 1
fi
for package in \
    gir1.2-gtk-4.0 gir1.2-poppler-0.18 python3-pikepdf python3-pil \
    librsvg2-bin libheif-examples gstreamer1.0-gtk4 gstreamer1.0-libav \
    gstreamer1.0-plugins-base gstreamer1.0-plugins-good gstreamer1.0-plugins-bad \
    gstreamer1.0-plugins-ugly tesseract-ocr tesseract-ocr-deu ffmpeg ghostscript \
    desktop-file-utils shared-mime-info; do
    grep -Fxq "$package" "$ROOT/build/liview-packages.txt"
done
for size in 64 128 256 512; do
    test -s "$ROOT/build/rootfs/usr/share/icons/LiMaD/${size}x${size}/apps/de.limad.LiView.png"
    test -s "$ROOT/build/rootfs/usr/share/icons/hicolor/${size}x${size}/apps/de.limad.LiView.png"
done
python3 -B "$ROOT/tests/test-v23-liview.py"
python3 -B "$ROOT/tests/test-v26-liview-performance.py"

# V24 gaming integration: native Ubuntu stack, amd64+i386 offline closure and ProtonUp-Qt.
for path in \
    "$ROOT/build/gaming-packages.txt" \
    "$ROOT/build/prepare-gaming-offline-repo.sh" \
    "$ROOT/build/rootfs/usr/local/bin/limad-gaming-deps" \
    "$ROOT/build/rootfs/usr/share/limad/gaming/REQUIRED-PACKAGES.txt"; do
    test -s "$path"
done
test -x "$ROOT/build/prepare-gaming-offline-repo.sh"
test -x "$ROOT/build/rootfs/usr/local/bin/limad-gaming-deps"
grep -Fq 'prepare-gaming-offline-repo.sh' "$ROOT/build/prepare-payload.sh"
grep -Fq '/usr/local/bin/limad-gaming-deps' "$ROOT/build/install-target.sh"
if grep -F '/usr/local/bin/limad-gaming-deps' "$ROOT/build/install-target.sh" | grep -Fq '|| true'; then
    echo 'ERROR: Gaming dependency installation must be install-critical' >&2
    exit 1
fi
for package in \
    steam-installer steam-devices lutris protontricks wine wine32:i386 winetricks \
    gamemode mangohud gamescope vulkan-tools mesa-vulkan-drivers:amd64 \
    mesa-vulkan-drivers:i386 libvulkan1:amd64 libvulkan1:i386 libglx-mesa0:i386 \
    mesa-utils vkbasalt goverlay; do
    grep -Fxq "$package" "$ROOT/build/gaming-packages.txt"
done
grep -Fq 'net.davidotek.pupgui2' "$ROOT/build/rootfs/usr/local/bin/limad-required-user-apps"
grep -Fq 'required-user-apps-v25.done' "$ROOT/build/rootfs/usr/local/bin/limad-required-user-apps"
python3 -B "$ROOT/tests/test-v24-gaming.py"
python3 -B "$ROOT/tests/test-v24-build-pipeline-safety.py"


# V26 Heroic Games Launcher: official pinned DEB plus target-aware offline dependency closure.
for path in \
    "$ROOT/build/prepare-heroic-offline-repo.sh" \
    "$ROOT/build/rootfs/usr/local/bin/limad-heroic-deps"; do
    test -s "$path"
done
test -x "$ROOT/build/prepare-heroic-offline-repo.sh"
test -x "$ROOT/build/rootfs/usr/local/bin/limad-heroic-deps"
grep -Fq 'prepare-heroic-offline-repo.sh' "$ROOT/build/prepare-payload.sh"
grep -Fq '/usr/local/bin/limad-heroic-deps' "$ROOT/build/install-target.sh"
grep -Fq 'run_stage Heroic /usr/local/bin/limad-heroic-deps' "$ROOT/build/preflight-target-install.sh"
if grep -F '/usr/local/bin/limad-heroic-deps' "$ROOT/build/install-target.sh" | grep -Fq '|| true'; then
    echo 'ERROR: Heroic installation must be install-critical' >&2
    exit 1
fi
python3 -B "$ROOT/tests/test-v26-heroic.py"

# V25 GRUBENVOLK integration: system app, updater, Dock and offline GTK4/WebKit runtime.
for path in \
    "$ROOT/build/grubenvolk-packages.txt" \
    "$ROOT/build/prepare-grubenvolk-offline-repo.sh" \
    "$ROOT/build/rootfs/usr/local/bin/limad-grubenvolk" \
    "$ROOT/build/rootfs/usr/local/bin/limad-grubenvolk-deps" \
    "$ROOT/build/rootfs/usr/share/limad-grubenvolk/VERSION" \
    "$ROOT/build/rootfs/usr/share/limad-grubenvolk/web/index.html" \
    "$ROOT/build/rootfs/usr/share/limad-grubenvolk/src/limad_grubenvolk/__main__.py" \
    "$ROOT/build/rootfs/usr/share/limad-grubenvolk/src/limad_grubenvolk/shell.py" \
    "$ROOT/build/rootfs/usr/share/applications/de.limad.Grubenvolk.desktop"; do
    test -s "$path"
done
[ "$(cat "$ROOT/build/rootfs/usr/share/limad-grubenvolk/VERSION")" = "3.6.8" ]
test -x "$ROOT/build/prepare-grubenvolk-offline-repo.sh"
test -x "$ROOT/build/rootfs/usr/local/bin/limad-grubenvolk"
test -x "$ROOT/build/rootfs/usr/local/bin/limad-grubenvolk-deps"
grep -Fq 'de.limad.Grubenvolk' "$ROOT/build/rootfs/usr/share/limad-updater/apps.json"
grep -Fq 'de.limad.Grubenvolk.desktop' "$ROOT/build/rootfs/usr/local/bin/limad-desktop-core-system"
grep -Fq 'de.limad.Grubenvolk.desktop' "$ROOT/build/rootfs/usr/local/bin/limad-base1-first-login"
grep -Fq 'required-user-apps-v25.done' "$ROOT/build/rootfs/usr/local/bin/limad-required-user-apps"
grep -Fq 'prepare-grubenvolk-offline-repo.sh' "$ROOT/build/prepare-payload.sh"
grep -Fq '/usr/local/bin/limad-grubenvolk-deps' "$ROOT/build/install-target.sh"
if grep -F '/usr/local/bin/limad-grubenvolk-deps' "$ROOT/build/install-target.sh" | grep -Fq '|| true'; then
    echo 'ERROR: GRUBENVOLK dependency installation must be install-critical' >&2
    exit 1
fi
for package in python3 python3-gi gir1.2-gtk-4.0 gir1.2-webkit-6.0; do
    grep -Fxq "$package" "$ROOT/build/grubenvolk-packages.txt"
done
python3 -B "$ROOT/tests/test-v25-grubenvolk.py"
python3 -B "$ROOT/tests/test-v25-target-preflight.py"

echo "SOURCE VALIDATION: PASS"
