# ResearchFlow Design System - Execution Plan

## Overview

This document outlines the complete execution plan for implementing the Figma → Replit → Production design system pipeline.

---

## Phase 1: Design Tokens Infrastructure (ROS-88)

### 1.1 Package Structure
```
packages/design-tokens/
├── package.json              # NPM package configuration
├── tokens/
│   ├── base/
│   │   ├── colors.json       # Color primitives
│   │   ├── spacing.json      # Spacing scale
│   │   ├── typography.json   # Font sizes, weights, line heights
│   │   ├── radii.json        # Border radius values
│   │   └── shadows.json      # Box shadow definitions
│   ├── semantic/
│   │   ├── colors.json       # Semantic color mappings
│   │   └── components.json   # Component-level tokens
│   └── index.json            # Token aggregation
├── style-dictionary.config.js # Build configuration
├── dist/
│   ├── tokens.css            # CSS custom properties (generated)
│   └── tokens.ts             # TypeScript constants (generated)
└── README.md
```

### 1.2 Token Categories

**Base Tokens:**
- Colors: Primary, secondary, gray scale, status colors (red, yellow, green, blue)
- Spacing: 0, 1, 2, 3, 4, 5, 6, 8, 10, 12, 16, 20, 24, 32, 40, 48, 64 (in 4px increments)
- Typography: xs, sm, base, lg, xl, 2xl, 3xl, 4xl
- Radii: none, sm, md, lg, xl, full
- Shadows: none, sm, md, lg, xl

**Semantic Tokens:**
- Background: surface, surface-alt, overlay, muted
- Text: primary, secondary, muted, inverse
- Border: default, muted, strong, focus
- Status: info, success, warning, error
- Interactive: primary, hover, active, disabled

**Component Tokens:**
- Button: padding, height, border-radius per size (sm, md, lg)
- Input: padding, height, border-radius, focus-ring
- Badge: padding, font-size per variant
- Modal: border-radius, shadow, backdrop-opacity

---

## Phase 2: UI Component Library (ROS-89)

### 2.1 Package Structure
```
packages/ui/
├── package.json
├── tsconfig.json
├── src/
│   ├── primitives/
│   │   ├── Button/
│   │   │   ├── Button.tsx
│   │   │   ├── Button.stories.tsx
│   │   │   └── index.ts
│   │   ├── Input/
│   │   ├── Badge/
│   │   ├── Modal/
│   │   ├── Card/
│   │   ├── Alert/
│   │   ├── Table/
│   │   └── Tabs/
│   ├── domain/
│   │   ├── AuditLogViewer/
│   │   ├── ArtifactBrowserPanel/
│   │   └── WorkflowGraph/
│   ├── governance/
│   │   ├── PHIGateBanner/
│   │   ├── TransparencyPanel/
│   │   ├── ModelTierBadge/
│   │   └── ApprovalStatusIndicator/
│   ├── hooks/
│   │   ├── useGovernanceMode.ts
│   │   └── useAuditLog.ts
│   ├── utils/
│   │   └── cn.ts              # className utility (clsx + twMerge)
│   └── index.ts
└── README.md
```

### 2.2 Component Requirements

Each component must:
1. Use design tokens via CSS variables
2. Support all UI states: default, loading, empty, error, success, disabled
3. Include Figma reference comment
4. Be fully accessible (ARIA, keyboard navigation)
5. Have TypeScript props interface
6. Include Storybook stories

---

## Phase 3: Documentation (ROS-93)

### 3.1 Files to Create
```
docs/design/
├── design-system.md          # Token naming, usage guide
├── component-inventory.md    # Figma ↔ Code mapping table
├── prototype-workflow.md     # Replit workflow guide
├── accessibility-checklist.md # A11y requirements
└── contributing-design.md    # Design contribution guide
```

### 3.2 PR Template Update
```
.github/
└── PULL_REQUEST_TEMPLATE.md  # Add Figma + Replit link fields
```

---

## Phase 4: Replit/MSW Setup (ROS-91)

### 4.1 MSW Handlers Structure
```
services/web/src/mocks/
├── handlers/
│   ├── workflow.ts           # Workflow states
│   ├── manuscript.ts         # Manuscript editor states
│   ├── governance.ts         # PHI gate, approvals
│   ├── audit.ts              # Audit log mock data
│   └── library.ts            # Library empty/populated
├── data/
│   ├── workflows.json        # Mock workflow data
│   ├── manuscripts.json      # Mock manuscript data
│   └── auditLogs.json        # Mock audit entries
├── handlers.ts               # Handler aggregation
├── browser.ts                # Browser worker setup
└── server.ts                 # Node worker setup (for tests)
```

---

## Phase 5: Prototype Structure

### 5.1 Prototype Folders
```
prototypes/
├── workflow-graph/
│   ├── package.json
│   ├── src/
│   └── README.md
├── governance-panels/
│   ├── package.json
│   ├── src/
│   └── README.md
├── pdf-annotation/
│   └── README.md
└── manuscript-comments/
    └── README.md
```

---

## Execution Order

1. **packages/design-tokens/** (Foundation)
   - Create package.json
   - Create token JSON files
   - Create Style Dictionary config
   - Generate CSS/TS outputs

2. **packages/ui/** (Components)
   - Create package.json with design-tokens dependency
   - Create utility functions (cn.ts)
   - Create primitive components
   - Create governance components

3. **docs/design/** (Documentation)
   - Create all markdown files
   - Update PR template

4. **services/web/src/mocks/** (MSW)
   - Create mock handlers
   - Create mock data files
   - Setup browser/server workers

5. **prototypes/** (Scaffolding)
   - Create folder structure
   - Add README files

---

## Deliverables

After execution, the following will be created:
- [ ] 15+ token JSON files
- [ ] Style Dictionary configuration
- [ ] Generated tokens.css and tokens.ts
- [ ] 8+ UI components with TypeScript
- [ ] 4 governance-specific components
- [ ] 5 documentation markdown files
- [ ] Updated PR template
- [ ] MSW mock handlers for 5 domains
- [ ] Prototype folder scaffolding

---

## Integration Points

### Figma MCP
Components include figma reference comments:
```typescript
// figma: fileKey=ABC123 nodeId=1:234
```

### Replit
MSW handlers allow frontend-only development:
- Import services/web from GitHub
- Run with `VITE_MOCK_API=true`
- All API calls intercepted by MSW

### Linear/Notion
Work items linked to Linear issues and tracked in Product Work Items database.

---

## Next Steps After Execution

1. **Figma Setup**: Create/organize Figma file with matching component names
2. **Storybook**: Add Storybook configuration to packages/ui
3. **CI Integration**: Add token build step to GitHub Actions
4. **Replit Project**: Create Replit project and import repo
