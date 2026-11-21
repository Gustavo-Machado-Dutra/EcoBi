# ecobi-finalization verification

**Verdict**: FAIL (initial verifier round at `acc416c`; all verifier and post-audit findings closed through `29de035` / `1c1f6e1`)
**Proofs**: `proofs.md` regenerated at clean `HEAD` after closure fixes
**Verifier**: independent sub-agent (author != verifier) at `acc416c` + independent real-Chrome visual audit at `36882d0` / `29de035`

## Checks

| Check | Test | Holds |
| --- | --- | --- |
| C1 | `tests/test_phase4_packaging_scheduler_multiproject.py` `test_c21_windows_launcher_and_bootstrap_lifecycle`; `tests/test_root_launcher.py` `test_root_start_script_reaches_launcher_in_isolated_project_root`; `tests/test_local_network_security.py` `test_launcher_rejects_network_bind_hosts_before_startup` | yes |
| C2 | `tests/test_phase4_packaging_scheduler_multiproject.py` `test_c25_*` (5 tests); `tests/test_ollama_bootstrap.py` (14 tests) | yes |
| C3 | `tests/test_phase4_packaging_scheduler_multiproject.py` `test_c22_scheduled_connector_sync_and_concurrency_lock` | yes |
| C4 | `tests/test_phase4_packaging_scheduler_multiproject.py` `test_c23_scheduled_hmac_backup_retention_and_restore_trial` | yes |
| C5 | `tests/test_phase4_packaging_scheduler_multiproject.py` `test_c24_multiproject_dashboard_consolidation_and_rbac` | yes |
| C6 | `tests/frontend/onboarding.test.cjs` `contextual guides cover all twelve existing views`, `stored onboarding preferences are versioned and non-sensitive`, `welcome and tour preserve non-modal keyboard navigation while help remains modal` | yes |
| C7 | `tests/test_finalization_frontend.py` `test_application_shell_loads_onboarding_controller`, `test_onboarding_controller_is_served_as_local_static_asset` | yes (bound in `fba5520`; asset route verified in live `18093`/`18094` runtimes) |
| C8 | `tests/test_data_quality.py` `test_corrupted_file_rejected_cleanly`, `test_canonical_mapping_save_and_reapply` | yes |
| C9 | `tests/test_simulation.py` `test_simulation_outputs_separated_and_bounds_validated` | yes |
| C10 | `tests/test_security_memory_api.py` `test_auth_session_lgpd_consent_and_401`, `test_pii_masking_and_lgpd_cascade_purge` | yes |
| C11 | `tests/test_quality_overflow.py` `test_quality_mapping_table_keeps_accessible_labels_inside_scrollport`; `tests/test_powerbi_generator.py` `test_pbip_deduplicates_repeated_analyses_preserving_source_period_rows` | yes |
| C12 | `tests/test_analytics_financial_esg.py` `test_financial_esg_deterministic_and_credit_separation` | yes |
| C13 | `tests/test_llm_tool_calling.py` `test_assistant_api_endpoint` | yes |
| C14 | `tests/test_predictive_backtesting.py` `test_temporal_split_and_insufficient_history` | yes |
| C15 | `tests/test_validation_engine.py` `test_rejected_analysis_blocks_powerbi_generation` | yes |
| C16 | `tests/test_powerbi_generator.py` `test_pbip_pbir_generation_and_reconciliation` | yes |
| C17 | `tests/test_phase4_packaging_scheduler_multiproject.py` `test_scheduler_dispatches_persisted_due_job_once` | yes |
| C18 | `Run suite` (`pytest -vv`, 77 passed) | yes |
| C19 | `tests/frontend/onboarding.test.cjs` `general tour controls navigate only existing views, issue no controller-owned fetches, and persist completion`, `general tour uses real navigation without business writes or project changes` | yes |
| C20 | `tests/test_finalization_e2e.py` `test_api_journey_persists_project_import_quality_analysis_validation_and_powerbi` | yes |
| C21 | `tests/test_finalization_e2e.py` `test_failed_reupload_with_existing_filename_preserves_dataset_file`; `tests/test_data_quality.py` `test_concurrent_same_filename_ingests_use_distinct_storage_paths` | yes |
| C22 | `tests/test_finalization_e2e.py` `test_upload_under_tight_host_ram_and_clean_rollback_when_exhausted` | yes |
| C23 | `tests/test_root_launcher.py` `test_start_ecobi_accepts_python_3_11_plus_and_checks_declared_imports`, `test_root_start_script_serves_health_and_onboarding_then_shuts_down_cleanly` | yes |

## Findings

| Finding | Evidence | Fix | Closed |
| --- | --- | --- | --- |
| `normalizeState` crashes with an uncaught `TypeError` when `localStorage["ecobi.onboarding.v1"]` contains the valid JSON literal `"null"`, breaking onboarding startup instead of resetting invalid state (spec Implicit-Requirement Sweep: "testar arquivos inválidos e estado de onboarding inválido") | `frontend/onboarding.js:102-111` parses `"null"` to `null` without throwing and dereferences `saved.version`; `tests/frontend/onboarding.test.cjs:58-64` tests only syntax-invalid `"invalid"` and version `"0.9"` | Guard `normalizeState` so non-object, `null`, or array JSON falls back to `{}` and assert `"null"`, `"[]"`, and `"42"` reset to default state in `tests/frontend/onboarding.test.cjs` | `fba5520` (C6) |
| C7's selected proof does not fail if `/static/onboarding.js` is not served | `tasks.md:230-231` binds C7 ("serves the navbar/sidebar help controls and local controller asset") only to `tests/test_finalization_frontend.py::test_application_shell_loads_onboarding_controller`, which only calls `GET /` and never requests `/static/onboarding.js` | Add `test_onboarding_controller_is_served_as_local_static_asset PASSED` proof under `run shell` to C7 in `.specs/features/ecobi-finalization/tasks.md` and rerun `check_proofs.py` | `fba5520` (C7) |
| Hidden SVG backdrop dimmed non-tour screens on `display: block`, `openHelp()` left tour overlays behind chooser, `ARROW_EDGE_PAD=22` overhung `18px` rounded corners, and 78-char recovery copy clipped inside fixed `228px` panel | Chrome visual audit (`onboarding-visual-audit.json` + `probe_390.mjs` + `audit-chooser-over-tour-bug-light-1440x900.png`): `getComputedStyle(.eco-tour-backdrop).display` was `"block"` while `hidden`; clicking `?` mid-tour kept panel/backdrop visible; edge `arrowOffset` hit `22`/`24` vs `18px` radius; `contentScroll` reached `123 > 119` on recovery | Add `[hidden] { display: none !important; }` CSS rule, set `ARROW_EDGE_PAD = 28`, close active tour in `openHelp()`, guard `renderCurrent()` `rAF`, shorten recovery copy, style `general-help` CTA + `<480px` modal stack (`36882d0`), and toggle SVG DOM `hidden` attribute via `removeAttribute`/`setAttribute` (`29de035`); re-verified in Chrome with 0 findings across all 46 steps and 4 directions × 4 viewports × 2 themes (`1c1f6e1`) | `36882d0`, `29de035` (C6, C7) |
