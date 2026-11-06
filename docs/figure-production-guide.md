# Figure production guide

The repository declares exactly 9 final artifacts in
`config/artifacts.json`. Every pipeline starts from the checksum-verified
`data/apm_shared_tudh_x2000000.npz` table and writes generated intermediates
under `output/`. The audited final set is tracked in `figures/` for immediate
inspection and comparison. `config/figure_data.json` assigns one generated CSV
file and its `csv_file_sha256` value to each figure. When several figures share
a working table, the pipeline writes a separate figure-specific CSV projection.

## Selected-prime bundles: 3 PDFs

```bash
./reproduce.sh selected-prime-bundles
```

`apm_build_delta_cache.py` computes the local-type increments for

```text
29, 101, 397, 797, 1597, 2593, 3989, 5987
```

and `apm_make_selected_prime_bundles.py` forms cumulative sums, normalizes by
\(C_p x\sqrt p\), and writes the CSV and PGFPlots sources. The profile then
calls `latexmk` to produce:

- `apm_bundle_plus_over_cpx.pdf`
- `apm_bundle_minus_over_cpx.pdf`
- `apm_bundle_sum_over_cpx.pdf`

The raw step is 500, the centered moving-average window is 5000, and the
panel-specific vertical bounds are in `config/selected_prime_bundles.json`.

## Split and ramified comparison: 1 PNG

```bash
./reproduce.sh pairwise
```

`plot_apm_pairwise_averaging_figures.py` samples

```text
x in [200000,1000000] with step 5000
p/x in [0.002,0.006]
```

and plots the split and ramified normalized sums against \(p/x\), including
their arithmetic bin-mean curves. It produces
`apm_experiments_split_ramified.png`.

## Main-subtracted terms: 5 PNGs

```bash
./reproduce.sh survivors
```

Main-subtracted terms use `li_x_squared` from `scripts/apm_local_types.py`,
with the normalization
`Li(x^2) = Ei(2 log(x)) - Ei(log(2))`, the integral from 2 to `x^2` of
`dt/log(t)`.

`plot_apm_surviving_terms.py` uses the same pair sample and decomposes the
main-subtracted local-type terms. It produces:

- `apm_experiments_survivor_split_bin_mean_compare.png`
- `apm_experiments_survivor_ramified_zero_bin_mean_compare.png`
- `apm_experiments_survivor_scalar_zero_bin_mean_compare.png`
- `apm_experiments_survivor_ramified_sigma_bin_mean_compare.png`
- `apm_experiments_survivor_scalar_sigma_bin_mean_compare.png`

Despite the `_bin_mean_compare` suffix, each of these five figures shows
a single arithmetic bin-mean curve.

## Output and checks

The generators write final working files to `output/figures`. The verification
and export tools consult `config/artifacts.json`, so undeclared byproducts are
neither accepted nor exported. Each profile also writes its figure-specific
CSV files under `output/figure-data` and compares their rows and file SHA-256
values with `config/figure_data.json`; final PDF or PNG byte identity is not
required for numerical verification.

```bash
./reproduce.sh verify-data
./reproduce.sh export
```
