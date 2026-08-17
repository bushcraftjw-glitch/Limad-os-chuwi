#!/usr/bin/bash
set -euo pipefail

chmod 0755 /usr/local/bin/limad-base1-first-login \
    /usr/local/bin/limad-first-login-setup \
    /usr/local/bin/limad-runtime-deps \
    /usr/local/bin/limad-sync-gtk4-theme \
    /usr/local/bin/limad-design-system \
    /usr/local/bin/limad-link-status-ensure \
    /usr/local/bin/limad-link-health-check \
    /usr/local/bin/limad-lidrop-status-ensure

if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database /usr/share/applications || true
fi

if command -v gtk-update-icon-cache >/dev/null 2>&1 && [ -f /usr/share/icons/LiMaD/index.theme ]; then
    gtk-update-icon-cache -f /usr/share/icons/LiMaD || true
fi

IMAC_PRODUCT="$(cat /sys/class/dmi/id/product_name 2>/dev/null || true)"
if [ "$IMAC_PRODUCT" = "iMac17,1" ] || [ -f /tmp/limad-imac17-1 ]; then
    mkdir -p /etc/modprobe.d
    cat > /etc/modprobe.d/90-limad-imac17-radeon.conf <<'MODPROBE'
# LiMaD OS compatibility profile for Apple iMac17,1 / Radeon R9 M380 Mac Edition.
options radeon cik_support=1
options amdgpu cik_support=0
MODPROBE
    echo "iMac17,1 Radeon CIK compatibility profile: installed"
else
    rm -f /etc/modprobe.d/90-limad-imac17-radeon.conf
fi
rm -f /tmp/limad-imac17-1

systemctl enable limad-runtime-deps.service

if [ -f /usr/lib/systemd/user/limad-link.service ]; then
    systemctl --global enable limad-link.service
fi

if systemctl list-unit-files avahi-daemon.service >/dev/null 2>&1; then
    systemctl enable avahi-daemon.service || true
fi

/usr/local/bin/limad-runtime-deps || true
/usr/local/bin/limad-design-system || true

printf '%s
' "LiMaD OS BASE1 V16 design target integration complete." > /var/log/limad-base1-install.log
