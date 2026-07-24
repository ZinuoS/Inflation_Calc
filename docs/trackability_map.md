# Trackability map — what can and cannot be nowcast, and why

Derived from `mapping/sampling.yaml` (BLS-cited sampling design) + computed seasonal reliability.
**`seasonal_reliability_bp`** = mean across calendar months of the std-dev of that month's NSA MoM
across years (2014+). LOW ⇒ the seasonal-mean fallback is trustworthy; HIGH ⇒ it is structurally
weak and only a proxy can help.

## Classes (share of CPI weight)

| class | n | weight | error-floor rationale |
|---|--:|--:|---|
| **structurally-slow** | 22 | **51.5%** | Design or administrative smoothing (housing 6-panel/6-month ratios; low-dispersion services). The seasonal/AR fallback is *appropriate* here — floor is small and comes from the smoothing rate itself, not from missing data. **A proxy adds little to next-print; it adds trajectory.** |
| **untrackable-idiosyncratic** | 150 | **32.9%** | High same-month dispersion, no candidate high-frequency source. Floor ≈ the dispersion itself; this is the **fat-tail generator** (June-2026 style). Honest answer: not nowcastable at CPI-day with public data. |
| **proxy-plausible** | 7 | **9.8%** | A named candidate source exists (Part B). Floor should fall toward the proxy's own tracking error if acquisition succeeds. |
| **proxy-admitted** | 2 | **5.8%** | Gasoline (EIA, R² 0.978) and used cars (Manheim lag-2). Floor already realized — this is where today's edge lives. |

### structurally-slow (top by weight)
| code | name | wt | seas.rel (bp) |
|---|---|--:|--:|
| SEHC01 | Owners' equivalent rent of primary res | 25.23 | 13.4 |
| SEHA | Rent of primary residence | 7.84 | 14.3 |
| SETA01 | New vehicles | 3.84 | 38.5 |
| SEFV02 | Limited service meals and snacks | 2.68 | 20.0 |
| SEFV01 | Full service meals and snacks | 2.39 | 20.4 |
| SEMC01 | Physicians' services | 1.68 | 33.8 |
| SEEB01 | College tuition and fees | 1.35 | 15.4 |
| SEHG01 | Water and sewerage maintenance | 0.78 | 18.8 |

### proxy-plausible — the Part-B target list
| code | name | wt | seas.rel (bp) |
|---|---|--:|--:|
| SETE | Motor vehicle insurance | 2.75 | 123.8 |
| SEHF01 | Electricity | 2.49 | 77.2 |
| SEED03 | Wireless telephone services | 1.34 | 74.8 |
| SEHB02 | Other lodging away from home including | 1.07 | 224.2 |
| SEMF01 | Prescription drugs | 0.97 | 58.1 |
| SETG01 | Airline fares | 0.88 | 317.6 |
| SEHE01 | Fuel oil | 0.08 | 555.2 |

### untrackable-idiosyncratic (top by weight)
| code | name | wt | seas.rel (bp) |
|---|---|--:|--:|
| SEMD01 | Hospital services | 2.17 | 44.6 |
| SEEE03 | Internet services and electronic infor | 0.92 | 56.4 |
| SEMC02 | Dental services | 0.90 | 40.9 |
| SEME | Health insurance | 0.89 | 145.4 |
| SEHF02 | Utility (piped) gas service | 0.77 | 228.6 |
| SERF01 | Club membership for shopping clubs, fr | 0.77 | 76.6 |
| SERF02 | Admissions | 0.70 | 120.0 |
| SERB01 | Pets and pet products | 0.61 | 52.9 |

## Acquisition outcomes (Part B) — amendments to the classes above

- **SEHB02 lodging (wt 1.07): RECLASSIFIED `proxy-plausible` → `untrackable-idiosyncratic`** (S1,
  2026-07-23). No admissible source; see `checkpoint_log_s7.md` §S1. Revised class weights:
  structurally-slow 51.5% / untrackable 34.0% / proxy-plausible 8.7% / proxy-admitted 5.8%.
- **SEED03 wireless (wt 1.34): RECLASSIFIED `proxy-plausible` → `untrackable-idiosyncratic`** (S2,
  2026-07-23). The pre-registered hedonic caveat was **confirmed**: CPI wireless and PPI wireless
  share ~zero monthly co-movement (corr **+0.08**, n=150) despite near-identical 12-year drift, and
  in June-2026 CPI moved **−331 bp while PPI moved +1 bp**. The monthly signal is internal to BLS
  measurement, not a market event any external tracker can see. Revised class weights:
  structurally-slow 51.5% / untrackable **35.4%** / proxy-plausible **7.3%** / proxy-admitted 5.8%.

## The June-2026 movers — does sampling design explain the reversal?

Actual move measured in units of that stratum's own same-month dispersion (σ = seasonal_reliability).

| stratum | actual | σ | move/σ | design contribution | verdict |
|---|--:|--:|--:|---|---|
| **SETE** insurance | −214 | 123.8 | −1.7σ | **bimonthly outside NY/LA/Chicago** → a filed-rate change is collected over two months, so a print can be a *catch-up* rather than a one-month event | **partly design, partly genuine** |
| **SEED03** wireless | −331 | 74.8 | **−4.4σ** | none — priced like other services; but BLS **quality-adjusts** (more data at same price = price decline) | **genuine idiosyncratic repricing**; a posted-price tracker would likely have MISSED it (hedonic, not sticker) |
| **SEHB02** lodging | −296 | 224.2 | −1.3σ | none specific | **within its own normal dispersion** — the seasonal fallback was never reliable here; a weekly proxy should help materially |
| **SEHF01** electricity | +149 (fcst +303) | 77.2 | ~2σ over-predict | monthly in all areas (energy) | genuine; official EIA-861M exists but at ~2-month lag ⇒ **trajectory, not next-print** |
| **SEHC01** OER | +23 (fcst +34) | 13.4 | ~0.8σ | **6-panel / 6-month rent ratios** — smoothing is the design | small per-unit error × 27% weight; **H11 target** |
| **SEHA** rent | +13 (fcst +34) | 14.3 | ~1.5σ | same panel design | **H11 target** |

**Reading:** only *one* of the three big reversals (insurance) is partly a sampling artifact; wireless
was a genuine 4.4σ repricing that our planned proxy would probably not catch, and lodging was
ordinary variance for a stratum whose seasonal fallback is structurally weak. This tempers the
Part-B expectation before any source is built: **acquisition buys tail reduction on ~10% of weight,
not a transformation of the mean** — and the wireless case argues for pre-registering the hedonic
caveat rather than assuming a tracker solves it.
