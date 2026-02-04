/**
 * AI Bridge Batch Optimizer
 * 
 * Optimizes batch processing for better performance and cost efficiency
 */

import { createLogger } from '../utils/logger';

const logger = createLogger('ai-bridge-batch-optimizer');

interface BatchRequest {
  prompt: string;
  options: any;
  metadata?: any;
}

interface OptimizedBatch {
  requests: BatchRequest[];
  estimatedCost: number;
  estimatedTokens: number;
  processingStrategy: 'sequential' | 'parallel' | 'adaptive';
}

export class BatchOptimizer {
  private readonly maxTokensPerBatch = 180000; // Leave buffer for model limits
  private readonly maxCostPerBatch = 5.0;      // Cost limit per batch
  private readonly optimalBatchSize = 8;        // Sweet spot for parallel processing
  
  /**
   * Optimize batch processing strategy
   */
  optimizeBatch(requests: BatchRequest[]): OptimizedBatch[] {
    // Sort by estimated complexity (longer prompts first for better packing)
    const sortedRequests = this.sortByComplexity(requests);
    
    // Split into optimized chunks
    const chunks = this.createOptimalChunks(sortedRequests);
    
    // Determine processing strategy for each chunk
    return chunks.map(chunk => ({
      requests: chunk,
      estimatedCost: this.estimateBatchCost(chunk),
      estimatedTokens: this.estimateBatchTokens(chunk),
      processingStrategy: this.determineStrategy(chunk),
    }));
  }
  
  /**
   * Sort requests by complexity for optimal batching
   */
  private sortByComplexity(requests: BatchRequest[]): BatchRequest[] {
    return requests.sort((a, b) => {
      const complexityA = this.calculateComplexity(a);
      const complexityB = this.calculateComplexity(b);
      return complexityB - complexityA; // Descending order
    });
  }
  
  /**
   * Calculate request complexity score
   */
  private calculateComplexity(request: BatchRequest): number {
    const promptLength = request.prompt.length;
    const taskTypeWeight = this.getTaskTypeWeight(request.options.taskType);
    const tierWeight = this.getTierWeight(request.options.modelTier);
    
    return promptLength * taskTypeWeight * tierWeight;
  }
  
  /**
   * Get task type processing weight
   */
  private getTaskTypeWeight(taskType: string): number {
    const weights: Record<string, number> = {
      'phi_redaction': 2.0,
      'statistical_analysis': 1.8,
      'ethical_review': 1.6,
      'data_analysis': 1.4,
      'hypothesis_generation': 1.2,
      'manuscript_drafting': 1.0,
      'literature_search': 0.8,
      'summarization': 0.6,
      'citation_formatting': 0.4,
    };
    
    return weights[taskType] || 1.0;
  }
  
  /**
   * Get model tier processing weight
   */
  private getTierWeight(tier: string): number {
    const weights: Record<string, number> = {
      'PREMIUM': 1.5,
      'STANDARD': 1.0,
      'ECONOMY': 0.7,
    };
    
    return weights[tier] || 1.0;
  }
  
  /**
   * Create optimal chunks based on token and cost limits
   */
  private createOptimalChunks(requests: BatchRequest[]): BatchRequest[][] {
    const chunks: BatchRequest[][] = [];
    let currentChunk: BatchRequest[] = [];
    let currentTokens = 0;
    let currentCost = 0;
    
    for (const request of requests) {
      const requestTokens = this.estimateTokens(request);
      const requestCost = this.estimateCost(request);
      
      // Check if adding this request would exceed limits
      if (
        currentChunk.length > 0 &&
        (currentTokens + requestTokens > this.maxTokensPerBatch ||
         currentCost + requestCost > this.maxCostPerBatch ||
         currentChunk.length >= this.optimalBatchSize)
      ) {
        // Start new chunk
        chunks.push(currentChunk);
        currentChunk = [request];
        currentTokens = requestTokens;
        currentCost = requestCost;
      } else {
        // Add to current chunk
        currentChunk.push(request);
        currentTokens += requestTokens;
        currentCost += requestCost;
      }
    }
    
    // Add final chunk
    if (currentChunk.length > 0) {
      chunks.push(currentChunk);
    }
    
    return chunks;
  }
  
  /**
   * Estimate tokens for a single request
   */
  private estimateTokens(request: BatchRequest): number {
    // Rough estimation: 4 chars per token, plus output estimation
    const inputTokens = Math.ceil(request.prompt.length / 4);
    const outputTokens = this.estimateOutputTokens(request);
    
    return inputTokens + outputTokens;
  }
  
  /**
   * Estimate output tokens based on task type
   */
  private estimateOutputTokens(request: BatchRequest): number {
    const baseOutput = Math.ceil(request.prompt.length / 8); // Typical compression
    
    const taskMultipliers: Record<string, number> = {
      'statistical_analysis': 1.5,
      'data_analysis': 1.3,
      'hypothesis_generation': 1.2,
      'manuscript_drafting': 2.0,
      'phi_redaction': 0.8,
      'summarization': 0.5,
      'citation_formatting': 0.3,
    };
    
    const multiplier = taskMultipliers[request.options.taskType] || 1.0;
    return Math.ceil(baseOutput * multiplier);
  }
  
  /**
   * Estimate cost for a single request
   */
  private estimateCost(request: BatchRequest): number {
    const tokens = this.estimateTokens(request);
    const tierCosts = {
      'ECONOMY': 0.0001,
      'STANDARD': 0.001,
      'PREMIUM': 0.01,
    };
    
    const costPerToken = tierCosts[request.options.modelTier as keyof typeof tierCosts] || tierCosts.STANDARD;
    return tokens * costPerToken;
  }
  
  /**
   * Estimate total batch cost
   */
  private estimateBatchCost(requests: BatchRequest[]): number {
    return requests.reduce((total, request) => total + this.estimateCost(request), 0);
  }
  
  /**
   * Estimate total batch tokens
   */
  private estimateBatchTokens(requests: BatchRequest[]): number {
    return requests.reduce((total, request) => total + this.estimateTokens(request), 0);
  }
  
  /**
   * Determine optimal processing strategy
   */
  private determineStrategy(requests: BatchRequest[]): 'sequential' | 'parallel' | 'adaptive' {
    const avgComplexity = requests.reduce((sum, req) => sum + this.calculateComplexity(req), 0) / requests.length;
    const batchSize = requests.length;
    
    // High complexity or PHI compliance requires sequential processing
    if (avgComplexity > 5000 || requests.some(req => req.options.requirePhiCompliance)) {
      return 'sequential';
    }
    
    // Small batches can be parallel
    if (batchSize <= 3) {
      return 'parallel';
    }
    
    // Large batches use adaptive strategy
    return 'adaptive';
  }
  
  /**
   * Get processing recommendations
   */
  getProcessingRecommendations(optimizedBatches: OptimizedBatch[]): {
    totalEstimatedCost: number;
    totalEstimatedTokens: number;
    estimatedDuration: number;
    recommendations: string[];
  } {
    const totalCost = optimizedBatches.reduce((sum, batch) => sum + batch.estimatedCost, 0);
    const totalTokens = optimizedBatches.reduce((sum, batch) => sum + batch.estimatedTokens, 0);
    
    // Estimate duration based on strategy
    const estimatedDuration = optimizedBatches.reduce((sum, batch) => {
      const baseTime = batch.requests.length * 2000; // 2s per request base
      const strategyMultiplier = {
        'parallel': 0.4,
        'sequential': 1.0,
        'adaptive': 0.7,
      };
      return sum + (baseTime * strategyMultiplier[batch.processingStrategy]);
    }, 0);
    
    const recommendations: string[] = [];
    
    if (totalCost > 10) {
      recommendations.push('Consider using lower-tier models for simpler tasks');
    }
    
    if (optimizedBatches.length > 5) {
      recommendations.push('Large number of batches - consider spreading requests over time');
    }
    
    const hasHighComplexity = optimizedBatches.some(batch => 
      batch.requests.some(req => this.calculateComplexity(req) > 10000)
    );
    
    if (hasHighComplexity) {
      recommendations.push('High complexity requests detected - expect longer processing times');
    }
    
    return {
      totalEstimatedCost: totalCost,
      totalEstimatedTokens: totalTokens,
      estimatedDuration: estimatedDuration / 1000, // Convert to seconds
      recommendations,
    };
  }
  
  /**
   * Validate batch before processing
   */
  validateBatch(requests: BatchRequest[]): { valid: boolean; errors: string[] } {
    const errors: string[] = [];
    
    if (requests.length === 0) {
      errors.push('Empty batch not allowed');
    }
    
    if (requests.length > 50) {
      errors.push('Batch too large - maximum 50 requests');
    }
    
    // Check for mixed governance modes
    const governanceModes = new Set(requests.map(req => req.options.governanceMode));
    if (governanceModes.size > 1) {
      errors.push('Mixed governance modes in single batch not recommended');
    }
    
    // Check for extremely large prompts
    const largPrompts = requests.filter(req => req.prompt.length > 50000);
    if (largPrompts.length > 0) {
      errors.push(`${largPrompts.length} prompts exceed recommended size (50k chars)`);
    }
    
    return {
      valid: errors.length === 0,
      errors,
    };
  }
}

// Singleton instance
let batchOptimizer: BatchOptimizer | null = null;

export function getBatchOptimizer(): BatchOptimizer {
  if (!batchOptimizer) {
    batchOptimizer = new BatchOptimizer();
  }
  return batchOptimizer;
}

export default BatchOptimizer;