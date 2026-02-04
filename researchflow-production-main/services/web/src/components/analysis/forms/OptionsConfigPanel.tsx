import React, { useState, useCallback, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Label } from '@/components/ui/label';
import { Input } from '@/components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Switch } from '@/components/ui/switch';
import { Slider } from '@/components/ui/slider';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { 
  Settings, 
  ArrowLeft, 
  Play, 
  Info, 
  CheckCircle,
  AlertCircle,
  Sparkles,
  Target,
  BarChart3,
  FileText
} from 'lucide-react';
import { TestType, AnalysisOptions } from '@/types/statistical-analysis';

interface OptionsConfigPanelProps {
  options: AnalysisOptions;
  onChange: (options: AnalysisOptions) => void;
  testType: TestType;
  onRunAnalysis: () => void;
  onBack: () => void;
  loading: boolean;
}

const TEST_SPECIFIC_CONFIG = {
  [TestType.T_TEST_INDEPENDENT]: {
    name: 'Independent t-test',
    assumptions: ['Normality', 'Homogeneity of variance', 'Independence'],
    effectSizes: ['Cohen\\'s d', 'Hedges\\' g', 'Glass\\'s delta'],
    postHocOptions: [],
    powerAnalysisAvailable: true,
    clinicalSignificanceRelevant: true
  },
  [TestType.T_TEST_PAIRED]: {
    name: 'Paired t-test',
    assumptions: ['Normality of differences', 'Independence of pairs'],
    effectSizes: ['Cohen\\'s d (paired)', 'Hedges\\' g'],
    postHocOptions: [],
    powerAnalysisAvailable: true,
    clinicalSignificanceRelevant: true
  },
  [TestType.MANN_WHITNEY]: {
    name: 'Mann-Whitney U test',
    assumptions: ['Independence', 'Similar distribution shapes'],
    effectSizes: ['Rank-biserial correlation', 'Common language effect size'],
    postHocOptions: [],
    powerAnalysisAvailable: false,
    clinicalSignificanceRelevant: true
  },
  [TestType.ANOVA_ONEWAY]: {
    name: 'One-way ANOVA',
    assumptions: ['Normality within groups', 'Homogeneity of variance', 'Independence'],
    effectSizes: ['Eta-squared', 'Omega-squared'],
    postHocOptions: ['tukey', 'bonferroni', 'scheffe'],
    powerAnalysisAvailable: true,
    clinicalSignificanceRelevant: true
  },
  [TestType.KRUSKAL_WALLIS]: {
    name: 'Kruskal-Wallis test',
    assumptions: ['Independence', 'Similar distribution shapes'],
    effectSizes: ['Epsilon-squared'],
    postHocOptions: ['dunn'],
    powerAnalysisAvailable: false,
    clinicalSignificanceRelevant: true
  },
  [TestType.CHI_SQUARE]: {
    name: 'Chi-square test',
    assumptions: ['Expected cell counts ≥ 5', 'Independence'],
    effectSizes: ['Cramér\\'s V', 'Phi coefficient'],
    postHocOptions: [],
    powerAnalysisAvailable: false,
    clinicalSignificanceRelevant: false
  },
  [TestType.FISHER_EXACT]: {
    name: 'Fisher\\'s exact test',
    assumptions: ['Independence', '2x2 contingency table'],
    effectSizes: ['Odds ratio'],
    postHocOptions: [],
    powerAnalysisAvailable: false,
    clinicalSignificanceRelevant: false
  },
  [TestType.CORRELATION_PEARSON]: {
    name: 'Pearson correlation',
    assumptions: ['Normality', 'Linear relationship', 'Homoscedasticity'],
    effectSizes: ['Pearson r', 'R-squared'],
    postHocOptions: [],
    powerAnalysisAvailable: true,
    clinicalSignificanceRelevant: false
  },
  [TestType.CORRELATION_SPEARMAN]: {
    name: 'Spearman correlation',
    assumptions: ['Monotonic relationship', 'Independence'],
    effectSizes: ['Spearman rho'],
    postHocOptions: [],
    powerAnalysisAvailable: false,
    clinicalSignificanceRelevant: false
  }
};

const MULTIPLE_COMPARISON_OPTIONS = [
  { value: 'none', label: 'None', description: 'No correction applied' },
  { value: 'benjamini_hochberg', label: 'Benjamini-Hochberg', description: 'False Discovery Rate control (recommended)' },
  { value: 'bonferroni', label: 'Bonferroni', description: 'Conservative family-wise error control' },
  { value: 'holm', label: 'Holm-Bonferroni', description: 'Step-down method, more powerful than Bonferroni' },
  { value: 'sidak', label: 'Šidák', description: 'More accurate than Bonferroni for independent tests' }
];

const CLINICAL_DOMAINS = [
  { value: 'general', label: 'General Medicine', description: 'Standard Cohen\\'s conventions' },
  { value: 'psychology', label: 'Psychology', description: 'Psychological research standards' },
  { value: 'cardiology', label: 'Cardiology', description: 'More conservative thresholds' },
  { value: 'education', label: 'Education', description: 'Educational research standards' }
];

export function OptionsConfigPanel({ 
  options, 
  onChange, 
  testType, 
  onRunAnalysis, 
  onBack, 
  loading 
}: OptionsConfigPanelProps) {
  const [expandedSections, setExpandedSections] = useState({
    basic: true,
    advanced: false,
    clinical: false,
    output: false
  });

  const testConfig = TEST_SPECIFIC_CONFIG[testType];

  const updateOption = useCallback(<K extends keyof AnalysisOptions>(
    key: K, 
    value: AnalysisOptions[K]
  ) => {
    onChange({ ...options, [key]: value });
  }, [options, onChange]);

  const toggleSection = useCallback((section: keyof typeof expandedSections) => {
    setExpandedSections(prev => ({ ...prev, [section]: !prev[section] }));
  }, []);

  // Auto-enable/disable features based on test type
  useEffect(() => {
    if (!testConfig.powerAnalysisAvailable && options.powerAnalysis) {
      updateOption('powerAnalysis', false);
    }
    if (!testConfig.clinicalSignificanceRelevant && options.clinicalSignificance.enabled) {
      updateOption('clinicalSignificance', { ...options.clinicalSignificance, enabled: false });
    }
    if (testConfig.postHocOptions.length === 0 && options.postHocTests !== 'none') {
      updateOption('postHocTests', 'none');
    }
  }, [testType, testConfig, options, updateOption]);

  const getRecommendedSettings = () => {
    const recommendations: string[] = [];
    
    if (options.alpha !== 0.05) {
      recommendations.push('Consider using α = 0.05 (standard in most fields)');
    }
    
    if (!options.effectSizeCalculation) {
      recommendations.push('Enable effect size calculation for clinical interpretation');
    }
    
    if (!options.assumptionChecking) {
      recommendations.push('Enable assumption checking for statistical validity');
    }
    
    if (testConfig.postHocOptions.length > 0 && options.postHocTests === 'none') {
      recommendations.push('Consider post-hoc tests for pairwise comparisons');
    }
    
    if (options.multipleComparisonCorrection === 'none' && testConfig.postHocOptions.length > 0) {
      recommendations.push('Apply multiple comparison correction to control Type I error');
    }
    
    return recommendations;
  };

  const recommendations = getRecommendedSettings();

  return (
    <div className=\"space-y-6\">
      {/* Test Overview */}
      <Card>
        <CardHeader>
          <CardTitle className=\"flex items-center gap-2\">
            <Target className=\"h-5 w-5\" />
            {testConfig.name} Configuration
          </CardTitle>
        </CardHeader>
        <CardContent className=\"space-y-4\">
          <div className=\"grid md:grid-cols-2 gap-4\">
            <div>
              <h4 className=\"font-medium mb-2\">Statistical Assumptions</h4>
              <ul className=\"space-y-1\">
                {testConfig.assumptions.map((assumption, index) => (
                  <li key={index} className=\"flex items-center gap-2 text-sm\">
                    <div className=\"h-1.5 w-1.5 bg-blue-500 rounded-full\" />
                    {assumption}
                  </li>
                ))}
              </ul>
            </div>
            <div>
              <h4 className=\"font-medium mb-2\">Available Effect Sizes</h4>
              <div className=\"flex flex-wrap gap-1\">
                {testConfig.effectSizes.map((effect, index) => (
                  <Badge key={index} variant=\"secondary\" className=\"text-xs\">
                    {effect}
                  </Badge>
                ))}
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Recommendations */}
      {recommendations.length > 0 && (
        <Alert>
          <Sparkles className=\"h-4 w-4\" />
          <AlertDescription>
            <strong>AI Recommendations:</strong>
            <ul className=\"mt-2 space-y-1\">
              {recommendations.map((rec, index) => (
                <li key={index} className=\"text-sm\">• {rec}</li>
              ))}
            </ul>
          </AlertDescription>
        </Alert>
      )}

      {/* Basic Settings */}
      <Card>
        <CardHeader className=\"cursor-pointer\" onClick={() => toggleSection('basic')}>
          <CardTitle className=\"flex items-center justify-between\">
            <span className=\"flex items-center gap-2\">
              <Settings className=\"h-5 w-5\" />
              Basic Settings
            </span>
            <Badge>{expandedSections.basic ? 'Collapse' : 'Expand'}</Badge>
          </CardTitle>
        </CardHeader>
        {expandedSections.basic && (
          <CardContent className=\"space-y-6\">
            {/* Alpha Level */}
            <div className=\"space-y-2\">
              <Label htmlFor=\"alpha\">Significance Level (α)</Label>
              <div className=\"flex items-center gap-4\">
                <Slider
                  id=\"alpha\"
                  min={0.001}
                  max={0.10}
                  step={0.001}
                  value={[options.alpha]}
                  onValueChange={([value]) => updateOption('alpha', value)}
                  className=\"flex-1\"
                />
                <div className=\"w-20\">
                  <Input
                    type=\"number\"
                    value={options.alpha}
                    onChange={(e) => updateOption('alpha', parseFloat(e.target.value) || 0.05)}
                    min={0.001}
                    max={0.10}
                    step={0.001}
                    className=\"text-center\"
                  />
                </div>
              </div>
              <div className=\"text-xs text-gray-600\">
                Lower values require stronger evidence for significance (α = 0.05 is standard)
              </div>
            </div>

            {/* Confidence Level */}
            <div className=\"space-y-2\">
              <Label htmlFor=\"confidence\">Confidence Level</Label>
              <Select value={options.confidenceLevel.toString()} onValueChange={(value) => updateOption('confidenceLevel', parseFloat(value))}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value=\"0.90\">90% (α = 0.10)</SelectItem>
                  <SelectItem value=\"0.95\">95% (α = 0.05) - Standard</SelectItem>
                  <SelectItem value=\"0.99\">99% (α = 0.01)</SelectItem>
                </SelectContent>
              </Select>
            </div>

            {/* Core Features */}
            <div className=\"space-y-4\">
              <div className=\"flex items-center justify-between\">
                <div>
                  <Label htmlFor=\"effect-size\">Calculate Effect Sizes</Label>
                  <div className=\"text-sm text-gray-600\">Essential for clinical interpretation</div>
                </div>
                <Switch
                  id=\"effect-size\"
                  checked={options.effectSizeCalculation}
                  onCheckedChange={(checked) => updateOption('effectSizeCalculation', checked)}
                />
              </div>

              <div className=\"flex items-center justify-between\">
                <div>
                  <Label htmlFor=\"assumptions\">Check Statistical Assumptions</Label>
                  <div className=\"text-sm text-gray-600\">Validates test appropriateness</div>
                </div>
                <Switch
                  id=\"assumptions\"
                  checked={options.assumptionChecking}
                  onCheckedChange={(checked) => updateOption('assumptionChecking', checked)}
                />
              </div>

              {testConfig.powerAnalysisAvailable && (
                <div className=\"flex items-center justify-between\">
                  <div>
                    <Label htmlFor=\"power\">Power Analysis</Label>
                    <div className=\"text-sm text-gray-600\">Sample size recommendations</div>
                  </div>
                  <Switch
                    id=\"power\"
                    checked={options.powerAnalysis}
                    onCheckedChange={(checked) => updateOption('powerAnalysis', checked)}
                  />
                </div>
              )}
            </div>
          </CardContent>
        )}
      </Card>

      {/* Advanced Settings */}
      <Card>
        <CardHeader className=\"cursor-pointer\" onClick={() => toggleSection('advanced')}>
          <CardTitle className=\"flex items-center justify-between\">
            <span className=\"flex items-center gap-2\">
              <BarChart3 className=\"h-5 w-5\" />
              Advanced Settings
            </span>
            <Badge variant=\"outline\">{expandedSections.advanced ? 'Collapse' : 'Expand'}</Badge>
          </CardTitle>
        </CardHeader>
        {expandedSections.advanced && (
          <CardContent className=\"space-y-6\">
            {/* Post-hoc Tests */}
            {testConfig.postHocOptions.length > 0 && (
              <div className=\"space-y-2\">
                <Label htmlFor=\"posthoc\">Post-hoc Tests</Label>
                <Select value={options.postHocTests} onValueChange={(value: any) => updateOption('postHocTests', value)}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value=\"auto\">Automatic (recommended)</SelectItem>
                    <SelectItem value=\"tukey\">Tukey HSD</SelectItem>
                    <SelectItem value=\"bonferroni\">Bonferroni</SelectItem>
                    {testType === TestType.KRUSKAL_WALLIS && (
                      <SelectItem value=\"dunn\">Dunn test</SelectItem>
                    )}
                    <SelectItem value=\"none\">None</SelectItem>
                  </SelectContent>
                </Select>
                <div className=\"text-xs text-gray-600\">
                  Post-hoc tests identify which specific groups differ significantly
                </div>
              </div>
            )}

            {/* Multiple Comparison Correction */}
            <div className=\"space-y-2\">
              <Label htmlFor=\"correction\">Multiple Comparison Correction</Label>
              <Select 
                value={options.multipleComparisonCorrection} 
                onValueChange={(value: any) => updateOption('multipleComparisonCorrection', value)}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {MULTIPLE_COMPARISON_OPTIONS.map((option) => (
                    <SelectItem key={option.value} value={option.value}>
                      <div>
                        <div className=\"font-medium\">{option.label}</div>
                        <div className=\"text-xs text-gray-600\">{option.description}</div>
                      </div>
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            {/* Visualizations */}
            <div className=\"space-y-3\">
              <Label>Visualizations</Label>
              <div className=\"space-y-2\">
                {[
                  { id: 'qq_plot', label: 'Q-Q Plot', description: 'Assess normality assumption' },
                  { id: 'histogram', label: 'Histogram', description: 'Show data distribution' },
                  { id: 'boxplot', label: 'Box Plot', description: 'Compare group distributions' },
                  { id: 'scatter', label: 'Scatter Plot', description: 'For correlation analysis' }
                ].map((viz) => (
                  <div key={viz.id} className=\"flex items-center justify-between\">
                    <div>
                      <div className=\"font-medium text-sm\">{viz.label}</div>
                      <div className=\"text-xs text-gray-600\">{viz.description}</div>
                    </div>
                    <Switch
                      checked={options.visualizations.includes(viz.id)}
                      onCheckedChange={(checked) => {
                        if (checked) {
                          updateOption('visualizations', [...options.visualizations, viz.id]);
                        } else {
                          updateOption('visualizations', options.visualizations.filter(v => v !== viz.id));
                        }
                      }}
                    />
                  </div>
                ))}
              </div>
            </div>
          </CardContent>
        )}
      </Card>

      {/* Clinical Significance */}
      {testConfig.clinicalSignificanceRelevant && (
        <Card>
          <CardHeader className=\"cursor-pointer\" onClick={() => toggleSection('clinical')}>
            <CardTitle className=\"flex items-center justify-between\">
              <span className=\"flex items-center gap-2\">
                <Target className=\"h-5 w-5\" />
                Clinical Significance
              </span>
              <Badge variant=\"outline\">{expandedSections.clinical ? 'Collapse' : 'Expand'}</Badge>
            </CardTitle>
          </CardHeader>
          {expandedSections.clinical && (
            <CardContent className=\"space-y-6\">
              <div className=\"flex items-center justify-between\">
                <div>
                  <Label htmlFor=\"clinical-enabled\">Enable Clinical Significance Assessment</Label>
                  <div className=\"text-sm text-gray-600\">Evaluate practical importance beyond statistical significance</div>
                </div>
                <Switch
                  id=\"clinical-enabled\"
                  checked={options.clinicalSignificance.enabled}
                  onCheckedChange={(checked) => 
                    updateOption('clinicalSignificance', { ...options.clinicalSignificance, enabled: checked })
                  }
                />
              </div>

              {options.clinicalSignificance.enabled && (
                <>
                  <div className=\"space-y-2\">
                    <Label htmlFor=\"domain\">Clinical Domain</Label>
                    <Select 
                      value={options.clinicalSignificance.domain} 
                      onValueChange={(value) => 
                        updateOption('clinicalSignificance', { ...options.clinicalSignificance, domain: value })
                      }
                    >
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        {CLINICAL_DOMAINS.map((domain) => (
                          <SelectItem key={domain.value} value={domain.value}>
                            <div>
                              <div className=\"font-medium\">{domain.label}</div>
                              <div className=\"text-xs text-gray-600\">{domain.description}</div>
                            </div>
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>

                  <div className=\"space-y-2\">
                    <Label htmlFor=\"mcid\">Minimum Clinically Important Difference (MCID)</Label>
                    <Input
                      id=\"mcid\"
                      type=\"number\"
                      value={options.clinicalSignificance.mcid || ''}
                      onChange={(e) => 
                        updateOption('clinicalSignificance', { 
                          ...options.clinicalSignificance, 
                          mcid: e.target.value ? parseFloat(e.target.value) : undefined 
                        })
                      }
                      placeholder=\"Optional - specify if known\"
                      step=\"0.1\"
                    />
                    <div className=\"text-xs text-gray-600\">
                      If known, specify the smallest change considered clinically meaningful
                    </div>
                  </div>
                </>
              )}
            </CardContent>
          )}
        </Card>
      )}

      {/* Output Formats */}
      <Card>
        <CardHeader className=\"cursor-pointer\" onClick={() => toggleSection('output')}>
          <CardTitle className=\"flex items-center justify-between\">
            <span className=\"flex items-center gap-2\">
              <FileText className=\"h-5 w-5\" />
              Output & Export
            </span>
            <Badge variant=\"outline\">{expandedSections.output ? 'Collapse' : 'Expand'}</Badge>
          </CardTitle>
        </CardHeader>
        {expandedSections.output && (
          <CardContent className=\"space-y-4\">
            <div>
              <Label>Export Formats</Label>
              <div className=\"grid grid-cols-2 gap-2 mt-2\">
                {[
                  { id: 'latex', label: 'LaTeX', description: 'Publication tables' },
                  { id: 'csv', label: 'CSV', description: 'Data analysis' },
                  { id: 'json', label: 'JSON', description: 'Raw data' },
                  { id: 'pdf', label: 'PDF', description: 'Reports' }
                ].map((format) => (
                  <div key={format.id} className=\"flex items-center space-x-2\">
                    <Switch
                      checked={options.exportFormats.includes(format.id)}
                      onCheckedChange={(checked) => {
                        if (checked) {
                          updateOption('exportFormats', [...options.exportFormats, format.id]);
                        } else {
                          updateOption('exportFormats', options.exportFormats.filter(f => f !== format.id));
                        }
                      }}
                    />
                    <div>
                      <div className=\"text-sm font-medium\">{format.label}</div>
                      <div className=\"text-xs text-gray-600\">{format.description}</div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </CardContent>
        )}
      </Card>

      {/* Navigation */}
      <div className=\"flex justify-between\">
        <Button variant=\"outline\" onClick={onBack}>
          <ArrowLeft className=\"h-4 w-4 mr-2\" />
          Back to Test Selection
        </Button>
        <Button onClick={onRunAnalysis} disabled={loading} size=\"lg\" className=\"min-w-32\">
          {loading ? (
            <>
              <div className=\"animate-spin h-4 w-4 mr-2 border-2 border-white border-t-transparent rounded-full\" />
              Running...
            </>
          ) : (
            <>
              <Play className=\"h-4 w-4 mr-2\" />
              Run Analysis
            </>
          )}
        </Button>
      </div>
    </div>
  );
}