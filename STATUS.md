## Current phase

Phase 0 (Repository scaffold & architecture of record) is complete per `AGENTS.md`.
Phases 1–17 are not marked complete. Uncommitted work beyond Phase 0 exists (FastAPI
skeleton, domain models/schemas, default Next.js app) but is unfinished and broken —
do not treat it as a finished phase.

## What is done

- Operating docs: `AGENTS.md`, `ARCHITECTURE.md`, `DECISIONS.md`, `README.md`
- Repo scaffold: `Makefile`, `docker-compose.yml`, `.env.example`, `.github/workflows/ci.yml`, `LICENSE`
- Cursor contract rule: `.cursor/rules/revivepay.mdc`
- Backend package layout under `backend/` (`pyproject.toml`, `Dockerfile`)
- Settings: `backend/app/config.py`
- DB engine/session: `backend/app/db.py`
- Logging / middleware / errors: `backend/app/logging_config.py`, `backend/app/middleware.py`, `backend/app/errors.py`
- FastAPI app with `/api/health`, `/api/version`, `/api/system/config`: `backend/app/main.py`
- Domain ORM modules: `backend/app/models/` (`enums.py`, `base.py`, `merchants.py`, `customers.py`, `transactions.py`, `events.py`, `cases.py`, `decisions.py`, `actions.py`, `outcomes.py`, `audit.py`, `metadata.py`, `other.py`, plus unused/conflicting `core.py`)
- Pydantic domain schemas: `backend/app/schemas/domain.py`, `backend/app/schemas/__init__.py`
- Backend tests: `backend/tests/` (`test_health.py`, `test_version.py`, `test_settings.py`, `test_config_endpoint.py`, `test_errors.py`, `test_domain_models.py`, `test_domain_schemas.py`, `conftest.py`)
- Frontend default Next.js scaffold: `frontend/` (`app/page.tsx`, `app/layout.tsx`, etc.) — not product UI
- Empty `core/` placeholders: `backend/app/core/{environment,executor,llm,policy}/`

## What is broken or unfinished

- Full `pytest` suite does **not** pass. Verified 2026-08-25:
  - `tests/test_domain_models.py` — collection **ERROR**: imports `PolicyVerdictRecord` and `Proposal` from `app.models`, but `__init__.py` does not export them (models use `Decision` instead; duplicate definitions live in unused `core.py`).
  - `tests/test_domain_schemas.py::test_case_read_from_model` — **FAILED**: constructs `Case` with `external_id` / float `amount`; exported `Case` in `cases.py` uses `amount_at_risk_minor` (int paise) and different fields.
  - Other collected tests (health/version/settings/config/errors + two schema tests): 34 passed when `test_domain_models.py` is ignored.
- Conflicting domain designs: `backend/app/models/core.py` (float `amount`, `Proposal`/`PolicyVerdictRecord`) vs modular models (integer minor units). Schemas in `domain.py` still use `float` for money, which violates the paise-integer contract.
- `scripts/verify.ps1` does not exist (referenced by the Cursor rules contract).
- No `backend/.venv`; Makefile `make verify` targets assume a Unix venv path.
- `ARCHITECTURE.md` still says Phase 0 / “no business logic”; docs drift vs present code.
- `core/` decision pipeline, synthetic seed, evaluation, and product frontend are not implemented.
- Frontend builds (`npm run build` in `frontend/` succeeded) but is still the stock create-next-app page.

## Next action

Do not invent or continue phases on your own. Wait for an explicit request for the next numbered phase; when asked, start from a green verify path and reconcile models/schemas/tests only if that phase requires it.

## How to verify

Intended command (per project contract): `scripts/verify.ps1` — **file missing today**.

Until it exists, from the repo root on this machine:

```powershell
cd backend; $env:PYTHONPATH = "."; python -m ruff check .; python -m ruff format --check .; python -m mypy app/ --config-file pyproject.toml; python -m pytest tests/ -v
cd ..\frontend; npm run build
```

Expected when healthy: ruff/mypy clean, all pytest tests pass, frontend build succeeds.
**Current result:** ruff and mypy clean; frontend build succeeds; pytest is red (collection error + `test_case_read_from_model` failure).

## Do not

- Do not implement future phases early or “finish” uncommitted Phase 1+ work unless that phase is explicitly requested.
- Do not trust a previous session’s test results — re-run the suite yourself.
- Do not delete, skip, xfail, or weaken failing domain tests to make CI green.
- Do not keep or introduce float/`Decimal` currency fields; money is integer paise only.
- Do not leave two competing Case/Proposal model designs (`core.py` vs modular models) unresolved when working the models phase.
- Do not claim Razorpay production integration; all payment effects are simulated.
