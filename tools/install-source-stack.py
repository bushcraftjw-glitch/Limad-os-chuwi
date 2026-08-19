#!/usr/bin/python3
from __future__ import annotations

import argparse
import os
from pathlib import Path

import yaml


def get_sources(data):
    if isinstance(data, list):
        return data
    if isinstance(data, dict) and isinstance(data.get("sources"), list):
        return data["sources"]
    raise ValueError("unsupported install-sources structure")


def select_source(data, source_id: str):
    matches = [entry for entry in get_sources(data) if isinstance(entry, dict) and entry.get("id") == source_id]
    if len(matches) != 1:
        raise ValueError(f"expected exactly one {source_id!r} source, found {len(matches)}")
    return matches[0]


def source_path(entry) -> str:
    path = entry.get("path")
    if isinstance(path, str) and path:
        return path

    variations = entry.get("variations")
    if isinstance(variations, dict):
        default = variations.get("default")
        if isinstance(default, dict):
            path = default.get("path")
            if isinstance(path, str) and path:
                return path
        candidates = [
            value.get("path")
            for value in variations.values()
            if isinstance(value, dict) and isinstance(value.get("path"), str) and value.get("path")
        ]
        if len(candidates) == 1:
            return candidates[0]

    raise ValueError("selected install source has no unambiguous image path")


def image_stack(entry):
    image_type = entry.get("type")
    path = source_path(entry)
    if path.startswith("/"):
        path = path.lstrip("/")

    if image_type == "fsimage":
        return [path]
    if image_type != "fsimage-layered":
        raise ValueError(f"unsupported install source type: {image_type!r}")

    directory = os.path.dirname(path)
    filename = os.path.basename(path)
    stem, extension = os.path.splitext(filename)
    if not stem or not extension:
        raise ValueError(f"invalid layered image path: {path!r}")

    parts = stem.split(".")
    result = []
    for index in range(1, len(parts) + 1):
        name = ".".join(parts[:index]) + extension
        result.append(os.path.join(directory, name) if directory else name)
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("catalog", type=Path)
    parser.add_argument("--source-id", default="ubuntu-desktop")
    args = parser.parse_args()

    data = yaml.safe_load(args.catalog.read_text(encoding="utf-8"))
    try:
        entry = select_source(data, args.source_id)
        stack = image_stack(entry)
    except ValueError as exc:
        raise SystemExit(f"ERROR: {exc}") from exc

    for path in stack:
        print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
