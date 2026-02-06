/**
 * Workflow Stages Execution Router
 *
 * API endpoints for executing individual workflow stages.
 * Handles job queuing via BullMQ for async stage processing.
 *
 * @module routes/workflow/stages
 */

import { Router, Request, Response } from 'express';
import { z } from 'zod';
import { requireAuth } from '../../middleware/auth';
import { Queue } from 'bullmq';
import crypto from 'crypto';
import { getEvents, isDone } from '../../services/sse-event-store';

const router = Router();

// Request validation schemas
const Stage2InputsSchema = z.object({
  query: z.string().optional(),
  databases: z.array(z.enum(['pubmed', 'semantic_scholar'])).default(['pubmed']),
  max_results: z.number().int().min(1).max(200).default(25),
  year_range: z.object({
    from: z.number().int().optional(),
    to: z.number().int().optional(),
  }).optional(),
  study_types: z.array(z.enum([
    'clinical_trial',
    'randomized_controlled_trial',
    'cohort_study',
    'case_control_study',
    'cross_sectional_study',
    'systematic_review',
    'meta_analysis',
    'case_report',
    'observational_study',
    'review'
  ])).optional(),
  mesh_terms: z.array(z.string()).optional(),
  include_keywords: z.array(z.string()).optional(),
  exclude_keywords: z.array(z.string()).optional(),
  language: z.string().default('en'),
  dedupe: z.boolean().default(true),
  require_abstract: z.boolean().default(true),
});

const Stage2ExecuteSchema = z.object({
  workflow_id: z.string().uuid('Invalid workflow ID format'),
  research_question: z.string().min(10, 'Research question must be at least 10 characters'),
  mode: z.enum(['DEMO', 'LIVE']).default('DEMO'),
  risk_tier: z.enum(['PHI', 'SENSITIVE', 'NON_SENSITIVE']).default('NON_SENSITIVE'),
  domain_id: z.string().default('clinical'),
  inputs: Stage2InputsSchema.optional(),
});

// BullMQ Queue setup
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

// Workflow Stages Queue
let workflowStagesQueue: Queue | null = null;

// Initialize queue lazily
function getWorkflowStagesQueue(): Queue {
  if (!workflowStagesQueue) {
    workflowStagesQueue = new Queue('workflow-stages', {
      connection,
      defaultJobOptions: {
        attempts: 3,
        backoff: {
          type: 'exponential',
          delay: 5000,
        },
        removeOnComplete: 100,
        removeOnFail: 50,
      },
    });
  }
  return workflowStagesQueue;
}

/**
 * POST /api/workflow/stages/2/execute
 * Execute Stage 2: Literature Review and Analysis
 */
router.post('/2/execute', requireAuth, async (req: Request, res: Response) => {
  try {
    // Validate request body
    const parsed = Stage2ExecuteSchema.safeParse(req.body);
    if (!parsed.success) {
      return res.status(400).json({
        error: 'Invalid request body',
        details: parsed.error.issues,
      });
    }

    const { workflow_id, research_question, mode, risk_tier, domain_id } = parsed.data;
    const userId = (req as any).user?.id;

    // Parse and validate inputs with defaults
    const inputs = Stage2InputsSchema.parse(parsed.data.inputs ?? {});

    // Generate job ID
    const job_id = crypto.randomUUID();

    // Get queue instance
    const queue = getWorkflowStagesQueue();

    // Dispatch job to BullMQ queue with deterministic payload
    const job = await queue.add(
      'stage-2-execute',
      {
        stage: 2,
        job_id,
        workflow_id,
        research_question,
        mode,
        risk_tier,
        domain_id,
        inputs,
        user_id: userId,
        timestamp: new Date().toISOString(),
      },
      {
        jobId: job_id,
        priority: 5, // Normal priority
      }
    );

    console.log(`[Stage 2] Job ${job_id} dispatched for workflow ${workflow_id} (${mode}/${risk_tier}/${domain_id})`);

    // Return job ID for status polling with routing info and normalized inputs
    res.status(202).json({
      success: true,
      job_id,
      stage: 2,
      workflow_id,
      status: 'queued',
      message: 'Stage 2 execution job has been queued',
      routing: {
        mode,
        risk_tier,
        domain_id,
      },
      normalized_inputs: inputs,
    });

  } catch (error) {
    console.error('[Stage 2] Execute error:', error);
    res.status(500).json({
      error: 'Failed to execute Stage 2',
      message: error instanceof Error ? error.message : 'Unknown error',
    });
  }
});

/**
 * GET /api/workflow/stages/:stage/jobs/:job_id/status
 * Get job status for polling
 */
router.get('/:stage/jobs/:job_id/status', requireAuth, async (req: Request, res: Response) => {
  try {
    const { stage, job_id } = req.params;
    
    // Get queue instance
    const queue = getWorkflowStagesQueue();
    
    // Get job from queue
    const job = await queue.getJob(job_id);
    
    if (!job) {
      return res.status(404).json({
        error: 'Job not found',
        job_id,
        stage: parseInt(stage),
      });
    }

    const state = await job.getState();
    const progress = job.progress as number || 0;

    res.json({
      job_id,
      stage: parseInt(stage),
      status: state,
      progress,
      data: job.data,
      result: job.returnvalue,
      error: job.failedReason,
      created_at: job.timestamp,
      processed_at: job.processedOn,
      finished_at: job.finishedOn,
    });

  } catch (error) {
    console.error('[Stage Status] Error:', error);
    res.status(500).json({
      error: 'Failed to get job status',
      message: error instanceof Error ? error.message : 'Unknown error',
    });
  }
});

/**
 * GET /api/workflow/stages/:stage/jobs/:job_id/stream
 * SSE endpoint: replays stored events from Redis, then polls for new events
 * until :done marker (Stage 2) or BullMQ terminal state or timeout.
 */
router.get('/:stage/jobs/:job_id/stream', requireAuth, async (req: Request, res: Response) => {
  const stage = req.params.stage as string;
  const stageNum = parseInt(stage, 10);
  const job_id = req.params.job_id as string;

  res.setHeader('Content-Type', 'text/event-stream');
  res.setHeader('Cache-Control', 'no-cache');
  res.setHeader('Connection', 'keep-alive');
  res.setHeader('X-Accel-Buffering', 'no');
  res.flushHeaders();

  let closed = false;
  req.on('close', () => { closed = true; });

  const POLL_INTERVAL_MS = 500;
  const STREAM_TIMEOUT_MS = 120 * 1000; // 120s
  const startTime = Date.now();
  let lastSeq = 0;

  const queue = getWorkflowStagesQueue();

  const writeEvent = (evt: { seq: number; event?: string; data: unknown }): void => {
    if (closed) return;
    res.write(`id: ${evt.seq}\nevent: ${evt.event || 'message'}\ndata: ${JSON.stringify(evt.data)}\n\n`);
  };

  try {
    // Replay all stored events immediately
    const initial = await getEvents(job_id, 0);
    for (const evt of initial) {
      if (closed) break;
      writeEvent(evt);
      lastSeq = evt.seq + 1;
    }

    while (!closed && (Date.now() - startTime) < STREAM_TIMEOUT_MS) {
      const events = await getEvents(job_id, lastSeq);

      for (const evt of events) {
        if (closed) break;
        writeEvent(evt);
        lastSeq = evt.seq + 1;
      }

      // Stage 2: end when :done marker exists
      if (stageNum === 2) {
        if (await isDone(job_id)) {
          const remaining = await getEvents(job_id, lastSeq);
          for (const evt of remaining) {
            if (closed) break;
            writeEvent(evt);
            lastSeq = evt.seq + 1;
          }
          if (!closed) {
            res.write(`event: done\ndata: ${JSON.stringify({ job_id, stage: stageNum })}\n\n`);
          }
          break;
        }
      } else {
        // Non–Stage 2: use BullMQ terminal state
        const job = await queue.getJob(job_id);
        if (job) {
          const state = await job.getState();
          if (state === 'completed' || state === 'failed') {
            const remaining = await getEvents(job_id, lastSeq);
            for (const evt of remaining) {
              if (closed) break;
              writeEvent(evt);
              lastSeq = evt.seq + 1;
            }
            if (!closed) {
              res.write(`event: ${state}\ndata: ${JSON.stringify({
                job_id,
                stage: stageNum,
                status: state,
                result: job.returnvalue,
                error: job.failedReason,
              })}\n\n`);
            }
            break;
          }
        }
      }

      if (events.length === 0 && !closed) {
        res.write(': keepalive\n\n');
      }

      await new Promise(resolve => setTimeout(resolve, POLL_INTERVAL_MS));
    }
  } catch (error) {
    if (!closed) {
      res.write(`event: error\ndata: ${JSON.stringify({ error: error instanceof Error ? error.message : 'Stream error' })}\n\n`);
    }
  }

  if (!closed) {
    res.end();
  }
});

/**
 * Cleanup function for graceful shutdown
 */
export async function closeWorkflowStagesQueue(): Promise<void> {
  if (workflowStagesQueue) {
    await workflowStagesQueue.close();
    workflowStagesQueue = null;
    console.log('[Workflow Stages] Queue closed');
  }
}

export default router;