# Contributing to ResearchFlow Design System

## Overview

This guide covers how to contribute to the ResearchFlow design system, including adding tokens, creating components, and maintaining documentation.

## Getting Started

### Prerequisites

- Node.js 18+
- pnpm (recommended) or npm
- Access to Figma file (for designers)
- Familiarity with React and TypeScript

### Setup

```bash
# Clone repository
git clone https://github.com/ry86pkqf74-rgb/researchflow-production.git
cd researchflow-production

# Install dependencies
pnpm install

# Build design tokens
cd packages/design-tokens
pnpm build

# Start Storybook (when available)
cd ../ui
pnpm storybook
```

---

## Adding Design Tokens

### When to Add Tokens

Add new tokens when:
- Introducing a new color that will be used in multiple places
- Creating consistent spacing for a new component type
- Defining a new semantic meaning (e.g., new status type)

### How to Add Tokens

1. **Identify the token type**:
   - Base token: Raw value (color hex, pixel value)
   - Semantic token: Meaningful name referencing base tokens
   - Component token: Component-specific configuration

2. **Add to appropriate JSON file**:

   ```json
   // tokens/semantic/colors.json
   {
     "semantic": {
       "status": {
         "pending": {
           "bg": { "value": "{color.base.amber.50}" },
           "text": { "value": "{color.base.amber.700}" }
         }
       }
     }
   }
   ```

3. **Build and verify**:

   ```bash
   cd packages/design-tokens
   pnpm build
   ```

4. **Update documentation**:
   - Add to `docs/design/design-system.md` if it's a new category
   - Update relevant component documentation

### Token Naming Conventions

| Type | Pattern | Example |
|------|---------|---------|
| Base color | `color.base.{color}.{shade}` | `color.base.gray.500` |
| Semantic bg | `semantic.bg.{purpose}` | `semantic.bg.surface` |
| Semantic text | `semantic.text.{purpose}` | `semantic.text.primary` |
| Component | `component.{name}.{size}.{property}` | `component.button.md.height` |

---

## Creating Components

### Component Checklist

Before creating a new component:

- [ ] Check if similar component exists
- [ ] Review Figma design (if available)
- [ ] Identify all states (loading, error, empty, disabled)
- [ ] Plan accessibility requirements

### Component Structure

```
packages/ui/src/primitives/NewComponent/
├── NewComponent.tsx     # Main component
├── NewComponent.test.tsx # Tests (optional for now)
├── index.ts             # Exports
└── README.md            # Component docs (optional)
```

### Component Template

```tsx
import * as React from 'react';
import { cn } from '../../utils/cn';

// figma: fileKey=PENDING nodeId=PENDING
// Component contract: RF/ComponentName

export interface NewComponentProps extends React.HTMLAttributes<HTMLDivElement> {
  /** Description of prop */
  variant?: 'default' | 'alternate';
  /** Loading state */
  isLoading?: boolean;
}

export const NewComponent = React.forwardRef<HTMLDivElement, NewComponentProps>(
  ({ className, variant = 'default', isLoading = false, children, ...props }, ref) => {
    return (
      <div
        ref={ref}
        className={cn(
          // Base styles using design tokens
          'rounded-[var(--radius-md)]',
          'bg-[var(--semantic-bg-surface)]',
          // Variant styles
          variant === 'alternate' && 'bg-[var(--semantic-bg-surface-alt)]',
          // Loading state
          isLoading && 'animate-pulse',
          className
        )}
        {...props}
      >
        {children}
      </div>
    );
  }
);

NewComponent.displayName = 'NewComponent';

export default NewComponent;
```

### Required Patterns

1. **Use design tokens**: No hardcoded colors, spacing, or typography
2. **Forward ref**: All components should use `forwardRef`
3. **Figma reference**: Include `// figma:` comment
4. **TypeScript**: Full type definitions for props
5. **Accessibility**: ARIA attributes, keyboard support

### Export from Index

Update `packages/ui/src/primitives/index.ts`:

```tsx
export { NewComponent, type NewComponentProps } from './NewComponent';
```

---

## Governance Components

Governance components have additional requirements:

1. **PHI safety**: Never display or log actual PHI
2. **Mode awareness**: Respect DEMO/LIVE mode
3. **Audit integration**: Log significant actions
4. **Clear status**: Make governance state obvious

### Governance Component Locations

- `packages/ui/src/governance/` - Governance-specific components
- `packages/ui/src/hooks/` - Governance hooks

---

## Documentation

### What to Document

- New token categories → `docs/design/design-system.md`
- New components → `docs/design/component-inventory.md`
- Workflow changes → `docs/design/prototype-workflow.md`
- A11y requirements → `docs/design/accessibility-checklist.md`

### Documentation Style

- Use clear, concise language
- Include code examples
- Add visual examples where helpful
- Keep tables updated

---

## Pull Request Process

### Before Submitting

1. Run token build: `cd packages/design-tokens && pnpm build`
2. TypeCheck components: `cd packages/ui && pnpm typecheck`
3. Update component inventory if adding components
4. Add Figma link if design exists

### PR Template Requirements

Fill out all sections in the PR template:
- Design traceability (Figma links)
- UI states covered
- Governance impact
- Accessibility verification

### Review Process

1. Code review by team member
2. Design review (if UI changes)
3. Accessibility spot-check
4. Merge to main

---

## Best Practices

### DO

- ✅ Use semantic tokens over base tokens
- ✅ Test all component states
- ✅ Include loading and error states
- ✅ Support keyboard navigation
- ✅ Write meaningful commit messages
- ✅ Update documentation

### DON'T

- ❌ Hardcode colors or spacing
- ❌ Skip accessibility attributes
- ❌ Forget to export new components
- ❌ Leave Figma references as "PENDING" long-term
- ❌ Create one-off styles that should be tokens

---

## Getting Help

- **Design questions**: Check Figma file or ask in #design channel
- **Technical questions**: Ask in #engineering channel
- **Token questions**: Review design-system.md first
- **Accessibility questions**: Consult accessibility-checklist.md

---

## Resources

- [Design System Documentation](./design-system.md)
- [Component Inventory](./component-inventory.md)
- [Accessibility Checklist](./accessibility-checklist.md)
- [Prototype Workflow](./prototype-workflow.md)
