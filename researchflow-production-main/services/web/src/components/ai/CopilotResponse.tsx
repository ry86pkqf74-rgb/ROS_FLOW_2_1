import React, { useEffect, useRef } from 'react';

export interface SourceCitation {
  id: string;
  title: string;
  url?: string;
  type: 'document' | 'dataset' | 'analysis' | 'external';
  relevanceScore: number;
}

export interface CopilotResponseProps {
  content: string;
  sources: SourceCitation[];
  confidenceScore: number;
  isStreaming?: boolean;
  onSourceClick?: (sourceId: string) => void;
  className?: string;
  showConfidenceMetrics?: boolean;
}

interface ParsedContent {
  text: string;
  citations: Map<string, string[]>;
}

/**
 * Parses response content to identify inline citations
 * Looks for patterns like [1], [ref:1], [source:docId]
 */
const parseContent = (content: string): ParsedContent => {
  const citations = new Map<string, string[]>();
  const citationRegex = /\[(?:ref:|source:|)([^\]]+)\]/g;

  let match;
  while ((match = citationRegex.exec(content)) !== null) {
    const refId = match[1];
    if (!citations.has(refId)) {
      citations.set(refId, []);
    }
    if (match.index !== undefined) {
      citations.get(refId)?.push(`${match.index}:${match[0].length}`);
    }
  }

  return {
    text: content,
    citations,
  };
};

/**
 * Renders text with inline citation links
 */
const RichTextContent: React.FC<{
  content: string;
  citations: Map<string, string[]>;
  sources: Map<string, SourceCitation>;
  onSourceClick?: (sourceId: string) => void;
}> = ({ content, citations, sources, onSourceClick }) => {
  const parts: React.ReactNode[] = [];
  let lastIndex = 0;
  const citationRegex = /\[(?:ref:|source:|)([^\]]+)\]/g;

  let match;
  while ((match = citationRegex.exec(content)) !== null) {
    const refId = match[1];
    const source = sources.get(refId);

    // Add text before citation
    if (match.index > lastIndex) {
      parts.push(
        <span key={`text-${lastIndex}`}>
          {content.substring(lastIndex, match.index)}
        </span>
      );
    }

    // Add citation link
    if (source) {
      parts.push(
        <button
          key={`citation-${match.index}`}
          onClick={() => {
            onSourceClick?.(refId);
          }}
          className="inline-text-blue-600 hover:text-blue-800 hover:underline cursor-pointer font-medium text-sm"
          title={source.title}
          aria-label={`Citation: ${source.title}`}
        >
          [{refId}]
        </button>
      );
    } else {
      // Unknown citation, just render as text
      parts.push(
        <span key={`citation-text-${match.index}`} className="text-gray-500">
          {match[0]}
        </span>
      );
    }

    lastIndex = match.index + match[0].length;
  }

  // Add remaining text
  if (lastIndex < content.length) {
    parts.push(
      <span key={`text-${lastIndex}`}>{content.substring(lastIndex)}</span>
    );
  }

  return <>{parts}</>;
};

/**
 * Source Card Component
 */
const SourceCard: React.FC<{
  source: SourceCitation;
  onClick?: () => void;
}> = ({ source, onClick }) => {
  const typeColors: Record<string, string> = {
    document: 'bg-blue-50 border-blue-200 text-blue-700',
    dataset: 'bg-purple-50 border-purple-200 text-purple-700',
    analysis: 'bg-green-50 border-green-200 text-green-700',
    external: 'bg-gray-50 border-gray-200 text-gray-700',
  };

  const typeIcons: Record<string, string> = {
    document: '📄',
    dataset: '📊',
    analysis: '🔬',
    external: '🔗',
  };

  const colorClass = typeColors[source.type] || typeColors.external;
  const icon = typeIcons[source.type] || '📌';

  return (
    <button
      onClick={onClick}
      className={`w-full text-left p-3 rounded-lg border ${colorClass} hover:shadow-md transition-shadow`}
    >
      <div className="flex items-start gap-2">
        <span className="text-lg flex-shrink-0">{icon}</span>
        <div className="flex-1 min-w-0">
          <p className="font-medium text-sm line-clamp-2">{source.title}</p>
          <div className="flex items-center gap-2 mt-2">
            <div className="flex-1 h-1.5 bg-gray-200 rounded-full overflow-hidden">
              <div
                className="h-full bg-green-500 transition-all"
                style={{
                  width: `${Math.round(source.relevanceScore * 100)}%`,
                }}
              />
            </div>
            <span className="text-xs font-semibold whitespace-nowrap">
              {Math.round(source.relevanceScore * 100)}%
            </span>
          </div>
        </div>
      </div>
    </button>
  );
};

/**
 * Main Copilot Response Component
 */
export const CopilotResponse: React.FC<CopilotResponseProps> = ({
  content,
  sources,
  confidenceScore,
  isStreaming = false,
  onSourceClick,
  className = '',
  showConfidenceMetrics = true,
}) => {
  const contentRef = useRef<HTMLDivElement>(null);
  const parsed = parseContent(content);
  const sourceMap = new Map(sources.map((s) => [s.id, s]));

  // Auto-scroll to bottom when streaming
  useEffect(() => {
    if (isStreaming && contentRef.current) {
      contentRef.current.scrollIntoView({ behavior: 'smooth', block: 'end' });
    }
  }, [content, isStreaming]);

  // Group sources by type
  const sourcesByType = sources.reduce(
    (acc, source) => {
      if (!acc[source.type]) {
        acc[source.type] = [];
      }
      acc[source.type].push(source);
      return acc;
    },
    {} as Record<string, SourceCitation[]>
  );

  // Sort sources by relevance within each type
  Object.values(sourcesByType).forEach((typeSources) => {
    typeSources.sort((a, b) => b.relevanceScore - a.relevanceScore);
  });

  const confidenceLevel =
    confidenceScore > 0.8 ? 'high' : confidenceScore > 0.6 ? 'medium' : 'low';
  const confidenceColor =
    confidenceLevel === 'high'
      ? 'text-green-700 bg-green-50'
      : confidenceLevel === 'medium'
        ? 'text-yellow-700 bg-yellow-50'
        : 'text-orange-700 bg-orange-50';

  return (
    <div className={`space-y-4 ${className}`}>
      {/* Main Response Content */}
      <div className="bg-white rounded-lg border border-gray-200 p-6">
        <div
          ref={contentRef}
          className="prose prose-sm max-w-none text-gray-800 leading-relaxed"
        >
          <RichTextContent
            content={content}
            citations={parsed.citations}
            sources={sourceMap}
            onSourceClick={onSourceClick}
          />
          {isStreaming && (
            <span className="inline-block w-2 h-5 ml-1 bg-blue-600 animate-pulse" />
          )}
        </div>

        {/* Metadata */}
        <div className="mt-6 pt-6 border-t border-gray-200 flex flex-wrap items-center gap-4">
          {showConfidenceMetrics && (
            <div className="flex items-center gap-2">
              <span className="text-sm font-medium text-gray-600">
                Confidence:
              </span>
              <div className="flex items-center gap-2">
                <div className="h-2 w-20 bg-gray-200 rounded-full overflow-hidden">
                  <div
                    className={`h-full transition-all ${
                      confidenceLevel === 'high'
                        ? 'bg-green-500'
                        : confidenceLevel === 'medium'
                          ? 'bg-yellow-500'
                          : 'bg-orange-500'
                    }`}
                    style={{
                      width: `${confidenceScore * 100}%`,
                    }}
                  />
                </div>
                <span className={`text-sm font-semibold ${confidenceColor}`}>
                  {Math.round(confidenceScore * 100)}%
                </span>
              </div>
            </div>
          )}

          {/* Citation count */}
          {sources.length > 0 && (
            <div className="text-sm text-gray-600">
              <span className="font-medium">{sources.length}</span> source
              {sources.length !== 1 ? 's' : ''} cited
            </div>
          )}

          {/* Streaming indicator */}
          {isStreaming && (
            <div className="flex items-center gap-2 text-sm text-blue-600">
              <span className="inline-block w-2 h-2 bg-blue-600 rounded-full animate-pulse" />
              Streaming response...
            </div>
          )}
        </div>
      </div>

      {/* Sources Section */}
      {sources.length > 0 && (
        <div className="bg-white rounded-lg border border-gray-200 p-6">
          <h3 className="font-semibold text-gray-900 mb-4 flex items-center gap-2">
            <span>📚 Sources</span>
            <span className="inline-block px-2 py-0.5 bg-gray-100 text-gray-700 text-xs font-medium rounded-full">
              {sources.length}
            </span>
          </h3>

          <div className="space-y-6">
            {Object.entries(sourcesByType).map(([type, typeSources]) => (
              <div key={type}>
                <h4 className="text-sm font-medium text-gray-700 mb-3 capitalize">
                  {type === 'document'
                    ? 'Documents'
                    : type === 'dataset'
                      ? 'Datasets'
                      : type === 'analysis'
                        ? 'Analyses'
                        : 'External Sources'}
                </h4>
                <div className="space-y-2">
                  {typeSources.map((source) => (
                    <SourceCard
                      key={source.id}
                      source={source}
                      onClick={() => {
                        onSourceClick?.(source.id);
                      }}
                    />
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* No Sources Warning */}
      {sources.length === 0 && (
        <div className="bg-amber-50 border border-amber-200 rounded-lg p-4">
          <p className="text-sm text-amber-800">
            ℹ️ This response was generated without source citations. Results
            should be reviewed carefully.
          </p>
        </div>
      )}
    </div>
  );
};

export default CopilotResponse;
