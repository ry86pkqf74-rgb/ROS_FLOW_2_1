/**
 * Figure Preview Modal
 * 
 * Detailed figure preview component with:
 * - Full metadata display
 * - High-resolution image preview
 * - Export options (PNG, SVG, PDF)
 * - PHI scan details and status
 * - Edit and duplicate actions
 * - Accessibility information
 */

import React, { useState, useEffect, useCallback } from 'react';
import { useVisualization, type Figure } from '@/hooks/useVisualization';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Separator } from '@/components/ui/separator';
import { Alert, AlertDescription } from '@/components/ui/alert';
import {
  Download,
  Edit,
  Copy,
  Trash2,
  FileImage,
  Info,
  Shield,
  ShieldAlert,
  ShieldCheck,
  Clock,
  ExternalLink,
  Zap,
  Database,
  Palette,
  Settings,
  Eye,
  Loader2
} from 'lucide-react';
import { cn, formatBytes, formatDistanceToNow } from '@/lib/utils';

interface FigurePreviewModalProps {
  figureId: string | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onEdit?: (figure: Figure) => void;
  onDelete?: (figureId: string) => void;
  onDuplicate?: (figure: Figure) => void;
}

interface FigureWithImage extends Figure {
  image_data?: string;
}

const PHI_STATUS_CONFIG = {
  'PENDING': { 
    label: 'PHI Scan Pending', 
    icon: Clock, 
    variant: 'secondary' as const,
    color: 'text-yellow-600',
    description: 'PHI compliance scan is currently in progress'
  },
  'PASS': { 
    label: 'PHI Scan Passed', 
    icon: ShieldCheck, 
    variant: 'default' as const,
    color: 'text-green-600',
    description: 'No protected health information detected'
  },
  'FAIL': { 
    label: 'PHI Detected', 
    icon: ShieldAlert, 
    variant: 'destructive' as const,
    color: 'text-red-600',
    description: 'Protected health information detected - requires review'
  },
  'OVERRIDE': { 
    label: 'PHI Override Approved', 
    icon: Shield, 
    variant: 'outline' as const,
    color: 'text-blue-600',
    description: 'PHI detected but approved for use by authorized personnel'
  }
};

export default function FigurePreviewModal({
  figureId,
  open,
  onOpenChange,
  onEdit,
  onDelete,
  onDuplicate
}: FigurePreviewModalProps) {
  const { getFigure, loading } = useVisualization();
  
  const [figure, setFigure] = useState<FigureWithImage | null>(null);
  const [imageLoading, setImageLoading] = useState(false);
  const [showFullImage, setShowFullImage] = useState(false);

  // Load figure data when modal opens
  useEffect(() => {
    if (open && figureId) {
      loadFigureData();
    } else {
      setFigure(null);
    }
  }, [open, figureId]);

  const loadFigureData = useCallback(async () => {
    if (!figureId) return;
    
    try {
      // First load metadata
      const figureData = await getFigure(figureId, false);
      setFigure(figureData);
      
      // Then load image data if needed
      if (figureData.has_image_data) {
        setImageLoading(true);
        const figureWithImage = await getFigure(figureId, true);
        setFigure(figureWithImage);
      }
    } catch (error) {
      console.error('Failed to load figure:', error);
    } finally {
      setImageLoading(false);
    }
  }, [figureId, getFigure]);

  const handleDownload = useCallback((format: 'png' | 'svg' | 'pdf') => {
    if (!figure?.image_data) return;

    const link = document.createElement('a');
    const filename = `${figure.title?.replace(/\s+/g, '_') || 'figure'}.${format}`;
    
    if (format === 'svg' && figure.image_format === 'svg') {
      // For SVG, decode base64 and create blob
      const svgData = atob(figure.image_data);
      const blob = new Blob([svgData], { type: 'image/svg+xml' });
      link.href = URL.createObjectURL(blob);
    } else {
      // For other formats, use data URL
      link.href = `data:image/${format};base64,${figure.image_data}`;
    }
    
    link.download = filename;
    link.click();
  }, [figure]);

  const handleAction = (action: 'edit' | 'delete' | 'duplicate') => {
    if (!figure) return;
    
    switch (action) {
      case 'edit':
        onEdit?.(figure);
        break;
      case 'delete':
        onDelete?.(figure.id);
        onOpenChange(false);
        break;
      case 'duplicate':
        onDuplicate?.(figure);
        break;
    }
  };

  if (!figure) {
    return (
      <Dialog open={open} onOpenChange={onOpenChange}>
        <DialogContent className="max-w-4xl">
          <div className="flex items-center justify-center h-64">
            <Loader2 className="h-8 w-8 animate-spin" />
          </div>
        </DialogContent>
      </Dialog>
    );
  }

  const phiConfig = PHI_STATUS_CONFIG[figure.phi_scan_status];

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-6xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <FileImage className="h-5 w-5" />
            {figure.title || 'Untitled Figure'}
          </DialogTitle>
          <DialogDescription>
            {figure.figure_type.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase())} • 
            Created {formatDistanceToNow(new Date(figure.created_at))} ago
          </DialogDescription>
        </DialogHeader>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Image Preview */}
          <div className="lg:col-span-2 space-y-4">
            <Card>
              <CardHeader>
                <div className="flex items-center justify-between">
                  <CardTitle className="text-base">Preview</CardTitle>
                  <div className="flex items-center gap-2">
                    <Badge variant="outline">
                      {figure.image_format?.toUpperCase()}
                    </Badge>
                    <Badge variant="outline">
                      {figure.width} × {figure.height}
                    </Badge>
                  </div>
                </div>
              </CardHeader>
              <CardContent>
                {imageLoading ? (
                  <div className="flex items-center justify-center h-64 bg-muted rounded-lg">
                    <Loader2 className="h-8 w-8 animate-spin" />
                  </div>
                ) : figure.image_data ? (
                  <div className="relative">
                    <img
                      src={`data:image/${figure.image_format};base64,${figure.image_data}`}
                      alt={figure.alt_text || 'Figure preview'}
                      className={cn(
                        "w-full h-auto rounded-lg border cursor-pointer transition-transform hover:scale-105",
                        showFullImage ? "max-h-none" : "max-h-96 object-contain"
                      )}
                      onClick={() => setShowFullImage(!showFullImage)}
                    />
                    {!showFullImage && (
                      <Button
                        variant="secondary"
                        size="sm"
                        className="absolute bottom-2 right-2"
                        onClick={() => setShowFullImage(true)}
                      >
                        <Eye className="h-4 w-4 mr-1" />
                        View Full Size
                      </Button>
                    )}
                  </div>
                ) : (
                  <div className="flex items-center justify-center h-64 bg-muted rounded-lg">
                    <div className="text-center">
                      <FileImage className="h-12 w-12 text-muted-foreground mx-auto mb-2" />
                      <p className="text-sm text-muted-foreground">
                        Image data not available
                      </p>
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>

            {/* Actions */}
            <div className="flex flex-wrap gap-2">
              <Button onClick={() => handleDownload('png')}>
                <Download className="h-4 w-4 mr-2" />
                Download PNG
              </Button>
              <Button variant="outline" onClick={() => handleDownload('svg')}>
                <Download className="h-4 w-4 mr-2" />
                Download SVG
              </Button>
              <Button variant="outline" onClick={() => handleDownload('pdf')}>
                <Download className="h-4 w-4 mr-2" />
                Download PDF
              </Button>
              <Separator orientation="vertical" className="h-10" />
              <Button variant="outline" onClick={() => handleAction('edit')}>
                <Edit className="h-4 w-4 mr-2" />
                Edit
              </Button>
              <Button variant="outline" onClick={() => handleAction('duplicate')}>
                <Copy className="h-4 w-4 mr-2" />
                Duplicate
              </Button>
              <Button 
                variant="destructive" 
                onClick={() => handleAction('delete')}
              >
                <Trash2 className="h-4 w-4 mr-2" />
                Delete
              </Button>
            </div>
          </div>

          {/* Metadata and Details */}
          <div className="space-y-4">
            {/* PHI Status */}
            <Card>
              <CardHeader>
                <CardTitle className="text-base flex items-center gap-2">
                  <Shield className="h-4 w-4" />
                  PHI Compliance
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  <div className="flex items-center gap-2">
                    <phiConfig.icon className={cn("h-4 w-4", phiConfig.color)} />
                    <Badge variant={phiConfig.variant}>
                      {phiConfig.label}
                    </Badge>
                  </div>
                  <p className="text-sm text-muted-foreground">
                    {phiConfig.description}
                  </p>
                  
                  {figure.phi_findings && figure.phi_findings.length > 0 && (
                    <Alert variant={figure.phi_scan_status === 'FAIL' ? 'destructive' : 'default'}>
                      <Info className="h-4 w-4" />
                      <AlertDescription>
                        <div className="font-medium mb-1">Scan Results:</div>
                        <ul className="list-disc list-inside space-y-1 text-xs">
                          {figure.phi_findings.map((finding, index) => (
                            <li key={index}>{finding.description || finding}</li>
                          ))}
                        </ul>
                      </AlertDescription>
                    </Alert>
                  )}
                  
                  {figure.phi_risk_level && (
                    <div className="text-sm">
                      <span className="font-medium">Risk Level:</span>{' '}
                      <Badge 
                        variant={
                          figure.phi_risk_level === 'HIGH' ? 'destructive' :
                          figure.phi_risk_level === 'MEDIUM' ? 'outline' : 'secondary'
                        }
                      >
                        {figure.phi_risk_level}
                      </Badge>
                    </div>
                  )}
                </div>
              </CardContent>
            </Card>

            {/* Technical Details */}
            <Tabs defaultValue="metadata" className="w-full">
              <TabsList className="grid w-full grid-cols-3">
                <TabsTrigger value="metadata">Details</TabsTrigger>
                <TabsTrigger value="config">Config</TabsTrigger>
                <TabsTrigger value="generation">Generation</TabsTrigger>
              </TabsList>

              <TabsContent value="metadata" className="space-y-3">
                <Card>
                  <CardContent className="pt-6">
                    <dl className="space-y-3 text-sm">
                      <div className="flex justify-between">
                        <dt className="text-muted-foreground">ID:</dt>
                        <dd className="font-mono text-xs">{figure.id}</dd>
                      </div>
                      <div className="flex justify-between">
                        <dt className="text-muted-foreground">Type:</dt>
                        <dd>{figure.figure_type.replace('_', ' ')}</dd>
                      </div>
                      <div className="flex justify-between">
                        <dt className="text-muted-foreground">Size:</dt>
                        <dd>{formatBytes(figure.size_bytes)}</dd>
                      </div>
                      <div className="flex justify-between">
                        <dt className="text-muted-foreground">DPI:</dt>
                        <dd>{figure.dpi}</dd>
                      </div>
                      <div className="flex justify-between">
                        <dt className="text-muted-foreground">Format:</dt>
                        <dd>{figure.image_format?.toUpperCase()}</dd>
                      </div>
                      <div className="flex justify-between">
                        <dt className="text-muted-foreground">Created:</dt>
                        <dd>{new Date(figure.created_at).toLocaleString()}</dd>
                      </div>
                      <div className="flex justify-between">
                        <dt className="text-muted-foreground">Updated:</dt>
                        <dd>{new Date(figure.updated_at).toLocaleString()}</dd>
                      </div>
                    </dl>
                  </CardContent>
                </Card>
              </TabsContent>

              <TabsContent value="config" className="space-y-3">
                <Card>
                  <CardContent className="pt-6">
                    <dl className="space-y-3 text-sm">
                      <div className="flex justify-between">
                        <dt className="text-muted-foreground">Journal Style:</dt>
                        <dd>{figure.journal_style || 'Default'}</dd>
                      </div>
                      <div className="flex justify-between">
                        <dt className="text-muted-foreground">Color Palette:</dt>
                        <dd>{figure.color_palette || 'Default'}</dd>
                      </div>
                      {figure.chart_config && (
                        <div>
                          <dt className="text-muted-foreground mb-2">Chart Config:</dt>
                          <ScrollArea className="h-32">
                            <pre className="text-xs font-mono bg-muted p-2 rounded">
                              {JSON.stringify(figure.chart_config, null, 2)}
                            </pre>
                          </ScrollArea>
                        </div>
                      )}
                    </dl>
                  </CardContent>
                </Card>
              </TabsContent>

              <TabsContent value="generation" className="space-y-3">
                <Card>
                  <CardContent className="pt-6">
                    <dl className="space-y-3 text-sm">
                      <div className="flex justify-between">
                        <dt className="text-muted-foreground">Generated By:</dt>
                        <dd>{figure.generated_by}</dd>
                      </div>
                      <div className="flex justify-between">
                        <dt className="text-muted-foreground">Agent Version:</dt>
                        <dd>{figure.agent_version}</dd>
                      </div>
                      <div className="flex justify-between">
                        <dt className="text-muted-foreground">Research ID:</dt>
                        <dd className="font-mono text-xs">{figure.research_id}</dd>
                      </div>
                      {figure.artifact_id && (
                        <div className="flex justify-between">
                          <dt className="text-muted-foreground">Artifact ID:</dt>
                          <dd className="font-mono text-xs">{figure.artifact_id}</dd>
                        </div>
                      )}
                      {figure.metadata && Object.keys(figure.metadata).length > 0 && (
                        <div>
                          <dt className="text-muted-foreground mb-2">Metadata:</dt>
                          <ScrollArea className="h-32">
                            <pre className="text-xs font-mono bg-muted p-2 rounded">
                              {JSON.stringify(figure.metadata, null, 2)}
                            </pre>
                          </ScrollArea>
                        </div>
                      )}
                    </dl>
                  </CardContent>
                </Card>
              </TabsContent>
            </Tabs>

            {/* Accessibility Information */}
            {figure.alt_text && (
              <Card>
                <CardHeader>
                  <CardTitle className="text-base flex items-center gap-2">
                    <Eye className="h-4 w-4" />
                    Accessibility
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-2">
                    <div>
                      <div className="text-sm font-medium">Alt Text:</div>
                      <p className="text-sm text-muted-foreground mt-1">
                        {figure.alt_text}
                      </p>
                    </div>
                  </div>
                </CardContent>
              </Card>
            )}

            {/* Caption */}
            {figure.caption && (
              <Card>
                <CardHeader>
                  <CardTitle className="text-base">Caption</CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-sm">{figure.caption}</p>
                </CardContent>
              </Card>
            )}
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}