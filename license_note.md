# License / access note — bea_pce_detail

**Source:** U.S. Bureau of Economic Analysis (BEA), NIPA Underlying Detail Tables 2.4.5U
(U20405, nominal PCE by type of product) and 2.4.4U (U20404, price indexes), via the BEA Data
API (`https://apps.bea.gov/api/data`, dataset `NIUnderlyingDetail`). Checked 2026-07-21.

**Copyright / terms.** Work of the U.S. federal government; not subject to copyright (public
domain). BEA asks that BEA be cited as the source and that the API not be represented as an
official BEA product. Free API key (`BEA_API_KEY`, https://apps.bea.gov/api/signup/), stored in
gitignored `.env`, read from `os.environ`, never committed or logged. We store only derived
official statistics (nominal levels, price indexes) with a provenance record (url with the key
REDACTED, retrieval timestamp, bytes hash) per CLAUDE.md rule 4. No auth wall beyond the free
key; no scraping — the sanctioned API is used.
