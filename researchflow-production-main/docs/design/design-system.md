# ResearchFlow Design System

## Overview

The ResearchFlow Design System provides a consistent, accessible, and governance-aware UI foundation for clinical research workflows.

## Token Architecture

### Three-Tier Structure

```
┌─────────────────────────────────────────────────────────────┐
│ Component Tokens (button.md.padding, input.height, etc.)    │
├─────────────────────────────────────────────────────────────┤
│ Semantic Tokens (bg.surface, text.primary, status.error)    │
├─────────────────────────────────────────────────────────────┤
│ Base Tokens (gray.500, spacing.4, font.size.sm)             │
└─────────────────────────────────────────────────────────────┘
```

### Base Tokens

Raw design values. **Never use directly in components.**

| Category | Examples | File |
|----------|----------|------|
| Colors | `gray.500`, `primary.600`, `red.400` | `tokens/base/colors.json` |
| Spacing | `spacing.1` (4px), `spacing.4` (16px) | `tokens/base/spacing.json` |
| Typography | `font.size.sm`, `font.weight.bold` | `tokens/base/typography.json` |
| Radii | `radius.md`, `radius.full` | `tokens/base/radii.json` |
| Shadows | `shadow.md`, `shadow.lg` | `tokens/base/shadows.json` |

### Semantic Tokens

Meaningful names for UI purposes. **Use these in components.**

#### Background Colors
| Token | Usage |
|-------|-------|
| `semantic.bg.surface` | Main content background |
| `semantic.bg.surface-alt` | Alternating/secondary backgrounds |
| `semantic.bg.surface-hover` | Hover state for surfaces |
| `semantic.bg.muted` | De-emphasized areas |
| `semantic.bg.overlay` | Modal/dialog overlays |

#### Text Colors
| Token | Usage |
|-------|-------|
| `semantic.text.primary` | Main body text |
| `semantic.text.secondary` | Supporting text |
| `semantic.text.muted` | De-emphasized text |
| `semantic.text.placeholder` | Input placeholders |
| `semantic.text.link` | Hyperlinks |

#### Status Colors
| Token Group | Usage |
|-------------|-------|
| `semantic.status.info.*` | Informational messages |
| `semantic.status.success.*` | Success states |
| `semantic.status.warning.*` | Warning states |
| `semantic.status.error.*` | Error states |

Each status group includes: `bg`, `border`, `text`, `icon`

#### Governance Colors
| Token | Usage |
|-------|-------|
| `semantic.governance.demo.*` | DEMO mode indicators |
| `semantic.governance.live.*` | LIVE mode indicators |
| `semantic.governance.phi.*` | PHI status (blocked/warning/safe) |
| `semantic.governance.modelTier.*` | Model tier badges (nano/mini/frontier) |

### Component Tokens

Pre-configured component values:

```css
/* Button sizes */
--component-button-sm-height: var(--spacing-8);
--component-button-md-height: var(--spacing-10);
--component-button-lg-height: var(--spacing-12);

/* Input fields */
--component-input-height: var(--spacing-10);
--component-input-radius: var(--radius-md);

/* Cards */
--component-card-padding: var(--spacing-6);
--component-card-radius: var(--radius-lg);
```

## Color Palette

### Primary (Indigo)
Used for interactive elements, links, and focus states.

### Status Colors
- **Info (Blue)**: Informational content
- **Success (Green)**: Successful operations, approved states
- **Warning (Amber)**: Caution, DEMO mode, pending approvals
- **Error (Red)**: Errors, blocked access, PHI warnings

### Governance-Specific
- **DEMO Mode**: Amber background with locked icon
- **LIVE Mode**: Green background with unlocked icon
- **PHI Blocked**: Red indicators
- **Model Tiers**: Gray (Nano), Blue (Mini), Purple (Frontier)

## Typography

### Font Family
- **Sans**: Inter (primary), system fallbacks
- **Mono**: JetBrains Mono (code)

### Scale
| Name | Size | Usage |
|------|------|-------|
| xs | 0.75rem (12px) | Badges, captions |
| sm | 0.875rem (14px) | Body text, buttons |
| base | 1rem (16px) | Default body |
| lg | 1.125rem (18px) | Subtitles |
| xl | 1.25rem (20px) | Section headers |
| 2xl+ | 1.5rem+ | Page titles |

## Spacing Scale

Based on 4px increments:

| Token | Value | Usage |
|-------|-------|-------|
| 1 | 4px | Tight spacing |
| 2 | 8px | Component internal spacing |
| 3 | 12px | Small gaps |
| 4 | 16px | Default component padding |
| 6 | 24px | Section spacing |
| 8 | 32px | Large spacing |

## Usage in Code

### CSS Variables

```css
.my-component {
  background: var(--semantic-bg-surface);
  color: var(--semantic-text-primary);
  border: 1px solid var(--semantic-border-default);
  border-radius: var(--radius-md);
  padding: var(--spacing-4);
}
```

### TypeScript

```typescript
import { cssVars } from '@researchflow/design-tokens';

const styles = {
  backgroundColor: cssVars.SEMANTIC_BG_SURFACE,
  padding: cssVars.SPACING_4,
};
```

### Tailwind (with CSS variables)

```jsx
<div className="bg-[var(--semantic-bg-surface)] p-[var(--spacing-4)]">
  Content
</div>
```

## Adding New Tokens

1. Add to appropriate JSON file in `packages/design-tokens/tokens/`
2. Follow naming conventions:
   - Base: `category.variant.shade` (e.g., `color.base.gray.500`)
   - Semantic: `semantic.purpose.variant` (e.g., `semantic.bg.surface`)
   - Component: `component.name.size.property` (e.g., `component.button.md.height`)
3. Run `npm run build` in `packages/design-tokens`
4. Update this documentation

## Governance Considerations

### PHI-Safe Design
- All governance components use semantic tokens
- No hardcoded colors for status indicators
- Consistent visual language across DEMO/LIVE modes

### Accessibility
- All text colors meet WCAG 2.1 AA contrast requirements
- Focus indicators use high-visibility colors
- Status colors are paired with icons (not color-only)
