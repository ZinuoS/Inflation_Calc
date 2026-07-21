# License / access note — equity_path (S&P 500)

**Source:** S&P 500 index level via FRED series `SP500` (FRED redistributes S&P Dow Jones
Indices LLC data). Retrieved through the FRED API with `FRED_API_KEY`. Checked 2026-07-20.

**Terms.** S&P 500 index values are © S&P Dow Jones Indices LLC; FRED provides a rolling
~10-year window under license. We do NOT redistribute raw index values: `data/` is gitignored
(never committed), and only a DERIVED monthly price relative (MoM change) enters the bridge as
the equity-market path for AUM-based fee components. No raw levels appear in the repo or in any
published artifact. If broader redistribution is ever needed, substitute a freely-licensed
broad-market index (e.g. Wilshire 5000) — economically equivalent for this fee-path purpose
(monthly correlation ~0.99).
