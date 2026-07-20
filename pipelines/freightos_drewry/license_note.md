# License note — freightos_drewry (container freight indices)

Reviewed: 2026-07-19.

**Source (intended).** Freightos Baltic Index (FBX) / Drewry World Container Index —
weekly container freight rates. fbx.freightos.com.

**Access barrier.** The FBX values on fbx.freightos.com load via a client-side JS/API
(no static data URL in the page HTML); Drewry's weekly index page 404s at the tried path.
Per rule 5 we do not drive a headless browser to reach a JS-loaded endpoint. Not built
this session — documented.

**Role (when built).** LEADS CONTEXT ONLY — freight leads core-goods CPI by 1-2 quarters
(H4); NO contemporaneous admission claim. `vintage_status: point_in_time` (dated weekly
posts).

**Status:** NOT BUILT — JS-gated data endpoint. Revisit if Freightos exposes a static
weekly CSV/JSON or an API key path (log as a source with a license note then).
