/**
 * Stage 14 - Discussion Writing (manuscript writing pipeline)
 * Key findings, limitations, implications
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
import { Check } from 'lucide-react';

interface StageProps {
  workflowId: string;
  manuscriptId?: string;
  onComplete: () => void;
}

export function Stage14DiscussionWriting({
  workflowId,
  manuscriptId,
  onComplete,
}: StageProps) {
  const [keyFindings, setKeyFindings] = useState('');
  const [limitations, setLimitations] = useState('');
  const [implications, setImplications] = useState('');

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>Key findings</CardTitle>
          <CardDescription>Summarize the main results and how they answer the research questions.</CardDescription>
        </CardHeader>
        <CardContent>
          <Textarea
            value={keyFindings}
            onChange={(e) => setKeyFindings(e.target.value)}
            className="min-h-[120px] resize-y"
            placeholder="Key findings..."
          />
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Limitations</CardTitle>
          <CardDescription>Describe study limitations and generalizability.</CardDescription>
        </CardHeader>
        <CardContent>
          <Textarea
            value={limitations}
            onChange={(e) => setLimitations(e.target.value)}
            className="min-h-[120px] resize-y"
            placeholder="Limitations..."
          />
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Implications</CardTitle>
          <CardDescription>Clinical, policy, or research implications.</CardDescription>
        </CardHeader>
        <CardContent>
          <Textarea
            value={implications}
            onChange={(e) => setImplications(e.target.value)}
            className="min-h-[120px] resize-y"
            placeholder="Implications..."
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

export default Stage14DiscussionWriting;
