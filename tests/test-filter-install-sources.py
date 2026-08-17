#!/usr/bin/python3
import copy
import importlib.util
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "tools" / "filter-install-sources.py"
spec = importlib.util.spec_from_file_location("filter_install_sources", MODULE_PATH)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

minimal = {
    "id": "ubuntu-desktop-minimal",
    "variant": "desktop",
    "path": "minimal.squashfs",
    "size": 1,
    "type": "fsimage",
    "default": True,
}
full = {
    "id": "ubuntu-desktop",
    "variant": "desktop",
    "path": "minimal.standard.squashfs",
    "size": 2,
    "type": "fsimage-layered",
}

legacy = module.select_full_desktop([copy.deepcopy(minimal), copy.deepcopy(full)])
assert isinstance(legacy, list)
assert len(legacy) == 1
assert legacy[0]["id"] == "ubuntu-desktop"
assert legacy[0]["default"] is True

catalog = {
    "version": 2,
    "sources": [copy.deepcopy(minimal), copy.deepcopy(full)],
    "kernel": {
        "default": "linux-generic",
        "bridge": "linux-generic-hwe-26.04",
        "bridge_reasons": ["drivers"],
    },
}
result = module.select_full_desktop(copy.deepcopy(catalog))
assert isinstance(result, dict)
assert result["version"] == 2
assert result["kernel"] == catalog["kernel"]
assert len(result["sources"]) == 1
assert result["sources"][0]["id"] == "ubuntu-desktop"
assert result["sources"][0]["default"] is True

try:
    module.select_full_desktop({"version": 2, "sources": [copy.deepcopy(minimal)], "kernel": {"default": "linux-generic"}})
except ValueError:
    pass
else:
    raise AssertionError("missing ubuntu-desktop source must fail")

print("INSTALL SOURCES FILTER TEST: PASS")
