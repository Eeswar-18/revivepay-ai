## Current phase

Step 4 complete: All items (taxonomy reconciliation, synthetic data generation, 
domain API routers/services) have been implemented and tested.

## What is done

- Phase 0 scaffold and docs; Cursor rule `.cursor/rules/revivepay.mdc`
- FastAPI system endpoints in `backend/app/main.py` (`/api/health`, `/api/version`, `/api/system/config`)
- Session/engine plumbing in `backend/app/db.py`
- ORM models under `backend/app/models/` (14 tables)
- Repository layer under `backend/app/repositories/`
  (`base.py`, `errors.py`, `cases.py`, `transactions.py`, `decisions.py`, `actions.py`,
  `outcomes.py`, `audit.py`, `contact_ledger.py`, `bandit_stats.py`, `__init__.py`)
- Pydantic schemas in `backend/app/schemas/domain.py`
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
  - `backend/app/economics/net_value.py`: pure `net_expected_value()` returning
    `NetValueBreakdown` (frozen dataclass exposing `expected_gross_recovery_minor`,
    `mdr_deduction_minor`, `intervention_cost_minor`, `expected_churn_cost_minor`,
    `net_ev_minor`); raises `ValueError` if `intervention="STOP"` with `p_success != 0.0`
  - `backend/tests/test_net_value.py`: 11 tests
- **Step 4 ITEM 1 — taxonomy reconciliation, schema gaps, boundary hardening:**
  - `app/models/enums.py`: `FailureClass` and `ActionType` REPLACED to match the
    pre-registered `world_config.yaml` taxonomy (they previously shared exactly ONE
    member with it — every name the agent could emit was ungradeable). Added four new
    enums: `DelayBand`, `CustomerSegment`, `AmountBand`, `Rail`.
    `ESCALATE_HUMAN` and `NO_ACTION_WAIT` were deliberately dropped, not renamed:
    escalation is a `PolicyVerdict`, and waiting is `STOP` plus a `DelayBand`.
  - `app/models/customers.py`: added required `segment` column (observable).
    Still deliberately NO patience column anywhere.
  - `app/models/transactions.py`: added required `rail` column, so
    `RETRY_ALTERNATE_RAIL` is meaningful (card volume splits RAIL_A / RAIL_B).
  - `app/models/merchants.py`: corrected the `contact_budget_per_week` comment, which
    wrongly said `# minor units`. It is a CONTACT COUNT, not money — a 100x landmine
    for rule R006.
  - `app/config/settings.py`: REMOVED `WORLD_CONFIG_FILE`. It pointed at a stale path
    (`app/core/environment/...`) and was an env-overridable, decision-side pointer at
    held-out truth; a configurable path would let anyone repoint the "pre-registered"
    world. Also corrected `ECON_CONFIG_FILE` to `app/config/economics.yaml`.
  - `tests/test_architecture.py`: rewritten. The `app.sim` ban is now a UNIVERSAL ban
    with a one-entry allowlist (`app.sim` itself) instead of an enumerated list of
    decision-side packages — enumerating the forbidden set fails open every time a new
    package is added, which is exactly how `app.economics` and `app.config` ended up
    silently exempt. Three real bypasses are now closed and each has a negative test:
    (a) non-`environment` submodules (`from app.sim.generators import ...`),
    (b) relative imports (`from ..sim.environment import World`),
    (c) `from app import sim`.
    The two divergent AST walkers were collapsed into one resolver.
    The `world_config` string check now ignores docstrings, so the boundary can be
    documented in the modules that must obey it.
  - `tests/test_taxonomy_alignment.py` (NEW): set-BIJECTION tests binding all six
    enums to `world_config.yaml` keys, plus a pre-registration hash test and
    agreement between `banding.py`'s mirrored thresholds and the config.
  - `.gitattributes`: added `*.txt text eol=lf` (and py/md/toml/cfg/json). Only
    `*.yaml` was protected, so `WORLD_CONFIG_HASH.txt` had been rewritten with CRLF
    and showed as permanently modified even though the hash value was identical.
  - Restored `backend/data/.gitkeep` — the whole `backend/data/` directory was missing
    from the working tree (blob now matches the committed one).
- **Decision Pipeline (features, calibrated risk model, policy kernel, LLM planner, orchestrator):**
  - `backend/app/core/features.py`: feature builder that computes deterministic features
  - `backend/app/api/features.py`: feature computation API endpoints
  - `backend/app/core/risk_model.py`: calibrated recovery probability model
  - `backend/app/core/policy/engine.py` and `backend/app/core/policy/rules.py`: deterministic policy kernel
  - `backend/app/core/policy/policy.yaml`: policy rules configuration
  - `backend/app/core/llm/planner.py`: LLM planner for generating action proposals
  - `backend/app/core/llm/validate.py`: proposal validation
  - `backend/app/core/econ.py`: expected net value scoring
  - `backend/app/core/candidates.py`: candidate generation based on failure classification
  - `backend/app/core/orchestrator.py`: orchestrates the full decision pipeline
  - `backend/tests/test_features.py`: 7 tests for feature computation
  - `backend/tests/test_orchestrator.py`: 3 tests for orchestrator functionality
  - `backend/tests/test_decision_pipeline.py`: 4 tests for end-to-end pipeline integration

## What is broken or unfinished

- Evaluation harness, baselines, committed evaluation report
- Product frontend
- `scripts/verify.ps1` still missing
- `pyproject.toml` `[tool.mypy] exclude` patterns are written as `^backend/app/...`
  but the documented command runs `mypy app` from inside `backend/`, so those
  excludes almost certainly do not match. Pre-existing; not fixed here.

## Next action

Since the Decision Pipeline is complete and Step 2 probes have been verified, proceed with:
1. Developing evaluation harness and baselines
2. Committing evaluation report
3. Fixing `scripts/verify.ps1`
4. Fixing `pyproject.toml` `[tool.mypy] exclude` patterns

## How to verify

```powershell
cd backend
python -m pytest -q
python -m ruff format .        # may reformat files touched in ITEM 1
python -m ruff check .
python -m mypy app
```

Expected: **88 tests pass** (69 before ITEM 1, +7 new architecture tests, +12 new
taxonomy alignment tests). Ruff "All checks passed". Mypy "Success".

Confirm the held-out directory is untouched:

```powershell
git status --short backend/app/sim/
git hash-object backend/app/sim/world_config.yaml
git rev-parse :backend/app/sim/world_config.yaml   # must equal the line above
```

`world_config.yaml` must still hash to
`d69e2fe3c47f0282b14fb87acb2c7aa115c005b2294a3a832bcc6c2b6ed49591`
(sha256 over NEWLINE-NORMALISED text, not raw bytes).

## Do not

- Do not implement future steps early.
- Do not trust a previous session's test results — re-run the suite yourself.
- Do not delete, skip, xfail, or weaken tests to make CI green.
- Do not reintroduce float/`Decimal`/`Numeric` monetary columns.
- Do not import `app.sim` from anywhere outside `app.sim`; do not add entries to
  `_SIM_IMPORT_ALLOWLIST` in `tests/test_architecture.py` without an ADR.
- Do not reintroduce a `WORLD_CONFIG_FILE` setting or otherwise make the held-out
  config path configurable.
- Do not add a `patience` field to any model — it is held-out latent truth.
- Do not rename `Merchant.contact_budget_per_week` to `*_minor`. It is a COUNT.
- Do not claim Razorpay production integration; all payment effects are simulated.
- Do not modify `backend/app/sim/world_config.yaml` or `backend/app/sim/WORLD_CONFIG_HASH.txt`.
- Do not "correct" `estimated_churn_hazard_by_contact_index` in `economics.yaml` to match
  the world's true values — the divergence is intentional (see header comment in that file).
