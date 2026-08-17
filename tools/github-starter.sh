#!/usr/bin/bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source "$ROOT/config/build.env"

for command in git gh sha256sum rsync mktemp; do
    if ! command -v "$command" >/dev/null 2>&1; then
        echo "ERROR: Required command not found: $command" >&2
        exit 1
    fi
done

if ! gh auth status -h github.com >/dev/null 2>&1; then
    gh auth login -h github.com -p https -w
fi

gh auth setup-git >/dev/null 2>&1 || true

REPO="${LIMAD_GITHUB_REPO:-bushcraftjw-glitch/Limad-os-chuwi}"
REPO_URL="https://github.com/${REPO}.git"

"$ROOT/tests/validate-source.sh"

PUSH_WORK="$(mktemp -d)"
trap 'rm -rf "$PUSH_WORK"' EXIT
PUSH_REPO="$PUSH_WORK/repo"

# Use the existing repository directly. Do not create repositories and do not
# query the GitHub user API before cloning.
git clone --quiet "$REPO_URL" "$PUSH_REPO"

if git -C "$PUSH_REPO" rev-parse --verify HEAD >/dev/null 2>&1; then
    git -C "$PUSH_REPO" checkout -q -B main
else
    git -C "$PUSH_REPO" checkout -q --orphan main
fi

rsync -a --delete \
    --exclude='.git/' \
    --exclude='.cache/' \
    --exclude='__pycache__/' \
    --exclude='*.pyc' \
    "$ROOT/" "$PUSH_REPO/"

git -C "$PUSH_REPO" config user.name "LiMaD Build"
git -C "$PUSH_REPO" config user.email "limad-build@users.noreply.github.com"
git -C "$PUSH_REPO" add -A

if git -C "$PUSH_REPO" diff --cached --quiet; then
    COMMIT="$(git -C "$PUSH_REPO" rev-parse HEAD)"
else
    BUILD_VERSION="$(cat "$ROOT/VERSION")"
    git -C "$PUSH_REPO" commit -q -m "Build $BUILD_VERSION"
    COMMIT="$(git -C "$PUSH_REPO" rev-parse HEAD)"
    git -C "$PUSH_REPO" push -u origin main
fi

DISPATCHED=0
for _ in {1..10}; do
    if gh workflow run build-iso.yml --repo "$REPO" --ref main; then
        DISPATCHED=1
        break
    fi
    sleep 5
done
if [ "$DISPATCHED" -ne 1 ]; then
    echo "ERROR: GitHub workflow could not be dispatched." >&2
    exit 1
fi

RUN_ID=""
for _ in {1..30}; do
    RUN_ID="$(gh run list --repo "$REPO" --workflow build-iso.yml --branch main --limit 20 --json databaseId,headSha --jq ".[] | select(.headSha == \"$COMMIT\") | .databaseId" 2>/dev/null | head -n1 || true)"
    if [ -n "$RUN_ID" ]; then
        break
    fi
    sleep 2
done

if [ -z "$RUN_ID" ]; then
    echo "ERROR: GitHub Actions run was not found for commit $COMMIT" >&2
    exit 1
fi

RUN_STATUS=""
RUN_CONCLUSION=""
for _ in {1..240}; do
    RUN_STATE="$(gh run view "$RUN_ID" --repo "$REPO" --json status,conclusion --jq '[.status, (.conclusion // "")] | @tsv' 2>/dev/null || true)"
    if [ -z "$RUN_STATE" ]; then
        echo "GitHub status API temporarily unavailable; retrying in 15 seconds..."
        sleep 15
        continue
    fi

    IFS=$'\t' read -r RUN_STATUS RUN_CONCLUSION <<< "$RUN_STATE"
    if [ "$RUN_STATUS" = "completed" ]; then
        break
    fi

    echo "GitHub Actions run $RUN_ID status: $RUN_STATUS"
    sleep 15
done

if [ "$RUN_STATUS" != "completed" ]; then
    echo "ERROR: GitHub Actions status could not be confirmed after retries. Run $RUN_ID may still be active." >&2
    exit 2
fi

if [ "$RUN_CONCLUSION" != "success" ]; then
    echo "ERROR: GitHub Actions run $RUN_ID completed with conclusion: $RUN_CONCLUSION" >&2
    gh run view "$RUN_ID" --repo "$REPO" --log-failed || true
    exit 1
fi

DOWNLOAD_DIR="$(xdg-user-dir DOWNLOAD 2>/dev/null || true)"
[ -d "$DOWNLOAD_DIR" ] || DOWNLOAD_DIR="$HOME/Downloads"
mkdir -p "$DOWNLOAD_DIR"

PART_DIR="$DOWNLOAD_DIR/LiMaD-OS-BASE1-GITHUB-RELEASE-PARTS"
rm -rf "$PART_DIR"
mkdir -p "$PART_DIR"

RELEASE_DOWNLOADED=0
for _ in {1..10}; do
    if gh release download "$RELEASE_TAG" --repo "$REPO" --dir "$PART_DIR" --clobber; then
        RELEASE_DOWNLOADED=1
        break
    fi
    echo "GitHub release API temporarily unavailable; retrying in 10 seconds..."
    sleep 10
done
if [ "$RELEASE_DOWNLOADED" -ne 1 ]; then
    echo "ERROR: Release files could not be downloaded after retries." >&2
    exit 2
fi

(
    cd "$PART_DIR"
    sha256sum -c ISO-PARTS-SHA256.txt
    cat "$OUTPUT_ISO_NAME".part-* > "$DOWNLOAD_DIR/$OUTPUT_ISO_NAME"
    EXPECTED="$(awk '{print $1}' ISO-SHA256.txt)"
    printf '%s  %s\n' "$EXPECTED" "$DOWNLOAD_DIR/$OUTPUT_ISO_NAME" | sha256sum -c -
)

printf '\nISO ready:\n%s\n' "$DOWNLOAD_DIR/$OUTPUT_ISO_NAME"
printf 'GitHub repository:\nhttps://github.com/%s\n' "$REPO"
printf 'GitHub Actions:\nhttps://github.com/%s/actions\n' "$REPO"
