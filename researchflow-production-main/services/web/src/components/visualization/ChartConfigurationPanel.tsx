/**
 * Chart Configuration Panel
 * 
 * Advanced configuration component that integrates with backend capabilities
 * Features:
 * - Journal style selection with preview
 * - Quality profiles with detailed settings
 * - Real-time validation with backend constraints
 * - Color palette and theme selection
 * - Export format preferences
 */

import React, { useState, useEffect, useMemo } from 'react';
import { useVisualization } from '@/hooks/useVisualization';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Input } from '@/components/ui/input';
import { Switch } from '@/components/ui/switch';
import { Slider } from '@/components/ui/slider';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Separator } from '@/components/ui/separator';
import {
  Settings,
  Palette,
  FileImage,
  Zap,
  AlertTriangle,
  Info,
  CheckCircle,
  Sparkles
} from 'lucide-react';
import { cn } from '@/lib/utils';

export interface ChartConfiguration {
  chartType: string;
  journalStyle: string;
  qualityProfile: string;
  dimensions: {
    width: number;
    height: number;
  };
  dpi: number;
  format: string;
  colorPalette: string;
  theme: string;
  advanced: {
    antialiasing: boolean;
    vectorization: boolean;
    compression: number;
    backgroundTransparent: boolean;
    showGrid: boolean;
    showLegend: boolean;
    fontSize: number;
    lineWidth: number;
  };
  accessibility: {
    colorblindSafe: boolean;
    highContrast: boolean;
    largeText: boolean;
    altTextGeneration: boolean;
  };
  performance: {
    enableCaching: boolean;
    priority: 'speed' | 'quality' | 'balanced';
    maxDataPoints: number;
  };
}

interface JournalStyleInfo {
  id: string;
  name: string;
  description: string;
  requirements: string[];
  dimensions: { width: number; height: number };
  dpi: number;
  colorRestrictions?: string[];
}

const JOURNAL_STYLES: JournalStyleInfo[] = [
  {
    id: 'nature',
    name: 'Nature',
    description: 'High-impact scientific journal format',
    requirements: ['Vector format preferred', 'Minimum 300 DPI', 'Sans-serif fonts'],
    dimensions: { width: 800, height: 600 },
    dpi: 300,
    colorRestrictions: ['Colorblind-safe palette required']
  },
  {
    id: 'jama',
    name: 'JAMA',
    description: 'Journal of American Medical Association',
    requirements: ['Conservative color palette', 'Clear typography', 'Professional styling'],
    dimensions: { width: 600, height: 450 },
    dpi: 300
  },
  {
    id: 'nejm',
    name: 'NEJM',
    description: 'New England Journal of Medicine',
    requirements: ['Minimal color usage', 'High contrast', 'Medical-grade precision'],
    dimensions: { width: 700, height: 500 },
    dpi: 600
  },
  {
    id: 'science',
    name: 'Science',
    description: 'AAAS Science magazine format',
    requirements: ['Bold visual impact', 'Modern styling', 'High resolution'],
    dimensions: { width: 900, height: 600 },
    dpi: 300
  },
  {
    id: 'plos',
    name: 'PLOS ONE',
    description: 'Open-access scientific journal',
    requirements: ['Open format standards', 'Accessible design', 'Reproducible styling'],
    dimensions: { width: 800, height: 600 },
    dpi: 300
  }
];

const QUALITY_PROFILES = [
  {
    id: 'draft',
    name: 'Draft',
    description: 'Fast generation for exploration',
    settings: { dpi: 72, format: 'png', antialiasing: false, compression: 80 }
  },
  {
    id: 'presentation',
    name: 'Presentation',
    description: 'Balanced quality for slides',
    settings: { dpi: 150, format: 'png', antialiasing: true, compression: 60 }
  },
  {
    id: 'publication',
    name: 'Publication',
    description: 'Maximum quality for journals',
    settings: { dpi: 300, format: 'svg', antialiasing: true, compression: 20 }
  },
  {
    id: 'web',
    name: 'Web',
    description: 'Optimized for web display',
    settings: { dpi: 96, format: 'png', antialiasing: true, compression: 70 }
  }
];

const COLOR_PALETTES = [
  { id: 'colorblind_safe', name: 'Colorblind Safe', preview: ['#0173B2', '#DE8F05', '#029E73', '#CC78BC'] },
  { id: 'viridis', name: 'Viridis', preview: ['#440154', '#31688e', '#35b779', '#fde725'] },
  { id: 'plasma', name: 'Plasma', preview: ['#0d0887', '#7e03a8', '#cc4778', '#f89441'] },
  { id: 'grayscale', name: 'Grayscale', preview: ['#000000', '#404040', '#808080', '#c0c0c0'] },
  { id: 'nature', name: 'Nature Style', preview: ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728'] },
  { id: 'medical', name: 'Medical', preview: ['#2166ac', '#762a83', '#5aae61', '#e66101'] }
];

interface ChartConfigurationPanelProps {
  configuration: ChartConfiguration;
  onChange: (config: ChartConfiguration) => void;
  onValidate?: (config: ChartConfiguration) => Promise<{ valid: boolean; issues: string[] }>;
  disabled?: boolean;
}

export default function ChartConfigurationPanel({
  configuration,
  onChange,
  onValidate,
  disabled = false
}: ChartConfigurationPanelProps) {
  const { capabilities, health } = useVisualization();
  const [validationIssues, setValidationIssues] = useState<string[]>([]);
  const [isValidating, setIsValidating] = useState(false);

  // Get current journal style info
  const currentJournalStyle = useMemo(
    () => JOURNAL_STYLES.find(style => style.id === configuration.journalStyle) || JOURNAL_STYLES[0],
    [configuration.journalStyle]
  );

  // Get current quality profile
  const currentQualityProfile = useMemo(
    () => QUALITY_PROFILES.find(profile => profile.id === configuration.qualityProfile) || QUALITY_PROFILES[1],
    [configuration.qualityProfile]
  );

  // Validate configuration when it changes
  useEffect(() => {
    if (onValidate) {
      setIsValidating(true);
      onValidate(configuration)
        .then(result => {
          setValidationIssues(result.valid ? [] : result.issues);
        })
        .catch(() => {
          setValidationIssues(['Validation service unavailable']);
        })
        .finally(() => {
          setIsValidating(false);
        });
    }
  }, [configuration, onValidate]);

  // Auto-apply journal style requirements
  const handleJournalStyleChange = (styleId: string) => {
    const style = JOURNAL_STYLES.find(s => s.id === styleId);
    if (!style) return;

    const newConfig: ChartConfiguration = {
      ...configuration,
      journalStyle: styleId,
      dimensions: style.dimensions,
      dpi: style.dpi,
      accessibility: {
        ...configuration.accessibility,
        colorblindSafe: style.colorRestrictions?.includes('Colorblind-safe palette required') ?? false
      }
    };

    onChange(newConfig);
  };

  // Auto-apply quality profile settings
  const handleQualityProfileChange = (profileId: string) => {
    const profile = QUALITY_PROFILES.find(p => p.id === profileId);
    if (!profile) return;

    const newConfig: ChartConfiguration = {
      ...configuration,
      qualityProfile: profileId,
      dpi: profile.settings.dpi,
      format: profile.settings.format,
      advanced: {
        ...configuration.advanced,
        antialiasing: profile.settings.antialiasing,
        compression: profile.settings.compression
      }
    };

    onChange(newConfig);
  };

  const updateConfiguration = (updates: Partial<ChartConfiguration>) => {
    onChange({ ...configuration, ...updates });
  };

  const updateAdvanced = (updates: Partial<ChartConfiguration['advanced']>) => {
    updateConfiguration({
      advanced: { ...configuration.advanced, ...updates }
    });
  };

  const updateAccessibility = (updates: Partial<ChartConfiguration['accessibility']>) => {
    updateConfiguration({
      accessibility: { ...configuration.accessibility, ...updates }
    });
  };

  const updatePerformance = (updates: Partial<ChartConfiguration['performance']>) => {
    updateConfiguration({
      performance: { ...configuration.performance, ...updates }
    });
  };

  return (
    <div className="space-y-4">
      {/* Validation Status */}
      {isValidating && (
        <Alert>
          <Zap className="h-4 w-4" />
          <AlertDescription>Validating configuration with backend...</AlertDescription>
        </Alert>
      )}

      {validationIssues.length > 0 && (
        <Alert variant="destructive">
          <AlertTriangle className="h-4 w-4" />
          <AlertDescription>
            <div className="font-medium mb-1">Configuration Issues:</div>
            <ul className="list-disc list-inside space-y-1">
              {validationIssues.map((issue, index) => (
                <li key={index} className="text-sm">{issue}</li>
              ))}
            </ul>
          </AlertDescription>
        </Alert>
      )}

      <Tabs defaultValue="basic" className="w-full">
        <TabsList className="grid w-full grid-cols-4">
          <TabsTrigger value="basic">Basic</TabsTrigger>
          <TabsTrigger value="styling">Styling</TabsTrigger>
          <TabsTrigger value="advanced">Advanced</TabsTrigger>
          <TabsTrigger value="performance">Performance</TabsTrigger>
        </TabsList>

        <TabsContent value="basic" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Settings className="h-5 w-5" />
                Basic Configuration
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              {/* Chart Type */}
              <div className="space-y-2">
                <Label>Chart Type</Label>
                <Select 
                  value={configuration.chartType} 
                  onValueChange={(value) => updateConfiguration({ chartType: value })}
                  disabled={disabled}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {capabilities?.chart_types?.map(type => (
                      <SelectItem key={type} value={type}>
                        {type.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase())}
                      </SelectItem>
                    )) || [
                      <SelectItem key="bar_chart" value="bar_chart">Bar Chart</SelectItem>,
                      <SelectItem key="line_chart" value="line_chart">Line Chart</SelectItem>,
                      <SelectItem key="scatter_plot" value="scatter_plot">Scatter Plot</SelectItem>
                    ]}
                  </SelectContent>
                </Select>
              </div>

              {/* Journal Style */}
              <div className="space-y-2">
                <Label>Journal Style</Label>
                <Select 
                  value={configuration.journalStyle} 
                  onValueChange={handleJournalStyleChange}
                  disabled={disabled}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {JOURNAL_STYLES.map(style => (
                      <SelectItem key={style.id} value={style.id}>
                        {style.name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                <div className="text-xs text-muted-foreground">
                  {currentJournalStyle.description}
                </div>
                {currentJournalStyle.requirements.length > 0 && (
                  <div className="text-xs">
                    <div className="font-medium">Requirements:</div>
                    <ul className="list-disc list-inside ml-2">
                      {currentJournalStyle.requirements.map((req, index) => (
                        <li key={index}>{req}</li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>

              {/* Quality Profile */}
              <div className="space-y-2">
                <Label>Quality Profile</Label>
                <Select 
                  value={configuration.qualityProfile} 
                  onValueChange={handleQualityProfileChange}
                  disabled={disabled}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {QUALITY_PROFILES.map(profile => (
                      <SelectItem key={profile.id} value={profile.id}>
                        {profile.name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                <div className="text-xs text-muted-foreground">
                  {currentQualityProfile.description}
                </div>
              </div>

              {/* Dimensions */}
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label>Width (px)</Label>
                  <Input
                    type="number"
                    value={configuration.dimensions.width}
                    onChange={(e) => updateConfiguration({
                      dimensions: { ...configuration.dimensions, width: parseInt(e.target.value) || 800 }
                    })}
                    disabled={disabled}
                    min={200}
                    max={2000}
                  />
                </div>
                <div className="space-y-2">
                  <Label>Height (px)</Label>
                  <Input
                    type="number"
                    value={configuration.dimensions.height}
                    onChange={(e) => updateConfiguration({
                      dimensions: { ...configuration.dimensions, height: parseInt(e.target.value) || 600 }
                    })}
                    disabled={disabled}
                    min={200}
                    max={2000}
                  />
                </div>
              </div>

              {/* DPI & Format */}
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label>DPI</Label>
                  <Select 
                    value={configuration.dpi.toString()} 
                    onValueChange={(value) => updateConfiguration({ dpi: parseInt(value) })}
                    disabled={disabled}
                  >
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {(capabilities?.dpi_options || [72, 150, 300, 600]).map(dpi => (
                        <SelectItem key={dpi} value={dpi.toString()}>
                          {dpi} DPI
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-2">
                  <Label>Format</Label>
                  <Select 
                    value={configuration.format} 
                    onValueChange={(value) => updateConfiguration({ format: value })}
                    disabled={disabled}
                  >
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {(capabilities?.export_formats || ['png', 'svg', 'pdf']).map(format => (
                        <SelectItem key={format} value={format}>
                          {format.toUpperCase()}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="styling" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Palette className="h-5 w-5" />
                Styling Options
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              {/* Color Palette */}
              <div className="space-y-2">
                <Label>Color Palette</Label>
                <div className="grid grid-cols-1 gap-2">
                  {COLOR_PALETTES.map(palette => (
                    <button
                      key={palette.id}
                      type="button"
                      className={cn(
                        "flex items-center gap-3 p-3 border rounded-lg text-left hover:bg-muted transition-colors",
                        configuration.colorPalette === palette.id && "border-primary bg-primary/5"
                      )}
                      onClick={() => updateConfiguration({ colorPalette: palette.id })}
                      disabled={disabled}
                    >
                      <div className="flex gap-1">
                        {palette.preview.map((color, index) => (
                          <div
                            key={index}
                            className="w-4 h-4 rounded border"
                            style={{ backgroundColor: color }}
                          />
                        ))}
                      </div>
                      <div>
                        <div className="font-medium text-sm">{palette.name}</div>
                      </div>
                    </button>
                  ))}
                </div>
              </div>

              {/* Typography */}
              <div className="space-y-2">
                <Label>Font Size</Label>
                <div className="px-3">
                  <Slider
                    value={[configuration.advanced.fontSize]}
                    onValueChange={(value) => updateAdvanced({ fontSize: value[0] })}
                    min={8}
                    max={24}
                    step={1}
                    disabled={disabled}
                    className="w-full"
                  />
                  <div className="flex justify-between text-xs text-muted-foreground mt-1">
                    <span>8px</span>
                    <span>{configuration.advanced.fontSize}px</span>
                    <span>24px</span>
                  </div>
                </div>
              </div>

              {/* Line Width */}
              <div className="space-y-2">
                <Label>Line Width</Label>
                <div className="px-3">
                  <Slider
                    value={[configuration.advanced.lineWidth]}
                    onValueChange={(value) => updateAdvanced({ lineWidth: value[0] })}
                    min={0.5}
                    max={5}
                    step={0.1}
                    disabled={disabled}
                    className="w-full"
                  />
                  <div className="flex justify-between text-xs text-muted-foreground mt-1">
                    <span>0.5</span>
                    <span>{configuration.advanced.lineWidth}</span>
                    <span>5.0</span>
                  </div>
                </div>
              </div>

              {/* Display Options */}
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <Label htmlFor="show-grid">Show Grid</Label>
                  <Switch
                    id="show-grid"
                    checked={configuration.advanced.showGrid}
                    onCheckedChange={(checked) => updateAdvanced({ showGrid: checked })}
                    disabled={disabled}
                  />
                </div>
                <div className="flex items-center justify-between">
                  <Label htmlFor="show-legend">Show Legend</Label>
                  <Switch
                    id="show-legend"
                    checked={configuration.advanced.showLegend}
                    onCheckedChange={(checked) => updateAdvanced({ showLegend: checked })}
                    disabled={disabled}
                  />
                </div>
                <div className="flex items-center justify-between">
                  <Label htmlFor="transparent-bg">Transparent Background</Label>
                  <Switch
                    id="transparent-bg"
                    checked={configuration.advanced.backgroundTransparent}
                    onCheckedChange={(checked) => updateAdvanced({ backgroundTransparent: checked })}
                    disabled={disabled}
                  />
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="advanced" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Sparkles className="h-5 w-5" />
                Advanced Settings
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              {/* Rendering Options */}
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <div>
                    <Label htmlFor="antialiasing">Anti-aliasing</Label>
                    <div className="text-xs text-muted-foreground">Smooth edges and curves</div>
                  </div>
                  <Switch
                    id="antialiasing"
                    checked={configuration.advanced.antialiasing}
                    onCheckedChange={(checked) => updateAdvanced({ antialiasing: checked })}
                    disabled={disabled}
                  />
                </div>
                <div className="flex items-center justify-between">
                  <div>
                    <Label htmlFor="vectorization">Vectorization</Label>
                    <div className="text-xs text-muted-foreground">Enable vector output when possible</div>
                  </div>
                  <Switch
                    id="vectorization"
                    checked={configuration.advanced.vectorization}
                    onCheckedChange={(checked) => updateAdvanced({ vectorization: checked })}
                    disabled={disabled}
                  />
                </div>
              </div>

              {/* Compression */}
              <div className="space-y-2">
                <Label>Compression Level</Label>
                <div className="px-3">
                  <Slider
                    value={[configuration.advanced.compression]}
                    onValueChange={(value) => updateAdvanced({ compression: value[0] })}
                    min={0}
                    max={100}
                    step={5}
                    disabled={disabled}
                    className="w-full"
                  />
                  <div className="flex justify-between text-xs text-muted-foreground mt-1">
                    <span>No compression</span>
                    <span>{configuration.advanced.compression}%</span>
                    <span>Maximum</span>
                  </div>
                </div>
              </div>

              {/* Accessibility */}
              <Separator />
              <div className="space-y-3">
                <h4 className="font-medium">Accessibility</h4>
                <div className="flex items-center justify-between">
                  <div>
                    <Label htmlFor="colorblind-safe">Colorblind Safe</Label>
                    <div className="text-xs text-muted-foreground">Use colorblind-friendly palettes</div>
                  </div>
                  <Switch
                    id="colorblind-safe"
                    checked={configuration.accessibility.colorblindSafe}
                    onCheckedChange={(checked) => updateAccessibility({ colorblindSafe: checked })}
                    disabled={disabled}
                  />
                </div>
                <div className="flex items-center justify-between">
                  <div>
                    <Label htmlFor="high-contrast">High Contrast</Label>
                    <div className="text-xs text-muted-foreground">Enhanced contrast for better readability</div>
                  </div>
                  <Switch
                    id="high-contrast"
                    checked={configuration.accessibility.highContrast}
                    onCheckedChange={(checked) => updateAccessibility({ highContrast: checked })}
                    disabled={disabled}
                  />
                </div>
                <div className="flex items-center justify-between">
                  <div>
                    <Label htmlFor="large-text">Large Text</Label>
                    <div className="text-xs text-muted-foreground">Use larger font sizes</div>
                  </div>
                  <Switch
                    id="large-text"
                    checked={configuration.accessibility.largeText}
                    onCheckedChange={(checked) => updateAccessibility({ largeText: checked })}
                    disabled={disabled}
                  />
                </div>
                <div className="flex items-center justify-between">
                  <div>
                    <Label htmlFor="alt-text">Generate Alt Text</Label>
                    <div className="text-xs text-muted-foreground">Automatic accessibility descriptions</div>
                  </div>
                  <Switch
                    id="alt-text"
                    checked={configuration.accessibility.altTextGeneration}
                    onCheckedChange={(checked) => updateAccessibility({ altTextGeneration: checked })}
                    disabled={disabled}
                  />
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="performance" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Zap className="h-5 w-5" />
                Performance Settings
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <Label htmlFor="enable-caching">Enable Caching</Label>
                  <div className="text-xs text-muted-foreground">Cache results for faster regeneration</div>
                </div>
                <Switch
                  id="enable-caching"
                  checked={configuration.performance.enableCaching}
                  onCheckedChange={(checked) => updatePerformance({ enableCaching: checked })}
                  disabled={disabled}
                />
              </div>

              <div className="space-y-2">
                <Label>Priority</Label>
                <Select 
                  value={configuration.performance.priority} 
                  onValueChange={(value: 'speed' | 'quality' | 'balanced') => updatePerformance({ priority: value })}
                  disabled={disabled}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="speed">Speed (faster generation)</SelectItem>
                    <SelectItem value="balanced">Balanced (default)</SelectItem>
                    <SelectItem value="quality">Quality (slower but better)</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-2">
                <Label>Max Data Points</Label>
                <Input
                  type="number"
                  value={configuration.performance.maxDataPoints}
                  onChange={(e) => updatePerformance({ maxDataPoints: parseInt(e.target.value) || 10000 })}
                  disabled={disabled}
                  min={100}
                  max={100000}
                />
                <div className="text-xs text-muted-foreground">
                  Limit data points to improve performance
                </div>
              </div>

              {/* System Health Indicator */}
              {health && (
                <div className="pt-4 border-t">
                  <div className="text-sm font-medium mb-2">System Status</div>
                  <div className="grid grid-cols-3 gap-2 text-xs">
                    <div className="flex items-center gap-1">
                      <div className={cn(
                        "w-2 h-2 rounded-full",
                        health.components.worker.status === 'healthy' ? 'bg-green-500' : 'bg-red-500'
                      )} />
                      Worker
                    </div>
                    <div className="flex items-center gap-1">
                      <div className={cn(
                        "w-2 h-2 rounded-full",
                        health.components.cache.status === 'healthy' ? 'bg-green-500' : 'bg-red-500'
                      )} />
                      Cache
                    </div>
                    <div className="flex items-center gap-1">
                      <div className={cn(
                        "w-2 h-2 rounded-full",
                        health.components.database.healthy ? 'bg-green-500' : 'bg-red-500'
                      )} />
                      Database
                    </div>
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}