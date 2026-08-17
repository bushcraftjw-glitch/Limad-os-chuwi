#!/usr/bin/python3
import copy
import pathlib
import sys
import yaml


def select_full_desktop(data):
    if isinstance(data, list):
        entries = data
        wrapper = None
    elif isinstance(data, dict):
        entries = data.get("sources")
        if not isinstance(entries, list):
            raise ValueError("SourceCatalog mapping has no list-valued 'sources' field")
        wrapper = copy.deepcopy(data)
    else:
        raise ValueError(f"unsupported install-sources YAML root type: {type(data).__name__}")

    matches = [entry for entry in entries if isinstance(entry, dict) and entry.get("id") == "ubuntu-desktop"]
    if len(matches) != 1:
        raise ValueError(f"expected exactly one ubuntu-desktop source, found {len(matches)}")

    selected = copy.deepcopy(matches[0])
    selected["default"] = True

    if wrapper is None:
        return [selected]

    wrapper["sources"] = [selected]
    return wrapper


def main():
    if len(sys.argv) != 3:
        raise SystemExit("usage: filter-install-sources.py INPUT OUTPUT")

    source = pathlib.Path(sys.argv[1])
    target = pathlib.Path(sys.argv[2])
    data = yaml.safe_load(source.read_text(encoding="utf-8"))

    try:
        result = select_full_desktop(data)
    except ValueError as exc:
        raise SystemExit(f"ERROR: {exc}") from exc

    target.write_text(
        yaml.safe_dump(result, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
