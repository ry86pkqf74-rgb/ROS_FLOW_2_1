/**
 * Workflow Stages Worker
 *
 * BullMQ worker for processing workflow stage execution jobs.
 * Handles communication with the Python worker service.
 */

import { Worker, Job } from 'bullmq';
import { EventEmitter } from 'events';

// Job data interface
export interface StageJobData {
  stage: number;
  job_id: string;
  workflow_id: string;
  research_question: string;
  user_id: string;
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

// Worker instance
let workflowStagesWorker: Worker<StageJobData> | null = null;

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
      console.log(`[Stage Worker] Processing stage ${job.data.stage} job ${job.data.job_id}`);

      try {
        // Update job progress
        await job.updateProgress(10);

        // Call worker service for stage execution
        const workerUrl = process.env.WORKER_URL || 'http://worker:8000';
        const endpoint = `${workerUrl}/api/workflow/stages/${job.data.stage}/execute`;

        console.log(`[Stage Worker] Calling ${endpoint}`);

        await job.updateProgress(20);

        const response = await fetch(endpoint, {
          method: 'POST',
          headers: { 
            'Content-Type': 'application/json',
            'X-Request-ID': job.data.job_id,
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

        console.log(`[Stage Worker] Completed stage ${job.data.stage} job ${job.data.job_id} in ${workerResult.duration_ms}ms`);

        return workerResult;

      } catch (error) {
        const duration = Date.now() - startTime;
        console.error(`[Stage Worker] Stage ${job.data.stage} job ${job.data.job_id} failed after ${duration}ms:`, error);

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
    console.log(`[Stage Worker] Job ${job.id} completed`);
  });

  workflowStagesWorker.on('failed', (job, err) => {
    console.error(`[Stage Worker] Job ${job?.id} failed:`, err.message);
  });

  workflowStagesWorker.on('error', (error) => {
    console.error('[Stage Worker] Worker error:', error);
  });

  workflowStagesWorker.on('stalled', (jobId) => {
    console.warn(`[Stage Worker] Job ${jobId} stalled`);
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

export default {
  init: initWorkflowStagesWorker,
  shutdown: shutdownWorkflowStagesWorker,
  getStatus: getWorkerStatus,
  events: stageJobEvents,
};