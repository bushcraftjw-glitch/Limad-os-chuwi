#!/usr/bin/bash
set -euo pipefail

MODE="${1:-}"
PAYLOAD_ROOT="/limad-payload"

rm -f /etc/apt/sources.list
rm -f /etc/apt/sources.list.d/*.list /etc/apt/sources.list.d/*.sources

case "$MODE" in
    liview)
        mkdir -p /usr/share/limad/offline /usr/local/bin
        ln -s "$PAYLOAD_ROOT/usr/share/liview" /usr/share/liview
        ln -s "$PAYLOAD_ROOT/usr/share/limad/offline/liview" /usr/share/limad/offline/liview
        install -m 0755 "$PAYLOAD_ROOT/usr/local/bin/limad-liview-deps" /usr/local/bin/limad-liview-deps
        /usr/local/bin/limad-liview-deps
        ;;
    gaming)
        mkdir -p /usr/share/limad/offline /usr/local/bin
        ln -s "$PAYLOAD_ROOT/usr/share/limad/gaming" /usr/share/limad/gaming
        ln -s "$PAYLOAD_ROOT/usr/share/limad/offline/gaming" /usr/share/limad/offline/gaming
        install -m 0755 "$PAYLOAD_ROOT/usr/local/bin/limad-gaming-deps" /usr/local/bin/limad-gaming-deps
        /usr/local/bin/limad-gaming-deps
        ;;
    grubenvolk)
        mkdir -p /usr/share/limad/offline /usr/local/bin /usr/local/libexec
        ln -s "$PAYLOAD_ROOT/usr/share/limad-grubenvolk" /usr/share/limad-grubenvolk
        ln -s "$PAYLOAD_ROOT/usr/share/limad/offline/grubenvolk" /usr/share/limad/offline/grubenvolk
        install -m 0755 "$PAYLOAD_ROOT/usr/local/bin/limad-grubenvolk-deps" /usr/local/bin/limad-grubenvolk-deps
        install -m 0755 "$PAYLOAD_ROOT/usr/local/bin/limad-grubenvolk" /usr/local/bin/limad-grubenvolk
        install -m 0755 "$PAYLOAD_ROOT/usr/local/libexec/limad-select-app-root" /usr/local/libexec/limad-select-app-root
        /usr/local/bin/limad-grubenvolk-deps
        ;;
    full)
        chmod 0755 /tmp/limad-install-target.sh
        /usr/bin/bash /tmp/limad-install-target.sh
        ;;
    *)
        echo "ERROR: Unknown target preflight mode: $MODE" >&2
        exit 1
        ;;
esac
