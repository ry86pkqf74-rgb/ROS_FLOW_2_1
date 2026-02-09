/**
 * Branch Persistence Service
 * Phase 3.3: PostgreSQL-backed branch and revision management
 * Phase 5: All branch state mutations emit audit events in the same DB transaction.
 *
 * Replaces in-memory BranchManagerService with persistent storage.
 * Supports: create, merge, diff, revision history
 */

import crypto from 'crypto';

import { pool, query as dbQuery } from '../../db';
import { appendEvent, type DbClient } from './audit.service';

export interface Branch {
  id: string;
  manuscriptId: string;
  branchName: string;
  parentBranch: string;
  status: 'active' | 'merged' | 'archived' | 'deleted';
  description?: string;
  versionHash?: string;
  wordCounts?: Record<string, number>;
  createdBy?: string;
  createdAt: Date;
  updatedAt: Date;
}

export interface Revision {
  id: string;
  branchId: string;
  revisionNumber: number;
  content: Record<string, any>;
  sectionsChanged: string[];
  diffFromParent?: Record<string, any>;
  wordCount?: number;
  commitMessage?: string;
  createdBy?: string;
  createdAt: Date;
}

export interface CreateBranchRequest {
  manuscriptId: string;
  branchName: string;
  parentBranch?: string;
  description?: string;
  createdBy?: string;
}

export interface CreateRevisionRequest {
  branchId: string;
  content: Record<string, any>;
  commitMessage?: string;
  createdBy?: string;
}

export interface MergeBranchRequest {
  sourceBranchId: string;
  targetBranchId: string;
  mergeType?: 'fast_forward' | 'squash' | 'rebase';
  mergedBy?: string;
}

const STREAM_TYPE_MANUSCRIPT = 'MANUSCRIPT';
const SERVICE_ORCHESTRATOR = 'orchestrator';

/**
 * Run a function inside a DB transaction. Commits on success, rolls back on throw.
 */
async function runWithTransaction<T>(fn: (tx: DbClient) => Promise<T>): Promise<T> {
  if (!pool) throw new Error('Database pool not initialized');
  const client = await pool.connect();
  try {
    await client.query('BEGIN');
    const result = await fn(client as DbClient);
    await client.query('COMMIT');
    return result;
  } catch (err) {
    await client.query('ROLLBACK').catch(() => {});
    throw err;
  } finally {
    client.release();
  }
}

/**
 * Canonical hash for branch state (PHI-free: ids, names, status, version hash).
 */
function branchStateHash(b: { manuscriptId: string; id: string; branchName: string; status: string; versionHash?: string | null }): string {
  const canonical = JSON.stringify({
    manuscriptId: b.manuscriptId,
    branchId: b.id,
    branchName: b.branchName,
    status: b.status,
    versionHash: b.versionHash ?? null
  }, Object.keys({ manuscriptId: 1, branchId: 1, branchName: 1, status: 1, versionHash: 1 }).sort());
  return crypto.createHash('sha256').update(canonical).digest('hex').substring(0, 16);
}

/**
 * Branch Persistence Service
 */
export class BranchPersistenceService {
  private static instance: BranchPersistenceService;
  
  private constructor() {}
  
  static getInstance(): BranchPersistenceService {
    if (!this.instance) {
      this.instance = new BranchPersistenceService();
    }
    return this.instance;
  }
  
  /**
   * Create a new branch
   */
  async createBranch(request: CreateBranchRequest): Promise<Branch> {
    const { manuscriptId, branchName, parentBranch = 'main', description, createdBy } = request;
    
    return runWithTransaction(async (tx) => {
      const existing = await tx.query(
        'SELECT id FROM manuscript_branches WHERE manuscript_id = $1 AND branch_name = $2',
        [manuscriptId, branchName]
      );
      if (existing.rows.length > 0) {
        throw new Error(`Branch '${branchName}' already exists for this manuscript`);
      }
      
      const result = await tx.query(`
        INSERT INTO manuscript_branches 
          (manuscript_id, branch_name, parent_branch, description, created_by)
        VALUES ($1, $2, $3, $4, $5)
        RETURNING *
      `, [manuscriptId, branchName, parentBranch, description, createdBy]);
      
      const branch = this.mapBranch(result.rows[0]);
      const afterHash = branchStateHash(branch);
      
      await appendEvent(tx, {
        stream_type: STREAM_TYPE_MANUSCRIPT,
        stream_key: manuscriptId,
        actor_type: 'USER',
        actor_id: createdBy ?? null,
        service: SERVICE_ORCHESTRATOR,
        action: 'CREATE',
        resource_type: 'BRANCH',
        resource_id: branch.id,
        before_hash: null,
        after_hash: afterHash,
        payload: { manuscript_id: manuscriptId, branch_id: branch.id, branch_name: branchName, parent_branch: parentBranch },
        dedupe_key: `branch:${branch.id}:create:${branch.id}`,
      });
      
      return branch;
    });
  }
  
  /**
   * Get branch by ID
   */
  async getBranch(branchId: string): Promise<Branch | null> {
    const result = await dbQuery(
      'SELECT * FROM manuscript_branches WHERE id = $1',
      [branchId]
    );
    
    if (result.rows.length === 0) return null;
    return this.mapBranch(result.rows[0]);
  }
  
  /**
   * Get branch by name
   */
  async getBranchByName(manuscriptId: string, branchName: string): Promise<Branch | null> {
    const result = await dbQuery(
      'SELECT * FROM manuscript_branches WHERE manuscript_id = $1 AND branch_name = $2',
      [manuscriptId, branchName]
    );
    
    if (result.rows.length === 0) return null;
    return this.mapBranch(result.rows[0]);
  }
  
  /**
   * List branches for a manuscript
   */
  async listBranches(manuscriptId: string, includeArchived = false): Promise<Branch[]> {
    let query = `
      SELECT b.*, 
             (SELECT MAX(revision_number) FROM manuscript_revisions r WHERE r.branch_id = b.id) as latest_revision
      FROM manuscript_branches b
      WHERE b.manuscript_id = $1
    `;
    
    if (!includeArchived) {
      query += ` AND b.status IN ('active', 'merged')`;
    }
    
    query += ` ORDER BY b.branch_name = 'main' DESC, b.updated_at DESC`;
    
    const result = await dbQuery(query, [manuscriptId]);
    return result.rows.map(row => this.mapBranch(row));
  }
  
  /**
   * Create a new revision.
   * When opts.tx is provided, uses that client (caller owns transaction).
   * When opts.skipAudit is true, does not emit an audit event (e.g. when called from mergeBranch).
   */
  async createRevision(request: CreateRevisionRequest, opts?: { tx?: DbClient; skipAudit?: boolean }): Promise<Revision> {
    const { branchId, content, commitMessage, createdBy } = request;
    const run = async (tx: DbClient) => {
      const prevResult = await tx.query(`
        SELECT content FROM manuscript_revisions
        WHERE branch_id = $1
        ORDER BY revision_number DESC
        LIMIT 1
      `, [branchId]);
      const prevContent = prevResult.rows[0]?.content || {};
      
      const diff = this.computeDiff(prevContent, content);
      const sectionsChanged = Object.keys(diff).filter(k => diff[k].action !== 'unchanged');
      const wordCount = this.computeTotalWordCount(content);
      const versionHash = this.computeHash(content);
      
      const nextNumResult = await tx.query(
        'SELECT get_next_revision_number($1) as next_num',
        [branchId]
      );
      const revisionNumber = nextNumResult.rows[0].next_num;
      
      const result = await tx.query(`
        INSERT INTO manuscript_revisions 
          (branch_id, revision_number, content, sections_changed, diff_from_parent, word_count, commit_message, created_by)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
        RETURNING *
      `, [branchId, revisionNumber, JSON.stringify(content), sectionsChanged, JSON.stringify(diff), wordCount, commitMessage, createdBy]);
      
      await tx.query(`
        UPDATE manuscript_branches
        SET version_hash = $1, word_counts = $2
        WHERE id = $3
      `, [versionHash, JSON.stringify(this.computeSectionWordCounts(content)), branchId]);
      
      const revision = this.mapRevision(result.rows[0]);
      const shouldEmitAudit = opts?.skipAudit !== true;
      
      if (shouldEmitAudit) {
        const branchRow = await tx.query('SELECT manuscript_id FROM manuscript_branches WHERE id = $1', [branchId]);
        const manuscriptId = branchRow.rows[0]?.manuscript_id ?? branchId;
        const beforeHash = prevResult.rows.length > 0 ? this.computeHash(prevContent) : null;
        await appendEvent(tx, {
          stream_type: STREAM_TYPE_MANUSCRIPT,
          stream_key: manuscriptId,
          actor_type: 'USER',
          actor_id: createdBy ?? null,
          service: SERVICE_ORCHESTRATOR,
          action: 'CREATE',
          resource_type: 'REVISION',
          resource_id: revision.id,
          before_hash: beforeHash,
          after_hash: versionHash,
          payload: { branch_id: branchId, revision_id: revision.id, revision_number: revisionNumber, sections_changed_count: sectionsChanged.length, word_count: wordCount },
          dedupe_key: `branch:${branchId}:revision:${revision.id}`,
        });
      }
      
      return revision;
    };
    
    if (opts?.tx) {
      return run(opts.tx);
    }
    return runWithTransaction(run);
  }
  
  /**
   * Get revision by number
   */
  async getRevision(branchId: string, revisionNumber: number): Promise<Revision | null> {
    const result = await dbQuery(`
      SELECT * FROM manuscript_revisions
      WHERE branch_id = $1 AND revision_number = $2
    `, [branchId, revisionNumber]);
    
    if (result.rows.length === 0) return null;
    return this.mapRevision(result.rows[0]);
  }
  
  /**
   * Get latest revision for a branch
   */
  async getLatestRevision(branchId: string): Promise<Revision | null> {
    const result = await dbQuery(`
      SELECT * FROM manuscript_revisions
      WHERE branch_id = $1
      ORDER BY revision_number DESC
      LIMIT 1
    `, [branchId]);
    
    if (result.rows.length === 0) return null;
    return this.mapRevision(result.rows[0]);
  }
  
  /**
   * List revisions for a branch
   */
  async listRevisions(branchId: string, limit = 50): Promise<Revision[]> {
    const result = await dbQuery(`
      SELECT * FROM manuscript_revisions
      WHERE branch_id = $1
      ORDER BY revision_number DESC
      LIMIT $2
    `, [branchId, limit]);
    
    return result.rows.map(row => this.mapRevision(row));
  }
  
  /**
   * Merge branches
   */
  async mergeBranch(request: MergeBranchRequest): Promise<{ success: boolean; conflicts?: string[] }> {
    const { sourceBranchId, targetBranchId, mergeType = 'fast_forward', mergedBy } = request;
    
    const sourceRevision = await this.getLatestRevision(sourceBranchId);
    const targetRevision = await this.getLatestRevision(targetBranchId);
    
    if (!sourceRevision) {
      throw new Error('Source branch has no revisions');
    }
    
    const conflicts: string[] = [];
    if (targetRevision) {
      const sourceChanged = new Set(sourceRevision.sectionsChanged);
      const targetChanged = new Set(targetRevision.sectionsChanged);
      for (const section of sourceChanged) {
        if (targetChanged.has(section)) conflicts.push(section);
      }
    }
    
    if (conflicts.length > 0 && mergeType === 'fast_forward') {
      if (pool) {
        const client = await pool.connect();
        try {
          await client.query('BEGIN');
          await client.query(`
            INSERT INTO branch_merges (source_branch_id, target_branch_id, merge_type, conflicts)
            VALUES ($1, $2, $3, $4)
          `, [sourceBranchId, targetBranchId, mergeType, JSON.stringify(conflicts)]);
          await client.query('COMMIT');
        } catch (e) {
          await client.query('ROLLBACK').catch(() => {});
          throw e;
        } finally {
          client.release();
        }
        return { success: false, conflicts };
      }
      return { success: false, conflicts };
    }
    
    return runWithTransaction(async (tx) => {
      const mergedContent = mergeType === 'squash'
        ? sourceRevision.content
        : { ...targetRevision?.content, ...sourceRevision.content };
      
      await this.createRevision({
        branchId: targetBranchId,
        content: mergedContent,
        commitMessage: `Merge ${mergeType} from ${sourceBranchId}`,
        createdBy: mergedBy
      }, { tx, skipAudit: true });
      
      await tx.query(`
        UPDATE manuscript_branches
        SET status = 'merged', merged_at = NOW(), merged_by = $1
        WHERE id = $2
      `, [mergedBy, sourceBranchId]);
      
      await tx.query(`
        INSERT INTO branch_merges (source_branch_id, target_branch_id, merge_type, merged_by)
        VALUES ($1, $2, $3, $4)
      `, [sourceBranchId, targetBranchId, mergeType, mergedBy]);
      
      const targetBranchRow = await tx.query('SELECT manuscript_id FROM manuscript_branches WHERE id = $1', [targetBranchId]);
      const manuscriptId = targetBranchRow.rows[0]?.manuscript_id ?? targetBranchId;
      const targetBeforeHash = targetRevision ? this.computeHash(targetRevision.content) : null;
      const afterHash = this.computeHash(mergedContent);
      
      await appendEvent(tx, {
        stream_type: STREAM_TYPE_MANUSCRIPT,
        stream_key: manuscriptId,
        actor_type: 'USER',
        actor_id: mergedBy ?? null,
        service: SERVICE_ORCHESTRATOR,
        action: 'MERGE',
        resource_type: 'BRANCH',
        resource_id: targetBranchId,
        before_hash: targetBeforeHash,
        after_hash: afterHash,
        payload: { source_branch_id: sourceBranchId, target_branch_id: targetBranchId, merge_type: mergeType },
        dedupe_key: `branch:${sourceBranchId}:merge:${targetBranchId}`,
      });
      
      return { success: true };
    });
  }
  
  /**
   * Archive a branch
   */
  async archiveBranch(branchId: string, userId?: string): Promise<void> {
    return runWithTransaction(async (tx) => {
      const beforeRow = await tx.query(
        'SELECT manuscript_id, version_hash FROM manuscript_branches WHERE id = $1',
        [branchId]
      );
      if (beforeRow.rows.length === 0) return;
      const manuscriptId = beforeRow.rows[0].manuscript_id;
      const beforeHash = beforeRow.rows[0].version_hash ?? null;
      
      await tx.query(`
        UPDATE manuscript_branches
        SET status = 'archived'
        WHERE id = $1
      `, [branchId]);
      
      const afterHash = crypto.createHash('sha256')
        .update(JSON.stringify({ branchId, status: 'archived', versionHash: beforeHash }))
        .digest('hex').substring(0, 16);
      
      await appendEvent(tx, {
        stream_type: STREAM_TYPE_MANUSCRIPT,
        stream_key: manuscriptId,
        actor_type: 'USER',
        actor_id: userId ?? null,
        service: SERVICE_ORCHESTRATOR,
        action: 'ARCHIVE',
        resource_type: 'BRANCH',
        resource_id: branchId,
        before_hash: beforeHash,
        after_hash: afterHash,
        payload: { branch_id: branchId },
        dedupe_key: `branch:${branchId}:archive:${branchId}`,
      });
    });
  }
  
  /**
   * Compare two revisions
   */
  async compareRevisions(
    branchId: string,
    fromRevision: number,
    toRevision: number
  ): Promise<{ diff: Record<string, any>; summary: string }> {
    const [fromRev, toRev] = await Promise.all([
      this.getRevision(branchId, fromRevision),
      this.getRevision(branchId, toRevision)
    ]);
    
    if (!fromRev || !toRev) {
      throw new Error('One or both revisions not found');
    }
    
    const diff = this.computeDiff(fromRev.content, toRev.content);
    const changes = Object.entries(diff).filter(([_, v]) => v.action !== 'unchanged');
    
    const summary = `${changes.length} section(s) changed between r${fromRevision} and r${toRevision}`;
    
    return { diff, summary };
  }
  
  // Helper methods
  
  private computeDiff(oldContent: Record<string, any>, newContent: Record<string, any>): Record<string, any> {
    const diff: Record<string, any> = {};
    const allKeys = new Set([...Object.keys(oldContent), ...Object.keys(newContent)]);
    
    for (const key of allKeys) {
      if (!(key in oldContent)) {
        diff[key] = { action: 'added' };
      } else if (!(key in newContent)) {
        diff[key] = { action: 'deleted' };
      } else if (JSON.stringify(oldContent[key]) !== JSON.stringify(newContent[key])) {
        diff[key] = { action: 'modified' };
      } else {
        diff[key] = { action: 'unchanged' };
      }
    }
    
    return diff;
  }
  
  private computeHash(content: Record<string, any>): string {
    const str = JSON.stringify(content, Object.keys(content).sort());
    return crypto.createHash('sha256').update(str).digest('hex').substring(0, 16);
  }
  
  private computeTotalWordCount(content: Record<string, any>): number {
    let total = 0;
    for (const value of Object.values(content)) {
      if (typeof value === 'string') {
        total += value.split(/\s+/).filter(w => w.length > 0).length;
      }
    }
    return total;
  }
  
  private computeSectionWordCounts(content: Record<string, any>): Record<string, number> {
    const counts: Record<string, number> = {};
    for (const [key, value] of Object.entries(content)) {
      if (typeof value === 'string') {
        counts[key] = value.split(/\s+/).filter(w => w.length > 0).length;
      }
    }
    return counts;
  }
  
  private mapBranch(row: any): Branch {
    return {
      id: row.id,
      manuscriptId: row.manuscript_id,
      branchName: row.branch_name,
      parentBranch: row.parent_branch,
      status: row.status,
      description: row.description,
      versionHash: row.version_hash,
      wordCounts: row.word_counts,
      createdBy: row.created_by,
      createdAt: row.created_at,
      updatedAt: row.updated_at
    };
  }
  
  private mapRevision(row: any): Revision {
    return {
      id: row.id,
      branchId: row.branch_id,
      revisionNumber: row.revision_number,
      content: row.content,
      sectionsChanged: row.sections_changed || [],
      diffFromParent: row.diff_from_parent,
      wordCount: row.word_count,
      commitMessage: row.commit_message,
      createdBy: row.created_by,
      createdAt: row.created_at
    };
  }
}

// TODO: Add unit tests for audit event emission (createBranch, createRevision, mergeBranch, archiveBranch)
// when a test harness exists; no branch-persistence*.test.ts found yet.
export const branchPersistenceService = BranchPersistenceService.getInstance();
export default branchPersistenceService;
