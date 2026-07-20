# usda_ams — NOT BUILT this session (documented, not fabricated)

Two compounding barriers, both real:

1. **Credential:** the USDA AMS MARS API requires a free `USDA_AMS_API_KEY`
   (mymarketnews.ams.usda.gov). None is present in `.env`.
2. **Complexity:** AMS retail data is the per-commodity weekly "National Retail Report"
   (advertised-price ranges by commodity/region), not a clean national series. A
   deterministic monthly food-at-home index requires matched-commodity mean-of-relatives
   across many report types — real index construction, best done in the 3A methodology
   pass, not shimmed here.

The official target side IS ready: CPI Food at home (CUSR0000SAF11) ALFRED vintages were
added in Task 3, so the moment a clean USDA series exists it can be reconciled on the
first-release side. To enable: add `USDA_AMS_API_KEY` to `.env` and build the
feature-report parser (spec.yaml basket_rule). No other repo component depends on it yet.
