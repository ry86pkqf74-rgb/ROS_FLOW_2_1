/**
 * AI Bridge End-to-End Integration Test
 * 
 * Validates the complete flow from Python-style request through the bridge
 */

import assert from 'node:assert';
import { test, describe, beforeEach } from 'node:test';

import express from 'express';
import request from 'supertest';

import aiBridgeRoutes from '../ai-bridge';

// Create test app with full middleware stack
function createE2ETestApp() {
  const app = express();
  app.use(express.json());
  
  // Mock authenticated user with proper context
  app.use((req, res, next) => {
    req.user = {
      id: 'python-agent-user',
      email: 'python-agent@researchflow.ai',
      role: 'researcher',
    };
    next();
  });
  
  app.use('/api/ai-bridge', aiBridgeRoutes);
  return app;
}

describe('AI Bridge End-to-End Tests', () => {
  test('should handle hypothesis generation workflow', async () => {
    const app = createE2ETestApp();
    
    // Simulate a typical Python agent request
    const pythonAgentRequest = {
      prompt: `Based on the following preliminary data, generate 3 testable research hypotheses:
        
        Study Context: Effects of remote work on productivity
        Data Summary: 40% increase in self-reported productivity, 25% decrease in collaboration
        Sample Size: 500 knowledge workers
        Duration: 6 months
        
        Please provide hypotheses that are:
        1. Specific and measurable
        2. Address the productivity-collaboration trade-off
        3. Suitable for further statistical testing`,
      
      options: {
        taskType: 'hypothesis_generation',
        stageId: 3,
        modelTier: 'STANDARD',
        governanceMode: 'DEMO',
        requirePhiCompliance: false,
        maxTokens: 2000,
        temperature: 0.7
      },
      
      metadata: {
        agentId: 'research-hypothesis-agent',
        projectId: 'remote-work-study-2024',
        runId: 'hypothesis-gen-run-001',
        threadId: 'hypothesis-thread-main',
        stageRange: [1, 10],
        currentStage: 3
      }
    };
    
    const response = await request(app)
      .post('/api/ai-bridge/invoke')
      .send(pythonAgentRequest)
      .expect(200);
    
    // Validate response structure matches Python expectations
    assert(response.body.content);
    assert(typeof response.body.content === 'string');
    assert(response.body.content.length > 100, 'Response should be substantial');
    
    // Validate usage tracking
    assert(response.body.usage);
    assert(typeof response.body.usage.totalTokens === 'number');
    assert(response.body.usage.totalTokens > 0);
    assert(typeof response.body.usage.promptTokens === 'number');
    assert(typeof response.body.usage.completionTokens === 'number');
    
    // Validate cost tracking
    assert(response.body.cost);
    assert(typeof response.body.cost.total === 'number');
    assert(response.body.cost.total > 0);
    assert(typeof response.body.cost.input === 'number');
    assert(typeof response.body.cost.output === 'number');
    
    // Validate model routing worked
    assert(response.body.model);
    assert(response.body.tier);
    assert(['economy', 'standard', 'premium'].includes(response.body.tier));
    
    // Validate metadata for agent tracking
    assert(response.body.metadata);
    assert(response.body.metadata.requestId);
    assert(response.body.metadata.routingMethod === 'ai_router');
    assert(response.body.metadata.bridgeVersion === '1.0.0');
    
    console.log(`✅ Hypothesis Generation Test:
      - Response Length: ${response.body.content.length} chars
      - Total Tokens: ${response.body.usage.totalTokens}
      - Total Cost: $${response.body.cost.total.toFixed(4)}
      - Model: ${response.body.model}
      - Tier: ${response.body.tier}`);
  });

  test('should handle PHI redaction workflow', async () => {
    const app = createE2ETestApp();
    
    const phiRedactionRequest = {
      prompt: `Please analyze the following clinical note for potential PHI and redact any sensitive information:
        
        "Patient John Doe (DOB: 01/15/1975, SSN: 123-45-6789) was seen on 03/22/2024 at Memorial Hospital. 
        His phone number is 555-123-4567. He lives at 123 Main St, Boston, MA 02101. 
        Dr. Sarah Johnson noted elevated blood pressure (160/90) and prescribed medication. 
        Patient's email: john.doe@email.com. Insurance ID: ABC123456789."
        
        Replace all PHI with appropriate placeholders while preserving medical relevance.`,
      
      options: {
        taskType: 'phi_redaction',
        stageId: 8,
        modelTier: 'PREMIUM',
        governanceMode: 'LIVE',
        requirePhiCompliance: true,
        maxTokens: 1500,
        temperature: 0.1  // Lower temperature for consistency
      },
      
      metadata: {
        agentId: 'phi-redaction-agent',
        projectId: 'clinical-data-processing',
        runId: 'phi-redaction-run-002',
        threadId: 'phi-safety-thread',
        stageRange: [5, 15],
        currentStage: 8
      }
    };
    
    const response = await request(app)
      .post('/api/ai-bridge/invoke')
      .send(phiRedactionRequest)
      .expect(200);
    
    // Validate PHI handling response
    assert(response.body.content);
    assert(response.body.content.includes('['), 'Should contain redaction placeholders');
    
    // Should route to premium tier for PHI tasks
    assert(response.body.tier === 'standard' || response.body.tier === 'premium');
    
    console.log(`✅ PHI Redaction Test:
      - Content includes redaction: ${response.body.content.includes('[')}
      - PHI Compliance Mode: ${phiRedactionRequest.options.requirePhiCompliance}
      - Model Tier: ${response.body.tier}`);
  });

  test('should handle batch manuscript processing', async () => {
    const app = createE2ETestApp();
    
    const batchRequest = {
      prompts: [
        'Summarize the methodology section of this research paper focusing on data collection procedures.',
        'Extract the key statistical findings and their significance levels from the results.',
        'Identify the main limitations discussed by the authors and their potential impact.',
        'Summarize the conclusions and their implications for future research.'
      ],
      
      options: {
        taskType: 'manuscript_drafting',
        modelTier: 'STANDARD',
        governanceMode: 'DEMO',
        requirePhiCompliance: false,
        temperature: 0.5
      },
      
      metadata: {
        agentId: 'manuscript-processing-agent',
        projectId: 'literature-review-2024',
        runId: 'batch-manuscript-run-003',
        threadId: 'manuscript-batch-thread',
        stageRange: [10, 20],
        currentStage: 15
      }
    };
    
    const response = await request(app)
      .post('/api/ai-bridge/batch')
      .send(batchRequest)
      .expect(200);
    
    // Validate batch response structure
    assert(Array.isArray(response.body.responses));
    assert(response.body.responses.length === 4);
    
    // Check each response
    response.body.responses.forEach((resp: any, index: number) => {
      assert(resp.content, `Response ${index} should have content`);
      assert(resp.usage, `Response ${index} should have usage stats`);
      assert(resp.cost, `Response ${index} should have cost info`);
      assert(resp.index === index, `Response ${index} should have correct index`);
    });
    
    // Validate batch metadata
    assert(typeof response.body.totalCost === 'number');
    assert(typeof response.body.averageLatency === 'number');
    assert(response.body.successCount === 4);
    assert(response.body.errorCount === 0);
    
    console.log(`✅ Batch Processing Test:
      - Responses: ${response.body.responses.length}
      - Success Rate: ${response.body.successCount}/${response.body.successCount + response.body.errorCount}
      - Total Cost: $${response.body.totalCost.toFixed(4)}
      - Avg Latency: ${response.body.averageLatency}ms`);
  });

  test('should handle streaming data analysis', async () => {
    const app = createE2ETestApp();
    
    const streamRequest = {
      prompt: `Provide a comprehensive analysis of the following research dataset:
        
        Dataset: Customer satisfaction survey responses
        Variables: satisfaction_score (1-10), service_type (A/B/C), response_time (minutes), region (North/South/East/West)
        Sample size: 2,847 responses
        Collection period: Q1 2024
        
        Please analyze:
        1. Distribution patterns across variables
        2. Correlation between service_type and satisfaction
        3. Regional variations in satisfaction scores
        4. Impact of response_time on satisfaction
        5. Recommendations for service improvement
        
        Provide detailed statistical insights and actionable recommendations.`,
      
      options: {
        taskType: 'data_analysis',
        modelTier: 'PREMIUM',
        governanceMode: 'DEMO',
        requirePhiCompliance: false,
        maxTokens: 3000,
        temperature: 0.6
      },
      
      metadata: {
        agentId: 'data-analysis-agent',
        projectId: 'customer-satisfaction-study',
        runId: 'stream-analysis-run-004',
        threadId: 'analysis-stream-thread',
        stageRange: [5, 12],
        currentStage: 8
      }
    };
    
    const response = await request(app)
      .post('/api/ai-bridge/stream')
      .send(streamRequest)
      .expect(200);
    
    // Validate SSE headers
    assert(response.headers['content-type'] === 'text/event-stream');
    assert(response.headers['cache-control'] === 'no-cache');
    assert(response.headers.connection === 'keep-alive');
    
    // Parse SSE response
    const lines = response.text.split('\n');
    const dataLines = lines.filter(line => line.startsWith('data: '));
    
    // Should have status, content chunks, and completion
    const statusEvents = dataLines.filter(line => line.includes('"type":"status"'));
    const contentEvents = dataLines.filter(line => line.includes('"type":"content"'));
    const completeEvents = dataLines.filter(line => line.includes('"type":"complete"'));
    const doneMarker = lines.includes('data: [DONE]');
    
    assert(statusEvents.length > 0, 'Should have status events');
    assert(contentEvents.length > 0, 'Should have content events');
    assert(completeEvents.length > 0, 'Should have completion event');
    assert(doneMarker, 'Should have [DONE] marker');
    
    // Validate completion data
    const completeData = JSON.parse(completeEvents[0].substring(6));
    assert(completeData.finalContent);
    assert(completeData.usage);
    assert(completeData.cost);
    
    console.log(`✅ Streaming Test:
      - Status Events: ${statusEvents.length}
      - Content Events: ${contentEvents.length}
      - Complete Events: ${completeEvents.length}
      - Stream Complete: ${doneMarker}
      - Final Cost: $${completeData.cost?.total?.toFixed(4) || 'N/A'}`);
  });

  test('should validate metrics collection', async () => {
    const app = createE2ETestApp();
    
    // Make a few requests to generate metrics
    const testRequest = {
      prompt: 'Quick test for metrics collection',
      options: {
        taskType: 'summarization',
        modelTier: 'ECONOMY'
      },
      metadata: {
        agentId: 'metrics-test-agent',
        projectId: 'metrics-test',
        runId: 'metrics-run',
        threadId: 'metrics-thread',
        stageRange: [1, 5],
        currentStage: 1
      }
    };
    
    // Make multiple requests to generate metrics
    await request(app)
      .post('/api/ai-bridge/invoke')
      .send(testRequest)
      .expect(200);
    
    await request(app)
      .post('/api/ai-bridge/invoke')
      .send(testRequest)
      .expect(200);
    
    // Get metrics
    const metricsResponse = await request(app)
      .get('/api/ai-bridge/metrics')
      .expect(200);
    
    // Validate Prometheus format
    const metricsText = metricsResponse.text;
    assert(metricsText.includes('ai_bridge_requests_total'));
    assert(metricsText.includes('ai_bridge_request_duration_seconds'));
    assert(metricsText.includes('ai_bridge_cost_total_dollars'));
    assert(metricsText.includes('ai_bridge_tokens_total'));
    
    console.log(`✅ Metrics Test:
      - Prometheus format: ${metricsText.includes('# TYPE')}
      - Request metrics: ${metricsText.includes('ai_bridge_requests_total')}
      - Cost metrics: ${metricsText.includes('ai_bridge_cost_total_dollars')}
      - Token metrics: ${metricsText.includes('ai_bridge_tokens_total')}`);
  });
});
