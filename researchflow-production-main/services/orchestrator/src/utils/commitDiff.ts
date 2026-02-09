import { createHash } from 'node:crypto';

export type SectionContent = Record<string, string>;

export type CommitDiffSummary = {
  changed_sections_count: number;
  changed_section_keys: string[];
  added_sections_count: number;
  added_section_keys: string[];
  removed_sections_count: number;
  removed_section_keys: string[];
  modified_sections_count: number;
  modified_section_keys: string[];
  old_total_word_count: number;
  new_total_word_count: number;
  word_count_delta: number;
};

export type ComputeUnifiedDiffOptions = {
  /**
   * When true (default), output must not contain raw section values.
   * When false, diff lines include escaped raw values.
   */
  hipaaMode?: boolean;
  /**
   * Number of context lines around changes.
   */
  contextLines?: number;
  /**
   * Optional salt to reduce dictionary-attack risk against hashes while remaining deterministic.
   */
  hashSalt?: string;
  /**
   * How many hex chars of the hash to include (default: 12).
   */
  hashLength?: number;
  /**
   * Include per-section word counts in HIPAA mode (default: true).
   */
  includeWordCounts?: boolean;
};

function assertSectionContent(input: unknown, label: string): asserts input is SectionContent {
  if (input === null || typeof input !== 'object' || Array.isArray(input)) {
    throw new TypeError(`${label} must be an object keyed by section ID with string values`);
  }
  for (const [key, value] of Object.entries(input as Record<string, unknown>)) {
    if (typeof value !== 'string') {
      throw new TypeError(`${label}.${key} must be a string`);
    }
  }
}

function sortedKeys(obj: SectionContent): string[] {
  return Object.keys(obj).sort((a, b) => a.localeCompare(b));
}

function countWords(text: string): number {
  const trimmed = text.trim();
  if (!trimmed) return 0;
  return trimmed.split(/\s+/).length;
}

function sha256Hex(input: string): string {
  return createHash('sha256').update(input, 'utf8').digest('hex');
}

function escapeForSingleLine(value: string): string {
  return value.replace(/\r\n/g, '\n').replace(/\n/g, '\\n');
}

type DiffOp =
  | { type: 'equal'; line: string }
  | { type: 'delete'; line: string }
  | { type: 'insert'; line: string };

function computeLcsOps(oldLines: string[], newLines: string[]): DiffOp[] {
  const n = oldLines.length;
  const m = newLines.length;

  const dp: number[][] = Array.from({ length: n + 1 }, () => Array(m + 1).fill(0));
  for (let i = n - 1; i >= 0; i -= 1) {
    for (let j = m - 1; j >= 0; j -= 1) {
      dp[i][j] =
        oldLines[i] === newLines[j]
          ? dp[i + 1][j + 1] + 1
          : Math.max(dp[i + 1][j], dp[i][j + 1]);
    }
  }

  const ops: DiffOp[] = [];
  let i = 0;
  let j = 0;
  while (i < n && j < m) {
    if (oldLines[i] === newLines[j]) {
      ops.push({ type: 'equal', line: oldLines[i] });
      i += 1;
      j += 1;
      continue;
    }
    if (dp[i + 1][j] >= dp[i][j + 1]) {
      ops.push({ type: 'delete', line: oldLines[i] });
      i += 1;
    } else {
      ops.push({ type: 'insert', line: newLines[j] });
      j += 1;
    }
  }

  while (i < n) {
    ops.push({ type: 'delete', line: oldLines[i] });
    i += 1;
  }
  while (j < m) {
    ops.push({ type: 'insert', line: newLines[j] });
    j += 1;
  }

  return ops;
}

function unifiedDiffFromOps(
  oldLabel: string,
  newLabel: string,
  ops: DiffOp[],
  contextLines: number
): string {
  const oldLineAtOp: number[] = [];
  const newLineAtOp: number[] = [];

  let oldLine = 1;
  let newLine = 1;
  for (const op of ops) {
    oldLineAtOp.push(oldLine);
    newLineAtOp.push(newLine);
    if (op.type === 'equal' || op.type === 'delete') oldLine += 1;
    if (op.type === 'equal' || op.type === 'insert') newLine += 1;
  }

  const headerLines = [`--- ${oldLabel}`, `+++ ${newLabel}`];
  const hunkLines: string[] = [];

  let idx = 0;
  while (idx < ops.length) {
    while (idx < ops.length && ops[idx].type === 'equal') idx += 1;
    if (idx >= ops.length) break;

    const hunkStartIdx = Math.max(0, idx - contextLines);
    let hunkEndIdx = idx;
    let lastChangeIdx = idx;

    while (hunkEndIdx < ops.length) {
      if (ops[hunkEndIdx].type !== 'equal') lastChangeIdx = hunkEndIdx;
      hunkEndIdx += 1;

      if (hunkEndIdx - lastChangeIdx > contextLines) {
        hunkEndIdx = Math.min(ops.length, lastChangeIdx + contextLines + 1);
        break;
      }
    }

    const slice = ops.slice(hunkStartIdx, hunkEndIdx);
    const oldStart = oldLineAtOp[hunkStartIdx] ?? oldLine;
    const newStart = newLineAtOp[hunkStartIdx] ?? newLine;
    const oldCount = slice.filter((o) => o.type === 'equal' || o.type === 'delete').length;
    const newCount = slice.filter((o) => o.type === 'equal' || o.type === 'insert').length;

    hunkLines.push(`@@ -${oldStart},${oldCount} +${newStart},${newCount} @@`);
    for (const op of slice) {
      if (op.type === 'equal') hunkLines.push(` ${op.line}`);
      else if (op.type === 'delete') hunkLines.push(`-${op.line}`);
      else hunkLines.push(`+${op.line}`);
    }

    idx = hunkEndIdx;
  }

  if (hunkLines.length === 0) return `${headerLines.join('\n')}\n`;
  return `${headerLines.join('\n')}\n${hunkLines.join('\n')}\n`;
}

function toHipaaLines(content: SectionContent, options: Required<Pick<ComputeUnifiedDiffOptions, 'hashSalt' | 'hashLength' | 'includeWordCounts'>>): string[] {
  const { hashSalt, hashLength, includeWordCounts } = options;
  const keys = sortedKeys(content);
  return keys.map((key) => {
    const value = content[key] ?? '';
    const digest = sha256Hex(`${hashSalt}${value}`).slice(0, Math.max(1, hashLength));
    const wordCount = includeWordCounts ? ` words=${countWords(value)}` : '';
    return `${key}\tsha256=${digest}${wordCount}`;
  });
}

function toRawLines(content: SectionContent): string[] {
  const keys = sortedKeys(content);
  return keys.map((key) => `${key}\t${escapeForSingleLine(content[key] ?? '')}`);
}

export function computeSectionSummary(oldContent: unknown, newContent: unknown): CommitDiffSummary {
  assertSectionContent(oldContent, 'oldContent');
  assertSectionContent(newContent, 'newContent');

  const oldKeys = new Set(sortedKeys(oldContent));
  const newKeys = new Set(sortedKeys(newContent));

  const added = [...newKeys].filter((k) => !oldKeys.has(k)).sort((a, b) => a.localeCompare(b));
  const removed = [...oldKeys].filter((k) => !newKeys.has(k)).sort((a, b) => a.localeCompare(b));
  const modified = [...newKeys]
    .filter((k) => oldKeys.has(k) && oldContent[k] !== newContent[k])
    .sort((a, b) => a.localeCompare(b));

  const changed = [...new Set([...added, ...removed, ...modified])].sort((a, b) =>
    a.localeCompare(b)
  );

  const oldTotalWords = sortedKeys(oldContent).reduce((sum, k) => sum + countWords(oldContent[k]), 0);
  const newTotalWords = sortedKeys(newContent).reduce((sum, k) => sum + countWords(newContent[k]), 0);

  return {
    changed_sections_count: changed.length,
    changed_section_keys: changed,
    added_sections_count: added.length,
    added_section_keys: added,
    removed_sections_count: removed.length,
    removed_section_keys: removed,
    modified_sections_count: modified.length,
    modified_section_keys: modified,
    old_total_word_count: oldTotalWords,
    new_total_word_count: newTotalWords,
    word_count_delta: newTotalWords - oldTotalWords,
  };
}

export function computeUnifiedDiff(
  oldContent: unknown,
  newContent: unknown,
  options: ComputeUnifiedDiffOptions = {}
): string {
  assertSectionContent(oldContent, 'oldContent');
  assertSectionContent(newContent, 'newContent');

  const hipaaMode = options.hipaaMode ?? true;
  const contextLines = options.contextLines ?? 3;
  const hashSalt = options.hashSalt ?? '';
  const hashLength = options.hashLength ?? 12;
  const includeWordCounts = options.includeWordCounts ?? true;

  const oldLines = hipaaMode
    ? toHipaaLines(oldContent, { hashSalt, hashLength, includeWordCounts })
    : toRawLines(oldContent);
  const newLines = hipaaMode
    ? toHipaaLines(newContent, { hashSalt, hashLength, includeWordCounts })
    : toRawLines(newContent);

  const ops = computeLcsOps(oldLines, newLines);
  return unifiedDiffFromOps('old', 'new', ops, Math.max(0, contextLines));
}

