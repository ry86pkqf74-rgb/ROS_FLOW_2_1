import { Router } from 'express';

/**
 * Collaborative variable tagging routes.
 *
 * Endpoints:
 * - GET  /api/projects/:projectId/variables
 * - POST /api/projects/:projectId/variables/:name/tag
 * - POST /api/projects/:projectId/variables/:name/vote
 * - GET  /api/projects/:projectId/variables/suggestions
 */

const router = Router();

// NOTE: This repository's orchestrator is large and route modules vary in how they access DB/auth.
// To keep this change safe and non-destructive, we provide a minimal in-memory implementation
// that can be swapped to a real DB implementation once the orchestrator's DB service is wired.

type TagType = 'outcome' | 'predictor' | 'covariate' | 'confounder' | 'instrument' | 'exclude';

type VariableTag = {
  id: string;
  projectId: string;
  variableName: string;
  tagType: TagType;
  suggestedBy?: string | null;
  confidence: number;
  rationale?: string | null;
  createdAt: string;
};

type Vote = {
  id: string;
  tagId: string;
  userId: string;
  vote: -1 | 1;
  createdAt: string;
};

// Very small, process-local store (placeholder).
const memory = {
  tags: new Map<string, VariableTag>(), // key: `${projectId}:${variableName}`
  votes: new Map<string, Vote>() // key: `${tagId}:${userId}`
};

function nowIso() {
  return new Date().toISOString();
}

function uuidLike() {
  // Non-cryptographic; sufficient as a placeholder id.
  return `tmp_${Math.random().toString(16).slice(2)}_${Date.now().toString(16)}`;
}

function parseTagType(value: unknown): TagType | null {
  if (typeof value !== 'string') return null;
  const v = value.trim();
  const allowed: TagType[] = ['outcome', 'predictor', 'covariate', 'confounder', 'instrument', 'exclude'];
  return (allowed as string[]).includes(v) ? (v as TagType) : null;
}

// GET /api/projects/:projectId/variables - List variables with tags
router.get('/projects/:projectId/variables', async (req, res) => {
  const { projectId } = req.params;

  const tags = Array.from(memory.tags.values()).filter((t) => t.projectId === projectId);

  // Aggregate votes per tag (net score)
  const voteByTagId = new Map<string, { up: number; down: number; score: number }>();
  for (const v of memory.votes.values()) {
    const agg = voteByTagId.get(v.tagId) ?? { up: 0, down: 0, score: 0 };
    if (v.vote === 1) agg.up += 1;
    if (v.vote === -1) agg.down += 1;
    agg.score = agg.up - agg.down;
    voteByTagId.set(v.tagId, agg);
  }

  res.json({
    projectId,
    variables: tags.map((t) => ({
      name: t.variableName,
      tag: {
        id: t.id,
        type: t.tagType,
        confidence: t.confidence,
        rationale: t.rationale ?? null,
        suggested_by: t.suggestedBy ?? null,
        created_at: t.createdAt,
        votes: voteByTagId.get(t.id) ?? { up: 0, down: 0, score: 0 }
      }
    }))
  });
});

// POST /api/projects/:projectId/variables/:name/tag - Tag a variable
router.post('/projects/:projectId/variables/:name/tag', async (req, res) => {
  const { projectId, name } = req.params;

  const tagType = parseTagType(req.body?.tag_type ?? req.body?.tagType);
  if (!tagType) {
    return res.status(400).json({ error: 'Invalid tag_type', allowed: ['outcome', 'predictor', 'covariate', 'confounder', 'instrument', 'exclude'] });
  }

  const suggestedBy = typeof req.body?.suggested_by === 'string' ? req.body.suggested_by : (typeof req.body?.suggestedBy === 'string' ? req.body.suggestedBy : null);
  const confidenceRaw = req.body?.confidence;
  const confidence = typeof confidenceRaw === 'number' && Number.isFinite(confidenceRaw) ? Math.max(0, Math.min(1, confidenceRaw)) : 0.5;
  const rationale = typeof req.body?.rationale === 'string' ? req.body.rationale : null;

  const key = `${projectId}:${name}`;
  const existing = memory.tags.get(key);

  const tag: VariableTag = {
    id: existing?.id ?? uuidLike(),
    projectId,
    variableName: name,
    tagType,
    suggestedBy,
    confidence,
    rationale,
    createdAt: existing?.createdAt ?? nowIso()
  };

  memory.tags.set(key, tag);

  return res.json({
    projectId,
    variable: name,
    tag
  });
});

// POST /api/projects/:projectId/variables/:name/vote - Vote on tag
router.post('/projects/:projectId/variables/:name/vote', async (req, res) => {
  const { projectId, name } = req.params;

  const key = `${projectId}:${name}`;
  const tag = memory.tags.get(key);
  if (!tag) {
    return res.status(404).json({ error: 'Tag not found for variable', projectId, variable: name });
  }

  const userId = typeof req.body?.user_id === 'string' ? req.body.user_id : (typeof req.body?.userId === 'string' ? req.body.userId : null);
  if (!userId) {
    return res.status(400).json({ error: 'user_id is required' });
  }

  const voteRaw = req.body?.vote;
  const vote = voteRaw === 1 || voteRaw === -1 ? (voteRaw as -1 | 1) : (typeof voteRaw === 'string' && (voteRaw === '1' || voteRaw === '-1') ? (parseInt(voteRaw, 10) as -1 | 1) : null);
  if (vote !== 1 && vote !== -1) {
    return res.status(400).json({ error: 'vote must be 1 or -1' });
  }

  const voteKey = `${tag.id}:${userId}`;
  const record: Vote = {
    id: memory.votes.get(voteKey)?.id ?? uuidLike(),
    tagId: tag.id,
    userId,
    vote,
    createdAt: memory.votes.get(voteKey)?.createdAt ?? nowIso()
  };

  memory.votes.set(voteKey, record);

  // Compute updated tally
  let up = 0;
  let down = 0;
  for (const v of memory.votes.values()) {
    if (v.tagId !== tag.id) continue;
    if (v.vote === 1) up += 1;
    if (v.vote === -1) down += 1;
  }

  return res.json({
    projectId,
    variable: name,
    tag_id: tag.id,
    votes: { up, down, score: up - down }
  });
});

// GET /api/projects/:projectId/variables/suggestions - AI suggestions
router.get('/projects/:projectId/variables/suggestions', async (req, res) => {
  const { projectId } = req.params;

  // Placeholder: the real implementation should call the existing AI insights/router infrastructure.
  // We return an empty list to keep API stable.
  res.json({
    projectId,
    suggestions: []
  });
});

export default router;
