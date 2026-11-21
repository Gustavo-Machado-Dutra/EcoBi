# EcoBI Finalization — TLC Verification

**Date:** 2026-11-20
**Reviewed baseline:** `HEAD 9e7513b`; dirty worktree.
**Proofs**: `proofs.md` at 9e7513b (dirty worktree; 36 pass/0 fail rows)
**Verifier**: independent sub-agent (author != verifier)
**Verdict:** **FAIL — required clean-tree and user-facing evidence are missing.** This is an evidence verdict, not a confirmed product defect.
**Review:** Fresh read-only verifier; only this verification report was written. No other product, test, documentation, or `.git` changes were made.

## Checks

| Check | Test | Holds |
| --- | --- | --- |
| C1 | `tests/test_root_launcher.py:41-64,72-93`; `tests/test_local_network_security.py:144-166` | Partial — assertions detect check-only DB preservation and unsafe CLI bind, but not full fresh-clone startup, running-server shutdown, or scheduler recovery. |
| C2 | `tests/test_phase4_packaging_scheduler_multiproject.py:586-641`; `tests/test_ollama_bootstrap.py:106-172` | Partial — mocked local-model/fallback/install branches are discriminating; no live Ollama install, pull, or inference. |
| C3 | `tests/test_phase4_packaging_scheduler_multiproject.py:201-274,285-293` | Yes — asserts exact initial/incremental dataset rows and the overlapping-run lock outcome/history. |
| C4 | `tests/test_phase4_packaging_scheduler_multiproject.py:322-363,372-412` | Yes — asserts isolated restore snapshots, age/count retention, physical and metadata deletion, and HMAC verification. |
| C5 | `tests/test_phase4_packaging_scheduler_multiproject.py:485-493,515-521` | Yes — asserts multiproject totals and HTTP 403 for the restricted project case. |
| C6 | `tests/frontend/onboarding.test.cjs:25-49,104-175,185-280` | Partial — simulated DOM tests discriminate keyboard/focus/Escape and resize geometry, but do not cover real rendered behavior, screen readers, contrast, all specified viewports/themes, or captures. |
| C7 | `tests/test_finalization_frontend.py:6-12,15-20` | Yes — asserts shell help controls/controller references and local asset serving; not browser interaction. |
| C8 | `tests/test_data_quality.py:54-85,336-381` | Yes — asserts malformed upload rejection, saved mapping persistence, and reprofiled mapping/duplicate-period outcome. |
| C9 | `tests/test_simulation.py:89,113-133` | Yes — asserts invalid-bound HTTP 400 and separation of scenario output from observed impact. |
| C10 | `tests/test_security_memory_api.py:29-104,260-269` | Yes — asserts session/consent/role outcomes and DB/file removal on purge. |
| C11 | `tests/test_powerbi_generator.py:248-289`; `tests/test_quality_overflow.py:7-15` | Partial — export assertions discriminate source-row dedupe/reconciliation; layout test checks literal markup/CSS only, not rendered label containment or viewport scrolling. |
| C12 | `tests/test_analytics_financial_esg.py:74-78,116-123` | Yes (synthetic fixture) — checks independently calculated financial/ESG values and credit separation; no corporate dataset used. |
| C13 | `tests/test_llm_tool_calling.py:202-251` | Yes (fallback fixture) — asserts nonempty text, exact offline mode, tool name/IDs, and populated profile summary; not live Ollama. |
| C14 | `tests/test_predictive_backtesting.py:67-68,109,124` | Yes — checks insufficient-history outcome, chronological split, and baseline comparison for the tested fixture. |
| C15 | `tests/test_validation_engine.py:67-82,98-110` | Yes — asserts rejected analyses cannot publish and tested exports return HTTP 400. |
| C16 | `tests/test_powerbi_generator.py:200-214` | Yes (artifact-level) — checks reconciliation, discrepancies, tolerance, download, and required bundle members; not Power BI Desktop opening. |
| C17 | `tests/test_phase4_packaging_scheduler_multiproject.py:525-546` | Yes — asserts due dispatch, persisted next run/status, no duplicate dispatch, and one execution record. |
| C18 | `proofs.md:3-6,35,229-246`; `tasks.md:29` | No — ledger records 36 proof rows passed/0 failed and suite 72 passed, but supplied runner exits nonzero for dirty tree; clean-HEAD and complete Build gate are not proven. |
| C19 | `tests/frontend/onboarding.test.cjs:291-392,394-470` | Yes (simulated integration) — asserts navigation, GET-only requests, onboarding-only writes, and unchanged project/dataset state in the harness; not browser behavior. |
| C20 | `tests/test_finalization_e2e.py:145-190,192-` | Yes (synthetic API) — asserts read-after-write results and exact consolidated revenue across two projects plus export; in-process TestClient, not browser/live-source evidence. |
| C21 | `tests/test_finalization_e2e.py:11-74`; `tests/test_data_quality.py:108-148` | Yes (storage-path behavior) — asserts distinct sequential/concurrent paths, exact retained bytes, and preserved records; concurrency is direct service invocation, not simultaneous HTTP uploads. |

## Findings

| Finding | Evidence | Fix | Closed |
| --- | --- | --- | --- |
| P1 — Clean-tree proof gate fails | `proofs.md:3-6` records dirty tree and 36/0 proof rows; the supplied run exits nonzero for dirty-tree condition. Its dirty-path list (`proofs.md:4`) is narrower than current `git status --short --branch`. Full Build gate is specified at `tasks.md:29` but not evidenced in `proofs.md:41-45`. | Re-run the proof and complete Build gate against an exact clean committed snapshot; update the proof ledger from that run. | No — open |
| P1 — Browser/UAT evidence missing | `spec.md:115-119`; `tasks.md:125`; simulated focus/geometry only in `tests/frontend/onboarding.test.cjs:104-175,185-280`. No browser screenshots or full guide × viewport × theme run. | Perform authorized browser/a11y UAT across required guides, viewports, and themes; attach real captures and record any inaccessible states. | No — open |
| P1 — Installer and live-service evidence missing | `tests/test_root_launcher.py:41-64,72-93` uses `-CheckOnly`; Ollama harness results are recorded in `proofs.md:109-146`. No clean installer-first-run, vendor installation, live model pull/inference, or corporate-data evidence. Scope: `spec.md:128-139`. | Run the clean isolated installer/startup path and live local-model checks when available and authorized; report only observed results. | No — open |
| P1 — Discrimination sensor not run | Active TLC `validate.md:78-108` requires scratch-only mutations after a passing gate; current proof gate is nonzero. | After the proof gate passes, run targeted scratch mutations, record killed/survived outcomes, and verify the real worktree baseline is unchanged. | No — open |
