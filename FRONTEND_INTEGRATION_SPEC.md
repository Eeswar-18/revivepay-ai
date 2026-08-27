# RevivePay AI Frontend Integration Specification for Lovable

## Overview
This document specifies the backend API endpoints that Lovable should integrate with to build the RevivePay AI product frontend. The backend provides a RESTful API for managing cases, customers, merchants, and decisions in an autonomous revenue-recovery control plane.

## Backend Configuration
- **Base URL**: `http://localhost:8000` (from `NEXT_PUBLIC_API_BASE_URL` in settings)
- **Alternative Base URL**: Defined by `API_HOST` and `API_PORT` in settings (default: 127.0.0.1:8000)
- **CORS Origin**: `http://localhost:3000` (from `FRONTEND_ORIGIN` in settings)
- **Authentication**: API keys are configured but not enforced in current implementation:
  - `API_KEY_OPERATOR`: "change-me-operator-key-placeholder"
  - `API_KEY_VIEWER`: "change-me-viewer-key-placeholder"
  - Note: Current implementation does not require authentication for API access

## API Endpoints

### 1. Cases API
Manage payment failure cases that require recovery actions.

#### Base Path: `/api/cases`

| Endpoint | Method | Description | Request Schema | Response Schema |
|----------|--------|-------------|----------------|-----------------|
| `/api/cases` | GET | List cases with optional filtering and pagination | Query Parameters:<br>- `skip` (int, default 0): Number of cases to skip<br>- `limit` (int, default 100, max 1000): Maximum number of cases to return<br>- `merchant_id` (string, optional): Filter by merchant ID<br>- `customer_id` (string, optional): Filter by customer ID<br>- `case_type` (CaseType enum, optional): Filter by case type<br>- `state` (CaseState enum, optional): Filter by case state | Array of case objects:<br>```json<br>[<br>  {<br>    "id": "string (UUID)",<br>    "merchant_id": "string (UUID)",<br>    "customer_id": "string (UUID)",<br>    "case_type": "string (enum value)",<br>    "amount_at_risk_minor": "integer (paise)",<br>    "state": "string (enum value)",<br>    "detected_at": "string (ISO datetime) or null",<br>    "occurred_at": "string (ISO datetime) or null"<br>  }<br>]``` |
| `/api/cases/{case_id}` | GET | Get a specific case by ID | Path Parameter:<br>- `case_id` (string, UUID) | Case object:<br>```json<br>{<br>  "id": "string (UUID)",<br>  "transaction_id": "string (UUID) or null",<br>  "merchant_id": "string (UUID)",<br>  "customer_id": "string (UUID)",<br>  "case_type": "string (enum value)",<br>  "amount_at_risk_minor": "integer (paise)",<br>  "state": "string (enum value)",<br>  "detected_at": "string (ISO datetime) or null",<br>  "occurred_at": "string (ISO datetime) or null",<br>  "recovery_deadline_at": "string (ISO datetime) or null",<br>  "recovered_amount_minor": "integer or null",<br>  "closed_at": "string (ISO datetime) or null",<br>  "close_reason": "string or null",<br>  "priority_score": "integer or null",<br>  "expected_net_value_minor": "integer or null",<br>  "attempts_used": "integer or null",<br>  "simulation_run_id": "string (UUID) or null"<br>}``` |
| `/api/cases` | POST | Create a new case (primarily for testing/simulation) | JSON Body:<br>```json<br>{<br>  "merchant_id": "string (UUID) [required]",<br>  "customer_id": "string (UUID) [required]",<br>  "case_type": "string (enum value) [required]",<br>  "amount_at_risk_minor": "integer [required]",<br>  "state": "string (enum value, default: DETECTED)",<br>  "detected_at": "string (ISO datetime) or null",<br>  "occurred_at": "string (ISO datetime) or null",<br>  "recovery_deadline_at": "string (ISO datetime) or null",<br>  "recovered_amount_minor": "integer (default: 0)"<br>}``` | Success Response:<br>```json<br>{<br>  "id": "string (UUID)",<br>  "merchant_id": "string (UUID)",<br>  "customer_id": "string (UUID)",<br>  "case_type": "string (enum value)",<br>  "amount_at_risk_minor": "integer",<br>  "state": "string (enum value)",<br>  "detected_at": "string (ISO datetime) or null",<br>  "occurred_at": "string (ISO datetime) or null",<br>  "message": "string"<br>}``` |

#### Enums Used:
- **CaseType**: `FAILED_PAYMENT`, `CHARGEBACK`, `REFUND_ABUSE`, `PROMO_ABUSE`
- **CaseState**: `DETECTED`, `IN_PROGRESS`, `RESOLVED_SUCCESS`, `RESOLVED_FAILURE`, `EXPIRED`

### 2. Customers API
Manage customer information and profiles.

#### Base Path: `/api/customers`

| Endpoint | Method | Description | Request Schema | Response Schema |
|----------|--------|-------------|----------------|-----------------|
| `/api/customers` | GET | List customers with optional filtering and pagination | Query Parameters:<br>- `skip` (int, default 0): Number of customers to skip<br>- `limit` (int, default 100, max 1000): Maximum number of customers to return<br>- `merchant_id` (string, optional): Filter by merchant ID<br>- `segment` (CustomerSegment enum, optional): Filter by customer segment | Array of customer objects:<br>```json<br>[<br>  {<br>    "id": "string (UUID)",<br>    "merchant_id": "string (UUID)",<br>    "email_hash": "string (SHA-256 hex)",<br>    "phone_hash": "string (SHA-256 hex)",<br>    "region": "string (e.g., 'IN-MH')",<br>    "segment": "string (enum value)",<br>    "lifetime_txn_count": "integer",<br>    "lifetime_success_rate": "number (0.0-1.0)",<br>    "prior_recovery_successes": "integer",<br>    "prior_declines": "integer",<br>    "do_not_contact": "boolean",<br>    "mandate_active": "boolean",<br>    "preferred_method": "string (e.g., 'upi', 'card', 'netbanking', 'wallet')",<br>    "created_at": "string (ISO datetime) or null"<br>  }<br>]``` |
| `/api/customers/{customer_id}` | GET | Get a specific customer by ID | Path Parameter:<br>- `customer_id` (string, UUID) | Customer object:<br>```json<br>{<br>  "id": "string (UUID)",<br>  "merchant_id": "string (UUID)",<br>  "email_hash": "string (SHA-256 hex)",<br>  "phone_hash": "string (SHA-256 hex)",<br>  "region": "string",<br>  "segment": "string (enum value)",<br>  "lifetime_txn_count": "integer",<br>  "lifetime_success_rate": "number (0.0-1.0)",<br>  "prior_recovery_successes": "integer",<br>  "prior_declines": "integer",<br>  "do_not_contact": "boolean",<br>  "unsubscribed_at": "string (ISO datetime) or null",<br>  "mandate_active": "boolean",<br>  "mandate_expires_at": "string (ISO datetime) or null",<br>  "preferred_method": "string",<br>  "consented_instruments_json": "object",<br>  "created_at": "string (ISO datetime) or null"<br>}``` |
| `/api/customers` | POST | Create a new customer (primarily for testing/simulation) | JSON Body:<br>```json<br>{<br>  "merchant_id": "string (UUID) [required]",<br>  "email_hash": "string [required]",<br>  "phone_hash": "string [required]",<br>  "region": "string [required]",<br>  "segment": "string (enum value) [required]",<br>  "lifetime_txn_count": "integer (default: 0)",<br>  "lifetime_success_rate": "number (default: 0.0)",<br>  "prior_recovery_successes": "integer (default: 0)",<br>  "prior_declines": "integer (default: 0)",<br>  "do_not_contact": "boolean (default: false)",<br>  "mandate_active": "boolean (default: false)",<br>  "mandate_expires_at": "string (ISO datetime) or null",<br>  "preferred_method": "string (default: 'upi')",<br>  "consented_instruments_json": "object (default: {})"<br>}``` | Success Response:<br>```json<br>{<br>  "id": "string (UUID)",<br>  "merchant_id": "string (UUID)",<br>  "email_hash": "string",<br>  "phone_hash": "string",<br>  "region": "string",<br>  "segment": "string (enum value)",<br>  "lifetime_txn_count": "integer",<br>  "lifetime_success_rate": "number",<br>  "prior_recovery_successes": "integer",<br>  "prior_declines": "integer",<br>  "do_not_contact": "boolean",<br>  "mandate_active": "boolean",<br>  "preferred_method": "string",<br>  "message": "string"<br>}``` |

#### Enums Used:
- **CustomerSegment**: `NEW`, `OCCASIONAL`, `LOYAL`, `HIGH_VALUE`

### 3. Merchants API
Manage merchant information and configurations.

#### Base Path: `/api/merchants`

| Endpoint | Method | Description | Request Schema | Response Schema |
|----------|--------|-------------|----------------|-----------------|
| `/api/merchants` | GET | List merchants with optional filtering and pagination | Query Parameters:<br>- `skip` (int, default 0): Number of merchants to skip<br>- `limit` (int, default 100, max 1000): Maximum number of merchants to return<br>- `risk_appetite` (string, optional): Filter by risk appetite (`conservative`, `balanced`, `aggressive`) | Array of merchant objects:<br>```json<br>[<br>  {<br>    "id": "string (UUID)",<br>    "name": "string",<br>    "currency": "string (e.g., 'INR')",<br>    "risk_appetite": "string",<br>    "max_retries_default": "integer",<br>    "contact_budget_per_week": "integer (count, not money)",<br>    "mdr_bps": "integer (basis points, e.g., 200 = 2.0%)",<br>    "autonomous_amount_ceiling_minor": "integer (paise)",<br>    "created_at": "string (ISO datetime) or null"<br>  }<br>]``` |
| `/api/merchants/{merchant_id}` | GET | Get a specific merchant by ID | Path Parameter:<br>- `merchant_id` (string, UUID) | Merchant object:<br>```json<br>{<br>  "id": "string (UUID)",<br>  "name": "string",<br>  "currency": "string",<br>  "risk_appetite": "string",<br>  "max_retries_default": "integer",<br>  "contact_budget_per_week": "integer",<br>  "mdr_bps": "integer",<br>  "autonomous_amount_ceiling_minor": "integer",<br>  "created_at": "string (ISO datetime) or null"<br>}``` |
| `/api/merchants` | POST | Create a new merchant (primarily for testing/simulation) | JSON Body:<br>```json<br>{<br>  "name": "string [required]",<br>  "currency": "string [required, must be 'INR']",<br>  "risk_appetite": "string [required, one of: conservative, balanced, aggressive]",<br>  "mdr_bps": "integer [required]",<br>  "max_retries_default": "integer (default: 3)",<br>  "contact_budget_per_week": "integer (default: 10000)",<br>  "autonomous_amount_ceiling_minor": "integer (default: 1000000)"<br>}``` | Success Response:<br>```json<br>{<br>  "id": "string (UUID)",<br>  "name": "string",<br>  "currency": "string",<br>  "risk_appetite": "string",<br>  "max_retries_default": "integer",<br>  "contact_budget_per_week": "integer",<br>  "mdr_bps": "integer",<br>  "autonomous_amount_ceiling_minor": "integer",<br>  "created_at": "string (ISO datetime) or null",<br>  "message": "string"<br>}``` |

### 4. Decisions API
Manage decisions made for cases through the autonomous pipeline.

#### Base Path: `/api/decisions`

| Endpoint | Method | Description | Request Schema | Response Schema |
|----------|--------|-------------|----------------|-----------------|
| `/api/decisions` | GET | List decisions with optional filtering and pagination | Query Parameters:<br>- `skip` (int, default 0): Number of decisions to skip<br>- `limit` (int, default 100, max 1000): Maximum number of decisions to return<br>- `case_id` (string, optional): Filter by case ID<br>- `action_type` (ActionType enum, optional): Filter by action type<br>- `policy_verdict` (PolicyVerdict enum, optional): Filter by policy verdict<br>- `status` (ActionStatus enum, optional): Filter by action status | Array of decision objects:<br>```json<br>[<br>  {<br>    "id": "string (UUID)",<br>    "case_id": "string (UUID)",<br>    "seq": "integer",<br>    "action_type": "string (enum value)",<br>    "policy_verdict": "string (enum value)",<br>    "status": "string (enum value)",<br>    "llm_provider": "string",<br>    "llm_model": "string",<br>    "llm_confidence": "number",<br>    "llm_self_probability": "number",<br>    "prompt_version": "string",<br>    "applied_rules_json": "object",<br>    "created_at": "string (ISO datetime) or null"<br>  }<br>]``` |
| `/api/decisions/{decision_id}` | GET | Get a specific decision by ID | Path Parameter:<br>- `decision_id` (string, UUID) | Decision object:<br>```json<br>{<br>  "id": "string (UUID)",<br>  "case_id": "string (UUID)",<br>  "seq": "integer",<br>  "action_type": "string (enum value)",<br>  "policy_verdict": "string (enum value)",<br>  "status": "string (enum value)",<br>  "llm_provider": "string",<br>  "llm_model": "string",<br>  "llm_confidence": "number",<br>  "llm_self_probability": "number",<br>  "prompt_version": "string",<br>  "prompt_hash": "string (64 hex chars)",<br>  "raw_llm_output": "string",<br>  "proposal_json": "object",<br>  "validation_status": "string",<br>  "validation_errors_json": "object",<br>  "policy_version": "string",<br>  "applied_rules_json": "object",<br>  "violated_rules_json": "object",<br>  "chosen_action": "string (enum value)",<br>  "chosen_params_json": "object",<br>  "expected_net_value_minor": "integer or null",<br>  "decision_latency_ms": "integer or null",<br>  "seed": "integer or null",<br>  "fallback_used": "boolean or null",<br>  "created_at": "string (ISO datetime) or null"<br>}``` |
| `/api/decisions` | POST | Create a new decision (primarily for testing/simulation) | JSON Body:<br>```json<br>{<br>  "case_id": "string (UUID) [required]",<br>  "action_type": "string (enum value) [required]",<br>  "policy_verdict": "string (enum value) or null",<br>  "status": "string (enum value) or null",<br>  "llm_provider": "string (default: 'mock')",<br>  "llm_model": "string (default: 'mock-v1')",<br>  "llm_confidence": "number (default: 0.0)",<br>  "llm_self_probability": "number (default: 0.0)",<br>  "prompt_version": "string (default: 'p1')",<br>  "prompt_hash": "string (default: 'a'*64)",<br>  "raw_llm_output": "string (default: '')",<br>  "proposal_json": "object (default: {})",<br>  "validation_errors_json": "object (default: {})",<br>  "policy_version": "string (default: 'pol-v1')",<br>  "applied_rules_json": "object (default: {})",<br>  "violated_rules_json": "object (default: {})",<br>  "chosen_params_json": "object (default: {})",<br>  "expected_net_value_minor": "integer or null",<br>  "decision_latency_ms": "integer (default: 0)",<br>  "seed": "integer or null",<br>  "fallback_used": "boolean (default: false)"<br>}``` | Success Response:<br>```json<br>{<br>  "id": "string (UUID)",<br>  "case_id": "string (UUID)",<br>  "seq": "integer",<br>  "action_type": "string (enum value)",<br>  "policy_verdict": "string (enum value)",<br>  "status": "string (enum value)",<br>  "llm_provider": "string",<br>  "llm_model": "string",<br>  "message": "string"<br>}``` |

#### Enums Used:
- **ActionType**: `STOP`, `RETRY_SAME_RAIL`, `RETRY_ALTERNATE_RAIL`, `AGENT_CALL`, `ESCALATE_HUMAN`, `NO_ACTION_WAIT`
- **PolicyVerdict**: `APPROVE`, `MODIFY`, `BLOCK`, `ESCALATE`
- **ActionStatus**: `PENDING`, `VALID`, `INVALID`, `EXECUTED`, `FAILED`

### 5. Features API
Compute features for cases (used internally by the decision pipeline).

#### Base Path: `/api/features`

| Endpoint | Method | Description | Request Schema | Response Schema |
|----------|--------|-------------|----------------|-----------------|
| `/api/features/{case_id}` | GET | Compute features for a specific case | Path Parameter:<br>- `case_id` (string, UUID) | Feature object:<br>```json<br>{<br>  "case_id": "string (UUID)",<br>  "features": {<br>    // Dynamic feature names and values<br>    // Examples based on implementation:<br>    "amount_at_risk_log": "number",<br>    "customer_lifetime_value": "number",<br>    "merchant_risk_score": "number"<br>  }<br>}``` |

### 6. System Endpoints
Health check, version, and configuration endpoints.

#### Base Path: `/api`

| Endpoint | Method | Description | Request Schema | Response Schema |
|----------|--------|-------------|----------------|-----------------|
| `/api/health` | GET | Health check | None | ```json<br>{<br>  "status": "string ('ok' or 'degraded')",<br>  "uptime_seconds": "number",<br>  "database": "string ('ok' or 'error')",<br>  "timestamp": "string (ISO datetime)"<br>}``` |
| `/api/version` | GET | Application version | None | ```json<br>{<br>  "app_name": "string",<br>  "version": "string",<br>  "git_sha": "string or null",<br>  "llm_provider": "string",<br>  "environment": "string",<br>  "demo_mode": "boolean"<br>}``` |
| `/api/system/config` | GET | Redacted configuration (safe for sharing) | None | ```json<br>{<br>  // All settings with secrets masked<br>  "APP_ENV": "string",<br>  "APP_NAME": "string",<br>  "LOG_LEVEL": "string",<br>  "API_HOST": "string",<br>  "API_PORT": "integer",<br>  // ... all other settings with secrets replaced by "set"/"unset"<br>}``` |

## Main User Flow

The primary user flow for submitting a case and receiving a decision through the autonomous pipeline:

1. **Case Creation**: 
   - Frontend sends POST request to `/api/cases` with case details
   - Backend creates and stores the case, returns case ID

2. **Case Retrieval**:
   - Frontend periodically polls GET `/api/cases/{case_id}` to check case status
   - Alternatively, frontend can list all cases via GET `/api/cases`

3. **Decision Pipeline Trigger** (Internal):
   - When a case is in DETECTED state, the backend automatically triggers the decision pipeline
   - This involves: feature extraction → failure classification → candidate generation → risk modeling → LLM planning → policy validation → final decision

4. **Decision Retrieval**:
   - Frontend retrieves decisions via GET `/api/decisions?case_id={case_id}`
   - Decision includes: chosen action, policy verdict, expected net value, justification

5. **Case Update**:
   - Based on the decision, the case state is updated (e.g., to IN_PROGRESS)
   - Frontend can monitor case state changes via the cases API

## Environment Variables for Lovable

Lovable will need to configure these environment variables to connect to the backend:

```
# Backend Connection
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000

# Feature Flags
NEXT_PUBLIC_DEMO_MODE=true

# Optional: Override CORS if needed
# (Typically not needed as backend is configured for localhost:3000)
```

## Data Types and Formats

- **UUIDs**: Standard UUID v4 format as strings (e.g., "123e4567-e89b-12d3-a456-426614174000")
- **Timestamps**: ISO 8601 format strings (e.g., "2026-08-27T10:30:00Z") or null
- **Monetary Amounts**: Integer values in paise (1/100th of a rupee)
  - Example: ₹150.50 = 15050 paise
- **Percentages/Rates**: 
  - Basis points (bps): Integer where 100 bps = 1.0%
  - Success rates: Decimal between 0.0 and 1.0
- **Hashes**: SHA-256 as 64-character hexadecimal strings

## Error Responses

Standard error responses follow this format:

```json
{
  "detail": "string describing the error"
}
```

Common HTTP status codes:
- 400: Bad Request (validation errors)
- 404: Not Found (resource doesn't exist)
- 500: Internal Server Error

## Implementation Notes for Lovable

1. **Real-time Updates**: Consider implementing polling (every 5-10 seconds) to check for case/status updates since the backend doesn't currently support WebSockets for real-time notifications.

2. **Error Handling**: Implement proper error handling for API calls, displaying user-friendly messages based on the error detail.

3. **Loading States**: Show loading indicators during API requests.

4. **Data Transformation**: Transform API responses as needed for UI presentation (e.g., formatting timestamps, converting paise to rupee display).

5. **Security Note**: While API keys are configured in the backend, the current implementation does not enforce authentication. If authentication is added in the future, Lovable would need to include API keys in request headers.

6. **Demo Mode**: The backend runs in demo mode where all payment effects are simulated - no real money movement occurs.

## API Contract Stability

The backend APIs described above represent the current stable interface. Lovable can rely on these endpoints for building the frontend interface. Any future changes to the API will maintain backward compatibility where possible.