/**
 * ManuscriptPreview - Full manuscript preview with section navigation and print mode
 */

import React, { useMemo, useCallback } from 'react';
import { Download, Printer, FileText } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { ScrollArea } from '@/components/ui/scroll-area';
import { cn } from '@/lib/utils';

export interface ManuscriptSection {
  id: string;
  title: string;
  content: string;
}

export interface ManuscriptPreviewProps {
  manuscriptId: string;
  previewMarkdown?: string;
  title?: string;
  sections?: ManuscriptSection[];
  onDownloadSection?: (sectionId: string) => void;
  printMode?: boolean;
  className?: string;
}

/** Simple markdown-like rendering: # ## ### and paragraphs */
function renderMarkdown(text: string) {
  const lines = text.split('\n');
  const nodes: React.ReactNode[] = [];
  let key = 0;
  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    if (line.startsWith('### ')) {
      nodes.push(<h4 key={key++} className="text-sm font-semibold mt-4 mb-2">{line.slice(4)}</h4>);
    } else if (line.startsWith('## ')) {
      nodes.push(<h3 key={key++} className="text-base font-semibold mt-4 mb-2">{line.slice(3)}</h3>);
    } else if (line.startsWith('# ')) {
      nodes.push(<h2 key={key++} className="text-lg font-semibold mt-4 mb-2">{line.slice(2)}</h2>);
    } else if (line.trim()) {
      nodes.push(<p key={key++} className="mb-2 text-sm">{line}</p>);
    } else {
      nodes.push(<br key={key++} />);
    }
  }
  return nodes;
}

export function ManuscriptPreview({
  manuscriptId,
  previewMarkdown,
  title,
  sections = [],
  onDownloadSection,
  printMode = false,
  className,
}: ManuscriptPreviewProps) {
  const navItems = useMemo(() => {
    if (sections.length) {
      return sections.map((s) => ({ id: s.id, title: s.title }));
    }
    if (previewMarkdown) {
      const lines = previewMarkdown.split('\n');
      const items: { id: string; title: string }[] = [];
      lines.forEach((line, i) => {
        if (line.startsWith('# ') || line.startsWith('## ')) {
          const t = line.replace(/^#+\s*/, '');
          items.push({ id: `h-${i}`, title: t });
        }
      });
      return items;
    }
    return [];
  }, [sections, previewMarkdown]);

  const handlePrint = useCallback(() => {
    window.print();
  }, []);

  const content = useMemo(() => {
    if (previewMarkdown) {
      return (
        <div className="prose prose-sm max-w-none dark:prose-invert">
          {title && <h1 className="text-xl font-bold mb-4">{title}</h1>}
          {renderMarkdown(previewMarkdown)}
        </div>
      );
    }
    if (sections.length) {
      return (
        <div className="prose prose-sm max-w-none dark:prose-invert space-y-6">
          {title && <h1 className="text-xl font-bold mb-4">{title}</h1>}
          {sections.map((section) => (
            <div key={section.id} id={section.id} className="scroll-mt-4">
              <h2 className="text-lg font-semibold mb-2">{section.title}</h2>
              <div className="whitespace-pre-wrap text-sm">
                {section.content || <span className="text-muted-foreground italic">No content</span>}
              </div>
              {onDownloadSection && (
                <Button
                  variant="ghost"
                  size="sm"
                  className="mt-2"
                  onClick={() => onDownloadSection(section.id)}
                >
                  <Download className="mr-2 h-4 w-4" />
                  Download section
                </Button>
              )}
            </div>
          ))}
        </div>
      );
    }
    return (
      <div className="flex flex-col items-center justify-center py-12 text-muted-foreground">
        <FileText className="h-12 w-12 mb-4" />
        <p>No preview content available.</p>
      </div>
    );
  }, [previewMarkdown, title, sections, onDownloadSection]);

  return (
    <div
      className={cn(
        'flex flex-col h-full',
        printMode && 'print:block',
        className
      )}
    >
      {!printMode && (
        <div className="flex items-center justify-between gap-2 pb-3 border-b shrink-0">
          <nav className="flex items-center gap-2 overflow-x-auto">
            {navItems.map((item) => (
              <a
                key={item.id}
                href={`#${item.id}`}
                className="text-xs text-primary hover:underline whitespace-nowrap"
              >
                {item.title}
              </a>
            ))}
          </nav>
          <Button variant="outline" size="sm" onClick={handlePrint}>
            <Printer className="mr-2 h-4 w-4" />
            Print preview
          </Button>
        </div>
      )}
      <ScrollArea className={cn('flex-1', printMode && 'print:overflow-visible')}>
        <div className="p-4">{content}</div>
      </ScrollArea>
    </div>
  );
}
