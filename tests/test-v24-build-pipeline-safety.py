#!/usr/bin/python3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

verify = (ROOT / "tests/verify-built-iso.sh").read_text()
if "-report_el_torito plain 2>/dev/null |" in verify:
    raise AssertionError("verify-built-iso still pipes xorriso into grep -q under pipefail")
if "-pvd_info 2>/dev/null |" in verify:
    raise AssertionError("verify-built-iso still pipes xorriso PVD output into grep -q under pipefail")
for needle in [
    'EL_TORITO_REPORT="$TMP/el-torito.txt"',
    'PVD_REPORT="$TMP/pvd-info.txt"',
    'CURRENT_STAGE="El Torito and ISO volume metadata"',
    'ISO VALIDATION: boot metadata/volume ID PASS',
]:
    if needle not in verify:
        raise AssertionError(f"ISO verifier missing pipeline-safety marker: {needle}")

if "trusted-replace-fetch-response" in verify:
    raise AssertionError("ISO verifier still checks obsolete LiMusic pre-0.3.22 adblock marker")
for needle in [
    "org.limad.adblock-scriptlet-rules",
    "exact_key_replacements",
    "prune_keys",
    "validated_regex_replacements",
]:
    if needle not in verify:
        raise AssertionError(f"ISO verifier missing LiMusic 0.3.22 rule-schema check: {needle}")

for relative in [
    "build/prepare-liview-offline-repo.sh",
    "build/prepare-gaming-offline-repo.sh",
]:
    text = (ROOT / relative).read_text()
    if '< <(find' in text:
        raise AssertionError(f"{relative} still has a find process substitution that can SIGPIPE")
    if 'DEB_FILES=("$DESTINATION"/*.deb)' not in text:
        raise AssertionError(f"{relative} missing stable DEB file array")

validate_payload = (ROOT / "tests/validate-payload.sh").read_text()
if 'find "$ROOTFS/usr/share/limad/offline' in validate_payload and "| grep -q ." in validate_payload:
    raise AssertionError("validate-payload still uses find|grep -q for offline repositories")

workflow = (ROOT / ".github/workflows/build-iso.yml").read_text()
build_iso = (ROOT / "build/build-iso.sh").read_text()
for needle in [
    "uses: actions/cache@v4",
    "path: .cache/ubuntu-26.04-desktop-amd64.iso",
    "key: ubuntu-26.04-desktop-amd64-487f87faaf547ea30e0aba4d5b53346292571256b25333a978db1692bcee9dd2",
]:
    if needle not in workflow:
        raise AssertionError(f"GitHub workflow missing Ubuntu ISO cache marker: {needle}")
for needle in [
    "select_fastest_iso_url()",
    "https://nl.releases.ubuntu.com/26.04/$UBUNTU_ISO_NAME",
    "https://ftp.fau.de/ubuntu-releases/releases/26.04/$UBUNTU_ISO_NAME",
    'echo "Ubuntu ISO cache hit: $ISO"',
    '! -name "$UBUNTU_ISO_NAME"',
]:
    if needle not in build_iso:
        raise AssertionError(f"build-iso missing Ubuntu download/cache marker: {needle}")

print("V24 BUILD PIPELINE SAFETY TEST: PASS")
