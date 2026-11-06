#!/usr/bin/env python3
"""Minimal local-type arithmetic shared by active figure generators."""

from __future__ import annotations

import numpy as np
from scipy.special import expi


def li_x_squared(x):
    """Li(x^2) = integral from 2 to x^2 of dt/log(t)."""
    return expi(2.0 * np.log(x)) - expi(np.log(2.0))


def d0p_count_constant(p: np.ndarray) -> np.ndarray:
    """Return the normalizing constant C_p for an array of primes."""
    p_float = p.astype(np.float64)
    return (35.0 / 32.0) * (
        (p_float**3 + p_float * p_float + 3.0 * p_float - 1.0)
        / (p_float * (p_float * p_float + 1.0))
    )


def sampled_prefix_sums(delta_rows: np.ndarray, xs: np.ndarray) -> np.ndarray:
    """Evaluate row-wise prefix sums only at the requested sample points."""
    if delta_rows.ndim != 2:
        raise ValueError("expected a 2D array of delta rows")
    if xs.ndim != 1 or xs.size == 0:
        raise ValueError("expected a non-empty 1D array of sample points")
    last_x = int(xs[-1])
    if last_x >= delta_rows.shape[1]:
        raise ValueError("sample point exceeds available delta length")

    boundaries = np.concatenate(([0], xs[:-1] + 1)).astype(np.int64, copy=False)
    relevant = delta_rows[:, : last_x + 1].astype(np.int64, copy=False)
    block_sums = np.add.reduceat(relevant, boundaries, axis=1)
    return np.cumsum(block_sums, axis=1, dtype=np.int64)


def odd_primes_between_3_and(limit: int) -> np.ndarray:
    """Return the odd primes p with 3 < p < limit."""
    sieve = np.ones(limit, dtype=np.bool_)
    sieve[:2] = False
    for p in range(2, int(limit**0.5) + 1):
        if sieve[p]:
            sieve[p * p : limit : p] = False
    primes = np.nonzero(sieve)[0]
    return primes[primes > 3].astype(np.int64)


def legendre_table(p: int) -> np.ndarray:
    """Return the Legendre-symbol lookup table modulo p."""
    table = np.empty(p, dtype=np.int8)
    table[0] = 0
    for a in range(1, p):
        value = pow(a, (p - 1) // 2, p)
        table[a] = 1 if value == 1 else -1
    return table


def sampled_type_rows(
    p: int,
    d: np.ndarray,
    t: np.ndarray,
    u: np.ndarray,
    h: np.ndarray,
    xs: np.ndarray,
    xmax: int,
) -> dict[str, np.ndarray]:
    """Compute sampled scalar, split, ramified, and total contributions."""
    d_mod = np.mod(d, p).astype(np.int64)
    t_mod = np.mod(t, p).astype(np.int64)
    u_mod = np.mod(u, p).astype(np.int64)
    legendre = legendre_table(p)[d_mod]

    scalar = u_mod == 0
    split = (~scalar) & (legendre == 1)
    ramified = (~scalar) & (legendre == 0)

    inv2 = pow(2, -1, p)
    t_half_mod = (t_mod * inv2) % p
    sign = np.where(t_half_mod == 1, 1, -1).astype(np.int64)

    out: dict[str, np.ndarray] = {}
    weights = np.zeros_like(h, dtype=np.int64)
    if np.any(scalar):
        weights[scalar] = h[scalar] * (
            ((p + 1) * (p - 3)) // 2
            + sign[scalar] * (((p + 1) * (p - 1)) // 2)
        )
    delta = np.bincount(t, weights=weights, minlength=xmax + 1).astype(np.int64)
    out["scalar"] = sampled_prefix_sums(delta[None, :], xs)[0]

    weights.fill(0)
    if np.any(split):
        weights[split] = h[split] * (-2)
    delta = np.bincount(t, weights=weights, minlength=xmax + 1).astype(np.int64)
    out["split"] = sampled_prefix_sums(delta[None, :], xs)[0]

    weights.fill(0)
    if np.any(ramified):
        weights[ramified] = h[ramified] * (
            ((p - 3) // 2) + sign[ramified] * ((p - 1) // 2)
        )
    delta = np.bincount(t, weights=weights, minlength=xmax + 1).astype(np.int64)
    out["ramified"] = sampled_prefix_sums(delta[None, :], xs)[0]
    out["total"] = out["scalar"] + out["split"] + out["ramified"]
    return out


def _prefix_for(
    t: np.ndarray,
    h: np.ndarray,
    mask: np.ndarray,
    coeff: int,
    xs: np.ndarray,
    xmax: int,
) -> np.ndarray:
    if not np.any(mask) or coeff == 0:
        return np.zeros(len(xs), dtype=np.int64)
    weights = np.zeros_like(h, dtype=np.int64)
    weights[mask] = h[mask] * int(coeff)
    delta = np.bincount(t, weights=weights, minlength=xmax + 1).astype(np.int64)
    return sampled_prefix_sums(delta[None, :], xs)[0]


def sampled_secondary_rows(
    p: int,
    d: np.ndarray,
    t: np.ndarray,
    u: np.ndarray,
    h: np.ndarray,
    xs: np.ndarray,
    xmax: int,
) -> dict[str, np.ndarray]:
    """Compute the sampled secondary decomposition used by survivor plots."""
    d_mod = np.mod(d, p).astype(np.int64)
    t_mod = np.mod(t, p).astype(np.int64)
    u_mod = np.mod(u, p).astype(np.int64)
    legendre = legendre_table(p)[d_mod]

    scalar = u_mod == 0
    split = (~scalar) & (legendre == 1)
    ramified = (~scalar) & (legendre == 0)

    inv2 = pow(2, -1, p)
    positive = ((t_mod * inv2) % p) == 1
    negative = ~positive

    ram_plus_mass = _prefix_for(t, h, ramified & positive, 1, xs, xmax)
    ram_minus_mass = _prefix_for(t, h, ramified & negative, 1, xs, xmax)
    scalar_plus_mass = _prefix_for(t, h, scalar & positive, 1, xs, xmax)
    scalar_minus_mass = _prefix_for(t, h, scalar & negative, 1, xs, xmax)
    split_mass = _prefix_for(t, h, split, 1, xs, xmax)

    ram_mass = ram_plus_mass + ram_minus_mass
    scalar_mass = scalar_plus_mass + scalar_minus_mass

    out: dict[str, np.ndarray] = {}
    out["split"] = -2 * split_mass
    out["ram0"] = ((p - 3) // 2) * ram_mass
    out["ramsigma"] = ((p - 1) // 2) * (ram_plus_mass - ram_minus_mass)
    out["scalar0"] = (((p + 1) * (p - 3)) // 2) * scalar_mass
    out["scalarsigma"] = (
        ((p + 1) * (p - 1)) // 2
    ) * (scalar_plus_mass - scalar_minus_mass)
    out["unsigned"] = out["split"] + out["ram0"] + out["scalar0"]
    out["sigma"] = out["ramsigma"] + out["scalarsigma"]
    out["total"] = out["unsigned"] + out["sigma"]
    return out
