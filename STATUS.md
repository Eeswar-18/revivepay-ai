## Current phase

Step 2 of phased build complete: environment sampler.

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
- **Step 2 — environment sampler:**
  - `backend/app/core/banding.py`: `amount_band_for(amount_minor)` utility; hard-coded
    thresholds (MICRO ≤ 10 000, SMALL ≤ 100 000, MEDIUM ≤ 1 000 000, LARGE ≤ 5 000 000,
    XLARGE above); no `app.sim` imports; `ValueError` on negative input.
  - `backend/app/sim/environment.py`: `ActionContext` and `SampledOutcome` frozen
    dataclasses; `World` class with `default()` classmethod, `true_success_probability`,
    `true_churn_probability`, `sample_outcome`, and `active_downtime_severity`; strict
    10-step pipeline per spec; no module-level RNG; all randomness via caller-supplied
    `numpy.random.Generator`.
  - `backend/tests/test_environment.py`: 9 behavioural tests covering clamp coverage,
    HARD_DECLINE terminal threshold, CARD_EXPIRED retry floor, recoverable path existence,
    attempt decay, quiet-hour penalty, rail-downtime asymmetry, churn monotonicity, and
    cross-seed reproducibility over 200 draws.
  - `backend/pyproject.toml`: `python_version` bumped `3.11 → 3.12` to match installed
    numpy stubs (pre-existing mismatch, not introduced by this step).

## What is broken or unfinished

- Domain API routers / services
- Synthetic dataset generator (`backend/data/generate_dataset.py`)
- Decision pipeline under `backend/app/core/` (features, risk, policy, LLM, executor)
- Product frontend
- `scripts/verify.ps1` still missing
- `Merchant.contact_budget_per_week` naming still does not end in `_minor`

## Next action

Step 3 — synthetic dataset generator (`backend/data/generate_dataset.py`) and database
seeder (`backend/data/seed.py`).

## How to verify

```powershell
cd backend; python -m pytest
cd backend; python -m ruff check .
cd backend; python -m mypy app
```

Expected: 54 tests pass; ruff "All checks passed"; mypy "Success: no issues found in 40 source files".

## Do not

- Do not implement future steps early.
- Do not trust a previous session's test results — re-run the suite yourself.
- Do not delete, skip, xfail, or weaken tests to make CI green.
- Do not reintroduce float/`Decimal`/`Numeric` monetary columns.
- Do not import held-out environment modules from decision/policy/agent/ml code.
- Do not claim Razorpay production integration; all payment effects are simulated.
- Do not modify `backend/app/sim/world_config.yaml` or `backend/app/sim/WORLD_CONFIG_HASH.txt`.
