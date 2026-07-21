# Session 3A checkpoint log — index math + seasonal adjustment

## TASK 0 — carry-questions · CHECKPOINT 0

### 0a — C1–C3 conditional builds
`USDA_AMS_API_KEY`, `BEA_API_KEY`, `KEEPA_API_KEY` all still **ABSENT** from `.env`.
usda_ams / bea_pce_detail / keepa remain **SKIPPED** (folders + specs + STATUS notes
stand). No builds this session; their placeholder indices stay out of Task 4 scope
until a key lands.

### 0b — Manheim restatement verification → UNREVISED, historical ingested
Compared the point-in-time archive (11 dated files, Jan–Nov 2025, each file's newest row =
that month's first release) against the same months in the latest full download:
**all 11 months matched EXACTLY (diff 0.0000).** Methodology confirms the only historical
"recalculation" was the one-time 1995→1997 rebasing; "revised" = full-month superseding the
preliminary mid-month, not restatement of published full-month values.

→ MUVVI full-month is **unrevised**. Ingested the full **1997–2025 (347 months)** history
as `vintage_status: unrevised`, superseding the 11 point-in-time rows (values identical).
Evidence + residual caveat (2025-only exact-match window; annual SA revision of pre-2025
history not positively excluded) cited in `pipelines/manheim/license_note.md`.

**H1 no longer overlap-starved.** Reconciliation Manheim vs SETA02 (used cars),
first-release: contemporaneous **n=177, R²=0.015, unstable, NOT optimism-flagged**. That
low contemporaneous R² is the honest LEAD structure, not a defect — a lead-correlation
sanity check confirms it (and validates the pipeline is not buggy):

| lead k (months) | n | corr | R² |
|---|--:|--:|--:|
| 0 (contemporaneous) | 177 | +0.122 | 0.015 |
| 1 | 177 | +0.394 | 0.155 |
| **2** | 177 | **+0.592** | **0.350** |
| 3 | 177 | +0.435 | 0.190 |

Manheim wholesale leads CPI used-car retail by ~2 months (peak R²=0.35) — real H1 signal,
to be exploited as a LEAD in Session 4, not admitted as a contemporaneous next-print feature
(same shape as ZORI/shelter H2, but a stronger, cleaner lead).

### Task-3 preflight (heads-up, not blocking now)
`x13as` binary is **NOT on PATH**. Task 3 (X-13ARIMA-SEATS) will STOP for its install per
the prompt; flagging now so it can be installed during review. macOS install step will be
given at Task 3.

56 tests green.

## TASK 2 — bls_cpi_weights + weights.py · DONE
Built the `bls_cpi_weights` naru pipeline (didn't exist; Session 1 only had the manual
pull). 6 RI vintages (2020–2025, 1616 rows), license note, golden parse test.
`weights.py`: as-of-date serving, vintaged (rent 7.862 in 2020 vs 7.84 in 2025), refuses
out-of-coverage (2019/2026 → OutOfWeightCoverage).

## TASK 3 — seasonal.py (X-13) · CHECKPOINT 2 (HALT: all strata > 3bp)

### x13as install (reproducible — conda-forge ships only a Linux binary, so built from source)
```
# 1. micromamba standalone (osx-arm64)
mkdir -p ~/.local/bin && curl -Ls https://micro.mamba.pm/api/micromamba/osx-arm64/latest \
  | tar -xj -C /tmp/mm bin/micromamba && mv /tmp/mm/bin/micromamba ~/.local/bin/micromamba
# 2. NOTE: conda-forge r-x13binary is noarch and ships a LINUX x86-64 binary -> unusable on
#    macOS arm64. So install a Fortran toolchain and build the native binary from source:
export MAMBA_ROOT_PREFIX=~/micromamba
~/.local/bin/micromamba create -y -p ~/micromamba-envs/x13 -c conda-forge gfortran make
# 3. Census TEXT (ascii) source — statsmodels needs the text variant (.out/.err/.d11),
#    NOT x13ashtml (html only). Build b62 with -fallow-argument-mismatch for gfortran 15:
curl -sL -o /tmp/x13text/src.tar.gz \
  https://www2.census.gov/software/x-13arima-seats/x13as/unix-linux/program-archives/x13as_asciisrc-v1-1-b62.tar.gz
# tar xzf; cd x13as_asciisrc-v1-1-b62
PATH=~/micromamba-envs/x13/bin:$PATH make -f makefile.gf FC=gfortran FFLAGS="-O2 -fallow-argument-mismatch -std=legacy"
gfortran -o x13as *.o     # makefile's $(LINKER) is empty -> link manually
mkdir -p ~/micromamba-envs/x13/x13bin && cp x13as ~/micromamba-envs/x13/x13bin/x13as
```
**X13PATH = `/Users/zinuoshi/micromamba-envs/x13/x13bin`** (native Mach-O arm64 text x13as).
Set explicitly in every run command. statsmodels smoke test passes.

### SA replication floor — HALT (all four strata > 3bp/MoM)
Our default X-13 SA (CUUR NSA) vs BLS published SA (CUSR), MoM MAE bp, trailing 8y:

| stratum | code | n | MAE bp | corr |
|---|---|--:|--:|--:|
| Apparel | SAA | 86 | 16.6 | 0.966 |
| Gasoline | SETB01 | 95 | 72.9 | 0.986 |
| Used cars | SETA02 | 95 | 83.1 | 0.868 |
| Airfares | SETG01 | 86 | 95.4 | 0.959 |

VERIFIED GENUINE (not a scale bug): our SA tracks BLS in level/direction/volatility with
0.87–0.99 corr; residual scales with each stratum's MoM volatility. All exceed 3bp → HALT
per the standing instruction. docs/sa_floor.md written (711bp/3.5bp vintage exhibits +
this floor table + per-stratum implication). Decision needed: tune per-series X-13 specs
to match BLS, or carry these strata as lead/monitor rather than contemporaneous SA-MoM.
Gasoline note for Task 4: recoverable headroom on its NSA/SA reconciliation gap is bounded
by this 72.9bp SA-method residual.
