from __future__ import annotations

import argparse
import json
import sys

from . import __version__
from .core import find_duplicates, human_size


def parse_size(text: str) -> int:
    units = {"b": 1, "k": 1024, "m": 1024**2, "g": 1024**3}
    text = text.strip().lower().rstrip("b") or "0"
    if text[-1] in units:
        return int(float(text[:-1]) * units[text[-1]])
    return int(text)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog="dupefind", description="Find duplicate files by content."
    )
    ap.add_argument("paths", nargs="*", default=["."], help="folders/files to scan")
    ap.add_argument("-m", "--min-size", default="1", help="ignore smaller files (e.g. 10k, 5M)")
    ap.add_argument("-x", "--exclude", action="append", default=[], help="folder name to skip (repeatable)")
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    ap.add_argument("--delete", action="store_true", help="delete extras, keeping the oldest copy (asks first)")
    ap.add_argument("-y", "--yes", action="store_true", help="don't ask for confirmation with --delete")
    ap.add_argument("-V", "--version", action="version", version=__version__)
    args = ap.parse_args(argv)

    exclude = [".git", "node_modules", "__pycache__", *args.exclude]
    groups = find_duplicates(args.paths, parse_size(args.min_size), exclude)
    wasted = sum(g[0].stat().st_size * (len(g) - 1) for g in groups)

    if args.json:
        print(json.dumps({
            "wasted_bytes": wasted,
            "groups": [{"size": g[0].stat().st_size, "files": [str(p) for p in g]} for g in groups],
        }, indent=2))
    else:
        for g in groups:
            print(f"\n{human_size(g[0].stat().st_size)} x {len(g)}")
            for i, p in enumerate(g):
                print(f"  {'keep' if i == 0 else 'dup '}  {p}")
        print(f"\n{len(groups)} duplicate group(s), {human_size(wasted)} reclaimable.")

    if args.delete and groups:
        extras = [p for g in groups for p in g[1:]]
        if not args.yes:
            if input(f"Delete {len(extras)} file(s)? [y/N] ").strip().lower() != "y":
                print("Aborted.")
                return 1
        for p in extras:
            try:
                p.unlink()
                print(f"deleted {p}", file=sys.stderr)
            except OSError as e:
                print(f"failed {p}: {e}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
