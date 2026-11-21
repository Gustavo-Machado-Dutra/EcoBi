# Validation Record — EcoBI Finalization

**Result**: FAIL
**Author**: Implementer (not an independent verifier)
**Date**: 2026-11-19
**Spec**: `.specs/features/ecobi-finalization/spec.md` v1.0.0

## Verdict

This feature is not ready to close. An independent sub-agent reviewed the current onboarding and requirement evidence and returned important findings; that review did not provide a criterion-by-criterion TLC verifier PASS. The policy-gated browser UAT, live Ollama, complete module E2E evidence, clean proof tree and per-check verdict remain open. Keep the completion gate failed.

## Blocking gaps

- Real browser screenshot, DOM, tour interaction, responsive viewport, theme, and accessibility checks were denied by the Chrome DevTools MCP approval gate: `MCP tool call requires approval, but approval policy is never`.
- Official local Ollama installation/model setup and live inference remain unimplemented/unverified.
- Complete end-to-end flows for every module, restart/recovery, package smoke test, and UI-specific operation-safety proof remain incomplete.
- `.git` is read-only; task commits were not created. No permission bypass was attempted.

## Evidence reviewed by implementer

- `tests/test_finalization_frontend.py`: real FastAPI shell and onboarding static asset requests.
- `tests/frontend/onboarding.test.cjs`: guide coverage and versioned local state assertions.
- `tests/test_phase4_packaging_scheduler_multiproject.py`: C21 check-only DB isolation regression.
- `.specs/features/ecobi-finalization/proofs.md`: requirement-level result and evidence matrix.

This is a transparent blocked validation record, not the independent Verifier artifact required for a PASS.

## Independent review findings

- The help chooser modal behavior has a working-tree fix with inert background, outside-focus containment, restoration on close, and a simulated-DOM regression; browser behavior remains untested. The later independent review identified a separate ONB-01 welcome focus-trap defect, recorded in the follow-up below.
- Important documentation inconsistency: MOD-04 and SET-06 matrix statuses reconciled conservatively in the approved spec and the preserved requirement matrix.
- Remaining gaps: browser interaction/accessibility evidence, live Ollama installation and inference, complete module-specific E2E proof, and clean committed HEAD evidence.


## Latest TLC gate - 2026-11-19

- `check_proofs.py`: 27 pass, 0 fail; exit 1 because the repository tree is uncommitted.
- `validate_verification.py`: exit 1 with exactly one finding from the mechanical gate: `proofs.md` ran on uncommitted changes. The C1-C18 table/findings structure is present.
- `validate_tasks.py --execute`: 0 errors, 4 warnings. `validate_spec.py`: 0 errors, 0 warnings.
- This is still a FAIL for feature completion; no clean HEAD or commit was possible under the current read-only Git state.

## Independent review follow-up - 2026-11-19

A fresh read-only reviewer returned FAIL. The reviewer identified that ONB-01 says the welcome must not block navigation while the first-run Tab handler trapped focus; the working-tree fix removes that trap and preserves the help chooser modal trap. The C1 check now has separate proof rows for check-only DB isolation and unsafe bind rejection. The former C5/C13 concerns are historical and their claims were narrowed to the current assertions, without adding multi-user ownership.

The scoped re-verifier passed the Node harness (4/4); its Pytest attempt failed collection with `ModuleNotFoundError: fastapi`. The primary run using `.venv/Scripts/python.exe` passed the targeted launcher-bind test (1/1). The TLC proof run reported 27 passing proof/build rows with zero failing checks; completion remains blocked by dirty Git state. Browser/device/theme UAT, live Ollama, complete UI E2E, and clean-HEAD proof remain outstanding; overall result stays FAIL.


## Final verification continuation - 2026-11-19

- TLC proof: 28 pass, 0 failed checks; exit 1 because the repository tree is dirty. Full Pytest: 68 passed, 1 deprecation warning. Onboarding Node: 5 passed; Ollama bootstrap harness: 14 passed. Spec validation passed with 0 warnings; task validation passed with 0 errors and 4 advisory warnings.
- `validate_verification.py` returned one error: proofs were run on uncommitted changes. The clean-HEAD requirement cannot be met because `.git` is read-only; no ACL change or workaround was attempted.
- Scoped independent reviewers confirmed the loopback-listener fail-closed and first-panel geometry/test-coverage corrections. No criterion-by-criterion independent completion PASS is claimed.
- Packaged `--check-only` succeeded from a new PyInstaller build and created no database; real Ollama installation/model pull/inference remains untested. Chrome DevTools remained unavailable under the no-approval policy; no browser retry or alternate route was attempted.
- Verdict remains **FAIL**. Full UI E2E, visual/a11y UAT, live Ollama and clean committed HEAD remain pending.

## Independent review continuation — 2026-11-19

**Result: FAIL / not finalized.** A fresh read-only reviewer found (1) help chooser could overlap the welcome dialog and (2) spotlight lacked the requested direction marker. The first issue was corrected by hiding/restoring the welcome around help and preserving original Escape focus; the second received a CSS marker keyed to the measured panel position. The onboarding simulated DOM regression now passes 5/5.

Remaining evidence gaps are unchanged: no authorized real-browser screenshot/interaction/accessibility UAT, no installed Ollama or live inference, no complete browser UI E2E, and no clean committed HEAD. The independent review is scoped and does not certify all acceptance criteria.

## Current gate after review fix — 2026-11-19

The full suite passes (**68 passed**, one deprecation warning). TLC proof runner reports **28 pass / 0 fail rows** but exits nonzero for the dirty Git tree; `validate_verification.py` reports the corresponding single uncommitted-proof error. Spec validation passes; task validation has four advisories. Overall verdict stays **FAIL** because browser evidence, full UI E2E, live Ollama and clean committed HEAD remain unresolved.

## Independent criterion review — 2026-11-19

A fresh read-only review of all 52 IDs found consistency errors between SET-03–SET-07 in the approved spec and matrix, T8 marked complete despite those discrepancies, an ONB-16 traceability typo, and a stale spotlight direction marker on missing targets. The status tables and task status/range were reconciled; the fallback now sets `data-placement="center"`, with a simulated visible-to-missing target regression.

The review also found ONB-06's `data-tour` preference is not implemented; it remains partial. Remaining browser UAT, full UI E2E, live Ollama, package installation, and clean committed HEAD are blockers. Overall verdict remains **FAIL / not finalized**.

## Remediation of review findings — 2026-11-19

Corrected the `data-tour` selector gap: all general tour targets and contextual module targets now use stable shell attributes, asserted against the real HTML shell in the Node test. Corrected stale marker state for missing targets and added a regression that transitions from a positioned target to an unavailable one. This closes the source-level findings only; browser geometry and visual validation remain blocked.

## Independent continuation review — 2026-11-20

**Scope:** read-only inspection of the approved finalization spec, onboarding controller, tests, and evidence matrix. No browser, service installation, or code changes were performed by the reviewer.

| Finding | Severity | Disposition |
| --- | --- | --- |
| General/context guide progress appeared to share storage. | Important | Not reproducible in current behavior: each contextual guide is a single step; Back is disabled and final Next closes without persisting general progress. Added a regression that verifies general completion state survives contextual completion. No product-code change needed. |
| ONB-05/ONB-09 browser regression marked blocked despite locally testable interactions. | Important | Addressed partially with a Node DOM harness covering the complete tour controls, existing-view navigation, zero fetch calls, progress persistence, and retaining the last selected view. Browser/API/database before-after evidence remains unavailable. |
| New root launcher test was absent from the prior proof map and had not run. | Important | Test now passes independently and in current full suite; added its dedicated TLC proof command. |

The reviewer found no confirmed critical/security defect in this scoped pass. This was not a criterion-by-criterion acceptance verification and does not certify completion. Real-browser visual/accessibility and actual Ollama installation/inference remain blocked or not tested.

## Final gate status — 2026-11-20

- Mechanical proofs: 30/30 pass rows; exit 1 because `proofs.md` necessarily describes a dirty worktree.
- `validate_verification.py` has one remaining error: proofs were run on uncommitted changes. No ACL or permission workaround and no commit attempt was made.
- The separate TLC verifier request was unavailable (agent tool returned an unrelated refusal), so the scoped review is not promoted to an overall verifier PASS.
- `validate_state.py` is not part of the installed TLC 4.1.0 script set; STATE is recorded as FAIL/not finalized, not as validator-approved.
- Overall result: **FAIL / not finalized**, with external visual/service/install evidence and clean committed HEAD still outstanding.

## Latest integration rerun ? 2026-11-20

- C20 API E2E: **1 passed** using synthetic sample data and isolated SQLite; this proves the API persistence/export/audit chain, not dashboard rendering or corporate data operation.
- Current TLC check: **31 pass / 0 fail**, embedded full suite **70 passed** (one deprecation warning, 287.85 s); script exit 1 because the tree is dirty.
- Verification validator: one error only for uncommitted proofs. Spec strict and tasks execute validators pass their structural gates (0 spec errors; 0 task errors, 4 advisories).
- Final acceptance remains **FAIL / not finalized**: no authorized browser visuals/a11y, live Ollama/install/model/inference, clean installer-first-run, dedicated criterion verifier, or clean committed HEAD.


## Fresh independent C19 verification — 2026-11-20

**Overall result: FAIL / EcoBI finalization is not certifiable.** Scope: bounded independent review of ONB-09/C19, the new production-`switchView` test, and the existing C1–C21 proof/verification records. This is not a fresh criterion-by-criterion re-review of every C1–C21 row; prior rows remain recorded evidence, not fresh independent certification. Earlier history in this file is preserved.

### Spec-anchored outcome

| Requirement | Expected outcome | Fresh `file:line` assertion | Assessment |
|---|---|---|---|
| ONB-09 (`spec.md:111`) | Tour navigates only existing views, performs no business operation or data creation, and leaves the operator in the view active when the tour ends. | `tests/frontend/onboarding.test.cjs:6-23` loads/instruments the real `frontend/app.js` source in a VM to expose its `switchView`; `:430-444` drives that function through the real onboarding controller and asserts final view `view-scheduler` (`:436`), GET-only requests (`:440-441`), only the onboarding preference key is written (`:442`), and project/dataset storage keys remain absent (`:443-444`). The production function updates view state and calls module loaders at `frontend/app.js:331-392`. | **Partial, materially improved.** The test replaces the former stubbed callback concern with the production shell function and verifies client-observable navigation/storage/network-method behavior. It does not prove that mocked GET handlers have no server-side business, database, or audit effects. No confirmed product defect found. |

### Fresh verification and sensor

- `node --test tests/frontend/onboarding.test.cjs`: **7 passed, 0 failed**.
- Full Pytest had already completed in this verification turn (not rerun after the user’s instruction): **72 passed**, one Starlette/httpx deprecation warning, 332.03 seconds.
- Isolated discrimination sensor: injected `localStorage.setItem('ecobi_active_project_id', ...)` into a scratch copy of production `switchView`. The integrated test killed the mutant: **6 passed, 1 failed**, at the assertion allowing only `ecobi.onboarding.v1` writes (`onboarding.test.cjs:442`). Scratch was removed; real worktree status matched its pre-sensor baseline.
- Also passed: strict spec validation (0 errors/warnings), task validation (0 errors, 4 advisory warnings using the installed script’s supported invocation), Node syntax checks for `frontend/app.js` and `frontend/onboarding.js`, `audit-results.json` parse, PowerShell AST parse for the present launch scripts, and `git diff --check`.

### Ranked gaps / blockers

1. **Important evidence gap — ONB-09 remains partial.** The new test mocks HTTP responses and verifies methods, not the side effects of actual API handlers. Therefore it cannot fully establish “no business operations/data creation” on the server. This is an evidence limitation, not a confirmed defect (`tests/frontend/onboarding.test.cjs:15-18,430-444`).
2. **Feature-level verifier gap.** This review freshly re-derived ONB-09 only. The latest active TLC 4.1 `check_proofs.py` runs after this review generated `0 pass / 45 fail` because a Git Bash child exited with code `3221225794`; `validate_verification.py` reports 46 errors. The earlier 33-pass proof result is historical and superseded. These results do not substitute for a new independent assertion-by-assertion verification of all feature criteria. No feature-wide PASS is claimed.
3. **Browser/UAT blocker.** Chrome DevTools requires approval under a policy that does not grant it. No real-browser screenshots, responsive/theme review, accessibility review, or visual tour interaction were performed here. Do not treat simulated DOM evidence as visual approval.
4. **Ollama blocker.** Ollama is not installed. Real installation, model download, and local inference remain untested; harness results are not live-service evidence.
5. **Clean-HEAD gate blocker.** The worktree is dirty at `9e7513b`; `.git` is read-only. No commit or permission workaround was attempted. The clean-committed-HEAD proof condition remains unsatisfied.
6. **Documentation finding — resolved locally, uncommitted.** `spec.md:211` now describes the production `switchView` VM test and states its limits (mocked API handlers and no server-side database/audit or browser-rendering evidence). No commit hash is available because `.git` is read-only. This resolves the documentation inconsistency only; the overall verdict remains **FAIL / not finalized**.

No critical defect was confirmed in this bounded review. The overall status remains **FAIL / not finalized** due to the evidence and gate blockers above.


## Current rerun — 2026-11-20

- Full Pytest on the final code/test state: **72 passed**, 1 Starlette/httpx deprecation warning (308.66 s). Focused current regression reruns for C3/C4, C8, C11/C13, and C20/C21: **7 passed** total. `node --test tests/frontend/onboarding.test.cjs`: **7 passed**.
- Active TLC 4.1.0 `check_proofs.py`: **36 passed / 0 failed proofs**, including the full 72-test suite and build checks. The script exits 1 because it records proofs against the dirty worktree at `HEAD 9e7513b`.
- `validate_spec.py --strict`: **0 errors / 0 warnings**. `validate_tasks.py --execute`: **0 errors / 4 advisories**. Python compile, Node syntax, JSON parsing, PowerShell AST parsing, and `git diff --check` pass.
- Current `validate_verification.py` result: **3 errors**: dirty proof tree; missing `## Checks` table; missing `## Findings` section. The clean-tree error cannot be resolved while `.git` is read-only without a prohibited permission workaround. The report-structure errors are assigned to the independent verifier.
- Fresh independent C1–C21 verifier has been dispatched at the same recorded HEAD to update only `verification.md`; result pending. No visual browser evidence, live Ollama setup/inference, clean installer-first-run, or corporate-data validation is claimed. Overall verdict remains **FAIL / not finalized**.

## TLC finalization retake - 2026-11-20

- Active TLC 4.1.0 `check_proofs.py` executed all **36 proof rows**: 36 passed, 0 failed. The embedded complete Pytest suite reports **72 passed**, one Starlette/httpx deprecation warning. The command exits 1 because the worktree at `HEAD 9e7513b` is dirty; this is not a clean-HEAD proof pass.
- A fresh independent verifier reviewed C1-C21 and returned **FAIL**, with no confirmed critical product defect. C1, C2, C6, C11, and C18 remain partial; the four open findings concern clean-HEAD evidence, browser UAT, live Ollama/clean installer evidence, and the TLC discrimination sensor.
- `validate_spec.py --strict`: 0 errors, 0 warnings. `validate_tasks.py --execute`: 0 errors, 4 advisories. `validate_verification.py`: 5 errors (dirty proof tree and four findings not closed); the required C1-C21 Checks table and Findings table are now present.
- Local checks passed: Python `compileall`, `node --check` for both frontend scripts, PowerShell AST parsing for all three project scripts, `audit-results.json` JSON parsing, and `git diff --check`.
- The isolated synthetic API journey and module tests are not browser UI, corporate-data, or live-service evidence. Chrome DevTools approval remains unavailable and was not retried. Ollama is absent; no install/model download/inference or clean installer-first-run is claimed. No commit, push, ACL change, or permission workaround was attempted.
- Overall verdict remains **FAIL / not finalized**. The complete evidence and criterion review are in `proofs.md` and `verification.md`.
