#!/usr/bin/env python3
"""Verify the tracked numerical input against its manifest."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np


REPO_ROOT = Path(__file__).resolve().parents[1]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--manifest",
        default=str(REPO_ROOT / "data" / "manifest.json"),
    )
    parser.add_argument(
        "--input",
        default=None,
        help="Override the path of the single input declared in the manifest.",
    )
    return parser.parse_args()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def scalar_value(archive: np.lib.npyio.NpzFile, key: str) -> object:
    value = archive[key]
    if value.size != 1:
        raise ValueError(f"metadata field {key!r} is not scalar")
    return value.reshape(-1)[0]


def verify(manifest_path: Path, override: str | None) -> dict[str, object]:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("schema_version") != 1:
        raise ValueError("unsupported input manifest schema")
    inputs = manifest.get("inputs")
    if not isinstance(inputs, list) or len(inputs) != 1:
        raise ValueError("expected exactly one canonical input")
    spec = inputs[0]

    path = Path(override) if override else REPO_ROOT / spec["path"]
    if not path.is_file():
        raise FileNotFoundError(path)
    actual_bytes = path.stat().st_size
    if actual_bytes != spec["bytes"]:
        raise ValueError(f"size mismatch: expected {spec['bytes']}, got {actual_bytes}")
    actual_sha256 = sha256(path)
    if actual_sha256 != spec["sha256"]:
        raise ValueError(
            f"SHA-256 mismatch: expected {spec['sha256']}, got {actual_sha256}"
        )

    with np.load(path, allow_pickle=True) as archive:
        for name, array_spec in spec["arrays"].items():
            if name not in archive.files:
                raise ValueError(f"missing array {name!r}")
            array = archive[name]
            if str(array.dtype) != array_spec["dtype"]:
                raise ValueError(f"dtype mismatch for {name}")
            if list(array.shape) != array_spec["shape"]:
                raise ValueError(f"shape mismatch for {name}")

        metadata = spec["metadata"]
        for key in ("row_count", "complete_up_to_eps", "enumerator", "source_db"):
            actual = scalar_value(archive, key)
            expected = metadata[key]
            if str(actual) != str(expected):
                raise ValueError(
                    f"metadata mismatch for {key}: expected {expected!r}, got {actual!r}"
                )

        t = archive["t"].astype(np.int64, copy=False)
        d = archive["d"].astype(np.int64, copy=False)
        invariants = spec["invariants"]
        if int(t.min()) != invariants["t_min"] or int(t.max()) != invariants["t_max"]:
            raise ValueError("trace range mismatch")
        sorted_td = np.all((t[1:] > t[:-1]) | ((t[1:] == t[:-1]) & (d[1:] >= d[:-1])))
        if not bool(sorted_td):
            raise ValueError("rows are not ordered by (t,d)")

    return {
        "id": spec["id"],
        "path": str(path),
        "bytes": actual_bytes,
        "sha256": actual_sha256,
        "row_count": metadata["row_count"],
        "complete_up_to_eps": metadata["complete_up_to_eps"],
        "ordering": invariants["ordering"],
        "status": "ok",
    }


def main() -> None:
    args = parse_args()
    result = verify(Path(args.manifest), args.input)
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
