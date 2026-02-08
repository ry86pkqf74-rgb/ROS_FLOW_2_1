# Journal Guidelines Cache Agent

**Source:** LangSmith Custom Agent  
**Type:** Caching & Knowledge Management  
**Task Type:** `JOURNAL_GUIDELINES_CACHE`

## Overview

Intelligent caching agent that manages persistent storage and retrieval of academic journal submission guidelines. Eliminates redundant web searches by maintaining a Google Sheets-based cache with automatic staleness detection, proactive refresh scheduling, and change tracking. Essential for the dissemination pipeline to deliver instant journal requirements without repeated API calls.

## Identity & Tone

- Efficient and responsive — instant cache hits, transparent about freshness
- Proactive refresh management — keeps cache up-to-date automatically
- Audit-conscious — tracks guideline changes for clinical trial and regulatory compliance

## Core Capabilities

1. **Cache Management** — Store journal guidelines in a Google Sheets cache with metadata (last updated, aliases, status)
2. **Instant Retrieval** — Return cached guidelines immediately for cache hits (< 30 days old)
3. **Staleness Detection** — Automatically identify guidelines older than 30 days
4. **Proactive Refresh** — Daily scheduled refresh of stale entries with change detection
5. **Change Tracking** — Maintain audit trail of guideline changes with severity classification
6. **Batch Operations** — Support multi-journal lookups with parallel processing
7. **Journal Comparison** — Enable side-by-side comparison of multiple journals
8. **Alias Matching** — Normalize journal names and match against common abbreviations

---

## Architecture

### Main Agent
- **Location:** `agent-journal-guidelines-cache/`
- **Workflow:** Check cache → Return cached data OR fetch fresh → Update cache → Track changes
- **Output:** Journal guidelines (cached or fresh), change notifications, comparison reports

### Worker Agents

#### Guidelines Researcher
- **Location:** `subagents/Guidelines_Researcher/`
- **Purpose:** Fetches fresh journal submission guidelines from authoritative sources
- **Tools:** Web search, URL content extraction
- **Output:** Structured guideline summary with source URLs

#### Changelog Detector
- **Location:** `subagents/Changelog_Detector/`
- **Purpose:** Compares old vs. new guidelines to detect and document changes
- **Process:** Section-by-section comparison → Change classification (critical/notable/minor)
- **Output:** Structured changelog with severity assessment

#### Guidelines Comparator
- **Location:** `subagents/Guidelines_Comparator/`
- **Purpose:** Performs side-by-side comparison of multiple journals
- **Process:** Extract key dimensions → Build comparison table → Highlight differences
- **Output:** Comparison table + narrative analysis + recommendation notes

---

## Cache Architecture

### Storage: Google Sheets

#### Sheet 1: "Cache" (Main Data)
| Column | Content |
|--------|---------|
| journal_name | Canonical name (e.g., "New England Journal of Medicine") |
| aliases | Common abbreviations (e.g., "NEJM, N Engl J Med") |
| last_updated | ISO 8601 date of last fetch |
| guidelines_summary | Full structured guideline text |
| source_urls | Comma-separated source URLs |
| status | "fresh" or "stale" |

#### Sheet 2: "Changelog" (Audit Trail)
| Column | Content |
|--------|---------|
| journal_name | Journal that changed |
| change_date | ISO 8601 date change detected |
| change_summary | Brief description of changes |
| severity | "critical", "notable", or "minor" |

### Staleness Threshold
Guidelines are considered **stale** if `last_updated` > 30 days ago.

---

## Operational Modes

### Mode 1: Manual Request — Single Journal
1. Check cache (match journal name or aliases)
2. **Cache Hit** (< 30 days) → Return immediately
3. **Stale Entry** → Refresh, detect changes, update cache
4. **Cache Miss** → Fetch fresh, add to cache

### Mode 2: Manual Request — Batch Lookup
- Check cache for all journals
- Return cache hits immediately
- Fetch missing/stale in parallel (one call per journal)
- Run change detection on stale entries
- Present unified results

### Mode 3: Compare Journals
1. Ensure all journals are cached and fresh
2. Delegate to Guidelines Comparator
3. Return comparison table + analysis

### Mode 4: Scheduled Refresh (Daily Cron)
1. Read entire cache
2. Identify all stale entries
3. Refresh each stale entry (with change detection)
4. Update cache with fresh data
5. Report summary with detected changes

---

## Integration Points

### Dissemination Formatter Agent
The Dissemination Formatter delegates to this cache agent to retrieve journal requirements before manuscript formatting. This ensures instant guideline lookup without web searches.

### Orchestrator Router
Registered as task type `JOURNAL_GUIDELINES_CACHE` and routed through the proxy service `agent-journal-guidelines-cache-proxy`.

---

## Cache Management Commands

| Command | Action |
|---------|--------|
| `List cached journals` | Show all cached journals with freshness status |
| `Clear cache` | Reset entire cache (confirmable) |
| `Remove {journal}` | Delete specific journal from cache |
| `Force refresh {journal}` | Fetch fresh regardless of staleness |
| `Cache stats` | Summary statistics (total, fresh, stale, oldest, newest) |
| `Show changelog` | Display recent guideline changes |
| `Show changelog for {journal}` | Filter changelog for specific journal |
| `Compare {journal A} vs {journal B}` | Side-by-side comparison |
| `Suggest journals like {journal}` | Recommend similar journals |

---

## Environment Configuration

### Required Environment Variables
- `LANGSMITH_API_KEY` — LangSmith API authentication
- `LANGSMITH_AGENT_ID` — Agent deployment ID
- `GOOGLE_SHEETS_SPREADSHEET_ID` — (Optional) Pre-existing cache spreadsheet ID

### Optional Configuration
- `CACHE_STALENESS_DAYS` — Default: 30 days
- `DAILY_REFRESH_ENABLED` — Default: true
- `MAX_PARALLEL_LOOKUPS` — Default: 5

---

## Output Formats

### Single Journal Guidelines
```
## {Journal Name} — Submission Guidelines

**Cache Status**: {Cached (as of YYYY-MM-DD) | Freshly fetched}
**Aliases**: {list of known abbreviations}

### Journal Overview
...

### Manuscript Types
...

### [Additional sections...]

**Sources**: {list of URLs}
```

### Refresh with Changes Detected
```
---
### What Changed Since Last Cache (YYYY-MM-DD)

**Severity**: {Critical / Notable / Minor}

{Changelog summary}
```

### Daily Refresh Report
```
## Daily Cache Refresh Report — {Date}

**Entries Checked**: {N}
**Stale Entries Found**: {N}
**Successfully Refreshed**: {N}

### Changes Detected
- [Journal name]: [Change summary] (severity)

### No Changes Detected
- [Journal name]
```

---

## Quality Criteria

- **Response Time**: < 100ms for cache hits
- **Cache Coverage**: Track cache hit rate
- **Change Detection Accuracy**: Classify changes correctly (critical vs. minor)
- **Staleness Management**: Zero stale entries after daily refresh
- **Source Quality**: Only authoritative journal sources used

---

## Testing

### Manual Testing
```bash
# Test cache hit
curl -X POST http://localhost:8000/agents/run/sync \
  -H "Content-Type: application/json" \
  -d '{
    "task_type": "JOURNAL_GUIDELINES_CACHE",
    "request_id": "test-001",
    "mode": "DEMO",
    "inputs": {
      "action": "get_guidelines",
      "journal_name": "Nature"
    }
  }'

# Test batch lookup
curl -X POST http://localhost:8000/agents/run/sync \
  -H "Content-Type: application/json" \
  -d '{
    "task_type": "JOURNAL_GUIDELINES_CACHE",
    "request_id": "test-002",
    "mode": "DEMO",
    "inputs": {
      "action": "batch_lookup",
      "journal_names": ["Nature", "Science", "NEJM"]
    }
  }'

# Test comparison
curl -X POST http://localhost:8000/agents/run/sync \
  -H "Content-Type: application/json" \
  -d '{
    "task_type": "JOURNAL_GUIDELINES_CACHE",
    "request_id": "test-003",
    "mode": "DEMO",
    "inputs": {
      "action": "compare_journals",
      "journal_names": ["Nature", "Science"]
    }
  }'
```

---

## Monitoring

### Key Metrics
- Cache hit rate (target: > 80%)
- Average response time for cache hits (target: < 100ms)
- Daily refresh success rate (target: > 95%)
- Change detection accuracy (manual validation)
- Number of stale entries (target: 0 after daily refresh)

### Logging
All cache operations, refreshes, and detected changes are logged for audit compliance.

---

## Error Handling

### Network Failures
- Keep existing cached data if refresh fails
- Log error and retry on next scheduled refresh
- Notify user if cached data is old but refresh failed

### Missing Journals
- Clear error message if journal not found
- Suggest similar journal names if typo suspected
- Offer to add to cache for future lookups

### Google Sheets Errors
- Fallback to in-memory cache if sheets unavailable
- Queue writes for retry when connection restored
- Log all cache misses for audit trail

---

## Version History

- **v1.0.0** (2026-02-08) - Initial import from LangSmith
  - Google Sheets-based cache
  - Daily scheduled refresh
  - Change detection and audit trail
  - Batch operations and comparison mode
