/**
 * Final PHI Scan Bridge Service
 *
 * This service performs a final PHI detection pass before export/submission.
 * It is intentionally conservative.
 */

export type PhiRiskLevel = 'NONE' | 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';

export interface PhiIdentifier {
  type: string;
  match: string;
  confidence: number; // 0..1
  offsets?: { start: number; end: number };
}

export interface FinalPhiScanInput {
  text: string;
  /** Optional: treat any finding as blocking */
  strict?: boolean;
}

export interface FinalPhiScanResult {
  ok: boolean;
  timestamp: string;
  hasPhi: boolean;
  riskLevel: PhiRiskLevel;
  identifiers: PhiIdentifier[];
  redactedPreview?: string;
}

function clamp01(n: number): number {
  if (Number.isNaN(n)) return 0;
  return Math.max(0, Math.min(1, n));
}

function redact(text: string): string {
  // Keep it simple; avoid pulling in heavy deps.
  return text
    .replace(/\b\d{3}-\d{2}-\d{4}\b/g, '[REDACTED-SSN]')
    .replace(/\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b/gi, '[REDACTED-EMAIL]')
    .replace(/\b\d{10}\b/g, '[REDACTED-PHONE]')
    .replace(/\b\(\d{3}\)\s*\d{3}-\d{4}\b/g, '[REDACTED-PHONE]')
    .replace(/\bMRN\s*[:#]?\s*\d+\b/gi, '[REDACTED-MRN]');
}

const RULES: Array<{
  type: string;
  re: RegExp;
  confidence: number;
  risk: PhiRiskLevel;
}> = [
  { type: 'SSN', re: /\b\d{3}-\d{2}-\d{4}\b/g, confidence: 0.95, risk: 'CRITICAL' },
  { type: 'EMAIL', re: /\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b/gi, confidence: 0.9, risk: 'CRITICAL' },
  { type: 'PHONE_US', re: /\b\(\d{3}\)\s*\d{3}-\d{4}\b/g, confidence: 0.8, risk: 'HIGH' },
  { type: 'PHONE_10D', re: /\b\d{10}\b/g, confidence: 0.6, risk: 'MEDIUM' },
  { type: 'MRN', re: /\bMRN\s*[:#]?\s*\d+\b/gi, confidence: 0.75, risk: 'HIGH' },
  { type: 'DOB_TOKEN', re: /\b(dob|date of birth)\b/gi, confidence: 0.55, risk: 'LOW' },
  { type: 'PATIENT_TOKEN', re: /\bpatient\b/gi, confidence: 0.35, risk: 'LOW' },
];

function worstRisk(a: PhiRiskLevel, b: PhiRiskLevel): PhiRiskLevel {
  const order: PhiRiskLevel[] = ['NONE', 'LOW', 'MEDIUM', 'HIGH', 'CRITICAL'];
  return order[Math.max(order.indexOf(a), order.indexOf(b))] ?? 'NONE';
}

function scanIdentifiers(text: string): { identifiers: PhiIdentifier[]; riskLevel: PhiRiskLevel } {
  const identifiers: PhiIdentifier[] = [];
  let riskLevel: PhiRiskLevel = 'NONE';

  for (const rule of RULES) {
    rule.re.lastIndex = 0;
    let match: RegExpExecArray | null;
    while ((match = rule.re.exec(text))) {
      const start = match.index;
      const end = match.index + match[0].length;
      identifiers.push({
        type: rule.type,
        match: match[0].slice(0, 64),
        confidence: clamp01(rule.confidence),
        offsets: { start, end },
      });
      riskLevel = worstRisk(riskLevel, rule.risk);
    }
  }

  return { identifiers, riskLevel };
}

/**
 * Bridge method: scan
 */
export async function scan(input: FinalPhiScanInput): Promise<FinalPhiScanResult> {
  const text = input?.text ?? '';
  const strict = Boolean(input?.strict);

  const { identifiers, riskLevel } = scanIdentifiers(text);
  const hasPhi = identifiers.length > 0 && riskLevel !== 'NONE';

  const ok = strict ? !hasPhi : riskLevel !== 'CRITICAL' && riskLevel !== 'HIGH';

  return {
    ok,
    timestamp: new Date().toISOString(),
    hasPhi,
    riskLevel,
    identifiers,
    redactedPreview: redact(text).slice(0, 5000),
  };
}

const finalPhiScanService = { scan };
export default finalPhiScanService;
