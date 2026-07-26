"""Guards for H19 combination. It is a REPORTING product: never a claim about "ours" alone."""
import numpy as np

from nowcast import combo as C


def test_weight_is_never_fitted_to_the_scoring_months():
    """Estimation is pre-2023; scoring is consensus months (2023+). The sets must be disjoint."""
    rows = C._rows()
    for inst in C.INSTRUMENTS:
        est = {s["month"] for s in C.estimation_sample(inst, rows)}
        sc = {s["month"] for s in C.scoring_sample(inst, rows)}
        assert not (est & sc), f"{inst}: weight estimated on months it is scored on: {est & sc}"


def test_unstable_folds_force_the_precommitted_weight():
    """The whole point of the stability check: an unstable estimate must not be used."""
    for inst in C.INSTRUMENTS:
        d = C.choose_weight(inst)
        if d["path"] == "precommitted":
            assert d["w"] == C.W_PRECOMMITTED
            assert "unstable" in d["reason"] or "too small" in d["reason"]
        else:
            assert d["spread"] <= C.UNSTABLE_SPREAD


def test_combo_is_a_convex_blend():
    rows = C._rows()
    for inst in C.INSTRUMENTS:
        d = C.choose_weight(inst, rows=rows)
        assert 0.0 <= d["w"] <= 1.0
        sc = C.scoring_sample(inst, rows)
        if not sc:
            continue
        w = d["w"]
        for s in sc:                                    # blend must lie between its inputs
            b = w * s["ours"] + (1 - w) * s["other"]
            assert min(s["ours"], s["other"]) - 1e-9 <= b <= max(s["ours"], s["other"]) + 1e-9


def test_combo_cannot_beat_both_inputs_by_construction_check():
    """Sanity: reported combo MAE must equal an independent recomputation (no silent reweighting)."""
    rows = C._rows()
    for r in C.report():
        if not r["n_score"]:
            continue
        sc = C.scoring_sample(r["instrument"], rows)
        w = r["w"]
        mae = np.mean([abs(w * s["ours"] + (1 - w) * s["other"] - s["actual"]) for s in sc])
        assert abs(mae - r["mae_combo_pp"]) < 1e-4
