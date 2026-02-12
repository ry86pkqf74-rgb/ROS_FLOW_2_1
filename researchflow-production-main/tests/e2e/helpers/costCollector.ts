/**
 * Playwright Cost Collector (Bundle B - Cost Instrumentation)
 *
 * Listens to responses from AI endpoints and aggregates X-Ros-* headers
 * into a cost report. Writes cost-report.json at the end of the test run.
 *
 * Usage:
 *   const collector = new CostCollector(page);
 *   collector.start();
 *   // ... run tests ...
 *   await collector.stop();
 *   await collector.writeReport('cost-report.json');
 */

import * as fs from 'fs/promises';
import * as path from 'path';

import { Page, Response as PWResponse } from '@playwright/test';

// =============================================================================
// Types
// =============================================================================

export interface CostEnvelope {
  provider: string;
  model: string;
  tokensIn: number;
  tokensOut: number;
  tokensCached?: number;
  latencyMs: number;
  costUsd: number;
  timestamp: string;
  endpoint: string;
  stageId?: number;
}

export interface CostReport {
  testName: string;
  startTime: string;
  endTime: string;
  totalCostUsd: number;
  totalTokensIn: number;
  totalTokensOut: number;
  totalLatencyMs: number;
  callCount: number;
  costByProvider: Record<string, number>;
  costByModel: Record<string, number>;
  costByStage: Record<string, number>;
  calls: CostEnvelope[];
  budgetExceeded: boolean;
  maxBudgetUsd?: number;
}

// =============================================================================
// Cost Collector Class
// =============================================================================

export class CostCollector {
  private page: Page;
  private calls: CostEnvelope[] = [];
  private listening = false;
  private startTime: string = '';
  private testName: string = '';
  private maxBudgetUsd?: number;
  private responseHandler?: (response: PWResponse) => Promise<void>;

  // AI endpoint patterns to monitor
  private readonly AI_ENDPOINT_PATTERNS = [
    /\/api\/ai\//,
    /\/api\/chat\/.+\/message/,
    /\/api\/workflow\/.*\/execute/,
    /\/api\/agent-proxy/,
  ];

  constructor(page: Page, options?: { testName?: string; maxBudgetUsd?: number }) {
    this.page = page;
    this.testName = options?.testName || 'unnamed-test';
    this.maxBudgetUsd = options?.maxBudgetUsd;
  }

  /**
   * Start listening for AI endpoint responses
   */
  start(): void {
    if (this.listening) return;

    this.listening = true;
    this.startTime = new Date().toISOString();
    this.calls = [];

    this.responseHandler = async (response: PWResponse) => {
      await this.handleResponse(response);
    };

    this.page.on('response', this.responseHandler);
  }

  /**
   * Stop listening for responses
   */
  stop(): void {
    if (!this.listening) return;

    this.listening = false;

    if (this.responseHandler) {
      this.page.off('response', this.responseHandler);
      this.responseHandler = undefined;
    }
  }

  /**
   * Handle a response and extract cost headers if present
   */
  private async handleResponse(response: PWResponse): Promise<void> {
    const url = response.url();

    // Check if this is an AI endpoint
    if (!this.AI_ENDPOINT_PATTERNS.some((pattern) => pattern.test(url))) {
      return;
    }

    // Extract X-Ros-* headers
    const headers = response.headers();
    const provider = headers['x-ros-provider'];
    const model = headers['x-ros-model'];
    const tokensIn = headers['x-ros-tokens-in'];
    const tokensOut = headers['x-ros-tokens-out'];
    const tokensCached = headers['x-ros-tokens-cached'];
    const latencyMs = headers['x-ros-latency-ms'];
    const costUsd = headers['x-ros-cost-usd'];

    // Only record if we have cost headers
    if (!costUsd) return;

    // Try to extract stage ID from URL
    const stageMatch = url.match(/stage[_-]?(\d+)/i);
    const stageId = stageMatch ? parseInt(stageMatch[1], 10) : undefined;

    const envelope: CostEnvelope = {
      provider: provider || 'unknown',
      model: model || 'unknown',
      tokensIn: parseInt(tokensIn || '0', 10),
      tokensOut: parseInt(tokensOut || '0', 10),
      tokensCached: tokensCached ? parseInt(tokensCached, 10) : undefined,
      latencyMs: parseInt(latencyMs || '0', 10),
      costUsd: parseFloat(costUsd),
      timestamp: new Date().toISOString(),
      endpoint: new URL(url).pathname,
      stageId,
    };

    this.calls.push(envelope);

    // Check budget
    if (this.maxBudgetUsd !== undefined) {
      const totalCost = this.calls.reduce((sum, call) => sum + call.costUsd, 0);
      if (totalCost > this.maxBudgetUsd) {
        console.warn(
          `[CostCollector] Budget exceeded! Total: $${totalCost.toFixed(4)}, Max: $${this.maxBudgetUsd}`
        );
      }
    }
  }

  /**
   * Get the current total cost
   */
  getTotalCost(): number {
    return this.calls.reduce((sum, call) => sum + call.costUsd, 0);
  }

  /**
   * Check if budget has been exceeded
   */
  isBudgetExceeded(): boolean {
    if (this.maxBudgetUsd === undefined) return false;
    return this.getTotalCost() > this.maxBudgetUsd;
  }

  /**
   * Generate the cost report
   */
  generateReport(): CostReport {
    const totalCostUsd = this.calls.reduce((sum, call) => sum + call.costUsd, 0);
    const totalTokensIn = this.calls.reduce((sum, call) => sum + call.tokensIn, 0);
    const totalTokensOut = this.calls.reduce((sum, call) => sum + call.tokensOut, 0);
    const totalLatencyMs = this.calls.reduce((sum, call) => sum + call.latencyMs, 0);

    // Aggregate by provider
    const costByProvider: Record<string, number> = {};
    for (const call of this.calls) {
      costByProvider[call.provider] = (costByProvider[call.provider] || 0) + call.costUsd;
    }

    // Aggregate by model
    const costByModel: Record<string, number> = {};
    for (const call of this.calls) {
      costByModel[call.model] = (costByModel[call.model] || 0) + call.costUsd;
    }

    // Aggregate by stage
    const costByStage: Record<string, number> = {};
    for (const call of this.calls) {
      if (call.stageId !== undefined) {
        const stageKey = `stage-${call.stageId}`;
        costByStage[stageKey] = (costByStage[stageKey] || 0) + call.costUsd;
      }
    }

    return {
      testName: this.testName,
      startTime: this.startTime,
      endTime: new Date().toISOString(),
      totalCostUsd,
      totalTokensIn,
      totalTokensOut,
      totalLatencyMs,
      callCount: this.calls.length,
      costByProvider,
      costByModel,
      costByStage,
      calls: this.calls,
      budgetExceeded: this.isBudgetExceeded(),
      maxBudgetUsd: this.maxBudgetUsd,
    };
  }

  /**
   * Write the cost report to a file
   */
  async writeReport(filePath: string = 'cost-report.json'): Promise<CostReport> {
    const report = this.generateReport();

    // Ensure directory exists
    const dir = path.dirname(filePath);
    await fs.mkdir(dir, { recursive: true }).catch(() => {});

    // Write report
    await fs.writeFile(filePath, JSON.stringify(report, null, 2));

    console.log(`[CostCollector] Report written to ${filePath}`);
    console.log(`[CostCollector] Total cost: $${report.totalCostUsd.toFixed(4)}`);
    console.log(`[CostCollector] Total calls: ${report.callCount}`);
    console.log(`[CostCollector] Total tokens: ${report.totalTokensIn} in, ${report.totalTokensOut} out`);

    return report;
  }
}

// =============================================================================
// Fixture Helper
// =============================================================================

/**
 * Create a cost collector for use in Playwright test fixtures
 */
export function createCostCollector(
  page: Page,
  testName: string,
  maxBudgetUsd?: number
): CostCollector {
  return new CostCollector(page, { testName, maxBudgetUsd });
}

// =============================================================================
// Budget Gate
// =============================================================================

/**
 * Throw an error if budget is exceeded (for use in test assertions)
 */
export function assertBudgetNotExceeded(collector: CostCollector): void {
  if (collector.isBudgetExceeded()) {
    const report = collector.generateReport();
    throw new Error(
      `E2E cost budget exceeded! ` +
        `Total: $${report.totalCostUsd.toFixed(4)}, ` +
        `Max: $${report.maxBudgetUsd?.toFixed(2) || 'unlimited'}`
    );
  }
}

export default CostCollector;
