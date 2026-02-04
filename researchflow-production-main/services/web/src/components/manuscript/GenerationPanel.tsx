/**
 * GenerationPanel - Trigger and monitor manuscript section generation
 */

import React, { useState, useCallback } from 'react';
import {
  Sparkles,
  FileText,
  Loader2,
  AlertCircle,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Progress } from '@/components/ui/progress';
import { Badge } from '@/components/ui/badge';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { useManuscriptGeneration } from '@/hooks/useManuscriptGeneration';

interface GenerationPanelProps {
  projectId: string;
  onSectionGenerated?: (section: string, content: string) => void;
}

type SectionType = 'abstract' | 'methods' | 'results' | 'discussion' | 'full';
type AbstractStyle = 'structured' | 'unstructured' | 'bmj_structured' | 'consort';

export const GenerationPanel: React.FC<GenerationPanelProps> = ({
  projectId,
  onSectionGenerated,
}) => {
  const [selectedSection, setSelectedSection] = useState<SectionType>('abstract');
  const [abstractStyle, setAbstractStyle] = useState<AbstractStyle>('structured');

  const {
    isGenerating,
    progress,
    currentStep,
    error,
    generateSection,
    cancelGeneration,
  } = useManuscriptGeneration(projectId);

  const handleGenerate = useCallback(async () => {
    try {
      const result = await generateSection(selectedSection, {
        abstractStyle: selectedSection === 'abstract' ? abstractStyle : undefined,
      });

      if (result && onSectionGenerated) {
        onSectionGenerated(selectedSection, result.content);
      }
    } catch (err) {
      console.error('Generation failed:', err);
    }
  }, [selectedSection, abstractStyle, generateSection, onSectionGenerated]);

  const sectionOptions: { value: SectionType; label: string; description: string }[] = [
    { value: 'abstract', label: 'Abstract', description: 'Generate structured abstract' },
    { value: 'methods', label: 'Methods', description: 'Generate methods section' },
    { value: 'results', label: 'Results', description: 'Generate results narrative' },
    { value: 'discussion', label: 'Discussion', description: 'Generate discussion section' },
    { value: 'full', label: 'Full Manuscript', description: 'Generate complete IMRaD manuscript' },
  ];

  return (
    <Card className="w-full">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Sparkles className="h-5 w-5 text-purple-500" />
          AI Manuscript Generation
        </CardTitle>
        <CardDescription>
          Generate manuscript sections from your research data
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Section Selection */}
        <div className="space-y-2">
          <label className="text-sm font-medium">Section to Generate</label>
          <Select
            value={selectedSection}
            onValueChange={(v) => setSelectedSection(v as SectionType)}
            disabled={isGenerating}
          >
            <SelectTrigger>
              <SelectValue placeholder="Select section" />
            </SelectTrigger>
            <SelectContent>
              {sectionOptions.map((option) => (
                <SelectItem key={option.value} value={option.value}>
                  <div className="flex flex-col">
                    <span>{option.label}</span>
                    <span className="text-xs text-muted-foreground">
                      {option.description}
                    </span>
                  </div>
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        {/* Abstract Style (only for abstract) */}
        {selectedSection === 'abstract' && (
          <div className="space-y-2">
            <label className="text-sm font-medium">Abstract Style</label>
            <Select
              value={abstractStyle}
              onValueChange={(v) => setAbstractStyle(v as AbstractStyle)}
              disabled={isGenerating}
            >
              <SelectTrigger>
                <SelectValue placeholder="Select style" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="structured">Structured (IMRAD)</SelectItem>
                <SelectItem value="unstructured">Unstructured</SelectItem>
                <SelectItem value="bmj_structured">BMJ Structured</SelectItem>
                <SelectItem value="consort">CONSORT</SelectItem>
              </SelectContent>
            </Select>
          </div>
        )}

        {/* Progress Display */}
        {isGenerating && (
          <div className="space-y-2">
            <div className="flex items-center justify-between text-sm">
              <span className="text-muted-foreground">{currentStep}</span>
              <span className="font-medium">{progress}%</span>
            </div>
            <Progress value={progress} className="h-2" />
          </div>
        )}

        {/* Error Display */}
        {error && (
          <div className="flex items-center gap-2 p-3 bg-red-50 border border-red-200 rounded-md">
            <AlertCircle className="h-4 w-4 text-red-500" />
            <span className="text-sm text-red-700">{error}</span>
          </div>
        )}

        {/* Action Buttons */}
        <div className="flex gap-2">
          <Button
            onClick={handleGenerate}
            disabled={isGenerating}
            className="flex-1"
          >
            {isGenerating ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Generating...
              </>
            ) : (
              <>
                <FileText className="mr-2 h-4 w-4" />
                Generate {selectedSection === 'full' ? 'Manuscript' : 'Section'}
              </>
            )}
          </Button>

          {isGenerating && (
            <Button variant="outline" onClick={cancelGeneration}>
              Cancel
            </Button>
          )}
        </div>

        {/* Info Badge */}
        <div className="flex items-center gap-2 pt-2">
          <Badge variant="secondary" className="text-xs">
            HTI-1 Compliant
          </Badge>
          <span className="text-xs text-muted-foreground">
            AI transparency logged for all generations
          </span>
        </div>
      </CardContent>
    </Card>
  );
};

export default GenerationPanel;
