# DECISIONS.md — Architecture Decision Records

This file records every significant architectural decision made for RevivePay AI.
New ADRs are added in the same phase in which the decision is made.
Existing ADRs are amended (not deleted) if a decision is revised, with the revision date noted.

---

## ADR-0001 — SQLite over PostgreSQL for the prototype, with ORM-only access for portability

**Date:** 2026-08-25
**Status:** Accepted

### Context
The project requires a relational database that stores cases, events, proposals, policy
verdicts, actions, outcomes and audit log entries. Production fintech workloads demand a
robust, concurrent database. However, Phase 0–17 of this project is a prototype whose
primary goal is demonstrability and reproducibility, not production scale.

### Decision
Use **SQLite** as the default database. All database access is mediated exclusively through
**SQLAlchemy 2.0 ORM** — no raw SQL, no SQLite-specific pragma calls (except the WAL mode
pragma that SQLAlchemy applies automatically, which is also safe on PostgreSQL). The
`DATABASE_URL` environment variable is the only place the database engine is specified.

### Consequences
- **Positive:** Zero setup for a reviewer cloning the repo. No Docker dependency for the
  database. Deterministic, file-based storage makes test isolation trivial.
- **Positive:** Switching to PostgreSQL for production is a one-line change to `DATABASE_URL`
  (e.g., `postgresql+asyncpg://...`), requiring no code changes because no SQLite-specific
  SQL has been written.
- **Negative:** SQLite does not enforce foreign key constraints by default (must be enabled
  per-connection), has limited concurrent write throughput, and does not support some
  advanced SQL features. These limitations are acceptable for a prototype.
- **Negative:** The WAL journal mode is enabled to support concurrent read access during
  evaluation runs, but SQLite still serialises writes.

### Alternatives Rejected
- **PostgreSQL from day one:** Adds a Docker or cloud dependency that raises the bar for a
  reviewer to run the system. Rejected for prototype phase; re-evaluate at productionisation.
- **DynamoDB / NoSQL:** The data model is inherently relational (cases, events, actions,
  outcomes share foreign keys). A document store would require manual join emulation.

---

## ADR-0002 — The LLM is a planner and explainer, never an executor or pricer of risk

**Date:** 2026-08-25
**Status:** Accepted

### Context
Large language models are capable of generating free-form text that resembles decision
rationale. It is tempting to allow the LLM to both decide and execute recovery actions.
However, LLMs produce non-deterministic, hallucination-prone outputs that cannot be audited
or replicated reliably in a financial context.

### Decision
The LLM's role is strictly limited to **planning and explanation**:
1. It receives a structured prompt containing the feature vector, the feasible candidate
   actions with their pre-computed expected-net-value scores, and the policy rules (as
   prose context).
2. It returns a **proposal**: a JSON object selecting one candidate, proposing a schedule
   time, and providing a human-readable justification that cites specific features.
3. It does **not** compute probabilities, costs, amounts, currencies, or any numeric value
   that feeds into the objective function.
4. It does **not** invoke tools, call APIs, or trigger any side effect.
5. Its output is validated, schema-checked, and must pass the deterministic policy kernel
   before any action is taken.

### Consequences
- LLM errors result in rejected proposals, never in incorrect financial actions.
- The justification is auditable because the features it cites are logged and verifiable.
- The system can run end-to-end with a deterministic mock LLM (no API key required).

### Alternatives Rejected
- **LLM as tool-calling agent:** Allows the LLM to invoke payment APIs directly. Rejected
  because it violates the fail-closed safety requirement and makes audit impossible.
- **LLM computes recovery probability:** LLM confidence scores are not calibrated
  probabilities. Rejected; see ADR-0003.

---

## ADR-0003 — Recovery probability from a calibrated statistical model, not LLM confidence

**Date:** 2026-08-25
**Status:** Accepted

### Context
A recovery probability estimate is the foundation of the expected-value objective function.
An uncalibrated estimate produces systematically biased action selection.

### Decision
Recovery probability is estimated by a **scikit-learn classifier trained on logged outcomes**
and calibrated with `CalibratedClassifierCV` (isotonic regression on a held-out calibration
fold). The output is a proper probability (i.e., the average predicted probability for a
cohort equals the empirical recovery rate for that cohort). The LLM is never asked to
estimate, adjust or comment on probabilities — that would contaminate the calibration.

### Consequences
- Probabilities improve as more outcomes are logged (see ADR-0008 and `core/learning.py`).
- Calibration quality is reported explicitly (Brier score, reliability diagram).
- The model is versioned and its training data is logged, enabling reproducibility.
- In early phases, the model is trained on synthetic data; this is disclosed in the UI.

### Alternatives Rejected
- **LLM-reported confidence:** Not a calibrated probability. Varies with phrasing.
- **Hard-coded heuristics:** Cannot adapt to changing payment environment conditions.
- **Deep learning model:** Adds infrastructure complexity without benefit at prototype data
  volumes. Revisit if the dataset exceeds ~1 M rows.

---

## ADR-0004 — Objective function is expected NET recovered value

**Date:** 2026-08-25
**Status:** Accepted

### Context
Maximising gross recovery (recovered amount × probability) ignores the costs of the
recovery attempt, leading to over-intervention: sending too many emails, creating customer
fatigue, and incurring unnecessary gateway fees.

### Decision
The objective function is **expected net recovered value (ENRV)**:

```
ENRV(action, case) =
    P(recovery | action, features) × recovered_amount
  − gateway_cost(action)
  − contact_cost(action)
  − P(churn | action, features) × expected_lifetime_value
```

All cost parameters are loaded from `econ_config.yaml` (committed defaults) and overridable
via environment variable. The policy kernel may additionally enforce budget caps that the
ENRV score does not capture.

### Consequences
- The system will sometimes correctly choose to do nothing (ENRV < 0 for all actions).
- Cost parameters must be kept accurate; stale costs produce suboptimal decisions.
- Churn cost introduces a customer-lifetime-value dependency that must be documented.

### Alternatives Rejected
- **Gross recovery only:** Over-intervenes; financially unsound.
- **Rule-based fixed ladder (e.g., always retry once, then email):** Cannot adapt to
  case characteristics. Included as a baseline (see ADR-0008) but not the objective.

---

## ADR-0005 — The outcome environment is held out from all decision modules

**Date:** 2026-08-25
**Status:** Accepted

### Context
A common failure mode in simulated AI evaluations is "leakage": the decision logic can
access ground-truth outcome parameters (e.g., the true recovery probability for a given
case), inflating apparent performance.

### Decision
All ground-truth environment parameters live exclusively in `core/environment/` and
`world_config.yaml`. No module under `core/features`, `core/risk_model`, `core/econ`,
`core/llm`, `core/policy`, or `core/executor` may import from `core/environment` or read
`world_config.yaml` directly. This is enforced by an **architecture test** in
`tests/test_architecture.py` that uses AST analysis to verify import boundaries at CI time.
`world_config.yaml` is pre-hashed at the start of each evaluation run; the hash is stored
in the run manifest for auditability.

### Consequences
- Evaluation results are credible: the agent cannot cheat, even accidentally.
- Adding new environment parameters requires an explicit PR touching only `core/environment`.
- The architecture test must be updated whenever a new module is added.

### Alternatives Rejected
- **Trust-based separation (documentation only):** Insufficient; an engineer importing the
  wrong module by accident would silently invalidate all results.
- **Separate process / microservice for the environment:** Correct in production; too much
  infrastructure overhead for a prototype. The import-boundary test provides equivalent
  guarantees for a monorepo.

---

## ADR-0006 — The policy kernel is deterministic, versioned, ordered, and fails closed

**Date:** 2026-08-25
**Status:** Accepted

### Context
The policy kernel is the last line of defence between an LLM proposal and a financial action.
It must be auditable, reproducible, and safe under all failure modes.

### Decision
The policy kernel (`core/policy/engine.py`) has these properties:
- **Deterministic:** Given the same proposal and case state, it always produces the same
  verdict. No randomness, no external calls.
- **Versioned:** `policy.yaml` is loaded at startup and its SHA-256 hash is stored in every
  verdict record. A change to `policy.yaml` creates a new policy version.
- **Ordered:** Rules are evaluated in the order they appear in `policy.yaml`. The first
  matching rule wins.
- **Fails closed:** Any exception, parse error, unknown action type, missing field, or
  violated invariant results in `DENY`. The kernel never defaults to `ALLOW`.
- **Auditable:** Every verdict — approve, modify, block, escalate — is written to the
  append-only audit log with the matching rule name and the full proposal.

### Consequences
- Policy changes require editing `policy.yaml` under version control, making them auditable.
- Operators can block entire action classes by adding a rule to the top of `policy.yaml`.
- The fail-closed default means that a new action type introduced in code must also be
  explicitly permitted in `policy.yaml` before it can execute.

### Alternatives Rejected
- **LLM-generated policy decisions:** Non-deterministic, non-auditable. Rejected.
- **Fails open (ALLOW on error):** Unacceptable in a financial context.
- **Hard-coded Python rules only:** Rules-as-YAML allows operators to tune policy without a
  code deployment; Python enforces invariants that YAML cannot express.

---

## ADR-0007 — A virtual clock is used for time-dependent interventions

**Date:** 2026-08-25
**Status:** Accepted

### Context
Revenue-recovery interventions are time-dependent. Retrying a payment 24 hours after failure
is different from retrying 5 minutes after. Demonstrating and testing time-dependent
behaviour in real-time is impractical.

### Decision
All time-aware code reads from a **virtual clock** (`core/executor/clock.py`) rather than
`datetime.now()` or `time.time()`. The virtual clock starts at a configurable epoch and
advances at a configurable rate (default: 60× real time, making 24 simulated hours pass in
24 real minutes). In test mode, the clock can be advanced programmatically by any amount.
Scheduled actions are stored with their virtual execution timestamp; the executor checks the
virtual clock on each tick. The virtual clock state is part of the run manifest and is
reproducible from the seed.

### Consequences
- A full 7-day retry ladder can be demonstrated in ~7 minutes in demo mode.
- Tests can simulate arbitrary time sequences without `sleep()` calls.
- All production deployments must ensure the virtual clock is replaced with a real-time
  clock before connecting to live payment infrastructure.

### Alternatives Rejected
- **Mock `time.sleep()`:** Does not allow the scheduler to make decisions at arbitrary
  future times; only skips waits.
- **Real-time clock with accelerated simulation:** Requires waiting for real calendar time
  to pass during tests.

---

## ADR-0008 — Results reported only as counterfactual comparisons with confidence intervals

**Date:** 2026-08-25
**Status:** Accepted

### Context
Reporting a single recovery rate for the agent is meaningless without a baseline. An agent
that recovers 40% of failed payments sounds impressive until you learn the baseline
(do-nothing) recovers 38% — and the difference is within noise.

### Decision
Every evaluation run executes **all five strategies in parallel on identical case populations
using common random number streams** (same seeds, same environment, same case order):
1. `do_nothing` — baseline: take no action on any case.
2. `fixed_ladder` — baseline: fixed retry-once-after-24h, then email, then SMS.
3. `rules_only` — baseline: the policy kernel's rules applied without the ML model.
4. `econ_argmax` — ablation: the ENRV scorer without LLM planning.
5. `unconstrained_llm` — ablation: the LLM planner without the policy kernel (never
   executes real actions; shows what the unguarded LLM would have done).
6. `revivepay_ai` — the full system.

Uplift is reported as the **difference in ENRV** between `revivepay_ai` and each baseline,
with **bootstrap 95% confidence intervals** (1 000 resamples). A result is only highlighted
as a win if the lower bound of the CI is positive. Strategies 1–5 share the exact same
random seed as strategy 6 so environmental variance is zero.

### Consequences
- Results are honest even if RevivePay AI underperforms.
- The `unconstrained_llm` ablation quantifies the safety cost of the policy kernel.
- Bootstrap CIs require storing all per-case outcomes, not just aggregate statistics.

### Alternatives Rejected
- **Single-run point estimates:** Statistically meaningless; sampling noise dominates.
- **A/B test against live traffic:** Correct for production; not feasible in a prototype
  without a live payment system.
- **Reporting only wins:** Rejected on integrity grounds (see AGENTS.md invariants).

---

## ADR-0009 � Generic BaseRepository plus selective concrete repositories

**Date:** 2026-08-25
**Status:** Accepted

### Context
Every ORM table could have its own repository class. Doing so produces near-identical
wrappers that only forward to `session.add` / `session.get`, inflate the surface
area for review, and encourage copy-paste drift. At the same time, several aggregates
need real domain queries (open cases, legal state transitions, idempotent action insert,
hash-chained audit append, bandit posteriors) that do not belong on the ORM model or in
route handlers.

### Decision
Provide a typed generic `BaseRepository[ModelT]` with `add`, `get`, `get_or_raise`,
`list`, and `delete`. Add concrete repositories **only** for aggregates that need
domain-specific queries or invariants: Case, Transaction, Decision, Action, Outcome,
Audit, ContactLedger, BanditStats. All other models are accessed via `BaseRepository`
directly.

### Consequences
- **Positive:** Domain invariants (idempotency, state machine, audit chaining) live in one
  place and are unit-tested without HTTP.
- **Positive:** mypy infers concrete model types from the generic base.
- **Negative:** Call sites for simple tables must construct `BaseRepository(session, Model)`
  instead of a named class � accepted as clearer than empty subclasses.
- **Trade-off rejected:** One repository per table. Rejected because it adds boilerplate
  without behaviour and obscures which repositories actually encode domain rules.

### Alternatives Rejected
- **Active Record methods on models:** Couples persistence to entity definitions and makes
  the held-out / dependency-direction rules harder to enforce.
- **Anemic DAO per table:** Noise without benefit for read-by-id tables.

---

## ADR-0010 � Architecture constraints enforced as executable tests

**Date:** 2026-08-25
**Status:** Accepted

### Context
Financial-safety rules in `AGENTS.md` (held-out environment, inward model dependencies,
integer paise columns) are worthless if they only exist as prose. Documentation drifts;
import bans are easy to violate accidentally as packages appear in later phases.

### Decision
Encode the constraints in `backend/tests/test_architecture.py` as pure AST checks over
source text via `find_forbidden_imports` and mapped-column type scanning:

1. Modules under `app.policy`, `app.decision`, `app.agent`, `app.ml` must not import
   environment modules or reference `world_config`.
2. `app.models` must not import `app.services`, `app.api`, or `app.repositories`.
3. Model `mapped_column(...)` calls must not use `Float`, `Numeric`, or `Decimal`.

A **positive** test walks the real `backend/app` tree and asserts zero violations.
A **negative** test feeds synthetic source (`from app.core.environment import World` under
`app.policy.kernel`) and asserts the violation **is** detected. The negative test exists
because an architecture check that has never been observed to fail proves nothing � it may
be a no-op that always returns an empty list.

### Consequences
- Regressions fail CI even before the held-out environment package exists.
- Refactors that reintroduce float money or circular imports are caught locally with
  `pytest`.
- Authors must keep the AST helpers honest; the inverted assertion in the negative test
  documents that failure polarity was verified.

### Alternatives Rejected
- **Documentation-only bans:** Drift and silent violations.
- **Import-linter config alone:** Useful later; AST tests work before packages exist and
  cover `world_config` string references and `mapped_column` type names in one place.
