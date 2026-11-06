#!/usr/bin/env python3
"""Run one public figure-reproduction profile in the Python environment."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import subprocess
import sys


REPO_ROOT = Path(__file__).resolve().parents[1]
INPUT = REPO_ROOT / "data" / "apm_shared_tudh_x2000000.npz"
PROFILES = (
    "verify-input",
    "selected-prime-bundles",
    "pairwise",
    "survivors",
    "all-local",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("profile", choices=PROFILES, nargs="?", default="all-local")
    return parser.parse_args()


def run(*arguments: object, env: dict[str, str] | None = None) -> None:
    command = [str(argument) for argument in arguments]
    print("+ " + " ".join(command), flush=True)
    subprocess.run(command, cwd=REPO_ROOT, env=env, check=True)


def run_python(script: str, *arguments: object) -> None:
    run(sys.executable, REPO_ROOT / "scripts" / script, *arguments)


def verify_input() -> None:
    run_python("verify_inputs.py")


def build_and_verify_figure_data(group: str) -> None:
    run_python("build_figure_data.py", "--groups", group)
    run_python("verify_figure_data.py", "--groups", group)


def build_tex() -> None:
    figures_dir = REPO_ROOT / "output" / "figures"
    figures_dir.mkdir(parents=True, exist_ok=True)
    tex_files = sorted((REPO_ROOT / "output" / "tex").glob("*.tex"))
    if not tex_files:
        raise RuntimeError("no generated TeX files found under output/tex")

    environment = os.environ.copy()
    environment.setdefault("SOURCE_DATE_EPOCH", "946684800")
    for tex_path in tex_files:
        run(
            "latexmk",
            "-silent",
            "-pdf",
            "-interaction=nonstopmode",
            "-halt-on-error",
            f"-outdir={figures_dir}",
            tex_path,
            env=environment,
        )


def selected_prime_bundles(processes: int) -> None:
    for directory in ("cache", "csv", "tex", "summaries"):
        (REPO_ROOT / "output" / directory).mkdir(parents=True, exist_ok=True)
    delta_path = REPO_ROOT / "output" / "cache" / "apm_delta_selected_primes_xmax1000000.npz"
    run_python(
        "apm_build_delta_cache.py",
        "--shared-npz",
        INPUT,
        "--out-npz",
        delta_path,
        "--out-json",
        REPO_ROOT / "output" / "summaries" / "apm_delta_selected_primes_xmax1000000.json",
        "--primes",
        "29,101,397,797,1597,2593,3989,5987",
        "--xmax",
        1_000_000,
        "--processes",
        processes,
    )
    run_python("apm_make_selected_prime_bundles.py", "--delta-npz", delta_path)
    build_and_verify_figure_data("selected_prime_bundles")
    build_tex()
    run_python("verify_artifacts.py", "--groups", "selected_prime_bundles")


def pairwise() -> None:
    for directory in ("figures", "cache", "summaries"):
        (REPO_ROOT / "output" / directory).mkdir(parents=True, exist_ok=True)
    run_python("plot_apm_pairwise_averaging_figures.py")
    build_and_verify_figure_data("pairwise")
    run_python("verify_artifacts.py", "--groups", "pairwise")


def survivors() -> None:
    for directory in ("figures", "summaries"):
        (REPO_ROOT / "output" / directory).mkdir(parents=True, exist_ok=True)
    run_python("plot_apm_surviving_terms.py")
    build_and_verify_figure_data("survivors")
    run_python("verify_artifacts.py", "--groups", "survivors")


def main() -> None:
    args = parse_args()
    processes = int(os.environ.get("APM_PROCESSES", "4"))
    if processes <= 0:
        raise SystemExit("APM_PROCESSES must be positive")

    verify_input()
    if args.profile == "verify-input":
        return
    if args.profile in ("selected-prime-bundles", "all-local"):
        selected_prime_bundles(processes)
    if args.profile in ("pairwise", "all-local"):
        pairwise()
    if args.profile in ("survivors", "all-local"):
        survivors()


if __name__ == "__main__":
    main()
