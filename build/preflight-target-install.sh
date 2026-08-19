#!/usr/bin/bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PAYLOAD="$ROOT/.cache/payload"
BASE_IMAGE="${LIMAD_PREFLIGHT_IMAGE:-ubuntu:26.04}"
IMAGE_TAG="limad-v25-target-preflight:${GITHUB_SHA:-local}"
FULL_CONTAINER="limad-v25-target-preflight-full-$$"
CONTAINER_SCRIPT="$ROOT/build/preflight-target-container.sh"

cleanup() {
    docker rm -f "$FULL_CONTAINER" >/dev/null 2>&1 || true
    docker image rm -f "$IMAGE_TAG" >/dev/null 2>&1 || true
}
trap cleanup EXIT

if ! command -v docker >/dev/null 2>&1; then
    echo "ERROR: Target preflight requires Docker." >&2
    exit 1
fi

if [ ! -d "$PAYLOAD/rootfs" ] || [ ! -x "$PAYLOAD/install-target.sh" ] || [ ! -x "$CONTAINER_SCRIPT" ]; then
    echo "ERROR: Prepared LiMaD payload or target preflight helper is missing." >&2
    exit 1
fi

for path in \
    "$PAYLOAD/rootfs/usr/local/bin/limad-liview-deps" \
    "$PAYLOAD/rootfs/usr/local/bin/limad-gaming-deps" \
    "$PAYLOAD/rootfs/usr/local/bin/limad-grubenvolk-deps" \
    "$PAYLOAD/rootfs/usr/local/bin/limad-grubenvolk" \
    "$PAYLOAD/rootfs/usr/local/libexec/limad-select-app-root" \
    "$PAYLOAD/rootfs/usr/share/liview" \
    "$PAYLOAD/rootfs/usr/share/limad/gaming" \
    "$PAYLOAD/rootfs/usr/share/limad-grubenvolk" \
    "$PAYLOAD/rootfs/usr/share/limad/offline/liview" \
    "$PAYLOAD/rootfs/usr/share/limad/offline/gaming" \
    "$PAYLOAD/rootfs/usr/share/limad/offline/grubenvolk"; do
    if [ ! -e "$path" ]; then
        echo "ERROR: Target preflight payload component missing: $path" >&2
        exit 1
    fi
done

echo "TARGET PREFLIGHT: preparing Ubuntu 26.04 target image"
docker pull "$BASE_IMAGE" >/dev/null

docker build --tag "$IMAGE_TAG" - <<EOF_DOCKER
FROM $BASE_IMAGE
ENV DEBIAN_FRONTEND=noninteractive
RUN printf '#!/bin/sh\nexit 101\n' > /usr/sbin/policy-rc.d \
    && chmod 0755 /usr/sbin/policy-rc.d \
    && apt-get update \
    && apt-get install -y --no-install-recommends systemd dconf-cli ca-certificates \
    && rm -rf /var/lib/apt/lists/*
EOF_DOCKER

run_dependency_stage() {
    local stage="$1"
    local mode="$2"

    echo "TARGET PREFLIGHT: $stage START"
    if ! docker run --rm --network none \
        --mount "type=bind,src=$PAYLOAD/rootfs,dst=/limad-payload,readonly" \
        --mount "type=bind,src=$CONTAINER_SCRIPT,dst=/usr/local/bin/limad-preflight-container,readonly" \
        "$IMAGE_TAG" \
        /usr/bin/bash /usr/local/bin/limad-preflight-container "$mode"; then
        echo "ERROR: TARGET PREFLIGHT failed in $stage" >&2
        return 1
    fi
    echo "TARGET PREFLIGHT: $stage PASS"
}

FAILURES=0
if ! run_dependency_stage LiView liview; then
    FAILURES=$((FAILURES + 1))
fi
if ! run_dependency_stage Gaming gaming; then
    FAILURES=$((FAILURES + 1))
fi
if ! run_dependency_stage GRUBENVOLK grubenvolk; then
    FAILURES=$((FAILURES + 1))
fi

if [ "$FAILURES" -ne 0 ]; then
    echo "ERROR: TARGET PREFLIGHT found $FAILURES failing dependency stage(s). ISO build stopped before xorriso." >&2
    exit 1
fi

echo "TARGET PREFLIGHT: full install-target START"
docker create --name "$FULL_CONTAINER" --network none "$IMAGE_TAG" /usr/bin/sleep infinity >/dev/null
docker cp "$PAYLOAD/rootfs/." "$FULL_CONTAINER:/"
docker cp "$PAYLOAD/install-target.sh" "$FULL_CONTAINER:/tmp/limad-install-target.sh"
docker cp "$CONTAINER_SCRIPT" "$FULL_CONTAINER:/usr/local/bin/limad-preflight-container"
docker start "$FULL_CONTAINER" >/dev/null

if ! docker exec "$FULL_CONTAINER" /usr/bin/bash /usr/local/bin/limad-preflight-container full; then
    echo "ERROR: TARGET PREFLIGHT failed in full install-target" >&2
    exit 1
fi

echo "TARGET PREFLIGHT: full install-target PASS"
echo "TARGET PREFLIGHT: PASS"
