/**
 * Compliance Checker Bridge Service
 *
 * Bridge-friendly TypeScript service exposed via orchestrator /api/services.
 *
 * Responsibilities:
 * - HIPAA / IRB / GDPR-oriented compliance scan of text payloads
 * - Lightweight rule-based checks suitable for pre-export gating
 *
 * Notes:
 * - This module is intentionally dependency-light. It can be swapped with a
 *   stronger detector later (NLP / ML / external vendor) without changing the
 *   bridge contract.
 */

export type ComplianceRegime = 'HIPAA' | 'IRB' | 'GDPR';

export interface ComplianceScanInput {
  /** Arbitrary text to scan (manuscript section, abstract, full draft, etc.) */
  text: string;

  /** Optional: explicit regimes to run. Defaults to all. */
  regimes?: ComplianceRegime[];

  /** Optional: free-form metadata used only for reporting. */
  context?: Record<string, unknown>;
}

export type ComplianceFindingSeverity = 'info' | 'warning' | 'critical';

export interface ComplianceFinding {
  id: string;
  regime: ComplianceRegime;
  severity: ComplianceFindingSeverity;
  title: string;
  description: string;
  /** 0..1 heuristic confidence */
  confidence: number;
  /** Optional redacted snippet */
  snippet?: string;
  /** Optional location hints (best-effort) */
  offsets?: { start: number; end: number };
  remediation?: string;
}

export interface ComplianceScanResult {
  ok: boolean;
  timestamp: string;
  regimes: ComplianceRegime[];
  summary: {
    findings: number;
    critical: number;
    warnings: number;
    info: number;
  };
  findings: ComplianceFinding[];
}

function clamp01(n: number): number {
  if (Number.isNaN(n)) return 0;
  return Math.max(0, Math.min(1, n));
}

function safeSnippet(text: string, start: number, end: number): string {
  const s = Math.max(0, Math.min(text.length, start));
  const e = Math.max(0, Math.min(text.length, end));
  const raw = text.slice(s, e);
  // Redact obvious digit runs in snippet to avoid echoing sensitive data.
  return raw.replace(/\d{2,}/g, (m) => '*'.repeat(Math.min(m.length, 12)));
}

function pushFinding(
  findings: ComplianceFinding[],
  partial: Omit<ComplianceFinding, 'id'> & { id?: string }
): void {
  findings.push({
    id: partial.id ?? `${partial.regime}:${partial.title}`,
    ...partial,
    confidence: clamp01(partial.confidence),
  });
}

/**
 * Minimal heuristic patterns for compliance signals.
 *
 * These are *not* definitive legal/compliance determinations.
 */
const PATTERNS = {
  HIPAA: [
    {
      title: 'Possible PHI present (generic)',
      severity: 'warning' as const,
      // Broad: terms often used in clinical contexts.
      re: /\b(patient|mrn|medical record|diagnosis|treatment|clinic|hospital)\b/i,
      confidence: 0.35,
      remediation:
        'Ensure no Protected Health Information (PHI) is included. De-identify or redact before sharing/exporting.',
    },
    {
      title: 'Possible identifiers (SSN-like pattern)',
      severity: 'critical' as const,
      re: /\b\d{3}-\d{2}-\d{4}\b/g,
      confidence: 0.9,
      remediation:
        'Remove or redact identifier patterns. If real PHI is present, do not export externally.',
    },
    {
      title: 'Possible date of birth mention',
      severity: 'warning' as const,
      re: /\b(dob|date of birth)\b/i,
      confidence: 0.6,
      remediation:
        'Avoid including DOB or combine with other identifiers. Use age ranges and de-identified references.',
    },
  ],

  IRB: [
    {
      title: 'Human subjects / IRB language detected',
      severity: 'warning' as const,
      re: /\b(irb|institutional review board|human subjects|informed consent)\b/i,
      confidence: 0.6,
      remediation:
        'Confirm IRB approval/waiver details are appropriate and do not include sensitive subject information.',
    },
    {
      title: 'Consent / enrollment signals',
      severity: 'info' as const,
      re: /\b(consent(ed)?|enroll(ed|ment)?|participants?)\b/i,
      confidence: 0.35,
      remediation:
        'Ensure consent procedures are described at an appropriate level without exposing participant identifiers.',
    },
  ],

  GDPR: [
    {
      title: 'Personal data mention (generic)',
      severity: 'warning' as const,
      re: /\b(personal data|data subject|identifiable|pseudonymi[sz]e|anonymi[sz]e)\b/i,
      confidence: 0.45,
      remediation:
        'Verify GDPR lawful basis and ensure exported content is anonymized/pseudonymized as required.',
    },
    {
      title: 'Email-like identifier pattern',
      severity: 'critical' as const,
      re: /\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b/gi,
      confidence: 0.85,
      remediation:
        'Remove or redact direct identifiers (emails). Use anonymized identifiers if needed.',
    },
  ],
};

function runRegimeScan(text: string, regime: ComplianceRegime): ComplianceFinding[] {
  const findings: ComplianceFinding[] = [];
  const rules = PATTERNS[regime];

  for (const rule of rules) {
    // Global regex returns multiple matches, non-global returns at most one.
    if (rule.re.global) {
      let match: RegExpExecArray | null;
      rule.re.lastIndex = 0;
      while ((match = rule.re.exec(text))) {
        const start = match.index;
        const end = match.index + match[0].length;
        pushFinding(findings, {
          regime,
          severity: rule.severity,
          title: rule.title,
          description: `Detected pattern: ${rule.title}`,
          confidence: rule.confidence,
          snippet: safeSnippet(text, Math.max(0, start - 20), Math.min(text.length, end + 20)),
          offsets: { start, end },
          remediation: rule.remediation,
        });
      }
    } else {
      const m = text.match(rule.re);
      if (m) {
        // Best-effort location for first occurrence
        const idx = text.search(rule.re);
        const start = idx >= 0 ? idx : 0;
        const end = idx >= 0 ? Math.min(text.length, start + (m[0]?.length ?? 0)) : 0;
        pushFinding(findings, {
          regime,
          severity: rule.severity,
          title: rule.title,
          description: `Detected pattern: ${rule.title}`,
          confidence: rule.confidence,
          snippet: safeSnippet(text, Math.max(0, start - 20), Math.min(text.length, end + 20)),
          offsets: idx >= 0 ? { start, end } : undefined,
          remediation: rule.remediation,
        });
      }
    }
  }

  return findings;
}

function summarize(findings: ComplianceFinding[]): ComplianceScanResult['summary'] {
  const summary = { findings: findings.length, critical: 0, warnings: 0, info: 0 };
  for (const f of findings) {
    if (f.severity === 'critical') summary.critical += 1;
    else if (f.severity === 'warning') summary.warnings += 1;
    else summary.info += 1;
  }
  return summary;
}

/**
 * Bridge method: scan
 */
export async function scan(input: ComplianceScanInput): Promise<ComplianceScanResult> {
  const text = input?.text ?? '';
  const regimes: ComplianceRegime[] =
    input?.regimes && input.regimes.length > 0 ? input.regimes : ['HIPAA', 'IRB', 'GDPR'];

  const findings = regimes.flatMap((r) => runRegimeScan(text, r));
  // Basic gating: any critical finding fails.
  const ok = findings.every((f) => f.severity !== 'critical');

  return {
    ok,
    timestamp: new Date().toISOString(),
    regimes,
    summary: summarize(findings),
    findings,
  };
}

const complianceCheckerService = { scan };
export default complianceCheckerService;
