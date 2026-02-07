/**
 * AI Feedback → RAG service
 *
 * Aggregates ai_output_feedback joined to ai_invocations into guidance
 * documents (taskType, feedbackType) and indexes them into Chroma
 * collection ai_feedback_guidance. No raw prompts/outputs or free-text
 * comments are indexed.
 */

import { aiOutputFeedback, aiInvocations } from '@researchflow/core/schema';
import { eq, gte } from 'drizzle-orm';

import { db } from '../../db';
import { config } from '../config/env';

const RAG_COLLECTION = 'ai_feedback_guidance';
const DEFAULT_WINDOW_DAYS = 90;

export interface RebuildResult {
  indexed: number;
  updated: number;
  documents: number;
  error?: string;
}

/**
 * Aggregate feedback joined to invocations (last N days) into guidance
 * docs per (taskType, feedbackType). Uses only structured fields:
 * taskType, feedbackType, rating, tags. Excludes raw comment.
 */
export async function aggregateFeedbackGuidance(
  windowDays: number = DEFAULT_WINDOW_DAYS
): Promise<Array<{ id: string; content: string; metadata: Record<string, unknown> }>> {
  if (!db) {
    throw new Error('Database not initialized');
  }

  const since = new Date();
  since.setDate(since.getDate() - windowDays);

  const rows = await db
    .select({
      taskType: aiInvocations.taskType,
      feedbackType: aiOutputFeedback.feedbackType,
      rating: aiOutputFeedback.rating,
      tags: aiOutputFeedback.tags,
    })
    .from(aiOutputFeedback)
    .innerJoin(aiInvocations, eq(aiOutputFeedback.invocationId, aiInvocations.id))
    .where(gte(aiOutputFeedback.createdAt, since));

  const byKey = new Map<
    string,
    { ratings: number[]; tags: string[] }
  >();

  for (const r of rows) {
    const key = `${r.taskType}:${r.feedbackType}`;
    const existing = byKey.get(key);
    const tags = (r.tags as string[] | null) || [];
    const tagList = Array.isArray(tags) ? tags : (tags ? [String(tags)] : []);

    if (!existing) {
      byKey.set(key, {
        ratings: [Number(r.rating) || 0],
        tags: tagList,
      });
    } else {
      existing.ratings.push(Number(r.rating) || 0);
      existing.tags.push(...tagList);
    }
  }

  const docs: Array<{ id: string; content: string; metadata: Record<string, unknown> }> = [];

  for (const [key, data] of byKey.entries()) {
    const [taskType, feedbackType] = key.split(':');
    const id = `${RAG_COLLECTION}:${taskType}:${feedbackType}`;
    const count = data.ratings.length;
    const avgRating = count ? data.ratings.reduce((a, b) => a + b, 0) / count : 0;
    const topTags = [...new Set(data.tags)]
      .filter(Boolean)
      .slice(0, 10);
    const content = [
      `Task type: ${taskType}. Feedback type: ${feedbackType}.`,
      `Observed issues: ${count} feedback entries.`,
      `Average rating: ${avgRating.toFixed(1)}.`,
      topTags.length ? `Top tags: ${topTags.join(', ')}.` : '',
    ]
      .filter(Boolean)
      .join(' ');
    docs.push({
      id,
      content,
      metadata: {
        taskType,
        feedbackType,
        count,
        avgRating,
        topTags,
      },
    });
  }

  return docs;
}

/**
 * Rebuild RAG collection ai_feedback_guidance by aggregating feedback
 * and posting to worker /agents/rag/index.
 */
export async function rebuildFeedbackRAG(
  windowDays: number = DEFAULT_WINDOW_DAYS
): Promise<RebuildResult> {
  const workerUrl = config.workerUrl;

  const docs = await aggregateFeedbackGuidance(windowDays);
  if (docs.length === 0) {
    return { indexed: 0, updated: 0, documents: 0 };
  }

  const body = {
    collection: RAG_COLLECTION,
    documents: docs.map((d) => ({
      id: d.id,
      content: d.content,
      metadata: d.metadata,
    })),
  };

  const response = await fetch(`${workerUrl}/agents/rag/index`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
    signal: AbortSignal.timeout(60000),
  });

  if (!response.ok) {
    const text = await response.text();
    throw new Error(`Worker RAG index failed: ${response.status} ${text}`);
  }

  const result = (await response.json()) as { indexed_count: number; updated_count: number; collection: string };
  return {
    indexed: result.indexed_count ?? 0,
    updated: result.updated_count ?? 0,
    documents: docs.length,
  };
}
