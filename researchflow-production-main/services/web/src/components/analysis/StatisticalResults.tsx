/**
 * Statistical Results Display
 *
 * Comprehensive results display with tabbed interface for statistical analysis outputs,
 * including descriptive statistics, hypothesis tests, assumptions, and interpretations.
 */

import React, { useState, useMemo } from 'react';
import { Download, Eye, EyeOff, Copy, BookOpen, AlertTriangle, CheckCircle, Info, BarChart3 } from 'lucide-react';

import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Badge } from '@/components/ui/badge';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Checkbox } from '@/components/ui/checkbox';
import { Label } from '@/components/ui/label';
import { Separator } from '@/components/ui/separator';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '@/components/ui/collapsible';

import {
  StatisticalAnalysisResult,
  DescriptiveStats,
  HypothesisTestResult,
  AssumptionCheck,
  EffectSize,
  PostHocResult,
  APAFormattedResult,
  ResultsDisplayPreferences
} from '@/types/statistical-analysis';
import { VisualizationRenderer } from './VisualizationRenderer';

interface StatisticalResultsProps {
  /** Analysis results */
  results: StatisticalAnalysisResult;
  /** Display preferences */
  preferences?: Partial<ResultsDisplayPreferences>;
  /** Called when export is requested */
  onExport?: (sections: Record<string, boolean>) => void;
  /** Called when results are copied */
  onCopy?: (content: string, format: 'apa' | 'raw') => void;
}

const DEFAULT_PREFERENCES: ResultsDisplayPreferences = {
  showDescriptive: true,
  showHypothesisTest: true,
  showEffectSizes: true,
  showAssumptions: true,
  showVisualizations: true,
  showAPAText: true,
  visualizationTypes: ['histogram', 'boxplot', 'qq-plot', 'scatter', 'bar']
};

export function StatisticalResults({ 
  results, 
  preferences = {},
  onExport,
  onCopy 
}: StatisticalResultsProps) {
  const [activeTab, setActiveTab] = useState('summary');
  const [expandedSections, setExpandedSections] = useState<Set<string>>(new Set(['main-results']));
  const [displayPrefs, setDisplayPrefs] = useState<ResultsDisplayPreferences>({
    ...DEFAULT_PREFERENCES,
    ...preferences
  });

  // Derived data
  const significantResults = useMemo(() => {
    return results.hypothesisTest.significant;
  }, [results]);

  const assumptionViolations = useMemo(() => {
    return results.assumptions.filter(a => !a.passed);
  }, [results]);

  const hasWarnings = useMemo(() => {
    return results.warnings.length > 0 || assumptionViolations.length > 0;
  }, [results.warnings, assumptionViolations]);

  // Format numbers consistently
  const formatNumber = (value: number, decimals = 3) => {
    return value.toFixed(decimals);
  };

  const formatPValue = (pValue: number) => {
    if (pValue < 0.001) return 'p < 0.001';
    return `p = ${formatNumber(pValue)}`;
  };

  // Toggle section expansion
  const toggleSection = (sectionId: string) => {
    setExpandedSections(prev => {
      const newSet = new Set(prev);
      if (newSet.has(sectionId)) {
        newSet.delete(sectionId);
      } else {
        newSet.add(sectionId);
      }
      return newSet;
    });
  };

  // Update display preferences
  const updatePreferences = (updates: Partial<ResultsDisplayPreferences>) => {
    setDisplayPrefs(prev => ({ ...prev, ...updates }));
  };

  // Copy results to clipboard
  const copyResults = (format: 'apa' | 'raw') => {
    if (format === 'apa') {
      const apaText = results.apaFormatted
        .filter(section => displayPrefs[`show${section.section.charAt(0).toUpperCase() + section.section.slice(1)}` as keyof ResultsDisplayPreferences])
        .map(section => section.text)
        .join('\n\n');
      
      navigator.clipboard.writeText(apaText);
      onCopy?.(apaText, 'apa');
    } else {
      const rawText = JSON.stringify(results, null, 2);
      navigator.clipboard.writeText(rawText);
      onCopy?.(rawText, 'raw');
    }
  };

  // Render descriptive statistics table
  const renderDescriptiveStats = () => (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <BarChart3 className="h-5 w-5" />
          Descriptive Statistics
        </CardTitle>
      </CardHeader>
      <CardContent>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Variable</TableHead>
              <TableHead className="text-right">N</TableHead>
              <TableHead className="text-right">Mean</TableHead>
              <TableHead className="text-right">SD</TableHead>
              <TableHead className="text-right">Median</TableHead>
              <TableHead className="text-right">Min</TableHead>
              <TableHead className="text-right">Max</TableHead>
              <TableHead className="text-right">95% CI</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {results.descriptiveStats.map((stats: DescriptiveStats) => (
              <TableRow key={stats.variable}>
                <TableCell className="font-medium">{stats.variable}</TableCell>
                <TableCell className="text-right">{stats.n}</TableCell>
                <TableCell className="text-right">{formatNumber(stats.mean)}</TableCell>
                <TableCell className="text-right">{formatNumber(stats.sd)}</TableCell>
                <TableCell className="text-right">{formatNumber(stats.median)}</TableCell>
                <TableCell className="text-right">{formatNumber(stats.min)}</TableCell>
                <TableCell className="text-right">{formatNumber(stats.max)}</TableCell>
                <TableCell className="text-right">
                  [{formatNumber(stats.ci95[0])}, {formatNumber(stats.ci95[1])}]
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </CardContent>
    </Card>
  );

  // Render hypothesis test results
  const renderHypothesisTest = () => {
    const test = results.hypothesisTest;
    
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center justify-between">
            <span className="flex items-center gap-2">
              {test.significant ? (
                <CheckCircle className="h-5 w-5 text-green-600" />
              ) : (
                <AlertTriangle className="h-5 w-5 text-gray-500" />
              )}
              Hypothesis Test Results
            </span>
            <Badge variant={test.significant ? "default" : "outline"}>
              {test.significant ? 'Significant' : 'Not Significant'}
            </Badge>
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* Main test statistics */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="text-center p-3 bg-gray-50 rounded">
              <div className="text-sm text-gray-500">Test Statistic</div>
              <div className="text-lg font-semibold">
                {test.statisticName} = {formatNumber(test.statistic)}
              </div>
            </div>
            
            <div className="text-center p-3 bg-gray-50 rounded">
              <div className="text-sm text-gray-500">P-value</div>
              <div className={`text-lg font-semibold ${test.significant ? 'text-green-600' : 'text-gray-600'}`}>
                {formatPValue(test.pValue)}
              </div>
            </div>

            <div className="text-center p-3 bg-gray-50 rounded">
              <div className="text-sm text-gray-500">Degrees of Freedom</div>
              <div className="text-lg font-semibold">
                {Array.isArray(test.degreesOfFreedom) 
                  ? `${test.degreesOfFreedom[0]}, ${test.degreesOfFreedom[1]}`
                  : test.degreesOfFreedom
                }
              </div>
            </div>

            {test.confidenceInterval && (
              <div className="text-center p-3 bg-gray-50 rounded">
                <div className="text-sm text-gray-500">95% CI</div>
                <div className="text-lg font-semibold">
                  [{formatNumber(test.confidenceInterval[0])}, {formatNumber(test.confidenceInterval[1])}]
                </div>
              </div>
            )}
          </div>

          {/* Effect size */}
          {test.effectSize && displayPrefs.showEffectSizes && (
            <div className="border-t pt-4">
              <h4 className="font-medium mb-3">Effect Size</h4>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div className="text-center p-3 bg-blue-50 rounded">
                  <div className="text-sm text-gray-600">{test.effectSize.name}</div>
                  <div className="text-lg font-semibold text-blue-600">
                    {formatNumber(test.effectSize.value)}
                  </div>
                  <div className="text-xs text-gray-500 mt-1">
                    ({test.effectSize.interpretation})
                  </div>
                </div>
                
                {test.effectSize.confidenceInterval && (
                  <div className="text-center p-3 bg-blue-50 rounded">
                    <div className="text-sm text-gray-600">95% CI</div>
                    <div className="text-lg font-semibold text-blue-600">
                      [{formatNumber(test.effectSize.confidenceInterval[0])}, {formatNumber(test.effectSize.confidenceInterval[1])}]
                    </div>
                  </div>
                )}

                <div className="text-center p-3 bg-blue-50 rounded">
                  <div className="text-sm text-gray-600">Guidelines</div>
                  <div className="text-xs text-gray-500">
                    {test.effectSize.guidelines}
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Post-hoc tests */}
          {test.postHoc && test.postHoc.length > 0 && (
            <div className="border-t pt-4">
              <h4 className="font-medium mb-3">Post-hoc Comparisons</h4>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Comparison</TableHead>
                    <TableHead className="text-right">Mean Diff</TableHead>
                    <TableHead className="text-right">SE</TableHead>
                    <TableHead className="text-right">p-value</TableHead>
                    <TableHead className="text-right">Adj. p-value</TableHead>
                    <TableHead className="text-right">95% CI</TableHead>
                    <TableHead>Significant</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {test.postHoc.map((comparison: PostHocResult, index) => (
                    <TableRow key={index}>
                      <TableCell>{comparison.group1} vs {comparison.group2}</TableCell>
                      <TableCell className="text-right">{formatNumber(comparison.meanDifference)}</TableCell>
                      <TableCell className="text-right">{formatNumber(comparison.standardError)}</TableCell>
                      <TableCell className="text-right">{formatPValue(comparison.pValue)}</TableCell>
                      <TableCell className="text-right">{formatPValue(comparison.adjustedPValue)}</TableCell>
                      <TableCell className="text-right">
                        [{formatNumber(comparison.confidenceInterval[0])}, {formatNumber(comparison.confidenceInterval[1])}]
                      </TableCell>
                      <TableCell>
                        <Badge variant={comparison.significant ? "default" : "outline"}>
                          {comparison.significant ? 'Yes' : 'No'}
                        </Badge>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          )}
        </CardContent>
      </Card>
    );
  };

  // Render assumption checks
  const renderAssumptions = () => (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <CheckCircle className="h-5 w-5" />
          Statistical Assumptions
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          {results.assumptions.map((assumption: AssumptionCheck, index) => (
            <div key={index} className="border rounded-lg p-4">
              <div className="flex items-start justify-between mb-2">
                <div>
                  <h4 className="font-medium flex items-center gap-2">
                    {assumption.passed ? (
                      <CheckCircle className="h-4 w-4 text-green-600" />
                    ) : (
                      <AlertTriangle className="h-4 w-4 text-orange-500" />
                    )}
                    {assumption.name}
                  </h4>
                  <p className="text-sm text-gray-600">{assumption.description}</p>
                </div>
                <Badge variant={assumption.passed ? "default" : "destructive"}>
                  {assumption.passed ? 'Met' : 'Violated'}
                </Badge>
              </div>

              <div className="space-y-2">
                <p className="text-sm">{assumption.interpretation}</p>
                
                {assumption.statistic !== undefined && assumption.pValue !== undefined && (
                  <div className="text-sm text-gray-500">
                    Test statistic: {formatNumber(assumption.statistic)}, {formatPValue(assumption.pValue)}
                  </div>
                )}

                {assumption.recommendation && (
                  <Alert className="mt-3">
                    <Info className="h-4 w-4" />
                    <AlertDescription>
                      {assumption.recommendation}
                    </AlertDescription>
                  </Alert>
                )}
              </div>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );

  // Render APA formatted results
  const renderAPAResults = () => (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center justify-between">
          <span className="flex items-center gap-2">
            <BookOpen className="h-5 w-5" />
            APA Formatted Results
          </span>
          <div className="flex gap-2">
            <Button variant="outline" size="sm" onClick={() => copyResults('apa')}>
              <Copy className="h-4 w-4 mr-1" />
              Copy APA
            </Button>
          </div>
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-6">
          {results.apaFormatted.map((section: APAFormattedResult, index) => (
            <Collapsible key={index}>
              <CollapsibleTrigger className="flex items-center justify-between w-full p-3 bg-gray-50 rounded hover:bg-gray-100">
                <span className="font-medium capitalize">
                  {section.section.replace('-', ' ')} Statistics
                </span>
                <div className="flex items-center gap-2">
                  <Checkbox 
                    checked={section.includeInManuscript}
                    onChange={(checked) => {
                      // Update section inclusion
                    }}
                  />
                  <Label className="text-xs">Include in manuscript</Label>
                </div>
              </CollapsibleTrigger>
              <CollapsibleContent className="p-4 border border-t-0 rounded-b">
                <div className="font-mono text-sm whitespace-pre-wrap bg-white p-3 border rounded">
                  {section.text}
                </div>
              </CollapsibleContent>
            </Collapsible>
          ))}
        </div>
      </CardContent>
    </Card>
  );

  return (
    <div className="space-y-6">
      {/* Results Header */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="flex items-center gap-2">
                {significantResults ? (
                  <CheckCircle className="h-6 w-6 text-green-600" />
                ) : (
                  <AlertTriangle className="h-6 w-6 text-gray-500" />
                )}
                Analysis Results
              </CardTitle>
              <div className="flex items-center gap-4 text-sm text-gray-500">
                <span>Duration: {(results.duration / 1000).toFixed(2)}s</span>
                <span>•</span>
                <span>Completed: {new Date(results.createdAt).toLocaleString()}</span>
                <span>•</span>
                <span>ID: {results.id}</span>
              </div>
            </div>
            <div className="flex gap-2">
              <Button 
                variant="outline" 
                onClick={() => onExport?.({
                  descriptiveStats: displayPrefs.showDescriptive,
                  hypothesisTest: displayPrefs.showHypothesisTest,
                  effectSizes: displayPrefs.showEffectSizes,
                  assumptions: displayPrefs.showAssumptions,
                  visualizations: displayPrefs.showVisualizations,
                  apaText: displayPrefs.showAPAText
                })}
              >
                <Download className="h-4 w-4 mr-1" />
                Export
              </Button>
            </div>
          </div>
        </CardHeader>
      </Card>

      {/* Warnings */}
      {hasWarnings && (
        <Alert variant="destructive">
          <AlertTriangle className="h-4 w-4" />
          <AlertTitle>Analysis Warnings</AlertTitle>
          <AlertDescription>
            <div className="space-y-1">
              {assumptionViolations.map((violation, index) => (
                <div key={index}>• {violation.name}: {violation.recommendation}</div>
              ))}
              {results.warnings.map((warning, index) => (
                <div key={index}>• {warning}</div>
              ))}
            </div>
          </AlertDescription>
        </Alert>
      )}

      {/* Results Tabs */}
      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList className="grid grid-cols-5 w-full">
          <TabsTrigger value="summary">Summary</TabsTrigger>
          <TabsTrigger value="descriptive" disabled={!displayPrefs.showDescriptive}>
            Descriptive
          </TabsTrigger>
          <TabsTrigger value="inferential" disabled={!displayPrefs.showHypothesisTest}>
            Inferential
          </TabsTrigger>
          <TabsTrigger value="assumptions" disabled={!displayPrefs.showAssumptions}>
            Assumptions
          </TabsTrigger>
          <TabsTrigger value="visualization" disabled={!displayPrefs.showVisualizations}>
            Visualizations
          </TabsTrigger>
        </TabsList>

        {/* Summary Tab */}
        <TabsContent value="summary" className="space-y-4">
          {/* Key Findings */}
          <Card>
            <CardHeader>
              <CardTitle>Key Findings</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                <div className="p-4 bg-gray-50 rounded-lg">
                  <h4 className="font-medium mb-2">Interpretation</h4>
                  <p className="text-sm">{results.interpretation}</p>
                </div>

                {results.recommendations.length > 0 && (
                  <div className="p-4 bg-blue-50 rounded-lg">
                    <h4 className="font-medium mb-2">Recommendations</h4>
                    <ul className="text-sm space-y-1">
                      {results.recommendations.map((rec, index) => (
                        <li key={index} className="flex items-start gap-2">
                          <span>•</span>
                          <span>{rec}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}

                {/* Quick stats grid */}
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4 pt-4 border-t">
                  <div className="text-center">
                    <div className="text-2xl font-bold text-blue-600">
                      {formatPValue(results.hypothesisTest.pValue)}
                    </div>
                    <div className="text-sm text-gray-500">P-value</div>
                  </div>
                  
                  {results.hypothesisTest.effectSize && (
                    <div className="text-center">
                      <div className="text-2xl font-bold text-green-600">
                        {formatNumber(results.hypothesisTest.effectSize.value)}
                      </div>
                      <div className="text-sm text-gray-500">
                        {results.hypothesisTest.effectSize.name}
                      </div>
                    </div>
                  )}

                  <div className="text-center">
                    <div className="text-2xl font-bold text-purple-600">
                      {results.assumptions.filter(a => a.passed).length}/{results.assumptions.length}
                    </div>
                    <div className="text-sm text-gray-500">Assumptions Met</div>
                  </div>

                  <div className="text-center">
                    <div className="text-2xl font-bold text-orange-600">
                      {results.descriptiveStats.reduce((sum, stat) => sum + stat.n, 0)}
                    </div>
                    <div className="text-sm text-gray-500">Total N</div>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* APA Results Preview */}
          {displayPrefs.showAPAText && renderAPAResults()}
        </TabsContent>

        {/* Descriptive Tab */}
        <TabsContent value="descriptive">
          {displayPrefs.showDescriptive && renderDescriptiveStats()}
        </TabsContent>

        {/* Inferential Tab */}
        <TabsContent value="inferential">
          {displayPrefs.showHypothesisTest && renderHypothesisTest()}
        </TabsContent>

        {/* Assumptions Tab */}
        <TabsContent value="assumptions">
          {displayPrefs.showAssumptions && renderAssumptions()}
        </TabsContent>

        {/* Visualizations Tab */}
        <TabsContent value="visualization">
          {displayPrefs.showVisualizations && (
            <VisualizationRenderer 
              visualizations={results.visualizations}
              preferences={{
                types: displayPrefs.visualizationTypes,
                showAll: true
              }}
            />
          )}
        </TabsContent>
      </Tabs>
    </div>
  );
}

export default StatisticalResults;