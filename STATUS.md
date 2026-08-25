## Current phase

Step 3 complete: agent-visible economics config and net expected-value calculator.

## What is done

- Phase 0 scaffold and docs; Cursor rule `.cursor/rules/revivepay.mdc`
- FastAPI system endpoints in `backend/app/main.py` (`/api/health`, `/api/version`, `/api/system/config`)
- Session/engine plumbing in `backend/app/db.py`
- ORM models under `backend/app/models/` (14 tables)
- Repository layer under `backend/app/repositories/`
  (`base.py`, `errors.py`, `cases.py`, `transactions.py`, `decisions.py`, `actions.py`,
  `outcomes.py`, `audit.py`, `contact_ledger.py`, `bandit_stats.py`, `__init__.py`)
- Pydantic schemas in `backend/app/schemas/domain.py`
- Architecture tests: `backend/tests/test_architecture.py`
- Repository tests: `backend/tests/test_repositories.py`
- ADR-0009 (selective repositories), ADR-0010 (architecture tests) in `DECISIONS.md`
- **Step 2 — held-out outcome environment:**
  - `backend/app/sim/world_config.yaml` + `WORLD_CONFIG_HASH.txt` (pre-registered, immutable)
  - `backend/app/core/banding.py`: `amount_band_for(amount_minor)` utility
  - `backend/app/sim/environment.py`: `World`, `ActionContext`, `SampledOutcome`
  - `backend/tests/test_environment.py`: 9 behavioural tests
- **Step 3 — agent-visible economics and net expected-value calculator:**
  - `backend/app/config/economics.yaml`: agent-visible MDR, intervention costs,
    segment LTV/churn-sensitivity, and deliberately mis-specified estimated churn hazard
    (header comment explains the intentional divergence from world truth)
  - `backend/app/config/settings.py`: application pydantic-settings config, moved here
    from `backend/app/config.py` when the new `config/` package was created
  - `backend/app/config/__init__.py`: re-exports `Settings` and `get_settings` so all
    existing `from app.config import ...` importers continue to work unchanged
  - `backend/app/economics/__init__.py` + `backend/app/economics/net_value.py`:
    pure `net_expected_value()` function returning `NetValueBreakdown` (frozen dataclass
    exposing `expected_gross_recovery_minor`, `mdr_deduction_minor`,
    `intervention_cost_minor`, `expected_churn_cost_minor`, `net_ev_minor`)
  - `backend/tests/test_net_value.py`: 11 tests covering STOP argmax on micro transactions,
    AGENT_CALL positive on large amounts, p_success monotonicity, contact-index
    monotonicity, churn-zero for non-contacting interventions, default_beyond fallback,
    HIGH_VALUE-vs-OCCASIONAL churn cost (counterintuitive LTV-dominance property),
    component integrity sum, architecture ban on app.sim, and unknown-key KeyError

## What is broken or unfinished

- Domain API routers / services
- Synthetic dataset generator (`backend/data/generate_dataset.py`)
- Decision pipeline under `backend/app/core/` (features, risk, policy, LLM, executor)
- Product frontend
- `scripts/verify.ps1` still missing
- `Merchant.contact_budget_per_week` naming still does not end in `_minor`

## Next action

Step 4 — synthetic dataset generator and database seeder
(`backend/data/generate_dataset.py`, `backend/data/seed.py`).

## How to verify

```powershell
cd backend; python -m pytest
cd backend; python -m ruff check .
cd backend; python -m mypy app
```

Expected: 65 tests pass; ruff "All checks passed"; mypy "Success: no issues found in 43 source files".

## Do not

- Do not implement future steps early.
- Do not trust a previous session's test results — re-run the suite yourself.
- Do not delete, skip, xfail, or weaken tests to make CI green.
- Do not reintroduce float/`Decimal`/`Numeric` monetary columns.
- Do not import held-out environment modules from decision/policy/agent/ml/economics code.
- Do not claim Razorpay production integration; all payment effects are simulated.
- Do not modify `backend/app/sim/world_config.yaml` or `backend/app/sim/WORLD_CONFIG_HASH.txt`.
- Do not "correct" `estimated_churn_hazard_by_contact_index` in `economics.yaml` to match
  the world's true values — the divergence is intentional (see header comment in that file).
