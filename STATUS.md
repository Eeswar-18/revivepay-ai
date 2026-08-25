## Current phase

Phase 2 complete.

## What is done

- Phase 0 scaffold and docs; Cursor rule `.cursor/rules/revivepay.mdc`
- FastAPI system endpoints in `backend/app/main.py` (`/api/health`, `/api/version`, `/api/system/config`)
- Session/engine plumbing in `backend/app/db.py` (reused; no separate `db/session.py`)
- Explicit ORM modules under `backend/app/models/` (14 tables; `compute_audit_hash` in `audit.py`)
- Repository layer in `backend/app/repositories/`:
  `base.py`, `errors.py`, `cases.py`, `transactions.py`, `decisions.py`, `actions.py`,
  `outcomes.py`, `audit.py`, `contact_ledger.py`, `bandit_stats.py`, `__init__.py`
- Pydantic schemas aligned to current models (Decision, `*_minor` ints, `from_attributes`)
  in `backend/app/schemas/domain.py`
- Architecture tests: `backend/tests/test_architecture.py` (held-out ban, inward deps,
  no Float/Numeric/Decimal in `mapped_column`)
- Repository tests: `backend/tests/test_repositories.py`
- ADR-0009 (selective repositories) and ADR-0010 (executable architecture tests) in
  `DECISIONS.md`; repository section in `ARCHITECTURE.md`

## What is broken or unfinished

- Domain API routers / services (Phases 3+)
- Held-out world config and synthetic dataset (Phase 3)
- Decision pipeline under `backend/app/core/` (features, risk, policy, LLM, executor)
- Product frontend
- `scripts/verify.ps1` still missing
- `Merchant.contact_budget_per_week` naming still does not end in `_minor`

## Next action

Phase 3 — held-out world config and synthetic dataset.

## How to verify

```powershell
cd backend; python -m pytest -q
cd backend; python -m ruff check .
cd backend; python -m mypy app
```

Expected: all tests pass; ruff “All checks passed”; mypy “Success: no issues found”.

## Do not

- Do not implement future phases early.
- Do not trust a previous session’s test results — re-run the suite yourself.
- Do not delete, skip, xfail, or weaken tests to make CI green.
- Do not reintroduce float/`Decimal`/`Numeric` monetary columns.
- Do not import held-out environment modules from decision/policy/agent/ml code.
- Do not claim Razorpay production integration; all payment effects are simulated.
