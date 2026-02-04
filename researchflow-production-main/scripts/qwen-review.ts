#!/usr/bin/env node
/**
 * Qwen3 Systematic Code Review Script
 *
 * Automatically reviews ResearchFlow codebase in segments using
 * local Qwen3-Coder model for:
 * - Security vulnerabilities
 * - Code quality issues
 * - Architecture concerns
 * - Performance problems
 * - Refactoring suggestions
 *
 * Usage:
 *   npx ts-node scripts/qwen-review.ts [segment] [outputDir]
 *   npx ts-node scripts/qwen-review.ts --all
 *   npx ts-node scripts/qwen-review.ts --priority critical
 *
 * @module scripts/qwen-review
 */

import * as fs from 'fs';
import * as path from 'path';

// ============================================================================
// Configuration
// ============================================================================

const QWEN_ENDPOINT = process.env.LOCAL_MODEL_ENDPOINT || 'http://localhost:11434';
const QWEN_MODEL = process.env.LOCAL_MODEL_NAME || 'ai/qwen3-coder:latest';
const MAX_TOKENS_PER_CHUNK = 20000; // Conservative limit for 32K context
const OUTPUT_DIR = process.env.REVIEW_OUTPUT_DIR || './review-results';

// ============================================================================
// Types
// ============================================================================

interface ReviewSegment {
  name: string;
  description: string;
  patterns: string[];
  priority: 'critical' | 'high' | 'medium' | 'low';
  language: 'typescript' | 'python' | 'yaml' | 'mixed';
}

interface Issue {
  file: string;
  line?: number;
  severity: 'error' | 'warning' | 'info';
  category: 'security' | 'quality' | 'architecture' | 'performance' | 'documentation';
  rule: string;
  message: string;
  suggestion?: string;
}

interface Refactor {
  file: string;
  description: string;
  before: string;
  after: string;
  effort: 'low' | 'medium' | 'high';
}

interface SegmentResult {
  segment: string;
  priority: string;
  files: string[];
  issues: Issue[];
  refactors: Refactor[];
  summary: string;
  reviewedAt: string;
  duration: number;
}

interface ReviewSummary {
  timestamp: string;
  model: string;
  totalSegments: number;
  totalFiles: number;
  totalIssues: number;
  issuesByCategory: Record<string, number>;
  issuesBySeverity: Record<string, number>;
  issuesByPriority: Record<string, number>;
  results: SegmentResult[];
}

// ============================================================================
// Segment Definitions
// ============================================================================

const SEGMENTS: ReviewSegment[] = [
  {
    name: 'core-types',
    description: 'Core TypeScript types and shared schemas',
    patterns: ['packages/core/**/*.ts', 'shared/schemas/**/*.json'],
    priority: 'critical',
    language: 'typescript'
  },
  {
    name: 'ai-router',
    description: 'AI model routing and provider integrations',
    patterns: ['packages/ai-router/**/*.ts'],
    priority: 'critical',
    language: 'typescript'
  },
  {
    name: 'phi-engine',
    description: 'PHI detection and scrubbing engine',
    patterns: ['packages/phi-engine/**/*.ts'],
    priority: 'critical',
    language: 'typescript'
  },
  {
    name: 'orchestrator-auth',
    description: 'Authentication and JWT handling',
    patterns: ['services/orchestrator/src/auth/**/*.ts'],
    priority: 'critical',
    language: 'typescript'
  },
  {
    name: 'orchestrator-rbac',
    description: 'Role-based access control',
    patterns: ['services/orchestrator/src/rbac/**/*.ts'],
    priority: 'high',
    language: 'typescript'
  },
  {
    name: 'orchestrator-jobs',
    description: 'Job queue and task management',
    patterns: ['services/orchestrator/src/jobs/**/*.ts'],
    priority: 'high',
    language: 'typescript'
  },
  {
    name: 'orchestrator-routes',
    description: 'API route handlers',
    patterns: ['services/orchestrator/src/routes/**/*.ts'],
    priority: 'high',
    language: 'typescript'
  },
  {
    name: 'worker-validation',
    description: 'Data validation with Pandera',
    patterns: ['services/worker/src/validation/**/*.py'],
    priority: 'high',
    language: 'python'
  },
  {
    name: 'worker-workflow',
    description: '19-stage research workflow engine',
    patterns: ['services/worker/src/workflow/**/*.py'],
    priority: 'medium',
    language: 'python'
  },
  {
    name: 'worker-analysis',
    description: 'Statistical analysis and QC',
    patterns: ['services/worker/src/analysis/**/*.py'],
    priority: 'medium',
    language: 'python'
  },
  {
    name: 'web-components',
    description: 'React UI components',
    patterns: ['services/web/src/components/**/*.tsx', 'services/web/src/components/**/*.ts'],
    priority: 'medium',
    language: 'typescript'
  },
  {
    name: 'web-state',
    description: 'State management and hooks',
    patterns: ['services/web/src/hooks/**/*.ts', 'services/web/src/store/**/*.ts'],
    priority: 'medium',
    language: 'typescript'
  },
  {
    name: 'infrastructure',
    description: 'Docker and Kubernetes configurations',
    patterns: ['infrastructure/**/*.yml', 'infrastructure/**/*.yaml', 'docker-compose*.yml'],
    priority: 'low',
    language: 'yaml'
  },
  {
    name: 'tests',
    description: 'Test suites',
    patterns: ['tests/**/*.ts', 'tests/**/*.py', '**/*.test.ts', '**/*.spec.ts'],
    priority: 'low',
    language: 'mixed'
  },
  {
    name: 'scripts',
    description: 'Build and deployment scripts',
    patterns: ['scripts/**/*.sh', 'scripts/**/*.ts', 'scripts/**/*.py'],
    priority: 'low',
    language: 'mixed'
  }
];

// ============================================================================
// Review Prompts
// ============================================================================

const REVIEW_SYSTEM_PROMPT = `You are a senior software engineer performing a thorough code review.
Your task is to analyze code for issues and suggest improvements.

Focus areas:
1. SECURITY: Vulnerabilities, hardcoded secrets, injection risks, auth issues
2. CODE QUALITY: Anti-patterns, code smells, type safety, error handling
3. ARCHITECTURE: Design issues, coupling, separation of concerns
4. PERFORMANCE: Inefficiencies, N+1 queries, memory leaks
5. DOCUMENTATION: Missing docs, unclear code

Be specific and actionable. Include line numbers when possible.
Format response as valid JSON only, no markdown code blocks.`;

const getReviewPrompt = (language: string) => `
Analyze the following ${language} code. Return a JSON object with this exact structure:

{
  "issues": [
    {
      "file": "filename.ts",
      "line": 42,
      "severity": "error|warning|info",
      "category": "security|quality|architecture|performance|documentation",
      "rule": "short-rule-name",
      "message": "Description of the issue",
      "suggestion": "How to fix it"
    }
  ],
  "refactors": [
    {
      "file": "filename.ts",
      "description": "What to refactor and why",
      "before": "code snippet before",
      "after": "code snippet after",
      "effort": "low|medium|high"
    }
  ],
  "summary": "Brief overall assessment"
}

Return ONLY valid JSON. No explanations outside the JSON.

CODE TO REVIEW:
`;

// ============================================================================
// Utility Functions
// ============================================================================

function globSync(pattern: string, basePath: string = '.'): string[] {
  // Simple glob implementation for common patterns
  const files: string[] = [];
  const parts = pattern.split('/');

  function walkDir(dir: string, patternParts: string[], depth: number = 0): void {
    if (depth >= patternParts.length) return;

    const currentPattern = patternParts[depth];

    try {
      const entries = fs.readdirSync(dir, { withFileTypes: true });

      for (const entry of entries) {
        const fullPath = path.join(dir, entry.name);

        if (currentPattern === '**') {
          // Recursive glob
          if (entry.isDirectory()) {
            walkDir(fullPath, patternParts, depth);
            walkDir(fullPath, patternParts, depth + 1);
          } else if (depth === patternParts.length - 1 || matchPattern(entry.name, patternParts[depth + 1])) {
            if (matchPattern(entry.name, patternParts[patternParts.length - 1])) {
              files.push(fullPath);
            }
          }
        } else if (matchPattern(entry.name, currentPattern)) {
          if (entry.isDirectory() && depth < patternParts.length - 1) {
            walkDir(fullPath, patternParts, depth + 1);
          } else if (entry.isFile() && depth === patternParts.length - 1) {
            files.push(fullPath);
          }
        }
      }
    } catch (e) {
      // Directory doesn't exist or not accessible
    }
  }

  function matchPattern(name: string, pattern: string): boolean {
    if (pattern === '*') return true;
    if (pattern === '**') return true;

    // Handle *.ext patterns
    if (pattern.startsWith('*.')) {
      return name.endsWith(pattern.slice(1));
    }

    // Handle exact match
    return name === pattern;
  }

  walkDir(basePath, parts);
  return files;
}

function collectFiles(segment: ReviewSegment): string[] {
  const files: string[] = [];

  for (const pattern of segment.patterns) {
    const found = globSync(pattern);
    files.push(...found);
  }

  // Remove duplicates
  return [...new Set(files)];
}

function estimateTokens(text: string): number {
  // Rough estimate: 1 token ≈ 4 characters
  return Math.ceil(text.length / 4);
}

function chunkFiles(files: string[], maxTokens: number): string[][] {
  const chunks: string[][] = [];
  let currentChunk: string[] = [];
  let currentTokens = 0;

  for (const file of files) {
    try {
      const content = fs.readFileSync(file, 'utf-8');
      const tokens = estimateTokens(content);

      // If single file exceeds limit, it gets its own chunk
      if (tokens > maxTokens) {
        if (currentChunk.length > 0) {
          chunks.push(currentChunk);
          currentChunk = [];
          currentTokens = 0;
        }
        chunks.push([file]);
        continue;
      }

      // Check if adding this file would exceed limit
      if (currentTokens + tokens > maxTokens && currentChunk.length > 0) {
        chunks.push(currentChunk);
        currentChunk = [];
        currentTokens = 0;
      }

      currentChunk.push(file);
      currentTokens += tokens;
    } catch (e) {
      console.warn(`  ⚠️ Could not read file: ${file}`);
    }
  }

  if (currentChunk.length > 0) {
    chunks.push(currentChunk);
  }

  return chunks;
}

// ============================================================================
// Qwen3 API Client
// ============================================================================

async function callQwen(
  systemPrompt: string,
  userPrompt: string,
  retries: number = 3
): Promise<string> {
  for (let attempt = 1; attempt <= retries; attempt++) {
    try {
      const response = await fetch(`${QWEN_ENDPOINT}/api/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          model: QWEN_MODEL,
          messages: [
            { role: 'system', content: systemPrompt },
            { role: 'user', content: userPrompt }
          ],
          stream: false,
          options: {
            temperature: 0.1,
            num_predict: 4096,
          }
        })
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const data = await response.json();
      return data.message?.content ?? '';
    } catch (error) {
      console.warn(`  ⚠️ Attempt ${attempt}/${retries} failed:`,
        error instanceof Error ? error.message : 'Unknown error');

      if (attempt === retries) {
        throw error;
      }

      // Exponential backoff
      await sleep(1000 * Math.pow(2, attempt));
    }
  }

  throw new Error('All retries exhausted');
}

function sleep(ms: number): Promise<void> {
  return new Promise(resolve => setTimeout(resolve, ms));
}

// ============================================================================
// Review Engine
// ============================================================================

async function reviewChunk(
  segment: ReviewSegment,
  files: string[]
): Promise<{ issues: Issue[]; refactors: Refactor[]; summary: string }> {
  // Build code content
  const codeContent = files.map(file => {
    try {
      const content = fs.readFileSync(file, 'utf-8');
      return `\n--- FILE: ${file} ---\n${content}`;
    } catch (e) {
      return `\n--- FILE: ${file} ---\n[Error reading file]`;
    }
  }).join('\n');

  const prompt = getReviewPrompt(segment.language) + codeContent;

  try {
    const response = await callQwen(REVIEW_SYSTEM_PROMPT, prompt);

    // Extract JSON from response (handle potential markdown wrapping)
    let jsonStr = response.trim();
    if (jsonStr.startsWith('```json')) {
      jsonStr = jsonStr.slice(7);
    }
    if (jsonStr.startsWith('```')) {
      jsonStr = jsonStr.slice(3);
    }
    if (jsonStr.endsWith('```')) {
      jsonStr = jsonStr.slice(0, -3);
    }

    const parsed = JSON.parse(jsonStr.trim());

    return {
      issues: parsed.issues || [],
      refactors: parsed.refactors || [],
      summary: parsed.summary || 'No summary provided'
    };
  } catch (error) {
    console.error(`  ❌ Failed to parse response:`, error);
    return {
      issues: [],
      refactors: [],
      summary: `Error: ${error instanceof Error ? error.message : 'Unknown error'}`
    };
  }
}

async function reviewSegment(segment: ReviewSegment): Promise<SegmentResult> {
  const startTime = Date.now();
  console.log(`\n${'='.repeat(60)}`);
  console.log(`📁 Reviewing: ${segment.name}`);
  console.log(`   Priority: ${segment.priority.toUpperCase()}`);
  console.log(`   Description: ${segment.description}`);

  const files = collectFiles(segment);
  console.log(`   Files found: ${files.length}`);

  if (files.length === 0) {
    console.log(`   ⚠️ No files matched patterns`);
    return {
      segment: segment.name,
      priority: segment.priority,
      files: [],
      issues: [],
      refactors: [],
      summary: 'No files to review',
      reviewedAt: new Date().toISOString(),
      duration: 0
    };
  }

  const chunks = chunkFiles(files, MAX_TOKENS_PER_CHUNK);
  console.log(`   Chunks: ${chunks.length}`);

  const allIssues: Issue[] = [];
  const allRefactors: Refactor[] = [];
  const summaries: string[] = [];

  for (let i = 0; i < chunks.length; i++) {
    const chunk = chunks[i];
    console.log(`   📄 Processing chunk ${i + 1}/${chunks.length} (${chunk.length} files)...`);

    const result = await reviewChunk(segment, chunk);

    allIssues.push(...result.issues);
    allRefactors.push(...result.refactors);
    summaries.push(result.summary);

    console.log(`      Found: ${result.issues.length} issues, ${result.refactors.length} refactors`);

    // Rate limiting
    if (i < chunks.length - 1) {
      await sleep(1500);
    }
  }

  const duration = Date.now() - startTime;

  const result: SegmentResult = {
    segment: segment.name,
    priority: segment.priority,
    files,
    issues: allIssues,
    refactors: allRefactors,
    summary: summaries.join(' | '),
    reviewedAt: new Date().toISOString(),
    duration
  };

  console.log(`   ✅ Complete: ${allIssues.length} issues, ${allRefactors.length} refactors (${(duration / 1000).toFixed(1)}s)`);

  return result;
}

// ============================================================================
// Main Execution
// ============================================================================

async function main(): Promise<void> {
  const args = process.argv.slice(2);

  // Parse arguments
  let targetSegments: ReviewSegment[] = [];
  let outputDir = OUTPUT_DIR;

  if (args.includes('--help') || args.includes('-h')) {
    console.log(`
Qwen3 Code Review Script

Usage:
  npx ts-node scripts/qwen-review.ts [options] [segment-name] [output-dir]

Options:
  --all                 Review all segments
  --priority <level>    Review segments of specific priority (critical, high, medium, low)
  --list                List available segments
  --help, -h            Show this help message

Examples:
  npx ts-node scripts/qwen-review.ts core-types
  npx ts-node scripts/qwen-review.ts --priority critical
  npx ts-node scripts/qwen-review.ts --all ./my-review-results
    `);
    return;
  }

  if (args.includes('--list')) {
    console.log('\nAvailable segments:\n');
    for (const seg of SEGMENTS) {
      console.log(`  ${seg.name.padEnd(20)} [${seg.priority.padEnd(8)}] ${seg.description}`);
    }
    return;
  }

  if (args.includes('--all')) {
    targetSegments = SEGMENTS;
    const allIdx = args.indexOf('--all');
    if (args[allIdx + 1] && !args[allIdx + 1].startsWith('--')) {
      outputDir = args[allIdx + 1];
    }
  } else if (args.includes('--priority')) {
    const prioIdx = args.indexOf('--priority');
    const priority = args[prioIdx + 1] as 'critical' | 'high' | 'medium' | 'low';
    targetSegments = SEGMENTS.filter(s => s.priority === priority);
    if (args[prioIdx + 2] && !args[prioIdx + 2].startsWith('--')) {
      outputDir = args[prioIdx + 2];
    }
  } else if (args.length > 0 && !args[0].startsWith('--')) {
    const segmentName = args[0];
    const segment = SEGMENTS.find(s => s.name === segmentName);
    if (!segment) {
      console.error(`❌ Segment not found: ${segmentName}`);
      console.log('Available segments:', SEGMENTS.map(s => s.name).join(', '));
      process.exit(1);
    }
    targetSegments = [segment];
    if (args[1]) {
      outputDir = args[1];
    }
  } else {
    // Default: review critical segments
    targetSegments = SEGMENTS.filter(s => s.priority === 'critical');
    console.log('No segment specified. Reviewing critical segments by default.');
  }

  // Verify Qwen3 is available
  console.log('\n🔍 Qwen3 Code Review');
  console.log('='.repeat(60));
  console.log(`Endpoint: ${QWEN_ENDPOINT}`);
  console.log(`Model: ${QWEN_MODEL}`);
  console.log(`Output: ${outputDir}`);
  console.log(`Segments: ${targetSegments.map(s => s.name).join(', ')}`);

  try {
    const healthCheck = await fetch(`${QWEN_ENDPOINT}/api/tags`);
    if (!healthCheck.ok) {
      throw new Error(`Health check failed: ${healthCheck.status}`);
    }
    console.log('✅ Qwen3 connection verified');
  } catch (error) {
    console.error('❌ Cannot connect to Qwen3. Ensure Ollama is running.');
    console.error(`   Tried: ${QWEN_ENDPOINT}/api/tags`);
    process.exit(1);
  }

  // Create output directory
  fs.mkdirSync(outputDir, { recursive: true });

  // Run reviews
  const results: SegmentResult[] = [];

  for (const segment of targetSegments) {
    const result = await reviewSegment(segment);
    results.push(result);

    // Save individual segment result
    const segmentFile = path.join(outputDir, `${segment.name}.json`);
    fs.writeFileSync(segmentFile, JSON.stringify(result, null, 2));
    console.log(`   💾 Saved: ${segmentFile}`);
  }

  // Generate summary
  const summary: ReviewSummary = {
    timestamp: new Date().toISOString(),
    model: QWEN_MODEL,
    totalSegments: results.length,
    totalFiles: results.reduce((sum, r) => sum + r.files.length, 0),
    totalIssues: results.reduce((sum, r) => sum + r.issues.length, 0),
    issuesByCategory: {},
    issuesBySeverity: {},
    issuesByPriority: {},
    results
  };

  // Aggregate stats
  for (const result of results) {
    for (const issue of result.issues) {
      summary.issuesByCategory[issue.category] = (summary.issuesByCategory[issue.category] || 0) + 1;
      summary.issuesBySeverity[issue.severity] = (summary.issuesBySeverity[issue.severity] || 0) + 1;
    }
    summary.issuesByPriority[result.priority] = (summary.issuesByPriority[result.priority] || 0) + result.issues.length;
  }

  const summaryFile = path.join(outputDir, 'summary.json');
  fs.writeFileSync(summaryFile, JSON.stringify(summary, null, 2));

  // Print summary
  console.log('\n' + '='.repeat(60));
  console.log('📊 REVIEW SUMMARY');
  console.log('='.repeat(60));
  console.log(`Total Segments: ${summary.totalSegments}`);
  console.log(`Total Files: ${summary.totalFiles}`);
  console.log(`Total Issues: ${summary.totalIssues}`);
  console.log('\nBy Severity:');
  console.log(`  🔴 Errors:   ${summary.issuesBySeverity.error || 0}`);
  console.log(`  🟠 Warnings: ${summary.issuesBySeverity.warning || 0}`);
  console.log(`  🔵 Info:     ${summary.issuesBySeverity.info || 0}`);
  console.log('\nBy Category:');
  for (const [cat, count] of Object.entries(summary.issuesByCategory)) {
    console.log(`  ${cat}: ${count}`);
  }
  console.log(`\n✅ Results saved to: ${outputDir}`);
  console.log(`   Summary: ${summaryFile}`);
}

main().catch(error => {
  console.error('Fatal error:', error);
  process.exit(1);
});
