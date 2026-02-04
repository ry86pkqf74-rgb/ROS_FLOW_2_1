# Component Inventory

Mapping between Figma components and code implementations.

## Status Legend

| Icon | Status | Description |
|------|--------|-------------|
| ✅ | Complete | Implemented and reviewed |
| 🚧 | In Progress | Currently being developed |
| 📋 | Planned | Designed, not yet implemented |
| ⏸️ | Blocked | Waiting on dependencies |

---

## Primitive Components

| Figma Component | Code Component | File Path | Status | Figma Link |
|-----------------|----------------|-----------|--------|------------|
| RF/Button | Button | `packages/ui/src/primitives/Button/Button.tsx` | ✅ | [PENDING] |
| RF/Badge | Badge | `packages/ui/src/primitives/Badge/Badge.tsx` | ✅ | [PENDING] |
| RF/Alert | Alert | `packages/ui/src/primitives/Alert/Alert.tsx` | ✅ | [PENDING] |
| RF/Input | Input | `packages/ui/src/primitives/Input/Input.tsx` | 📋 | [PENDING] |
| RF/Card | Card | `packages/ui/src/primitives/Card/Card.tsx` | 📋 | [PENDING] |
| RF/Modal | Modal | `packages/ui/src/primitives/Modal/Modal.tsx` | 📋 | [PENDING] |
| RF/Table | Table | `packages/ui/src/primitives/Table/Table.tsx` | 📋 | [PENDING] |
| RF/Tabs | Tabs | `packages/ui/src/primitives/Tabs/Tabs.tsx` | 📋 | [PENDING] |

---

## Governance Components

| Figma Component | Code Component | File Path | Status | Figma Link |
|-----------------|----------------|-----------|--------|------------|
| RF/Governance/PHIGateBanner | PHIGateBanner | `packages/ui/src/governance/PHIGateBanner/PHIGateBanner.tsx` | ✅ | [PENDING] |
| RF/Governance/ModelTierBadge | ModelTierBadge | `packages/ui/src/governance/ModelTierBadge/ModelTierBadge.tsx` | ✅ | [PENDING] |
| RF/Governance/TransparencyPanel | TransparencyPanel | `packages/ui/src/governance/TransparencyPanel/TransparencyPanel.tsx` | ✅ | [PENDING] |
| RF/Governance/ApprovalStatus | ApprovalStatusIndicator | `packages/ui/src/governance/ApprovalStatusIndicator/` | 📋 | [PENDING] |

---

## Domain Components

| Figma Component | Code Component | File Path | Status | Figma Link |
|-----------------|----------------|-----------|--------|------------|
| RF/Domain/AuditLogViewer | AuditLogViewer | `packages/ui/src/domain/AuditLogViewer/` | 📋 | [PENDING] |
| RF/Domain/WorkflowGraph | WorkflowGraph | `packages/ui/src/domain/WorkflowGraph/` | 📋 | [PENDING] |
| RF/Domain/ArtifactBrowser | ArtifactBrowserPanel | `packages/ui/src/domain/ArtifactBrowserPanel/` | 📋 | [PENDING] |

---

## Adding Figma References

When implementing a component from Figma:

1. **Get the Figma link**: Right-click frame → "Copy link to selection"
2. **Extract node ID**: From URL format `?node-id=1234:5678`
3. **Add to component**: 
   ```typescript
   // figma: fileKey=ABC123 nodeId=1234:5678
   ```
4. **Update this table**: Add the Figma link to the corresponding row

## Component Standards

Each component should have:

- [ ] TypeScript props interface
- [ ] All UI states (loading, empty, error, success, disabled)
- [ ] Figma reference comment
- [ ] Design token usage (no hardcoded colors/spacing)
- [ ] Accessibility (ARIA attributes, keyboard navigation)
- [ ] Storybook story (when Storybook is set up)

## Variant Matrix

### Button Variants

| Variant | Size SM | Size MD | Size LG |
|---------|---------|---------|---------|
| Primary | ✅ | ✅ | ✅ |
| Secondary | ✅ | ✅ | ✅ |
| Outline | ✅ | ✅ | ✅ |
| Ghost | ✅ | ✅ | ✅ |
| Destructive | ✅ | ✅ | ✅ |

### Badge Variants

| Variant | Size SM | Size MD |
|---------|---------|---------|
| Default | ✅ | ✅ |
| Secondary | ✅ | ✅ |
| Success | ✅ | ✅ |
| Warning | ✅ | ✅ |
| Error | ✅ | ✅ |
| Info | ✅ | ✅ |

### Alert Variants

| Variant | With Title | Dismissible |
|---------|------------|-------------|
| Info | ✅ | ✅ |
| Success | ✅ | ✅ |
| Warning | ✅ | ✅ |
| Error | ✅ | ✅ |

### PHI Gate States

| State | Compact | Full |
|-------|---------|------|
| Blocked | ✅ | ✅ |
| Requires Approval | ✅ | ✅ |
| Approved | ✅ | ✅ |
| Demo Mode | ✅ | ✅ |

---

## Updating This Document

This document should be updated when:

1. A new component is designed in Figma
2. A component implementation is started
3. A component implementation is completed
4. Figma links are added/updated

**Last Updated**: 2026-01-30
