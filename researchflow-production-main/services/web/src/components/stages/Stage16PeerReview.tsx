/**
 * Stage 16 - Peer Review (manuscript writing pipeline)
 * Reviewer assignment, comment threads, revision tracking
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
import { Badge } from '@/components/ui/badge';
import { Textarea } from '@/components/ui/textarea';
import { Input } from '@/components/ui/input';
import { Users, MessageSquare, RefreshCw } from 'lucide-react';

interface StageProps {
  workflowId: string;
  manuscriptId?: string;
  onComplete: () => void;
}

export function Stage16PeerReview({
  workflowId,
  manuscriptId,
  onComplete,
}: StageProps) {
  const [reviewers, setReviewers] = useState<string>('');
  const [commentThread, setCommentThread] = useState('');
  const [revisionStatus, setRevisionStatus] = useState<'draft' | 'in_review' | 'revisions_requested'>('draft');

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Users className="h-5 w-5" />
            Reviewer assignment
          </CardTitle>
          <CardDescription>List reviewers (names and roles).</CardDescription>
        </CardHeader>
        <CardContent>
          <Textarea
            value={reviewers}
            onChange={(e) => setReviewers(e.target.value)}
            className="min-h-[80px] resize-y"
            placeholder="Reviewer 1 (methods), Reviewer 2 (stats)..."
          />
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <MessageSquare className="h-5 w-5" />
            Comment threads
          </CardTitle>
          <CardDescription>Reviewer comments and author responses.</CardDescription>
        </CardHeader>
        <CardContent>
          <Textarea
            value={commentThread}
            onChange={(e) => setCommentThread(e.target.value)}
            className="min-h-[160px] resize-y"
            placeholder="Add or view comment threads..."
          />
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center justify-between">
            Revision tracking
            <Badge variant={revisionStatus === 'revisions_requested' ? 'destructive' : 'secondary'}>
              {revisionStatus === 'draft' && 'Draft'}
              {revisionStatus === 'in_review' && 'In review'}
              {revisionStatus === 'revisions_requested' && 'Revisions requested'}
            </Badge>
          </CardTitle>
          <CardDescription>Current revision status.</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex gap-2">
            <Button
              type="button"
              variant={revisionStatus === 'draft' ? 'default' : 'outline'}
              size="sm"
              onClick={() => setRevisionStatus('draft')}
            >
              Draft
            </Button>
            <Button
              type="button"
              variant={revisionStatus === 'in_review' ? 'default' : 'outline'}
              size="sm"
              onClick={() => setRevisionStatus('in_review')}
            >
              In review
            </Button>
            <Button
              type="button"
              variant={revisionStatus === 'revisions_requested' ? 'default' : 'outline'}
              size="sm"
              onClick={() => setRevisionStatus('revisions_requested')}
            >
              Revisions requested
            </Button>
          </div>
        </CardContent>
      </Card>

      <div className="flex justify-end gap-2">
        <Button onClick={onComplete}>
          <RefreshCw className="h-4 w-4 mr-1" />
          Complete Stage
        </Button>
      </div>
    </div>
  );
}

export default Stage16PeerReview;
