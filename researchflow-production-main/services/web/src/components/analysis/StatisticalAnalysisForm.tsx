/**
 * Statistical Analysis Form
 *
 * Comprehensive form for configuring statistical analyses with guided test selection,
 * variable assignment, and assumption checking.
 */

import React, { useState, useCallback, useEffect, useMemo } from 'react';
import { AlertTriangle, Check, Info, Upload, FileText } from 'lucide-react';

import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Checkbox } from '@/components/ui/checkbox';
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import { Progress } from '@/components/ui/progress';

import {
  StatisticalTestType,
  StatisticalTestConfig,
  AnalysisVariable,
  VariableType,
  VariableRole,
  ValidationResult,
  DatasetMetadata,
  TestTypeInfo
} from '@/types/statistical-analysis';

import { useStatisticalAnalysis } from '@/hooks/use-statistical-analysis';

interface StatisticalAnalysisFormProps {
  /** Current dataset metadata */
  datasetMetadata: DatasetMetadata | null;
  /** Initial configuration (for editing) */
  initialConfig?: StatisticalTestConfig;
  /** Called when form is submitted */
  onSubmit: (config: StatisticalTestConfig) => void;
  /** Called when form validation changes */
  onValidationChange?: (validation: ValidationResult) => void;
  /** Whether form is disabled (during execution) */
  disabled?: boolean;
}

interface FormState {
  testType: StatisticalTestType | null;
  variables: AnalysisVariable[];
  confidenceLevel: number;
  alpha: number;
  multipleComparisonCorrection: 'bonferroni' | 'holm' | 'fdr' | 'none';
  options: {
    tails?: 'two' | 'one';
    direction?: 'greater' | 'less';
    equalVariance?: boolean;
    postHoc?: 'tukey' | 'bonferroni' | 'scheffe' | 'none';
    bootstrap?: boolean;
    bootstrapIterations?: number;
  };
}

const TEST_TYPES: TestTypeInfo[] = [
  {
    type: 't-test-independent',
    name: 'Independent Samples t-test',
    description: 'Compare means between two independent groups',
    requiredVariables: [
      { role: 'dependent', type: ['continuous'], minCount: 1, maxCount: 1 },
      { role: 'grouping', type: ['binary', 'categorical'], minCount: 1, maxCount: 1 }
    ],
    assumptions: ['Normality', 'Equal variances', 'Independence'],
    useCase: 'Comparing continuous outcome between two groups (e.g., treatment vs control)',
    examples: ['Drug efficacy study', 'Comparison of test scores between schools'],
    effectSizes: ["Cohen's d", 'Hedge\'s g']
  },
  {
    type: 't-test-paired',
    name: 'Paired Samples t-test',
    description: 'Compare means within the same subjects (before/after)',
    requiredVariables: [
      { role: 'dependent', type: ['continuous'], minCount: 2, maxCount: 2 }
    ],
    assumptions: ['Normality of differences', 'Independence'],
    useCase: 'Before/after comparisons or matched pairs',
    examples: ['Pre/post treatment measurements', 'Crossover trial analysis'],
    effectSizes: ["Cohen's d", 'Correlation']
  },
  {
    type: 'anova-one-way',
    name: 'One-Way ANOVA',
    description: 'Compare means across multiple groups',
    requiredVariables: [
      { role: 'dependent', type: ['continuous'], minCount: 1, maxCount: 1 },
      { role: 'grouping', type: ['categorical'], minCount: 1, maxCount: 1 }
    ],
    assumptions: ['Normality', 'Equal variances', 'Independence'],
    useCase: 'Comparing continuous outcome across 3+ groups',
    examples: ['Comparing multiple treatment arms', 'Performance across departments'],
    effectSizes: ['Eta squared', 'Omega squared']
  },
  {
    type: 'chi-square',
    name: 'Chi-square Test',
    description: 'Test association between categorical variables',
    requiredVariables: [
      { role: 'dependent', type: ['categorical', 'binary'], minCount: 1, maxCount: 1 },
      { role: 'independent', type: ['categorical', 'binary'], minCount: 1 }
    ],
    assumptions: ['Expected frequencies ≥ 5', 'Independence'],
    useCase: 'Testing relationships between categorical variables',
    examples: ['Treatment response by gender', 'Survey response patterns'],
    effectSizes: ["Cramer's V", 'Phi coefficient']
  },
  {
    type: 'correlation-pearson',
    name: 'Pearson Correlation',
    description: 'Linear relationship between continuous variables',
    requiredVariables: [
      { role: 'dependent', type: ['continuous'], minCount: 2 }
    ],
    assumptions: ['Normality', 'Linear relationship', 'Independence'],
    useCase: 'Measuring linear association between continuous variables',
    examples: ['Height and weight correlation', 'Test score relationships'],
    effectSizes: ['r', 'r²']
  },
  {
    type: 'regression-linear',
    name: 'Linear Regression',
    description: 'Model continuous outcome using predictors',
    requiredVariables: [
      { role: 'dependent', type: ['continuous'], minCount: 1, maxCount: 1 },
      { role: 'independent', type: ['continuous', 'categorical'], minCount: 1 }
    ],
    assumptions: ['Linearity', 'Independence', 'Homoscedasticity', 'Normality of residuals'],
    useCase: 'Predicting continuous outcomes or identifying significant predictors',
    examples: ['Predicting patient outcomes', 'Salary prediction models'],
    effectSizes: ['R²', 'Adjusted R²', 'Standardized beta']
  }
];

export function StatisticalAnalysisForm({
  datasetMetadata,
  initialConfig,
  onSubmit,
  onValidationChange,
  disabled = false
}: StatisticalAnalysisFormProps) {
  const { validateConfig } = useStatisticalAnalysis();

  const [formState, setFormState] = useState<FormState>(() => ({
    testType: initialConfig?.testType || null,
    variables: initialConfig?.variables || [],
    confidenceLevel: initialConfig?.confidenceLevel || 0.95,
    alpha: initialConfig?.alpha || 0.05,
    multipleComparisonCorrection: initialConfig?.multipleComparisonCorrection || 'fdr',
    options: initialConfig?.options || {}
  }));

  const [activeTab, setActiveTab] = useState('test-selection');
  const [validation, setValidation] = useState<ValidationResult | null>(null);

  // Available columns grouped by type
  const columnsByType = useMemo(() => {
    if (!datasetMetadata) return { continuous: [], categorical: [], binary: [], ordinal: [] };
    
    return datasetMetadata.columns.reduce((acc, col) => {
      if (col.suitable) {
        acc[col.type].push(col);
      }
      return acc;
    }, {
      continuous: [] as typeof datasetMetadata.columns,
      categorical: [] as typeof datasetMetadata.columns,
      binary: [] as typeof datasetMetadata.columns,
      ordinal: [] as typeof datasetMetadata.columns
    });
  }, [datasetMetadata]);

  // Filter test types based on available data
  const availableTestTypes = useMemo(() => {
    if (!datasetMetadata) return [];

    return TEST_TYPES.filter(testType => {
      return testType.requiredVariables.every(req => {
        const availableColumns = req.type.flatMap(type => columnsByType[type] || []);
        return availableColumns.length >= req.minCount;
      });
    });
  }, [columnsByType, datasetMetadata]);

  // Selected test info
  const selectedTestInfo = useMemo(() => {
    return TEST_TYPES.find(t => t.type === formState.testType);
  }, [formState.testType]);

  // Form completion progress
  const completionProgress = useMemo(() => {
    let completed = 0;
    const total = 4;

    if (formState.testType) completed++;
    if (formState.variables.length > 0) completed++;
    if (formState.confidenceLevel && formState.alpha) completed++;
    if (validation?.valid) completed++;

    return (completed / total) * 100;
  }, [formState, validation]);

  // Update form state
  const updateFormState = useCallback((updates: Partial<FormState>) => {
    setFormState(prev => ({ ...prev, ...updates }));
  }, []);

  // Validate configuration
  const validateConfiguration = useCallback(async () => {
    if (!formState.testType || !datasetMetadata) {
      setValidation({ valid: false, errors: [], warnings: [] });
      return;
    }

    const config: StatisticalTestConfig = {
      testType: formState.testType,
      variables: formState.variables,
      confidenceLevel: formState.confidenceLevel,
      alpha: formState.alpha,
      multipleComparisonCorrection: formState.multipleComparisonCorrection,
      options: formState.options
    };

    try {
      const result = await validateConfig(datasetMetadata.id, config);
      setValidation(result);
      onValidationChange?.(result);
    } catch (error) {
      console.error('Validation failed:', error);
    }
  }, [formState, datasetMetadata, validateConfig, onValidationChange]);

  // Validate when form changes
  useEffect(() => {
    validateConfiguration();
  }, [validateConfiguration]);

  // Handle test type selection
  const handleTestTypeChange = useCallback((testType: StatisticalTestType) => {
    updateFormState({
      testType,
      variables: [], // Reset variables when test changes
      options: {} // Reset options
    });
    setActiveTab('variables');
  }, [updateFormState]);

  // Handle variable assignment
  const handleVariableChange = useCallback((role: VariableRole, columnName: string, action: 'add' | 'remove') => {
    const column = datasetMetadata?.columns.find(c => c.name === columnName);
    if (!column) return;

    updateFormState({
      variables: formState.variables.filter(v => v.role !== role).concat(
        action === 'add' ? [{
          name: columnName,
          type: column.type,
          role,
          label: columnName,
          required: true
        }] : []
      )
    });
  }, [formState.variables, datasetMetadata, updateFormState]);

  // Handle form submission
  const handleSubmit = useCallback(() => {
    if (!validation?.valid || !formState.testType) return;

    const config: StatisticalTestConfig = {
      testType: formState.testType,
      variables: formState.variables,
      confidenceLevel: formState.confidenceLevel,
      alpha: formState.alpha,
      multipleComparisonCorrection: formState.multipleComparisonCorrection,
      options: formState.options
    };

    onSubmit(config);
  }, [formState, validation, onSubmit]);

  if (!datasetMetadata) {
    return (
      <Card>
        <CardContent className="py-8 text-center">
          <Upload className="h-12 w-12 mx-auto mb-4 text-gray-400" />
          <h3 className="text-lg font-semibold text-gray-900 mb-2">No Dataset Selected</h3>
          <p className="text-gray-500 mb-4">
            Please upload or select a dataset to configure your statistical analysis.
          </p>
          <Button variant="outline">
            <Upload className="h-4 w-4 mr-2" />
            Upload Dataset
          </Button>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-6">
      {/* Progress Header */}
      <Card>
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="text-lg">Configure Analysis</CardTitle>
              <p className="text-sm text-gray-500">
                Dataset: {datasetMetadata.name} ({datasetMetadata.rowCount} rows, {datasetMetadata.columns.length} columns)
              </p>
            </div>
            <div className="text-right">
              <div className="text-sm font-medium mb-1">{Math.round(completionProgress)}% Complete</div>
              <Progress value={completionProgress} className="w-32" />
            </div>
          </div>
        </CardHeader>
      </Card>

      {/* Validation Alerts */}
      {validation?.errors.length > 0 && (
        <Alert variant="destructive">
          <AlertTriangle className="h-4 w-4" />
          <AlertTitle>Configuration Issues</AlertTitle>
          <AlertDescription>
            <ul className="list-disc list-inside space-y-1">
              {validation.errors.map((error, index) => (
                <li key={index}>{error.message}</li>
              ))}
            </ul>
          </AlertDescription>
        </Alert>
      )}

      {validation?.warnings.length > 0 && (
        <Alert>
          <Info className="h-4 w-4" />
          <AlertTitle>Recommendations</AlertTitle>
          <AlertDescription>
            <ul className="list-disc list-inside space-y-1">
              {validation.warnings.map((warning, index) => (
                <li key={index}>{warning.message}</li>
              ))}
            </ul>
          </AlertDescription>
        </Alert>
      )}

      {/* Configuration Tabs */}
      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList className="grid grid-cols-4 w-full">
          <TabsTrigger value="test-selection" className="flex items-center gap-2">
            {formState.testType ? <Check className="h-4 w-4" /> : <div className="h-4 w-4" />}
            Test Selection
          </TabsTrigger>
          <TabsTrigger 
            value="variables" 
            disabled={!formState.testType}
            className="flex items-center gap-2"
          >
            {formState.variables.length > 0 ? <Check className="h-4 w-4" /> : <div className="h-4 w-4" />}
            Variables
          </TabsTrigger>
          <TabsTrigger 
            value="options"
            disabled={!formState.testType || formState.variables.length === 0}
            className="flex items-center gap-2"
          >
            Options
          </TabsTrigger>
          <TabsTrigger 
            value="review"
            disabled={!validation?.valid}
            className="flex items-center gap-2"
          >
            {validation?.valid ? <Check className="h-4 w-4" /> : <div className="h-4 w-4" />}
            Review
          </TabsTrigger>
        </TabsList>

        {/* Test Selection Tab */}
        <TabsContent value="test-selection" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Select Statistical Test</CardTitle>
              <p className="text-sm text-gray-500">
                Choose the appropriate test based on your research question and data structure.
              </p>
            </CardHeader>
            <CardContent>
              <div className="grid gap-4">
                {availableTestTypes.map(test => (
                  <div 
                    key={test.type}
                    className={`border rounded-lg p-4 cursor-pointer transition-colors ${
                      formState.testType === test.type
                        ? 'border-blue-500 bg-blue-50'
                        : 'border-gray-200 hover:border-gray-300'
                    }`}
                    onClick={() => handleTestTypeChange(test.type)}
                  >
                    <div className="flex items-start justify-between">
                      <div className="flex-1">
                        <h4 className="font-semibold text-gray-900">{test.name}</h4>
                        <p className="text-sm text-gray-600 mt-1">{test.description}</p>
                        <p className="text-xs text-gray-500 mt-2">{test.useCase}</p>
                        
                        <div className="flex flex-wrap gap-1 mt-3">
                          {test.effectSizes.map(effect => (
                            <Badge key={effect} variant="outline" className="text-xs">
                              {effect}
                            </Badge>
                          ))}
                        </div>
                      </div>
                      <RadioGroup value={formState.testType || ''}>
                        <RadioGroupItem value={test.type} />
                      </RadioGroup>
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Variables Tab */}
        <TabsContent value="variables" className="space-y-4">
          {selectedTestInfo && (
            <Card>
              <CardHeader>
                <CardTitle>Assign Variables</CardTitle>
                <p className="text-sm text-gray-500">
                  Assign dataset columns to the required roles for {selectedTestInfo.name}.
                </p>
              </CardHeader>
              <CardContent className="space-y-6">
                {selectedTestInfo.requiredVariables.map((req, index) => (
                  <div key={index} className="space-y-3">
                    <div className="flex items-center justify-between">
                      <Label className="text-sm font-medium capitalize">
                        {req.role} Variable
                        {req.minCount > 1 && ` (${req.minCount} required)`}
                      </Label>
                      <Badge variant="outline" className="text-xs">
                        {req.type.join(' / ')}
                      </Badge>
                    </div>

                    <Select 
                      value={formState.variables.find(v => v.role === req.role)?.name || ''}
                      onValueChange={(value) => handleVariableChange(req.role, value, 'add')}
                    >
                      <SelectTrigger>
                        <SelectValue placeholder={`Select ${req.role} variable...`} />
                      </SelectTrigger>
                      <SelectContent>
                        {req.type.flatMap(type => columnsByType[type] || []).map(column => (
                          <SelectItem key={column.name} value={column.name}>
                            <div className="flex items-center justify-between w-full">
                              <span>{column.name}</span>
                              <div className="flex items-center gap-2 text-xs text-gray-500">
                                <Badge variant="outline" className="text-xs">
                                  {column.type}
                                </Badge>
                                <span>{column.count} values</span>
                              </div>
                            </div>
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                ))}
              </CardContent>
            </Card>
          )}
        </TabsContent>

        {/* Options Tab */}
        <TabsContent value="options" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Analysis Options</CardTitle>
              <p className="text-sm text-gray-500">
                Configure statistical parameters and testing options.
              </p>
            </CardHeader>
            <CardContent className="space-y-6">
              {/* Basic Parameters */}
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label>Confidence Level</Label>
                  <Select 
                    value={formState.confidenceLevel.toString()}
                    onValueChange={(value) => updateFormState({ confidenceLevel: parseFloat(value) })}
                  >
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="0.90">90%</SelectItem>
                      <SelectItem value="0.95">95%</SelectItem>
                      <SelectItem value="0.99">99%</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                <div className="space-y-2">
                  <Label>Alpha Level</Label>
                  <Select 
                    value={formState.alpha.toString()}
                    onValueChange={(value) => updateFormState({ alpha: parseFloat(value) })}
                  >
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="0.01">0.01</SelectItem>
                      <SelectItem value="0.05">0.05</SelectItem>
                      <SelectItem value="0.10">0.10</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>

              {/* Multiple Comparison Correction */}
              <div className="space-y-2">
                <Label>Multiple Comparison Correction</Label>
                <Select 
                  value={formState.multipleComparisonCorrection}
                  onValueChange={(value: any) => updateFormState({ multipleComparisonCorrection: value })}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="none">None</SelectItem>
                    <SelectItem value="bonferroni">Bonferroni</SelectItem>
                    <SelectItem value="holm">Holm</SelectItem>
                    <SelectItem value="fdr">FDR (Benjamini-Hochberg)</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              {/* Test-specific options */}
              {formState.testType?.includes('t-test') && (
                <div className="space-y-4">
                  <Separator />
                  <h4 className="font-medium">T-test Options</h4>
                  
                  <div className="space-y-2">
                    <Label>Test Type</Label>
                    <RadioGroup 
                      value={formState.options.tails || 'two'}
                      onValueChange={(value: 'two' | 'one') => 
                        updateFormState({ options: { ...formState.options, tails: value } })
                      }
                    >
                      <div className="flex items-center space-x-2">
                        <RadioGroupItem value="two" />
                        <Label>Two-tailed</Label>
                      </div>
                      <div className="flex items-center space-x-2">
                        <RadioGroupItem value="one" />
                        <Label>One-tailed</Label>
                      </div>
                    </RadioGroup>
                  </div>

                  {formState.testType === 't-test-independent' && (
                    <div className="flex items-center space-x-2">
                      <Checkbox 
                        checked={formState.options.equalVariance ?? true}
                        onCheckedChange={(checked) =>
                          updateFormState({ 
                            options: { ...formState.options, equalVariance: !!checked } 
                          })
                        }
                      />
                      <Label>Assume equal variances</Label>
                    </div>
                  )}
                </div>
              )}

              {/* Bootstrap options */}
              <div className="space-y-4">
                <Separator />
                <div className="flex items-center space-x-2">
                  <Checkbox 
                    checked={formState.options.bootstrap ?? false}
                    onCheckedChange={(checked) =>
                      updateFormState({ 
                        options: { 
                          ...formState.options, 
                          bootstrap: !!checked,
                          bootstrapIterations: checked ? 1000 : undefined
                        } 
                      })
                    }
                  />
                  <Label>Bootstrap confidence intervals</Label>
                </div>

                {formState.options.bootstrap && (
                  <div className="space-y-2">
                    <Label>Bootstrap Iterations</Label>
                    <Input
                      type="number"
                      value={formState.options.bootstrapIterations || 1000}
                      onChange={(e) => updateFormState({ 
                        options: { 
                          ...formState.options, 
                          bootstrapIterations: parseInt(e.target.value) 
                        } 
                      })}
                      min={100}
                      max={10000}
                      step={100}
                    />
                  </div>
                )}
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Review Tab */}
        <TabsContent value="review" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Review Configuration</CardTitle>
              <p className="text-sm text-gray-500">
                Review your analysis configuration before execution.
              </p>
            </CardHeader>
            <CardContent className="space-y-6">
              {/* Configuration Summary */}
              <div className="space-y-4">
                <div>
                  <Label className="text-sm font-medium">Statistical Test</Label>
                  <p className="text-sm text-gray-600">{selectedTestInfo?.name}</p>
                </div>

                <div>
                  <Label className="text-sm font-medium">Variables</Label>
                  <div className="space-y-1">
                    {formState.variables.map(variable => (
                      <div key={`${variable.role}-${variable.name}`} className="flex items-center gap-2 text-sm">
                        <Badge variant="outline" className="text-xs capitalize">
                          {variable.role}
                        </Badge>
                        <span>{variable.name}</span>
                        <span className="text-gray-500">({variable.type})</span>
                      </div>
                    ))}
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <Label className="text-sm font-medium">Confidence Level</Label>
                    <p className="text-sm text-gray-600">{(formState.confidenceLevel * 100).toFixed(0)}%</p>
                  </div>
                  <div>
                    <Label className="text-sm font-medium">Alpha Level</Label>
                    <p className="text-sm text-gray-600">{formState.alpha}</p>
                  </div>
                </div>

                {formState.multipleComparisonCorrection !== 'none' && (
                  <div>
                    <Label className="text-sm font-medium">Multiple Comparison Correction</Label>
                    <p className="text-sm text-gray-600 capitalize">
                      {formState.multipleComparisonCorrection.replace('_', '-')}
                    </p>
                  </div>
                )}
              </div>

              {/* Submit Button */}
              <div className="pt-4">
                <Button 
                  onClick={handleSubmit}
                  disabled={disabled || !validation?.valid}
                  className="w-full"
                >
                  {disabled ? 'Running Analysis...' : 'Run Statistical Analysis'}
                </Button>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}

export default StatisticalAnalysisForm;