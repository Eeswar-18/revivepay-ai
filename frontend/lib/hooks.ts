// RevivePay AI — TanStack Query hooks for all API resources

'use client';

import { useQuery } from '@tanstack/react-query';
import { api, ApiRequestError } from './api-client';

// ── System ─────────────────────────────────────────────────────────────────

export function useHealth() {
  return useQuery({
    queryKey: ['health'],
    queryFn: api.health,
    refetchInterval: 30_000,
    retry: 3,
  });
}

export function useVersion() {
  return useQuery({
    queryKey: ['version'],
    queryFn: api.version,
    staleTime: 60_000,
  });
}

// ── Cases ──────────────────────────────────────────────────────────────────

export function useCases(params?: {
  skip?: number;
  limit?: number;
  merchant_id?: string;
  customer_id?: string;
  case_type?: string;
  state?: string;
}) {
  return useQuery({
    queryKey: ['cases', params],
    queryFn: () => api.cases.list(params),
  });
}

export function useCase(id: string | null) {
  return useQuery({
    queryKey: ['cases', id],
    queryFn: () => api.cases.get(id!),
    enabled: !!id,
  });
}

// ── Customers ──────────────────────────────────────────────────────────────

export function useCustomers(params?: {
  skip?: number;
  limit?: number;
  merchant_id?: string;
  segment?: string;
}) {
  return useQuery({
    queryKey: ['customers', params],
    queryFn: () => api.customers.list(params),
  });
}

export function useCustomer(id: string | null) {
  return useQuery({
    queryKey: ['customers', id],
    queryFn: () => api.customers.get(id!),
    enabled: !!id,
  });
}

// ── Merchants ──────────────────────────────────────────────────────────────

export function useMerchants(params?: {
  skip?: number;
  limit?: number;
  risk_appetite?: string;
}) {
  return useQuery({
    queryKey: ['merchants', params],
    queryFn: () => api.merchants.list(params),
  });
}

export function useMerchant(id: string | null) {
  return useQuery({
    queryKey: ['merchants', id],
    queryFn: () => api.merchants.get(id!),
    enabled: !!id,
  });
}

// ── Decisions ──────────────────────────────────────────────────────────────

export function useDecisions(params?: {
  skip?: number;
  limit?: number;
  case_id?: string;
  action_type?: string;
  policy_verdict?: string;
  status?: string;
}) {
  return useQuery({
    queryKey: ['decisions', params],
    queryFn: () => api.decisions.list(params),
  });
}

export function useDecision(id: string | null) {
  return useQuery({
    queryKey: ['decisions', id],
    queryFn: () => api.decisions.get(id!),
    enabled: !!id,
  });
}

// ── Features ───────────────────────────────────────────────────────────────

export function useFeatures(caseId: string | null) {
  return useQuery({
    queryKey: ['features', caseId],
    queryFn: () => api.features.get(caseId!),
    enabled: !!caseId,
  });
}
