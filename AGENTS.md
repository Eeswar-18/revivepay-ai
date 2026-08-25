# AGENTS.md — RevivePay AI Engineering Operating Contract

This file is the permanent operating contract for all engineering work on this repository.
**Re-read this file in full at the start of every phase before touching any code.**

---

## How to Work

Read STATUS.md before starting any work, and update STATUS.md before reporting a task complete.

### Repository-first discipline
- **Inspect before you write.** Before creating or editing any file, run a recursive listing
  of the relevant directories and read any existing module, type, component or utility that
  relates to your task. Print a short inventory of what already exists and state explicitly
  what you will change and what you will leave untouched.
- **Extend, never replace.** If a file already exists, add to it or modify it. If deletion is
  genuinely required, print the reason first, then delete.
- **Reuse before you create.** Before writing a new helper, schema, type or utility, search
  the codebase for an existing implementation. Do not create a second implementation of
  anything that already exists.

### Delivery standards
- **Implement completely.** Every phase must be fully implemented as described. Never leave
  `TODO`, `FIXME`, `pass  # implement later`, `raise NotImplementedError`, commented-out
  stubs, or placeholder return values in delivered code. A phase is not done until the code
  actually does what the spec says.
- **Keep existing behaviour.** Never replace working functionality to make your own change
  easier. If a genuine refactor is required, perform it in a separate, clearly-announced step
  and keep all existing tests green throughout.
- **Test what you ship.** Every new behaviour introduced in a phase must have accompanying
  tests. Tests must pass before you declare the phase complete.
- **Run the full verification suite after every phase:** `make verify` (lint, type-check,
  unit tests, frontend build). Fix every error you introduced before declaring done. If a
  pre-existing failure is unrelated to your changes, report it explicitly and separately —
  do not silently ignore it.

### Communication rules
- **Stop only when genuinely blocked.** Do not stop to ask permission for work that this
  contract already authorises. The only legitimate blocking reasons are a missing external
  credential that is genuinely required, or a design decision that the spec leaves genuinely
  ambiguous and that will cause irreversible work to be undone.
- **Documentation is code.** Update `ARCHITECTURE.md` and `DECISIONS.md` in the same phase
  in which you change architecture or add a major decision. Documentation drift is a defect.

---

## Financial-Safety Invariants

These rules are **non-negotiable** and apply to every line of code in this repository,
regardless of phase, author or urgency.

### LLM containment
- [ ] An LLM output must never reach a payment execution path without passing, **in order**:
      (1) JSON-schema / Pydantic validation, (2) enum and range checks,
      (3) feature-citation verification, (4) the deterministic policy kernel.
- [ ] The policy kernel is the sole authority on whether an action executes. It **fails
      closed**: unknown action types, unparseable proposals, missing context, or any internal
      error result in `DENY`, never `ALLOW`.

### Amount immutability
- [ ] A recovery action may **never** change the amount, currency, customer, or merchant of
      the original at-risk transaction. Any attempt must be rejected by the policy kernel.

### Idempotency
- [ ] Every executable action carries a **deterministic idempotency key** with a database
      uniqueness constraint. Re-running the same logical action must never produce a second
      financial effect.

### Metrics integrity
- [ ] No evaluation metric may be hard-coded, seeded with flattering constants, or computed
      from anything other than actual run outputs. If a metric cannot be computed, the system
      must display an explicit empty state — never a made-up number.
- [ ] Never claim, in code, UI, logs or documentation, that the system is integrated with
      Razorpay production. All payment effects are **simulated** unless a clearly
      feature-flagged test-mode adapter is explicitly enabled. Simulated or test data must be
      visibly labelled in the UI.

### Environment hold-out
- [ ] Ground-truth environment parameters are held out. No module under `core/features`,
      `core/risk_model`, `core/econ`, `core/llm`, or `core/policy` may import from
      `core/environment` or read `world_config.yaml`. This constraint is enforced by an
      architecture test that runs in CI.

### Secret hygiene
- [ ] All secrets come from environment variables only.
- [ ] Never commit a real key. `.env` is git-ignored; only `.env.example` is committed, with
      placeholder values.
- [ ] Never log or print a secret in any error message, stack trace or debug output.

### Personal data
- [ ] No real personal data. Customer identifiers are synthetic. Emails and phone numbers are
      stored hashed and displayed masked in all interfaces.

---

## Definition of Done for Every Phase

A phase is **complete** only when every item in this checklist is satisfied:

- [ ] Code implements the described behaviour with no placeholders.
- [ ] Tests exist for the phase's new behaviour and all pass (`pytest`).
- [ ] Lint passes with zero errors (`ruff check`).
- [ ] Format passes (`ruff format --check`).
- [ ] Type-check passes with zero errors (`mypy backend/`).
- [ ] Backend starts without errors (`uvicorn app.main:app`).
- [ ] Frontend builds without errors (`npm run build` inside `frontend/`).
- [ ] `ARCHITECTURE.md` and `DECISIONS.md` reflect the state of the codebase after this phase.
- [ ] `README.md` is updated if any user-facing behaviour changed.
- [ ] A **completion report** is printed containing:
      - What was created.
      - What was changed (and why).
      - What was deliberately **not** done (and why, if non-obvious).
      - The exact commands a reviewer can run to verify the phase.

---

## Phase Registry

| Phase | Title | Status |
|-------|-------|--------|
| 0 | Repository scaffold & architecture of record | ✅ Complete |
| 1–17 | (to be defined) | 🔲 Not started |
