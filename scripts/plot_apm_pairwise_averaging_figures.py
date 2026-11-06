#!/usr/bin/env python3
"""Build the split-versus-ramified figure used by the manuscript.

Run with Python, for example:

    python scripts/plot_apm_pairwise_averaging_figures.py
"""

from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.collections import PathCollection
import numpy as np

from apm_local_types import d0p_count_constant, odd_primes_between_3_and, sampled_type_rows

ETA_LO = 0.002
ETA_HI = 0.006
XMIN = 200_000
XMAX = 1_000_000
STEP = 5_000
CUTOFF = 20_000


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--shared-npz", default="data/apm_shared_tudh_x2000000.npz")
    parser.add_argument("--out-dir", default="output/figures")
    parser.add_argument("--pair-csv", default="output/cache/pairwise_primary_window_sample.csv")
    parser.add_argument("--summary-out", default="output/summaries/pairwise_primary_window.json")
    return parser.parse_args()


def load_or_make_pair_csv(shared_npz: Path, pair_csv: Path) -> None:
    pair_csv.parent.mkdir(parents=True, exist_ok=True)
    if pair_csv.exists():
        return

    max_prime_needed = min(CUTOFF, int(math.floor(ETA_HI * XMAX)) + 1)
    z = np.load(shared_npz)
    d_all = z["d"].astype(np.int64)
    t_all = z["t"].astype(np.int64)
    u_all = z["u"].astype(np.int64)
    h_all = z["h"].astype(np.int64)
    mask = t_all <= XMAX
    d, t, u, h = d_all[mask], t_all[mask], u_all[mask], h_all[mask]

    xs = np.arange(STEP, XMAX + 1, STEP, dtype=np.int64)
    primes = odd_primes_between_3_and(max_prime_needed + 1)
    cp = d0p_count_constant(primes)
    sqrtp = np.sqrt(primes.astype(np.float64))

    with pair_csv.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(
            [
                "x",
                "p",
                "eta",
                "scalar_ratio",
                "split_ratio",
                "ramified_ratio",
                "total_ratio",
                "denominator_cp",
            ]
        )
        for i, p_raw in enumerate(primes.tolist()):
            p = int(p_raw)
            rows = sampled_type_rows(p, d, t, u, h, xs, XMAX)
            denom_factor = float(cp[i] * sqrtp[i])
            for j, x_raw in enumerate(xs.tolist()):
                x = int(x_raw)
                if x < XMIN:
                    continue
                eta = p / x
                if not (ETA_LO <= eta <= ETA_HI):
                    continue
                denom = x * denom_factor
                writer.writerow(
                    [
                        x,
                        p,
                        eta,
                        float(rows["scalar"][j]) / denom,
                        float(rows["split"][j]) / denom,
                        float(rows["ramified"][j]) / denom,
                        float(rows["total"][j]) / denom,
                        denom,
                    ]
                )


def load_pair_arrays(pair_csv: Path) -> dict[str, np.ndarray]:
    values: dict[str, list[float]] = {
        "x": [],
        "p": [],
        "eta": [],
        "scalar": [],
        "split": [],
        "ramified": [],
        "total": [],
        "den": [],
    }
    with pair_csv.open(newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            values["x"].append(float(row["x"]))
            values["p"].append(float(row["p"]))
            values["eta"].append(float(row["eta"]))
            values["scalar"].append(float(row["scalar_ratio"]))
            values["split"].append(float(row["split_ratio"]))
            values["ramified"].append(float(row["ramified_ratio"]))
            values["total"].append(float(row["total_ratio"]))
            values["den"].append(float(row["denominator_cp"]))
    arrays = {key: np.array(val) for key, val in values.items()}
    return arrays


def binned_pair_means(values: dict[str, np.ndarray]) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    bins = np.linspace(ETA_LO, ETA_HI, 25)
    mids: list[float] = []
    split: list[float] = []
    ramified: list[float] = []
    eta = values["eta"]
    for a, b in zip(bins[:-1], bins[1:]):
        mask = (eta >= a) & (eta < b)
        if not np.any(mask):
            continue
        mids.append((a + b) / 2)
        split.append(float(np.mean(values["split"][mask])))
        ramified.append(float(np.mean(values["ramified"][mask])))
    return np.array(mids), np.array(split), np.array(ramified)


def savefig(out_dir: Path, name: str) -> None:
    plt.tight_layout()
    plt.savefig(out_dir / f"{name}.png", dpi=180)
    plt.close()


def plot_split_ramified(values: dict[str, np.ndarray], out_dir: Path) -> dict[str, object]:
    bin_eta, bin_split, bin_ramified = binned_pair_means(values)
    plt.figure(figsize=(7.0, 4.6))
    plt.scatter(values["eta"], values["split"], s=3, alpha=0.06, color="#1d4ed8", linewidths=0, label="split pairs")
    plt.scatter(
        values["eta"],
        values["ramified"],
        s=3,
        alpha=0.06,
        color="#b45309",
        linewidths=0,
        label="ramified pairs",
    )
    plt.plot(bin_eta, bin_split, color="#1d4ed8", lw=2.0, label="split bin mean")
    plt.plot(bin_eta, bin_ramified, color="#b45309", lw=2.0, label="ramified bin mean")
    yrange = np.concatenate([values["split"], values["ramified"]])
    plt.ylim(np.quantile(yrange, 0.01), np.quantile(yrange, 0.99))
    plt.xlabel(r"$\eta=p/x$")
    plt.ylabel(r"$A_p^T(x)/(C_p x\sqrt{p})$")
    plt.grid(alpha=0.25)
    legend = plt.legend(fontsize=8, ncol=2, loc="upper right")
    # Keep dense scatter points faint, but make their legend markers visible.
    for handle in legend.legend_handles:
        if isinstance(handle, PathCollection):
            handle.set_alpha(1.0)
            handle.set_sizes([24])
    savefig(out_dir, "apm_experiments_split_ramified")

    return {
        "pair_count": int(len(values["total"])),
        "split_bin_count": int(len(bin_split)),
        "ramified_bin_count": int(len(bin_ramified)),
    }


def main() -> None:
    args = parse_args()
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    pair_csv = Path(args.pair_csv)
    summary_path = Path(args.summary_out)
    summary_path.parent.mkdir(parents=True, exist_ok=True)

    load_or_make_pair_csv(Path(args.shared_npz), pair_csv)
    values = load_pair_arrays(pair_csv)

    summary = {
        "window": [ETA_LO, ETA_HI],
        "xmin": XMIN,
        "xmax": XMAX,
        "step": STEP,
        "cutoff": CUTOFF,
        "split_ramified": plot_split_ramified(values, out_dir),
    }
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
