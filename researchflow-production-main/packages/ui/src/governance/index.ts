// Governance Components
export { 
  PHIGateBanner, 
  type PHIGateBannerProps, 
  type PHIStatus 
} from './PHIGateBanner';

export { 
  ModelTierBadge, 
  type ModelTierBadgeProps, 
  type ModelTier 
} from './ModelTierBadge';

export { 
  TransparencyPanel, 
  type TransparencyPanelProps, 
  type TransparencyData 
} from './TransparencyPanel';

export {
  ApprovalStatusIndicator,
  type ApprovalStatusIndicatorProps,
  type ApprovalDetails,
  type ApprovalStatus,
} from './ApprovalStatusIndicator';

// Re-export defaults
export { default as PHIGateBanner } from './PHIGateBanner';
export { default as ModelTierBadge } from './ModelTierBadge';
export { default as TransparencyPanel } from './TransparencyPanel';
export { default as ApprovalStatusIndicator } from './ApprovalStatusIndicator';
