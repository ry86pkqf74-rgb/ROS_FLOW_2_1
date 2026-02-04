# Quick Start: Enhanced References API

This guide shows you how to use the new AI-enhanced reference processing endpoints in ResearchFlow's unified API.

## 🚀 Quick Setup

### 1. Start the Unified API Server

```bash
cd services/worker
python3 api_server.py
```

The server will start on `http://localhost:8000`. You can verify it's running:

```bash
curl http://localhost:8000/health
```

### 2. Check Enhanced References Availability

```bash
curl http://localhost:8000/api/references/health
```

Expected response:
```json
{
  "status": "healthy",
  "enhanced_references_available": true,
  "integration_hub_status": "healthy"
}
```

## 🎯 Basic Usage Examples

### Example 1: AI-Enhanced Reference Processing

Process manuscript text and get AI-powered reference suggestions:

```bash
curl -X POST "http://localhost:8000/api/references/process" \
  -H "Content-Type: application/json" \
  -d '{
    "study_id": "demo_001",
    "manuscript_text": "Recent studies show benefits of early intervention [citation needed]. Multiple randomized controlled trials have demonstrated significant efficacy in reducing mortality [citation needed]. However, there remain gaps in our understanding of optimal timing [citation needed].",
    "enable_ai_processing": true,
    "enable_semantic_matching": true,
    "enable_gap_detection": true,
    "enable_context_analysis": true,
    "target_style": "ama",
    "research_field": "clinical_medicine"
  }'
```

### Example 2: Get Reference Insights

Analyze existing references for improvement opportunities:

```bash
curl -X POST "http://localhost:8000/api/references/insights" \
  -H "Content-Type: application/json" \
  -d '{
    "references": [
      {
        "title": "Early intervention in acute care",
        "authors": ["Smith J", "Johnson A"],
        "journal": "NEJM",
        "year": 2023,
        "doi": "10.1056/NEJMoa2023001"
      }
    ],
    "manuscript_text": "Our study focuses on early intervention strategies...",
    "research_field": "emergency_medicine"
  }'
```

### Example 3: Optimize Citation Strategy

Get AI recommendations for citation optimization:

```bash
curl -X POST "http://localhost:8000/api/references/optimize" \
  -H "Content-Type: application/json" \
  -d '{
    "references": [
      {
        "title": "Clinical outcomes in emergency care",
        "authors": ["Brown R", "Davis M"],
        "journal": "Emergency Medicine Journal",
        "year": 2022
      }
    ],
    "target_journal": "NEJM",
    "manuscript_abstract": "This study evaluated the impact of early intervention protocols on patient outcomes in emergency departments."
  }'
```

## 🛠️ Configuration Options

### AI Enhancement Controls

You can fine-tune AI processing with these options:

```json
{
  "enable_ai_processing": true,        // Enable AI-enhanced processing
  "enable_semantic_matching": true,    // AI semantic similarity matching
  "enable_gap_detection": true,        // Literature gap identification
  "enable_context_analysis": true,     // Citation context analysis
  "enable_quality_metrics": true,      // Advanced quality assessment
  "enable_ai_insights": true,          // AI insights and recommendations
  "ai_fallback_on_error": true,        // Fall back to basic processing if AI fails
  "strict_mode": false                 // Fail on any error vs graceful degradation
}
```

### Citation Styles

Supported citation styles:
- `ama` (American Medical Association)
- `apa` (American Psychological Association)
- `vancouver` (Vancouver)
- `harvard` (Harvard)
- `chicago` (Chicago)
- `nature` (Nature)
- `cell` (Cell)
- `jama` (JAMA)
- `mla` (MLA)
- `ieee` (IEEE)

### Processing Limits

```json
{
  "max_references": 50,                // Maximum references to process
  "research_field": "clinical_medicine", // Research field for context
  "target_journal": "NEJM"             // Target journal for optimization
}
```

## 📊 Response Format

### Enhanced Processing Response

```json
{
  "success": true,
  "processing_mode": "ai_enhanced",
  "study_id": "demo_001",
  "references": [...],                 // Processed references
  "citations": [...],                  // Generated citations
  "bibliography": "...",               // Formatted bibliography
  
  "ai_enhancements": {
    "semantic_matches": [...],         // AI-found semantic matches
    "literature_gaps": [...],          // Identified gaps in literature
    "citation_contexts": [...],        // Context analysis results
    "quality_metrics": [...]           // Advanced quality scores
  },
  
  "quality_summary": {
    "overall_score": 0.85,             // Overall quality (0-1)
    "completeness_score": 0.90,        // Literature completeness
    "ai_confidence": 0.88              // AI confidence level
  },
  
  "insights": {
    "improvement_recommendations": [...], // Actionable improvements
    "priority_issues": [...],            // High-priority issues
    "suggested_actions": [...]           // Specific actions to take
  },
  
  "journal_recommendations": [...],      // Journal-specific guidance
  "processing_time_seconds": 3.45
}
```

## 🔧 Error Handling & Fallback

The system includes circuit breaker patterns and graceful fallbacks:

### Circuit Breaker Status

Check circuit breaker status:

```bash
curl http://localhost:8000/api/references/status
```

### Graceful Fallback

When AI processing fails, the system automatically falls back to basic processing:

```json
{
  "processing_mode": "basic",
  "ai_fallback_reason": "AI service temporarily unavailable",
  "circuit_breaker_status": "open"
}
```

## 🚦 Health Monitoring

### Check System Capabilities

```bash
curl http://localhost:8000/api/references/capabilities
```

### Monitor Performance

```bash
curl http://localhost:8000/api/references/status
```

## 📚 Integration Examples

### Python Integration

```python
import aiohttp
import asyncio
import json

async def process_references_ai(study_id, manuscript_text):
    async with aiohttp.ClientSession() as session:
        payload = {
            "study_id": study_id,
            "manuscript_text": manuscript_text,
            "enable_ai_processing": True,
            "enable_semantic_matching": True,
            "target_style": "ama"
        }
        
        async with session.post(
            "http://localhost:8000/api/references/process",
            json=payload
        ) as response:
            return await response.json()

# Usage
result = asyncio.run(process_references_ai(
    "study_001", 
    "Your manuscript text here..."
))
print(f"Processing mode: {result['processing_mode']}")
```

### JavaScript/Node.js Integration

```javascript
const axios = require('axios');

async function processReferences(studyId, manuscriptText) {
  try {
    const response = await axios.post('http://localhost:8000/api/references/process', {
      study_id: studyId,
      manuscript_text: manuscriptText,
      enable_ai_processing: true,
      enable_semantic_matching: true,
      target_style: 'ama'
    });
    
    console.log('Processing mode:', response.data.processing_mode);
    return response.data;
  } catch (error) {
    console.error('Error processing references:', error.message);
    throw error;
  }
}
```

### cURL Script for Batch Processing

```bash
#!/bin/bash

# Process multiple studies
studies=("study_001" "study_002" "study_003")

for study in "${studies[@]}"; do
  echo "Processing $study..."
  
  curl -X POST "http://localhost:8000/api/references/process" \
    -H "Content-Type: application/json" \
    -d "{
      \"study_id\": \"$study\",
      \"manuscript_text\": \"Sample manuscript text for $study...\",
      \"enable_ai_processing\": true,
      \"target_style\": \"ama\"
    }" | jq '.processing_mode, .success'
  
  echo "---"
done
```

## 🔍 Troubleshooting

### Common Issues

1. **Service Unavailable (503)**
   - Check if enhanced references module is loaded
   - Verify dependencies are installed

2. **AI Processing Fails**
   - Check circuit breaker status
   - Enable fallback mode with `ai_fallback_on_error: true`

3. **Slow Response Times**
   - Monitor circuit breaker state
   - Consider reducing AI enhancement features

### Debugging Commands

```bash
# Check service health
curl http://localhost:8000/api/references/health

# Check capabilities
curl http://localhost:8000/api/references/capabilities

# Check detailed status
curl http://localhost:8000/api/references/status

# Test basic health
curl http://localhost:8000/health
```

## 📈 Performance Optimization

### Recommended Settings for Production

```json
{
  "enable_ai_processing": true,
  "enable_semantic_matching": true,
  "enable_gap_detection": false,      // Disable for faster processing
  "enable_context_analysis": true,
  "enable_quality_metrics": false,   // Disable for faster processing
  "ai_fallback_on_error": true,
  "max_references": 30               // Limit for performance
}
```

### Batch Processing Tips

1. Process studies sequentially to avoid overwhelming the AI services
2. Use health checks to verify system status before batch operations
3. Monitor circuit breaker state during heavy usage
4. Enable fallback mode for reliability

---

## 🎯 Next Steps

1. **Run the smoke test**: `python3 services/worker/test_api_integration.py`
2. **Explore the full API documentation**: Visit `http://localhost:8000/docs`
3. **Check out advanced features**: Review the enhanced references module documentation
4. **Integrate with your workflow**: Use the examples above as starting points

---

*This guide covers the core functionality. For advanced configuration and customization, refer to the full API documentation and the enhanced reference management system documentation.*