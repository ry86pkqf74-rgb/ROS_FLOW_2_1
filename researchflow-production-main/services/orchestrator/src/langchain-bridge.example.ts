/**
 * LangChain Bridge - Usage Examples
 *
 * Demonstrates practical usage of the LangChain bridge for orchestrating
 * LangGraph agents from the Node.js service.
 *
 * Examples include:
 * - Running agents with different configurations
 * - Monitoring progress in real-time
 * - Error handling and retries
 * - Health checks and circuit breaker status
 */

import {
  getLangChainBridge,
  resetLangChainBridge,
  AgentType,
  TaskPriority,
  TaskStatus,
  type ProgressEvent,
  type AgentTaskResponse,
  type AgentStatusResponse,
} from './langchain-bridge';

// ============================================================================
// EXAMPLE 1: Basic Agent Execution
// ============================================================================

/**
 * Run a simple research analyzer agent
 */
async function example1_basicAgentExecution(): Promise<void> {
  const bridge = getLangChainBridge();

  try {
    // Run an agent
    const response = await bridge.runAgent(
      AgentType.ResearchAnalyzer,
      {
        title: 'COVID-19 mRNA Vaccines',
        keywords: ['mRNA', 'vaccination', 'efficacy'],
        maxResults: 50,
      },
      {
        timeout: 120000, // 2 minutes
        priority: TaskPriority.Normal,
        metadata: {
          userId: 'user-123',
          projectId: 'project-456',
          requestId: 'req-789',
          tags: ['research', 'vaccines'],
        },
      }
    );

    console.log('Agent started:', {
      taskId: response.taskId,
      status: response.status,
      agentType: response.agentType,
    });

    // Poll for completion (simple approach)
    let completed = false;
    let attempts = 0;
    while (!completed && attempts < 120) {
      await new Promise((resolve) => setTimeout(resolve, 1000));
      const status = await bridge.getAgentStatus(response.taskId);

      console.log(`Progress: ${status.progress.percentage}%`);

      if (
        status.status === TaskStatus.Completed ||
        status.status === TaskStatus.Failed
      ) {
        completed = true;
        console.log('Agent finished:', {
          status: status.status,
          result: status.result,
          error: status.error,
        });
      }

      attempts++;
    }
  } catch (error) {
    console.error('Error:', error);
  }
}

// ============================================================================
// EXAMPLE 2: Real-time Progress Monitoring
// ============================================================================

/**
 * Run agent with WebSocket progress streaming
 */
async function example2_realtimeProgressMonitoring(): Promise<void> {
  const bridge = getLangChainBridge();

  try {
    // Run agent
    const response = await bridge.runAgent(
      AgentType.LiteratureReviewer,
      {
        topic: 'Machine Learning in Healthcare',
        searchQuery: 'ML healthcare diagnosis treatment',
        includeAbstracts: true,
      }
    );

    const taskId = response.taskId;
    console.log(`Started task: ${taskId}`);

    // Subscribe to progress updates
    const unsubscribe = bridge.subscribeToProgress(taskId, (event: ProgressEvent) => {
      switch (event.type) {
        case 'progress':
          console.log(`Progress: ${event.data.progress?.percentage}%`);
          console.log(`  ${event.data.message}`);
          break;

        case 'checkpoint':
          console.log('Checkpoint reached:', event.data.checkpoint);
          break;

        case 'log':
          console.log(`[Log] ${event.data.log}`);
          break;

        case 'error':
          console.error(`[Error] ${event.data.error?.message} (${event.data.error?.code})`);
          break;

        case 'completed':
          console.log('Task completed!');
          unsubscribe(); // Stop listening
          break;
      }
    });

    // Listen to bridge events
    bridge.on('agent:completed', ({ taskId }) => {
      console.log(`Agent task ${taskId} completed`);
    });

    bridge.on('agent:error', ({ agentType, error }) => {
      console.error(`Agent ${agentType} error: ${error}`);
    });

    // Keep the process alive while task runs
    await new Promise((resolve) => setTimeout(resolve, 600000)); // 10 minutes
  } catch (error) {
    console.error('Error:', error);
  }
}

// ============================================================================
// EXAMPLE 3: Multiple Agents in Parallel
// ============================================================================

/**
 * Run multiple agents concurrently
 */
async function example3_multipleAgentsInParallel(): Promise<void> {
  const bridge = getLangChainBridge();

  try {
    // Start multiple agents
    const tasks = await Promise.all([
      bridge.runAgent(AgentType.DataProcessor, {
        datasetId: 'dataset-1',
        operation: 'normalize',
      }),

      bridge.runAgent(AgentType.ManuscriptGenerator, {
        title: 'AI in Medicine: A Comprehensive Review',
        outline: ['Introduction', 'Background', 'Methods', 'Results', 'Discussion'],
      }),

      bridge.runAgent(AgentType.GuidelineExtractor, {
        documentUrl: 'https://example.com/guidelines',
        domains: ['cardiology', 'oncology'],
      }),
    ]);

    console.log('Started tasks:', tasks.map((t) => t.taskId));

    // Monitor all tasks
    const statusPromises = tasks.map(async (task) => {
      const unsubscribe = bridge.subscribeToProgress(task.taskId, (event) => {
        if (event.type === 'progress') {
          console.log(
            `[${task.agentType}] ${event.data.progress?.percentage}% - ${event.data.message}`
          );
        }
      });

      // Wait for completion
      let status: AgentStatusResponse;
      do {
        await new Promise((resolve) => setTimeout(resolve, 5000));
        status = await bridge.getAgentStatus(task.taskId);
      } while (status.status === TaskStatus.Running);

      unsubscribe();
      return status;
    });

    const results = await Promise.all(statusPromises);

    console.log('All tasks completed:', {
      completed: results.filter((r) => r.status === TaskStatus.Completed).length,
      failed: results.filter((r) => r.status === TaskStatus.Failed).length,
    });
  } catch (error) {
    console.error('Error:', error);
  }
}

// ============================================================================
// EXAMPLE 4: Error Handling and Retries
// ============================================================================

/**
 * Demonstrate error handling with automatic retries
 */
async function example4_errorHandlingAndRetries(): Promise<void> {
  const bridge = getLangChainBridge();

  async function runAgentWithFallback(
    agentType: AgentType | string,
    data: Record<string, unknown>,
    maxAttempts: number = 3
  ): Promise<AgentTaskResponse | null> {
    for (let attempt = 1; attempt <= maxAttempts; attempt++) {
      try {
        console.log(`Attempt ${attempt}/${maxAttempts}...`);
        return await bridge.runAgent(agentType, data, {
          timeout: 60000,
        });
      } catch (error) {
        console.error(`Attempt ${attempt} failed:`, error);

        if (attempt < maxAttempts) {
          // Exponential backoff
          const delayMs = 1000 * Math.pow(2, attempt - 1);
          console.log(`Retrying after ${delayMs}ms...`);
          await new Promise((resolve) => setTimeout(resolve, delayMs));
        }
      }
    }

    return null;
  }

  try {
    const result = await runAgentWithFallback(
      AgentType.ResearchAnalyzer,
      {
        title: 'New Topic',
        keywords: ['research'],
      }
    );

    if (result) {
      console.log('Agent executed successfully:', result.taskId);
    } else {
      console.log('Agent execution failed after all retries');
    }
  } catch (error) {
    console.error('Error:', error);
  }
}

// ============================================================================
// EXAMPLE 5: Task Cancellation
// ============================================================================

/**
 * Run agent and cancel if it takes too long
 */
async function example5_taskCancellation(): Promise<void> {
  const bridge = getLangChainBridge();

  try {
    const response = await bridge.runAgent(AgentType.LiteratureReviewer, {
      topic: 'Complex Research Topic',
      maxResults: 10000, // Large request that might take time
    });

    const taskId = response.taskId;

    // Set a timeout to cancel the task
    const timeoutHandle = setTimeout(async () => {
      console.log('Timeout reached, cancelling task...');
      try {
        const cancelResult = await bridge.cancelTask(taskId);
        console.log('Task cancelled:', cancelResult);
      } catch (error) {
        console.error('Failed to cancel task:', error);
      }
    }, 300000); // 5 minutes

    // Monitor progress
    const unsubscribe = bridge.subscribeToProgress(taskId, (event) => {
      if (event.type === 'completed' || event.type === 'error') {
        clearTimeout(timeoutHandle);
        unsubscribe();
      }
    });
  } catch (error) {
    console.error('Error:', error);
  }
}

// ============================================================================
// EXAMPLE 6: Health Checks and Circuit Breaker
// ============================================================================

/**
 * Monitor bridge health and circuit breaker status
 */
async function example6_healthChecksAndCircuitBreaker(): Promise<void> {
  const bridge = getLangChainBridge();

  try {
    // Perform health check
    const health = await bridge.healthCheck();

    console.log('Bridge Health:', {
      healthy: health.healthy,
      connected: health.agentServiceConnected,
      latencyMs: health.latencyMs,
      error: health.error,
    });

    // Check circuit breaker status
    const cbStatus = bridge.getCircuitBreakerStatus();

    console.log('Circuit Breaker Status:', {
      state: cbStatus.state,
      failures: cbStatus.failures,
      successes: cbStatus.successes,
      lastFailure: cbStatus.lastFailure,
      nextAttempt: cbStatus.nextAttemptAt,
    });

    // If circuit is open, it will recover after reset timeout
    if (cbStatus.state === 'OPEN') {
      console.log(`Circuit is open, will attempt recovery at ${cbStatus.nextAttemptAt}`);
    }
  } catch (error) {
    console.error('Error:', error);
  }
}

// ============================================================================
// EXAMPLE 7: Event Listener Pattern
// ============================================================================

/**
 * Use EventEmitter pattern to listen to bridge events
 */
async function example7_eventListenerPattern(): Promise<void> {
  const bridge = getLangChainBridge();

  // Set up global event listeners
  bridge.on('agent:started', ({ taskId, agentType }) => {
    console.log(`Agent started: ${agentType} (${taskId})`);
  });

  bridge.on('agent:completed', ({ taskId }) => {
    console.log(`Agent completed: ${taskId}`);
  });

  bridge.on('agent:error', ({ agentType, error }) => {
    console.error(`Agent error in ${agentType}: ${error}`);
  });

  bridge.on('progress:connected', ({ taskId }) => {
    console.log(`WebSocket connected for task: ${taskId}`);
  });

  bridge.on('progress:disconnected', ({ taskId }) => {
    console.log(`WebSocket disconnected for task: ${taskId}`);
  });

  bridge.on('progress:update', ({ taskId, event }) => {
    console.log(`Progress update for ${taskId}:`, event.type);
  });

  // Now run an agent and events will be logged
  try {
    const response = await bridge.runAgent(AgentType.DataProcessor, {
      datasetId: 'dataset-1',
    });

    // Wait a bit to see events
    await new Promise((resolve) => setTimeout(resolve, 30000));
  } catch (error) {
    console.error('Error:', error);
  }
}

// ============================================================================
// EXAMPLE 8: Express Integration
// ============================================================================

/**
 * Integrate LangChain bridge into Express routes
 */
async function example8_expressIntegration(): Promise<void> {
  // This would be in your Express route handler
  // @ts-ignore
  const handleRunAgent = async (req: any, res: any): Promise<void> => {
    try {
      const bridge = getLangChainBridge();
      const { agentType, data, priority } = req.body;

      // Validate inputs
      if (!agentType || !data) {
        res.status(400).json({ error: 'Missing agentType or data' });
        return;
      }

      // Run agent
      const response = await bridge.runAgent(agentType, data, {
        priority,
        metadata: {
          userId: req.user?.id,
          projectId: req.query.projectId as string,
          requestId: req.id,
        },
      });

      res.json({
        success: true,
        taskId: response.taskId,
        status: response.status,
      });
    } catch (error) {
      res.status(500).json({
        error: error instanceof Error ? error.message : 'Unknown error',
      });
    }
  };

  // @ts-ignore
  const handleGetStatus = async (req: any, res: any): Promise<void> => {
    try {
      const bridge = getLangChainBridge();
      const { taskId } = req.params;

      const status = await bridge.getAgentStatus(taskId);

      res.json(status);
    } catch (error) {
      res.status(500).json({
        error: error instanceof Error ? error.message : 'Unknown error',
      });
    }
  };

  // @ts-ignore
  const handleCancelTask = async (req: any, res: any): Promise<void> => {
    try {
      const bridge = getLangChainBridge();
      const { taskId } = req.params;

      const result = await bridge.cancelTask(taskId);

      res.json(result);
    } catch (error) {
      res.status(500).json({
        error: error instanceof Error ? error.message : 'Unknown error',
      });
    }
  };

  console.log('Express route handlers defined (for reference)');
}

// ============================================================================
// EXAMPLE 9: WebSocket Progress Handler
// ============================================================================

/**
 * Advanced progress handling with custom transformation
 */
async function example9_advancedProgressHandling(): Promise<void> {
  const bridge = getLangChainBridge();

  interface TaskMetrics {
    totalProgress: number;
    stepsCompleted: number;
    estimatedTimeRemaining: number;
    averageStepTime: number;
  }

  const metrics: TaskMetrics = {
    totalProgress: 0,
    stepsCompleted: 0,
    estimatedTimeRemaining: 0,
    averageStepTime: 0,
  };

  const startTime = Date.now();
  const stepStartTimes: Record<string, number> = {};

  try {
    const response = await bridge.runAgent(AgentType.ManuscriptGenerator, {
      title: 'Research Manuscript',
    });

    bridge.subscribeToProgress(response.taskId, (event: ProgressEvent) => {
      if (event.type === 'progress' && event.data.progress) {
        const now = Date.now();
        const elapsedMs = now - startTime;
        const { current, total, percentage } = event.data.progress;

        // Update metrics
        metrics.totalProgress = percentage;
        metrics.stepsCompleted = current;

        // Calculate average step time
        if (metrics.stepsCompleted > 0) {
          metrics.averageStepTime = elapsedMs / metrics.stepsCompleted;
          metrics.estimatedTimeRemaining =
            metrics.averageStepTime * (total - current);
        }

        console.log('Task Metrics:', {
          progress: `${percentage}%`,
          stepsCompleted: `${current}/${total}`,
          elapsedSeconds: Math.round(elapsedMs / 1000),
          estimatedRemainingSeconds: Math.round(
            metrics.estimatedTimeRemaining / 1000
          ),
          averageStepSeconds: Math.round(metrics.averageStepTime / 1000),
        });
      }
    });

    // Wait for completion
    await new Promise((resolve) => setTimeout(resolve, 600000));
  } catch (error) {
    console.error('Error:', error);
  }
}

// ============================================================================
// EXAMPLE 10: Cleanup and Resource Management
// ============================================================================

/**
 * Proper cleanup when bridge is no longer needed
 */
async function example10_cleanupAndResourceManagement(): Promise<void> {
  const bridge = getLangChainBridge();

  try {
    // Use bridge
    const response = await bridge.runAgent(AgentType.ResearchAnalyzer, {
      title: 'Test',
    });

    console.log('Task started:', response.taskId);

    // Monitor with timeout
    const timeoutHandle = setTimeout(() => {
      console.log('Timeout, closing bridge');
      bridge.close(); // Clean up WebSocket connections
      resetLangChainBridge(); // Reset singleton
    }, 60000);

    // Wait for completion or timeout
    await new Promise((resolve) => setTimeout(resolve, 60000));
    clearTimeout(timeoutHandle);
  } catch (error) {
    console.error('Error:', error);
  } finally {
    // Always clean up
    bridge.close();
    resetLangChainBridge();
    console.log('Bridge cleaned up');
  }
}

// ============================================================================
// EXPORT EXAMPLES
// ============================================================================

export {
  example1_basicAgentExecution,
  example2_realtimeProgressMonitoring,
  example3_multipleAgentsInParallel,
  example4_errorHandlingAndRetries,
  example5_taskCancellation,
  example6_healthChecksAndCircuitBreaker,
  example7_eventListenerPattern,
  example8_expressIntegration,
  example9_advancedProgressHandling,
  example10_cleanupAndResourceManagement,
};
