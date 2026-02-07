/**
 * Workflow Stages Worker
 *
 * BullMQ worker for processing workflow stage execution jobs.
 * Handles communication with the Python worker service.
 * Stage 2 uses the new AI router -> agent architecture.
 */

import { createHash } from 'crypto';
import { EventEmitter } from 'events';

import { Worker, Job } from 'bullmq';

import { getAgentClient } from '../../clients/agentClient';
import { createLogger } from '../../utils/logger';
import { pushEvent, setDone } from '../sse-event-store';

const logger = createLogger('workflow-stages-worker');

// Migrated stages -> task types (single source of truth)
const MIGRATED_STAGE_TO_TASK_TYPE: Record<number, string> = {
  9: 'POLICY_REVIEW',
};

// TaskContract for AI router/agent communication (inline types for Step 3)
interface TaskContract {
  request_id: string;
  task_type: string;
  workflow_id: string;
  user_id: string;
  mode: 'LIVE' | 'DEMO';
  risk_tier?: string;
  domain_id?: string;
  inputs: Record<string, any>;
  budgets?: {
    max_time_ms?: number;
    max_tokens?: number;
  };
}

interface DispatchPlan {
  agent_url: string;
  agent_name: string;
  dispatch_type?: string;
  routing_strategy?: string;
}

// Job data interface
export interface StageJobData {
  stage: number;
  job_id: string;
  request_id?: string;
  workflow_id: string;
  research_question: string;
  user_id?: string;
  mode?: 'LIVE' | 'DEMO';
  risk_tier?: string;
  domain_id?: string;
  inputs?: Record<string, any>;
  budgets?: {
    max_time_ms?: number;
    max_tokens?: number;
  };
  timestamp: string;
}

// Worker result interface
export interface StageWorkerResult {
  success: boolean;
  stage: number;
  workflow_id: string;
  job_id: string;
  artifacts?: string[];
  results?: Record<string, any>;
  error?: string;
  duration_ms?: number;
}

// Event emitter for job status updates
export const stageJobEvents = new EventEmitter();

// Redis connection setup
const REDIS_URL = process.env.REDIS_URL || 'redis://localhost:6379';

function parseRedisUrl(url: string) {
  const parsed = new URL(url);
  return {
    host: parsed.hostname,
    port: parseInt(parsed.port || '6379'),
    password: parsed.password || undefined,
  };
}

const connection = parseRedisUrl(REDIS_URL);

// Helper to resolve request_id
function resolveRequestId(jobData: StageJobData): string {
  return jobData.request_id || jobData.job_id || `stage-${jobData.stage}-${jobData.workflow_id}`;
}

// Check if stage uses new router -> agent architecture
function isMigratedStage(stage: number): boolean {
  return Object.prototype.hasOwnProperty.call(MIGRATED_STAGE_TO_TASK_TYPE, stage);
}

function sha256(content: string): string {
  return createHash('sha256').update(content).digest('hex');
}

function safeJsonStringify(value: unknown): string {
  try {
    return JSON.stringify(value, null, 2);
  } catch (err) {
    return JSON.stringify({
      error: 'JSON_STRINGIFY_FAILED',
      message: err instanceof Error ? err.message : 'Unknown error',
    });
  }
}

function normalizeMode(mode: StageJobData['mode']): 'DEMO' | 'LIVE' {
  return (mode || 'DEMO').toUpperCase() === 'LIVE' ? 'LIVE' : 'DEMO';
}

function isOkAgentEnvelope(envelope: any): boolean {
  const s = String(envelope?.status || '').toLowerCase();
  return s === 'ok' || s === 'degraded';
}

function getAgentEnvelopeErrorMessage(envelope: any): string {
  if (!envelope || typeof envelope !== 'object') return 'Unknown agent error';
  const errorMsg =
    (typeof envelope?.error?.message === 'string' && envelope.error.message) ||
    (typeof envelope?.outputs?.error === 'string' && envelope.outputs.error) ||
    (typeof envelope?.outputs?.warning === 'string' && envelope.outputs.warning) ||
    '';
  return errorMsg || 'Unknown agent error';
}

type Stage2ScreeningCriteria = {
  inclusion: string[];
  exclusion: string[];
  required_keywords: string[];
  excluded_keywords: string[];
  study_types_required: string[];
  study_types_excluded: string[];
  year_min?: number;
  year_max?: number;
  require_abstract: boolean;
};

function buildStage2ScreeningCriteria(inputs: Record<string, any> | undefined): Stage2ScreeningCriteria {
  const i = inputs || {};
  const includeKeywords: string[] = Array.isArray(i.include_keywords) ? i.include_keywords.filter(Boolean).map(String) : [];
  const excludeKeywords: string[] = Array.isArray(i.exclude_keywords) ? i.exclude_keywords.filter(Boolean).map(String) : [];
  const meshTerms: string[] = Array.isArray(i.mesh_terms) ? i.mesh_terms.filter(Boolean).map(String) : [];
  const studyTypes: string[] = Array.isArray(i.study_types) ? i.study_types.filter(Boolean).map(String) : [];

  const yearRange = typeof i.year_range === 'object' && i.year_range ? i.year_range : undefined;
  const yearFrom = yearRange && Number.isFinite(Number(yearRange.from)) ? Number(yearRange.from) : undefined;
  const yearTo = yearRange && Number.isFinite(Number(yearRange.to)) ? Number(yearRange.to) : undefined;

  // Allow optional override in inputs.criteria (merged on top).
  const override = typeof i.criteria === 'object' && i.criteria ? i.criteria : {};

  const base: Stage2ScreeningCriteria = {
    inclusion: [...meshTerms, ...includeKeywords].filter(Boolean),
    exclusion: excludeKeywords.filter(Boolean),
    required_keywords: includeKeywords.filter(Boolean),
    excluded_keywords: excludeKeywords.filter(Boolean),
    study_types_required: studyTypes.filter(Boolean),
    study_types_excluded: [],
    year_min: yearFrom,
    year_max: yearTo,
    require_abstract: typeof i.require_abstract === 'boolean' ? i.require_abstract : true,
  };

  return {
    ...base,
    ...override,
    inclusion: Array.isArray(override.inclusion) ? override.inclusion : base.inclusion,
    exclusion: Array.isArray(override.exclusion) ? override.exclusion : base.exclusion,
    required_keywords: Array.isArray(override.required_keywords) ? override.required_keywords : base.required_keywords,
    excluded_keywords: Array.isArray(override.excluded_keywords) ? override.excluded_keywords : base.excluded_keywords,
    study_types_required: Array.isArray(override.study_types_required) ? override.study_types_required : base.study_types_required,
    study_types_excluded: Array.isArray(override.study_types_excluded) ? override.study_types_excluded : base.study_types_excluded,
    require_abstract: typeof override.require_abstract === 'boolean' ? override.require_abstract : base.require_abstract,
  };
}

type Stage2Paper = Record<string, any>;

function normalizePaperId(paper: Stage2Paper): string | null {
  const id = paper?.id ?? paper?.paper_id ?? paper?.pmid ?? null;
  if (typeof id === 'string' && id.trim()) return id.trim();
  if (typeof id === 'number' && Number.isFinite(id)) return String(id);
  return null;
}

function buildRagDocumentsFromPapers(papers: Stage2Paper[], domainId: string): Array<Record<string, any>> {
  return papers
    .map((paper) => {
      const docId = normalizePaperId(paper);
      if (!docId) return null;
      const title = typeof paper.title === 'string' ? paper.title : '';
      const abstract = typeof paper.abstract === 'string' ? paper.abstract : '';
      const text = [title, abstract].filter(Boolean).join('\n\n').trim();
      if (!text) return null;
      return {
        docId,
        title: title || undefined,
        source: paper.url || paper.source || 'pubmed',
        text,
        metadata: {
          domainId,
          year: paper.year ?? paper.publication_year,
          doi: paper.doi,
          journal: paper.journal,
        },
      };
    })
    .filter(Boolean) as Array<Record<string, any>>;
}

function buildGroundingPackFromRetrieve(retrieveEnvelope: any): Record<string, any> | null {
  const outputs = retrieveEnvelope?.outputs;
  if (!outputs || typeof outputs !== 'object') return null;
  const chunks = Array.isArray(outputs.chunks) ? outputs.chunks : [];
  const citations = Array.isArray(retrieveEnvelope?.artifacts) ? retrieveEnvelope.artifacts : [];
  const retrieval_trace = outputs.retrieval_trace ?? outputs.retrievalTrace ?? null;

  return {
    chunks,
    citations,
    retrieval_trace,
    // verify agent prefers sources[]; include it for cross-agent compatibility
    sources: chunks.map((c: any) => ({
      id: c?.chunk_id ?? c?.chunkId ?? c?.id ?? 'chunk',
      doc_id: c?.doc_id ?? c?.docId ?? c?.metadata?.docId ?? c?.metadata?.doc_id,
      text: c?.text ?? '',
      score: c?.score ?? 0,
      metadata: c?.metadata ?? {},
    })),
    span_refs: [],
  };
}

function deriveClaimsFromExtraction(extractEnvelope: any, maxClaims: number = 25): string[] {
  const outputs = extractEnvelope?.outputs;
  const table = Array.isArray(outputs?.extraction_table) ? outputs.extraction_table : [];
  const claims: string[] = [];

  for (const row of table) {
    const keyResults = row?.key_results;
    if (typeof keyResults === 'string' && keyResults.trim()) {
      claims.push(keyResults.trim());
    } else if (Array.isArray(keyResults)) {
      for (const item of keyResults) {
        if (typeof item === 'string' && item.trim()) claims.push(item.trim());
      }
    }
    if (claims.length >= maxClaims) break;
  }

  // Dedupe while preserving order
  const seen = new Set<string>();
  const out: string[] = [];
  for (const c of claims) {
    if (seen.has(c)) continue;
    seen.add(c);
    out.push(c);
  }
  return out.slice(0, maxClaims);
}

// Get internal service auth token (optional for migrated stages)
// Returns empty string if not configured (internal routing may not require it)
function getServiceToken(): string {
  const token = process.env.WORKER_SERVICE_TOKEN;
  if (!token) {
    logger.warn(
      'WORKER_SERVICE_TOKEN not set; internal auth will be skipped. ' +
      'May be required depending on internal auth configuration.'
    );
    return '';
  }
  return token;
}

// Worker instance
let workflowStagesWorker: Worker<StageJobData> | null = null;

type RoutedTaskResult = {
  taskContract: TaskContract;
  agentUrl: string;
  agentName: string;
  response: any;
  latencyMs: number;
};

async function storeStage2JsonArtifact(params: {
  workflowId: string;
  userId: string;
  filename: string;
  json: unknown;
}): Promise<{ artifactId: string } | null> {
  const content = safeJsonStringify(params.json);
  try {
    // Lazy import to avoid requiring DB for non-DB environments/tests.
    const mod = await import('../../../storage.js');
    const created = await (mod as any).storage.createArtifact({
      researchId: params.workflowId,
      stageId: '2',
      artifactType: 'analysis_output',
      filename: params.filename,
      mimeType: 'application/json',
      content,
      sizeBytes: Buffer.byteLength(content, 'utf8'),
      sha256Hash: sha256(content),
      createdBy: params.userId,
    } as any);
    return { artifactId: created.id };
  } catch (err) {
    // Best-effort: artifacts require DB; do not fail DEMO pipeline on persistence errors.
    logger.warn('stage2_artifact_persist_failed', {
      filename: params.filename,
      error: err instanceof Error ? err.message : String(err),
    });
    return null;
  }
}

/**
 * Initialize the workflow stages worker
 */
export function initWorkflowStagesWorker(): Worker<StageJobData> {
  if (workflowStagesWorker) {
    return workflowStagesWorker;
  }

  console.log('[Workflow Stages Worker] Initializing...');

  workflowStagesWorker = new Worker<StageJobData>(
    'workflow-stages',
    async (job: Job<StageJobData>) => {
      const startTime = Date.now();
      const requestId = resolveRequestId(job.data);
      console.log(`[Stage Worker] Processing stage ${job.data.stage} request_id ${requestId}`);

      try {
        // Update job progress
        await job.updateProgress(10);

        // Stage 2 DEMO/LIVE pipeline orchestrator (lit -> screen -> ingest -> retrieve -> extract -> verify)
        if (job.data.stage === 2) {
          const mode = normalizeMode(job.data.mode);
          const riskTier = job.data.risk_tier || 'NON_SENSITIVE';
          const domainId = job.data.domain_id || 'clinical';
          const userId = job.data.user_id || 'system';
          const workflowId = job.data.workflow_id;

          const orchestratorInternalUrl = process.env.ORCHESTRATOR_INTERNAL_URL || 'http://orchestrator:3001';
          const routerEndpoint = `${orchestratorInternalUrl}/api/ai/router/dispatch`;
          const serviceToken = getServiceToken();
          const agentClient = getAgentClient();

          const warnings: string[] = [];
          const artifacts: Record<string, string> = {};

          const emitStep = async (
            step: string,
            status: 'start' | 'complete' | 'error' | 'warning',
            data: Record<string, any> = {}
          ): Promise<void> => {
            try {
              await pushEvent(job.data.job_id, {
                event: 'progress',
                data: {
                  step,
                  status,
                  stage: 2,
                  mode,
                  request_id: requestId,
                  job_id: job.data.job_id,
                  ...data,
                },
              });
            } catch (err) {
              logger.warn('stage2_sse_emit_failed', {
                step,
                status,
                error: err instanceof Error ? err.message : String(err),
              });
            }
          };

          const runRoutedTask = async (taskType: string, inputs: Record<string, any>, suffix: string): Promise<RoutedTaskResult> => {
            const taskContract: TaskContract = {
              request_id: `${requestId}-${suffix}`,
              task_type: taskType,
              workflow_id: workflowId,
              user_id: userId,
              mode,
              risk_tier: riskTier,
              domain_id: domainId,
              inputs,
              budgets: job.data.budgets || {
                max_time_ms: 300000,
                max_tokens: 100000,
              },
            };

            const dispatchResponse = await fetch(routerEndpoint, {
              method: 'POST',
              headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${serviceToken}`,
                'X-Request-ID': taskContract.request_id,
              },
              body: JSON.stringify(taskContract),
            });

            if (!dispatchResponse.ok) {
              const errorText = await dispatchResponse.text();
              throw new Error(`Router dispatch failed (${dispatchResponse.status}): ${errorText}`);
            }

            const dispatchPlan: DispatchPlan = await dispatchResponse.json();

            const agentResponse = await agentClient.postSync(
              dispatchPlan.agent_url,
              '/agents/run/sync',
              taskContract,
              { headers: { 'X-Request-ID': taskContract.request_id } }
            );

            if (!agentResponse.success) {
              throw new Error(`Agent execution failed (${taskType}): ${agentResponse.error || 'Unknown error'}`);
            }

            return {
              taskContract,
              agentUrl: dispatchPlan.agent_url,
              agentName: dispatchPlan.agent_name,
              response: agentResponse.data,
              latencyMs: agentResponse.latencyMs,
            };
          };

          // ---- 1) Stage2 Lit ----
          await job.updateProgress(15);
          await emitStep('stage2_lit', 'start');

          const litInputs = {
            ...(job.data.inputs ?? {}),
            research_question: job.data.research_question,
            governanceMode: mode,
            domainId,
          };
          const lit = await runRoutedTask('STAGE_2_LITERATURE_REVIEW', litInputs, 'lit');
          if (!isOkAgentEnvelope(lit.response)) {
            const msg = getAgentEnvelopeErrorMessage(lit.response);
            await emitStep('stage2_lit', 'error', { code: 'STAGE2_LIT_FAILED', message: msg });
            try {
              await setDone(job.data.job_id);
            } catch (_) {
              // best-effort
            }
            throw new Error(`STAGE2_LIT_FAILED: ${msg}`);
          }
          const litArtifact = await storeStage2JsonArtifact({
            workflowId,
            userId,
            filename: 'stage2_lit.json',
            json: lit.response,
          });
          if (litArtifact) artifacts.stage2_lit = litArtifact.artifactId;

          const litOutputs = (lit.response as any)?.outputs || {};
          const papers: Stage2Paper[] = Array.isArray(litOutputs.papers) ? litOutputs.papers : [];
          if (papers.length === 0) {
            await emitStep('stage2_lit', 'error', { code: 'NO_PAPERS_FOUND', message: 'stage2-lit returned 0 papers' });
            try {
              await setDone(job.data.job_id);
            } catch (_) {
              // best-effort
            }
            throw new Error('NO_PAPERS_FOUND');
          }
          await emitStep('stage2_lit', 'complete', { count: papers.length });

          // ---- 2) Stage2 Screen ----
          await job.updateProgress(30);
          await emitStep('stage2_screen', 'start', { input_papers: papers.length });

          const criteria = buildStage2ScreeningCriteria(job.data.inputs);
          const screenInputs = {
            papers,
            criteria,
            domainId,
            governanceMode: mode,
          };
          const screen = await runRoutedTask('STAGE2_SCREEN', screenInputs, 'screen');
          if (!isOkAgentEnvelope(screen.response)) {
            const msg = getAgentEnvelopeErrorMessage(screen.response);
            await emitStep('stage2_screen', 'error', { code: 'STAGE2_SCREEN_FAILED', message: msg });
            try {
              await setDone(job.data.job_id);
            } catch (_) {
              // best-effort
            }
            throw new Error(`STAGE2_SCREEN_FAILED: ${msg}`);
          }
          const screenArtifact = await storeStage2JsonArtifact({
            workflowId,
            userId,
            filename: 'stage2_screen.json',
            json: screen.response,
          });
          if (screenArtifact) artifacts.stage2_screen = screenArtifact.artifactId;

          const screenOutputs = (screen.response as any)?.outputs || {};
          const included = Array.isArray(screenOutputs.included) ? screenOutputs.included : [];
          const includedIds = new Set(
            included
              .map((r: any) => (typeof r?.paper_id === 'string' ? r.paper_id : null))
              .filter(Boolean)
          );
          const includedPapers = papers.filter((p) => {
            const id = normalizePaperId(p);
            return id ? includedIds.has(id) : false;
          });

          if (includedPapers.length === 0) {
            await emitStep('stage2_screen', 'error', { code: 'NO_PAPERS_FOUND', message: 'No papers included after screening' });
            try {
              await setDone(job.data.job_id);
            } catch (_) {
              // best-effort
            }
            throw new Error('NO_PAPERS_FOUND');
          }
          await emitStep('stage2_screen', 'complete', { included: includedPapers.length, excluded: (screenOutputs.excluded || []).length });

          // ---- 3) RAG Ingest (best-effort in DEMO) ----
          await job.updateProgress(45);
          await emitStep('rag_ingest', 'start', { documents: includedPapers.length });

          const kbFromInputs =
            (job.data.inputs as any)?.knowledgeBase ||
            (job.data.inputs as any)?.rag?.knowledgeBase ||
            `stage2-${workflowId}`;
          const knowledgeBase = String(kbFromInputs).slice(0, 128);

          const documents = buildRagDocumentsFromPapers(includedPapers, domainId);
          let ingest: RoutedTaskResult | null = null;
          try {
            ingest = await runRoutedTask(
              'RAG_INGEST',
              {
                knowledgeBase,
                domainId,
                projectId: 'researchflow',
                documents,
              },
              'ingest'
            );
            if (!isOkAgentEnvelope(ingest.response)) {
              throw new Error(getAgentEnvelopeErrorMessage(ingest.response));
            }
          } catch (err) {
            const msg = err instanceof Error ? err.message : String(err);
            if (mode === 'DEMO') {
              warnings.push(`RAG ingest skipped (DEMO): ${msg}`);
              const skipped = await storeStage2JsonArtifact({
                workflowId,
                userId,
                filename: 'rag_ingest.json',
                json: { status: 'skipped', reason: msg, knowledgeBase, documents: documents.length },
              });
              if (skipped) artifacts.rag_ingest = skipped.artifactId;
              await emitStep('rag_ingest', 'warning', { warning: msg });
            } else {
              await emitStep('rag_ingest', 'error', { error: msg });
              try {
                await setDone(job.data.job_id);
              } catch (_) {
                // best-effort
              }
              throw err;
            }
          }

          if (ingest) {
            const ingestArtifact = await storeStage2JsonArtifact({
              workflowId,
              userId,
              filename: 'rag_ingest.json',
              json: ingest.response,
            });
            if (ingestArtifact) artifacts.rag_ingest = ingestArtifact.artifactId;
            await emitStep('rag_ingest', 'complete');
          }

          // ---- 4) RAG Retrieve (best-effort in DEMO) ----
          await job.updateProgress(60);
          await emitStep('rag_retrieve', 'start', { knowledgeBase });

          const ragTopK =
            Number((job.data.inputs as any)?.rag?.topK ?? (job.data.inputs as any)?.rag_top_k ?? 20);
          const ragSemanticK =
            Number((job.data.inputs as any)?.rag?.semanticK ?? (job.data.inputs as any)?.rag_semantic_k ?? 50);
          const ragRerankMode =
            String((job.data.inputs as any)?.rag?.rerankMode ?? (job.data.inputs as any)?.rag_rerank_mode ?? 'none');

          let retrieve: RoutedTaskResult | null = null;
          let groundingPack: Record<string, any> | null = null;
          try {
            retrieve = await runRoutedTask(
              'RAG_RETRIEVE',
              {
                query_text: job.data.research_question,
                collection: knowledgeBase,
                top_k: Number.isFinite(ragTopK) ? ragTopK : 20,
                semantic_k: Number.isFinite(ragSemanticK) ? ragSemanticK : 50,
                rerankMode: ragRerankMode,
              },
              'retrieve'
            );
            if (!isOkAgentEnvelope(retrieve.response)) {
              throw new Error(getAgentEnvelopeErrorMessage(retrieve.response));
            }
            groundingPack = buildGroundingPackFromRetrieve(retrieve.response);
          } catch (err) {
            const msg = err instanceof Error ? err.message : String(err);
            if (mode === 'DEMO') {
              warnings.push(`RAG retrieve skipped (DEMO): ${msg}`);
              const skipped = await storeStage2JsonArtifact({
                workflowId,
                userId,
                filename: 'rag_retrieve.json',
                json: { status: 'skipped', reason: msg, knowledgeBase },
              });
              if (skipped) artifacts.rag_retrieve = skipped.artifactId;
              await emitStep('rag_retrieve', 'warning', { warning: msg });
            } else {
              await emitStep('rag_retrieve', 'error', { error: msg });
              try {
                await setDone(job.data.job_id);
              } catch (_) {
                // best-effort
              }
              throw err;
            }
          }

          if (retrieve) {
            const retrieveArtifact = await storeStage2JsonArtifact({
              workflowId,
              userId,
              filename: 'rag_retrieve.json',
              json: retrieve.response,
            });
            if (retrieveArtifact) artifacts.rag_retrieve = retrieveArtifact.artifactId;
            await emitStep('rag_retrieve', 'complete', {
              chunks: (retrieve.response as any)?.outputs?.count ?? 0,
            });
          }

          // ---- 5) Stage2 Extract (requires abstracts; groundingPack optional) ----
          await job.updateProgress(80);
          await emitStep('stage2_extract', 'start', { grounding: Boolean(groundingPack) });

          const extractInputs: Record<string, any> = {
            governanceMode: mode,
            domainId,
            abstracts: includedPapers.map((p) => ({
              doc_id: normalizePaperId(p) || p.pmid || 'doc',
              title: p.title,
              abstract: p.abstract,
              year: p.year,
              doi: p.doi,
              url: p.url,
            })),
          };
          if (groundingPack) extractInputs.groundingPack = groundingPack;

          const extract = await runRoutedTask('STAGE_2_EXTRACT', extractInputs, 'extract');
          if (!isOkAgentEnvelope(extract.response)) {
            const msg = getAgentEnvelopeErrorMessage(extract.response);
            await emitStep('stage2_extract', 'error', { code: 'STAGE2_EXTRACT_FAILED', message: msg });
            try {
              await setDone(job.data.job_id);
            } catch (_) {
              // best-effort
            }
            throw new Error(`STAGE2_EXTRACT_FAILED: ${msg}`);
          }
          const extractArtifact = await storeStage2JsonArtifact({
            workflowId,
            userId,
            filename: 'stage2_extract.json',
            json: extract.response,
          });
          if (extractArtifact) artifacts.stage2_extract = extractArtifact.artifactId;
          await emitStep('stage2_extract', 'complete');

          // ---- 6) Verify (best-effort in DEMO, strict in LIVE) ----
          await job.updateProgress(92);
          await emitStep('verify', 'start');

          const claims = deriveClaimsFromExtraction(extract.response);
          let verify: RoutedTaskResult | null = null;
          try {
            verify = await runRoutedTask(
              'CLAIM_VERIFY',
              {
                governanceMode: mode,
                claims,
                groundingPack,
                strictness: mode === 'LIVE' ? 'strict' : 'normal',
              },
              'verify'
            );
            if (!isOkAgentEnvelope(verify.response)) {
              throw new Error(getAgentEnvelopeErrorMessage(verify.response));
            }
          } catch (err) {
            const msg = err instanceof Error ? err.message : String(err);
            if (mode === 'DEMO') {
              warnings.push(`Verify skipped (DEMO): ${msg}`);
              const skipped = await storeStage2JsonArtifact({
                workflowId,
                userId,
                filename: 'verify.json',
                json: { status: 'skipped', reason: msg, claims: claims.length, hasGrounding: Boolean(groundingPack) },
              });
              if (skipped) artifacts.verify = skipped.artifactId;
              await emitStep('verify', 'warning', { warning: msg });
            } else {
              await emitStep('verify', 'error', { error: msg });
              try {
                await setDone(job.data.job_id);
              } catch (_) {
                // best-effort
              }
              throw err;
            }
          }

          if (verify) {
            const verifyArtifact = await storeStage2JsonArtifact({
              workflowId,
              userId,
              filename: 'verify.json',
              json: verify.response,
            });
            if (verifyArtifact) artifacts.verify = verifyArtifact.artifactId;
            await emitStep('verify', 'complete', { claims: claims.length });
          }

          // Final complete event for stream subscribers
          try {
            await pushEvent(job.data.job_id, {
              event: 'complete',
              data: {
                success: true,
                warnings,
                artifacts,
              },
            });
          } catch (_) {
            // best-effort
          }
          try {
            await setDone(job.data.job_id);
          } catch (_) {
            // best-effort
          }

          await job.updateProgress(100);

          const workerResult: StageWorkerResult = {
            success: true,
            stage: 2,
            workflow_id: workflowId,
            job_id: job.data.job_id,
            duration_ms: Date.now() - startTime,
            artifacts: Object.values(artifacts),
            results: {
              mode,
              routing: { risk_tier: riskTier, domain_id: domainId },
              counts: {
                lit_papers: papers.length,
                screened_included: includedPapers.length,
                rag_documents: documents.length,
              },
              warnings,
              artifact_ids: artifacts,
              step_outputs: {
                stage2_lit: lit.response,
                stage2_screen: screen.response,
                rag_ingest: ingest?.response ?? null,
                rag_retrieve: retrieve?.response ?? null,
                stage2_extract: extract.response,
                verify: verify?.response ?? null,
              },
            },
          };

          stageJobEvents.emit(`job:${job.data.job_id}:completed`, workerResult);
          stageJobEvents.emit('stage:completed', {
            stage: 2,
            job_id: job.data.job_id,
            workflow_id: workflowId,
          });

          console.log(`[Stage Worker] Completed stage 2 request_id ${requestId} duration_ms ${workerResult.duration_ms}`);
          return workerResult;
        }

        // Check if this stage uses new router -> agent architecture
        if (isMigratedStage(job.data.stage)) {
          // NEW PATH: Migrated stages use router -> agent
          console.log(`[Stage Worker] Using router -> agent for stage ${job.data.stage} request_id ${requestId}`);
          
          const orchestratorInternalUrl = process.env.ORCHESTRATOR_INTERNAL_URL || 'http://orchestrator:3001';
          const routerEndpoint = `${orchestratorInternalUrl}/api/ai/router/dispatch`;

          await job.updateProgress(20);

          const taskType = MIGRATED_STAGE_TO_TASK_TYPE[job.data.stage];

          // Build TaskContract
          const taskContract: TaskContract = {
            request_id: requestId,
            task_type: taskType,
            workflow_id: job.data.workflow_id,
            user_id: job.data.user_id || 'system',
            mode: job.data.mode || 'DEMO',
            risk_tier: job.data.risk_tier || 'NON_SENSITIVE',
            domain_id: job.data.domain_id || 'clinical',
            inputs: { ...(job.data.inputs ?? {}), research_question: job.data.research_question },
            budgets: job.data.budgets || {
              max_time_ms: 300000, // 5 minutes default
              max_tokens: 100000,
            },
          };

          // Get service token for internal auth
          const serviceToken = getServiceToken();

          // Call router dispatch to get agent_url
          console.log(`[Stage Worker] Dispatching router for stage ${job.data.stage} request_id ${requestId}`);
          const dispatchResponse = await fetch(routerEndpoint, {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              'Authorization': `Bearer ${serviceToken}`,
              'X-Request-ID': requestId,
            },
            body: JSON.stringify(taskContract),
          });

          if (!dispatchResponse.ok) {
            const errorText = await dispatchResponse.text();
            throw new Error(`Router dispatch failed (${dispatchResponse.status}): ${errorText}`);
          }

          const dispatchPlan: DispatchPlan = await dispatchResponse.json();
          console.log(`[Stage Worker] Routed to agent for stage ${job.data.stage} request_id ${requestId}`);

          // Call agent via AgentClient.postSync (sync-only)
          const agentClient = getAgentClient();
          const agentResponse = await agentClient.postSync(
            dispatchPlan.agent_url,
            '/agents/run/sync',
            taskContract,
            { headers: { 'X-Request-ID': requestId } }
          );

          await job.updateProgress(80);

          if (!agentResponse.success) {
            await pushEvent(job.data.job_id, {
              event: 'error',
              data: { error: agentResponse.error },
            });
            await setDone(job.data.job_id);
            throw new Error(`Agent execution failed: ${agentResponse.error || 'Unknown error'}`);
          }

          // Store final complete event for stream subscribers
          await pushEvent(job.data.job_id, {
            event: 'complete',
            data: { success: true, duration_ms: agentResponse.latencyMs },
          });
          await setDone(job.data.job_id);

          await job.updateProgress(100);

          const workerResult: StageWorkerResult = {
            success: true,
            stage: job.data.stage,
            workflow_id: job.data.workflow_id,
            job_id: job.data.job_id,
            duration_ms: Date.now() - startTime,
            results: agentResponse.data as Record<string, any>,
          };

          // Emit completion event
          stageJobEvents.emit(`job:${job.data.job_id}:completed`, workerResult);
          stageJobEvents.emit('stage:completed', {
            stage: job.data.stage,
            job_id: job.data.job_id,
            workflow_id: job.data.workflow_id,
          });

          console.log(`[Stage Worker] Completed stage ${job.data.stage} request_id ${requestId} duration_ms ${workerResult.duration_ms}`);

          return workerResult;
        } else {
          // LEGACY PATH: All other stages use worker service
          const workerUrl = process.env.WORKER_URL || 'http://worker:8000';
          const endpoint = `${workerUrl}/api/workflow/stages/${job.data.stage}/execute`;

          console.log(`[Stage Worker] Calling worker for stage ${job.data.stage} request_id ${requestId}`);

          await job.updateProgress(20);

          const response = await fetch(endpoint, {
            method: 'POST',
            headers: { 
              'Content-Type': 'application/json',
              'X-Request-ID': requestId,
            },
            body: JSON.stringify({
              workflow_id: job.data.workflow_id,
              research_question: job.data.research_question,
              user_id: job.data.user_id,
              job_id: job.data.job_id,
            }),
          });

          await job.updateProgress(80);

          if (!response.ok) {
            const errorText = await response.text();
            throw new Error(`Worker service failed (${response.status}): ${errorText}`);
          }

          const result = await response.json();

          await job.updateProgress(100);

          const workerResult: StageWorkerResult = {
            success: true,
            stage: job.data.stage,
            workflow_id: job.data.workflow_id,
            job_id: job.data.job_id,
            duration_ms: Date.now() - startTime,
            ...result,
          };

          // Emit completion event
          stageJobEvents.emit(`job:${job.data.job_id}:completed`, workerResult);
          stageJobEvents.emit('stage:completed', {
            stage: job.data.stage,
            job_id: job.data.job_id,
            workflow_id: job.data.workflow_id,
          });

          console.log(`[Stage Worker] Completed stage ${job.data.stage} request_id ${requestId} duration_ms ${workerResult.duration_ms}`);

          return workerResult;
        }

      } catch (error) {
        const duration = Date.now() - startTime;
        if (job.data.stage === 2 || isMigratedStage(job.data.stage)) {
          try {
            await pushEvent(job.data.job_id, {
              event: 'error',
              data: { error: error instanceof Error ? error.message : 'Unknown error' },
            });
            await setDone(job.data.job_id);
          } catch (_) {
            // best-effort
          }
        }
        console.error(`[Stage Worker] Stage ${job.data.stage} request_id ${requestId} failed duration_ms ${duration} status error`);

        const errorResult: StageWorkerResult = {
          success: false,
          stage: job.data.stage,
          workflow_id: job.data.workflow_id,
          job_id: job.data.job_id,
          duration_ms: duration,
          error: error instanceof Error ? error.message : 'Unknown error',
        };

        // Emit failure event
        stageJobEvents.emit(`job:${job.data.job_id}:failed`, errorResult);
        stageJobEvents.emit('stage:failed', {
          stage: job.data.stage,
          job_id: job.data.job_id,
          workflow_id: job.data.workflow_id,
          error: errorResult.error,
        });

        throw error;
      }
    },
    {
      connection,
      concurrency: parseInt(process.env.STAGE_WORKER_CONCURRENCY || '2'),
    }
  );

  // Event handlers
  workflowStagesWorker.on('completed', (job) => {
    console.log('[Stage Worker] Job completed status success');
  });

  workflowStagesWorker.on('failed', (job, err) => {
    console.error('[Stage Worker] Job failed status error');
  });

  workflowStagesWorker.on('error', (error) => {
    console.error('[Stage Worker] Worker error status error');
  });

  workflowStagesWorker.on('stalled', (jobId) => {
    console.warn('[Stage Worker] Job stalled status warning');
  });

  console.log('[Workflow Stages Worker] Initialized with concurrency:', workflowStagesWorker.opts.concurrency);

  return workflowStagesWorker;
}

/**
 * Shutdown the worker gracefully
 */
export async function shutdownWorkflowStagesWorker(): Promise<void> {
  if (workflowStagesWorker) {
    console.log('[Workflow Stages Worker] Shutting down...');
    await workflowStagesWorker.close();
    workflowStagesWorker = null;
    console.log('[Workflow Stages Worker] Shutdown complete');
  }
}

/**
 * Get worker status
 */
export function getWorkerStatus(): { 
  isRunning: boolean; 
  concurrency: number; 
  queueName: string; 
} {
  return {
    isRunning: workflowStagesWorker !== null,
    concurrency: workflowStagesWorker?.opts.concurrency || 0,
    queueName: 'workflow-stages',
  };
}

export const __stage2TestUtils = {
  buildStage2ScreeningCriteria,
  buildRagDocumentsFromPapers,
  buildGroundingPackFromRetrieve,
  deriveClaimsFromExtraction,
  isOkAgentEnvelope,
  getAgentEnvelopeErrorMessage,
};

export default {
  init: initWorkflowStagesWorker,
  shutdown: shutdownWorkflowStagesWorker,
  getStatus: getWorkerStatus,
  events: stageJobEvents,
};
