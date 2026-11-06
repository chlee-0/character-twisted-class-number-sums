#!/usr/bin/env python3
"""Verify the actual CSV file recorded for each declared figure."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--manifest",
        default=str(REPO_ROOT / "config" / "figure_data.json"),
    )
    parser.add_argument("--output-root", default=str(REPO_ROOT / "output"))
    parser.add_argument("--groups", default=None, help="Comma-separated group names.")
    parser.add_argument("--report-out", default=None)
    return parser.parse_args()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def csv_rows(path: Path) -> int:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.reader(handle)
        try:
            next(reader)
        except StopIteration:
            return -1
        return sum(1 for _ in reader)


def main() -> None:
    args = parse_args()
    manifest = json.loads(Path(args.manifest).read_text(encoding="utf-8"))
    output_root = Path(args.output_root)
    selected = (
        {value.strip() for value in args.groups.split(",") if value.strip()}
        if args.groups
        else set(manifest["groups"])
    )
    unknown = selected - set(manifest["groups"])
    if unknown:
        raise SystemExit(f"unknown data groups: {', '.join(sorted(unknown))}")

    failures = 0
    results: list[dict[str, object]] = []
    for group_name, datasets in manifest["groups"].items():
        if group_name not in selected:
            continue
        for dataset in datasets:
            path = output_root / dataset["csv_file"]
            item = {
                "group": group_name,
                "figure": dataset["figure"],
                "csv_file": str(path),
            }
            if not path.is_file():
                item["status"] = "missing"
                failures += 1
            else:
                actual_hash = sha256(path)
                actual_rows = csv_rows(path)
                item.update(
                    {
                        "bytes": path.stat().st_size,
                        "rows": actual_rows,
                        "csv_file_sha256": actual_hash,
                    }
                )
                expected_hash = dataset["csv_file_sha256"]
                expected_rows = int(dataset["rows"])
                if actual_hash != expected_hash or actual_rows != expected_rows:
                    item.update(
                        {
                            "status": "mismatch",
                            "expected_rows": expected_rows,
                            "expected_csv_file_sha256": expected_hash,
                        }
                    )
                    failures += 1
                else:
                    item["status"] = "ok"
            results.append(item)

    report = {
        "output_root": str(output_root),
        "dataset_count": len(results),
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
