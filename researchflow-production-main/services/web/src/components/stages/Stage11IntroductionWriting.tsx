/**
 * Stage 11 - Introduction Writing (manuscript writing pipeline)
 * Research questions, literature context, AI generation, rich text editor
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
import { Sparkles, Save, Check } from 'lucide-react';

export interface IntroDraft {
  researchQuestions: string;
  literatureContext: string;
  introContent: string;
}

interface StageProps {
  workflowId: string;
  manuscriptId?: string;
  onComplete: () => void;
  onSave?: (data: IntroDraft) => void;
}

export function Stage11IntroductionWriting({
  workflowId,
  manuscriptId,
  onComplete,
  onSave,
}: StageProps) {
  const [researchQuestions, setResearchQuestions] = useState('');
  const [literatureContext, setLiteratureContext] = useState('');
  const [introContent, setIntroContent] = useState('');
  const [isGenerating, setIsGenerating] = useState(false);

  const handleSave = () => {
    if (onSave) {
      onSave({ researchQuestions, literatureContext, introContent });
    }
  };

  const handleGenerateAI = () => {
    setIsGenerating(true);
    // Placeholder: parent can wire to manuscript generation API
    setTimeout(() => {
      setIntroContent((prev) =>
        prev
          ? prev + '\n\n[AI-generated paragraph placeholder]'
          : '[AI-generated introduction placeholder based on research questions and literature context]'
      );
      setIsGenerating(false);
    }, 800);
  };

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>Research questions</CardTitle>
          <CardDescription>Define the main questions this manuscript addresses.</CardDescription>
        </CardHeader>
        <CardContent>
          <Textarea
            value={researchQuestions}
            onChange={(e) => setResearchQuestions(e.target.value)}
            className="min-h-[100px] resize-y"
            placeholder="e.g. What is the association between X and Y?"
          />
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Literature context</CardTitle>
          <CardDescription>Brief context from prior literature to frame the introduction.</CardDescription>
        </CardHeader>
        <CardContent>
          <Textarea
            value={literatureContext}
            onChange={(e) => setLiteratureContext(e.target.value)}
            className="min-h-[100px] resize-y"
            placeholder="Summarize relevant prior work and gaps..."
          />
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center justify-between">
            Introduction (rich text)
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={handleGenerateAI}
              disabled={isGenerating}
            >
              <Sparkles className="h-4 w-4 mr-1" />
              {isGenerating ? 'Generating...' : 'Generate with AI'}
            </Button>
          </CardTitle>
          <CardDescription>Draft the introduction section. Use AI to generate a first pass from questions and context.</CardDescription>
        </CardHeader>
        <CardContent>
          <Textarea
            value={introContent}
            onChange={(e) => setIntroContent(e.target.value)}
            className="min-h-[200px] resize-y"
            placeholder="Introduction content (rich text area)..."
          />
        </CardContent>
      </Card>

      <div className="flex justify-end gap-2">
        <Button variant="outline" type="button" onClick={handleSave}>
          <Save className="h-4 w-4 mr-1" />
          Save draft
        </Button>
        <Button onClick={onComplete}>
          <Check className="h-4 w-4 mr-1" />
          Complete Stage
        </Button>
      </div>
    </div>
  );
}

export default Stage11IntroductionWriting;
