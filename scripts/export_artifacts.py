#!/usr/bin/env python3
"""Copy manifest-declared final artifacts to a user-facing directory."""

from __future__ import annotations

import argparse
import filecmp
import json
import shutil
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--destination", required=True)
    parser.add_argument(
        "--manifest",
        default=str(REPO_ROOT / "config" / "artifacts.json"),
    )
    parser.add_argument("--source-dir", default=None)
    parser.add_argument("--groups", default=None, help="Comma-separated group names.")
    parser.add_argument(
        "--check",
        action="store_true",
        help="Report differences without copying files.",
    )
    parser.add_argument(
        "--require-complete",
        action="store_true",
        help="Fail if any selected artifact has not been generated.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    manifest = json.loads(Path(args.manifest).read_text(encoding="utf-8"))
    source_dir = Path(args.source_dir or manifest["output_directory"])
    destination_dir = Path(args.destination)
    selected = (
        {item.strip() for item in args.groups.split(",") if item.strip()}
        if args.groups
        else set(manifest["artifacts"])
    )
    unknown = selected - set(manifest["artifacts"])
    if unknown:
        raise SystemExit(f"unknown artifact groups: {', '.join(sorted(unknown))}")

    missing: list[str] = []
    changed: list[str] = []
    unchanged: list[str] = []
    for group_name, group in manifest["artifacts"].items():
        if group_name not in selected:
            continue
        for filename in group["files"]:
            source = source_dir / filename
            destination = destination_dir / filename
            if not source.is_file():
                missing.append(filename)
            elif destination.is_file() and filecmp.cmp(source, destination, shallow=False):
                unchanged.append(filename)
            else:
                changed.append(filename)
                if not args.check:
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(source, destination)

    report = {
        "mode": "check" if args.check else "copy",
        "source_directory": str(source_dir),
        "destination_directory": str(destination_dir),
        "missing": missing,
        "changed": changed,
        "unchanged": unchanged,
        "complete": not missing,
    }
    print(json.dumps(report, indent=2, sort_keys=True))
    if (args.require_complete and missing) or (args.check and (missing or changed)):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
