# @researchflow/design-tokens

Design tokens for ResearchFlow UI - compiled from Figma using Style Dictionary.

## Installation

```bash
npm install @researchflow/design-tokens
# or
pnpm add @researchflow/design-tokens
```

## Usage

### CSS Variables

Import the CSS file to get all tokens as CSS custom properties:

```css
@import '@researchflow/design-tokens/css';

.my-component {
  background-color: var(--semantic-bg-surface);
  color: var(--semantic-text-primary);
  border-radius: var(--radius-md);
  padding: var(--spacing-4);
}
```

### TypeScript

Import typed constants or CSS variable references:

```typescript
import { tokens, cssVars, colors, spacing } from '@researchflow/design-tokens';

// Direct values
const primaryColor = tokens.SEMANTIC_INTERACTIVE_PRIMARY_DEFAULT; // '#4F46E5'

// CSS variable references (for use in CSS-in-JS)
const styles = {
  backgroundColor: cssVars.SEMANTIC_BG_SURFACE, // 'var(--semantic-bg-surface)'
  padding: spacing['4'], // 'var(--spacing-4)'
};
```

## Token Structure

### Base Tokens

Raw design values - don't use directly in components:

- `color.base.*` - Color primitives (gray, primary, red, amber, green, blue, purple)
- `spacing.*` - Spacing scale (0-96 in 4px increments)
- `font.*` - Typography (family, size, weight, lineHeight, letterSpacing)
- `radius.*` - Border radius values
- `shadow.*` - Box shadow definitions

### Semantic Tokens

Meaningful names that reference base tokens:

- `semantic.bg.*` - Background colors (surface, muted, overlay, inverse)
- `semantic.text.*` - Text colors (primary, secondary, muted, inverse, link)
- `semantic.border.*` - Border colors (default, muted, strong, focus, error)
- `semantic.status.*` - Status colors (info, success, warning, error)
- `semantic.interactive.*` - Interactive states (primary, secondary, destructive)
- `semantic.governance.*` - Governance-specific colors (demo, live, phi, modelTier)

### Component Tokens

Pre-defined component configurations:

- `component.button.*` - Button sizes (sm, md, lg)
- `component.input.*` - Input field styles
- `component.badge.*` - Badge sizes
- `component.card.*` - Card styles
- `component.modal.*` - Modal configurations
- `component.table.*` - Table styles
- `component.alert.*` - Alert styles
- `component.tabs.*` - Tab styles

## Governance Tokens

Special tokens for ResearchFlow's governance UI:

```css
/* Demo vs Live mode */
.demo-banner {
  background: var(--semantic-governance-demo-bg);
  border-color: var(--semantic-governance-demo-border);
  color: var(--semantic-governance-demo-text);
}

/* PHI status indicators */
.phi-blocked { color: var(--semantic-governance-phi-blocked); }
.phi-warning { color: var(--semantic-governance-phi-warning); }
.phi-safe { color: var(--semantic-governance-phi-safe); }

/* Model tier badges */
.model-nano { background: var(--semantic-governance-modeltier-nano); }
.model-mini { background: var(--semantic-governance-modeltier-mini); }
.model-frontier { background: var(--semantic-governance-modeltier-frontier); }
```

## Building

```bash
# Build all outputs
npm run build

# Watch for changes
npm run build:watch

# Clean dist folder
npm run clean
```

## Outputs

After building:

- `dist/tokens.css` - CSS custom properties
- `dist/tokens.ts` - TypeScript constants with types
- `dist/tokens.js` - CommonJS module
- `dist/tokens.mjs` - ES module
- `dist/tokens.json` - Flat JSON (for tooling)

## Figma Integration

Tokens are designed to be exported from Figma using Tokens Studio or similar plugins:

1. Export tokens from Figma to JSON
2. Replace files in `tokens/` directory
3. Run `npm run build`
4. Commit updated `dist/` files

## Adding New Tokens

1. Add to appropriate JSON file in `tokens/base/` or `tokens/semantic/`
2. Follow naming conventions:
   - Base tokens: `category.variant.shade` (e.g., `color.base.gray.500`)
   - Semantic tokens: `semantic.purpose.variant` (e.g., `semantic.bg.surface`)
3. Run `npm run build` to regenerate outputs
4. Update this README if adding new categories

## License

MIT
