# ResearchFlow Design System - Execution Plan v2

## Current Status

### ✅ COMPLETED
| Item | Status | Notes |
|------|--------|-------|
| `packages/design-tokens` | ✅ Complete | Tokens built, CSS/TS outputs generated |
| Button component | ✅ Complete | All variants/sizes |
| Badge component | ✅ Complete | All variants/sizes |
| Alert component | ✅ Complete | All variants, dismissible |
| PHIGateBanner | ✅ Complete | All PHI states |
| ModelTierBadge | ✅ Complete | NANO/MINI/FRONTIER |
| TransparencyPanel | ✅ Complete | Collapsible, full data |
| design-system.md | ✅ Complete | Token architecture docs |
| component-inventory.md | ✅ Complete | Mapping table |
| prototype-workflow.md | ✅ Complete | Replit guide |
| accessibility-checklist.md | ✅ Complete | WCAG AA checklist |
| PR Template | ✅ Complete | Design traceability fields |
| governance handlers | ✅ Complete | PHI, approvals, model tier |
| workflow handlers | ✅ Complete | CRUD, state transitions |

### 🔲 REMAINING WORK
| Item | Priority | Effort |
|------|----------|--------|
| Input component | High | 15 min |
| Card component | High | 10 min |
| Modal component | High | 20 min |
| Table component | Medium | 25 min |
| Tabs component | Medium | 20 min |
| ApprovalStatusIndicator | High | 15 min |
| AuditLogViewer (domain) | Medium | 30 min |
| audit MSW handlers | Medium | 15 min |
| MSW setup (browser.ts, server.ts) | High | 10 min |
| contributing-design.md | Low | 10 min |
| Prototype folder scaffold | Low | 5 min |
| UI package build verification | High | 5 min |

---

## Execution Sequence

### Phase 1: Complete Primitive Components (45 min)
1. **Input** - Text input with all states, validation
2. **Card** - Container component with header/body/footer
3. **Modal** - Dialog with portal, focus trap, backdrop
4. **Table** - Data table with sorting, pagination placeholders
5. **Tabs** - Tab list with panels

### Phase 2: Complete Governance Components (15 min)
6. **ApprovalStatusIndicator** - Pending/approved/denied states

### Phase 3: Domain Components (30 min)
7. **AuditLogViewer** - Filterable log list with pagination

### Phase 4: MSW Infrastructure (25 min)
8. **audit handlers** - Log entries, filtering, export
9. **browser.ts** - MSW browser setup
10. **server.ts** - MSW node setup for tests
11. **handlers.ts** - Handler aggregation

### Phase 5: Documentation & Scaffolding (15 min)
12. **contributing-design.md** - Contribution guidelines
13. **prototypes/** folder structure
14. Update component-inventory.md with new components

### Phase 6: Build & Verify (10 min)
15. Install UI package dependencies
16. Verify TypeScript compilation
17. Generate final deliverables summary

---

## Deliverables After Execution

```
packages/
├── design-tokens/           # ✅ COMPLETE
│   ├── tokens/base/*.json   # Color, spacing, typography, radii, shadows
│   ├── tokens/semantic/*.json # Colors, components
│   ├── dist/tokens.css      # Generated CSS variables
│   ├── dist/tokens.ts       # Generated TypeScript
│   └── dist/tokens.json     # Generated flat JSON
│
└── ui/                      # 🔲 IN PROGRESS
    ├── src/primitives/
    │   ├── Button/          # ✅ COMPLETE
    │   ├── Badge/           # ✅ COMPLETE
    │   ├── Alert/           # ✅ COMPLETE
    │   ├── Input/           # 🔲 TODO
    │   ├── Card/            # 🔲 TODO
    │   ├── Modal/           # 🔲 TODO
    │   ├── Table/           # 🔲 TODO
    │   └── Tabs/            # 🔲 TODO
    ├── src/governance/
    │   ├── PHIGateBanner/   # ✅ COMPLETE
    │   ├── ModelTierBadge/  # ✅ COMPLETE
    │   ├── TransparencyPanel/ # ✅ COMPLETE
    │   └── ApprovalStatusIndicator/ # 🔲 TODO
    └── src/domain/
        └── AuditLogViewer/  # 🔲 TODO

services/web/src/mocks/
├── handlers/
│   ├── governance.ts        # ✅ COMPLETE
│   ├── workflow.ts          # ✅ COMPLETE
│   └── audit.ts             # 🔲 TODO
├── browser.ts               # 🔲 TODO
├── server.ts                # 🔲 TODO
└── handlers.ts              # 🔲 TODO

docs/design/
├── design-system.md         # ✅ COMPLETE
├── component-inventory.md   # ✅ COMPLETE (update needed)
├── prototype-workflow.md    # ✅ COMPLETE
├── accessibility-checklist.md # ✅ COMPLETE
└── contributing-design.md   # 🔲 TODO

prototypes/                  # 🔲 TODO (scaffold only)
├── workflow-graph/
├── governance-panels/
├── pdf-annotation/
└── manuscript-comments/
```

---

## Success Criteria

- [ ] All primitive components created with TypeScript interfaces
- [ ] All components use design tokens (no hardcoded values)
- [ ] MSW setup working for frontend-only development
- [ ] UI package compiles without TypeScript errors
- [ ] Documentation complete and cross-referenced
- [ ] Prototype folder structure ready for use

---

## Executing Now...
