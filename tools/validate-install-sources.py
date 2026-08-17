#!/usr/bin/python3
import argparse
import copy
import pathlib
import sys
import yaml


def load(path):
    return yaml.safe_load(pathlib.Path(path).read_text(encoding="utf-8"))


def get_sources(data):
    if isinstance(data, list):
        return data
    if isinstance(data, dict) and isinstance(data.get("sources"), list):
        return data["sources"]
    raise ValueError("unsupported install-sources structure")


def validate_filtered(data):
    sources = get_sources(data)
    if len(sources) != 1:
        raise ValueError(f"expected one filtered source, found {len(sources)}")
    source = sources[0]
    if not isinstance(source, dict):
        raise ValueError("filtered source is not a mapping")
    if source.get("id") != "ubuntu-desktop":
        raise ValueError(f"filtered source id is {source.get('id')!r}, expected 'ubuntu-desktop'")
    if source.get("default") is not True:
        raise ValueError("ubuntu-desktop source is not marked default")
    if any(isinstance(entry, dict) and entry.get("id") == "ubuntu-desktop-minimal" for entry in sources):
        raise ValueError("ubuntu-desktop-minimal remains in filtered catalog")
    if isinstance(data, dict):
        if not isinstance(data.get("version"), int):
            raise ValueError("SourceCatalog version is missing or invalid")
        if not isinstance(data.get("kernel"), dict):
            raise ValueError("SourceCatalog kernel metadata is missing or invalid")


def validate_preservation(original, filtered):
    original_sources = get_sources(original)
    matches = [entry for entry in original_sources if isinstance(entry, dict) and entry.get("id") == "ubuntu-desktop"]
    if len(matches) != 1:
        raise ValueError(f"original catalog contains {len(matches)} ubuntu-desktop sources")

    if isinstance(original, list):
        if not isinstance(filtered, list):
            raise ValueError("legacy list catalog changed root type")
        return

    if not isinstance(filtered, dict):
        raise ValueError("SourceCatalog mapping changed root type")

    original_meta = copy.deepcopy(original)
    filtered_meta = copy.deepcopy(filtered)
    original_meta.pop("sources", None)
    filtered_meta.pop("sources", None)
    if original_meta != filtered_meta:
        raise ValueError("SourceCatalog metadata changed while filtering")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("filtered")
    parser.add_argument("--original")
    args = parser.parse_args()

    try:
        filtered = load(args.filtered)
        validate_filtered(filtered)
        if args.original:
            validate_preservation(load(args.original), filtered)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc

    print("INSTALL SOURCES VALIDATION: PASS")


if __name__ == "__main__":
    main()
