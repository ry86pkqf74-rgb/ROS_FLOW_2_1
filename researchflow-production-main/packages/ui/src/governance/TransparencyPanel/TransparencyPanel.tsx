import { 
  Eye, 
  Clock, 
  DollarSign, 
  Shield, 
  FileText, 
  ChevronDown, 
  ChevronUp,
  ExternalLink 
} from 'lucide-react';
import * as React from 'react';

import { cn } from '../../utils/cn';
import { ModelTierBadge, type ModelTier } from '../ModelTierBadge';

// figma: fileKey=PENDING nodeId=PENDING
// Component contract: RF/Governance/TransparencyPanel

export interface TransparencyData {
  /** Model tier used */
  modelTier: ModelTier;
  /** Specific model identifier */
  modelId?: string;
  /** Processing latency in milliseconds */
  latencyMs: number;
  /** Estimated cost in cents */
  costCents?: number;
  /** Number of input tokens */
  inputTokens?: number;
  /** Number of output tokens */
  outputTokens?: number;
  /** Summary of data sent (PHI-safe) */
  dataSummary?: string;
  /** Redactions performed */
  redactions?: string[];
  /** Link to audit log entry */
  auditLogUrl?: string;
  /** Timestamp of operation */
  timestamp: Date;
}

export interface TransparencyPanelProps extends React.HTMLAttributes<HTMLDivElement> {
  /** Transparency data to display */
  data: TransparencyData;
  /** Collapsed by default */
  defaultCollapsed?: boolean;
  /** Title for the panel */
  title?: string;
}

export const TransparencyPanel = React.forwardRef<HTMLDivElement, TransparencyPanelProps>(
  (
    {
      className,
      data,
      defaultCollapsed = true,
      title = 'AI Transparency',
      ...props
    },
    ref
  ) => {
    const [isCollapsed, setIsCollapsed] = React.useState(defaultCollapsed);

    const formatLatency = (ms: number) => {
      if (ms < 1000) return `${ms}ms`;
      return `${(ms / 1000).toFixed(2)}s`;
    };

    const formatCost = (cents?: number) => {
      if (cents === undefined) return '—';
      if (cents < 1) return '<$0.01';
      return `$${(cents / 100).toFixed(4)}`;
    };

    const formatTimestamp = (date: Date) => {
      return new Intl.DateTimeFormat('en-US', {
        dateStyle: 'short',
        timeStyle: 'medium',
      }).format(date);
    };

    return (
      <div
        ref={ref}
        className={cn(
          'border rounded-[var(--radius-lg)]',
          'bg-[var(--semantic-bg-surface)]',
          'border-[var(--semantic-border-default)]',
          className
        )}
        {...props}
      >
        {/* Header - always visible */}
        <button
          type="button"
          onClick={() => setIsCollapsed(!isCollapsed)}
          className={cn(
            'w-full flex items-center justify-between',
            'px-4 py-3',
            'text-left',
            'hover:bg-[var(--semantic-bg-surface-hover)]',
            'transition-colors',
            'rounded-[var(--radius-lg)]',
            !isCollapsed && 'rounded-b-none border-b border-[var(--semantic-border-default)]'
          )}
        >
          <div className="flex items-center gap-3">
            <Eye className="h-5 w-5 text-[var(--semantic-text-muted)]" />
            <span className="font-medium text-[var(--semantic-text-primary)]">
              {title}
            </span>
            <ModelTierBadge tier={data.modelTier} size="sm" />
          </div>
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-1 text-sm text-[var(--semantic-text-muted)]">
              <Clock className="h-4 w-4" />
              {formatLatency(data.latencyMs)}
            </div>
            {isCollapsed ? (
              <ChevronDown className="h-5 w-5 text-[var(--semantic-text-muted)]" />
            ) : (
              <ChevronUp className="h-5 w-5 text-[var(--semantic-text-muted)]" />
            )}
          </div>
        </button>

        {/* Collapsible content */}
        {!isCollapsed && (
          <div className="px-4 py-4 space-y-4">
            {/* Model & Performance */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div>
                <div className="text-xs text-[var(--semantic-text-muted)] uppercase tracking-wider mb-1">
                  Model
                </div>
                <div className="flex items-center gap-2">
                  <ModelTierBadge tier={data.modelTier} size="sm" />
                  {data.modelId && (
                    <span className="text-sm text-[var(--semantic-text-secondary)]">
                      {data.modelId}
                    </span>
                  )}
                </div>
              </div>
              
              <div>
                <div className="text-xs text-[var(--semantic-text-muted)] uppercase tracking-wider mb-1">
                  Latency
                </div>
                <div className="flex items-center gap-1.5 text-sm text-[var(--semantic-text-primary)]">
                  <Clock className="h-4 w-4 text-[var(--semantic-text-muted)]" />
                  {formatLatency(data.latencyMs)}
                </div>
              </div>
              
              <div>
                <div className="text-xs text-[var(--semantic-text-muted)] uppercase tracking-wider mb-1">
                  Cost
                </div>
                <div className="flex items-center gap-1.5 text-sm text-[var(--semantic-text-primary)]">
                  <DollarSign className="h-4 w-4 text-[var(--semantic-text-muted)]" />
                  {formatCost(data.costCents)}
                </div>
              </div>
              
              <div>
                <div className="text-xs text-[var(--semantic-text-muted)] uppercase tracking-wider mb-1">
                  Tokens
                </div>
                <div className="text-sm text-[var(--semantic-text-primary)]">
                  {data.inputTokens ?? '—'} in / {data.outputTokens ?? '—'} out
                </div>
              </div>
            </div>

            {/* Data Summary */}
            {data.dataSummary && (
              <div>
                <div className="text-xs text-[var(--semantic-text-muted)] uppercase tracking-wider mb-1">
                  Data Sent (PHI-Safe Summary)
                </div>
                <div className="p-3 bg-[var(--semantic-bg-muted)] rounded-[var(--radius-md)] text-sm text-[var(--semantic-text-secondary)]">
                  {data.dataSummary}
                </div>
              </div>
            )}

            {/* Redactions */}
            {data.redactions && data.redactions.length > 0 && (
              <div>
                <div className="flex items-center gap-1.5 text-xs text-[var(--semantic-text-muted)] uppercase tracking-wider mb-2">
                  <Shield className="h-4 w-4" />
                  Redactions Applied ({data.redactions.length})
                </div>
                <div className="flex flex-wrap gap-2">
                  {data.redactions.map((redaction, index) => (
                    <span
                      key={index}
                      className={cn(
                        'inline-flex items-center',
                        'px-2 py-0.5 rounded-full',
                        'text-xs font-medium',
                        'bg-[var(--semantic-status-warning-bg)]',
                        'text-[var(--semantic-status-warning-text)]',
                        'border border-[var(--semantic-status-warning-border)]'
                      )}
                    >
                      {redaction}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {/* Footer */}
            <div className="flex items-center justify-between pt-2 border-t border-[var(--semantic-border-muted)]">
              <div className="text-xs text-[var(--semantic-text-muted)]">
                {formatTimestamp(data.timestamp)}
              </div>
              {data.auditLogUrl && (
                <a
                  href={data.auditLogUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  className={cn(
                    'inline-flex items-center gap-1',
                    'text-xs font-medium',
                    'text-[var(--semantic-text-link)]',
                    'hover:text-[var(--semantic-text-link-hover)]',
                    'hover:underline'
                  )}
                >
                  <FileText className="h-3.5 w-3.5" />
                  View Audit Log
                  <ExternalLink className="h-3 w-3" />
                </a>
              )}
            </div>
          </div>
        )}
      </div>
    );
  }
);

TransparencyPanel.displayName = 'TransparencyPanel';

export default TransparencyPanel;
