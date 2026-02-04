/**
 * Stage 19 - Submission (manuscript writing pipeline)
 * Journal selector, cover letter, submission checklist
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

const JOURNAL_OPTIONS = [
  { value: 'thyroid', label: 'Thyroid' },
  { value: 'jama', label: 'JAMA' },
  { value: 'nejm', label: 'NEJM' },
  { value: 'bmj', label: 'BMJ' },
  { value: 'plos_one', label: 'PLOS ONE' },
  { value: 'other', label: 'Other' },
];

const SUBMISSION_CHECKLIST = [
  { id: 'manuscript', label: 'Manuscript file ready' },
  { id: 'figures', label: 'Figures and tables prepared' },
  { id: 'cover', label: 'Cover letter drafted' },
  { id: 'supplementary', label: 'Supplementary materials (if any) ready' },
  { id: 'author_info', label: 'Author information and affiliations confirmed' },
];

export function Stage19Submission({
  workflowId,
  manuscriptId,
  onComplete,
}: StageProps) {
  const [journal, setJournal] = useState<string>('');
  const [journalOther, setJournalOther] = useState('');
  const [coverLetter, setCoverLetter] = useState('');
  const [checklist, setChecklist] = useState<Record<string, boolean>>(
    SUBMISSION_CHECKLIST.reduce((acc, i) => ({ ...acc, [i.id]: false }), {})
  );

  const toggleChecklist = (id: string) => {
    setChecklist((prev) => ({ ...prev, [id]: !prev[id] }));
  };

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>Journal selector</CardTitle>
          <CardDescription>Select target journal for submission.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-2">
          <Select value={journal} onValueChange={setJournal}>
            <SelectTrigger>
              <SelectValue placeholder="Select journal" />
            </SelectTrigger>
            <SelectContent>
              {JOURNAL_OPTIONS.map((opt) => (
                <SelectItem key={opt.value} value={opt.value}>
                  {opt.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          {journal === 'other' && (
            <Input
              value={journalOther}
              onChange={(e) => setJournalOther(e.target.value)}
              placeholder="Journal name"
              className="mt-2"
            />
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Cover letter</CardTitle>
          <CardDescription>Draft the submission cover letter.</CardDescription>
        </CardHeader>
        <CardContent>
          <Textarea
            value={coverLetter}
            onChange={(e) => setCoverLetter(e.target.value)}
            className="min-h-[200px] resize-y"
            placeholder="Dear Editor, ..."
          />
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Submission checklist</CardTitle>
          <CardDescription>Confirm all items before submitting.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-2">
          {SUBMISSION_CHECKLIST.map((item) => (
            <div key={item.id} className="flex items-center space-x-2">
              <Checkbox
                id={item.id}
                checked={checklist[item.id]}
                onCheckedChange={() => toggleChecklist(item.id)}
              />
              <Label htmlFor={item.id}>{item.label}</Label>
            </div>
          ))}
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

export default Stage19Submission;
