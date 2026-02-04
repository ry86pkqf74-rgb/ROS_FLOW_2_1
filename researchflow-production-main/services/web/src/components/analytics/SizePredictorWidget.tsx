/*
Size Predictor Widget Component
==============================

React component for manuscript size prediction using machine learning models.
Provides interface for input data and displays comprehensive size predictions.
*/

import React, { useState } from 'react';
import { Card, CardHeader, CardContent, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Badge } from '@/components/ui/badge';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Progress } from '@/components/ui/progress';
import { PieChart, Pie, Cell, ResponsiveContainer, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip } from 'recharts';
import { FileText, Calculator, TrendingUp, Download, Upload, Info } from 'lucide-react';

// ============================================================================
// Types & Interfaces
// ============================================================================

interface ManuscriptData {
  title?: string;
  abstract?: string;
  introduction?: string;
  methods?: string;
  results?: string;
  discussion?: string;
  references?: string[];
  metadata?: {
    word_count?: number;
    reference_count?: number;
    figure_count?: number;
    table_count?: number;
  };
}

interface SizePrediction {
  predicted_size_bytes: number;
  confidence_score: number;
  predicted_compression_ratio: number;
  estimated_processing_time: number;
  recommended_compression_level: string;
  breakdown: {
    text_content: number;
    references: number;
    figures: number;
    tables: number;
    metadata: number;
    formatting: number;
  };
  factors: {
    word_count_impact: number;
    media_content_impact: number;
    complexity_impact: number;
    citation_impact: number;
  };
}

interface SizePredictorWidgetProps {
  className?: string;
  onPredictionComplete?: (prediction: SizePrediction) => void;
}

// ============================================================================
// Size Predictor Widget Component
// ============================================================================

export const SizePredictorWidget: React.FC<SizePredictorWidgetProps> = ({
  className = '',
  onPredictionComplete
}) => {
  // Form state
  const [manuscriptData, setManuscriptData] = useState<ManuscriptData>({
    metadata: {}
  });
  
  // UI state
  const [prediction, setPrediction] = useState<SizePrediction | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [inputMethod, setInputMethod] = useState<'form' | 'json' | 'file'>('form');
  const [jsonInput, setJsonInput] = useState('');

  // Handle form field changes
  const handleFieldChange = (field: string, value: any) => {
    if (field.startsWith('metadata.')) {
      const metadataField = field.replace('metadata.', '');
      setManuscriptData(prev => ({
        ...prev,
        metadata: {
          ...prev.metadata,
          [metadataField]: value
        }
      }));
    } else {
      setManuscriptData(prev => ({
        ...prev,
        [field]: value
      }));
    }
  };

  // Handle JSON input
  const handleJsonInput = () => {
    try {
      const jsonData = JSON.parse(jsonInput);
      setManuscriptData(jsonData);
      setError(null);
    } catch (e) {
      setError('Invalid JSON format');
    }
  };

  // Handle file upload
  const handleFileUpload = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = (e) => {
      try {
        const content = e.target?.result as string;
        if (file.type === 'application/json') {
          const jsonData = JSON.parse(content);
          setManuscriptData(jsonData);
        } else {
          // Treat as text manuscript
          setManuscriptData({
            title: file.name.replace(/\.[^/.]+$/, ""),
            abstract: content.substring(0, 500) + "...", // First 500 chars as abstract
            introduction: content,
            metadata: {
              word_count: content.split(/\s+/).length
            }
          });
        }
        setError(null);
      } catch (e) {
        setError('Failed to process uploaded file');
      }
    };
    reader.readAsText(file);
  };

  // Submit prediction request
  const handlePredictSize = async () => {
    setIsLoading(true);
    setError(null);

    try {
      const response = await fetch('/api/analytics/predict-size', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(manuscriptData)
      });

      if (!response.ok) {
        throw new Error(`Prediction failed: ${response.statusText}`);
      }

      const data = await response.json();
      setPrediction(data.prediction);
      
      // Merge breakdown and factors
      const fullPrediction = {
        ...data.prediction,
        breakdown: data.breakdown,
        factors: data.factors
      };

      if (onPredictionComplete) {
        onPredictionComplete(fullPrediction);
      }

    } catch (e) {
      setError(e instanceof Error ? e.message : 'Prediction request failed');
    } finally {
      setIsLoading(false);
    }
  };

  // Format file size
  const formatFileSize = (bytes: number): string => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  // Get confidence color
  const getConfidenceColor = (score: number): string => {
    if (score >= 0.8) return 'text-green-600';
    if (score >= 0.6) return 'text-yellow-600';
    return 'text-red-600';
  };

  // Prepare chart data
  const breakdownData = prediction ? Object.entries(prediction.breakdown).map(([key, value]) => ({
    name: key.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase()),
    value,
    percentage: ((value / prediction.predicted_size_bytes) * 100).toFixed(1)
  })) : [];

  const factorsData = prediction ? Object.entries(prediction.factors).map(([key, value]) => ({
    name: key.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase()),
    impact: (value * 100).toFixed(1)
  })) : [];

  const COLORS = ['#0088FE', '#00C49F', '#FFBB28', '#FF8042', '#8884D8', '#82CA9D'];

  return (
    <div className={`size-predictor-widget space-y-6 ${className}`}>
      {/* Header */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center">
            <Calculator className="h-5 w-5 mr-2" />
            Manuscript Size Predictor
          </CardTitle>
          <p className="text-sm text-gray-600">
            Predict manuscript package size, compression ratio, and processing time using machine learning.
          </p>
        </CardHeader>
      </Card>

      {/* Input Method Selection */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Input Method</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex space-x-2 mb-4">
            <Button 
              variant={inputMethod === 'form' ? 'default' : 'outline'}
              size="sm"
              onClick={() => setInputMethod('form')}
            >
              <FileText className="h-4 w-4 mr-1" />
              Form Input
            </Button>
            <Button 
              variant={inputMethod === 'json' ? 'default' : 'outline'}
              size="sm"
              onClick={() => setInputMethod('json')}
            >
              <Info className="h-4 w-4 mr-1" />
              JSON Input
            </Button>
            <Button 
              variant={inputMethod === 'file' ? 'default' : 'outline'}
              size="sm"
              onClick={() => setInputMethod('file')}
            >
              <Upload className="h-4 w-4 mr-1" />
              File Upload
            </Button>
          </div>

          {/* Form Input */}
          {inputMethod === 'form' && (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="space-y-4">
                <div>
                  <Label htmlFor="title">Title</Label>
                  <Input
                    id="title"
                    value={manuscriptData.title || ''}
                    onChange={(e) => handleFieldChange('title', e.target.value)}
                    placeholder="Enter manuscript title"
                  />
                </div>

                <div>
                  <Label htmlFor="abstract">Abstract</Label>
                  <Textarea
                    id="abstract"
                    value={manuscriptData.abstract || ''}
                    onChange={(e) => handleFieldChange('abstract', e.target.value)}
                    placeholder="Enter abstract text"
                    rows={3}
                  />
                </div>

                <div>
                  <Label htmlFor="content">Main Content</Label>
                  <Textarea
                    id="content"
                    value={manuscriptData.introduction || ''}
                    onChange={(e) => handleFieldChange('introduction', e.target.value)}
                    placeholder="Enter main manuscript content"
                    rows={5}
                  />
                </div>
              </div>

              <div className="space-y-4">
                <div>
                  <Label htmlFor="word_count">Word Count</Label>
                  <Input
                    id="word_count"
                    type="number"
                    value={manuscriptData.metadata?.word_count || ''}
                    onChange={(e) => handleFieldChange('metadata.word_count', parseInt(e.target.value) || 0)}
                    placeholder="Number of words"
                  />
                </div>

                <div>
                  <Label htmlFor="reference_count">Reference Count</Label>
                  <Input
                    id="reference_count"
                    type="number"
                    value={manuscriptData.metadata?.reference_count || ''}
                    onChange={(e) => handleFieldChange('metadata.reference_count', parseInt(e.target.value) || 0)}
                    placeholder="Number of references"
                  />
                </div>

                <div>
                  <Label htmlFor="figure_count">Figure Count</Label>
                  <Input
                    id="figure_count"
                    type="number"
                    value={manuscriptData.metadata?.figure_count || ''}
                    onChange={(e) => handleFieldChange('metadata.figure_count', parseInt(e.target.value) || 0)}
                    placeholder="Number of figures"
                  />
                </div>

                <div>
                  <Label htmlFor="table_count">Table Count</Label>
                  <Input
                    id="table_count"
                    type="number"
                    value={manuscriptData.metadata?.table_count || ''}
                    onChange={(e) => handleFieldChange('metadata.table_count', parseInt(e.target.value) || 0)}
                    placeholder="Number of tables"
                  />
                </div>
              </div>
            </div>
          )}

          {/* JSON Input */}
          {inputMethod === 'json' && (
            <div className="space-y-4">
              <div>
                <Label htmlFor="json-input">JSON Manuscript Data</Label>
                <Textarea
                  id="json-input"
                  value={jsonInput}
                  onChange={(e) => setJsonInput(e.target.value)}
                  placeholder={`{\n  "title": "Manuscript Title",\n  "abstract": "Abstract text...",\n  "metadata": {\n    "word_count": 5000,\n    "reference_count": 25\n  }\n}`}
                  rows={8}
                  className="font-mono text-sm"
                />
              </div>
              <Button onClick={handleJsonInput} variant="outline">
                Parse JSON
              </Button>
            </div>
          )}

          {/* File Upload */}
          {inputMethod === 'file' && (
            <div className="space-y-4">
              <div>
                <Label htmlFor="file-upload">Upload Manuscript File</Label>
                <Input
                  id="file-upload"
                  type="file"
                  accept=".txt,.json,.md,.docx"
                  onChange={handleFileUpload}
                />
                <p className="text-xs text-gray-500 mt-1">
                  Supported formats: TXT, JSON, Markdown, DOCX
                </p>
              </div>
            </div>
          )}

          {/* Submit Button */}
          <div className="mt-6">
            <Button 
              onClick={handlePredictSize} 
              disabled={isLoading}
              className="w-full"
            >
              {isLoading ? (
                <>
                  <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                  Predicting...
                </>
              ) : (
                <>
                  <TrendingUp className="h-4 w-4 mr-2" />
                  Predict Size
                </>
              )}
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Error Display */}
      {error && (
        <Alert variant="destructive">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      {/* Prediction Results */}
      {prediction && (
        <div className="space-y-4">
          {/* Summary Results */}
          <Card>
            <CardHeader>
              <CardTitle>Prediction Results</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                <div className="text-center">
                  <div className="text-2xl font-bold text-blue-600">
                    {formatFileSize(prediction.predicted_size_bytes)}
                  </div>
                  <div className="text-sm text-gray-600">Predicted Size</div>
                </div>

                <div className="text-center">
                  <div className={`text-2xl font-bold ${getConfidenceColor(prediction.confidence_score)}`}>
                    {(prediction.confidence_score * 100).toFixed(1)}%
                  </div>
                  <div className="text-sm text-gray-600">Confidence</div>
                </div>

                <div className="text-center">
                  <div className="text-2xl font-bold text-green-600">
                    {(prediction.predicted_compression_ratio * 100).toFixed(1)}%
                  </div>
                  <div className="text-sm text-gray-600">Compression Ratio</div>
                </div>

                <div className="text-center">
                  <div className="text-2xl font-bold text-orange-600">
                    {prediction.estimated_processing_time.toFixed(2)}s
                  </div>
                  <div className="text-sm text-gray-600">Processing Time</div>
                </div>
              </div>

              <div className="mt-4">
                <Badge variant="outline" className="mr-2">
                  Recommended Compression: {prediction.recommended_compression_level.toUpperCase()}
                </Badge>
                <Badge variant={prediction.confidence_score > 0.8 ? 'default' : 'secondary'}>
                  {prediction.confidence_score > 0.8 ? 'High Confidence' : 
                   prediction.confidence_score > 0.6 ? 'Medium Confidence' : 'Low Confidence'}
                </Badge>
              </div>
            </CardContent>
          </Card>

          {/* Size Breakdown Chart */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            <Card>
              <CardHeader>
                <CardTitle>Size Breakdown</CardTitle>
              </CardHeader>
              <CardContent>
                <ResponsiveContainer width="100%" height={300}>
                  <PieChart>
                    <Pie
                      data={breakdownData}
                      cx="50%"
                      cy="50%"
                      labelLine={false}
                      label={({ name, percentage }) => `${name}: ${percentage}%`}
                      outerRadius={80}
                      fill="#8884d8"
                      dataKey="value"
                    >
                      {breakdownData.map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                      ))}
                    </Pie>
                    <Tooltip formatter={(value) => [formatFileSize(Number(value)), 'Size']} />
                  </PieChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Impact Factors</CardTitle>
              </CardHeader>
              <CardContent>
                <ResponsiveContainer width="100%" height={300}>
                  <BarChart data={factorsData}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="name" angle={-45} textAnchor="end" height={80} />
                    <YAxis />
                    <Tooltip formatter={(value) => [`${value}%`, 'Impact']} />
                    <Bar dataKey="impact" fill="#8884d8" />
                  </BarChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>
          </div>

          {/* Detailed Breakdown Table */}
          <Card>
            <CardHeader>
              <CardTitle>Detailed Breakdown</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b">
                      <th className="text-left p-2">Component</th>
                      <th className="text-right p-2">Size</th>
                      <th className="text-right p-2">Percentage</th>
                    </tr>
                  </thead>
                  <tbody>
                    {breakdownData.map((item, index) => (
                      <tr key={index} className="border-b">
                        <td className="p-2">{item.name}</td>
                        <td className="p-2 text-right">{formatFileSize(item.value)}</td>
                        <td className="p-2 text-right">{item.percentage}%</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </CardContent>
          </Card>

          {/* Download Results */}
          <div className="flex justify-end">
            <Button
              variant="outline"
              size="sm"
              onClick={() => {
                const dataStr = JSON.stringify({
                  prediction,
                  input_data: manuscriptData,
                  timestamp: new Date().toISOString()
                }, null, 2);
                const dataBlob = new Blob([dataStr], {type: 'application/json'});
                const url = URL.createObjectURL(dataBlob);
                const link = document.createElement('a');
                link.href = url;
                link.download = 'size_prediction.json';
                link.click();
                URL.revokeObjectURL(url);
              }}
            >
              <Download className="h-4 w-4 mr-2" />
              Download Results
            </Button>
          </div>
        </div>
      )}
    </div>
  );
};

export default SizePredictorWidget;