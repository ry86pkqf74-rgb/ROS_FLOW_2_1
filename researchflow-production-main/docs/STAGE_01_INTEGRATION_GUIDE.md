# Stage 1 Protocol Design Agent - Integration Guide

## Overview

The Stage 1 Protocol Design Agent is a new PICO-based implementation that replaces the legacy file upload stage. This guide covers integration, deployment, and usage.

## Architecture

### New Implementation
- **Agent**: `ProtocolDesignAgent` (LangGraph-based)
- **Wrapper**: `ProtocolDesignStage` (Workflow Engine adapter)
- **Registry**: Feature flag controlled via `ENABLE_NEW_STAGE_1`

### PICO Framework Integration
```
Stage 1: Protocol Design  →  Stage 2: Literature  →  Stage 3: IRB
         PICO Elements    →   Search Queries    →   Protocol Data
```

## Feature Flag Deployment

### Environment Configuration

```bash
# services/worker/.env
ENABLE_NEW_STAGE_1=false  # CRITICAL: Set to 'true' to enable new agent

# Protocol Design Agent Settings
PICO_LLM_MODEL_TIER=STANDARD
PROTOCOL_DESIGN_TIMEOUT=300
PROTOCOL_MAX_ITERATIONS=5

# Quality Thresholds
PICO_QUALITY_THRESHOLD=70.0
PROTOCOL_SECTIONS_MIN=7
PROTOCOL_LENGTH_MIN=500

# Integration Flags
STAGE2_PICO_INTEGRATION=true
STAGE3_PICO_INTEGRATION=true
```

### Deployment Strategy

1. **Phase 1: Deploy with flag disabled** (`ENABLE_NEW_STAGE_1=false`)
2. **Phase 2: Internal testing** (Enable for dev team only)  
3. **Phase 3: Beta rollout** (10% of traffic)
4. **Phase 4: Full rollout** (100% of traffic)
5. **Phase 5: Legacy deprecation** (Remove old upload stage)

## Integration Points

### Stage 2 Literature Integration

Stage 2 automatically detects and uses PICO data from Stage 1:

```python
# services/worker/src/workflow_engine/stages/stage_02_literature.py
def _extract_search_config(self, context: StageContext) -> Dict[str, Any]:
    stage1_output = context.get_prior_stage_output(1) or {}
    pico_elements = stage1_output.get("pico_elements", {})
    pico_search_query = stage1_output.get("search_query", "")
    
    if pico_elements:
        # Use PICO-optimized search
        return {
            "pico_search_query": pico_search_query,
            "keywords": pico_keywords,
            "pico_driven_search": True
        }
```

### Stage 3 IRB Integration

Stage 3 uses PICO data for protocol generation:

```python
# services/worker/src/workflow_engine/stages/stage_03_irb.py
def _extract_irb_data(self, context: StageContext) -> Dict[str, Any]:
    stage1_output = context.get_prior_stage_output(1) or {}
    pico_elements = stage1_output.get("pico_elements", {})
    
    return {
        "hypothesis": stage1_output.get("primary_hypothesis"),
        "population": pico_elements.get("population"),
        "variables": pico_elements.get("outcomes", []),
        "studyType": map_study_type(stage1_output.get("study_type"))
    }
```

## Agent Execution Flow

### 1. Entry Mode Detection
```
User Input → [Quick Entry | PICO Direct | Hypothesis Mode]
```

### 2. PICO Processing
```
Quick Entry → LLM Extraction → PICO Elements
PICO Direct → Validation → PICO Elements  
Hypothesis → Skip to Study Design → PICO Elements
```

### 3. Protocol Generation
```
PICO Elements → Hypothesis → Study Design → Protocol Outline → Quality Gate
```

### 4. Quality Gates
- PICO completeness and quality (≥70 score)
- Hypothesis generation (null, alternative, comparative)
- Study type identification
- Protocol sections (≥7 sections)
- Protocol length (≥500 characters)
- PHI compliance

## Frontend Integration

### TypeScript Types

```typescript
// packages/ai-agents/src/types/protocol-design.types.ts
interface ProtocolDesignOutput {
  pico_elements: PICOElements;
  hypotheses: ResearchHypotheses;
  study_type: StudyType;
  protocol_outline: string;
  search_query: string;
  stage_1_complete: boolean;
}

interface PICOElements {
  population: string;
  intervention: string;
  comparator: string;
  outcomes: string[];
  timeframe: string;
}
```

### Stage Definition Update

```typescript
// services/web/src/workflow/stages.ts
1: {
  name: 'Protocol Design',
  description: 'Design research protocols using PICO framework and AI assistance',
  outputTypes: ['pico_framework.json', 'protocol_outline.md', 'hypotheses.json'],
  estimatedDuration: 45,
  recommendedModelTier: 'STANDARD',
}
```

## Testing

### Unit Tests
```bash
# PICO Module Tests
pytest tests/unit/agents/common/test_pico.py -v

# Protocol Design Agent Tests  
pytest tests/unit/agents/protocol_design/test_agent.py -v

# Feature Flag Tests
pytest tests/integration/test_stage1_feature_flag.py -v
```

### Integration Tests
```bash
# PICO Pipeline Tests
pytest tests/integration/test_pico_pipeline.py -v

# Stage 1→2→3 Flow
pytest tests/integration/test_pico_pipeline.py::test_full_pico_pipeline_stage1_to_stage2 -v
```

### End-to-End Testing
```bash
# Feature flag enabled
ENABLE_NEW_STAGE_1=true pytest tests/integration/ -k "stage1" -v

# Feature flag disabled (legacy)
ENABLE_NEW_STAGE_1=false pytest tests/integration/ -k "stage1" -v
```

## Monitoring & Metrics

### Key Metrics
- **PICO Quality Score**: Target >75 average
- **Protocol Generation Success**: Target >95%
- **Stage 1→2 Integration**: Target >90% valid handoff
- **User Completion Rate**: Compare to legacy Stage 1

### Logging
```python
logger.info(f"Using PICO output from Stage 1: {pico.population[:50]}...")
logger.info(f"Enhanced PICO search integration: {pico.population[:50]}...")
logger.info(f"Stage 1 protocol design completed successfully")
```

### Error Monitoring
- PICO extraction failures
- LLM timeout errors
- Quality gate failures
- Integration breakages

## Troubleshooting

### Common Issues

**1. Feature Flag Not Working**
```bash
# Check environment variable
echo $ENABLE_NEW_STAGE_1

# Check registry logs
docker-compose logs worker | grep "Stage 1"
```

**2. PICO Integration Missing**
```bash
# Check Stage 2 logs
docker-compose logs worker | grep "PICO"

# Verify Stage 1 output format
# Should contain: pico_elements, search_query, stage_1_complete
```

**3. Quality Gate Failures**
```python
# Check quality criteria
from src.agents.protocol_design.agent import ProtocolDesignAgent
agent = ProtocolDesignAgent(llm_bridge)
criteria = agent.get_quality_criteria()
print(criteria)
```

**4. LLM Bridge Issues**
```bash
# Check AI Router connectivity
curl http://orchestrator:3001/api/ai/router/health

# Check environment variables
echo $AI_ROUTER_URL
echo $PHI_SCAN_ENABLED
```

## Performance Considerations

### Resource Usage
- **CPU**: LangGraph execution is CPU-intensive
- **Memory**: Agent state can be large with long protocols
- **Network**: Multiple LLM calls per execution

### Optimization Tips
- Use `STANDARD` model tier for production (balance cost/quality)
- Set reasonable timeouts (`PROTOCOL_DESIGN_TIMEOUT=300`)
- Limit iterations (`PROTOCOL_MAX_ITERATIONS=5`)
- Enable caching for repeated PICO extractions

## Security & Compliance

### PHI Protection
- All LLM calls route through AI Router for PHI scanning
- Quality gate includes PHI compliance check
- No patient data stored in agent state

### Governance Modes
- **DEMO**: Synthetic data, no PHI allowed
- **LIVE**: Real data, PHI scanning enabled, human review required
- **STANDBY**: Service available but restricted

## Migration Strategy

### From Legacy Stage 1 (Upload)

1. **Before Migration**
   ```bash
   # Backup current Stage 1 configurations
   pg_dump -t stage_configs > stage1_backup.sql
   ```

2. **Feature Flag Deployment**
   ```bash
   # Deploy with new agent disabled
   ENABLE_NEW_STAGE_1=false

   # Test both implementations
   pytest tests/integration/test_stage1_feature_flag.py
   ```

3. **Gradual Rollout**
   ```bash
   # Enable for 10% of users
   # Monitor metrics for 48 hours
   # Increase to 50%, then 100%
   ```

4. **Legacy Deprecation**
   ```bash
   # After 2 weeks stable, remove old stage
   rm services/worker/src/workflow_engine/stages/stage_01_upload.py
   ```

### Data Migration
- No data migration needed (stages are stateless)
- Existing projects continue with their original Stage 1 data
- New projects use new Protocol Design Agent

## Support & Documentation

### Internal Documentation
- `README_STAGE_01_IMPLEMENTATION.md` - Implementation status
- `IMPLEMENTATION_NEXT_STEPS.md` - Development guide
- `STAGE_01_ASSESSMENT.md` - Architecture analysis

### External Documentation
- `docs/stages/01-protocol-design.md` - User guide
- `docs/api/protocol-design-agent.md` - API reference
- `docs/tutorials/pico-framework.md` - PICO tutorial

### Contact Points
- **Development**: See implementation documentation
- **Deployment**: Infrastructure team
- **User Issues**: Product support team

## Checklist

### Pre-Deployment
- [ ] Environment variables configured
- [ ] Feature flag set to `false` initially
- [ ] All tests passing
- [ ] Documentation updated
- [ ] Monitoring configured

### Post-Deployment
- [ ] Health checks passing
- [ ] Metrics baseline established
- [ ] User feedback collected
- [ ] Performance monitoring active
- [ ] Error rates within targets

### Feature Rollout
- [ ] Internal testing complete
- [ ] Beta user feedback positive
- [ ] Gradual rollout successful
- [ ] Legacy stage deprecated
- [ ] Documentation finalized

---

**Status**: Ready for deployment with feature flag approach
**Last Updated**: 2024 (during integration implementation)
**Next Review**: After initial deployment feedback