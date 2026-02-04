# Accessibility Checklist

## Overview

ResearchFlow serves healthcare professionals. All UI must meet WCAG 2.1 AA standards and be usable via keyboard, screen readers, and assistive technologies.

## Quick Checklist

Use this checklist when reviewing any UI component or page:

### Keyboard Navigation

- [ ] All interactive elements are focusable via Tab
- [ ] Focus order follows logical reading order
- [ ] Focus indicators are clearly visible
- [ ] Escape closes modals/dropdowns
- [ ] Enter/Space activates buttons and controls
- [ ] Arrow keys navigate within composite widgets (tabs, menus)
- [ ] No keyboard traps

### Screen Reader

- [ ] All images have meaningful alt text (or empty alt for decorative)
- [ ] Form inputs have associated labels
- [ ] Error messages are announced
- [ ] Page has proper heading hierarchy (h1 → h2 → h3)
- [ ] Dynamic content changes are announced (aria-live)
- [ ] Icons have accessible names or are hidden (aria-hidden)

### Color & Contrast

- [ ] Text contrast ratio ≥ 4.5:1 (normal text)
- [ ] Text contrast ratio ≥ 3:1 (large text, 18px+ or 14px+ bold)
- [ ] UI component contrast ratio ≥ 3:1
- [ ] Information not conveyed by color alone (use icons, text, patterns)
- [ ] Focus indicators have sufficient contrast

### Forms

- [ ] All inputs have visible labels
- [ ] Required fields are indicated (not just by color)
- [ ] Error messages are clear and specific
- [ ] Error states are visually distinct
- [ ] Autocomplete attributes are used appropriately

### Motion & Time

- [ ] No content flashes more than 3 times per second
- [ ] Animations respect `prefers-reduced-motion`
- [ ] No time limits (or user can extend/disable)
- [ ] Auto-updating content can be paused

---

## Component-Specific Guidelines

### Buttons

```tsx
// ✅ Good
<button type="button" onClick={handleClick}>
  Save Changes
</button>

// ✅ Good - icon with text
<button type="button">
  <SaveIcon aria-hidden="true" />
  Save
</button>

// ✅ Good - icon only with label
<button type="button" aria-label="Save changes">
  <SaveIcon aria-hidden="true" />
</button>

// ❌ Bad - no accessible name
<button type="button">
  <SaveIcon />
</button>
```

### Modals/Dialogs

```tsx
// Required attributes
<div
  role="dialog"
  aria-modal="true"
  aria-labelledby="dialog-title"
  aria-describedby="dialog-description"
>
  <h2 id="dialog-title">Confirm Action</h2>
  <p id="dialog-description">Are you sure you want to proceed?</p>
  {/* Focus should be trapped within dialog */}
  <button>Cancel</button>
  <button>Confirm</button>
</div>
```

### Alerts & Notifications

```tsx
// Status messages that don't require action
<div role="status" aria-live="polite">
  Changes saved successfully.
</div>

// Important alerts that require attention
<div role="alert" aria-live="assertive">
  Error: Unable to save changes.
</div>
```

### Tables

```tsx
<table>
  <caption>Workflow execution history</caption>
  <thead>
    <tr>
      <th scope="col">Date</th>
      <th scope="col">Status</th>
      <th scope="col">Duration</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td>2026-01-30</td>
      <td>Completed</td>
      <td>2m 34s</td>
    </tr>
  </tbody>
</table>
```

### Tabs

```tsx
<div role="tablist" aria-label="Dashboard sections">
  <button
    role="tab"
    aria-selected="true"
    aria-controls="panel-overview"
    id="tab-overview"
  >
    Overview
  </button>
  <button
    role="tab"
    aria-selected="false"
    aria-controls="panel-details"
    id="tab-details"
    tabIndex={-1}
  >
    Details
  </button>
</div>

<div
  role="tabpanel"
  id="panel-overview"
  aria-labelledby="tab-overview"
>
  {/* Panel content */}
</div>
```

### Loading States

```tsx
// Spinner with status
<div role="status" aria-live="polite">
  <Spinner aria-hidden="true" />
  <span className="sr-only">Loading workflow data...</span>
</div>

// Skeleton loading
<div aria-busy="true" aria-describedby="loading-message">
  <p id="loading-message" className="sr-only">
    Loading content, please wait.
  </p>
  <SkeletonCard />
  <SkeletonCard />
</div>
```

---

## Governance-Specific Accessibility

### PHI Gate Banner

```tsx
<div
  role="alert"
  aria-live="polite"
  className="phi-gate-banner"
>
  <ShieldIcon aria-hidden="true" />
  <div>
    <h4>PHI Access Blocked</h4>
    <p>This content requires approval to access.</p>
  </div>
  <button>Request Access</button>
</div>
```

### Model Tier Indicators

Always pair color with text/icon:

```tsx
// ✅ Good - color AND text
<span className="model-tier nano">
  <CpuIcon aria-hidden="true" />
  Nano Tier
</span>

// ❌ Bad - color only
<span className="model-tier nano" style={{ background: 'gray' }} />
```

### Audit Log

- Ensure filter controls are labeled
- Announce when results update
- Provide keyboard navigation through log entries
- Export functionality is keyboard accessible

---

## Testing Tools

### Automated

- **axe DevTools**: Browser extension for quick audits
- **Lighthouse**: Built into Chrome DevTools
- **eslint-plugin-jsx-a11y**: Catch issues during development

### Manual

- **Keyboard-only testing**: Unplug mouse, navigate with Tab/Enter/Escape
- **Screen reader testing**: NVDA (Windows), VoiceOver (Mac), JAWS
- **Zoom testing**: Test at 200% and 400% zoom
- **Color blindness simulators**: Chrome DevTools rendering emulation

### Continuous

Add to CI/CD:

```yaml
# Example GitHub Action
- name: Accessibility audit
  run: npx @axe-core/cli http://localhost:5173 --exit
```

---

## Resources

- [WCAG 2.1 Guidelines](https://www.w3.org/WAI/WCAG21/quickref/)
- [ARIA Authoring Practices Guide](https://www.w3.org/WAI/ARIA/apg/)
- [Inclusive Components](https://inclusive-components.design/)
- [A11y Project Checklist](https://www.a11yproject.com/checklist/)

---

## When to Get Expert Review

Request accessibility expert review when:

- Building new complex interactive patterns
- Handling sensitive user data (PHI)
- Creating custom form controls
- Implementing data visualizations
- Adding real-time/live updating content
- Unsure about ARIA usage
