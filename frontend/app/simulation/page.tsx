'use client';

import { useState } from 'react';
import { FlaskConical, Play, CheckCircle2, Loader2, Sparkles, Shield, Brain } from 'lucide-react';
import { Card, CardHeader } from '@/components/ui/card';
import { Badge, VerdictBadge } from '@/components/ui/badge';
import { api } from '@/lib/api-client';
import { formatPaise, formatActionType, formatPercent, truncateId } from '@/lib/utils';
import type { CaseDetail, DecisionDetail } from '@/lib/types';

const PIPELINE_STAGES = [
  { label: 'Analyzing transaction', icon: FlaskConical, description: 'Validating input and checking case existence' },
  { label: 'Extracting features', icon: Brain, description: 'Computing deterministic feature vector' },
  { label: 'Evaluating risk', icon: Shield, description: 'Estimating calibrated recovery probability' },
  { label: 'Applying policy', icon: Shield, description: 'Running deterministic policy kernel checks' },
  { label: 'Generating decision', icon: Sparkles, description: 'LLM planner selecting and timing intervention' },
];

const CASE_TYPES = [
  { value: 'FAILED_PAYMENT', label: 'Failed Payment' },
  { value: 'ABANDONED_CHECKOUT', label: 'Abandoned Checkout' },
  { value: 'SUBSCRIPTION_DUNNING', label: 'Subscription Dunning' },
  { value: 'INSTRUMENT_EXPIRY', label: 'Instrument Expiry' },
];

const AMOUNT_PRESETS = [
  { value: 100000, label: '₹1,000' },
  { value: 500000, label: '₹5,000' },
  { value: 1000000, label: '₹10,000' },
  { value: 5000000, label: '₹50,000' },
];

export default function SimulationPage() {
  const [merchantId, setMerchantId] = useState('');
  const [customerId, setCustomerId] = useState('');
  const [caseType, setCaseType] = useState('FAILED_PAYMENT');
  const [amount, setAmount] = useState('500000');
  const [isRunning, setIsRunning] = useState(false);
  const [stage, setStage] = useState(-1);
  const [result, setResult] = useState<{ case: CaseDetail; decision?: DecisionDetail } | null>(null);
  const [error, setError] = useState<string | null>(null);

  const runSimulation = async () => {
    if (!merchantId || !customerId) {
      setError('Please provide Merchant ID and Customer ID');
      return;
    }

    setIsRunning(true);
    setStage(0);
    setError(null);
    setResult(null);

    try {
      // Stage 1: Create case
      const caseResult = await api.cases.create({
        merchant_id: merchantId,
        customer_id: customerId,
        case_type: caseType,
        amount_at_risk_minor: parseInt(amount) || 500000,
      });

      // Small delay to show animation
      await new Promise((r) => setTimeout(r, 600));
      setStage(1);

      // Stage 2: Fetch case detail
      const caseDetail = await api.cases.get(caseResult.id);
      await new Promise((r) => setTimeout(r, 600));
      setStage(2);

      // Stage 3: Try to get decisions
      let decision: DecisionDetail | undefined;
      try {
        const decisions = await api.decisions.list({ case_id: caseResult.id });
        if (decisions.length > 0) {
          decision = await api.decisions.get(decisions[0].id);
        }
      } catch {
        // Decisions may not exist yet
      }
      await new Promise((r) => setTimeout(r, 600));
      setStage(3);

      // Stage 4: Complete
      await new Promise((r) => setTimeout(r, 500));
      setStage(4);

      setResult({ case: caseDetail, decision });
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Simulation failed');
    } finally {
      setIsRunning(false);
      setStage(-1);
    }
  };

  const resetForm = () => {
    setMerchantId('');
    setCustomerId('');
    setCaseType('FAILED_PAYMENT');
    setAmount('500000');
    setResult(null);
    setError(null);
    setStage(-1);
  };

  return (
    <div className="space-y-6 page-enter">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-text-1">Simulation</h1>
        <p className="mt-1 text-sm text-text-3">
          Submit a payment scenario and observe the complete decision pipeline in action.
        </p>
      </div>

      <div className="grid grid-cols-1 gap-6 xl:grid-cols-2">
        {/* Input Form */}
        <Card>
          <CardHeader title="Payment Scenario" description="Configure a test case to run through the pipeline" />
          <div className="mt-5 space-y-4">
            <div>
              <label htmlFor="sim-merchant" className="block text-[10px] font-semibold uppercase tracking-wider text-text-4 mb-1.5">Merchant ID</label>
              <input
                id="sim-merchant"
                type="text"
                value={merchantId}
                onChange={(e) => setMerchantId(e.target.value)}
                placeholder="UUID of an existing merchant"
                aria-required="true"
                className="w-full rounded-lg border border-border bg-surface-2/50 px-3.5 py-2.5 text-sm text-text-1 placeholder:text-text-4 focus:border-accent focus:outline-none focus:ring-1 focus:ring-accent/20 font-mono text-[12px] transition-colors"
              />
            </div>
            <div>
              <label htmlFor="sim-customer" className="block text-[10px] font-semibold uppercase tracking-wider text-text-4 mb-1.5">Customer ID</label>
              <input
                id="sim-customer"
                type="text"
                value={customerId}
                onChange={(e) => setCustomerId(e.target.value)}
                placeholder="UUID of an existing customer"
                aria-required="true"
                className="w-full rounded-lg border border-border bg-surface-2/50 px-3.5 py-2.5 text-sm text-text-1 placeholder:text-text-4 focus:border-accent focus:outline-none focus:ring-1 focus:ring-accent/20 font-mono text-[12px] transition-colors"
              />
            </div>
            <div>
              <label htmlFor="sim-casetype" className="block text-[10px] font-semibold uppercase tracking-wider text-text-4 mb-1.5">Case Type</label>
              <select
                id="sim-casetype"
                value={caseType}
                onChange={(e) => setCaseType(e.target.value)}
                className="w-full rounded-lg border border-border bg-surface-2/50 px-3.5 py-2.5 text-sm text-text-2 focus:border-accent focus:outline-none focus:ring-1 focus:ring-accent/20 transition-colors"
              >
                {CASE_TYPES.map((ct) => (
                  <option key={ct.value} value={ct.value}>{ct.label}</option>
                ))}
              </select>
            </div>
            <div>
              <label htmlFor="sim-amount" className="block text-[10px] font-semibold uppercase tracking-wider text-text-4 mb-1.5">Amount (paise)</label>
              <div className="relative">
                <input
                  id="sim-amount"
                  type="number"
                  value={amount}
                  onChange={(e) => setAmount(e.target.value)}
                  className="w-full rounded-lg border border-border bg-surface-2/50 px-3.5 py-2.5 text-sm text-text-1 tabular focus:border-accent focus:outline-none focus:ring-1 focus:ring-accent/20 transition-colors"
                />
                <div className="absolute right-3 top-1/2 -translate-y-1/2 text-xs text-text-3 font-semibold tabular">
                  {formatPaise(parseInt(amount) || 0)}
                </div>
              </div>
              {/* Amount presets */}
              <div className="flex items-center gap-2 mt-2">
                {AMOUNT_PRESETS.map((preset) => (
                  <button
                    key={preset.value}
                    onClick={() => setAmount(String(preset.value))}
                    className={`rounded-lg border px-2.5 py-1 text-[10px] font-medium transition-all ${
                      parseInt(amount) === preset.value
                        ? 'border-accent/30 bg-accent/10 text-accent'
                        : 'border-border bg-surface-2/30 text-text-3 hover:border-border-strong hover:text-text-2'
                    }`}
                  >
                    {preset.label}
                  </button>
                ))}
              </div>
            </div>

            {error && (
              <div className="rounded-lg bg-danger/8 border border-danger/15 px-4 py-3 text-sm text-danger">
                {error}
              </div>
            )}

            <button
              onClick={runSimulation}
              disabled={isRunning || !merchantId || !customerId}
              className="w-full flex items-center justify-center gap-2.5 rounded-lg bg-accent px-4 py-3 text-sm font-semibold text-white transition-all duration-200 hover:bg-accent-hover hover:shadow-lg hover:shadow-accent/20 disabled:opacity-40 disabled:cursor-not-allowed disabled:hover:shadow-none"
            >
              {isRunning ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  Processing...
                </>
              ) : (
                <>
                  <Play className="h-4 w-4" fill="currentColor" />
                  Run Simulation
                </>
              )}
            </button>

            {result && (
              <button
                onClick={resetForm}
                className="w-full flex items-center justify-center gap-2 rounded-lg border border-border bg-surface-2/30 px-4 py-2.5 text-sm font-medium text-text-2 transition-colors hover:bg-surface-2 hover:text-text-1"
              >
                Run Another Simulation
              </button>
            )}
          </div>
        </Card>

        {/* Pipeline Progress */}
        <Card>
          <CardHeader title="Pipeline Progress" description="Decision pipeline execution stages" />
          <div className="mt-5 space-y-1.5">
            {PIPELINE_STAGES.map((pipelineStage, idx) => {
              const Icon = pipelineStage.icon;                  const isComplete = stage > idx;
                  const isCurrent = stage === idx;

              return (
                <div
                  key={idx}
                  className={`relative flex items-center gap-3.5 rounded-xl px-4 py-3.5 transition-all duration-300 ${
                    isCurrent
                      ? 'bg-accent/8 border border-accent/20 shadow-sm shadow-accent/5'
                      : isComplete
                      ? 'bg-success/5 border border-success/10'
                      : 'bg-surface-2/20 border border-transparent'
                  }`}
                >
                  {/* Step indicator */}
                  <div
                    className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-full transition-all duration-300 ${
                      isComplete
                        ? 'bg-success text-white shadow-sm glow-success'
                        : isCurrent
                        ? 'bg-accent text-white shadow-sm glow-accent'
                        : 'bg-surface-3 text-text-4'
                    }`}
                  >
                    {isComplete ? (
                      <CheckCircle2 className="h-4 w-4" />
                    ) : isCurrent ? (
                      <Loader2 className="h-4 w-4 animate-spin" />
                    ) : (
                      <Icon className="h-4 w-4" />
                    )}
                  </div>

                  {/* Content */}
                  <div className="min-w-0 flex-1">
                    <p
                      className={`text-sm ${
                        isCurrent ? 'font-semibold text-text-1' : isComplete ? 'text-success font-medium' : 'text-text-4'
                      }`}
                    >
                      {pipelineStage.label}
                    </p>
                    <p className="text-[10px] text-text-4 mt-0.5 truncate">{pipelineStage.description}</p>
                  </div>

                  {/* Connector line */}
                  {idx < PIPELINE_STAGES.length - 1 && (
                    <div className="absolute left-[34px] top-full h-1.5 w-[2px]">
                      <div className={`h-full w-full transition-colors duration-500 ${isComplete ? 'bg-success/40' : 'bg-border/40'}`} />
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </Card>
      </div>

      {/* Results */}
      {result && (
        <div className="space-y-6 animate-fade-in-up">
          {/* Case Created */}
          <Card accent>
            <div className="absolute top-0 left-0 right-0 h-[2px] bg-gradient-to-r from-success/60 via-success to-success/60" />
            <CardHeader title="Case Created" description="The payment case has been created and processed through the pipeline" />
            <div className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-4">
              <div className="rounded-xl bg-surface-2/40 border border-border/40 px-4 py-3.5 hover:border-border-strong transition-colors">
                <p className="text-[10px] font-semibold uppercase tracking-wider text-text-4">Case ID</p>
                <p className="mt-1.5 font-mono text-xs text-accent">{truncateId(result.case.id)}…</p>
              </div>
              <div className="rounded-xl bg-surface-2/40 border border-border/40 px-4 py-3.5 hover:border-border-strong transition-colors">
                <p className="text-[10px] font-semibold uppercase tracking-wider text-text-4">Amount</p>
                <p className="mt-1.5 text-base font-bold tabular text-text-1">{formatPaise(result.case.amount_at_risk_minor)}</p>
              </div>
              <div className="rounded-xl bg-surface-2/40 border border-border/40 px-4 py-3.5 hover:border-border-strong transition-colors">
                <p className="text-[10px] font-semibold uppercase tracking-wider text-text-4">State</p>
                <div className="mt-1.5"><Badge variant={result.case.state === 'DETECTED' ? 'info' : 'accent'}>{result.case.state}</Badge></div>
              </div>
              <div className="rounded-xl bg-surface-2/40 border border-border/40 px-4 py-3.5 hover:border-border-strong transition-colors">
                <p className="text-[10px] font-semibold uppercase tracking-wider text-text-4">Priority</p>
                <p className="mt-1.5 metric-number text-text-1">{result.case.priority_score?.toFixed(2) || '—'}</p>
              </div>
            </div>
          </Card>

          {/* Decision (if available) */}
          {result.decision && (
            <Card accent>
              <div className="absolute top-0 left-0 right-0 h-[2px] bg-gradient-to-r from-accent/60 via-accent to-accent/60" />
              <CardHeader title="AI Decision" description="The decision generated by the RevivePay pipeline" />
              <div className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-4">
                <div className="rounded-xl bg-surface-2/40 border border-border/40 px-4 py-3.5 hover:border-border-strong transition-colors">
                  <p className="text-[10px] font-semibold uppercase tracking-wider text-text-4">Action</p>
                  <p className="mt-1.5 text-sm font-semibold text-text-1">{formatActionType(result.decision.action_type)}</p>
                </div>
                <div className="rounded-xl bg-surface-2/40 border border-border/40 px-4 py-3.5 hover:border-border-strong transition-colors">
                  <p className="text-[10px] font-semibold uppercase tracking-wider text-text-4">Policy Verdict</p>
                  <div className="mt-1.5">
                    <VerdictBadge verdict={result.decision.policy_verdict || 'APPROVE'} />
                  </div>
                </div>
                <div className="rounded-xl bg-surface-2/40 border border-border/40 px-4 py-3.5 hover:border-border-strong transition-colors">
                  <p className="text-[10px] font-semibold uppercase tracking-wider text-text-4">LLM Provider</p>
                  <p className="mt-1.5 text-sm font-medium text-text-1">{result.decision.llm_provider}</p>
                </div>
                <div className="rounded-xl bg-surface-2/40 border border-border/40 px-4 py-3.5 hover:border-border-strong transition-colors">
                  <p className="text-[10px] font-semibold uppercase tracking-wider text-text-4">Confidence</p>
                  <p className="mt-1.5 text-sm font-bold tabular text-text-1">
                    {result.decision.llm_confidence != null ? formatPercent(result.decision.llm_confidence) : '—'}
                  </p>
                </div>
              </div>

              {result.decision.proposal_json && (
                <div className="mt-4 rounded-xl bg-surface-2/40 border border-border/40 p-4">
                  <p className="text-[10px] font-semibold uppercase tracking-wider text-text-3">LLM Proposal</p>
                  <pre className="mt-2 overflow-x-auto font-mono text-[11px] text-text-3 leading-relaxed">
                    {JSON.stringify(result.decision.proposal_json, null, 2)}
                  </pre>
                </div>
              )}
            </Card>
          )}
        </div>
      )}
    </div>
  );
}
