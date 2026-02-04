/**
 * Stage 15 - Manuscript Compilation (manuscript writing pipeline)
 * Section assembly, reference management, format selector
 */

import * as React from 'react';
import { useState } from 'react';
import {
  Card,
  CardHeader,
  CardTitle,
  CardContent,
  CardDescription,
} from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Checkbox } from '@/components/ui/checkbox';
import { Label } from '@/components/ui/label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Check } from 'lucide-react';

interface StageProps {
  workflowId: string;
  manuscriptId?: string;
  onComplete: () => void;
}

const SECTIONS = [
  { id: 'title', label: 'Title' },
  { id: 'abstract', label: 'Abstract' },
  { id: 'intro', label: 'Introduction' },
  { id: 'methods', label: 'Methods' },
  { id: 'results', label: 'Results' },
  { id: 'discussion', label: 'Discussion' },
  { id: 'references', label: 'References' },
  { id: 'appendices', label: 'Appendices' },
];

const FORMAT_OPTIONS = [
  { value: 'imrad', label: 'IMRaD' },
  { value: 'apa', label: 'APA' },
  { value: 'ama', label: 'AMA' },
  { value: 'vancouver', label: 'Vancouver' },
];

export function Stage15ManuscriptCompilation({
  workflowId,
  manuscriptId,
  onComplete,
}: StageProps) {
  const [includedSections, setIncludedSections] = useState<Record<string, boolean>>(
    SECTIONS.reduce((acc, s) => ({ ...acc, [s.id]: true }), {})
  );
  const [format, setFormat] = useState<string>('imrad');

  const toggleSection = (id: string) => {
    setIncludedSections((prev) => ({ ...prev, [id]: !prev[id] }));
  };

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>Section assembly</CardTitle>
          <CardDescription>Include or exclude sections in the compiled manuscript.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-2">
          {SECTIONS.map((s) => (
            <div key={s.id} className="flex items-center space-x-2">
              <Checkbox
                id={s.id}
                checked={includedSections[s.id] ?? true}
                onCheckedChange={() => toggleSection(s.id)}
              />
              <Label htmlFor={s.id}>{s.label}</Label>
            </div>
          ))}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Reference list</CardTitle>
          <CardDescription>References will be assembled from citations used in the manuscript.</CardDescription>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">Reference list placeholder — managed via citation keys in sections.</p>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Format selector</CardTitle>
          <CardDescription>Choose the manuscript/reference format.</CardDescription>
        </CardHeader>
        <CardContent>
          <Select value={format} onValueChange={setFormat}>
            <SelectTrigger>
              <SelectValue placeholder="Select format" />
            </SelectTrigger>
            <SelectContent>
              {FORMAT_OPTIONS.map((opt) => (
                <SelectItem key={opt.value} value={opt.value}>
                  {opt.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </CardContent>
      </Card>

      <div className="flex justify-end gap-2">
        <Button onClick={onComplete}>
          <Check className="h-4 w-4 mr-1" />
          Complete Stage
        </Button>
      </div>
    </div>
  );
}

export default Stage15ManuscriptCompilation;
