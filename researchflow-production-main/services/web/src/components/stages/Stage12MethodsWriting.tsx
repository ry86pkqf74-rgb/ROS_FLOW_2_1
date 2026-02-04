/**
 * Stage 12 - Methods Writing (manuscript writing pipeline)
 * Study design, reporting checklist (CONSORT/STROBE), protocol reference
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
import { Textarea } from '@/components/ui/textarea';
import { Input } from '@/components/ui/input';
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

const CHECKLIST_OPTIONS = [
  { value: 'none', label: 'None' },
  { value: 'consort', label: 'CONSORT (trials)' },
  { value: 'strobe', label: 'STROBE (observational)' },
  { value: 'prisma', label: 'PRISMA (reviews)' },
  { value: 'other', label: 'Other' },
];

export function Stage12MethodsWriting({
  workflowId,
  manuscriptId,
  onComplete,
}: StageProps) {
  const [studyDesign, setStudyDesign] = useState('');
  const [checklist, setChecklist] = useState<string>('none');
  const [protocolRef, setProtocolRef] = useState('');

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>Study design</CardTitle>
          <CardDescription>Describe study design, setting, participants, and procedures.</CardDescription>
        </CardHeader>
        <CardContent>
          <Textarea
            value={studyDesign}
            onChange={(e) => setStudyDesign(e.target.value)}
            className="min-h-[180px] resize-y"
            placeholder="Study design and methods..."
          />
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Reporting checklist</CardTitle>
          <CardDescription>Select the reporting guideline checklist used for this manuscript.</CardDescription>
        </CardHeader>
        <CardContent>
          <Select value={checklist} onValueChange={setChecklist}>
            <SelectTrigger>
              <SelectValue placeholder="Select checklist" />
            </SelectTrigger>
            <SelectContent>
              {CHECKLIST_OPTIONS.map((opt) => (
                <SelectItem key={opt.value} value={opt.value}>
                  {opt.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Protocol reference</CardTitle>
          <CardDescription>Link or citation to the registered protocol (e.g. trial registry, OSF).</CardDescription>
        </CardHeader>
        <CardContent>
          <Input
            value={protocolRef}
            onChange={(e) => setProtocolRef(e.target.value)}
            placeholder="e.g. ClinicalTrials.gov NCT..., OSF URL..."
          />
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

export default Stage12MethodsWriting;
