#!/usr/bin/bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source "$ROOT/config/build.env"

[ "$UBUNTU_ISO_NAME" = "ubuntu-26.04-desktop-amd64.iso" ]
[ "$UBUNTU_ISO_SHA256" = "487f87faaf547ea30e0aba4d5b53346292571256b25333a978db1692bcee9dd2" ]
[ "$WHITESUR_REF" = "1b356fe48ad5d05fb2ca6be071efe6801df3ac72" ]
[ "$OUTPUT_ISO_NAME" = "LiMaD-OS-3.0-RC1-BASE1-UBUNTU-26.04-FULL-WHITESUR-V16-amd64.iso" ]
[ "$RELEASE_TAG" = "base1-ubuntu2604-full-whitesur-v16" ]

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
grep -Fq 'background-color: #ff5f57' "$ROOT/build/rootfs/usr/share/limad/gtk4/gtk.css"
grep -Fq 'background-color: #febc2e' "$ROOT/build/rootfs/usr/share/limad/gtk4/gtk.css"
grep -Fq 'background-color: #28c840' "$ROOT/build/rootfs/usr/share/limad/gtk4/gtk.css"
grep -Fq "rm -rf -- \"\${DEST:?}/assets\"" "$ROOT/build/rootfs/usr/local/bin/limad-sync-gtk4-theme"
for uuid in lilink@limad.local lidrop@limad.local; do
    test -s "$ROOT/build/rootfs/usr/share/gnome-shell/extensions/$uuid/metadata.json"
    test -s "$ROOT/build/rootfs/usr/share/gnome-shell/extensions/$uuid/extension.js"
done
grep -Fq '"shell-version": ["50"]' "$ROOT/build/rootfs/usr/share/gnome-shell/extensions/lilink@limad.local/metadata.json"
grep -Fq '"shell-version": ["50"]' "$ROOT/build/rootfs/usr/share/gnome-shell/extensions/lidrop@limad.local/metadata.json"
grep -Fq 'Main.panel.addToStatusArea(this.uuid, this._indicator);' "$ROOT/build/rootfs/usr/share/gnome-shell/extensions/lilink@limad.local/extension.js"
grep -Fq 'Main.panel.addToStatusArea(this.uuid, this._indicator);' "$ROOT/build/rootfs/usr/share/gnome-shell/extensions/lidrop@limad.local/extension.js"
grep -Fq 'limad-lidrop-status-ensure' "$ROOT/build/rootfs/usr/local/bin/limad-base1-first-login"
grep -Fq "python3 -B \"\$ROOT/tools/strip-lidrop-airdrop.py\" \"\$PAYLOAD/rootfs\"" "$ROOT/build/prepare-payload.sh"
test -s "$ROOT/build/rootfs/usr/lib/systemd/user/limad-link.service"
grep -Fq 'ExecStart=/usr/bin/python3 /usr/share/limad-link/daemon.py' "$ROOT/build/rootfs/usr/lib/systemd/user/limad-link.service"
grep -Fq 'systemctl --global enable limad-link.service' "$ROOT/build/install-target.sh"
grep -Fq '/usr/local/bin/limad-link-health-check' "$ROOT/build/rootfs/usr/local/bin/limad-link-status-ensure"
for package in avahi-utils deskflow freerdp-x11 gnome-remote-desktop openssl qrencode; do
    grep -Fq "    $package" "$ROOT/build/rootfs/usr/local/bin/limad-runtime-deps"
done

grep -Fq 'LiMaD-Wallpaper-01-Logo-Links-4K.png' "$ROOT/build/prepare-payload.sh"
grep -Fq 'org.gnome.desktop.background picture-uri' "$ROOT/build/rootfs/usr/local/bin/limad-base1-first-login"
grep -Fq 'set_key_required org.gnome.shell.extensions.dash-to-dock extend-height false false' "$ROOT/build/rootfs/usr/local/bin/limad-base1-first-login"
grep -Fq 'update-initramfs -u' "$ROOT/build/rootfs/usr/local/bin/limad-design-system"

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
test -x "$ROOT/build/build-iso.sh"
test -x "$ROOT/build/prepare-payload.sh"
test -x "$ROOT/build/prepare-imac17-initrd.sh"
test -x "$ROOT/build/casper-bottom/62limad-branding"
test -x "$ROOT/build/install-target.sh"
test -x "$ROOT/build/rootfs/usr/local/bin/limad-design-system"
test -x "$ROOT/build/rootfs/usr/local/bin/limad-link-health-check"
test -x "$ROOT/build/rootfs/usr/local/bin/limad-link-status-ensure"

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
python3 -B "$ROOT/tests/test-status-and-titlebuttons.py"
python3 -B "$ROOT/tests/test-installer-branding.py"
python3 -B "$ROOT/tests/test-imac17-firmware.py"
python3 -B "$ROOT/tests/test-lilink-and-lidrop-scope.py"

grep -Fq "INSTALL_SOURCES_ORIGINAL=\"\$CACHE/install-sources.original.yaml\"" "$ROOT/build/build-iso.sh"
grep -Fq "MD5_ORIGINAL=\"\$CACHE/md5sum.original.txt\"" "$ROOT/build/build-iso.sh"
grep -Fq "rm -rf \"\$CACHE\"" "$ROOT/build/build-iso.sh"
grep -Fq "rm -f \"out/\$OUTPUT_ISO_NAME\"" "$ROOT/.github/workflows/build-iso.yml"
grep -Fq 'INSTALL_SOURCES_MD5=' "$ROOT/tests/verify-built-iso.sh"
grep -Fq 'INITRD_MD5=' "$ROOT/tests/verify-built-iso.sh"
grep -Fq 'GRUB_MD5=' "$ROOT/tests/verify-built-iso.sh"

echo "SOURCE VALIDATION: PASS"
