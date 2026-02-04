/**
 * Publication Prep Bridge Service
 *
 * Prepares a manuscript package for journal submission.
 *
 * Scope (this module):
 * - Validate required metadata
 * - Generate a structured submission checklist
 * - Provide a normalized "package" descriptor (not a real file export)
 */

export interface PublicationPrepInput {
  title: string;
  abstract?: string;
  manuscriptText: string;
  /** Target journal name (optional) */
  journal?: string;
  /** Optional author list */
  authors?: Array<{ name: string; email?: string; affiliation?: string; orcid?: string }>;
  /** Optional: keywords */
  keywords?: string[];
  /** Optional: include cover letter content */
  coverLetter?: string;
}

export type ChecklistItemStatus = 'PASS' | 'WARN' | 'FAIL';

export interface ChecklistItem {
  id: string;
  status: ChecklistItemStatus;
  title: string;
  details?: string;
}

export interface PublicationPrepResult {
  ok: boolean;
  timestamp: string;
  journal?: string;
  checklist: ChecklistItem[];
  package: {
    title: string;
    hasAbstract: boolean;
    wordCount: number;
    authorsCount: number;
    keywordsCount: number;
    artifacts: Array<{ name: string; mime: string; description: string }>;
  };
}

function wordCount(text: string): number {
  const t = (text ?? '').trim();
  if (!t) return 0;
  return t.split(/\s+/).length;
}

function checklistItem(id: string, status: ChecklistItemStatus, title: string, details?: string): ChecklistItem {
  return { id, status, title, details };
}

/**
 * Bridge method: prepare
 */
export async function prepare(input: PublicationPrepInput): Promise<PublicationPrepResult> {
  if (!input?.title?.trim()) {
    throw new Error('title is required');
  }
  if (!input?.manuscriptText?.trim()) {
    throw new Error('manuscriptText is required');
  }

  const wc = wordCount(input.manuscriptText);
  const authorsCount = input.authors?.length ?? 0;
  const keywordsCount = input.keywords?.length ?? 0;

  const checklist: ChecklistItem[] = [];

  checklist.push(
    checklistItem('title', 'PASS', 'Title present'),
    checklistItem('abstract', input.abstract?.trim() ? 'PASS' : 'WARN', 'Abstract present', input.abstract?.trim() ? undefined : 'Abstract missing'),
    checklistItem(
      'authors',
      authorsCount > 0 ? 'PASS' : 'WARN',
      'Author list provided',
      authorsCount > 0 ? undefined : 'No authors provided; journal systems usually require author metadata'
    ),
    checklistItem(
      'word-count',
      wc >= 250 ? 'PASS' : 'WARN',
      'Manuscript length looks reasonable',
      wc >= 250 ? `Word count: ${wc}` : `Word count: ${wc} (may be too short for typical submissions)`
    ),
    checklistItem(
      'keywords',
      keywordsCount >= 3 ? 'PASS' : 'WARN',
      'Keywords provided',
      keywordsCount >= 3 ? `Keywords: ${keywordsCount}` : `Keywords: ${keywordsCount} (journals often request 3–8 keywords)`
    )
  );

  if (input.coverLetter && input.coverLetter.trim().length < 200) {
    checklist.push(checklistItem('cover-letter', 'WARN', 'Cover letter length', 'Cover letter seems very short'));
  } else {
    checklist.push(checklistItem('cover-letter', input.coverLetter?.trim() ? 'PASS' : 'WARN', 'Cover letter included', input.coverLetter?.trim() ? undefined : 'No cover letter provided'));
  }

  const ok = checklist.every((c) => c.status !== 'FAIL');

  return {
    ok,
    timestamp: new Date().toISOString(),
    journal: input.journal,
    checklist,
    package: {
      title: input.title,
      hasAbstract: Boolean(input.abstract?.trim()),
      wordCount: wc,
      authorsCount,
      keywordsCount,
      artifacts: [
        { name: 'manuscript.txt', mime: 'text/plain', description: 'Normalized manuscript text' },
        { name: 'metadata.json', mime: 'application/json', description: 'Submission metadata (title/authors/keywords/journal)' },
        { name: 'checklist.json', mime: 'application/json', description: 'Automated pre-submission checklist results' },
      ],
    },
  };
}

const publicationPrepService = { prepare };
export default publicationPrepService;
