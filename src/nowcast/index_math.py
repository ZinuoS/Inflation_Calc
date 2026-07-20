"""Official index mathematics as pure functions — no I/O, no state (Session 3A, Task 1).

Methodology replication. Citations are to the BLS Handbook of Methods, Chapter 17
"The Consumer Price Index" (the CPI chapter), and to BEA's NIPA methodology for the
Fisher index used on the PCE side. These are the exact formulas BLS/BEA apply; the
aggregation stack that reconstructs CPI (nb03) composes them.

Elementary (lower-level) aggregation: BLS uses the geometric-mean (Jevons) formula for
most item strata; the arithmetic-mean (Carli) form is documented here only to exhibit
its upward bias (Jevons <= Carli), which is why BLS abandoned it for most strata in 1999.
Upper-level aggregation: a modified-Laspeyres cost-weighted average of lower-level
relatives, chained period to period. PCE uses a chain-type Fisher index (BEA).
"""

from __future__ import annotations

import math
from collections.abc import Sequence


def _check_positive(values: Sequence[float], name: str) -> None:
    if len(values) == 0:
        raise ValueError(f"{name}: empty sequence")
    if any(v <= 0 for v in values):
        raise ValueError(f"{name}: all values must be strictly positive (got a non-positive)")


def jevons(relatives: Sequence[float]) -> float:
    """Lower-level Jevons elementary index: the geometric mean of price relatives.

    BLS Handbook of Methods, CPI ch. 17 (elementary/basic index calculation): for most
    item strata the elementary aggregate is the geometric mean of the price relatives of
    the matched quotes, equivalent to the ratio of geometric mean prices. Returns the
    stratum price relative for the period.

    >>> round(jevons([1.0, 4.0]), 6)   # geomean(1,4) = 2
    2.0
    """
    _check_positive(relatives, "jevons")
    return math.exp(sum(math.log(r) for r in relatives) / len(relatives))


def carli(relatives: Sequence[float]) -> float:
    """Carli elementary index: the arithmetic mean of price relatives.

    BLS Handbook, CPI ch. 17: NOT used for production aggregation — the Carli mean is
    upward-biased relative to Jevons (Jevons <= Carli by AM-GM), the reason BLS switched
    most strata to the geometric mean in 1999. Provided only to make that bias testable.
    """
    _check_positive(relatives, "carli")
    return sum(relatives) / len(relatives)


def laspeyres_upper(relatives: Sequence[float], weights: Sequence[float]) -> float:
    """Upper-level modified-Laspeyres aggregate relative: cost-weighted arithmetic mean
    of lower-level relatives.

    BLS Handbook of Methods, CPI ch. 17 (aggregation): an aggregate index advances by the
    cost-weighted average of its components' relatives, the weights being relative
    importances (cost weights). Returns sum(w_i * rel_i) / sum(w_i) — the aggregate's
    period relative, to be chained by `chain`.

    >>> round(laspeyres_upper([1.10, 1.00], [0.25, 0.75]), 6)
    1.025
    """
    if len(relatives) != len(weights):
        raise ValueError("laspeyres_upper: relatives and weights differ in length")
    _check_positive(relatives, "laspeyres_upper relatives")
    total_w = sum(weights)
    if total_w <= 0:
        raise ValueError("laspeyres_upper: weights sum to a non-positive value")
    return sum(w * r for w, r in zip(weights, relatives)) / total_w


def chain(relatives: Sequence[float], base: float = 100.0) -> list[float]:
    """Chain period-to-period relatives into an index level series.

    BLS Handbook, CPI ch. 17: the published index is chained — each period's level is the
    prior level times the current period relative. Returns [base, base*r1, base*r1*r2, ...]
    (length len(relatives)+1).

    >>> chain([1.10, 1.00, 0.95], base=100.0)
    [100.0, 110.00000000000001, 110.00000000000001, 104.5]
    """
    _check_positive(relatives, "chain")
    levels = [base]
    for r in relatives:
        levels.append(levels[-1] * r)
    return levels


def fisher(
    p0: Sequence[float], p1: Sequence[float], q0: Sequence[float], q1: Sequence[float]
) -> float:
    """Chain-type Fisher price index: geometric mean of the Laspeyres and Paasche price
    indexes (the PCE side).

    BEA NIPA methodology ("Concepts and Methods of the U.S. NIPAs"): PCE price indexes are
    chain-type Fisher. Laspeyres_P = sum(p1*q0)/sum(p0*q0) (base-period quantity weights);
    Paasche_P = sum(p1*q1)/sum(p0*q1) (current-period quantity weights); Fisher =
    sqrt(Laspeyres_P * Paasche_P).

    >>> round(fisher([1.0], [1.5], [10.0], [8.0]), 6)   # single good: both = 1.5
    1.5
    """
    n = len(p0)
    if not (len(p1) == len(q0) == len(q1) == n):
        raise ValueError("fisher: p0, p1, q0, q1 must have equal length")
    _check_positive(p0, "fisher p0")
    _check_positive(p1, "fisher p1")
    _check_positive(q0, "fisher q0")
    _check_positive(q1, "fisher q1")
    lasp = sum(pi1 * qi0 for pi1, qi0 in zip(p1, q0)) / sum(pi0 * qi0 for pi0, qi0 in zip(p0, q0))
    paasche = sum(pi1 * qi1 for pi1, qi1 in zip(p1, q1)) / sum(pi0 * qi1 for pi0, qi1 in zip(p0, q1))
    return math.sqrt(lasp * paasche)
