from __future__ import annotations
import argparse
from . import APP_NAME, VERSION


def main() -> int:
    parser = argparse.ArgumentParser(prog="limad-grubenvolk", description="GRUBENVOLK for LiMaD OS")
    parser.add_argument("--version", action="version", version=f"{APP_NAME} {VERSION}")
    parser.parse_args()
    from .shell import launch
    return launch()


if __name__ == "__main__":
    raise SystemExit(main())
