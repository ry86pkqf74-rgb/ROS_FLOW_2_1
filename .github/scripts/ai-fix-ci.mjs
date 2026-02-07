#!/usr/bin/env node
/**
 * AI CI fixer: fetches failed CI run logs, calls LLM (Anthropic or OpenAI),
 * outputs a unified diff to apply. Used by ai-fix-ci.yml.
 * Model order: attempt 1 = Anthropic, 2 = OpenAI, 3 = Anthropic.
 */
import { writeFileSync } from 'fs';
import { execSync } from 'child_process';

const RUN_ID = process.env.RUN_ID;
const REPO = process.env.GITHUB_REPOSITORY;
const TOKEN = process.env.GITHUB_TOKEN;
const ATTEMPT = parseInt(process.env.ATTEMPT || '1', 10);
const OUT_PATCH = process.env.OUT_PATCH || 'fix.patch';

if (!RUN_ID || !REPO || !TOKEN) {
  console.error('Missing RUN_ID, GITHUB_REPOSITORY, or GITHUB_TOKEN');
  process.exit(1);
}

const [owner, repo] = REPO.split('/');
const base = `https://api.github.com`;

async function ghFetch(url, opts = {}) {
  const res = await fetch(url, {
    ...opts,
    headers: {
      Authorization: `Bearer ${TOKEN}`,
      Accept: 'application/vnd.github+json',
      'X-GitHub-Api-Version': '2022-11-28',
      ...opts.headers,
    },
  });
  if (!res.ok) throw new Error(`API ${res.status}: ${await res.text()}`);
  return res.json();
}

async function getFailedJobsLogs() {
  const jobList = await ghFetch(
    `${base}/repos/${owner}/${repo}/actions/runs/${RUN_ID}/jobs`
  );
  const failed = (jobList.jobs || []).filter((j) => j.conclusion === 'failure');
  const logParts = [];
  for (const job of failed) {
    const logUrl = `${base}/repos/${owner}/${repo}/actions/jobs/${job.id}/logs`;
    const logRes = await fetch(logUrl, {
      headers: { Authorization: `Bearer ${TOKEN}`, Accept: 'application/vnd.github+json' },
    });
    if (logRes.ok) logParts.push(`=== Job: ${job.name} ===\n${await logRes.text()}`);
  }
  return logParts.join('\n\n') || 'No job logs retrieved.';
}

function getRepoContext() {
  try {
    const status = execSync('git status -sb', { encoding: 'utf-8' });
    const diff = execSync('git diff HEAD', { encoding: 'utf-8', maxBuffer: 2 * 1024 * 1024 });
    const list = execSync('git diff --name-only HEAD', { encoding: 'utf-8' });
    return `git status:\n${status}\n\nChanged files:\n${list}\n\ngit diff HEAD (abbrev):\n${diff.slice(0, 50000)}`;
  } catch (e) {
    return `git context error: ${e.message}`;
  }
}

function selectModel(attempt) {
  return attempt === 2 ? 'openai' : 'anthropic';
}

async function callAnthropic(logs, context) {
  const key = process.env.ANTHROPIC_API_KEY;
  if (!key) throw new Error('ANTHROPIC_API_KEY not set');
  const res = await fetch('https://api.anthropic.com/v1/messages', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'x-api-key': key,
      'anthropic-version': '2023-06-01',
    },
    body: JSON.stringify({
      model: 'claude-sonnet-4-20250514',
      max_tokens: 8192,
      messages: [
        {
          role: 'user',
          content: `Our CI failed. Produce a single unified diff (patch) to fix the failures. Do not explain; only output the diff, starting with "diff --git" and suitable for \`patch -p1\`. If you cannot produce a safe fix, output exactly: NO_PATCH\n\nCI job logs:\n${logs.slice(0, 80000)}\n\nRepo context:\n${context.slice(0, 20000)}`,
        },
      ],
    }),
  });
  if (!res.ok) throw new Error(`Anthropic ${res.status}: ${await res.text()}`);
  const data = await res.json();
  const text = data.content?.[0]?.text || '';
  const patchMatch = text.match(/diff --git[\s\S]*/);
  return patchMatch ? patchMatch[0].trim() : null;
}

async function callOpenAI(logs, context) {
  const key = process.env.OPENAI_API_KEY;
  if (!key) throw new Error('OPENAI_API_KEY not set');
  const res = await fetch('https://api.openai.com/v1/chat/completions', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${key}`,
    },
    body: JSON.stringify({
      model: 'gpt-4o',
      max_tokens: 8192,
      messages: [
        {
          role: 'user',
          content: `Our CI failed. Produce a single unified diff (patch) to fix the failures. Do not explain; only output the diff, starting with "diff --git" and suitable for \`patch -p1\`. If you cannot produce a safe fix, output exactly: NO_PATCH\n\nCI job logs:\n${logs.slice(0, 80000)}\n\nRepo context:\n${context.slice(0, 20000)}`,
        },
      ],
    }),
  });
  if (!res.ok) throw new Error(`OpenAI ${res.status}: ${await res.text()}`);
  const data = await res.json();
  const text = data.choices?.[0]?.message?.content || '';
  if (text.includes('NO_PATCH')) return null;
  const patchMatch = text.match(/diff --git[\s\S]*/);
  return patchMatch ? patchMatch[0].trim() : null;
}

async function main() {
  const logs = await getFailedJobsLogs();
  const context = getRepoContext();
  const provider = selectModel(ATTEMPT);
  const patch =
    provider === 'anthropic'
      ? await callAnthropic(logs, context)
      : await callOpenAI(logs, context);
  if (!patch) {
    console.log('No patch produced (NO_PATCH or parse failure)');
    writeFileSync(OUT_PATCH, '');
    process.exit(0);
  }
  writeFileSync(OUT_PATCH, patch);
  console.log('Wrote patch to', OUT_PATCH);
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
