#!/usr/bin/python3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
packages = [
    line.strip()
    for line in (ROOT / 'build/gaming-packages.txt').read_text().splitlines()
    if line.strip() and not line.lstrip().startswith('#')
]
required = {
    'steam-installer',
    'steam-devices',
    'lutris',
    'protontricks',
    'wine',
    'wine32:i386',
    'winetricks',
    'gamemode',
    'mangohud',
    'gamescope',
    'vulkan-tools',
    'mesa-vulkan-drivers:amd64',
    'mesa-vulkan-drivers:i386',
    'libvulkan1:amd64',
    'libvulkan1:i386',
    'libglx-mesa0:i386',
    'mesa-utils',
    'vkbasalt',
    'goverlay',
}
missing = sorted(required.difference(packages))
if missing:
    raise AssertionError(f'gaming package list missing: {missing}')

repo = (ROOT / 'build/prepare-gaming-offline-repo.sh').read_text()
if '< <(find' in repo:
    raise AssertionError('gaming repo builder must not use early-closing find process substitutions')
for needle in [
    'arch=amd64,i386',
    'APT::Architectures::=amd64',
    'APT::Architectures::=i386',
    'steam-libs-i386',
    'mesa-vulkan-drivers',
    'libvulkan1',
    'libglx-mesa0',
    'dpkg-scanpackages --multiversion',
]:
    if needle not in repo:
        raise AssertionError(f'gaming repo builder missing {needle!r}')

deps = (ROOT / 'build/rootfs/usr/local/bin/limad-gaming-deps').read_text()
for needle in [
    'dpkg --add-architecture i386',
    '/usr/share/limad/offline/gaming',
    'steam-installer',
    'steam-libs-i386:i386',
    'lutris',
    'protontricks',
    'gamemoderun',
    'mangohud',
    'gamescope',
    'vulkaninfo',
]:
    if needle not in deps:
        raise AssertionError(f'gaming dependency helper missing {needle!r}')

payload = (ROOT / 'build/prepare-payload.sh').read_text()
if 'prepare-gaming-offline-repo.sh' not in payload:
    raise AssertionError('gaming offline repository is not added to payload')

installer = (ROOT / 'build/install-target.sh').read_text()
if '/usr/local/bin/limad-gaming-deps' not in installer:
    raise AssertionError('gaming dependency helper is not called by target installer')
for line in installer.splitlines():
    if '/usr/local/bin/limad-gaming-deps' in line and '|| true' in line:
        raise AssertionError('gaming dependency installation must be install-critical')

user_apps = (ROOT / 'build/rootfs/usr/local/bin/limad-required-user-apps').read_text()
for needle in [
    'EASYEFFECTS_ID="com.github.wwmm.easyeffects"',
    'PROTONUP_ID="net.davidotek.pupgui2"',
    'install_user_app "$EASYEFFECTS_ID"',
    'install_user_app "$PROTONUP_ID"',
]:
    if needle not in user_apps:
        raise AssertionError(f'required user apps missing {needle!r}')

print('V24 GAMING TEST: PASS')
