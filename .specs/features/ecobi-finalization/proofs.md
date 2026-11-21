# ecobi-finalization proofs

**HEAD**: acc416c
**Tree**: clean
**Shell**: C:/Program Files/Git\bin\bash.exe
**Result**: 39 pass, 0 fail

| Check | Proof | Result |
| --- | --- | --- |
| C1 | `run launcher / test_c21_windows_launcher_and_bootstrap_lifecycle PASSED` | pass |
| C1 | `run root-launcher / test_root_start_script_reaches_launcher_in_isolated_project_root PASSED` | pass |
| C1 | `run launcher-bind / test_launcher_rejects_network_bind_hosts_before_startup PASSED` | pass |
| C2 | `run local-ai / 5 passed` | pass |
| C2 | `run ollama-bootstrap / 14 passed` | pass |
| C3 | `run flows / test_c22_scheduled_connector_sync_and_concurrency_lock PASSED` | pass |
| C4 | `run flows / test_c23_scheduled_hmac_backup_retention_and_restore_trial PASSED` | pass |
| C5 | `run flows / test_c24_multiproject_dashboard_consolidation_and_rbac PASSED` | pass |
| C6 | `run onboarding / contextual guides cover all twelve existing views` | pass |
| C6 | `run onboarding / stored onboarding preferences are versioned and non-sensitive` | pass |
| C6 | `run onboarding / welcome and tour preserve non-modal keyboard navigation while help remains modal` | pass |
| C7 | `run shell / test_application_shell_loads_onboarding_controller PASSED` | pass |
| C8 | `run flows / test_corrupted_file_rejected_cleanly PASSED` | pass |
| C8 | `run flows / test_canonical_mapping_save_and_reapply PASSED` | pass |
| C9 | `run flows / test_simulation_outputs_separated_and_bounds_validated PASSED` | pass |
| C10 | `run flows / test_auth_session_lgpd_consent_and_401 PASSED` | pass |
| C10 | `run flows / test_pii_masking_and_lgpd_cascade_purge PASSED` | pass |
| C11 | `run quality / test_quality_mapping_table_keeps_accessible_labels_inside_scrollport PASSED` | pass |
| C11 | `run quality / test_pbip_deduplicates_repeated_analyses_preserving_source_period_rows PASSED` | pass |
| C12 | `run flows / test_financial_esg_deterministic_and_credit_separation PASSED` | pass |
| C13 | `run flows / test_assistant_api_endpoint PASSED` | pass |
| C14 | `run flows / test_temporal_split_and_insufficient_history PASSED` | pass |
| C15 | `run flows / test_rejected_analysis_blocks_powerbi_generation PASSED` | pass |
| C16 | `run flows / test_pbip_pbir_generation_and_reconciliation PASSED` | pass |
| C17 | `run flows / test_scheduler_dispatches_persisted_due_job_once PASSED` | pass |
| C18 | `run suite / 77 passed` | pass |
| C19 | `run onboarding / general tour controls navigate only existing views, issue no controller-owned fetches, and pe` | pass |
| C19 | `run onboarding / general tour uses real navigation without business writes or project changes` | pass |
| C20 | `run api-e2e / test_api_journey_persists_project_import_quality_analysis_validation_and_powerbi PASSED` | pass |
| C21 | `run api-e2e / test_failed_reupload_with_existing_filename_preserves_dataset_file PASSED` | pass |
| C21 | `run reupload-collision / test_concurrent_same_filename_ingests_use_distinct_storage_paths PASSED` | pass |
| C22 | `run api-e2e / test_upload_under_tight_host_ram_and_clean_rollback_when_exhausted PASSED` | pass |
| C23 | `run root-launcher / test_start_ecobi_accepts_python_3_11_plus_and_checks_declared_imports PASSED` | pass |
| C23 | `run root-launcher / test_root_start_script_serves_health_and_onboarding_then_shuts_down_cleanly PASSED` | pass |
| Build | `node --check frontend/app.js` | pass |
| Build | `node --check frontend/onboarding.js` | pass |
| Build | `.venv/Scripts/python.exe -m compileall -q backend scripts` | pass |
| Build | `.venv/Scripts/python.exe -m json.tool audit-results.json > /dev/null` | pass |
| Build | `git diff --check` | pass |

## Output

`Run launcher` - exit 0

```
cachedir: .pytest_cache
rootdir: C:\Users\Pichau\Downloads\EcoBI
plugins: asyncio-1.5.0, anyio-4.9.0
asyncio: mode=Mode.STRICT, debug=False, asyncio_default_fixture_loop_scope=None, asyncio_default_test_loop_scope=function
collecting ... collected 11 items / 10 deselected / 1 selected

tests/test_phase4_packaging_scheduler_multiproject.py::test_c21_windows_launcher_and_bootstrap_lifecycle PASSED [100%]

============================== warnings summary ===============================
.venv\Lib\site-packages\fastapi\testclient.py:1
  C:\Users\Pichau\Downloads\EcoBI\.venv\Lib\site-packages\fastapi\testclient.py:1: StarletteDeprecationWarning: Using `httpx` with `starlette.testclient` is deprecated; install `httpx2` instead.
    from starlette.testclient import TestClient as TestClient  # noqa

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
================= 1 passed, 10 deselected, 1 warning in 4.83s =================
```

`Run root-launcher` - exit 0

```
plugins: asyncio-1.5.0, anyio-4.9.0
asyncio: mode=Mode.STRICT, debug=False, asyncio_default_fixture_loop_scope=None, asyncio_default_test_loop_scope=function
collecting ... collected 3 items

tests/test_root_launcher.py::test_root_start_script_reaches_launcher_in_isolated_project_root PASSED [ 33%]
tests/test_root_launcher.py::test_start_ecobi_accepts_python_3_11_plus_and_checks_declared_imports PASSED [ 66%]
tests/test_root_launcher.py::test_root_start_script_serves_health_and_onboarding_then_shuts_down_cleanly PASSED [100%]

============================== warnings summary ===============================
.venv\Lib\site-packages\fastapi\testclient.py:1
  C:\Users\Pichau\Downloads\EcoBI\.venv\Lib\site-packages\fastapi\testclient.py:1: StarletteDeprecationWarning: Using `httpx` with `starlette.testclient` is deprecated; install `httpx2` instead.
    from starlette.testclient import TestClient as TestClient  # noqa

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
======================== 3 passed, 1 warning in 27.60s ========================
```

`Run launcher-bind` - exit 0

```
cachedir: .pytest_cache
rootdir: C:\Users\Pichau\Downloads\EcoBI
plugins: asyncio-1.5.0, anyio-4.9.0
asyncio: mode=Mode.STRICT, debug=False, asyncio_default_fixture_loop_scope=None, asyncio_default_test_loop_scope=function
collecting ... collected 10 items / 9 deselected / 1 selected

tests/test_local_network_security.py::test_launcher_rejects_network_bind_hosts_before_startup PASSED [100%]

============================== warnings summary ===============================
.venv\Lib\site-packages\fastapi\testclient.py:1
  C:\Users\Pichau\Downloads\EcoBI\.venv\Lib\site-packages\fastapi\testclient.py:1: StarletteDeprecationWarning: Using `httpx` with `starlette.testclient` is deprecated; install `httpx2` instead.
    from starlette.testclient import TestClient as TestClient  # noqa

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
================= 1 passed, 9 deselected, 1 warning in 1.85s ==================
```

`Run local-ai` - exit 0

```
collecting ... collected 11 items / 6 deselected / 5 selected

tests/test_phase4_packaging_scheduler_multiproject.py::test_c25_local_ollama_readiness_accepts_only_installed_default_model PASSED [ 20%]
tests/test_phase4_packaging_scheduler_multiproject.py::test_c25_local_ollama_readiness_uses_fallback_when_model_is_missing PASSED [ 40%]
tests/test_phase4_packaging_scheduler_multiproject.py::test_c25_local_ollama_readiness_rejects_unapproved_destination PASSED [ 60%]
tests/test_phase4_packaging_scheduler_multiproject.py::test_c25_local_ollama_connection_failure_uses_fallback PASSED [ 80%]
tests/test_phase4_packaging_scheduler_multiproject.py::test_c25_external_ai_is_blocked_by_default PASSED [100%]

============================== warnings summary ===============================
.venv\Lib\site-packages\fastapi\testclient.py:1
  C:\Users\Pichau\Downloads\EcoBI\.venv\Lib\site-packages\fastapi\testclient.py:1: StarletteDeprecationWarning: Using `httpx` with `starlette.testclient` is deprecated; install `httpx2` instead.
    from starlette.testclient import TestClient as TestClient  # noqa

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
================= 5 passed, 6 deselected, 1 warning in 3.38s ==================
```

`Run ollama-bootstrap` - exit 0

```
tests/test_ollama_bootstrap.py::test_source_launcher_invokes_shared_bootstrap_with_configured_model PASSED [ 57%]
tests/test_ollama_bootstrap.py::test_packaged_launcher_resolves_bundled_bootstrap_asset PASSED [ 64%]
tests/test_ollama_bootstrap.py::test_installer_failure_keeps_local_fallback_and_cleans_download PASSED [ 71%]
tests/test_ollama_bootstrap.py::test_declining_first_run_setup_performs_no_download_or_install PASSED [ 78%]
tests/test_ollama_bootstrap.py::test_declining_missing_model_download_keeps_install_and_uses_fallback PASSED [ 85%]
tests/test_ollama_bootstrap.py::test_existing_wildcard_ollama_listener_is_rejected_before_cli_use PASSED [ 92%]
tests/test_ollama_bootstrap.py::test_unverifiable_or_private_ollama_listener_uses_fallback PASSED [100%]

============================== warnings summary ===============================
.venv\Lib\site-packages\fastapi\testclient.py:1
  C:\Users\Pichau\Downloads\EcoBI\.venv\Lib\site-packages\fastapi\testclient.py:1: StarletteDeprecationWarning: Using `httpx` with `starlette.testclient` is deprecated; install `httpx2` instead.
    from starlette.testclient import TestClient as TestClient  # noqa

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
======================= 14 passed, 1 warning in 15.25s ========================
```

`Run flows` - exit 0

```
tests/test_powerbi_generator.py::test_pbip_deduplicates_repeated_analyses_preserving_source_period_rows PASSED [ 83%]
tests/test_security_memory_api.py::test_auth_session_lgpd_consent_and_401 PASSED [ 86%]
tests/test_security_memory_api.py::test_project_isolation_and_duplicate_conflict PASSED [ 88%]
tests/test_security_memory_api.py::test_pii_masking_and_lgpd_cascade_purge PASSED [ 91%]
tests/test_security_memory_api.py::test_memory_budget_psutil_and_9b_gate PASSED [ 94%]
tests/test_security_memory_api.py::test_legacy_user_token_authenticates_protected_route_and_rejects_invalid_tokens PASSED [ 97%]
tests/test_security_memory_api.py::test_session_expiration_and_revocation_remain_enforced PASSED [100%]

============================== warnings summary ===============================
.venv\Lib\site-packages\fastapi\testclient.py:1
  C:\Users\Pichau\Downloads\EcoBI\.venv\Lib\site-packages\fastapi\testclient.py:1: StarletteDeprecationWarning: Using `httpx` with `starlette.testclient` is deprecated; install `httpx2` instead.
    from starlette.testclient import TestClient as TestClient  # noqa

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
================== 36 passed, 1 warning in 110.71s (0:01:50) ==================
```

`Run onboarding` - exit 0

```
✔ general guide covers all 18 documented topics and module targets (2.4477ms)
✔ contextual guides cover all twelve existing views (2.2737ms)
✔ stored onboarding preferences are versioned and non-sensitive (0.3786ms)
✔ welcome and tour preserve non-modal keyboard navigation while help remains modal (1.2465ms)
✔ tour spotlight and panel remain within the viewport after resize (2.7504ms)
✔ general tour controls navigate only existing views, issue no controller-owned fetches, and persist completion (1.6071ms)
✔ general tour uses real navigation without business writes or project changes (13.8375ms)
ℹ tests 7
ℹ suites 0
ℹ pass 7
ℹ fail 0
ℹ cancelled 0
ℹ skipped 0
ℹ todo 0
ℹ duration_ms 160.6047
```

`Run shell` - exit 0

```
rootdir: C:\Users\Pichau\Downloads\EcoBI
plugins: asyncio-1.5.0, anyio-4.9.0
asyncio: mode=Mode.STRICT, debug=False, asyncio_default_fixture_loop_scope=None, asyncio_default_test_loop_scope=function
collecting ... collected 2 items

tests/test_finalization_frontend.py::test_application_shell_loads_onboarding_controller PASSED [ 50%]
tests/test_finalization_frontend.py::test_onboarding_controller_is_served_as_local_static_asset PASSED [100%]

============================== warnings summary ===============================
.venv\Lib\site-packages\fastapi\testclient.py:1
  C:\Users\Pichau\Downloads\EcoBI\.venv\Lib\site-packages\fastapi\testclient.py:1: StarletteDeprecationWarning: Using `httpx` with `starlette.testclient` is deprecated; install `httpx2` instead.
    from starlette.testclient import TestClient as TestClient  # noqa

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
======================== 2 passed, 1 warning in 1.58s =========================
```

`Run quality` - exit 0

```
plugins: asyncio-1.5.0, anyio-4.9.0
asyncio: mode=Mode.STRICT, debug=False, asyncio_default_fixture_loop_scope=None, asyncio_default_test_loop_scope=function
collecting ... collected 3 items

tests/test_quality_overflow.py::test_quality_mapping_table_keeps_accessible_labels_inside_scrollport PASSED [ 33%]
tests/test_powerbi_generator.py::test_pbip_pbir_generation_and_reconciliation PASSED [ 66%]
tests/test_powerbi_generator.py::test_pbip_deduplicates_repeated_analyses_preserving_source_period_rows PASSED [100%]

============================== warnings summary ===============================
.venv\Lib\site-packages\fastapi\testclient.py:1
  C:\Users\Pichau\Downloads\EcoBI\.venv\Lib\site-packages\fastapi\testclient.py:1: StarletteDeprecationWarning: Using `httpx` with `starlette.testclient` is deprecated; install `httpx2` instead.
    from starlette.testclient import TestClient as TestClient  # noqa

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
======================== 3 passed, 1 warning in 12.53s ========================
```

`Run suite` - exit 0

```
tests/test_security_memory_api.py::test_memory_budget_psutil_and_9b_gate PASSED [ 92%]
tests/test_security_memory_api.py::test_legacy_user_token_authenticates_protected_route_and_rejects_invalid_tokens PASSED [ 93%]
tests/test_security_memory_api.py::test_session_expiration_and_revocation_remain_enforced PASSED [ 94%]
tests/test_simulation.py::test_simulation_outputs_separated_and_bounds_validated PASSED [ 96%]
tests/test_validation_engine.py::test_rejected_analysis_blocks_powerbi_generation PASSED [ 97%]
tests/test_validation_engine.py::test_carbon_credit_offsetting_violation_triggers_rejection PASSED [ 98%]
tests/test_validation_engine.py::test_mathematical_discrepancy_triggers_rejection PASSED [100%]

============================== warnings summary ===============================
.venv\Lib\site-packages\fastapi\testclient.py:1
  C:\Users\Pichau\Downloads\EcoBI\.venv\Lib\site-packages\fastapi\testclient.py:1: StarletteDeprecationWarning: Using `httpx` with `starlette.testclient` is deprecated; install `httpx2` instead.
    from starlette.testclient import TestClient as TestClient  # noqa

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
================== 77 passed, 1 warning in 266.93s (0:04:26) ==================
```

`Run api-e2e` - exit 0

```
plugins: asyncio-1.5.0, anyio-4.9.0
asyncio: mode=Mode.STRICT, debug=False, asyncio_default_fixture_loop_scope=None, asyncio_default_test_loop_scope=function
collecting ... collected 3 items

tests/test_finalization_e2e.py::test_failed_reupload_with_existing_filename_preserves_dataset_file PASSED [ 33%]
tests/test_finalization_e2e.py::test_api_journey_persists_project_import_quality_analysis_validation_and_powerbi PASSED [ 66%]
tests/test_finalization_e2e.py::test_upload_under_tight_host_ram_and_clean_rollback_when_exhausted PASSED [100%]

============================== warnings summary ===============================
.venv\Lib\site-packages\fastapi\testclient.py:1
  C:\Users\Pichau\Downloads\EcoBI\.venv\Lib\site-packages\fastapi\testclient.py:1: StarletteDeprecationWarning: Using `httpx` with `starlette.testclient` is deprecated; install `httpx2` instead.
    from starlette.testclient import TestClient as TestClient  # noqa

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
======================== 3 passed, 1 warning in 23.74s ========================
```

`Run reupload-collision` - exit 0

```
cachedir: .pytest_cache
rootdir: C:\Users\Pichau\Downloads\EcoBI
plugins: asyncio-1.5.0, anyio-4.9.0
asyncio: mode=Mode.STRICT, debug=False, asyncio_default_fixture_loop_scope=None, asyncio_default_test_loop_scope=function
collecting ... collected 6 items / 5 deselected / 1 selected

tests/test_data_quality.py::test_concurrent_same_filename_ingests_use_distinct_storage_paths PASSED [100%]

============================== warnings summary ===============================
.venv\Lib\site-packages\fastapi\testclient.py:1
  C:\Users\Pichau\Downloads\EcoBI\.venv\Lib\site-packages\fastapi\testclient.py:1: StarletteDeprecationWarning: Using `httpx` with `starlette.testclient` is deprecated; install `httpx2` instead.
    from starlette.testclient import TestClient as TestClient  # noqa

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
================= 1 passed, 5 deselected, 1 warning in 2.63s ==================
```
