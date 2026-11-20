# Authentication token regression

## Change

`get_current_session` now validates legacy API tokens through `database.verify_user_token_by_token(token)`. The existing `verify_user_token(username, token, conn)` contract remains unchanged. The fallback verifies stored PBKDF2 hashes and returns the matched persisted user; invalid values still resolve to HTTP 401. Session token validation remains first and continues to enforce expiry, revocation, and LGPD consent.

## Evidence (2026-11-20)

- Focused authentication/network tests: 16 passed.
- Full Pytest suite: 73 passed, 1 failed. The unrelated failure is `tests/test_finalization_e2e.py::test_api_journey_persists_project_import_quality_analysis_validation_and_powerbi`, where the second upload returns HTTP 400 instead of 201.
- Live launcher: `start.ps1 -Port 8002 -NoBrowser` started Uvicorn on `127.0.0.1:8002`; `/api/health` and `/` returned HTTP 200. Invalid bearer token on `/api/auth/session` returned HTTP 401 without an exception. Listener PID 32800 was stopped with Ctrl+C.
- Local Ollama `/api/tags` reported `qwen3.5:4b`; a real local `/api/generate` request completed successfully.
- A protected route with a valid legacy user token, invalid token, expired session, and revoked session is covered through the real TestClient/database validation path in `tests/test_security_memory_api.py`.

The full suite is not green because of the independent upload failure. Browser-driven module navigation was not performed in this validation.
