#!/usr/bin/env python3
"""Plot the five normalized B_p remainder terms as (eta, value) pairs."""

from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from apm_local_types import (
    li_x_squared,
    odd_primes_between_3_and,
    sampled_secondary_rows,
)

ETA_LO = 0.002
ETA_HI = 0.006
XMIN = 200_000
XMAX = 1_000_000
STEP = 5_000


# Display notation follows the manuscript; retain the historical CSV keys.
TERMS = {
    "split": {
        "filename": "apm_experiments_survivor_split.png",
        "title": "split even remainder",
        "ylabel": r"$B_p^{\mathrm{sp},+}(x)$",
        "color": "#2563eb",
        "legend_loc": "upper right",
    },
    "ram0": {
        "filename": "apm_experiments_survivor_ramified_zero.png",
        "title": "ramified even remainder",
        "ylabel": r"$B_p^{\mathrm{ram},+}(x)$",
        "color": "#059669",
        "legend_loc": "lower left",
    },
    "scalar0": {
        "filename": "apm_experiments_survivor_scalar_zero.png",
        "title": "scalar even remainder",
        "ylabel": r"$B_p^{\mathrm{sc},+}(x)$",
        "color": "#7c3aed",
        "legend_loc": "upper left",
    },
    "ramsigma": {
        "filename": "apm_experiments_survivor_ramified_sigma.png",
        "title": "ramified odd remainder",
        "ylabel": r"$B_p^{\mathrm{ram},-}(x)$",
        "color": "#d97706",
        "legend_loc": "lower left",
    },
    "scalarsigma": {
        "filename": "apm_experiments_survivor_scalar_sigma.png",
        "title": "scalar odd remainder",
        "ylabel": r"$B_p^{\mathrm{sc},-}(x)$",
        "color": "#be185d",
        "legend_loc": "upper right",
        "point_alpha": 0.70,
        "y_padding": 0.05,
    },
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--shared-npz", default="data/apm_shared_tudh_x2000000.npz")
    parser.add_argument("--out-dir", default="output/figures")
    parser.add_argument(
        "--summary-out",
        default="output/summaries/apm_surviving_terms.json",
    )
    parser.add_argument(
        "--values-csv",
        default=None,
        help="Render from an existing survivor-value CSV instead of recomputing it.",
    )
    return parser.parse_args()


def binned_means(
    eta: np.ndarray,
    value: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    bins = np.linspace(ETA_LO, ETA_HI, 25)
    mids: list[float] = []
    means: list[float] = []
    for left, right in zip(bins[:-1], bins[1:]):
        mask = (eta >= left) & (eta < right)
        if np.any(mask):
            mids.append(float((left + right) / 2.0))
            means.append(float(np.mean(value[mask])))
    return np.array(mids), np.array(means)


def summarize(values: np.ndarray) -> dict[str, float]:
    return {
        "min": float(np.min(values)),
        "q01": float(np.quantile(values, 0.01)),
        "q10": float(np.quantile(values, 0.10)),
        "mean": float(np.mean(values)),
        "median": float(np.median(values)),
        "q90": float(np.quantile(values, 0.90)),
        "q99": float(np.quantile(values, 0.99)),
        "max": float(np.max(values)),
    }


def load_values_csv(
    path: Path,
) -> tuple[dict[str, list[float]], list[float], list[int], list[int]]:
    values: dict[str, list[float]] = {name: [] for name in TERMS}
    etas: list[float] = []
    ps: list[int] = []
    xvals: list[int] = []
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        required = {"x", "p", "eta", *TERMS}
        missing = sorted(required - set(reader.fieldnames or ()))
        if missing:
            raise ValueError(f"missing columns in {path}: {', '.join(missing)}")
        for row in reader:
            xvals.append(int(row["x"]))
            ps.append(int(row["p"]))
            etas.append(float(row["eta"]))
            for name in TERMS:
                values[name].append(float(row[name]))
    return values, etas, ps, xvals


def main() -> None:
    args = parse_args()
    out_dir = Path(args.out_dir)
    summary_path = Path(args.summary_out)
    out_dir.mkdir(parents=True, exist_ok=True)
    summary_path.parent.mkdir(parents=True, exist_ok=True)

    values_csv = Path(args.values_csv) if args.values_csv else None
    if values_csv is not None:
        values, etas, ps, xvals = load_values_csv(values_csv)
        prime_count = len(set(ps))
    else:
        z = np.load(args.shared_npz)
        d_all = z["d"].astype(np.int64)
        t_all = z["t"].astype(np.int64)
        u_all = z["u"].astype(np.int64)
        h_all = z["h"].astype(np.int64)
        mask = t_all <= XMAX
        d = d_all[mask]
        t = t_all[mask]
        u = u_all[mask]
        h = h_all[mask]

        xs = np.arange(STEP, XMAX + 1, STEP, dtype=np.int64)
        max_prime_needed = int(math.floor(ETA_HI * XMAX)) + 2
        primes = odd_primes_between_3_and(max_prime_needed)
        prime_count = len(primes)

        values = {name: [] for name in TERMS}
        etas = []
        ps = []
        xvals = []
        for p in primes.tolist():
            rows = sampled_secondary_rows(int(p), d, t, u, h, xs, XMAX)
            sqrt_p = math.sqrt(float(p))
            for j, x_raw in enumerate(xs.tolist()):
                x = int(x_raw)
                if x < XMIN:
                    continue
                eta = float(p) / float(x)
                if not (ETA_LO <= eta <= ETA_HI):
                    continue

                li = li_x_squared(x)
                denom = float(x) * sqrt_p
                etas.append(eta)
                ps.append(int(p))
                xvals.append(x)
                values["split"].append(
                    (float(rows["split"][j]) + ((p - 3.0) / (p - 1.0)) * li) / denom
                )
                values["ram0"].append(
                    (float(rows["ram0"][j]) - ((p - 3.0) / p) * li) / denom
                )
                values["scalar0"].append(
                    (float(rows["scalar0"][j]) - ((p - 3.0) / (p * (p - 1.0))) * li)
                    / denom
                )
                values["ramsigma"].append(float(rows["ramsigma"][j]) / denom)
                values["scalarsigma"].append(float(rows["scalarsigma"][j]) / denom)

    eta_arr = np.array(etas, dtype=np.float64)
    summary: dict[str, object] = {
        "eta_window": [ETA_LO, ETA_HI],
        "x_window": [XMIN, XMAX],
        "step": STEP,
        "pair_count": int(len(eta_arr)),
        "prime_count": int(prime_count),
        "cp_was_not_used_in_denominator": True,
        "outputs": {},
    }

    for name, info in TERMS.items():
        val = np.array(values[name], dtype=np.float64)
        mids, means = binned_means(eta_arr, val)
        sparse_scalar = name == "scalarsigma"
        point_size = info.get("point_size", 4)
        point_zorder = 3 if sparse_scalar else 1
        mean_zorder = 4 if sparse_scalar else 2
        zero_zorder = 1 if sparse_scalar else 2

        plt.figure(figsize=(7.0, 4.6))
        plt.scatter(eta_arr, val, s=point_size, alpha=info.get("point_alpha", 0.13), color=info["color"], linewidths=0, zorder=point_zorder)
        plt.plot(mids, means, color="#111827", lw=1.8, label="bin mean", zorder=mean_zorder)
        plt.axhline(0, color="#6b7280", lw=1.0, ls="--", zorder=zero_zorder)
        plt.xlabel(r"$\eta=p/x$")
        plt.ylabel(info["ylabel"])
        plt.title(info["title"])
        ylo = float(np.quantile(val, 0.01))
        yhi = float(np.quantile(val, 0.99))
        if ylo == yhi:
            ylo = float(np.min(val))
            yhi = float(np.max(val))
        if ylo == yhi:
            ylo -= 1.0
            yhi += 1.0
        # A zero-heavy sample must not put its point mass on the plot boundary.
        padding = info.get("y_padding", 0.0) * (yhi - ylo)
        ylo -= padding
        yhi += padding
        plt.ylim(ylo, yhi)
        plt.grid(alpha=0.25)
        plt.legend(fontsize=8, loc=info["legend_loc"])
        plt.tight_layout()
        plt.savefig(out_dir / str(info["filename"]), dpi=180)
        plt.close()

        comparison_filename = str(info["filename"]).replace(".png", "_bin_mean_compare.png")
        plt.figure(figsize=(7.0, 4.6))
        plt.scatter(eta_arr, val, s=point_size, alpha=info.get("point_alpha", 0.10), color=info["color"], linewidths=0, zorder=point_zorder)
        plt.plot(mids, means, color="#111827", lw=1.8, label="bin mean", zorder=mean_zorder)
        plt.axhline(0, color="#6b7280", lw=1.0, ls=":", zorder=zero_zorder)
        plt.xlabel(r"$\eta=p/x$")
        plt.ylabel(info["ylabel"])
        plt.title(info["title"])
        plt.ylim(ylo, yhi)
        plt.grid(alpha=0.25)
        plt.legend(fontsize=8, loc=info["legend_loc"])
        plt.tight_layout()
        plt.savefig(out_dir / comparison_filename, dpi=180)
        plt.close()

        summary["outputs"][name] = {
            "file": str(out_dir / str(info["filename"])),
            "bin_mean_comparison_file": str(out_dir / comparison_filename),
            "summary": summarize(val),
        }

    csv_path = values_csv if values_csv is not None else summary_path.with_suffix(".csv")
    if values_csv is None:
        with csv_path.open("w", newline="", encoding="utf-8") as fh:
            writer = csv.writer(fh)
            writer.writerow(["x", "p", "eta"] + list(TERMS))
            for i, eta in enumerate(eta_arr.tolist()):
                writer.writerow([xvals[i], ps[i], eta] + [values[name][i] for name in TERMS])
    summary["csv"] = str(csv_path)
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
