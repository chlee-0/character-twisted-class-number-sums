#!/usr/bin/env python3
r"""Build exact trace-bucket delta caches for A_p^\pm(x)."""

from __future__ import annotations

import argparse
import json
import multiprocessing as mp
import time
from pathlib import Path

import numpy as np


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--shared-npz", required=True, help="Shared DTUH bundle, ordered by (t,d).")
    parser.add_argument("--out-npz", required=True, help="Output compressed NPZ path.")
    parser.add_argument("--out-json", required=True, help="Output summary JSON path.")
    parser.add_argument("--p-limit", type=int, default=100, help="Store odd primes p with 3 < p < p-limit.")
    parser.add_argument(
        "--primes",
        help="Comma-separated exact prime list; overrides --p-limit.",
    )
    parser.add_argument("--xmax", type=int, default=1_000_000, help="Maximum x / trace bucket.")
    parser.add_argument("--processes", type=int, default=4, help="Worker processes.")
    return parser.parse_args()


def odd_primes_between_3_and(limit: int) -> np.ndarray:
    sieve = np.ones(limit, dtype=np.bool_)
    sieve[:2] = False
    for p in range(2, int(limit**0.5) + 1):
        if sieve[p]:
            sieve[p * p : limit : p] = False
    primes = np.nonzero(sieve)[0]
    return primes[primes > 3].astype(np.int32)


def selected_primes(raw: str | None, p_limit: int) -> np.ndarray:
    if raw is None:
        return odd_primes_between_3_and(p_limit)
    values = [int(value.strip()) for value in raw.split(",") if value.strip()]
    if not values:
        raise ValueError("--primes must contain at least one prime")
    if len(values) != len(set(values)):
        raise ValueError("--primes contains duplicates")
    for p in values:
        if p <= 3 or any(p % q == 0 for q in range(2, int(p**0.5) + 1)):
            raise ValueError(f"--primes contains a non-prime or unsupported value: {p}")
    return np.array(sorted(values), dtype=np.int32)


def legendre_table(p: int) -> np.ndarray:
    table = np.empty(p, dtype=np.int8)
    table[0] = 0
    for a in range(1, p):
        val = pow(a, (p - 1) // 2, p)
        table[a] = 1 if val == 1 else -1
    return table


D: np.ndarray
T: np.ndarray
U: np.ndarray
H: np.ndarray
XMAX: int


def init_worker(shared_path: str, xmax: int) -> None:
    global D, T, U, H, XMAX
    z = np.load(shared_path, allow_pickle=True)
    XMAX = int(xmax)
    d_all = z["d"].astype(np.int64)
    t_all = z["t"].astype(np.int64)
    u_all = z["u"].astype(np.int64)
    h_all = z["h"].astype(np.int64)
    mask = t_all <= XMAX
    D = d_all[mask]
    T = t_all[mask]
    U = u_all[mask]
    H = h_all[mask]


def compute_delta_for_prime(p: int) -> tuple[int, np.ndarray, np.ndarray]:
    d_mod = np.mod(D, p).astype(np.int64)
    t_mod = np.mod(T, p).astype(np.int64)
    u_mod = np.mod(U, p).astype(np.int64)
    leg = legendre_table(p)[d_mod]
    scalar = u_mod == 0
    split = (~scalar) & (leg == 1)
    ramified = (~scalar) & (leg == 0)

    inv2 = pow(2, -1, p)
    t_half_mod = (t_mod * inv2) % p
    sign = np.where(t_half_mod == 1, 1, -1).astype(np.int64)

    plus = np.zeros_like(H, dtype=np.int64)
    minus = np.zeros_like(H, dtype=np.int64)

    if np.any(scalar):
        plus[scalar] = H[scalar] * (((p + 1) * (p - 3)) // 2)
        minus[scalar] = H[scalar] * sign[scalar] * (((p + 1) * (p - 1)) // 2)
    if np.any(split):
        plus[split] = H[split] * (-2)
    if np.any(ramified):
        plus[ramified] = H[ramified] * ((p - 3) // 2)
        minus[ramified] = H[ramified] * sign[ramified] * ((p - 1) // 2)

    delta_plus = np.bincount(T, weights=plus, minlength=XMAX + 1).astype(np.int64)
    delta_minus = np.bincount(T, weights=minus, minlength=XMAX + 1).astype(np.int64)
    return int(p), delta_plus, delta_minus


def main() -> None:
    args = parse_args()
    shared_path = Path(args.shared_npz)
    out_npz = Path(args.out_npz)
    out_json = Path(args.out_json)
    if not shared_path.exists():
        raise SystemExit(f"Shared NPZ does not exist: {shared_path}")
    out_npz.parent.mkdir(parents=True, exist_ok=True)
    out_json.parent.mkdir(parents=True, exist_ok=True)

    primes = selected_primes(args.primes, int(args.p_limit))
    t0 = time.perf_counter()
    ctx = mp.get_context("fork")
    with ctx.Pool(
        int(args.processes),
        initializer=init_worker,
        initargs=(str(shared_path), int(args.xmax)),
    ) as pool:
        triples = pool.map(compute_delta_for_prime, [int(p) for p in primes.tolist()])
    wall = time.perf_counter() - t0

    triples.sort(key=lambda item: item[0])
    primes_out = np.array([item[0] for item in triples], dtype=np.int32)
    delta_plus = np.stack([item[1] for item in triples], axis=0)
    delta_minus = np.stack([item[2] for item in triples], axis=0)

    np.savez_compressed(
        out_npz,
        primes=primes_out,
        delta_plus=delta_plus,
        delta_minus=delta_minus,
        xmax=np.array([int(args.xmax)], dtype=np.int32),
        p_limit=np.array([int(args.p_limit) if args.primes is None else 0], dtype=np.int32),
    )

    summary = {
        "shared_npz": str(shared_path),
        "out_npz": str(out_npz),
        "xmax": int(args.xmax),
        "p_limit": int(args.p_limit),
        "requested_primes": args.primes,
        "prime_count": int(primes_out.shape[0]),
        "shape_delta_plus": list(delta_plus.shape),
        "shape_delta_minus": list(delta_minus.shape),
        "processes": int(args.processes),
        "wall_seconds": wall,
        "first_primes": [int(x) for x in primes_out[: min(5, len(primes_out))]],
        "last_primes": [int(x) for x in primes_out[max(0, len(primes_out) - 5) :]],
    }
    out_json.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
