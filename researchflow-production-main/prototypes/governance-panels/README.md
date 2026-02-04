# Governance Panels Prototype

## Purpose

Prototype governance UI surfaces for clinical transparency:
- PHI Gate interactions
- AI Transparency panel
- Audit Log viewer
- DEMO vs LIVE mode switching
- Approval workflow states

## Status

🔲 **Not Started**

## Components to Prototype

### 1. PHI Gate Banner
- Blocked state with "Request Access" flow
- Pending approval state
- Approved state with steward info
- DEMO mode state (always blocked)

### 2. Transparency Panel
- Collapsible by default
- Model tier display
- Cost/latency metrics
- Data summary (PHI-safe)
- Redaction list
- Audit log link

### 3. Audit Log Viewer
- Filterable table
- Pagination
- Export functionality
- Role-based filtering

### 4. DEMO/LIVE Toggle
- Clear visual distinction
- Confirmation modal for switching
- State persistence indicator

## Mock Data States

Test with query params:
- `?_status=blocked` - PHI blocked
- `?_status=requires-approval` - Pending approval
- `?_status=approved` - Access granted
- `?_status=demo-mode` - Demo mode active
- `?_tier=NANO|MINI|FRONTIER` - Force model tier

## Graduation Criteria

- [ ] All PHI gate states prototyped
- [ ] Transparency panel layout finalized
- [ ] Audit log filtering works
- [ ] Accessibility verified
- [ ] Components extracted to packages/ui/governance

## Notes

**Important**: Never use real PHI in mock data!

<!-- Add findings and learnings here -->
