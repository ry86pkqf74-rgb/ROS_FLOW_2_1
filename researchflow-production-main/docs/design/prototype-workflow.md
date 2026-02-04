# Prototype Workflow Guide

## Overview

This guide describes when and how to use Replit for UI prototyping vs implementing directly in the codebase.

## Decision Matrix

### When to Use Replit Prototypes

| Situation | Use Replit? | Reason |
|-----------|-------------|--------|
| New UX pattern exploration | ✅ Yes | Fast iteration, easy sharing |
| Stakeholder signoff needed | ✅ Yes | Shareable preview URLs |
| Complex state transitions | ✅ Yes | Easier to test edge cases |
| Design validation | ✅ Yes | Quick visual feedback |
| Simple component addition | ❌ No | Direct implementation faster |
| Bug fix in existing UI | ❌ No | Fix in place |
| Performance-critical feature | ❌ No | Need real build environment |

### Prototype vs Production

| Aspect | Prototype (Replit) | Production (services/web) |
|--------|-------------------|---------------------------|
| Data | MSW mocks | Real API |
| State | Local/mocked | Full Redux/React Query |
| Auth | Bypassed | Real RBAC |
| PHI | Always safe | Governance-controlled |
| Styling | Design tokens | Design tokens |
| Deployment | Replit Preview | Docker/K8s |

## Setting Up Replit

### 1. Import from GitHub

```bash
# In Replit, use "Import from GitHub"
# URL: https://github.com/ry86pkqf74-rgb/researchflow-production
# Path: services/web
```

### 2. Configure for Frontend-Only

Create/update `.replit`:

```toml
run = "npm run dev"
entrypoint = "src/main.tsx"

[env]
VITE_MOCK_API = "true"
VITE_DEMO_MODE = "true"

[nix]
channel = "stable-23_11"

[deployment]
run = ["npm", "run", "preview"]
```

### 3. Enable MSW

The mock service worker intercepts API calls when `VITE_MOCK_API=true`:

```typescript
// src/main.tsx
if (import.meta.env.VITE_MOCK_API === 'true') {
  const { worker } = await import('./mocks/browser');
  await worker.start({ onUnhandledRequest: 'bypass' });
}
```

## MSW Mock Patterns

### Basic Handler Structure

```typescript
// src/mocks/handlers/workflow.ts
import { http, HttpResponse } from 'msw';

export const workflowHandlers = [
  // List workflows
  http.get('/api/workflows', () => {
    return HttpResponse.json({
      workflows: mockWorkflows,
      total: mockWorkflows.length,
    });
  }),

  // Get single workflow with different states
  http.get('/api/workflows/:id', ({ params }) => {
    const workflow = mockWorkflows.find(w => w.id === params.id);
    if (!workflow) {
      return new HttpResponse(null, { status: 404 });
    }
    return HttpResponse.json(workflow);
  }),
];
```

### Simulating States

```typescript
// Toggle states via query params for easy testing
http.get('/api/workflows/:id', ({ request, params }) => {
  const url = new URL(request.url);
  const forceState = url.searchParams.get('_state');
  
  const workflow = { ...mockWorkflows[0], id: params.id };
  
  if (forceState) {
    workflow.status = forceState; // 'running' | 'completed' | 'failed' | 'paused'
  }
  
  return HttpResponse.json(workflow);
});
```

### Error State Testing

```typescript
// Force errors with query param
http.get('/api/workflows', ({ request }) => {
  const url = new URL(request.url);
  
  if (url.searchParams.get('_error') === 'true') {
    return new HttpResponse(
      JSON.stringify({ error: 'Internal server error' }),
      { status: 500 }
    );
  }
  
  // Normal response
  return HttpResponse.json({ workflows: mockWorkflows });
});
```

## Prototype Folder Structure

```
prototypes/
├── workflow-graph/          # Workflow visualization spike
│   ├── package.json
│   ├── src/
│   │   ├── App.tsx
│   │   └── components/
│   └── README.md
├── governance-panels/       # PHI/Audit/Transparency UI
│   ├── package.json
│   ├── src/
│   └── README.md
├── pdf-annotation/         # PDF viewer interactions
│   └── README.md
└── manuscript-comments/    # Collaboration UI
    └── README.md
```

Each prototype should have:
- `README.md` with purpose, key findings, and "graduate to production" notes
- Minimal dependencies (share design tokens, but self-contained otherwise)
- Screenshots or recordings of key states

## Sharing Prototypes

### Replit Preview URLs

1. Run the project in Replit
2. Click "Open in new tab" to get preview URL
3. Share URL format: `https://<project>.<username>.repl.co`

### Adding to Notion/Linear

When creating a work item, include:
- **Replit Prototype**: Preview URL
- **Key States Tested**: List of states (loading, error, empty, etc.)
- **Screenshots**: Embedded or linked

## Graduating to Production

When a prototype is validated:

1. **Document learnings**: Update prototype README with findings
2. **Create Linear issues**: Break down into implementation tasks
3. **Copy relevant code**: Extract components to `packages/ui`
4. **Add MSW handlers**: Move to `services/web/src/mocks/`
5. **Archive prototype**: Keep for reference, mark as "graduated"

### Graduation Checklist

- [ ] All states prototyped and validated
- [ ] Stakeholder signoff received
- [ ] Components moved to packages/ui
- [ ] Design tokens used (no hardcoded values)
- [ ] Accessibility verified
- [ ] MSW handlers complete
- [ ] Linear issues created for remaining work
- [ ] Prototype README updated with "graduated" status

## Best Practices

### DO

- Use design tokens from `@researchflow/design-tokens`
- Test all UI states (loading, empty, error, success, permission denied)
- Share preview URLs early for feedback
- Document edge cases discovered during prototyping
- Keep prototypes focused on one feature/flow

### DON'T

- Use Replit for production deployments
- Include real PHI in mock data
- Over-engineer prototypes (they're throwaway)
- Skip the graduation process
- Forget to update Notion/Linear with prototype links
