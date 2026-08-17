#!/usr/bin/python3
import pathlib
import subprocess
import tempfile
import yaml

ROOT = pathlib.Path(__file__).resolve().parents[1]
CONFIG = ROOT / "build" / "installer-whitelabel.yaml"
HOOK = ROOT / "build" / "casper-bottom" / "62limad-branding"
SLIDES = ROOT / "build" / "installer-slides" / "1"

config = yaml.safe_load(CONFIG.read_text(encoding="utf-8"))
if config.get("mode") != "standard":
    raise SystemExit("ERROR: installer mode must remain standard")
if config.get("app-name") != "LiMaD OS Installer":
    raise SystemExit("ERROR: LiMaD installer app-name missing")

theme = config.get("theme", {})
for variant in ("light", "dark"):
    if theme.get(variant, {}).get("accent-color") != "#BB7FF0":
        raise SystemExit(f"ERROR: LiMaD installer accent missing: {variant}")

pages = config.get("pages", {})
for page in ("try-or-install", "storage-icon", "done"):
    if page not in pages:
        raise SystemExit(f"ERROR: installer page branding missing: {page}")
    if not pages[page].get("image") or not pages[page].get("image-dark"):
        raise SystemExit(f"ERROR: light/dark installer image missing: {page}")

for name in ("slide_de_DE.html", "slide_en_US.html"):
    text = (SLIDES / name).read_text(encoding="utf-8")
    if "LiMaD OS 3.0" not in text:
        raise SystemExit(f"ERROR: LiMaD slide title missing: {name}")

with tempfile.TemporaryDirectory() as temp:
    temp_path = pathlib.Path(temp)
    source = temp_path / "source"
    target = temp_path / "root"
    (source / "images").mkdir(parents=True)
    (source / "slides" / "1").mkdir(parents=True)
    (target / "usr" / "share").mkdir(parents=True)

    (source / "whitelabel.yaml").write_bytes(CONFIG.read_bytes())
    for logo in ("limad-logo-192.png", "limad-logo-256.png"):
        (source / "images" / logo).write_bytes((ROOT / "build" / "branding" / logo).read_bytes())
    for slide in ("slide_de_DE.html", "slide_en_US.html"):
        (source / "slides" / "1" / slide).write_bytes((SLIDES / slide).read_bytes())

    env = {
        "PATH": "/usr/bin:/bin",
        "rootmnt": str(target),
        "LIMAD_INSTALLER_SOURCE": str(source),
    }
    subprocess.run([str(HOOK)], check=True, env=env)
    installed = target / "usr" / "share" / "desktop-provision"
    if not (installed / "whitelabel.yaml").is_file():
        raise SystemExit("ERROR: live branding hook did not install whitelabel.yaml")
    if not (installed / "slides" / "1" / "slide_de_DE.html").is_file():
        raise SystemExit("ERROR: live branding hook did not install German slide")

print("INSTALLER BRANDING TEST: PASS")
