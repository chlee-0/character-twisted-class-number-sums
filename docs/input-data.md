# Canonical input data

## Role in the reproduction pipeline

All public figure pipelines start from the tracked file
`data/apm_shared_tudh_x2000000.npz`. The repository does not download data at
run time. `./reproduce.sh verify-input` checks its size, SHA-256, array names,
dtypes, shapes, ordering, row count, and completeness metadata before a
reproduction profile starts.

This NPZ is the published processed arithmetic input, not a disposable cache.
It replaces the much larger upstream SQLite database for the purpose of figure
reproduction. Every active generator reads it directly or first converts it
into a prime-specific delta cache.

## Row schema

The table has 4,366,961 rows sorted lexicographically by `(t,d)`. A row is

\[
  (d,t_d,u_d,h^+(d)),
\]

where:

- `d` is a positive nonsquare quadratic-order discriminant with
  \(d\equiv0,1\pmod 4\);
- \(\epsilon_d\) is the fundamental positive norm-one unit of the order of
  discriminant \(d\): if \(\eta_d>1\) is a fundamental unit, then
  \(\epsilon_d=\eta_d\) when \(N(\eta_d)=1\), and
  \(\epsilon_d=\eta_d^2\) when \(N(\eta_d)=-1\); equivalently, it is the
  smallest totally positive unit greater than $1$ in that order;
- `t` and `u` are the integers in the canonical norm-one unit
  \(\epsilon_d=(t_d+u_d\sqrt d)/2>1\), so
  \(t_d^2-du_d^2=4\);
- `h` is the narrow class number \(h^+(d)\), equivalently the number of
  proper classes of primitive indefinite binary quadratic forms of
  discriminant \(d\).

The metadata value `complete_up_to_eps=2000000` means the table contains every
canonical row with \(\epsilon_d\le 2,000,000\). At the integer sample cutoffs
used in these figures, \(\epsilon_d\le x\) is equivalent to \(t_d\le x\).

## How the four arrays produce the plotted sums

For each selected prime $p$, the active local-type calculation uses the row
as follows:

1. `u mod p` detects scalar rows.
2. For non-scalar rows, the Legendre symbol of `d mod p` distinguishes split
   and ramified rows.
3. `t/2 mod p` supplies the sign appearing in the minus contribution.
4. The resulting local coefficient is multiplied by the narrow class number
   `h`.
5. Weighted rows are collected at their trace `t` and cumulatively summed for
   `t <= x`.

Consequently the archive contains exactly the row-level information needed to
form $A_p^+(x)$, $A_p^-(x)$, and their scalar, split, and ramified
decompositions. It does not contain those curves in precomputed form.

## Provenance boundary

The table was produced by trace-first enumeration. Candidate factorizations
\(t^2-4=du^2\) were checked against canonical quadratic-order rows computed
with the PARI backend, and the resulting slim SQLite table was exported to
NPZ. The source SQLite checksum is retained in `data/manifest.json` but the
198 MB database is not needed by any figure generator.

This repository therefore guarantees artifact-level reproducibility from the
published processed table. Re-enumerating the table from first principles is
a separate upstream computation and is intentionally outside the minimal
public dependency set.
