# LESSONS - auto-maintained by scripts/lessons.py

> Machine-owned. Do NOT hand-edit. Changes are overwritten on the next `lessons.py` write.
> Canonical state lives in `.specs/lessons.json`. Edit lessons only via the script.
> promote_threshold=2 distinct features · window_days=45 · quarantine_threshold=2

## Confirmed (load these at Plan/Checks)

Corroborated across multiple features. Safe to apply as guidance.

_none_

## Candidates (under observation - do NOT load as guidance yet)

Seen once or not yet corroborated. Tracked, not trusted.

### L-001 - Guard JSON.parse output against null, arrays, and non-object primitives before dereferencing fields when normalizing persisted client state.
- signal: `ac_gap` · recurrence: 1 feature(s) · scope: `onboarding` · harmful: 0
- features: ecobi-finalization
- evidence: frontend/onboarding.js:102-111 (onboarding)
- last seen: 2026-11-21T02:10:04Z

### L-002 - When a check requires serving a static asset, bind a proof that requests the asset route directly instead of only asserting its tag in HTML.
- signal: `weak_test` · recurrence: 1 feature(s) · scope: `specs-proofs` · harmful: 0
- features: ecobi-finalization
- evidence: C7 (specs-proofs)
- last seen: 2026-11-21T02:10:04Z

### L-003 - On SVGElement overlays, toggle the DOM hidden attribute via setAttribute/removeAttribute rather than the .hidden property and assert computed display in real browser screenshots.
- signal: `ac_gap` · recurrence: 1 feature(s) · scope: `onboarding` · harmful: 0
- features: ecobi-finalization
- evidence: frontend/onboarding.js:241-274 (onboarding)
- last seen: 2026-11-21T03:16:51Z

## Quarantined (failed when applied - ignore)

A confirmed lesson that recurred alongside failure. Kept for the maintainer to review.

_none_
