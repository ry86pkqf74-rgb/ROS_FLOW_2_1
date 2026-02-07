/**
 * AI-Assisted Editing Loops with RAG integration
 */

import { createHash, randomUUID } from "crypto";

import { sql } from "drizzle-orm";

import { db } from "../../db";
import { config } from "../config/env";

import { scanForPhi, redactPhiInData } from "./phi-protection";


export interface EditingSuggestion {
  sectionId: string;
  originalText: string;
  suggestedText: string;
  rationale: string;
  confidence: number;
  type: "grammar" | "clarity" | "style" | "citation" | "content";
}

export interface RefinementResult {
  manuscriptId: string;
  iterations: number;
  suggestionsGenerated: number;
  suggestionsApplied: number;
  updatedVersionId?: string;
  summary: string;
  sections?: Record<string, { content: string }>;
}

export interface StyleIssue {
  sectionId: string;
  category: "consistency" | "voice" | "citation" | "structure" | "tone";
  severity: "low" | "medium" | "high";
  message: string;
  example?: string;
}

export interface StyleReport {
  manuscriptId: string;
  createdAt: Date;
  metrics: Record<string, number>;
  issues: StyleIssue[];
  summary: string;
}

type StoredSuggestion = EditingSuggestion & {
  id: string;
  status: "pending" | "accepted" | "rejected" | "modified";
  createdAt?: Date;
};

type ManuscriptContent = {
  sections?: Record<string, { content?: string; [key: string]: any }>;
  text?: string;
  [key: string]: any;
};

function ensureDb() {
  if (!db) {
    throw new Error("Database not initialized");
  }
}

function computeHash(text: string): string {
  return createHash("sha256").update(text).digest("hex").slice(0, 16);
}

function wordCount(text: string): number {
  return text.split(/\s+/).filter(Boolean).length;
}

function splitSentences(text: string): string[] {
  return text
    .split(/(?<=[.!?])\s+/)
    .map((s) => s.trim())
    .filter(Boolean);
}

function detectPassiveVoice(sentence: string): boolean {
  return /\b(is|was|were|be|been|being)\b\s+\w+ed\b/i.test(sentence);
}

function detectRepeatedWords(text: string): string[] {
  const matches: string[] = [];
  const regex = /\b(\w+)\s+\1\b/gi;
  let match: RegExpExecArray | null;
  while ((match = regex.exec(text)) !== null) {
    matches.push(match[0]);
  }
  return matches;
}

function detectCitationStyle(text: string): "numeric" | "author-year" | "none" {
  if (/\[\d+\]/.test(text)) {
    return "numeric";
  }
  if (/\([A-Za-z][^)]*\d{4}[^)]*\)/.test(text)) {
    return "author-year";
  }
  return "none";
}

function normalizeSectionContent(content: ManuscriptContent, sectionId: string): string {
  if (content.sections && content.sections[sectionId]) {
    return content.sections[sectionId]?.content || "";
  }
  if (typeof content.text === "string") {
    return content.text;
  }
  return "";
}

async function queryRagGuidance(query: string): Promise<string[]> {
  const body = {
    collection: "ai_feedback_guidance",
    query,
    top_k: 3,
  };

  try {
    const response = await fetch(`${config.workerUrl}/agents/rag/search`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
      signal: AbortSignal.timeout(10000),
    });

    if (!response.ok) {
      return [];
    }

    const result = (await response.json()) as {
      matches?: Array<{ content: string }>;
    };

    return (result.matches || []).map((m) => m.content).filter(Boolean);
  } catch {
    return [];
  }
}

export class AIEditingService {
  private static instance: AIEditingService;
  private schemaReady = false;

  private constructor() {}

  static getInstance(): AIEditingService {
    if (!this.instance) {
      this.instance = new AIEditingService();
    }
    return this.instance;
  }

  async generateSuggestions(
    manuscriptId: string,
    sectionId: string
  ): Promise<EditingSuggestion[]> {
    ensureDb();
    await this.ensureSchema();

    const content = await this.fetchManuscriptContent(manuscriptId);
    const sectionText = normalizeSectionContent(content, sectionId);

    if (!sectionText) {
      return [];
    }

    const phiResult = scanForPhi(sectionText);
    const safeText = phiResult.detected ? redactPhiInData(sectionText) : sectionText;
    const ragHints = await queryRagGuidance(`editing ${sectionId}`);

    const suggestions = this.generateSuggestionsForText(sectionId, safeText, ragHints);
    const stored = await this.storeSuggestions(manuscriptId, sectionId, suggestions);

    return stored.map((s) => ({
      sectionId: s.sectionId,
      originalText: s.originalText,
      suggestedText: s.suggestedText,
      rationale: s.rationale,
      confidence: s.confidence,
      type: s.type,
      ...(s.id ? { id: s.id } : {}),
    })) as EditingSuggestion[];
  }

  async applyWithFeedback(
    suggestionId: string,
    feedback: "accept" | "reject" | "modify"
  ): Promise<void> {
    ensureDb();
    await this.ensureSchema();

    const existing = await db.execute(sql`
      SELECT id
      FROM manuscript_ai_suggestions
      WHERE id = ${suggestionId}
    `);

    if (existing.rows.length === 0) {
      throw new Error("Suggestion not found");
    }

    const status =
      feedback === "accept" ? "accepted" : feedback === "reject" ? "rejected" : "modified";

    await db.execute(sql`
      UPDATE manuscript_ai_suggestions
      SET status = ${status}, updated_at = NOW()
      WHERE id = ${suggestionId}
    `);
  }

  async runIterativeRefinement(
    manuscriptId: string,
    maxIterations: number
  ): Promise<RefinementResult> {
    ensureDb();
    await this.ensureSchema();

    const content = await this.fetchManuscriptContent(manuscriptId);
    const sections = content.sections || {};
    const sectionIds = Object.keys(sections);

    if (sectionIds.length === 0) {
      return {
        manuscriptId,
        iterations: 0,
        suggestionsGenerated: 0,
        suggestionsApplied: 0,
        summary: "No sections available for refinement",
      };
    }

    let iterations = 0;
    let generated = 0;
    let applied = 0;

    for (let i = 0; i < maxIterations; i++) {
      iterations++;
      let iterationApplied = 0;

      for (const sectionId of sectionIds) {
        const rawText = normalizeSectionContent(content, sectionId);
        if (!rawText) continue;

        const suggestions = this.generateSuggestionsForText(sectionId, rawText, []);
        generated += suggestions.length;

        const highConfidence = suggestions.filter((s) => s.confidence >= 0.82);
        for (const suggestion of highConfidence) {
          const updated = this.applySuggestionToText(rawText, suggestion);
          if (updated !== rawText) {
            sections[sectionId] = {
              ...(sections[sectionId] || {}),
              content: updated,
            };
            iterationApplied++;
            applied++;
          }
        }
      }

      if (iterationApplied === 0) {
        break;
      }
    }

    let updatedVersionId: string | undefined;
    if (applied > 0) {
      updatedVersionId = await this.persistRefinedVersion(manuscriptId, content);
    }

    await db.execute(sql`
      INSERT INTO manuscript_ai_refinement_runs (manuscript_id, iterations, suggestions_generated, suggestions_applied)
      VALUES (${manuscriptId}, ${iterations}, ${generated}, ${applied})
    `);

    return {
      manuscriptId,
      iterations,
      suggestionsGenerated: generated,
      suggestionsApplied: applied,
      updatedVersionId,
      summary:
        applied === 0
          ? "No high-confidence edits applied"
          : `Applied ${applied} suggestions across ${iterations} iteration(s)`,
      sections: content.sections,
    };
  }

  async checkStyleConsistency(manuscriptId: string): Promise<StyleReport> {
    ensureDb();
    const content = await this.fetchManuscriptContent(manuscriptId);
    const sections = content.sections || {};
    const sectionIds = Object.keys(sections);
    const issues: StyleIssue[] = [];

    let totalSentences = 0;
    let totalSentenceLength = 0;
    let passiveSentences = 0;
    let citationNumeric = 0;
    let citationAuthorYear = 0;

    for (const sectionId of sectionIds) {
      const text = normalizeSectionContent(content, sectionId);
      if (!text) continue;

      const sentences = splitSentences(text);
      totalSentences += sentences.length;

      for (const sentence of sentences) {
        const length = wordCount(sentence);
        totalSentenceLength += length;
        if (detectPassiveVoice(sentence)) {
          passiveSentences += 1;
        }
        if (length > 35) {
          issues.push({
            sectionId,
            category: "structure",
            severity: "medium",
            message: "Long sentence detected; consider splitting for clarity.",
            example: sentence.slice(0, 200),
          });
        }
      }

      const citationStyle = detectCitationStyle(text);
      if (citationStyle === "numeric") citationNumeric += 1;
      if (citationStyle === "author-year") citationAuthorYear += 1;

      if (citationStyle === "none" && /study|research|trial|analysis/i.test(text)) {
        issues.push({
          sectionId,
          category: "citation",
          severity: "high",
          message: "Section references studies but lacks citations.",
        });
      }

      if (/\bwe\b/i.test(text) && /\bthe study\b/i.test(text)) {
        issues.push({
          sectionId,
          category: "voice",
          severity: "low",
          message: "Inconsistent voice detected (first-person vs third-person).",
        });
      }
    }

    const avgSentenceLength =
      totalSentences === 0 ? 0 : Number((totalSentenceLength / totalSentences).toFixed(2));
    const passiveRatio =
      totalSentences === 0 ? 0 : Number((passiveSentences / totalSentences).toFixed(2));

    if (citationNumeric > 0 && citationAuthorYear > 0) {
      issues.push({
        sectionId: "global",
        category: "consistency",
        severity: "high",
        message: "Mixed citation styles detected across sections.",
      });
    }

    if (passiveRatio > 0.35) {
      issues.push({
        sectionId: "global",
        category: "tone",
        severity: "medium",
        message: "High passive voice usage; consider switching to active voice.",
      });
    }

    return {
      manuscriptId,
      createdAt: new Date(),
      metrics: {
        averageSentenceLength: avgSentenceLength,
        passiveVoiceRatio: passiveRatio,
        sectionsAnalyzed: sectionIds.length,
      },
      issues,
      summary: `Detected ${issues.length} style issue(s) across ${sectionIds.length} section(s)`,
    };
  }

  private async ensureSchema(): Promise<void> {
    if (this.schemaReady) return;
    ensureDb();

    await db.execute(sql`
      CREATE TABLE IF NOT EXISTS manuscript_ai_suggestions (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        manuscript_id UUID NOT NULL,
        section_id TEXT NOT NULL,
        original_text TEXT NOT NULL,
        suggested_text TEXT NOT NULL,
        rationale TEXT,
        confidence NUMERIC,
        suggestion_type VARCHAR(20) NOT NULL,
        status VARCHAR(20) DEFAULT 'pending',
        created_at TIMESTAMPTZ DEFAULT NOW(),
        updated_at TIMESTAMPTZ DEFAULT NOW()
      )
    `);

    await db.execute(sql`
      CREATE TABLE IF NOT EXISTS manuscript_ai_refinement_runs (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        manuscript_id UUID NOT NULL,
        iterations INT NOT NULL,
        suggestions_generated INT NOT NULL,
        suggestions_applied INT NOT NULL,
        created_at TIMESTAMPTZ DEFAULT NOW()
      )
    `);

    this.schemaReady = true;
  }

  private async fetchManuscriptContent(manuscriptId: string): Promise<ManuscriptContent> {
    ensureDb();
    const result = await db.execute(sql`
      SELECT mv.content
      FROM manuscripts m
      JOIN manuscript_versions mv ON m.current_version_id = mv.id
      WHERE m.id = ${manuscriptId}
    `);

    if (result.rows.length === 0) {
      throw new Error("Manuscript not found");
    }

    return (result.rows[0] as any).content as ManuscriptContent;
  }

  private generateSuggestionsForText(
    sectionId: string,
    text: string,
    ragHints: string[]
  ): EditingSuggestion[] {
    const suggestions: EditingSuggestion[] = [];

    const doubleSpace = text.match(/\s{2,}/);
    if (doubleSpace) {
      suggestions.push({
        sectionId,
        originalText: doubleSpace[0],
        suggestedText: " ",
        rationale: "Extra whitespace can reduce readability.",
        confidence: 0.95,
        type: "grammar",
      });
    }

    const repeats = detectRepeatedWords(text);
    for (const repeat of repeats.slice(0, 3)) {
      suggestions.push({
        sectionId,
        originalText: repeat,
        suggestedText: repeat.split(" ")[0],
        rationale: "Repeated words can be simplified.",
        confidence: 0.8,
        type: "grammar",
      });
    }

    const sentences = splitSentences(text);
    const longSentence = sentences.find((s) => wordCount(s) > 30);
    if (longSentence) {
      suggestions.push({
        sectionId,
        originalText: longSentence,
        suggestedText: `${longSentence} (Consider splitting this sentence)`,
        rationale: "Long sentences reduce clarity; split for readability.",
        confidence: 0.74,
        type: "clarity",
      });
    }

    const passive = sentences.find(detectPassiveVoice);
    if (passive) {
      suggestions.push({
        sectionId,
        originalText: passive,
        suggestedText: passive.replace(/\b(is|was|were|be|been|being)\b/i, "actively"),
        rationale: "Active voice improves engagement and clarity.",
        confidence: 0.7,
        type: "style",
      });
    }

    const citationStyle = detectCitationStyle(text);
    if (citationStyle === "none" && /study|research|trial|analysis/i.test(text)) {
      suggestions.push({
        sectionId,
        originalText: text.slice(0, 120),
        suggestedText: `${text.slice(0, 120)} [citation needed]`,
        rationale: "Statements referencing prior work should include citations.",
        confidence: 0.78,
        type: "citation",
      });
    }

    if (wordCount(text) < 80) {
      suggestions.push({
        sectionId,
        originalText: text,
        suggestedText: `${text}\n\n[Add more detail to strengthen this section.]`,
        rationale: "Section appears short; expand with additional context.",
        confidence: 0.67,
        type: "content",
      });
    }

    if (ragHints.length > 0) {
      suggestions.push({
        sectionId,
        originalText: text.slice(0, 120),
        suggestedText: text.slice(0, 120),
        rationale: `RAG guidance: ${ragHints[0].slice(0, 200)}`,
        confidence: 0.6,
        type: "style",
      });
    }

    return suggestions;
  }

  private async storeSuggestions(
    manuscriptId: string,
    sectionId: string,
    suggestions: EditingSuggestion[]
  ): Promise<StoredSuggestion[]> {
    if (suggestions.length === 0) return [];

    const stored: StoredSuggestion[] = [];
    for (const suggestion of suggestions) {
      const id = randomUUID();
      await db.execute(sql`
        INSERT INTO manuscript_ai_suggestions (
          id,
          manuscript_id,
          section_id,
          original_text,
          suggested_text,
          rationale,
          confidence,
          suggestion_type,
          status
        )
        VALUES (
          ${id},
          ${manuscriptId},
          ${sectionId},
          ${suggestion.originalText},
          ${suggestion.suggestedText},
          ${suggestion.rationale},
          ${suggestion.confidence},
          ${suggestion.type},
          'pending'
        )
      `);

      stored.push({
        ...suggestion,
        id,
        status: "pending",
      });
    }

    return stored;
  }

  private applySuggestionToText(text: string, suggestion: EditingSuggestion): string {
    if (!suggestion.originalText) return text;
    if (text.includes(suggestion.originalText)) {
      return text.replace(suggestion.originalText, suggestion.suggestedText);
    }
    return text;
  }

  private async persistRefinedVersion(
    manuscriptId: string,
    content: ManuscriptContent
  ): Promise<string> {
    const currentResult = await db.execute(sql`
      SELECT mv.version_number, mv.current_hash, mv.id
      FROM manuscripts m
      JOIN manuscript_versions mv ON m.current_version_id = mv.id
      WHERE m.id = ${manuscriptId}
    `);

    if (currentResult.rows.length === 0) {
      throw new Error("Manuscript not found");
    }

    const current = currentResult.rows[0] as any;
    const newVersionNumber = Number(current.version_number || 0) + 1;
    const newVersionId = `ver_${computeHash(`${manuscriptId}:${Date.now()}`)}`;

    const contentHash = computeHash(JSON.stringify(content));
    const totalWordCount = wordCount(
      content.sections
        ? Object.values(content.sections)
            .map((s) => s?.content || "")
            .join(" ")
        : content.text || ""
    );

    await db.execute(sql`
      INSERT INTO manuscript_versions (
        id,
        manuscript_id,
        version_number,
        content,
        data_snapshot_hash,
        word_count,
        change_description,
        previous_hash,
        current_hash,
        created_by
      )
      VALUES (
        ${newVersionId},
        ${manuscriptId},
        ${newVersionNumber},
        ${JSON.stringify(content)}::jsonb,
        ${contentHash},
        ${totalWordCount},
        ${"AI refinement iteration"},
        ${current.current_hash || null},
        ${contentHash},
        ${"system"}
      )
    `);

    await db.execute(sql`
      UPDATE manuscripts
      SET current_version_id = ${newVersionId}, updated_at = NOW()
      WHERE id = ${manuscriptId}
    `);

    return newVersionId;
  }
}

export const aiEditingService = AIEditingService.getInstance();
export default aiEditingService;
