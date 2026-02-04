import React, { useState, useCallback, useRef } from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { 
  Upload, 
  FileSpreadsheet, 
  Type, 
  Database, 
  AlertCircle, 
  CheckCircle,
  Trash2,
  Plus,
  Download,
  ArrowRight
} from 'lucide-react';
import { StudyData } from '@/types/statistical-analysis';
import Papa from 'papaparse';

interface DataInputPanelProps {
  onDataChange: (data: StudyData) => void;
  initialData?: StudyData | null;
  onNext: () => void;
}

interface DataValidation {
  isValid: boolean;
  errors: string[];
  warnings: string[];
  summary: {
    totalObservations: number;
    variables: number;
    groups: number;
    missingValues: number;
  };
}

interface ManualDataEntry {
  groups: string[];
  outcomeVariable: string;
  outcomeValues: number[];
}

export function DataInputPanel({ onDataChange, initialData, onNext }: DataInputPanelProps) {
  const [activeTab, setActiveTab] = useState<'manual' | 'upload' | 'sample'>('manual');
  const [manualData, setManualData] = useState<ManualDataEntry>({
    groups: [],
    outcomeVariable: 'outcome',
    outcomeValues: []
  });
  const [csvData, setCsvData] = useState<string>('');
  const [validation, setValidation] = useState<DataValidation | null>(null);
  const [dragOver, setDragOver] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const sampleDatasets = [
    {
      name: 'Blood Pressure Trial',
      description: 'Comparison of treatment vs control groups',
      data: {
        groups: ['Treatment', 'Treatment', 'Treatment', 'Treatment', 'Treatment', 
                'Control', 'Control', 'Control', 'Control', 'Control'],
        outcomes: {
          systolic_bp: [120, 118, 122, 119, 121, 135, 138, 140, 136, 139]
        },
        metadata: {
          study_title: 'Blood Pressure Clinical Trial',
          outcome_unit: 'mmHg',
          description: 'Randomized controlled trial comparing antihypertensive treatments'
        }
      }
    },
    {
      name: 'Educational Intervention',
      description: 'Pre-post comparison of test scores',
      data: {
        groups: ['Pre', 'Pre', 'Pre', 'Pre', 'Pre', 'Pre',
                'Post', 'Post', 'Post', 'Post', 'Post', 'Post'],
        outcomes: {
          test_score: [72, 68, 75, 71, 73, 69, 82, 79, 85, 81, 84, 78]
        },
        metadata: {
          study_title: 'Educational Intervention Study',
          outcome_unit: 'points',
          description: 'Paired comparison of test scores before and after intervention'
        }
      }
    },
    {
      name: 'Multi-Group ANOVA',
      description: 'Comparison of three treatment groups',
      data: {
        groups: ['Group_A', 'Group_A', 'Group_A', 'Group_A',
                'Group_B', 'Group_B', 'Group_B', 'Group_B',
                'Group_C', 'Group_C', 'Group_C', 'Group_C'],
        outcomes: {
          response: [12, 14, 13, 15, 18, 20, 19, 17, 25, 23, 26, 24]
        },
        metadata: {
          study_title: 'Three-Group Comparison Study',
          outcome_unit: 'units',
          description: 'One-way ANOVA comparing three treatment conditions'
        }
      }
    }
  ];

  const validateData = useCallback((data: StudyData): DataValidation => {
    const errors: string[] = [];
    const warnings: string[] = [];

    // Check if data exists
    if (!data.outcomes || Object.keys(data.outcomes).length === 0) {
      errors.push('No outcome variables provided');
      return {
        isValid: false,
        errors,
        warnings,
        summary: { totalObservations: 0, variables: 0, groups: 0, missingValues: 0 }
      };
    }

    // Get outcome data
    const outcomeKeys = Object.keys(data.outcomes);
    const firstOutcome = data.outcomes[outcomeKeys[0]];
    const totalObservations = firstOutcome.length;
    
    // Check group-outcome length consistency
    if (data.groups && data.groups.length !== totalObservations) {
      errors.push(`Group labels (${data.groups.length}) don't match outcome data (${totalObservations})`);
    }

    // Check for missing values
    let missingValues = 0;
    outcomeKeys.forEach(key => {
      const values = data.outcomes[key];
      missingValues += values.filter(v => v == null || isNaN(Number(v))).length;
    });

    // Sample size warnings
    if (totalObservations < 3) {
      errors.push('At least 3 observations required for statistical analysis');
    } else if (totalObservations < 10) {
      warnings.push('Small sample size (n < 10) may limit statistical power');
    }

    // Group size warnings
    if (data.groups) {
      const uniqueGroups = [...new Set(data.groups)];
      const groupCounts = uniqueGroups.map(group => 
        data.groups!.filter(g => g === group).length
      );
      
      const minGroupSize = Math.min(...groupCounts);
      if (minGroupSize < 2) {
        errors.push('All groups must have at least 2 observations');
      } else if (minGroupSize < 5) {
        warnings.push('Small group sizes may limit statistical power');
      }
    }

    // Missing value warnings
    if (missingValues > 0) {
      const missingPercent = (missingValues / (totalObservations * outcomeKeys.length)) * 100;
      if (missingPercent > 20) {
        warnings.push(`High percentage of missing values (${missingPercent.toFixed(1)}%)`);
      } else {
        warnings.push(`${missingValues} missing values detected - will be excluded from analysis`);
      }
    }

    return {
      isValid: errors.length === 0,
      errors,
      warnings,
      summary: {
        totalObservations,
        variables: outcomeKeys.length,
        groups: data.groups ? [...new Set(data.groups)].length : 1,
        missingValues
      }
    };
  }, []);

  const handleManualDataSubmit = useCallback(() => {
    if (manualData.groups.length === 0 || manualData.outcomeValues.length === 0) {
      return;
    }

    const studyData: StudyData = {
      groups: manualData.groups,
      outcomes: {
        [manualData.outcomeVariable]: manualData.outcomeValues
      },
      metadata: {
        study_title: 'Manual Data Entry',
        data_source: 'manual_input'
      }
    };

    const validation = validateData(studyData);
    setValidation(validation);
    
    if (validation.isValid) {
      onDataChange(studyData);
    }
  }, [manualData, validateData, onDataChange]);

  const handleFileUpload = useCallback((file: File) => {
    const reader = new FileReader();
    reader.onload = (e) => {
      const csvText = e.target?.result as string;
      setCsvData(csvText);
      
      Papa.parse(csvText, {
        header: true,
        skipEmptyLines: true,
        complete: (results) => {
          if (results.errors.length > 0) {
            setValidation({
              isValid: false,
              errors: results.errors.map(e => e.message),
              warnings: [],
              summary: { totalObservations: 0, variables: 0, groups: 0, missingValues: 0 }
            });
            return;
          }

          const data = results.data as Record<string, any>[];
          if (data.length === 0) {
            setValidation({
              isValid: false,
              errors: ['No data found in CSV file'],
              warnings: [],
              summary: { totalObservations: 0, variables: 0, groups: 0, missingValues: 0 }
            });
            return;
          }

          // Extract columns
          const columns = Object.keys(data[0]);
          
          // Try to identify group and outcome columns
          const groupColumn = columns.find(col => 
            col.toLowerCase().includes('group') || 
            col.toLowerCase().includes('condition') ||
            col.toLowerCase().includes('treatment')
          ) || columns[0];
          
          const outcomeColumns = columns.filter(col => 
            col !== groupColumn && 
            !isNaN(Number(data[0][col]))
          );

          if (outcomeColumns.length === 0) {
            setValidation({
              isValid: false,
              errors: ['No numeric outcome variables found'],
              warnings: [],
              summary: { totalObservations: 0, variables: 0, groups: 0, missingValues: 0 }
            });
            return;
          }

          // Build StudyData
          const studyData: StudyData = {
            groups: data.map(row => String(row[groupColumn] || 'Group1')),
            outcomes: {},
            metadata: {
              study_title: file.name.replace(/\\.csv$/i, ''),
              data_source: 'csv_upload',
              columns_detected: columns
            }
          };

          // Add outcome variables
          outcomeColumns.forEach(col => {
            studyData.outcomes[col] = data.map(row => {
              const value = row[col];
              return value === '' || value == null ? NaN : Number(value);
            });
          });

          const validation = validateData(studyData);
          setValidation(validation);
          
          if (validation.isValid) {
            onDataChange(studyData);
          }
        }
      });
    };
    reader.readAsText(file);
  }, [validateData, onDataChange]);

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    
    const files = Array.from(e.dataTransfer.files);
    const csvFile = files.find(file => file.name.endsWith('.csv'));
    
    if (csvFile) {
      handleFileUpload(csvFile);
    }
  }, [handleFileUpload]);

  const handleSampleDataSelect = useCallback((sampleData: StudyData) => {
    const validation = validateData(sampleData);
    setValidation(validation);
    onDataChange(sampleData);
  }, [validateData, onDataChange]);

  return (
    <div className=\"space-y-6\">
      <Tabs value={activeTab} onValueChange={(value) => setActiveTab(value as any)}>
        <TabsList className=\"grid w-full grid-cols-3\">
          <TabsTrigger value=\"manual\" className=\"flex items-center gap-2\">
            <Type className=\"h-4 w-4\" />
            Manual Entry
          </TabsTrigger>
          <TabsTrigger value=\"upload\" className=\"flex items-center gap-2\">
            <Upload className=\"h-4 w-4\" />
            File Upload
          </TabsTrigger>
          <TabsTrigger value=\"sample\" className=\"flex items-center gap-2\">
            <Database className=\"h-4 w-4\" />
            Sample Data
          </TabsTrigger>
        </TabsList>

        <TabsContent value=\"manual\" className=\"space-y-4\">
          <Card>
            <CardHeader>
              <CardTitle>Enter Data Manually</CardTitle>
            </CardHeader>
            <CardContent className=\"space-y-4\">
              <div>
                <Label htmlFor=\"outcome-variable\">Outcome Variable Name</Label>
                <Input
                  id=\"outcome-variable\"
                  value={manualData.outcomeVariable}
                  onChange={(e) => setManualData(prev => ({ ...prev, outcomeVariable: e.target.value }))}
                  placeholder=\"e.g., blood_pressure, test_score\"
                />
              </div>
              
              <div>
                <Label htmlFor=\"groups\">Group Labels (comma-separated)</Label>
                <Input
                  id=\"groups\"
                  placeholder=\"e.g., Treatment,Treatment,Control,Control\"
                  onChange={(e) => {
                    const groups = e.target.value.split(',').map(g => g.trim()).filter(g => g);
                    setManualData(prev => ({ ...prev, groups }));
                  }}
                />
              </div>
              
              <div>
                <Label htmlFor=\"values\">Outcome Values (comma-separated numbers)</Label>
                <Textarea
                  id=\"values\"
                  placeholder=\"e.g., 120,118,135,140\"
                  rows={3}
                  onChange={(e) => {
                    const values = e.target.value.split(',').map(v => {
                      const num = parseFloat(v.trim());
                      return isNaN(num) ? 0 : num;
                    }).filter(v => !isNaN(v));
                    setManualData(prev => ({ ...prev, outcomeValues: values }));
                  }}
                />
              </div>
              
              <Button onClick={handleManualDataSubmit} className=\"w-full\">
                <CheckCircle className=\"h-4 w-4 mr-2\" />
                Validate Data
              </Button>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value=\"upload\" className=\"space-y-4\">
          <Card>
            <CardHeader>
              <CardTitle>Upload CSV File</CardTitle>
            </CardHeader>
            <CardContent>
              <div
                className={`border-2 border-dashed rounded-lg p-8 text-center transition-colors ${
                  dragOver ? 'border-blue-400 bg-blue-50' : 'border-gray-300'
                }`}
                onDragOver={handleDragOver}
                onDragLeave={handleDragLeave}
                onDrop={handleDrop}
              >
                <FileSpreadsheet className=\"h-12 w-12 text-gray-400 mx-auto mb-4\" />
                <p className=\"text-lg font-medium text-gray-700 mb-2\">
                  Drag and drop your CSV file here
                </p>
                <p className=\"text-gray-500 mb-4\">or</p>
                <Button
                  variant=\"outline\"
                  onClick={() => fileInputRef.current?.click()}
                >
                  Choose File
                </Button>
                <input
                  ref={fileInputRef}
                  type=\"file\"
                  accept=\".csv\"
                  className=\"hidden\"
                  onChange={(e) => {
                    const file = e.target.files?.[0];
                    if (file) handleFileUpload(file);
                  }}
                />
                <p className=\"text-xs text-gray-500 mt-4\">
                  Supported format: CSV files with headers
                </p>
              </div>
              
              {csvData && (
                <div className=\"mt-4\">
                  <Label>CSV Preview</Label>
                  <div className=\"bg-gray-50 p-3 rounded border text-sm font-mono max-h-32 overflow-auto\">
                    {csvData.split('\\n').slice(0, 5).join('\\n')}
                    {csvData.split('\\n').length > 5 && '\\n...'}
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value=\"sample\" className=\"space-y-4\">
          <div className=\"grid gap-4\">
            {sampleDatasets.map((sample, index) => (
              <Card key={index} className=\"cursor-pointer hover:bg-gray-50 transition-colors\">
                <CardContent className=\"p-4\">
                  <div className=\"flex justify-between items-start mb-2\">
                    <div>
                      <h3 className=\"font-medium text-gray-900\">{sample.name}</h3>
                      <p className=\"text-sm text-gray-600\">{sample.description}</p>
                    </div>
                    <Button
                      variant=\"outline\"
                      size=\"sm\"
                      onClick={() => handleSampleDataSelect(sample.data)}
                    >
                      Use Sample
                    </Button>
                  </div>
                  <div className=\"flex gap-2 text-xs\">
                    <Badge variant=\"secondary\">
                      n = {sample.data.outcomes[Object.keys(sample.data.outcomes)[0]].length}
                    </Badge>
                    <Badge variant=\"secondary\">
                      {[...new Set(sample.data.groups)].length} groups
                    </Badge>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </TabsContent>
      </Tabs>

      {/* Validation Results */}
      {validation && (
        <Card>
          <CardHeader>
            <CardTitle className=\"flex items-center gap-2\">
              {validation.isValid ? (
                <CheckCircle className=\"h-5 w-5 text-green-600\" />
              ) : (
                <AlertCircle className=\"h-5 w-5 text-red-600\" />
              )}
              Data Validation
            </CardTitle>
          </CardHeader>
          <CardContent className=\"space-y-4\">
            {/* Summary Stats */}
            <div className=\"grid grid-cols-2 md:grid-cols-4 gap-4\">
              <div className=\"text-center p-3 bg-gray-50 rounded\">
                <div className=\"text-2xl font-bold text-gray-900\">{validation.summary.totalObservations}</div>
                <div className=\"text-sm text-gray-600\">Observations</div>
              </div>
              <div className=\"text-center p-3 bg-gray-50 rounded\">
                <div className=\"text-2xl font-bold text-gray-900\">{validation.summary.variables}</div>
                <div className=\"text-sm text-gray-600\">Variables</div>
              </div>
              <div className=\"text-center p-3 bg-gray-50 rounded\">
                <div className=\"text-2xl font-bold text-gray-900\">{validation.summary.groups}</div>
                <div className=\"text-sm text-gray-600\">Groups</div>
              </div>
              <div className=\"text-center p-3 bg-gray-50 rounded\">
                <div className=\"text-2xl font-bold text-gray-900\">{validation.summary.missingValues}</div>
                <div className=\"text-sm text-gray-600\">Missing</div>
              </div>
            </div>

            {/* Errors */}
            {validation.errors.length > 0 && (
              <Alert variant=\"destructive\">
                <AlertCircle className=\"h-4 w-4\" />
                <AlertDescription>
                  <div className=\"space-y-1\">
                    {validation.errors.map((error, index) => (
                      <div key={index}>• {error}</div>
                    ))}
                  </div>
                </AlertDescription>
              </Alert>
            )}

            {/* Warnings */}
            {validation.warnings.length > 0 && (
              <Alert>
                <AlertCircle className=\"h-4 w-4\" />
                <AlertDescription>
                  <div className=\"space-y-1\">
                    {validation.warnings.map((warning, index) => (
                      <div key={index}>• {warning}</div>
                    ))}
                  </div>
                </AlertDescription>
              </Alert>
            )}

            {/* Next Button */}
            {validation.isValid && (
              <Button onClick={onNext} className=\"w-full\" size=\"lg\">
                Continue to Test Selection
                <ArrowRight className=\"h-4 w-4 ml-2\" />
              </Button>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  );
}