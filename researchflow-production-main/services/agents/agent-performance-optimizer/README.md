# Performance Optimizer Agent

**Imported:** 2026-02-08  
**Source:** LangSmith Custom Agent  
**Task Type:** `PERFORMANCE_OPTIMIZATION`  
**Stage:** 0 (cross-cutting monitoring)

## Overview

The Performance Optimizer Agent monitors and optimizes LLM/agent workflow metrics to reduce API costs by 20-30% and improve performance at enterprise scale. It analyzes latency, token costs, and error rates, providing actionable recommendations backed by research and cost benchmarking.

## Architecture

### Main Agent
- Performance metrics collection & analysis
- Bottleneck identification (cost, latency, errors)
- Alert threshold monitoring
- Historical trend tracking
- Automated report generation

### Sub-Workers

#### Optimization_Researcher
Researches LLM optimization strategies, best practices, latency reduction techniques, prompt efficiency, and caching approaches.

**Input:** Performance issue description  
**Output:** Structured report with findings, recommended strategies, and estimated impact

#### Cost_Benchmarker
Analyzes AI provider pricing and recommends cost-optimal model selections.

**Input:** Current models in use, token volumes, costs  
**Output:** Pricing comparison table, alternative model recommendations, projected savings

## Alert Thresholds

### Critical
- Error rate > 10%
- Cost spike > 50% day-over-day
- P99 latency > 30 seconds

### Warning
- Error rate > 5%
- Cost increase > 20% week-over-week
- Avg latency increase > 30% week-over-week

## Usage

### Scheduled Analysis (Cron)
1. Reads latest metrics from configured Google Sheets
2. Compares against previous periods
3. Checks alert thresholds
4. Identifies top 3-5 performance issues
5. Delegates research to sub-workers
6. Generates and archives report to Google Docs
7. Updates tracking spreadsheet

### On-Demand Analysis
Triggered manually with:
- Pasted metrics data
- Google Sheets reference
- Targeted question (e.g., "Why is my latency so high?")

## Integration

- **Task Type:** `PERFORMANCE_OPTIMIZATION`
- **Router:** Registered in `services/orchestrator/src/routes/ai-router.ts`
- **Contract:** Added to `services/orchestrator/src/services/task-contract.ts`
- **Inventory:** Listed in `AGENT_INVENTORY.md` under Governance & Policy Agents

### Request Example

```json
{
  "request_id": "perf-001",
  "task_type": "PERFORMANCE_OPTIMIZATION",
  "mode": "DEMO",
  "inputs": {
    "metrics_spreadsheet_id": "abc123...",
    "analysis_focus": "latency",
    "time_period": "last_7_days"
  }
}
```

### Optional Inputs
- `metrics_spreadsheet_id`: Google Sheets ID containing metrics
- `metrics_data`: Direct metrics data (if not using spreadsheet)
- `analysis_focus`: Specific area to analyze (latency, cost, errors)
- `time_period`: Time range for analysis (last_7_days, last_30_days, custom)

## Tools

- **Google Sheets:** Read/write/append/create spreadsheets
- **Google Docs:** Create/append/read documents  
- **Web Search:** Research current pricing and best practices

## Environment Variables

- `LANGSMITH_API_KEY` - LangSmith API access (optional)
- `GOOGLE_SHEETS_API_KEY` - For metrics reading/writing (optional)
- `GOOGLE_DOCS_API_KEY` - For report generation (optional)

## Files

```
agent-performance-optimizer/
├── AGENTS.md              # Main agent prompt and instructions
├── config.json            # Agent metadata and configuration
├── tools.json             # Tool dependencies
├── README.md              # This file
└── subagents/
    ├── Cost_Benchmarker/
    │   ├── AGENTS.md      # Cost benchmarker worker prompt
    │   └── tools.json     # Cost benchmarker tools
    └── Optimization_Researcher/
        ├── AGENTS.md      # Optimization researcher prompt
        └── tools.json     # Optimization researcher tools
```

## Status

✅ **IMPORTED** (2026-02-08)  
- Configuration files ready
- Task type registered in router
- Listed in AGENT_INVENTORY.md
- Awaiting deployment integration (proxy service optional)

## Next Steps

1. **Optional:** Create proxy service if local integration needed
2. **Optional:** Add to Docker Compose for containerized deployment
3. **Configure:** Set up Google Sheets metrics tracking
4. **Test:** Validate with sample metrics data
5. **Schedule:** Configure cron trigger for automated monitoring

## References

- **AGENTS.md:** Full agent prompt and operational instructions
- **AGENT_INVENTORY.md:** Fleet-wide agent documentation
- **ai-router.ts:** Task type registration
- **task-contract.ts:** Input validation rules
