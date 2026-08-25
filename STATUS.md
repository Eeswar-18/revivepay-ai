## Current phase

Phase 2 Rescue A complete.

## What is done

- Phase 0 scaffold and docs (`AGENTS.md`, `ARCHITECTURE.md`, `DECISIONS.md`, `README.md`)
- Cursor rule: `.cursor/rules/revivepay.mdc`
- FastAPI skeleton: `backend/app/main.py` (`/api/health`, `/api/version`, `/api/system/config`), `config.py`, `db.py`, `errors.py`, `middleware.py`, `logging_config.py`
- Explicit model module set under `backend/app/models/`:
  `base.py`, `enums.py`, `merchants.py`, `customers.py`, `transactions.py`, `cases.py`,
  `events.py`, `decisions.py`, `actions.py`, `outcomes.py`, `audit.py`,
  `policy_versions.py`, `model_versions.py`, `simulation_runs.py`, `bandit_stats.py`,
  `contact_ledger.py` (deleted vague `core.py`, `metadata.py`, `other.py`)
- All required tables present: merchants, customers, transactions, cases, events,
  decisions, actions, outcomes, audit_log, policy_versions, model_versions,
  simulation_runs, bandit_stats, contact_ledger
- Domain model tests repaired for `Decision` (merged Proposal + PolicyVerdictRecord):
  `backend/tests/test_domain_models.py`, `backend/tests/test_domain_schemas.py`
- `backend/tests/conftest.py` imports `app.models` so `init_db` creates all tables
- pytest / ruff / mypy green for this rescue (verified this session)

## What is broken or unfinished

- `backend/app/repositories/` — not created
- Pydantic schema updates — `backend/app/schemas/domain.py` still uses legacy float
  `amount` / `external_id` / Proposal+PolicyVerdict shapes; not aligned to ORM
- `backend/tests/test_architecture.py` — missing
- Missing tables from ITEM 4: **none** (all 14 required tables exist)
- Naming invariant note: `Merchant.contact_budget_per_week` is BigInteger monetary
  (minor units) but does not end in `_minor` (rename deferred; not a type-only fix)
- `scripts/verify.ps1` still missing
- Decision pipeline under `backend/app/core/`, seed, evaluation, product frontend — not started

## Next action

Phase 2 Rescue B.

## How to verify

```powershell
cd backend; python -m pytest -q
cd backend; python -m ruff check .
cd backend; python -m mypy app
```

Expected: all tests pass, ruff “All checks passed”, mypy “Success: no issues found”.

## Do not

- Do not implement future phases early or invent phase work beyond the asked rescue.
- Do not trust a previous session’s test results — re-run the suite yourself.
- Do not delete, skip, xfail, or weaken domain tests to make CI green.
- Do not reintroduce float/`Decimal`/`Numeric` monetary columns; money is integer paise (`*_minor`).
- Do not resurrect `core.py` / `metadata.py` / `other.py` or duplicate Case/Proposal models.
- Do not claim Razorpay production integration; all payment effects are simulated.
