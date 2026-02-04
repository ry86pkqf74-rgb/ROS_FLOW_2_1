/**
 * MermaidDiagram - Renders Mermaid diagram source as SVG
 * Uses mermaid.run() with a container; handles loading and errors.
 */

import React, { useEffect, useRef, useState } from 'react';
import mermaid from 'mermaid';
import { cn } from '@/lib/utils';

export interface MermaidDiagramProps {
  diagram: string;
  className?: string;
}

let mermaidInitialized = false;

function initMermaid() {
  if (mermaidInitialized) return;
  mermaid.initialize({
    startOnLoad: false,
    theme: 'neutral',
    securityLevel: 'loose',
  });
  mermaidInitialized = true;
}

export function MermaidDiagram({ diagram, className }: MermaidDiagramProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    initMermaid();
    setError(null);
    setLoading(true);

    if (!diagram.trim()) {
      setLoading(false);
      return;
    }

    const container = containerRef.current;
    if (!container) {
      setLoading(false);
      return;
    }

    const id = `mermaid-${Date.now()}-${Math.random().toString(36).slice(2, 9)}`;
    container.innerHTML = '';
    const pre = document.createElement('div');
    pre.id = id;
    pre.className = 'mermaid';
    pre.textContent = diagram;
    container.appendChild(pre);

    mermaid
      .run({
        nodes: [pre],
        suppressErrors: false,
      })
      .then(() => {
        setLoading(false);
      })
      .catch((err) => {
        setError(err.message ?? 'Failed to render diagram');
        setLoading(false);
      });
  }, [diagram]);

  if (!diagram.trim()) {
    return (
      <div
        className={cn(
          'flex items-center justify-center rounded-md border border-dashed bg-muted/30 text-sm text-muted-foreground p-8',
          className
        )}
      >
        No diagram available.
      </div>
    );
  }

  if (error) {
    return (
      <div
        className={cn(
          'rounded-md border border-destructive/50 bg-destructive/5 p-4 text-sm text-destructive',
          className
        )}
      >
        <p className="font-medium">Diagram error</p>
        <p className="mt-1">{error}</p>
      </div>
    );
  }

  if (loading) {
    return (
      <div
        className={cn(
          'flex items-center justify-center rounded-md border bg-muted/30 text-sm text-muted-foreground p-8',
          className
        )}
      >
        Rendering diagram…
      </div>
    );
  }

  return (
    <div
      ref={containerRef}
      className={cn('mermaid-container overflow-auto', className)}
    />
  );
}
