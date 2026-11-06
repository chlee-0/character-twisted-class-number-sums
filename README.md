# Character-Twisted Class Number Sums

This repository regenerates the 9 numerical figures used in the accompanying
manuscript, *Character-Twisted Sums of Real Quadratic Class Numbers and a
Selberg-Type Conjecture*, by Chul-hee Lee, Kyu-Hwan Lee, and Jinsung Park.
The reference outputs are tracked in
[`figures/`](figures/), and the repository includes the processed arithmetic
input and code needed to recreate them. Each of the 9 figures also has a
canonical CSV file and a checksum of that file, so the numerical result can be
verified independently of differences between plotting or TeX installations.

## What is being computed?

The manuscript studies real quadratic class-number sums after inserting
prime-indexed character and local-type weights. Numerically, the code forms
the cumulative quantities $A_p^+(x)$ and $A_p^-(x)$, separates scalar,
split, and ramified contributions, and tests how these data behave after the
normalizations used in the paper.

## Numerical input

`data/apm_shared_tudh_x2000000.npz` is a compressed NumPy archive containing
the processed arithmetic table from which every figure is calculated. For each
positive nonsquare order discriminant $d$, let $\eta_d>1$ be a fundamental
unit of the real quadratic order $\mathcal O_d$. We use the fundamental
positive norm-one unit

\[
  \epsilon_d=
  \begin{cases}
    \eta_d, & N(\eta_d)=1,\\
    \eta_d^2, & N(\eta_d)=-1.
  \end{cases}
\]

Equivalently, $\epsilon_d$ is the smallest totally positive unit greater than
$1$ in $\mathcal O_d$. For each row, arrays with the same index give

\[
  (d,t_d,u_d,h^+(d)), \qquad
  t_d^2-d u_d^2=4,
  \qquad \epsilon_d=\frac{t_d+u_d\sqrt d}{2}.
\]

| Array | Meaning | Use in the figure code |
| --- | --- | --- |
| `d` | positive nonsquare quadratic-order discriminant | its Legendre symbol modulo $p$ distinguishes split and ramified rows |
| `t` | trace $t_d=\epsilon_d+\epsilon_d^{-1}$ | rows with $t\le x$ are accumulated, and $t/2\pmod p$ determines the sign term |
| `u` | Pell coefficient $u_d$ | $u\equiv0\pmod p$ identifies the scalar rows |
| `h` | narrow class number $h^+(d)$ | supplies the class-number weight of the row |

Thus, for each prime $p$, the scripts reduce `(d,t,u)` modulo $p$, assign a
scalar, split, or ramified local coefficient, multiply it by `h`, group the
result by `t`, and take prefix sums up to $t\le x$. Those prefix sums are the
quantities plotted as $A_p^+(x)$, $A_p^-(x)$, and the local-type contributions.

The archive has 4,366,961 rows ordered by `(t,d)` and is 32,051,265 bytes.
It contains the complete processed table needed for the manuscript's range
$x\le1,000,000$; its recorded construction cutoff is
`complete_up_to_eps=2000000`. The archive is included in the repository, so no
separate download or upstream database is needed. `data/manifest.json`
records and verifies its checksum, schema, ordering, and provenance. See
[`docs/input-data.md`](docs/input-data.md) for the full row schema and data
provenance.

## Quick start

Docker is the only required dependency. The image uses Python 3.13.5 with the
scientific-package versions pinned in `requirements.txt`. From the repository
root, build the environment and verify the included input:

```bash
./reproduce.sh build
./reproduce.sh verify-input
```

Then generate all nine figures:

```bash
./reproduce.sh all-local
```

## Figures and reproduction commands

| Files | Command | What they show |
| --- | --- | --- |
| `apm_bundle_plus_over_cpx.pdf`<br>`apm_bundle_minus_over_cpx.pdf`<br>`apm_bundle_sum_over_cpx.pdf` | `./reproduce.sh selected-prime-bundles` | $A_p^+(x)$, $A_p^-(x)$, and their sum, each divided by $C_p x\sqrt p$, for selected primes from $29$ to $5987$ |
| `apm_experiments_split_ramified.png` | `./reproduce.sh pairwise` | split–ramified cancellation in the coordinate $p/x$ |
| the five `apm_experiments_survivor_*_bin_mean_compare.png` files | `./reproduce.sh survivors` | scalar, split, and ramified terms remaining after the predicted leading terms are removed |

`./reproduce.sh all-local` generates all nine files listed above.
A more detailed filename-to-generator map is in
[`docs/figure-production-guide.md`](docs/figure-production-guide.md), and the
expected numerical hashes are recorded in `config/figure_data.json`.

## Where are the results?

The audited final PDFs and PNGs are already tracked in `figures/`. Newly
generated files are kept separate from these reference copies so reproduction
runs never overwrite the figures shipped with the repository.

Generated caches, tables, TeX sources, and working figures are stored outside
the checkout under
`$XDG_DATA_HOME/character-twisted-class-number-sums` (normally
`~/.local/share/character-twisted-class-number-sums`). Set `APM_RUNTIME_DIR`
to use another location:

```bash
APM_RUNTIME_DIR=/data/character-sum-results ./reproduce.sh pairwise
```

After running a profile, copy its completed final files into the visible,
Git-ignored `results/` directory with:

```bash
./reproduce.sh export
```

The export report lists any figures that have not yet been generated. Compare
`results/` with the tracked `figures/` reference set. Intermediate files remain
in the runtime directory.

## Verification

Every reproduction profile writes one canonical CSV file for each figure under
the runtime directory's `figure-data/` folder and compares that file's SHA-256
with the `csv_file_sha256` field in `config/figure_data.json`. Row order,
selected columns, UTF-8 encoding, and LF line endings are fixed. The generated
CSV files are not stored in Git. After generating all 9 figures, run the
complete numerical check with:

```bash
./reproduce.sh verify-data
```

Final image hashes are a secondary, environment-sensitive regression check:

```bash
./reproduce.sh verify-reference pairwise
./reproduce.sh verify-reference survivors
```

PDF bytes can vary with the TeX Live release even when their CSV data are
unchanged. PNG bytes may also vary with renderer or font changes. The hashes
in `config/artifacts.json` therefore record the audited build but are not the
primary numerical reproducibility criterion.
