/**
 * JournalStyleSelector - Journal style dropdown with visual previews and metadata
 */

import React, { useMemo } from 'react';
import { BookOpen } from 'lucide-react';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { cn } from '@/lib/utils';

const STORAGE_RECENT = 'researchflow_export_recent_styles';
const RECENT_MAX = 5;

export interface JournalStyle {
  key: string;
  name: string;
  description: string;
  wordLimit?: string;
  citationFormat?: string;
}

export const JOURNAL_STYLES: JournalStyle[] = [
  { key: 'none', name: 'None / Default', description: 'No journal template', citationFormat: 'AMA' },
  {
    key: 'jama',
    name: 'JAMA',
    description: 'Journal of the American Medical Association',
    wordLimit: '3500',
    citationFormat: 'Vancouver',
  },
  {
    key: 'nejm',
    name: 'NEJM',
    description: 'New England Journal of Medicine',
    wordLimit: '3000',
    citationFormat: 'Vancouver',
  },
  {
    key: 'bmj',
    name: 'BMJ',
    description: 'British Medical Journal',
    wordLimit: '3000',
    citationFormat: 'Vancouver',
  },
  {
    key: 'lancet',
    name: 'The Lancet',
    description: 'The Lancet',
    wordLimit: '3000',
    citationFormat: 'Vancouver',
  },
  {
    key: 'nature',
    name: 'Nature',
    description: 'Nature',
    wordLimit: '3000',
    citationFormat: 'Nature',
  },
  {
    key: 'plos',
    name: 'PLOS',
    description: 'Public Library of Science',
    wordLimit: '3000',
    citationFormat: 'Vancouver',
  },
];

function getRecentKeys(): string[] {
  try {
    const raw = localStorage.getItem(STORAGE_RECENT);
    if (!raw) return [];
    const parsed = JSON.parse(raw) as unknown;
    return Array.isArray(parsed) ? parsed.slice(0, RECENT_MAX) : [];
  } catch {
    return [];
  }
}

function setRecentKeys(keys: string[]) {
  try {
    localStorage.setItem(STORAGE_RECENT, JSON.stringify(keys.slice(0, RECENT_MAX)));
  } catch {
    // ignore
  }
}

export interface JournalStyleSelectorProps {
  value: string | null;
  onChange: (key: string | null) => void;
  disabled?: boolean;
  showRecent?: boolean;
  className?: string;
}

export function JournalStyleSelector({
  value,
  onChange,
  disabled = false,
  showRecent = true,
  className,
}: JournalStyleSelectorProps) {
  const recentKeys = useMemo(getRecentKeys, [value]);

  const sortedStyles = useMemo(() => {
    const byKey = new Map(JOURNAL_STYLES.map((s) => [s.key, s]));
    const recent = recentKeys
      .map((k) => byKey.get(k))
      .filter(Boolean) as JournalStyle[];
    const rest = JOURNAL_STYLES.filter((s) => !recentKeys.includes(s.key));
    return [...recent, ...rest];
  }, [recentKeys]);

  const handleChange = (key: string) => {
    const next = key === 'none' || !key ? null : key;
    onChange(next);
    if (next) {
      const prev = getRecentKeys().filter((k) => k !== next);
      setRecentKeys([next, ...prev]);
    }
  };

  return (
    <div className={cn('space-y-2', className)}>
      <label className="text-sm font-medium flex items-center gap-2">
        <BookOpen className="h-4 w-4" />
        Journal style
      </label>
      <Select
        value={value ?? 'none'}
        onValueChange={handleChange}
        disabled={disabled}
      >
        <SelectTrigger>
          <SelectValue placeholder="Select journal style" />
        </SelectTrigger>
        <SelectContent>
          {sortedStyles.map((style) => (
            <SelectItem key={style.key} value={style.key}>
              <div className="flex flex-col gap-0.5 py-0.5">
                <span className="font-medium">{style.name}</span>
                <span className="text-xs text-muted-foreground font-normal">
                  {style.description}
                  {style.wordLimit && ` · ${style.wordLimit} words`}
                  {style.citationFormat && ` · ${style.citationFormat}`}
                </span>
              </div>
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>
  );
}
