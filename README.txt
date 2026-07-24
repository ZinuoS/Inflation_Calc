inflation-nowcast — 2 commits not yet on GitHub (origin was at dac2f2c)
Repo: https://github.com/ZinuoS/Inflation_Calc   branch: main
Commits: f66c30c (BEA weights / valid gate / rescope / H9c reversal / OOS report)
         ca5b3d4 (analyst report docs/report_01_0722.md)

THREE WAYS TO GET THESE ONTO GITHUB — pick one:

1) EXACT COMMITS (best; preserves history & authorship = Zinuo A Shi):
   In a terminal, from your local repo, once GitHub auth works:
       git push origin main
   OR apply the bundle to any clone and push:
       git pull /path/to/inflation-nowcast-2commits.bundle main
       git push origin main
   OR apply the patch files:
       git am /path/to/patches/*.patch   (then push)

2) MANUAL WEB UPLOAD (content only, makes a new web commit under your name):
   The files/ folder mirrors the repo layout. On github.com, for each file use
   "Add file > Upload files" (or drag the whole files/ contents) — the paths
   under files/ are exactly where they belong in the repo. 15 files, listed below.

FILES (repo-relative paths under files/):
  docs/checkpoint_log_s3b.md      (modified)
  docs/holdout_2026.md            (modified)
  docs/oos_report_1.md            (new)
  docs/pce_bridge_acceptance.md   (modified)
  docs/report_01_0722.md          (new — the analyst report)
  mapping/mapping.yaml            (modified)
  pipelines/bea_pce_detail/fetch.py        (new)
  pipelines/bea_pce_detail/license_note.md (new)
  pipelines/bea_pce_detail/spec.yaml       (modified)
  src/nowcast/pce_acceptance.py   (modified)
  src/nowcast/pce_bridge.py       (modified)
  tests/test_bea_pce_detail.py    (new)
  tests/test_mapping.py           (modified)
  tests/test_pce_acceptance.py    (modified)
  tests/test_pce_bridge.py        (modified)

No data/, no .env, no API keys included. Verified.
