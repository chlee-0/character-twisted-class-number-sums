#!/usr/bin/env python3
"""Verify declared artifacts by existence and optional reference hash."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--manifest",
        default=str(REPO_ROOT / "config" / "artifacts.json"),
    )
    parser.add_argument("--source-dir", default=None)
    parser.add_argument("--groups", default=None, help="Comma-separated group names.")
    parser.add_argument(
        "--reference-hashes",
        action="store_true",
        help="Require byte-identical hashes to the audited reference artifacts.",
    )
    parser.add_argument("--report-out", default=None)
    return parser.parse_args()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    args = parse_args()
    manifest = json.loads(Path(args.manifest).read_text(encoding="utf-8"))
    source_dir = Path(args.source_dir or manifest["output_directory"])
    selected = (
        {item.strip() for item in args.groups.split(",") if item.strip()}
        if args.groups
        else set(manifest["artifacts"])
    )
    unknown = selected - set(manifest["artifacts"])
    if unknown:
        raise SystemExit(f"unknown artifact groups: {', '.join(sorted(unknown))}")

    results: list[dict[str, object]] = []
    failures = 0
    for group_name, group in manifest["artifacts"].items():
        if group_name not in selected:
            continue
        for filename, expected_hash in group["files"].items():
            path = source_dir / filename
            item: dict[str, object] = {
                "group": group_name,
                "file": filename,
                "path": str(path),
            }
            if not path.is_file():
                item["status"] = "missing"
                failures += 1
            else:
                actual_hash = sha256(path)
                item["bytes"] = path.stat().st_size
                item["sha256"] = actual_hash
                if args.reference_hashes and actual_hash != expected_hash:
                    item["status"] = "hash-mismatch"
                    item["expected_sha256"] = expected_hash
                    failures += 1
                else:
                    item["status"] = "ok"
            results.append(item)

    report = {
        "source_directory": str(source_dir),
        "reference_hashes_checked": bool(args.reference_hashes),
        "artifact_count": len(results),
        "failure_count": failures,
        "results": results,
        "status": "ok" if failures == 0 else "failed",
    }
    text = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.report_out:
        report_path = Path(args.report_out)
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(text, encoding="utf-8")
    print(text, end="")
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
