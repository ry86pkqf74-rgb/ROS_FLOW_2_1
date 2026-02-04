/**
 * Git-Like Manuscript Version Control
 * Features: Branch creation, three-way merge, diff generation, AI suggestions
 */

import { db } from "../../db";
import { sql } from "drizzle-orm";
import { createHash } from "crypto";
import { logAction } from "./audit-service";

export interface ManuscriptBranch {
  id: string;
  name: string;
  baseVersionId: string;
  headVersionId: string;
  createdBy: string;
  createdAt: Date;
  status: "active" | "merged" | "abandoned";
}

export interface MergeResult {
  success: boolean;
  conflicts: ConflictBlock[];
  mergedContent?: string;
  newVersionId?: string;
}

export interface ConflictBlock {
  startLine: number;
  endLine: number;
  ourContent: string;
  theirContent: string;
  baseContent: string;
}

export interface DiffOperation {
  operation: "equal" | "insert" | "delete";
  text: string;
  fromLine?: number;
  toLine?: number;
}

export interface DiffResult {
  fromVersionId: string;
  toVersionId: string;
  addedLines: number;
  removedLines: number;
  unchangedLines: number;
  operations: DiffOperation[];
  summary: string;
}

export interface VersionNode {
  id: string;
  branchId: string;
  branchName: string;
  revisionNumber: number;
  createdAt: Date;
  createdBy?: string;
  parentId?: string | null;
  children: VersionNode[];
  commitMessage?: string;
  wordCount?: number;
}

type RawBranchRow = {
  id: string;
  manuscript_id: string;
  branch_name: string;
  parent_branch: string | null;
  status: string;
  created_by: string | null;
  created_at: Date;
  updated_at: Date;
};

type RawRevisionRow = {
  id: string;
  branch_id: string;
  revision_number: number;
  content: any;
  sections_changed: string[] | null;
  diff_from_parent: any;
  word_count: number | null;
  commit_message: string | null;
  created_by: string | null;
  created_at: Date;
  branch_name?: string;
};

type VersionRecord = {
  id: string;
  content: any;
  createdAt?: Date;
  createdBy?: string | null;
  source: "revision" | "version";
  branchId?: string;
  branchName?: string;
};

type Edit = {
  baseStart: number;
  baseEnd: number;
  newLines: string[];
};

const STATUS_MAP: Record<string, ManuscriptBranch["status"]> = {
  active: "active",
  merged: "merged",
  archived: "abandoned",
  deleted: "abandoned",
  abandoned: "abandoned",
};

function ensureDb() {
  if (!db) {
    throw new Error("Database not initialized");
  }
}

function normalizeBranchStatus(status: string): ManuscriptBranch["status"] {
  return STATUS_MAP[status] ?? "active";
}

function buildContentText(content: any): string {
  if (!content) {
    return "";
  }

  if (typeof content === "string") {
    return content;
  }

  if (typeof content?.text === "string") {
    return content.text;
  }

  const sections = content?.sections;
  if (sections && typeof sections === "object") {
    return Object.entries(sections)
      .map(([sectionId, section]) => {
        const sectionContent =
          typeof (section as any)?.content === "string"
            ? (section as any).content
            : "";
        return `## ${sectionId}\n\n${sectionContent}`.trim();
      })
      .filter(Boolean)
      .join("\n\n");
  }

  try {
    return JSON.stringify(content, null, 2);
  } catch {
    return String(content);
  }
}

function computeWordCount(content: any): number {
  const text = buildContentText(content);
  return text.split(/\s+/).filter(Boolean).length;
}

function computeSectionWordCounts(content: any): Record<string, number> {
  const sections = content?.sections;
  if (!sections || typeof sections !== "object") {
    return { body: computeWordCount(content) };
  }

  const counts: Record<string, number> = {};
  for (const [sectionId, section] of Object.entries(sections)) {
    const sectionText =
      typeof (section as any)?.content === "string" ? (section as any).content : "";
    counts[sectionId] = sectionText.split(/\s+/).filter(Boolean).length;
  }
  return counts;
}

function hashContent(content: any): string {
  const normalized = buildContentText(content);
  return createHash("sha256").update(normalized).digest("hex").slice(0, 16);
}

function computeLcsTable(a: string[], b: string[]): number[][] {
  const m = a.length;
  const n = b.length;
  const dp = Array.from({ length: m + 1 }, () => Array(n + 1).fill(0));

  for (let i = 1; i <= m; i++) {
    for (let j = 1; j <= n; j++) {
      if (a[i - 1] === b[j - 1]) {
        dp[i][j] = dp[i - 1][j - 1] + 1;
      } else {
        dp[i][j] = Math.max(dp[i - 1][j], dp[i][j - 1]);
      }
    }
  }

  return dp;
}

function diffLines(fromLines: string[], toLines: string[]): DiffOperation[] {
  const dp = computeLcsTable(fromLines, toLines);
  const ops: DiffOperation[] = [];
  let i = fromLines.length;
  let j = toLines.length;

  while (i > 0 || j > 0) {
    if (i > 0 && j > 0 && fromLines[i - 1] === toLines[j - 1]) {
      ops.unshift({ operation: "equal", text: fromLines[i - 1] });
      i--;
      j--;
    } else if (j > 0 && (i === 0 || dp[i][j - 1] >= dp[i - 1][j])) {
      ops.unshift({ operation: "insert", text: toLines[j - 1] });
      j--;
    } else {
      ops.unshift({ operation: "delete", text: fromLines[i - 1] });
      i--;
    }
  }

  return ops;
}

function buildEdits(baseLines: string[], otherLines: string[]): Edit[] {
  const operations = diffLines(baseLines, otherLines);
  const edits: Edit[] = [];
  let baseIndex = 0;
  let current: Edit | null = null;

  const flush = () => {
    if (current) {
      edits.push(current);
      current = null;
    }
  };

  for (const op of operations) {
    if (op.operation === "equal") {
      flush();
      baseIndex++;
      continue;
    }

    if (op.operation === "delete") {
      if (!current) {
        current = {
          baseStart: baseIndex,
          baseEnd: baseIndex + 1,
          newLines: [],
        };
      } else {
        current.baseEnd = baseIndex + 1;
      }
      baseIndex++;
      continue;
    }

    if (op.operation === "insert") {
      if (!current) {
        current = {
          baseStart: baseIndex,
          baseEnd: baseIndex,
          newLines: [op.text],
        };
      } else {
        current.newLines.push(op.text);
      }
    }
  }

  flush();
  return edits;
}

function editsEqual(a: Edit, b: Edit): boolean {
  if (a.baseStart !== b.baseStart || a.baseEnd !== b.baseEnd) {
    return false;
  }
  if (a.newLines.length !== b.newLines.length) {
    return false;
  }
  for (let i = 0; i < a.newLines.length; i++) {
    if (a.newLines[i] !== b.newLines[i]) {
      return false;
    }
  }
  return true;
}

function rangesOverlap(a: Edit, b: Edit): boolean {
  const aStart = a.baseStart;
  const aEnd = a.baseEnd;
  const bStart = b.baseStart;
  const bEnd = b.baseEnd;
  if (aStart === aEnd && bStart === bEnd) {
    return aStart === bStart;
  }
  return aStart < bEnd && bStart < aEnd;
}

function buildConflict(
  baseLines: string[],
  editA: Edit,
  editB: Edit
): ConflictBlock {
  const start = Math.min(editA.baseStart, editB.baseStart);
  const end = Math.max(editA.baseEnd, editB.baseEnd);
  const baseContent = baseLines.slice(start, end).join("\n");
  const ourContent = editA.newLines.join("\n");
  const theirContent = editB.newLines.join("\n");

  return {
    startLine: start + 1,
    endLine: Math.max(start + 1, end),
    ourContent,
    theirContent,
    baseContent,
  };
}

function resolveConflict(
  conflict: ConflictBlock,
  strategy: "ours" | "theirs" | "manual"
): string[] {
  if (strategy === "ours") {
    return conflict.ourContent ? conflict.ourContent.split("\n") : [];
  }
  if (strategy === "theirs") {
    return conflict.theirContent ? conflict.theirContent.split("\n") : [];
  }
  const marker = [
    "<<<<<<< ours",
    conflict.ourContent,
    "=======",
    conflict.theirContent,
    ">>>>>>> theirs",
  ]
    .filter(Boolean)
    .join("\n");
  return marker.split("\n");
}

function threeWayMergeText(
  baseText: string,
  ourText: string,
  theirText: string,
  strategy: "ours" | "theirs" | "manual"
): { mergedText: string; conflicts: ConflictBlock[] } {
  const baseLines = baseText.split("\n");
  const ourLines = ourText.split("\n");
  const theirLines = theirText.split("\n");

  const ourEdits = buildEdits(baseLines, ourLines);
  const theirEdits = buildEdits(baseLines, theirLines);

  let basePos = 0;
  let i = 0;
  let j = 0;
  const merged: string[] = [];
  const conflicts: ConflictBlock[] = [];

  while (basePos <= baseLines.length) {
    const ourEdit = ourEdits[i];
    const theirEdit = theirEdits[j];

    const nextStart = Math.min(
      ourEdit?.baseStart ?? baseLines.length,
      theirEdit?.baseStart ?? baseLines.length,
      baseLines.length
    );

    if (basePos < nextStart) {
      merged.push(...baseLines.slice(basePos, nextStart));
      basePos = nextStart;
      continue;
    }

    const ourActive = ourEdit && ourEdit.baseStart === basePos;
    const theirActive = theirEdit && theirEdit.baseStart === basePos;

    if (!ourActive && !theirActive) {
      if (basePos < baseLines.length) {
        merged.push(baseLines[basePos]);
        basePos++;
        continue;
      }
      break;
    }

    if (ourActive && theirActive) {
      if (editsEqual(ourEdit, theirEdit)) {
        merged.push(...ourEdit.newLines);
        basePos = Math.max(ourEdit.baseEnd, theirEdit.baseEnd);
        i++;
        j++;
        continue;
      }

      const conflict = buildConflict(baseLines, ourEdit, theirEdit);
      conflicts.push(conflict);
      if (strategy !== "manual") {
        merged.push(...resolveConflict(conflict, strategy));
      }
      basePos = Math.max(ourEdit.baseEnd, theirEdit.baseEnd);
      i++;
      j++;
      continue;
    }

    if (ourActive) {
      if (theirEdit && rangesOverlap(ourEdit, theirEdit)) {
        const conflict = buildConflict(baseLines, ourEdit, theirEdit);
        conflicts.push(conflict);
        if (strategy !== "manual") {
          merged.push(...resolveConflict(conflict, strategy));
        }
        basePos = Math.max(ourEdit.baseEnd, theirEdit.baseEnd);
        i++;
        j++;
        continue;
      }
      merged.push(...ourEdit.newLines);
      basePos = ourEdit.baseEnd;
      i++;
      continue;
    }

    if (theirActive) {
      if (ourEdit && rangesOverlap(ourEdit, theirEdit)) {
        const conflict = buildConflict(baseLines, ourEdit, theirEdit);
        conflicts.push(conflict);
        if (strategy !== "manual") {
          merged.push(...resolveConflict(conflict, strategy));
        }
        basePos = Math.max(ourEdit.baseEnd, theirEdit.baseEnd);
        i++;
        j++;
        continue;
      }
      merged.push(...theirEdit.newLines);
      basePos = theirEdit.baseEnd;
      j++;
      continue;
    }
  }

  return { mergedText: merged.join("\n"), conflicts };
}

function buildDiffResult(
  fromVersionId: string,
  toVersionId: string,
  fromText: string,
  toText: string
): DiffResult {
  const fromLines = fromText.split("\n");
  const toLines = toText.split("\n");
  const operations = diffLines(fromLines, toLines);
  let added = 0;
  let removed = 0;
  let unchanged = 0;
  let fromLine = 0;
  let toLine = 0;

  const detailedOps: DiffOperation[] = [];

  for (const op of operations) {
    if (op.operation === "equal") {
      fromLine++;
      toLine++;
      unchanged++;
      detailedOps.push({
        operation: "equal",
        text: op.text,
        fromLine,
        toLine,
      });
    } else if (op.operation === "insert") {
      toLine++;
      added++;
      detailedOps.push({
        operation: "insert",
        text: op.text,
        toLine,
      });
    } else {
      fromLine++;
      removed++;
      detailedOps.push({
        operation: "delete",
        text: op.text,
        fromLine,
      });
    }
  }

  const summaryParts: string[] = [];
  if (added > 0) summaryParts.push(`+${added}`);
  if (removed > 0) summaryParts.push(`-${removed}`);
  const summary = summaryParts.length ? summaryParts.join(", ") : "No changes";

  return {
    fromVersionId,
    toVersionId,
    addedLines: added,
    removedLines: removed,
    unchangedLines: unchanged,
    operations: detailedOps,
    summary,
  };
}

export class ManuscriptVersionService {
  private static instance: ManuscriptVersionService;

  private constructor() {}

  static getInstance(): ManuscriptVersionService {
    if (!this.instance) {
      this.instance = new ManuscriptVersionService();
    }
    return this.instance;
  }

  async createBranch(
    manuscriptId: string,
    name: string,
    fromVersionId: string
  ): Promise<ManuscriptBranch> {
    ensureDb();

    const existing = await db.execute(sql`
      SELECT id FROM manuscript_branches
      WHERE manuscript_id = ${manuscriptId} AND branch_name = ${name}
    `);

    if (existing.rows.length > 0) {
      throw new Error(`Branch '${name}' already exists`);
    }

    const baseVersion = await this.getVersionRecord(fromVersionId);
    if (!baseVersion) {
      throw new Error("Base version not found");
    }

    const branchResult = await db.execute(sql`
      INSERT INTO manuscript_branches (manuscript_id, branch_name, parent_branch, created_by)
      VALUES (${manuscriptId}, ${name}, ${baseVersion.branchName || "main"}, ${baseVersion.createdBy || "system"})
      RETURNING *
    `);

    const branchRow = branchResult.rows[0] as RawBranchRow;
    const branchId = branchRow.id;

    const revisionResult = await db.execute(sql`
      INSERT INTO manuscript_revisions (
        branch_id,
        revision_number,
        content,
        sections_changed,
        diff_from_parent,
        word_count,
        commit_message,
        created_by
      )
      VALUES (
        ${branchId},
        1,
        ${JSON.stringify(baseVersion.content)}::jsonb,
        ${JSON.stringify(Object.keys(baseVersion.content?.sections || {}))}::text[],
        ${JSON.stringify({ baseVersionId: fromVersionId })}::jsonb,
        ${computeWordCount(baseVersion.content)},
        ${`Branch created from ${fromVersionId}`},
        ${baseVersion.createdBy || "system"}
      )
      RETURNING *
    `);

    const revisionRow = revisionResult.rows[0] as RawRevisionRow;

    await db.execute(sql`
      UPDATE manuscript_branches
      SET version_hash = ${hashContent(baseVersion.content)},
          word_counts = ${JSON.stringify(computeSectionWordCounts(baseVersion.content))}::jsonb
      WHERE id = ${branchId}
    `);

    await logAction({
      eventType: "MANUSCRIPT_BRANCH_CREATED",
      action: "CREATE",
      resourceType: "MANUSCRIPT_BRANCH",
      resourceId: branchId,
      userId: branchRow.created_by || undefined,
      details: { manuscriptId, name, fromVersionId },
    });

    return {
      id: branchId,
      name,
      baseVersionId: fromVersionId,
      headVersionId: revisionRow.id,
      createdBy: branchRow.created_by || "system",
      createdAt: branchRow.created_at,
      status: normalizeBranchStatus(branchRow.status),
    };
  }

  async mergeBranch(
    branchId: string,
    targetBranch: string,
    strategy: "ours" | "theirs" | "manual"
  ): Promise<MergeResult> {
    ensureDb();

    const sourceBranch = await this.getBranchById(branchId);
    if (!sourceBranch) {
      throw new Error("Source branch not found");
    }

    const target = await this.getBranchByName(sourceBranch.manuscriptId, targetBranch);
    if (!target) {
      throw new Error("Target branch not found");
    }

    const [sourceHead, targetHead] = await Promise.all([
      this.getBranchHeadRevision(sourceBranch.id),
      this.getBranchHeadRevision(target.id),
    ]);

    if (!sourceHead || !targetHead) {
      throw new Error("Cannot merge branches without revisions");
    }

    const baseVersionId = await this.getBranchBaseVersionId(sourceBranch.id);
    const baseVersion = baseVersionId
      ? await this.getVersionRecord(baseVersionId)
      : null;

    const baseContent = baseVersion?.content ?? targetHead.content;
    const baseText = buildContentText(baseContent);
    const targetText = buildContentText(targetHead.content);
    const sourceText = buildContentText(sourceHead.content);

    const mergeResult = threeWayMergeText(
      baseText,
      targetText,
      sourceText,
      strategy
    );

    if (mergeResult.conflicts.length > 0 && strategy === "manual") {
      return {
        success: false,
        conflicts: mergeResult.conflicts,
      };
    }

    const mergedPayload = this.mergeStructuredContent(
      baseContent,
      targetHead.content,
      sourceHead.content,
      strategy
    );

    const insertResult = await db.execute(sql`
      INSERT INTO manuscript_revisions (
        branch_id,
        revision_number,
        content,
        sections_changed,
        diff_from_parent,
        word_count,
        commit_message,
        created_by
      )
      VALUES (
        ${target.id},
        ${targetHead.revision_number + 1},
        ${JSON.stringify(mergedPayload)}::jsonb,
        ${JSON.stringify(["merge"])}::text[],
        ${JSON.stringify({
          mergeBase: baseVersionId,
          sourceBranch: sourceBranch.id,
          targetBranch: target.id,
        })}::jsonb,
        ${computeWordCount(mergedPayload)},
        ${`Merged ${sourceBranch.name} into ${targetBranch}`},
        ${sourceBranch.createdBy || "system"}
      )
      RETURNING *
    `);

    const newRevision = insertResult.rows[0] as RawRevisionRow;

    await db.execute(sql`
      UPDATE manuscript_branches
      SET version_hash = ${hashContent(mergedPayload)},
          word_counts = ${JSON.stringify(computeSectionWordCounts(mergedPayload))}::jsonb
      WHERE id = ${target.id}
    `);

    await db.execute(sql`
      UPDATE manuscript_branches
      SET status = 'merged', merged_at = NOW()
      WHERE id = ${sourceBranch.id}
    `);

    await logAction({
      eventType: "MANUSCRIPT_BRANCH_MERGED",
      action: "MERGE",
      resourceType: "MANUSCRIPT_BRANCH",
      resourceId: target.id,
      userId: sourceBranch.createdBy || undefined,
      details: {
        manuscriptId: sourceBranch.manuscriptId,
        sourceBranch: sourceBranch.id,
        targetBranch: target.id,
        conflicts: mergeResult.conflicts.length,
      },
    });

    return {
      success: true,
      conflicts: mergeResult.conflicts,
      mergedContent: buildContentText(mergedPayload),
      newVersionId: newRevision.id,
    };
  }

  async diffVersions(v1: string, v2: string): Promise<DiffResult> {
    ensureDb();
    const [versionA, versionB] = await Promise.all([
      this.getVersionRecord(v1),
      this.getVersionRecord(v2),
    ]);

    if (!versionA || !versionB) {
      throw new Error("One or both versions not found");
    }

    const fromText = buildContentText(versionA.content);
    const toText = buildContentText(versionB.content);

    return buildDiffResult(v1, v2, fromText, toText);
  }

  async getVersionHistory(
    manuscriptId: string,
    branch?: string
  ): Promise<VersionNode[]> {
    ensureDb();

    const branchesResult = await db.execute(sql`
      SELECT *
      FROM manuscript_branches
      WHERE manuscript_id = ${manuscriptId}
      ${branch ? sql`AND branch_name = ${branch}` : sql``}
    `);

    if (branchesResult.rows.length === 0) {
      return [];
    }

    const branchRows = branchesResult.rows as RawBranchRow[];
    const branchIds = branchRows.map((b) => b.id);
    const branchIdList = sql.join(
      branchIds.map((id) => sql`${id}`),
      sql`, `
    );

    const revisionsResult = await db.execute(sql`
      SELECT r.*, b.branch_name
      FROM manuscript_revisions r
      JOIN manuscript_branches b ON b.id = r.branch_id
      WHERE r.branch_id IN (${branchIdList})
      ORDER BY r.created_at ASC, r.revision_number ASC
    `);

    const revisionRows = revisionsResult.rows as RawRevisionRow[];
    const nodeMap = new Map<string, VersionNode>();

    for (const row of revisionRows) {
      const parentId =
        row.revision_number > 1
          ? this.getPreviousRevisionId(revisionRows, row.branch_id, row.revision_number)
          : (row.diff_from_parent?.baseVersionId as string | undefined) || null;

      nodeMap.set(row.id, {
        id: row.id,
        branchId: row.branch_id,
        branchName: row.branch_name || "main",
        revisionNumber: row.revision_number,
        createdAt: row.created_at,
        createdBy: row.created_by || undefined,
        parentId: parentId || null,
        children: [],
        commitMessage: row.commit_message || undefined,
        wordCount: row.word_count ?? undefined,
      });
    }

    for (const node of nodeMap.values()) {
      if (node.parentId && nodeMap.has(node.parentId)) {
        nodeMap.get(node.parentId)!.children.push(node);
      }
    }

    const roots: VersionNode[] = [];
    for (const node of nodeMap.values()) {
      if (!node.parentId || !nodeMap.has(node.parentId)) {
        roots.push(node);
      }
    }

    return roots.sort((a, b) => a.createdAt.getTime() - b.createdAt.getTime());
  }

  async revertToVersion(manuscriptId: string, versionId: string): Promise<string> {
    ensureDb();

    const version = await this.getVersionRecord(versionId);
    if (!version) {
      throw new Error("Version not found");
    }

    const branch =
      version.branchId
        ? await this.getBranchById(version.branchId)
        : await this.getBranchByName(manuscriptId, "main");

    if (!branch) {
      throw new Error("Target branch not found");
    }

    const head = await this.getBranchHeadRevision(branch.id);
    if (!head) {
      throw new Error("Branch has no revisions");
    }

    const insertResult = await db.execute(sql`
      INSERT INTO manuscript_revisions (
        branch_id,
        revision_number,
        content,
        sections_changed,
        diff_from_parent,
        word_count,
        commit_message,
        created_by
      )
      VALUES (
        ${branch.id},
        ${head.revision_number + 1},
        ${JSON.stringify(version.content)}::jsonb,
        ${JSON.stringify(["revert"])}::text[],
        ${JSON.stringify({ revertedTo: versionId })}::jsonb,
        ${computeWordCount(version.content)},
        ${`Revert to ${versionId}`},
        ${version.createdBy || "system"}
      )
      RETURNING *
    `);

    const newRevision = insertResult.rows[0] as RawRevisionRow;

    await db.execute(sql`
      UPDATE manuscript_branches
      SET version_hash = ${hashContent(version.content)},
          word_counts = ${JSON.stringify(computeSectionWordCounts(version.content))}::jsonb
      WHERE id = ${branch.id}
    `);

    await logAction({
      eventType: "MANUSCRIPT_VERSION_REVERTED",
      action: "REVERT",
      resourceType: "MANUSCRIPT_REVISION",
      resourceId: newRevision.id,
      userId: version.createdBy || undefined,
      details: { manuscriptId, versionId },
    });

    return newRevision.id;
  }

  async getBranchById(branchId: string): Promise<{
    id: string;
    name: string;
    manuscriptId: string;
    createdBy?: string;
    createdAt: Date;
  } | null> {
    ensureDb();
    const result = await db.execute(sql`
      SELECT *
      FROM manuscript_branches
      WHERE id = ${branchId}
    `);

    if (result.rows.length === 0) return null;
    const row = result.rows[0] as RawBranchRow;

    return {
      id: row.id,
      name: row.branch_name,
      manuscriptId: row.manuscript_id,
      createdBy: row.created_by || undefined,
      createdAt: row.created_at,
    };
  }

  async getBranchByName(
    manuscriptId: string,
    branchName: string
  ): Promise<{ id: string; name: string; manuscriptId: string; createdBy?: string } | null> {
    ensureDb();
    const result = await db.execute(sql`
      SELECT *
      FROM manuscript_branches
      WHERE manuscript_id = ${manuscriptId} AND branch_name = ${branchName}
    `);

    if (result.rows.length === 0) return null;
    const row = result.rows[0] as RawBranchRow;

    return {
      id: row.id,
      name: row.branch_name,
      manuscriptId: row.manuscript_id,
      createdBy: row.created_by || undefined,
    };
  }

  async listBranches(manuscriptId: string): Promise<ManuscriptBranch[]> {
    ensureDb();
    const result = await db.execute(sql`
      SELECT *
      FROM manuscript_branches
      WHERE manuscript_id = ${manuscriptId}
      ORDER BY created_at ASC
    `);

    const branches = result.rows as RawBranchRow[];
    const output: ManuscriptBranch[] = [];

    for (const row of branches) {
      const head = await this.getBranchHeadRevision(row.id);
      const base = await this.getBranchBaseVersionId(row.id);
      output.push({
        id: row.id,
        name: row.branch_name,
        baseVersionId: base || head?.id || row.id,
        headVersionId: head?.id || row.id,
        createdBy: row.created_by || "system",
        createdAt: row.created_at,
        status: normalizeBranchStatus(row.status),
      });
    }

    return output;
  }

  async updateBranchStatus(
    branchId: string,
    status: "active" | "merged" | "abandoned"
  ): Promise<void> {
    ensureDb();
    await db.execute(sql`
      UPDATE manuscript_branches
      SET status = ${status}
      WHERE id = ${branchId}
    `);
  }

  async deleteBranch(branchId: string): Promise<void> {
    ensureDb();
    await db.execute(sql`
      UPDATE manuscript_branches
      SET status = 'deleted'
      WHERE id = ${branchId}
    `);
  }

  async getBranchHeadRevision(branchId: string): Promise<RawRevisionRow | null> {
    ensureDb();
    const result = await db.execute(sql`
      SELECT *
      FROM manuscript_revisions
      WHERE branch_id = ${branchId}
      ORDER BY revision_number DESC
      LIMIT 1
    `);

    if (result.rows.length === 0) return null;
    return result.rows[0] as RawRevisionRow;
  }

  async getBranchBaseVersionId(branchId: string): Promise<string | null> {
    ensureDb();
    const result = await db.execute(sql`
      SELECT diff_from_parent
      FROM manuscript_revisions
      WHERE branch_id = ${branchId}
      ORDER BY revision_number ASC
      LIMIT 1
    `);

    if (result.rows.length === 0) return null;
    const diff = (result.rows[0] as RawRevisionRow).diff_from_parent as any;
    if (diff?.baseVersionId) {
      return diff.baseVersionId as string;
    }
    return null;
  }

  async getVersionRecord(versionId: string): Promise<VersionRecord | null> {
    ensureDb();
    const revisionResult = await db.execute(sql`
      SELECT r.*, b.branch_name
      FROM manuscript_revisions r
      JOIN manuscript_branches b ON b.id = r.branch_id
      WHERE r.id = ${versionId}
    `);

    if (revisionResult.rows.length > 0) {
      const row = revisionResult.rows[0] as RawRevisionRow;
      return {
        id: row.id,
        content: row.content,
        createdAt: row.created_at,
        createdBy: row.created_by,
        source: "revision",
        branchId: row.branch_id,
        branchName: row.branch_name,
      };
    }

    const versionResult = await db.execute(sql`
      SELECT id, content, created_at, created_by
      FROM manuscript_versions
      WHERE id = ${versionId}
    `);

    if (versionResult.rows.length === 0) {
      return null;
    }

    const versionRow = versionResult.rows[0] as any;
    return {
      id: versionRow.id,
      content: versionRow.content,
      createdAt: versionRow.created_at,
      createdBy: versionRow.created_by,
      source: "version",
    };
  }

  private getPreviousRevisionId(
    revisions: RawRevisionRow[],
    branchId: string,
    revisionNumber: number
  ): string | null {
    const prev = revisions.find(
      (row) => row.branch_id === branchId && row.revision_number === revisionNumber - 1
    );
    return prev?.id || null;
  }

  private mergeStructuredContent(
    baseContent: any,
    targetContent: any,
    sourceContent: any,
    strategy: "ours" | "theirs" | "manual"
  ): any {
    const baseSections = baseContent?.sections;
    const targetSections = targetContent?.sections;
    const sourceSections = sourceContent?.sections;

    if (!baseSections || !targetSections || !sourceSections) {
      if (strategy === "theirs") {
        return sourceContent;
      }
      return targetContent;
    }

    const mergedSections: Record<string, any> = {};
    const allSectionIds = new Set([
      ...Object.keys(baseSections),
      ...Object.keys(targetSections),
      ...Object.keys(sourceSections),
    ]);

    for (const sectionId of allSectionIds) {
      const baseText = (baseSections[sectionId]?.content as string) || "";
      const targetText = (targetSections[sectionId]?.content as string) || "";
      const sourceText = (sourceSections[sectionId]?.content as string) || "";

      const merge = threeWayMergeText(baseText, targetText, sourceText, strategy);
      const mergedText =
        strategy === "manual" && merge.conflicts.length > 0
          ? targetText
          : merge.mergedText;

      mergedSections[sectionId] = {
        ...(targetSections[sectionId] || {}),
        content: mergedText,
      };
    }

    return {
      ...targetContent,
      sections: mergedSections,
    };
  }
}

export const manuscriptVersionService = ManuscriptVersionService.getInstance();
export default manuscriptVersionService;
