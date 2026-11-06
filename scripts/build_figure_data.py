#!/usr/bin/env python3
"""Materialize one canonical CSV file for each declared figure."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Iterator


REPO_ROOT = Path(__file__).resolve().parents[1]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--manifest",
        default=str(REPO_ROOT / "config" / "figure_data.json"),
    )
    parser.add_argument("--output-root", default=str(REPO_ROOT / "output"))
    parser.add_argument("--groups", default=None, help="Comma-separated group names.")
    return parser.parse_args()


def require_columns(reader: csv.DictReader, path: Path, columns: list[str]) -> None:
    missing = sorted(set(columns) - set(reader.fieldnames or ()))
    if missing:
        raise ValueError(f"missing columns in {path}: {', '.join(missing)}")


def projection_rows(output_root: Path, source: dict[str, object]) -> Iterator[list[str]]:
    path = output_root / str(source["path"])
    columns = [str(value) for value in source["columns"]]
    row_filter = source.get("filter")
    yield columns
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        required = columns.copy()
        if row_filter:
            required.append(str(row_filter["column"]))
        require_columns(reader, path, required)
        for row in reader:
            if row_filter and row[str(row_filter["column"])] != str(row_filter["value"]):
                continue
            yield [row[column] for column in columns]


def selected_family_rows(
    output_root: Path, source: dict[str, object]
) -> Iterator[list[str]]:
    directory = output_root / str(source["directory"])
    primes = [int(value) for value in source["primes"]]
    step = int(source["step"])
    window = int(source["moving_average_window"])
    raw_column = str(source["raw_column"])
    average_column = str(source["moving_average_column"])
    yield ["series", "p", "x", "value"]
    for prime in primes:
        stem = f"apm_atlas_p{prime:06d}_step{step}"
        inputs = (
            ("raw", directory / f"{stem}.csv", raw_column),
            ("moving_average", directory / f"{stem}_ma{window}.csv", average_column),
        )
        for series, path, value_column in inputs:
            with path.open(newline="", encoding="utf-8") as handle:
                reader = csv.DictReader(handle)
                require_columns(reader, path, ["x", value_column])
                for row in reader:
                    yield [series, str(prime), row["x"], row[value_column]]


def dataset_rows(output_root: Path, source: dict[str, object]) -> Iterator[list[str]]:
    kind = source["kind"]
    if kind == "csv_projection":
        return projection_rows(output_root, source)
    if kind == "selected_prime_family":
        return selected_family_rows(output_root, source)
    raise ValueError(f"unknown data source kind: {kind}")


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

    results: list[dict[str, object]] = []
    for group_name, datasets in manifest["groups"].items():
        if group_name not in selected:
            continue
        for dataset in datasets:
            destination = output_root / dataset["csv_file"]
            destination.parent.mkdir(parents=True, exist_ok=True)
            row_count = -1
            with destination.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.writer(handle, lineterminator="\n")
                for row_count, row in enumerate(dataset_rows(output_root, dataset["source"])):
                    writer.writerow(row)
            if row_count != int(dataset["rows"]):
                raise ValueError(
                    f"{destination} has {row_count} data rows, expected {dataset['rows']}"
                )
            results.append(
                {
                    "group": group_name,
                    "figure": dataset["figure"],
                    "csv_file": str(destination),
                    "rows": row_count,
                    "status": "ok",
                }
            )
    print(json.dumps({"dataset_count": len(results), "results": results, "status": "ok"}, indent=2))


if __name__ == "__main__":
    main()
