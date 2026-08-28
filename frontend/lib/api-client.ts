// RevivePay AI — Centralized API client

import type {
  Case,
  CaseDetail,
  Customer,
  CustomerDetail,
  Merchant,
  Decision,
  DecisionDetail,
  FeatureVector,
  HealthResponse,
  VersionResponse,
  SystemConfig,
  ApiError,
} from './types';

// When NEXT_PUBLIC_API_BASE_URL is set, use it directly (e.g. for SSR or testing).
// Otherwise, use a relative path so requests go through the Next.js rewrite proxy,
// which forwards them to the backend and avoids CORS issues in the browser.
const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || '';

// ── Error handling ─────────────────────────────────────────────────────────

export class ApiRequestError extends Error {
  status: number;
  detail: string;
  requestId: string;

  constructor(error: ApiError) {
    super(error.detail);
    this.name = 'ApiRequestError';
    this.status = error.status;
    this.detail = error.detail;
    this.requestId = error.request_id;
  }
}

// ── Generic fetcher ────────────────────────────────────────────────────────

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const url = `${API_BASE}${path}`;
  const res = await fetch(url, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
  });

  if (!res.ok) {
    let errorBody: ApiError;
    try {
      errorBody = await res.json();
    } catch {
      errorBody = {
        type: 'about:blank',
        title: 'Request Failed',
        status: res.status,
        detail: res.statusText || 'An unexpected error occurred',
        request_id: res.headers.get('X-Request-Id') || 'unknown',
      };
    }
    throw new ApiRequestError(errorBody);
  }

  // Handle 204 No Content
  if (res.status === 204) return undefined as T;

  return res.json();
}

// ── System endpoints ───────────────────────────────────────────────────────

export const api = {
  health: () => request<HealthResponse>('/api/health'),
  version: () => request<VersionResponse>('/api/version'),
  config: () => request<SystemConfig>('/api/system/config'),

  // ── Cases ──────────────────────────────────────────────────────────────
  cases: {
    list: (params?: {
      skip?: number;
      limit?: number;
      merchant_id?: string;
      customer_id?: string;
      case_type?: string;
      state?: string;
    }) => {
      const searchParams = new URLSearchParams();
      if (params?.skip !== undefined) searchParams.set('skip', String(params.skip));
      if (params?.limit !== undefined) searchParams.set('limit', String(params.limit));
      if (params?.merchant_id) searchParams.set('merchant_id', params.merchant_id);
      if (params?.customer_id) searchParams.set('customer_id', params.customer_id);
      if (params?.case_type) searchParams.set('case_type', params.case_type);
      if (params?.state) searchParams.set('state', params.state);
      const qs = searchParams.toString();
      return request<Case[]>(`/api/cases${qs ? `?${qs}` : ''}`);
    },
    get: (id: string) => request<CaseDetail>(`/api/cases/${id}`),
    create: (data: {
      merchant_id: string;
      customer_id: string;
      case_type: string;
      amount_at_risk_minor: number;
      state?: string;
      detected_at?: string;
      occurred_at?: string;
      recovery_deadline_at?: string;
      recovered_amount_minor?: number;
    }) =>
      request<{ id: string; message: string } & Record<string, unknown>>('/api/cases', {
        method: 'POST',
        body: JSON.stringify(data),
      }),
  },

  // ── Customers ──────────────────────────────────────────────────────────
  customers: {
    list: (params?: {
      skip?: number;
      limit?: number;
      merchant_id?: string;
      segment?: string;
    }) => {
      const searchParams = new URLSearchParams();
      if (params?.skip !== undefined) searchParams.set('skip', String(params.skip));
      if (params?.limit !== undefined) searchParams.set('limit', String(params.limit));
      if (params?.merchant_id) searchParams.set('merchant_id', params.merchant_id);
      if (params?.segment) searchParams.set('segment', params.segment);
      const qs = searchParams.toString();
      return request<Customer[]>(`/api/customers${qs ? `?${qs}` : ''}`);
    },
    get: (id: string) => request<CustomerDetail>(`/api/customers/${id}`),
  },

  // ── Merchants ──────────────────────────────────────────────────────────
  merchants: {
    list: (params?: { skip?: number; limit?: number; risk_appetite?: string }) => {
      const searchParams = new URLSearchParams();
      if (params?.skip !== undefined) searchParams.set('skip', String(params.skip));
      if (params?.limit !== undefined) searchParams.set('limit', String(params.limit));
      if (params?.risk_appetite) searchParams.set('risk_appetite', params.risk_appetite);
      const qs = searchParams.toString();
      return request<Merchant[]>(`/api/merchants${qs ? `?${qs}` : ''}`);
    },
    get: (id: string) => request<Merchant>(`/api/merchants/${id}`),
  },

  // ── Decisions ──────────────────────────────────────────────────────────
  decisions: {
    list: (params?: {
      skip?: number;
      limit?: number;
      case_id?: string;
      action_type?: string;
      policy_verdict?: string;
      status?: string;
    }) => {
      const searchParams = new URLSearchParams();
      if (params?.skip !== undefined) searchParams.set('skip', String(params.skip));
      if (params?.limit !== undefined) searchParams.set('limit', String(params.limit));
      if (params?.case_id) searchParams.set('case_id', params.case_id);
      if (params?.action_type) searchParams.set('action_type', params.action_type);
      if (params?.policy_verdict) searchParams.set('policy_verdict', params.policy_verdict);
      if (params?.status) searchParams.set('status', params.status);
      const qs = searchParams.toString();
      return request<Decision[]>(`/api/decisions${qs ? `?${qs}` : ''}`);
    },
    get: (id: string) => request<DecisionDetail>(`/api/decisions/${id}`),
  },

  // ── Features ───────────────────────────────────────────────────────────
  features: {
    get: (caseId: string) => request<FeatureVector>(`/api/features/${caseId}`),
  },
};
