/**
 * IMRaD Section Gate Service
 * ──────────────────────────
 * Enforces the "verify-after-write" quality gate for every manuscript section.
 *
 * Flow (per section):
 *   1. Writer agent produces { sectionMarkdown, claimsWithEvidence[] }
 *   2. This gate service extracts the claim strings from claimsWithEvidence
 *   3. Dispatches them to agent-verify (CLAIM_VERIFY) with the grounding pack
 *   4. Blocks progression if overallPass === false (LIVE mode)
 *      or emits warnings (DEMO mode)
 *
 * Integration point:
 *   Called from manuscript-generation.ts after each section-write dispatch.
 */

import { logAction } from './audit-service';

// ──────────────────────────────────────────────
// Types
// ──────────────────────────────────────────────

/** Shape returned by every section writer agent's outputs. */
export interface SectionWriterOutput {
  sectionMarkdown: string;
  claimsWithEvidence: ClaimWithEvidence[];
  warnings?: string[];
  overallPass: boolean;
}

export interface ClaimWithEvidence {
  claim: string;
  evidence_refs: Array<{ chunk_id: string; doc_id: string }>;
}

export interface ClaimVerdict {
  claim: string;
  verdict: 'pass' | 'fail' | 'unclear';
  evidence: Array<{ chunkId: string; quote: string }>;
}

export interface VerifyGateResult {
  /** True when all claims verified pass (or DEMO mode override). */
  gatePass: boolean;
  /** The section markdown (unchanged). */
  sectionMarkdown: string;
  /** Claims list as returned by the writer. */
  claimsWithEvidence: ClaimWithEvidence[];
  /** Per-claim verdicts from agent-verify. */
  claimVerdicts: ClaimVerdict[];
  /** Human-readable warnings. */
  warnings: string[];
  /** Whether the gate blocked progression. */
  blocked: boolean;
  /** The governance mode used. */
  governanceMode: 'LIVE' | 'DEMO';
  /** Section name (e.g. introduction, methods, …). */
  section: string;
}

// ──────────────────────────────────────────────
// Agent dispatch helpers
// ──────────────────────────────────────────────

function agentEndpoints(): Record<string, string> {
  const raw = process.env.AGENT_ENDPOINTS_JSON;
  if (!raw) return {};
  try {
    return JSON.parse(raw);
  } catch {
    return {};
  }
}

async function dispatchVerifyAgent(
  claims: string[],
  groundingPack: Record<string, unknown>,
  governanceMode: string,
  requestId: string,
): Promise<{ claimVerdicts: ClaimVerdict[]; overallPass: boolean }> {
  const endpoints = agentEndpoints();
  const agentUrl = endpoints['agent-verify'];

  if (!agentUrl) {
    // No verify agent configured — fail-closed in LIVE, pass in DEMO
    const failClosed = governanceMode === 'LIVE';
    return {
      claimVerdicts: claims.map((c) => ({
        claim: c,
        verdict: 'unclear' as const,
        evidence: [],
      })),
      overallPass: !failClosed,
    };
  }

  const payload = {
    request_id: `verify-${requestId}`,
    task_type: 'CLAIM_VERIFY',
    mode: governanceMode,
    inputs: {
      claims,
      groundingPack,
      governanceMode,
    },
  };

  const token = process.env.WORKER_SERVICE_TOKEN || '';
  const headers: Record<string, string> = { 'Content-Type': 'application/json' };
  if (token) headers['Authorization'] = `Bearer ${token}`;

  const resp = await fetch(`${agentUrl}/agents/run/sync`, {
    method: 'POST',
    headers,
    body: JSON.stringify(payload),
  });

  if (!resp.ok) {
    const text = await resp.text().catch(() => '');
    throw new Error(`agent-verify returned ${resp.status}: ${text}`);
  }

  const data = (await resp.json()) as {
    outputs?: {
      claim_verdicts?: ClaimVerdict[];
      overallPass?: boolean;
    };
  };

  return {
    claimVerdicts: data.outputs?.claim_verdicts ?? [],
    overallPass: data.outputs?.overallPass ?? false,
  };
}

// ──────────────────────────────────────────────
// Main gate function
// ──────────────────────────────────────────────

/**
 * Run the verify-after-write quality gate for one section.
 *
 * @param section        - e.g. "introduction", "methods", "results", "discussion"
 * @param writerOutput   - Output envelope from the section writer agent
 * @param groundingPack  - The grounding pack used for writing
 * @param governanceMode - LIVE or DEMO
 * @param requestId      - Trace request ID
 * @param userId         - For audit logging
 * @param manuscriptId   - For audit logging
 *
 * @returns VerifyGateResult
 *
 * Behaviour:
 *   1. Writer-side check: if writerOutput.overallPass is already false and mode=LIVE,
 *      gate immediately blocks (writer's own evidence grounding failed).
 *   2. Verification agent check: extracts claim strings → dispatches to agent-verify.
 *   3. LIVE: overallPass must be true to proceed. If false → blocked=true.
 *   4. DEMO: warnings emitted but blocked=false.
 */
export async function runSectionVerifyGate(
  section: string,
  writerOutput: SectionWriterOutput,
  groundingPack: Record<string, unknown>,
  governanceMode: 'LIVE' | 'DEMO',
  requestId: string,
  userId?: string,
  manuscriptId?: string,
): Promise<VerifyGateResult> {
  const warnings: string[] = [...(writerOutput.warnings ?? [])];

  // ── Step 1: Writer-side evidence grounding check ──────────────
  if (!writerOutput.overallPass && governanceMode === 'LIVE') {
    const result: VerifyGateResult = {
      gatePass: false,
      sectionMarkdown: writerOutput.sectionMarkdown,
      claimsWithEvidence: writerOutput.claimsWithEvidence,
      claimVerdicts: [],
      warnings: [
        ...warnings,
        `[GATE BLOCKED] Section "${section}" writer returned overallPass=false — ` +
          `claims lack evidence grounding. Section cannot proceed in LIVE mode.`,
      ],
      blocked: true,
      governanceMode,
      section,
    };

    await logGateEvent(result, userId, manuscriptId, requestId);
    return result;
  }

  // ── Step 2: Extract claim strings for verification ────────────
  const claimStrings = (writerOutput.claimsWithEvidence ?? [])
    .map((c) => c.claim)
    .filter((c) => c && c.trim());

  if (claimStrings.length === 0) {
    // No claims to verify — pass if writer passed, warn otherwise
    const noClaimsPass = governanceMode !== 'LIVE';
    const result: VerifyGateResult = {
      gatePass: writerOutput.overallPass || noClaimsPass,
      sectionMarkdown: writerOutput.sectionMarkdown,
      claimsWithEvidence: writerOutput.claimsWithEvidence,
      claimVerdicts: [],
      warnings: [
        ...warnings,
        governanceMode === 'LIVE'
          ? `[GATE BLOCKED] Section "${section}" produced no verifiable claims. LIVE mode requires claims with evidence.`
          : `[GATE WARNING] Section "${section}" produced no verifiable claims.`,
      ],
      blocked: governanceMode === 'LIVE' && !writerOutput.overallPass,
      governanceMode,
      section,
    };

    await logGateEvent(result, userId, manuscriptId, requestId);
    return result;
  }

  // ── Step 3: Dispatch to agent-verify ──────────────────────────
  let verifyResult: { claimVerdicts: ClaimVerdict[]; overallPass: boolean };
  try {
    verifyResult = await dispatchVerifyAgent(
      claimStrings,
      groundingPack,
      governanceMode,
      requestId,
    );
  } catch (err) {
    // Verify agent unreachable — fail-closed in LIVE, warn in DEMO
    const errMsg = err instanceof Error ? err.message : String(err);
    if (governanceMode === 'LIVE') {
      const result: VerifyGateResult = {
        gatePass: false,
        sectionMarkdown: writerOutput.sectionMarkdown,
        claimsWithEvidence: writerOutput.claimsWithEvidence,
        claimVerdicts: [],
        warnings: [
          ...warnings,
          `[GATE BLOCKED] agent-verify unreachable for section "${section}" in LIVE mode: ${errMsg}`,
        ],
        blocked: true,
        governanceMode,
        section,
      };
      await logGateEvent(result, userId, manuscriptId, requestId);
      return result;
    }

    // DEMO: proceed with warning
    const result: VerifyGateResult = {
      gatePass: true,
      sectionMarkdown: writerOutput.sectionMarkdown,
      claimsWithEvidence: writerOutput.claimsWithEvidence,
      claimVerdicts: [],
      warnings: [
        ...warnings,
        `[GATE WARNING] agent-verify unreachable for section "${section}" (DEMO — proceeding): ${errMsg}`,
      ],
      blocked: false,
      governanceMode,
      section,
    };
    await logGateEvent(result, userId, manuscriptId, requestId);
    return result;
  }

  // ── Step 4: Evaluate verdicts ─────────────────────────────────
  const failedClaims = verifyResult.claimVerdicts.filter(
    (v) => v.verdict === 'fail' || v.verdict === 'unclear',
  );
  const verifyPassed = verifyResult.overallPass;

  if (!verifyPassed && failedClaims.length > 0) {
    for (const fc of failedClaims) {
      warnings.push(
        `[VERIFY ${fc.verdict.toUpperCase()}] "${fc.claim.slice(0, 100)}…"`,
      );
    }
  }

  const blocked = governanceMode === 'LIVE' && !verifyPassed;

  if (blocked) {
    warnings.push(
      `[GATE BLOCKED] Section "${section}" failed claim verification — ` +
        `${failedClaims.length}/${claimStrings.length} claims did not pass. ` +
        `Progression blocked in LIVE mode.`,
    );
  } else if (!verifyPassed && governanceMode === 'DEMO') {
    warnings.push(
      `[GATE WARNING] Section "${section}" has ${failedClaims.length} unverified claims ` +
        `(DEMO mode — proceeding).`,
    );
  }

  const result: VerifyGateResult = {
    gatePass: verifyPassed || governanceMode === 'DEMO',
    sectionMarkdown: writerOutput.sectionMarkdown,
    claimsWithEvidence: writerOutput.claimsWithEvidence,
    claimVerdicts: verifyResult.claimVerdicts,
    warnings,
    blocked,
    governanceMode,
    section,
  };

  await logGateEvent(result, userId, manuscriptId, requestId);
  return result;
}

// ──────────────────────────────────────────────
// Audit helper
// ──────────────────────────────────────────────

async function logGateEvent(
  result: VerifyGateResult,
  userId?: string,
  manuscriptId?: string,
  requestId?: string,
): Promise<void> {
  try {
    await logAction({
      eventType: result.blocked ? 'SECTION_GATE_BLOCKED' : 'SECTION_GATE_PASSED',
      action: 'VERIFY_GATE',
      resourceType: 'MANUSCRIPT_SECTION',
      resourceId: manuscriptId || 'unknown',
      userId: userId || 'system',
      details: {
        section: result.section,
        governanceMode: result.governanceMode,
        gatePass: result.gatePass,
        blocked: result.blocked,
        totalClaims: result.claimsWithEvidence.length,
        verifiedClaims: result.claimVerdicts.length,
        failedClaims: result.claimVerdicts.filter(
          (v) => v.verdict !== 'pass',
        ).length,
        warningCount: result.warnings.length,
        requestId,
      },
    });
  } catch {
    // Audit failure must not block pipeline
  }
}

// ──────────────────────────────────────────────
// Pipeline orchestrator — run all 4 sections with gating
// ──────────────────────────────────────────────

/** Section definitions for IMRaD pipeline ordering and dispatch. */
export const IMRAD_SECTIONS = [
  { name: 'introduction', taskType: 'SECTION_WRITE_INTRO',       agentName: 'agent-intro-writer',      stage: 12 },
  { name: 'methods',      taskType: 'SECTION_WRITE_METHODS',     agentName: 'agent-methods-writer',    stage: 13 },
  { name: 'results',      taskType: 'SECTION_WRITE_RESULTS',     agentName: 'agent-results-writer',    stage: 14 },
  { name: 'discussion',   taskType: 'SECTION_WRITE_DISCUSSION',  agentName: 'agent-discussion-writer', stage: 15 },
] as const;

export interface IMRaDPipelineInput {
  manuscriptId: string;
  outline: string[];
  verifiedClaims: Record<string, unknown>[];
  extractionRows: Record<string, unknown>[];
  groundingPack: Record<string, unknown>;
  styleParams?: Record<string, unknown>;
  governanceMode: 'LIVE' | 'DEMO';
  requestId: string;
  userId?: string;
}

export interface IMRaDSectionResult {
  section: string;
  gateResult: VerifyGateResult;
}

export interface IMRaDPipelineResult {
  manuscriptId: string;
  sections: IMRaDSectionResult[];
  allGatesPassed: boolean;
  blockedAt?: string;
  governanceMode: 'LIVE' | 'DEMO';
}

/**
 * Dispatch a single section writer agent and return its output.
 * Returns SectionWriterOutput (normalised).
 */
async function dispatchSectionWriter(
  agentName: string,
  taskType: string,
  inputs: Record<string, unknown>,
  governanceMode: string,
  requestId: string,
): Promise<SectionWriterOutput> {
  const endpoints = agentEndpoints();
  const agentUrl = endpoints[agentName];

  if (!agentUrl) {
    return {
      sectionMarkdown: '',
      claimsWithEvidence: [],
      warnings: [`Agent ${agentName} not configured in AGENT_ENDPOINTS_JSON`],
      overallPass: false,
    };
  }

  const payload = {
    request_id: requestId,
    task_type: taskType,
    mode: governanceMode,
    inputs,
  };

  const token = process.env.WORKER_SERVICE_TOKEN || '';
  const headers: Record<string, string> = { 'Content-Type': 'application/json' };
  if (token) headers['Authorization'] = `Bearer ${token}`;

  const resp = await fetch(`${agentUrl}/agents/run/sync`, {
    method: 'POST',
    headers,
    body: JSON.stringify(payload),
  });

  if (!resp.ok) {
    const text = await resp.text().catch(() => '');
    return {
      sectionMarkdown: '',
      claimsWithEvidence: [],
      warnings: [`Agent ${agentName} returned ${resp.status}: ${text}`],
      overallPass: false,
    };
  }

  const data = (await resp.json()) as {
    outputs?: {
      sectionMarkdown?: string;
      section_markdown?: string;
      claimsWithEvidence?: ClaimWithEvidence[];
      claims_with_evidence?: ClaimWithEvidence[];
      warnings?: string[];
      overallPass?: boolean;
    };
  };

  const outputs = data.outputs ?? {};

  return {
    sectionMarkdown: outputs.sectionMarkdown || outputs.section_markdown || '',
    claimsWithEvidence: outputs.claimsWithEvidence || outputs.claims_with_evidence || [],
    warnings: outputs.warnings ?? [],
    overallPass: outputs.overallPass ?? false,
  };
}

/**
 * Run the full IMRaD pipeline: write each section sequentially, verify after each.
 * In LIVE mode, blocks at the first section that fails verification.
 * In DEMO mode, continues with warnings.
 */
export async function runIMRaDPipeline(
  input: IMRaDPipelineInput,
): Promise<IMRaDPipelineResult> {
  const results: IMRaDSectionResult[] = [];
  let blockedAt: string | undefined;

  for (const sec of IMRAD_SECTIONS) {
    // Build writer inputs
    const writerInputs: Record<string, unknown> = {
      outline: input.outline,
      verifiedClaims: input.verifiedClaims,
      extractionRows: input.extractionRows,
      groundingPack: input.groundingPack,
      styleParams: input.styleParams ?? {},
      governanceMode: input.governanceMode,
    };

    // ── Step A: Write the section ──
    const writerOutput = await dispatchSectionWriter(
      sec.agentName,
      sec.taskType,
      writerInputs,
      input.governanceMode,
      `${input.requestId}-${sec.name}`,
    );

    // ── Step B: Verify gate ──
    const gateResult = await runSectionVerifyGate(
      sec.name,
      writerOutput,
      input.groundingPack as Record<string, unknown>,
      input.governanceMode,
      `${input.requestId}-${sec.name}`,
      input.userId,
      input.manuscriptId,
    );

    results.push({ section: sec.name, gateResult });

    // ── Step C: Block if gated in LIVE ──
    if (gateResult.blocked) {
      blockedAt = sec.name;
      break; // Stop pipeline — cannot proceed past a failed gate
    }
  }

  return {
    manuscriptId: input.manuscriptId,
    sections: results,
    allGatesPassed: !blockedAt && results.every((r) => r.gateResult.gatePass),
    blockedAt,
    governanceMode: input.governanceMode,
  };
}
