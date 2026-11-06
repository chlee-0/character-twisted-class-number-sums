#!/usr/bin/env python3
"""Generate the diverse-prime A_p bundle CSV and TeX artifacts."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

import numpy as np

FAMILIES = {
    "plus": ("plus_ratio", "plus_ratio_ma", "blue!70!black"),
    "minus": ("minus_ratio", "minus_ratio_ma", "red!70!black"),
    "sum": ("sum_ratio", "sum_ratio_ma", "green!45!black"),
}


def d0p_count_constant(p: int) -> float:
    return (35.0 / 32.0) * ((p**3 + p * p + 3.0 * p - 1.0) / (p * (p * p + 1.0)))


def sampled_prefix_sums(delta_rows: np.ndarray, xs: np.ndarray) -> np.ndarray:
    if delta_rows.ndim != 2:
        raise ValueError("expected a 2D array of selected delta rows")
    if xs.ndim != 1 or xs.size == 0:
        raise ValueError("expected a non-empty 1D array of sample points")
    if int(xs[-1]) >= delta_rows.shape[1]:
        raise ValueError("sample point exceeds available delta length")

    boundaries = np.concatenate(([0], xs[:-1] + 1)).astype(np.int64, copy=False)
    relevant = delta_rows[:, : int(xs[-1]) + 1].astype(np.int64, copy=False)
    block_sums = np.add.reduceat(relevant, boundaries, axis=1)
    return np.cumsum(block_sums, axis=1, dtype=np.int64)


def dense_ratio_moving_average(
    delta_rows: np.ndarray,
    roots: np.ndarray,
    xs: np.ndarray,
    xmax: int,
    window: int,
    cp: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    radius = window // 2
    centers = xs[(xs - radius >= 1) & (xs + radius <= xmax)]
    if centers.size == 0:
        raise ValueError("moving average window leaves no plottable sample points")

    relevant = delta_rows[:, : xmax + 1].astype(np.int64, copy=False)
    cum = np.cumsum(relevant, axis=1, dtype=np.int64)
    all_x = np.arange(1, xmax + 1, dtype=np.float64)
    denominator = (
        all_x[None, :]
        * np.sqrt(roots.astype(np.float64)[:, None])
        * cp[:, None]
    )
    ratios = cum[:, 1:] / denominator
    prefix = np.concatenate(
        [np.zeros((delta_rows.shape[0], 1), dtype=np.float64), np.cumsum(ratios, axis=1)],
        axis=1,
    )
    lo = centers - radius
    hi = centers + radius
    averaged = (prefix[:, hi] - prefix[:, lo - 1]) / (hi - lo + 1)[None, :]
    return centers, averaged


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--delta-npz", required=True)
    parser.add_argument("--config", default="config/selected_prime_bundles.json")
    parser.add_argument("--csv-out-dir", default="output/csv/selected_primes")
    parser.add_argument("--tex-out-dir", default="output/tex")
    parser.add_argument("--summary-out", default="output/summaries/selected_prime_bundles.json")
    parser.add_argument("--csv-tex-prefix", default="output/csv/selected_primes")
    return parser.parse_args()


def write_csv(path: Path, fields: list[str], rows: zip) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(fields)
        writer.writerows(rows)


def make_tex(
    family: str,
    primes: list[int],
    bounds: list[int],
    csv_prefix: str,
    step: int,
    ma_window: int,
) -> str:
    raw_field, ma_field, color = FAMILIES[family]
    panels: list[str] = []
    for p, bound in zip(primes, bounds, strict=True):
        half = bound // 2
        stem = f"apm_atlas_p{p:06d}_step{step}"
        panels.append(
            rf"""\nextgroupplot[title={{$p={p}$}},ymin=-{bound},ymax={bound},ytick={{-{bound},-{half},0,{half},{bound}}}]
\addplot[const plot mark right,no markers,thin,draw=gray!55]
  table[x=x,y={raw_field},col sep=comma]{{{csv_prefix}/{stem}.csv}};
\addplot[const plot mark right,no markers,semithick,draw={color}]
  table[x=x,y={ma_field},col sep=comma]{{{csv_prefix}/{stem}_ma{ma_window}.csv}};
\addplot[dashed,black]
  table[x=x,y=zero,col sep=comma]{{{csv_prefix}/{stem}.csv}};
"""
        )
    return rf"""\documentclass[a4paper,11pt]{{article}}
\usepackage[margin=8mm]{{geometry}}
\usepackage{{pgfplots}}
\usepgfplotslibrary{{groupplots}}
\pgfplotsset{{compat=1.18}}
\usepackage[active,tightpage]{{preview}}
\PreviewEnvironment{{tikzpicture}}
\setlength{{\PreviewBorder}}{{4mm}}
\pagestyle{{empty}}

\begin{{document}}
\centering
\begin{{tikzpicture}}
\begin{{groupplot}}[
  group style={{group size=2 by 4,horizontal sep=8mm,vertical sep=13mm}},
  width=0.42\textwidth,
  height=0.18\textheight,
  scale only axis,
  grid=major,
  grid style={{gray!30}},
  scaled x ticks=false,
  scaled y ticks=false,
  tick label style={{font=\small}},
  xtick={{100000,200000,300000,400000,500000,600000,700000,800000,900000,1000000}},
  xticklabels={{0.10,0.20,0.30,0.40,0.50,0.60,0.70,0.80,0.90,1.00}},
  xticklabel style={{font=\small}},
  yticklabel style={{font=\small}},
  title style={{font=\normalsize}},
  xmin=0,
  xmax=1000000,
  after end axis/.code={{
    \node[below=7pt,font=\small] at (rel axis cs:1,0) {{$\cdot 10^6$}};
  }},
]

{''.join(panels)}\end{{groupplot}}
\end{{tikzpicture}}
\end{{document}}
"""


def main() -> None:
    args = parse_args()
    config = json.loads(Path(args.config).read_text(encoding="utf-8"))
    primes = [int(p) for p in config["primes"]]
    xmax = int(config["xmax"])
    step = int(config["step"])
    ma_window = int(config["moving_average_window"])

    with np.load(args.delta_npz) as archive:
        available = archive["primes"].astype(np.int64)
        rows = {int(p): index for index, p in enumerate(available.tolist())}
        missing = [p for p in primes if p not in rows]
        if missing:
            raise ValueError(f"delta cache is missing primes: {missing}")
        indices = np.array([rows[p] for p in primes], dtype=np.int64)
        delta_plus = archive["delta_plus"][indices, : xmax + 1].astype(np.int64)
        delta_minus = archive["delta_minus"][indices, : xmax + 1].astype(np.int64)

    xs = np.arange(step, xmax + 1, step, dtype=np.int64)
    roots = np.array(primes, dtype=np.int64)
    cp = np.array([d0p_count_constant(p) for p in primes], dtype=np.float64)
    denominator = xs.astype(np.float64)[None, :] * np.sqrt(roots)[:, None] * cp[:, None]
    plus = sampled_prefix_sums(delta_plus, xs) / denominator
    minus = sampled_prefix_sums(delta_minus, xs) / denominator
    ma_xs, plus_ma = dense_ratio_moving_average(delta_plus, roots, xs, xmax, ma_window, cp)
    minus_ma_xs, minus_ma = dense_ratio_moving_average(delta_minus, roots, xs, xmax, ma_window, cp)
    if not np.array_equal(ma_xs, minus_ma_xs):
        raise ValueError("plus and minus moving-average grids differ")

    csv_dir = Path(args.csv_out_dir)
    for i, p in enumerate(primes):
        stem = f"apm_atlas_p{p:06d}_step{step}"
        write_csv(
            csv_dir / f"{stem}.csv",
            ["x", "plus_ratio", "minus_ratio", "sum_ratio", "zero"],
            zip(xs, plus[i], minus[i], plus[i] + minus[i], np.zeros_like(xs, dtype=np.float64), strict=True),
        )
        write_csv(
            csv_dir / f"{stem}_ma{ma_window}.csv",
            ["x", "plus_ratio_ma", "minus_ratio_ma", "sum_ratio_ma", "zero"],
            zip(ma_xs, plus_ma[i], minus_ma[i], plus_ma[i] + minus_ma[i], np.zeros_like(ma_xs, dtype=np.float64), strict=True),
        )

    tex_dir = Path(args.tex_out_dir)
    tex_dir.mkdir(parents=True, exist_ok=True)
    for family in FAMILIES:
        bounds = [int(value) for value in config["axes"][family]]
        if len(bounds) != len(primes):
            raise ValueError(f"axis list for {family} does not match prime list")
        (tex_dir / f"apm_bundle_{family}_over_cpx.tex").write_text(
            make_tex(family, primes, bounds, args.csv_tex_prefix.rstrip("/"), step, ma_window),
            encoding="utf-8",
        )

    summary = {
        "delta_npz": args.delta_npz,
        "config": args.config,
        "primes": primes,
        "xmax": xmax,
        "step": step,
        "moving_average_window": ma_window,
        "axes": config["axes"],
    }
    summary_path = Path(args.summary_out)
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
