// RevivePay AI — TypeScript types matching backend API responses
// All monetary amounts are in paise (integer minor units)
// All UUIDs are strings

// ── Enums ──────────────────────────────────────────────────────────────────

export type CaseState =
  | 'DETECTED'
  | 'FEATURISED'
  | 'PROPOSED'
  | 'APPROVED'
  | 'BLOCKED'
  | 'ESCALATED'
  | 'SCHEDULED'
  | 'EXECUTING'
  | 'AWAITING_OUTCOME'
  | 'RECOVERED'
  | 'FAILED'
  | 'STOPPED'
  | 'EXPIRED'
  | 'CLOSED';

export type ActionType =
  | 'STOP'
  | 'RETRY_SAME_RAIL'
  | 'RETRY_ALTERNATE_RAIL'
  | 'EMAIL_NUDGE'
  | 'SMS_NUDGE'
  | 'WHATSAPP_NUDGE'
  | 'REQUEST_NEW_INSTRUMENT'
  | 'AGENT_CALL';

export type CaseType =
  | 'FAILED_PAYMENT'
  | 'ABANDONED_CHECKOUT'
  | 'SUBSCRIPTION_DUNNING'
  | 'INSTRUMENT_EXPIRY';

export type FailureClass =
  | 'INSUFFICIENT_FUNDS'
  | 'BANK_DOWNTIME'
  | 'NETWORK_TIMEOUT'
  | 'AUTH_FAILURE'
  | 'LIMIT_EXCEEDED'
  | 'RISK_DECLINE'
  | 'CARD_EXPIRED'
  | 'HARD_DECLINE'
  | 'UNKNOWN';

export type PolicyVerdict =
  | 'APPROVE'
  | 'MODIFY'
  | 'BLOCK'
  | 'ESCALATE';

export type ActionStatus =
  | 'PENDING'
  | 'EXECUTING'
  | 'EXECUTED'
  | 'FAILED'
  | 'CANCELLED'
  | 'SUPERSEDED';

export type CustomerSegment = 'NEW' | 'OCCASIONAL' | 'LOYAL' | 'HIGH_VALUE';

export type DelayBand = 'IMMEDIATE' | 'SHORT' | 'MEDIUM' | 'LONG' | 'EXTENDED';

export type Rail = 'RAIL_A' | 'RAIL_B' | 'RAIL_UPI' | 'RAIL_NETBANKING';

// ── Domain Models ──────────────────────────────────────────────────────────

export interface Merchant {
  id: string;
  name: string;
  currency: string;
  risk_appetite: string;
  max_retries_default: number;
  contact_budget_per_week: number;
  mdr_bps: number;
  autonomous_amount_ceiling_minor: number;
  created_at: string | null;
}

export interface Customer {
  id: string;
  merchant_id: string;
  email_hash: string;
  phone_hash: string;
  region: string;
  segment: CustomerSegment;
  lifetime_txn_count: number;
  lifetime_success_rate: number;
  prior_recovery_successes: number;
  prior_declines: number;
  do_not_contact: boolean;
  mandate_active: boolean;
  preferred_method: string;
  created_at: string | null;
}

export interface CustomerDetail extends Customer {
  unsubscribed_at: string | null;
  mandate_expires_at: string | null;
  consented_instruments_json: Record<string, unknown>;
}

export interface Case {
  id: string;
  merchant_id: string;
  customer_id: string;
  case_type: CaseType;
  amount_at_risk_minor: number;
  state: CaseState;
  detected_at: string | null;
  occurred_at: string | null;
}

export interface CaseDetail extends Case {
  transaction_id: string | null;
  recovery_deadline_at: string | null;
  recovered_amount_minor: number;
  closed_at: string | null;
  close_reason: string | null;
  priority_score: number;
  expected_net_value_minor: number | null;
  attempts_used: number;
  simulation_run_id: string | null;
}

export interface Decision {
  id: string;
  case_id: string;
  seq: number;
  action_type: string | null;
  policy_verdict: string | null;
  status: string | null;
  llm_provider: string;
  llm_model: string;
  llm_confidence: number | null;
  llm_self_probability: number | null;
  prompt_version: string;
  applied_rules_json: Record<string, unknown>;
  created_at: string | null;
}

export interface DecisionDetail extends Decision {
  prompt_hash: string;
  raw_llm_output: string | null;
  proposal_json: Record<string, unknown> | null;
  validation_status: string;
  validation_errors_json: Record<string, unknown>;
  policy_version: string;
  violated_rules_json: Record<string, unknown>;
  chosen_action: string | null;
  chosen_params_json: Record<string, unknown> | null;
  expected_net_value_minor: number;
  decision_latency_ms: number;
  seed: number;
  fallback_used: boolean;
}

// ── Feature Vector ─────────────────────────────────────────────────────────

export type FeatureVector = Record<string, number | boolean>;

// ── System ─────────────────────────────────────────────────────────────────

export interface HealthResponse {
  status: 'ok' | 'degraded';
  uptime_seconds: number;
  database: string;
  timestamp: string;
}

export interface VersionResponse {
  app_name: string;
  version: string;
  git_sha: string | null;
  llm_provider: string;
  environment: string;
  demo_mode: boolean;
}

export interface SystemConfig {
  APP_ENV: string;
  APP_NAME: string;
  LOG_LEVEL: string;
  API_HOST: string;
  API_PORT: number;
  FRONTEND_ORIGIN: string;
  DATABASE_URL: string;
  API_KEY_OPERATOR: string;
  API_KEY_VIEWER: string;
  LLM_PROVIDER: string;
  LLM_MODEL: string;
  LLM_TIMEOUT_SECONDS: number;
  LLM_MAX_RETRIES: number;
  GEMINI_API_KEY: string;
  OPENAI_API_KEY: string;
  ANTHROPIC_API_KEY: string;
  POLICY_FILE: string;
  ECON_CONFIG_FILE: string;
  SIM_DEFAULT_SEED: number;
  VIRTUAL_EPOCH: string;
  VIRTUAL_CLOCK_RATE: number;
  EXPECTED_CHURN_COST_MULTIPLIER: number;
  KILL_SWITCH_ENABLED: boolean;
  RATE_LIMIT_SIMULATION_PER_MIN: number;
  RAZORPAY_ADAPTER_ENABLED: boolean;
  RAZORPAY_KEY_ID: string;
  RAZORPAY_KEY_SECRET: string;
  NEXT_PUBLIC_API_BASE_URL: string;
  NEXT_PUBLIC_DEMO_MODE: boolean;
}

// ── API Error ──────────────────────────────────────────────────────────────

export interface ApiError {
  type: string;
  title: string;
  status: number;
  detail: string;
  request_id: string;
  errors?: Array<{
    field: string;
    message: string;
    type: string;
  }>;
}
