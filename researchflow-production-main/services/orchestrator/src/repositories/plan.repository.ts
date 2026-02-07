/**
 * Plan Repository
 *
 * Data access layer for analysis plans, jobs, artifacts, and events.
 * Uses Drizzle ORM for type-safe database operations.
 */
import {
  analysisPlans,
  analysisJobs,
  analysisJobEvents,
  analysisArtifacts,
} from '@researchflow/core/schema';
import { eq, desc, and, gt } from 'drizzle-orm';

import { db } from '../../db';
import type {
  AnalysisPlan,
  AnalysisJob,
  AnalysisArtifact,
  PlanStatus,
  JobStatus,
  JobEvent,
} from '../types/planning';

export class PlanRepository {
  // ===== PLANS =====

  async createPlan(
    data: Omit<AnalysisPlan, 'id' | 'createdAt' | 'updatedAt'>
  ): Promise<AnalysisPlan> {
    if (!db) throw new Error('Database not initialized');
    
    const [result] = await db
      .insert(analysisPlans)
      .values({
        projectId: data.projectId || null,
        datasetId: data.datasetId,
        name: data.name,
        description: data.description || null,
        researchQuestion: data.researchQuestion,
        planType: data.planType,
        constraints: data.constraints,
        planSpec: data.planSpec,
        status: data.status,
        requiresApproval: data.requiresApproval,
        createdBy: data.createdBy,
      })
      .returning();

    return this.mapPlanRow(result);
  }

  async getPlan(planId: string): Promise<AnalysisPlan | null> {
    if (!db) throw new Error('Database not initialized');
    
    const [result] = await db
      .select()
      .from(analysisPlans)
      .where(eq(analysisPlans.id, planId))
      .limit(1);

    return result ? this.mapPlanRow(result) : null;
  }

  async listPlans(
    userId: string,
    projectId?: string,
    limit = 50
  ): Promise<AnalysisPlan[]> {
    if (!db) throw new Error('Database not initialized');
    
    const conditions = [eq(analysisPlans.createdBy, userId)];
    if (projectId) {
      conditions.push(eq(analysisPlans.projectId, projectId));
    }

    const results = await db
      .select()
      .from(analysisPlans)
      .where(and(...conditions))
      .orderBy(desc(analysisPlans.createdAt))
      .limit(limit);

    return results.map((r) => this.mapPlanRow(r));
  }

  async updatePlanStatus(
    planId: string,
    status: PlanStatus,
    extras?: Partial<AnalysisPlan>
  ): Promise<AnalysisPlan | null> {
    if (!db) throw new Error('Database not initialized');
    
    const updateData: Record<string, unknown> = { status };

    if (extras?.approvedBy) updateData.approvedBy = extras.approvedBy;
    if (extras?.approvedAt) updateData.approvedAt = new Date(extras.approvedAt);
    if (extras?.rejectionReason) updateData.rejectionReason = extras.rejectionReason;
    if (extras?.planSpec) updateData.planSpec = extras.planSpec;

    const [result] = await db
      .update(analysisPlans)
      .set(updateData)
      .where(eq(analysisPlans.id, planId))
      .returning();

    return result ? this.mapPlanRow(result) : null;
  }

  async deletePlan(planId: string): Promise<boolean> {
    if (!db) throw new Error('Database not initialized');
    
    const result = await db
      .delete(analysisPlans)
      .where(eq(analysisPlans.id, planId));

    return (result as any).rowCount > 0;
  }

  // ===== JOBS =====

  async createJob(
    planId: string,
    jobType: 'plan_build' | 'plan_run',
    startedBy: string
  ): Promise<AnalysisJob> {
    if (!db) throw new Error('Database not initialized');
    
    const [result] = await db
      .insert(analysisJobs)
      .values({
        planId,
        jobType,
        status: 'pending',
        progress: 0,
        stagesCompleted: [],
        startedBy,
      })
      .returning();

    return this.mapJobRow(result);
  }

  async getJob(jobId: string): Promise<AnalysisJob | null> {
    if (!db) throw new Error('Database not initialized');
    
    const [result] = await db
      .select()
      .from(analysisJobs)
      .where(eq(analysisJobs.id, jobId))
      .limit(1);

    return result ? this.mapJobRow(result) : null;
  }

  async getJobsByPlan(planId: string): Promise<AnalysisJob[]> {
    if (!db) throw new Error('Database not initialized');
    
    const results = await db
      .select()
      .from(analysisJobs)
      .where(eq(analysisJobs.planId, planId))
      .orderBy(desc(analysisJobs.createdAt));

    return results.map((r) => this.mapJobRow(r));
  }

  async updateJobStatus(jobId: string, status: JobStatus): Promise<AnalysisJob | null> {
    if (!db) throw new Error('Database not initialized');
    
    const updateData: Record<string, unknown> = { status };

    if (status === 'running') {
      updateData.startedAt = new Date();
    }
    if (status === 'completed' || status === 'failed' || status === 'cancelled') {
      updateData.completedAt = new Date();
    }

    const [result] = await db
      .update(analysisJobs)
      .set(updateData)
      .where(eq(analysisJobs.id, jobId))
      .returning();

    return result ? this.mapJobRow(result) : null;
  }

  async updateJobProgress(
    jobId: string,
    progress: number,
    currentStage?: string,
    stageCompleted?: string
  ): Promise<AnalysisJob | null> {
    if (!db) throw new Error('Database not initialized');
    
    const job = await this.getJob(jobId);
    if (!job) return null;

    const stagesCompleted = stageCompleted
      ? [...job.stagesCompleted, stageCompleted]
      : job.stagesCompleted;

    const updateData: Record<string, unknown> = {
      progress,
      currentStage: currentStage || null,
      stagesCompleted,
      status: 'running',
    };

    if (!job.startedAt) {
      updateData.startedAt = new Date();
    }

    const [result] = await db
      .update(analysisJobs)
      .set(updateData)
      .where(eq(analysisJobs.id, jobId))
      .returning();

    return result ? this.mapJobRow(result) : null;
  }

  async completeJob(
    jobId: string,
    result: Record<string, unknown>
  ): Promise<AnalysisJob | null> {
    if (!db) throw new Error('Database not initialized');
    
    const [row] = await db
      .update(analysisJobs)
      .set({
        status: 'completed',
        progress: 100,
        result,
        completedAt: new Date(),
      })
      .where(eq(analysisJobs.id, jobId))
      .returning();

    return row ? this.mapJobRow(row) : null;
  }

  async failJob(
    jobId: string,
    errorMessage: string,
    errorDetails?: Record<string, unknown>
  ): Promise<AnalysisJob | null> {
    if (!db) throw new Error('Database not initialized');
    
    const [row] = await db
      .update(analysisJobs)
      .set({
        status: 'failed',
        errorMessage,
        errorDetails: errorDetails || null,
        completedAt: new Date(),
      })
      .where(eq(analysisJobs.id, jobId))
      .returning();

    return row ? this.mapJobRow(row) : null;
  }

  // ===== JOB EVENTS =====

  async addJobEvent(
    jobId: string,
    eventType: string,
    eventData: Record<string, unknown>
  ): Promise<void> {
    if (!db) throw new Error('Database not initialized');
    
    await db.insert(analysisJobEvents).values({
      jobId,
      eventType,
      eventData,
    });
  }

  async getJobEvents(jobId: string, since?: Date): Promise<JobEvent[]> {
    if (!db) throw new Error('Database not initialized');
    
    const conditions = [eq(analysisJobEvents.jobId, jobId)];
    if (since) {
      conditions.push(gt(analysisJobEvents.createdAt, since));
    }

    const results = await db
      .select()
      .from(analysisJobEvents)
      .where(and(...conditions))
      .orderBy(analysisJobEvents.createdAt);

    return results.map((r) => ({
      type: r.eventType,
      data: r.eventData as Record<string, unknown>,
      timestamp: r.createdAt.toISOString(),
    }));
  }

  // ===== ARTIFACTS =====

  async createArtifact(
    data: Omit<AnalysisArtifact, 'id' | 'createdAt'>
  ): Promise<AnalysisArtifact> {
    if (!db) throw new Error('Database not initialized');
    
    const [result] = await db
      .insert(analysisArtifacts)
      .values({
        jobId: data.jobId,
        planId: data.planId,
        artifactType: data.artifactType,
        name: data.name,
        description: data.description || null,
        filePath: data.filePath || null,
        fileSize: data.fileSize || null,
        mimeType: data.mimeType || null,
        inlineData: data.inlineData || null,
        metadata: data.metadata,
      })
      .returning();

    return this.mapArtifactRow(result);
  }

  async getArtifact(artifactId: string): Promise<AnalysisArtifact | null> {
    if (!db) throw new Error('Database not initialized');
    
    const [result] = await db
      .select()
      .from(analysisArtifacts)
      .where(eq(analysisArtifacts.id, artifactId))
      .limit(1);

    return result ? this.mapArtifactRow(result) : null;
  }

  async getArtifacts(filters: {
    jobId?: string;
    planId?: string;
    type?: string;
  }): Promise<AnalysisArtifact[]> {
    if (!db) throw new Error('Database not initialized');
    
    const conditions: ReturnType<typeof eq>[] = [];
    if (filters.jobId) conditions.push(eq(analysisArtifacts.jobId, filters.jobId));
    if (filters.planId) conditions.push(eq(analysisArtifacts.planId, filters.planId));
    if (filters.type) conditions.push(eq(analysisArtifacts.artifactType, filters.type));

    const results = conditions.length > 0
      ? await db.select().from(analysisArtifacts).where(and(...conditions)).orderBy(desc(analysisArtifacts.createdAt))
      : await db.select().from(analysisArtifacts).orderBy(desc(analysisArtifacts.createdAt));

    return results.map((r) => this.mapArtifactRow(r));
  }

  async deleteArtifact(artifactId: string): Promise<boolean> {
    if (!db) throw new Error('Database not initialized');
    
    const result = await db
      .delete(analysisArtifacts)
      .where(eq(analysisArtifacts.id, artifactId));

    return (result as any).rowCount > 0;
  }

  // ===== MAPPERS =====

  private mapPlanRow(row: typeof analysisPlans.$inferSelect): AnalysisPlan {
    return {
      id: row.id,
      projectId: row.projectId || undefined,
      datasetId: row.datasetId,
      name: row.name,
      description: row.description || undefined,
      researchQuestion: row.researchQuestion,
      planType: row.planType as AnalysisPlan['planType'],
      constraints: row.constraints as AnalysisPlan['constraints'],
      planSpec: row.planSpec as AnalysisPlan['planSpec'],
      status: row.status as AnalysisPlan['status'],
      requiresApproval: row.requiresApproval,
      approvedBy: row.approvedBy || undefined,
      approvedAt: row.approvedAt?.toISOString(),
      rejectionReason: row.rejectionReason || undefined,
      createdBy: row.createdBy,
      createdAt: row.createdAt.toISOString(),
      updatedAt: row.updatedAt.toISOString(),
    };
  }

  private mapJobRow(row: typeof analysisJobs.$inferSelect): AnalysisJob {
    return {
      id: row.id,
      planId: row.planId,
      jobType: row.jobType as AnalysisJob['jobType'],
      status: row.status as AnalysisJob['status'],
      progress: row.progress,
      currentStage: row.currentStage || undefined,
      stagesCompleted: row.stagesCompleted as string[],
      result: row.result as Record<string, unknown> | undefined,
      errorMessage: row.errorMessage || undefined,
      errorDetails: row.errorDetails as Record<string, unknown> | undefined,
      startedAt: row.startedAt?.toISOString(),
      completedAt: row.completedAt?.toISOString(),
      startedBy: row.startedBy,
      createdAt: row.createdAt.toISOString(),
    };
  }

  private mapArtifactRow(row: typeof analysisArtifacts.$inferSelect): AnalysisArtifact {
    return {
      id: row.id,
      jobId: row.jobId,
      planId: row.planId,
      artifactType: row.artifactType as AnalysisArtifact['artifactType'],
      name: row.name,
      description: row.description || undefined,
      filePath: row.filePath || undefined,
      fileSize: row.fileSize || undefined,
      mimeType: row.mimeType || undefined,
      inlineData: row.inlineData as Record<string, unknown> | undefined,
      metadata: row.metadata as Record<string, unknown>,
      createdAt: row.createdAt.toISOString(),
    };
  }
}

export const planRepository = new PlanRepository();
