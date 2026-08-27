# RevivePay-AI Architectural Audit Report

## 1. CURRENT PROJECT STATE

The repository is in a validated state following the completion of:
- Phase 0: Architecture skeleton
- Phase 1: Repository layer, domain models, schemas
- Phase 2: Held-out outcome environment (Step 2)
- Phase 3: Agent-visible economics configuration and net expected-value calculator (Step 3)
- Phase 4 ITEM 1: Taxonomy reconciliation, schema gaps, boundary hardening
- Phase 4 ITEM 2: Deterministic seeded synthetic generators (`backend/app/sim/generators.py`)

All tests pass (88 tests), Ruff and MyPy checks pass, and the held-out simulation boundary is preserved (world_config.yaml hash matches expected value).

## 2. WHAT IS VERIFIED WORKING

- **Domain Models**: ORM models for merchants, customers, transactions, cases, etc. with correct fields and constraints.
- **Repository Layer**: Typed persistence adapters (`cases.py`, `contact_ledger.py`, `errors.py`, etc.) with legal state transitions.
- **Simulation Environment**: `backend/app/sim/environment.py` provides `World`, `ActionContext`, `SampledOutcome` and deterministic outcome sampling.
- **Synthetic Data Generation**: `backend/app/sim/generators.py` creates reproducible synthetic populations via injected `numpy.random.Generator`.
- **Economics Module**: `backend/app/economics/net_value.py` computes net expected value from agent-visible configuration.
- **Configuration**: Pydantic-settings based configuration in `backend/app/config/`.
- **Architecture Tests**: `tests/test_architecture.py` enforces held-out boundary, inward dependencies, and monetary type bans.
- **Test Suite**: Behavioral tests for generators, environment, net value, repositories, etc. all pass.

## 3. WHAT IS INCOMPLETE

Based on the ARCHITECTURE.md and STATUS.md, the following major components are missing:

### 3.1 Decision Pipeline (Phase 4+)
- Revenue-at-risk detection (`core/detection.py`)
- Deterministic feature builder (`core/features.py`)
- Feasible candidate action generation (`core/candidates.py`)
- Calibrated recovery probability model (`core/risk_model.py`)
- Expected-net-value scoring (`core/econ.py`)
- LLM planner (`core/llm/planner.py`)
- Schema + invariant validation (`core/llm/validate.py`)
- Deterministic policy kernel (`core/policy/engine.py`)
- Blast-radius and kill-switch checks
- Idempotent executor (`core/executor/executor.py`)
- Adapter interface (`core/executor/adapters.py`)
- Virtual clock (`core/executor/clock.py`)
- Audit logging (`core/audit.py`)
- Evaluation metrics (`core/evaluation.py`)

### 3.2 API Layer
- FastAPI domain routes (`backend/app/api/`) for case management, actions, etc.

### 3.3 Frontend Integration
- No frontend work has begun (Lovable will handle this later).

### 3.4 Persistence Integration
- While repository layer exists, it is not yet wired into the decision pipeline or API.
- Database seeding scripts (`backend/data/`) are present but not integrated.

### 3.5 Evaluation Harness
- Counterfactual evaluation design described in ARCHITECTURE.md but not implemented.

## 4. WHAT IS BROKEN OR RISKY

- **No known broken components**: All existing tests pass.
- **Risk**: The held-out environment boundary is critical. Any future implementation must not violate the architecture test.
- **Risk**: The decision pipeline must be designed to access the held-out environment outcome simulator without importing `app.sim` from decision-side modules. This requires careful dependency injection or service locator pattern that respects the boundary.
- **Risk**: Synthetic data generators produce only failed transactions. The system must be able to simulate the outcomes of proposed actions (retries, nudges, etc.) via the held-out environment.

## 5. NEXT 5 IMPLEMENTATION MILESTONES

1. **Implement the Virtual Clock** (`core/executor/clock.py`)
   - Provides deterministic time simulation for scheduling and timeouts.
   - Dependency-free; can be implemented independently.

2. **Implement Revenue-at-Risk Detection** (`core/detection.py`)
   - Classifies incoming webhook events into `payment_failure`, `abandoned_checkout`, `mandate_debit_failure`.
   - Creates initial `Case` records in the repository.

3. **Implement Deterministic Feature Builder** (`core/features.py`)
   - Pure functions that convert `Case` and history into feature vectors.
   - Includes failure classification from feature vector.

4. **Implement Feasible Candidate Action Generation** (`core/candidates.py`)
   - Enumerates valid interventions given failure type and policy rules.
   - Outputs list of candidate actions for scoring.

5. **Implement Calibrated Recovery Probability Model** (`core/risk_model.py`)
   - Wraps a scikit-learn `CalibratedClassifierCV` to estimate P(recovery | action, features).
   - Must be trained offline; for now, implement stub that returns deterministic values for testing.

## 6. WHICH MILESTONE SHOULD BE DONE FIRST

**Milestone 1: Virtual Clock** is the most foundational and independent component. It has no external dependencies and is used throughout the system for time-sensitive operations (scheduling, timeouts, outcome sampling). Implementing it first unblocks time-dependent logic in other modules.

## 7. WHAT CLAUDE WILL IMPLEMENT

Claude (the coding agent) will implement all backend components:
- Virtual clock
- Detection, features, candidates, risk model, economics, LLM planner, validation, policy kernel, executor, adapters, audit, evaluation
- API routes wiring repositories and core logic
- Database integration (session management, migrations)
- Ensuring architecture test compliance

## 8. WHAT SUPABASE WILL HANDLE

Supabase will provide the PostgreSQL database instance for:
- Storing cases, merchants, customers, transactions, decisions, actions, outcomes, audit logs
- Connection via `DATABASE_URL` environment variable
- Schema migrations managed through SQLAlchemy (Alembic-style or manual)
- Claude will design the database schema via SQLAlchemy models; Supabase is just the storage backend.

## 9. WHAT LOVABLE WILL HANDLE

Lovable will handle the frontend implementation once backend API contracts are stable:
- Next.js 15 App Router pages for case dashboard, action history, metrics
- React components using shadcn/ui and Tailwind CSS
- API client using TanStack Query and Zod for runtime validation
- Charts using Recharts
- Lovable will implement based on OpenAPI docs generated from FastAPI routes.

## 10. DECISIONS NEEDED FROM YOU

Before proceeding with Milestone 1 (Virtual Clock), I need confirmation on:

1. **Virtual Clock Rate**: Should the default virtual-to-real time rate be 60 (as implied in ARCHITECTURE.md) or a different value for development/testing?
2. **Epoch Configuration**: Should the virtual epoch be configurable via environment variables or hard-coded to a specific date (e.g., 2024-01-01) for reproducibility?
3. **Dependencies**: Are we allowed to add new Python dependencies (e.g., for scikit-learn in the risk model) or must we use only existing project dependencies?

Please confirm these points so I can implement the Virtual Clock correctly and in alignment with project expectations.