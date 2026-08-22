#!/usr/bin/bash
set -euo pipefail

chmod 0755 /usr/local/bin/limad-base1-first-login \
    /usr/local/bin/limad-first-login-setup \
    /usr/local/bin/limad-runtime-deps \
    /usr/local/bin/limad-sync-gtk4-theme \
    /usr/local/bin/limad-design-system \
    /usr/local/bin/limad-desktop-core-system \
    /usr/local/bin/limad-link-status-ensure \
    /usr/local/bin/limad-link-health-check \
    /usr/local/bin/limad-lidrop-status-ensure \
    /usr/local/bin/limad-liview-deps \
    /usr/local/bin/limad-gaming-deps \
    /usr/local/bin/limad-heroic-deps \
    /usr/local/bin/limad-grubenvolk-deps \
    /usr/local/bin/limad-anycubic-deps \
    /usr/local/bin/limad-grubenvolk \
    /usr/local/bin/liview \
    /usr/bin/anycubicslicernext

/usr/local/bin/limad-liview-deps
/usr/local/bin/limad-gaming-deps
/usr/local/bin/limad-heroic-deps
/usr/local/bin/limad-grubenvolk-deps
/usr/local/bin/limad-anycubic-deps

if command -v update-mime-database >/dev/null 2>&1; then
    update-mime-database /usr/share/mime
fi

if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database /usr/share/applications
fi

if command -v gtk-update-icon-cache >/dev/null 2>&1; then
    if [ -f /usr/share/icons/LiMaD/index.theme ]; then
        gtk-update-icon-cache -f /usr/share/icons/LiMaD || true
    fi
    if [ -f /usr/share/icons/hicolor/index.theme ]; then
        gtk-update-icon-cache -f /usr/share/icons/hicolor || true
    fi
fi

IMAC_PRODUCT="$(cat /sys/class/dmi/id/product_name 2>/dev/null || true)"
IMAC_R9_M380=0
for PCI_DEVICE in /sys/bus/pci/devices/*; do
    [ -d "$PCI_DEVICE" ] || continue
    [ "$(cat "$PCI_DEVICE/vendor" 2>/dev/null || true)" = "0x1002" ] || continue
    [ "$(cat "$PCI_DEVICE/device" 2>/dev/null || true)" = "0x6640" ] || continue
    [ "$(cat "$PCI_DEVICE/subsystem_vendor" 2>/dev/null || true)" = "0x106b" ] || continue
    [ "$(cat "$PCI_DEVICE/subsystem_device" 2>/dev/null || true)" = "0x014b" ] || continue
    IMAC_R9_M380=1
    break
done

APPLY_IMAC_R9_M380_PROFILE=0
if [ "$IMAC_PRODUCT" = "iMac17,1" ]; then
    if [ "$IMAC_R9_M380" -eq 1 ]; then
        APPLY_IMAC_R9_M380_PROFILE=1
    fi
fi
if [ -f /tmp/limad-imac17-1 ]; then
    APPLY_IMAC_R9_M380_PROFILE=1
fi

if [ "$APPLY_IMAC_R9_M380_PROFILE" -eq 1 ]; then
    mkdir -p /etc/modprobe.d
    cat > /etc/modprobe.d/90-limad-imac17-radeon.conf <<'MODPROBE'
# LiMaD OS compatibility profile for Apple iMac17,1 / Radeon R9 M380 Mac Edition.
# PCI 1002:6640, Apple subsystem 106b:014b.
options radeon cik_support=0
options amdgpu cik_support=1 dc=0
MODPROBE
    echo "iMac17,1 Radeon R9 M380 AMDGPU compatibility profile: installed"
else
    rm -f /etc/modprobe.d/90-limad-imac17-radeon.conf
fi
rm -f /tmp/limad-imac17-1

systemctl enable limad-runtime-deps.service

if [ -f /usr/lib/systemd/user/limad-link.service ]; then
    systemctl --global enable limad-link.service
fi

if [ -f /usr/lib/systemd/user/limad-drop.service ]; then
    systemctl --global enable limad-drop.service
fi

if systemctl list-unit-files avahi-daemon.service >/dev/null 2>&1; then
    systemctl enable avahi-daemon.service || true
fi

/usr/local/bin/limad-runtime-deps || true
/usr/local/bin/limad-desktop-core-system
/usr/local/bin/limad-design-system || true

printf '%s
' "LiMaD OS BASE1 V38 LiView, gaming, GRUBENVOLK, Heroic and Anycubic integration complete." > /var/log/limad-base1-install.log
