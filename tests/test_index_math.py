"""Property + unit tests for index_math (Session 3A, Task 1).

The four index axioms the prompt names — identity, homogeneity, weight-permutation
invariance, and Jevons <= Carli — are checked via hypothesis so they hold across the
input space, not just hand-picked cases. Tolerances are floating-point (1e-9 relative).
"""

import math

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from nowcast.index_math import carli, chain, fisher, jevons, laspeyres_upper

pos = st.floats(min_value=0.01, max_value=100.0, allow_nan=False, allow_infinity=False)
rels = st.lists(pos, min_size=1, max_size=12)


def _rel_eq(a, b, tol=1e-9):
    return math.isclose(a, b, rel_tol=tol, abs_tol=1e-12)


# ---------- unit anchors ----------

def test_jevons_geomean():
    assert _rel_eq(jevons([1.0, 4.0]), 2.0)


def test_laspeyres_weighted_mean():
    assert _rel_eq(laspeyres_upper([1.10, 1.00], [0.25, 0.75]), 1.025)


def test_chain_levels():
    lv = chain([1.10, 1.00, 0.95], base=100.0)
    assert _rel_eq(lv[-1], 104.5)


def test_fisher_single_good_equals_relative():
    assert _rel_eq(fisher([1.0], [1.5], [10.0], [8.0]), 1.5)


def test_non_positive_rejected():
    for f in (jevons, carli):
        with pytest.raises(ValueError):
            f([1.0, 0.0])


# ---------- IDENTITY: no price change -> index 1 ----------

@given(st.integers(min_value=1, max_value=12), st.lists(pos, min_size=1, max_size=12))
def test_identity(n, weights):
    ones = [1.0] * n
    assert _rel_eq(jevons(ones), 1.0)
    w = (weights * n)[:n]
    assert _rel_eq(laspeyres_upper(ones, w), 1.0)


@given(st.lists(pos, min_size=1, max_size=8), st.lists(pos, min_size=1, max_size=8),
       st.lists(pos, min_size=1, max_size=8))
def test_fisher_identity(p, q0, q1):
    n = min(len(p), len(q0), len(q1))
    p, q0, q1 = p[:n], q0[:n], q1[:n]
    assert _rel_eq(fisher(p, p, q0, q1), 1.0)  # p1 == p0 -> no change


# ---------- HOMOGENEITY: scaling relatives/prices scales the index ----------

@given(rels, st.floats(min_value=0.1, max_value=10.0, allow_nan=False))
def test_homogeneity_jevons_laspeyres(r, lam):
    scaled = [x * lam for x in r]
    assert _rel_eq(jevons(scaled), lam * jevons(r))
    w = [1.0 + i for i in range(len(r))]
    assert _rel_eq(laspeyres_upper(scaled, w), lam * laspeyres_upper(r, w))


@given(st.lists(pos, min_size=1, max_size=6), st.lists(pos, min_size=1, max_size=6),
       st.lists(pos, min_size=1, max_size=6), st.lists(pos, min_size=1, max_size=6),
       st.floats(min_value=0.1, max_value=10.0, allow_nan=False))
def test_homogeneity_fisher(p0, p1, q0, q1, lam):
    n = min(len(p0), len(p1), len(q0), len(q1))
    p0, p1, q0, q1 = p0[:n], p1[:n], q0[:n], q1[:n]
    scaled_p1 = [x * lam for x in p1]
    assert _rel_eq(fisher(p0, scaled_p1, q0, q1), lam * fisher(p0, p1, q0, q1))


# ---------- WEIGHT-PERMUTATION INVARIANCE ----------

@given(rels, st.randoms())
def test_permutation_invariance(r, rng):
    w = [1.0 + i * 0.5 for i in range(len(r))]
    perm = list(range(len(r)))
    rng.shuffle(perm)
    rp = [r[i] for i in perm]
    wp = [w[i] for i in perm]
    assert _rel_eq(jevons(rp), jevons(r))                       # unweighted, order-free
    assert _rel_eq(laspeyres_upper(rp, wp), laspeyres_upper(r, w))  # joint permutation


# ---------- JEVONS <= CARLI (AM-GM) on the same basket ----------

@given(rels)
def test_jevons_le_carli(r):
    assert jevons(r) <= carli(r) + 1e-12
    if len({round(x, 9) for x in r}) == 1:   # identical relatives -> equality
        assert _rel_eq(jevons(r), carli(r))
