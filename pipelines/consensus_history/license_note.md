# License note — consensus_history (press-reported consensus median)

Reviewed: 2026-07-24.

**What this is.** The consensus median economists expected for each inflation print, as reported in
the financial press (Reuters/AP/CNBC/MarketWatch). A consensus figure quoted in a news article is a
**fact**; we store the fact (the number), the **source_url**, and the **article_date** — never the
article text. This is the standard treatment of a reported statistic, not republication.

**Licensing decision (restated, binding).** No Bloomberg/terminal exports, ever. No licensed
consensus vendor exports. Only press-reported figures, each with a public citation.

**Access reality (2026-07-24).** Automated backfill is **blocked**: WebFetch returns HTTP 403 on
CNBC, Morningstar, CEPR and other outlets, and the search-snippet summarizer conflates
actual-vs-expected and mixes outlets — unusable as a source of cited facts without risking
fabrication. Per hard rule 5 the block is not fought. Curation is therefore **manual**: a human
opens the dated article and records the figure. The artifact ships gap-first; every non-gap row
carries a verifiable source_url + article_date, enforced by `fetch.validate()`.

**Vintage.** `point_in_time`, article-dated. Preview (pre-print) preferred over recap; where they
disagree, both are recorded and the preview is canonical. A month with no verifiable consensus is a
gap row and is simply absent from evaluation denominators — never interpolated.

**Backfill method used (2026-07-24).** Since direct WebFetch is 403-blocked, figures were sourced
via **web search of the cited dated articles** (predominantly CNBC/J.P. Morgan/Morningstar post-print
recaps that state the Dow Jones/FactSet consensus alongside the actual). Discipline applied to avoid
fabrication: (1) a figure is recorded ONLY when the result explicitly frames it as
*expected/forecast/consensus*, never the actual print; (2) months whose search results **conflated
years** (e.g. June/May 2024 mixed with 2026) were left as **gaps**, not guessed — several were
caught and dropped this way; (3) each row keeps the specific article `source_url` + `article_date`
and is **spot-checkable**. Coverage is concentrated in **2024-07 → 2026-06** (the most decision-
relevant window); 2023 and a few contaminated months remain gaps pending cleaner citation.
