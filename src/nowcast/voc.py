"""H7 — value-of-complexity challenger (Session 4, Task 3). Deterministic, offline.

A high-dim ridge and an RFF (random Fourier feature) expansion over the full admitted feature
set, versus the parsimonious structured model (component_models). Complexity is SWEPT and
REPORTED AS A CURVE — a win requires monotone-ish OOS improvement along the sweep, not one lucky
cell — under purged embargoed walk-forward, intercept always in (Buncic), target
vol-standardized and features expanding-standardized INSIDE each fold (leakage-safe). Every
apparent win is decomposed against AR/energy before any verdict. DEGRADED: no Keepa goods panel.
"""
from __future__ import annotations

import datetime as dt
from pathlib import Path

import numpy as np

from nowcast import component_models as CM
from nowcast import db

DEFAULT_DB = Path(__file__).resolve().parents[2] / "data" / "db" / "nowcast.sqlite"
TARIFF_REGIME_START = "2025-02-01"   # first major 2025 tariff announcements (regime dummy, dated by announcement)


def _add(m, k):
    d = dt.date.fromisoformat(m); mo = d.month - 1 + k
    return dt.date(d.year + mo // 12, mo % 12 + 1, 1).isoformat()


def _monthly_mean_mom(conn, source, key, month):
    obs = {p: float(v) for p, v in conn.execute(
        "SELECT period, value FROM proxy_observations WHERE source=? AND series_key=? "
        "AND _superseded_by_run_id IS NULL", (source, key))}
    def mmean(m):
        xs = [v for d, v in obs.items() if d[:7] == m[:7]]
        return np.mean(xs) if xs else None
    a, b = mmean(month), mmean(_add(month, -1))
    return (a / b - 1.0) if (a and b) else 0.0


def _nsa_mom(conn, sid, m):
    px = {p: float(v) for p, v in conn.execute(
        "SELECT period, value FROM official_current WHERE series_id=? AND period IN (?,?) "
        "AND _superseded_by_run_id IS NULL", (sid, m, _add(m, -1)))}
    pm = _add(m, -1)
    return (px[m] / px[pm] - 1.0) if (m in px and pm in px and px[pm]) else None


def feature_matrix(months, db_path=DEFAULT_DB):
    """Vintage-safe monthly features (all knowable at CPI-day for month M) + target = headline
    NSA MoM(M). Returns X, y, names, kept_months."""
    ft_far = dt.date(2100, 1, 1)
    rows, ys, keep = [], [], []
    with db.connect(db_path) as conn:
        for m in months:
            y = _nsa_mom(conn, "CUUR0000SA0", m)
            if y is None:
                continue
            gas = CM._proxy_month_mom("eia_gasoline", "US", m, "full_month_mean", ft_far, db_path) or 0.0
            man = CM._proxy_month_mom("manheim", "US_full_month", _add(m, -2), "full_month_mean", ft_far, db_path) or 0.0
            nad = _monthly_mean_mom(conn, "nadac", "US_drug_index", m)
            usd = _monthly_mean_mom(conn, "macro_state", "broad_dollar", m)
            r2 = _monthly_mean_mom(conn, "macro_state", "rate_2y", m)
            wti = _monthly_mean_mom(conn, "macro_state", "wti", m)
            tariff = 1.0 if m >= TARIFF_REGIME_START else 0.0
            mo = int(m[5:7])
            s1, c1 = np.sin(2 * np.pi * mo / 12), np.cos(2 * np.pi * mo / 12)
            s2, c2 = np.sin(4 * np.pi * mo / 12), np.cos(4 * np.pi * mo / 12)
            l1 = _nsa_mom(conn, "CUUR0000SA0", _add(m, -1)) or 0.0
            l2 = _nsa_mom(conn, "CUUR0000SA0", _add(m, -2)) or 0.0
            l3 = _nsa_mom(conn, "CUUR0000SA0", _add(m, -3)) or 0.0
            rows.append([gas, man, nad, usd, r2, wti, tariff, s1, c1, s2, c2, l1, l2, l3,
                         gas * tariff, usd * wti, gas * l1])   # a few interactions
            ys.append(y); keep.append(m)
    names = ["gasoline", "manheim_l2", "nadac", "dollar", "rate2y", "wti", "tariff",
             "sin1", "cos1", "sin2", "cos2", "lag1", "lag2", "lag3",
             "gas_x_tariff", "dollar_x_wti", "gas_x_lag1"]
    return np.array(rows), np.array(ys), names, keep


def _ridge(Xtr, ytr, Xte, z):
    p = Xtr.shape[1]
    A = Xtr.T @ Xtr + z * np.eye(p)
    beta = np.linalg.solve(A, Xtr.T @ ytr)
    return Xte @ beta, beta


def _walkforward(X, y, fit_predict, min_train=48, embargo=2):
    """Expanding purged/embargoed walk-forward; features standardized + target vol-scaled INSIDE
    each fold on train only. Returns OOS predictions aligned to y (NaN where not scored)."""
    n = len(y); pred = np.full(n, np.nan)
    for t in range(min_train, n):
        tr = slice(0, t - embargo)
        Xtr, ytr = X[tr], y[tr]
        if len(ytr) < min_train - embargo:
            continue
        mu, sd = Xtr.mean(0), Xtr.std(0) + 1e-9
        vy = ytr.std() + 1e-9
        Xtr_s = np.c_[np.ones(len(ytr)), (Xtr - mu) / sd]         # intercept always in
        Xte_s = np.c_[np.ones(1), (X[t:t + 1] - mu) / sd]
        yhat = fit_predict(Xtr_s, ytr / vy, Xte_s) * vy
        pred[t] = yhat[0]
    return pred


def ridge_sweep(X, y, z_grid, **kw):
    return {z: _walkforward(X, y, lambda a, b, c: _ridge(a, b, c, z)[0], **kw) for z in z_grid}


def _rff(X, P, gamma, seed=0):
    rng = np.random.default_rng(seed)
    W = rng.normal(0, np.sqrt(2 * gamma), size=(X.shape[1], P))
    b = rng.uniform(0, 2 * np.pi, size=P)
    return np.sqrt(2.0 / P) * np.cos(X @ W + b)


def rff_sweep(X, y, P_grid, gamma=0.5, z=1.0, **kw):
    out = {}
    for P in P_grid:
        def fp(Xtr, ytr, Xte, P=P):
            # RFF built on the standardized features passed in (drop the intercept col first)
            Ztr, Zte = _rff(Xtr[:, 1:], P, gamma), _rff(Xte[:, 1:], P, gamma)
            Ztr = np.c_[np.ones(len(ytr)), Ztr]; Zte = np.c_[np.ones(len(Zte)), Zte]
            return _ridge(Ztr, ytr, Zte, z)[0]
        out[P] = _walkforward(X, y, fp, **kw)
    return out


def mae(pred, y):
    m = ~np.isnan(pred)
    return float(np.mean(np.abs(pred[m] - y[m]))) if m.any() else float("nan")
