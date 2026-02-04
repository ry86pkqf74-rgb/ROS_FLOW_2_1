/**
 * Figure Library Browser
 * 
 * Complete figure management interface with:
 * - Filtering by type, status, date
 * - Search functionality
 * - Grid/list view toggle
 * - Bulk operations
 * - PHI scan status indicators
 * - Export options
 */

import React, { useState, useEffect, useMemo, useCallback } from 'react';
import { useVisualization, type Figure, type FigureListResponse } from '@/hooks/useVisualization';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Checkbox } from '@/components/ui/checkbox';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Separator } from '@/components/ui/separator';
import { ScrollArea } from '@/components/ui/scroll-area';
import {
  Search,
  Filter,
  Grid3x3,
  List,
  Download,
  Trash2,
  Eye,
  Edit,
  Copy,
  MoreHorizontal,
  Calendar,
  FileImage,
  Shield,
  ShieldAlert,
  ShieldCheck,
  AlertTriangle,
  CheckCircle,
  Clock,
  Loader2,
  RefreshCw,
  Settings
} from 'lucide-react';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { cn } from '@/lib/utils';
import { formatBytes, formatDistanceToNow } from '@/lib/utils';

interface FigureLibraryBrowserProps {
  researchId: string;
  onFigureSelect?: (figure: Figure) => void;
  onFigureEdit?: (figure: Figure) => void;
  onFigurePreview?: (figure: Figure) => void;
  className?: string;
}

type ViewMode = 'grid' | 'list';
type SortBy = 'created_at' | 'title' | 'size_bytes' | 'figure_type';
type SortOrder = 'asc' | 'desc';

interface Filters {
  figureType: string;
  phiScanStatus: string;
  dateRange: string;
  search: string;
}

const PHI_STATUS_CONFIG = {
  'PENDING': { 
    label: 'Pending', 
    icon: Clock, 
    variant: 'secondary' as const, 
    description: 'PHI scan in progress' 
  },
  'PASS': { 
    label: 'Passed', 
    icon: ShieldCheck, 
    variant: 'default' as const, 
    description: 'No PHI detected' 
  },
  'FAIL': { 
    label: 'Failed', 
    icon: ShieldAlert, 
    variant: 'destructive' as const, 
    description: 'PHI detected - requires review' 
  },
  'OVERRIDE': { 
    label: 'Override', 
    icon: Shield, 
    variant: 'outline' as const, 
    description: 'PHI detected but approved for use' 
  }
};

const FIGURE_TYPE_ICONS = {
  'bar_chart': '📊',
  'line_chart': '📈',
  'scatter_plot': '⚬',
  'box_plot': '☐',
  'histogram': '▥',
  'heatmap': '▦',
  'violin': '🎻',
  'kaplan_meier': '📉'
};

export default function FigureLibraryBrowser({
  researchId,
  onFigureSelect,
  onFigureEdit,
  onFigurePreview,
  className
}: FigureLibraryBrowserProps) {
  const { listFigures, getFigureStats, deleteFigure, loading } = useVisualization();

  // State management
  const [figures, setFigures] = useState<Figure[]>([]);
  const [selectedFigures, setSelectedFigures] = useState<Set<string>>(new Set());
  const [viewMode, setViewMode] = useState<ViewMode>('grid');
  const [sortBy, setSortBy] = useState<SortBy>('created_at');
  const [sortOrder, setSortOrder] = useState<SortOrder>('desc');
  const [filters, setFilters] = useState<Filters>({
    figureType: 'all',
    phiScanStatus: 'all',
    dateRange: 'all',
    search: ''
  });
  const [pagination, setPagination] = useState({
    limit: 20,
    offset: 0,
    total: 0
  });
  const [stats, setStats] = useState<any>(null);
  const [isRefreshing, setIsRefreshing] = useState(false);

  // Load figures
  const loadFigures = useCallback(async () => {
    try {
      const options: any = {
        limit: pagination.limit,
        offset: pagination.offset
      };

      if (filters.figureType !== 'all') {
        options.figure_type = filters.figureType;
      }
      if (filters.phiScanStatus !== 'all') {
        options.phi_scan_status = filters.phiScanStatus;
      }

      const response = await listFigures(researchId, options);
      setFigures(response.figures);
      setPagination(prev => ({ ...prev, total: response.total }));
    } catch (error) {
      console.error('Failed to load figures:', error);
    }
  }, [researchId, pagination.limit, pagination.offset, filters, listFigures]);

  // Load stats
  const loadStats = useCallback(async () => {
    try {
      const response = await getFigureStats(researchId);
      setStats(response.statistics);
    } catch (error) {
      console.error('Failed to load figure stats:', error);
    }
  }, [researchId, getFigureStats]);

  // Initial load
  useEffect(() => {
    loadFigures();
    loadStats();
  }, [loadFigures, loadStats]);

  // Refresh data
  const handleRefresh = useCallback(async () => {
    setIsRefreshing(true);
    await Promise.all([loadFigures(), loadStats()]);
    setIsRefreshing(false);
  }, [loadFigures, loadStats]);

  // Filter and sort figures
  const filteredAndSortedFigures = useMemo(() => {
    let filtered = figures;

    // Apply search filter
    if (filters.search) {
      const searchLower = filters.search.toLowerCase();
      filtered = filtered.filter(figure => 
        figure.title?.toLowerCase().includes(searchLower) ||
        figure.caption?.toLowerCase().includes(searchLower) ||
        figure.figure_type.toLowerCase().includes(searchLower)
      );
    }

    // Apply date filter
    if (filters.dateRange !== 'all') {
      const now = new Date();
      const cutoff = new Date();
      
      switch (filters.dateRange) {
        case 'today':
          cutoff.setHours(0, 0, 0, 0);
          break;
        case 'week':
          cutoff.setDate(now.getDate() - 7);
          break;
        case 'month':
          cutoff.setMonth(now.getMonth() - 1);
          break;
      }
      
      filtered = filtered.filter(figure => 
        new Date(figure.created_at) >= cutoff
      );
    }

    // Sort figures
    filtered.sort((a, b) => {
      let aValue: any = a[sortBy];
      let bValue: any = b[sortBy];

      if (sortBy === 'created_at') {
        aValue = new Date(aValue).getTime();
        bValue = new Date(bValue).getTime();
      }

      if (sortOrder === 'desc') {
        return bValue > aValue ? 1 : -1;
      } else {
        return aValue > bValue ? 1 : -1;
      }
    });

    return filtered;
  }, [figures, filters, sortBy, sortOrder]);

  // Handle figure selection
  const toggleFigureSelection = (figureId: string) => {
    const newSelected = new Set(selectedFigures);
    if (newSelected.has(figureId)) {
      newSelected.delete(figureId);
    } else {
      newSelected.add(figureId);
    }
    setSelectedFigures(newSelected);
  };

  const selectAllFigures = () => {
    setSelectedFigures(new Set(filteredAndSortedFigures.map(f => f.id)));
  };

  const clearSelection = () => {
    setSelectedFigures(new Set());
  };

  // Handle bulk operations
  const handleBulkDelete = async () => {
    if (selectedFigures.size === 0) return;
    
    try {
      await Promise.all(
        Array.from(selectedFigures).map(figureId => deleteFigure(figureId))
      );
      clearSelection();
      await handleRefresh();
    } catch (error) {
      console.error('Bulk delete failed:', error);
    }
  };

  const handleBulkExport = async (format: 'png' | 'svg' | 'pdf') => {
    // Implementation for bulk export
    console.log('Bulk export:', Array.from(selectedFigures), 'as', format);
  };

  // Handle individual figure actions
  const handleFigureAction = (figure: Figure, action: string) => {
    switch (action) {
      case 'view':
        onFigurePreview?.(figure);
        break;
      case 'edit':
        onFigureEdit?.(figure);
        break;
      case 'select':
        onFigureSelect?.(figure);
        break;
      case 'delete':
        deleteFigure(figure.id).then(() => handleRefresh());
        break;
      case 'duplicate':
        // Implementation for duplication
        console.log('Duplicate figure:', figure.id);
        break;
      default:
        break;
    }
  };

  const getPHIStatusBadge = (status: string) => {
    const config = PHI_STATUS_CONFIG[status as keyof typeof PHI_STATUS_CONFIG];
    if (!config) return null;

    const Icon = config.icon;
    return (
      <Badge variant={config.variant} className="text-xs">
        <Icon className="h-3 w-3 mr-1" />
        {config.label}
      </Badge>
    );
  };

  const FigureCard = ({ figure }: { figure: Figure }) => (
    <Card className={cn(
      "cursor-pointer hover:shadow-md transition-shadow",
      selectedFigures.has(figure.id) && "ring-2 ring-primary"
    )}>
      <CardHeader className="pb-2">
        <div className="flex items-start justify-between">
          <div className="flex items-center gap-2">
            <Checkbox
              checked={selectedFigures.has(figure.id)}
              onCheckedChange={() => toggleFigureSelection(figure.id)}
              onClick={(e) => e.stopPropagation()}
            />
            <div className="text-lg">
              {FIGURE_TYPE_ICONS[figure.figure_type as keyof typeof FIGURE_TYPE_ICONS] || '📊'}
            </div>
          </div>
          <div className="flex items-center gap-1">
            {getPHIStatusBadge(figure.phi_scan_status)}
            <DropdownMenu>
              <DropdownMenuTrigger asChild onClick={(e) => e.stopPropagation()}>
                <Button variant="ghost" size="sm">
                  <MoreHorizontal className="h-4 w-4" />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end">
                <DropdownMenuItem onClick={() => handleFigureAction(figure, 'view')}>
                  <Eye className="h-4 w-4 mr-2" />
                  Preview
                </DropdownMenuItem>
                <DropdownMenuItem onClick={() => handleFigureAction(figure, 'edit')}>
                  <Edit className="h-4 w-4 mr-2" />
                  Edit
                </DropdownMenuItem>
                <DropdownMenuItem onClick={() => handleFigureAction(figure, 'duplicate')}>
                  <Copy className="h-4 w-4 mr-2" />
                  Duplicate
                </DropdownMenuItem>
                <DropdownMenuSeparator />
                <DropdownMenuItem 
                  onClick={() => handleFigureAction(figure, 'delete')}
                  className="text-destructive"
                >
                  <Trash2 className="h-4 w-4 mr-2" />
                  Delete
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
        </div>
      </CardHeader>
      <CardContent onClick={() => handleFigureAction(figure, 'select')}>
        <div className="space-y-2">
          <div>
            <div className="font-medium text-sm line-clamp-2">
              {figure.title || 'Untitled Chart'}
            </div>
            <div className="text-xs text-muted-foreground">
              {figure.figure_type.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase())}
            </div>
          </div>
          
          <div className="text-xs text-muted-foreground">
            {formatDistanceToNow(new Date(figure.created_at))} ago
          </div>
          
          <div className="flex items-center justify-between text-xs">
            <span>{formatBytes(figure.size_bytes)}</span>
            <span>{figure.image_format?.toUpperCase()}</span>
          </div>

          {figure.caption && (
            <div className="text-xs text-muted-foreground line-clamp-2">
              {figure.caption}
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );

  const FigureListItem = ({ figure }: { figure: Figure }) => (
    <div className={cn(
      "flex items-center gap-4 p-3 border rounded-lg hover:bg-muted/50 transition-colors",
      selectedFigures.has(figure.id) && "bg-primary/5 border-primary"
    )}>
      <Checkbox
        checked={selectedFigures.has(figure.id)}
        onCheckedChange={() => toggleFigureSelection(figure.id)}
      />
      
      <div className="text-xl">
        {FIGURE_TYPE_ICONS[figure.figure_type as keyof typeof FIGURE_TYPE_ICONS] || '📊'}
      </div>
      
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 mb-1">
          <div className="font-medium truncate">
            {figure.title || 'Untitled Chart'}
          </div>
          {getPHIStatusBadge(figure.phi_scan_status)}
        </div>
        <div className="text-sm text-muted-foreground">
          {figure.figure_type.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase())} • 
          {formatBytes(figure.size_bytes)} • 
          {formatDistanceToNow(new Date(figure.created_at))} ago
        </div>
      </div>
      
      <div className="flex items-center gap-2">
        <Button 
          variant="outline" 
          size="sm"
          onClick={() => handleFigureAction(figure, 'view')}
        >
          <Eye className="h-4 w-4" />
        </Button>
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" size="sm">
              <MoreHorizontal className="h-4 w-4" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            <DropdownMenuItem onClick={() => handleFigureAction(figure, 'edit')}>
              <Edit className="h-4 w-4 mr-2" />
              Edit
            </DropdownMenuItem>
            <DropdownMenuItem onClick={() => handleFigureAction(figure, 'duplicate')}>
              <Copy className="h-4 w-4 mr-2" />
              Duplicate
            </DropdownMenuItem>
            <DropdownMenuSeparator />
            <DropdownMenuItem 
              onClick={() => handleFigureAction(figure, 'delete')}
              className="text-destructive"
            >
              <Trash2 className="h-4 w-4 mr-2" />
              Delete
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    </div>
  );

  return (
    <div className={cn("space-y-4", className)}>
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-semibold">Figure Library</h2>
          <p className="text-muted-foreground">
            Manage and organize your research visualizations
          </p>
        </div>
        <Button onClick={handleRefresh} disabled={isRefreshing}>
          <RefreshCw className={cn("h-4 w-4 mr-2", isRefreshing && "animate-spin")} />
          Refresh
        </Button>
      </div>

      {/* Statistics */}
      {stats && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <Card>
            <CardContent className="p-4">
              <div className="text-2xl font-bold">{stats.total}</div>
              <div className="text-sm text-muted-foreground">Total Figures</div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="p-4">
              <div className="text-2xl font-bold">{stats.size_mb}</div>
              <div className="text-sm text-muted-foreground">Total Size</div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="p-4">
              <div className="text-2xl font-bold">
                {stats.by_status?.PASS || 0}
              </div>
              <div className="text-sm text-muted-foreground">PHI Cleared</div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="p-4">
              <div className="text-2xl font-bold">
                {Object.keys(stats.by_type || {}).length}
              </div>
              <div className="text-sm text-muted-foreground">Chart Types</div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Filters and Controls */}
      <div className="flex flex-col sm:flex-row gap-4 items-start sm:items-center justify-between">
        <div className="flex flex-wrap gap-2">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <Input
              placeholder="Search figures..."
              value={filters.search}
              onChange={(e) => setFilters(prev => ({ ...prev, search: e.target.value }))}
              className="pl-9 w-64"
            />
          </div>
          
          <Select
            value={filters.figureType}
            onValueChange={(value) => setFilters(prev => ({ ...prev, figureType: value }))}
          >
            <SelectTrigger className="w-32">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Types</SelectItem>
              <SelectItem value="bar_chart">Bar Chart</SelectItem>
              <SelectItem value="line_chart">Line Chart</SelectItem>
              <SelectItem value="scatter_plot">Scatter Plot</SelectItem>
              <SelectItem value="box_plot">Box Plot</SelectItem>
            </SelectContent>
          </Select>
          
          <Select
            value={filters.phiScanStatus}
            onValueChange={(value) => setFilters(prev => ({ ...prev, phiScanStatus: value }))}
          >
            <SelectTrigger className="w-32">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Status</SelectItem>
              <SelectItem value="PENDING">Pending</SelectItem>
              <SelectItem value="PASS">Passed</SelectItem>
              <SelectItem value="FAIL">Failed</SelectItem>
              <SelectItem value="OVERRIDE">Override</SelectItem>
            </SelectContent>
          </Select>

          <Select
            value={filters.dateRange}
            onValueChange={(value) => setFilters(prev => ({ ...prev, dateRange: value }))}
          >
            <SelectTrigger className="w-32">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Time</SelectItem>
              <SelectItem value="today">Today</SelectItem>
              <SelectItem value="week">This Week</SelectItem>
              <SelectItem value="month">This Month</SelectItem>
            </SelectContent>
          </Select>
        </div>

        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => setViewMode('grid')}
            className={cn(viewMode === 'grid' && "bg-muted")}
          >
            <Grid3x3 className="h-4 w-4" />
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={() => setViewMode('list')}
            className={cn(viewMode === 'list' && "bg-muted")}
          >
            <List className="h-4 w-4" />
          </Button>
        </div>
      </div>

      {/* Bulk Actions */}
      {selectedFigures.size > 0 && (
        <div className="flex items-center justify-between p-3 bg-muted rounded-lg">
          <div className="flex items-center gap-2">
            <span className="text-sm font-medium">
              {selectedFigures.size} figure{selectedFigures.size > 1 ? 's' : ''} selected
            </span>
            <Button variant="ghost" size="sm" onClick={clearSelection}>
              Clear
            </Button>
          </div>
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => handleBulkExport('png')}
            >
              <Download className="h-4 w-4 mr-1" />
              Export PNG
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => handleBulkExport('svg')}
            >
              <Download className="h-4 w-4 mr-1" />
              Export SVG
            </Button>
            <Button
              variant="destructive"
              size="sm"
              onClick={handleBulkDelete}
            >
              <Trash2 className="h-4 w-4 mr-1" />
              Delete
            </Button>
          </div>
        </div>
      )}

      {/* Figures Display */}
      {loading ? (
        <div className="flex items-center justify-center h-64">
          <Loader2 className="h-8 w-8 animate-spin" />
        </div>
      ) : filteredAndSortedFigures.length === 0 ? (
        <div className="text-center py-12">
          <FileImage className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
          <h3 className="text-lg font-medium mb-2">No figures found</h3>
          <p className="text-muted-foreground">
            {filters.search || filters.figureType !== 'all' || filters.phiScanStatus !== 'all'
              ? 'Try adjusting your filters'
              : 'Create your first visualization to get started'}
          </p>
        </div>
      ) : (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div className="text-sm text-muted-foreground">
              Showing {filteredAndSortedFigures.length} of {pagination.total} figures
            </div>
            <div className="flex items-center gap-2">
              <Select
                value={sortBy}
                onValueChange={(value: SortBy) => setSortBy(value)}
              >
                <SelectTrigger className="w-32">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="created_at">Date</SelectItem>
                  <SelectItem value="title">Title</SelectItem>
                  <SelectItem value="figure_type">Type</SelectItem>
                  <SelectItem value="size_bytes">Size</SelectItem>
                </SelectContent>
              </Select>
              <Button
                variant="outline"
                size="sm"
                onClick={() => setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc')}
              >
                {sortOrder === 'asc' ? '↑' : '↓'}
              </Button>
            </div>
          </div>

          {viewMode === 'grid' ? (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
              {filteredAndSortedFigures.map(figure => (
                <FigureCard key={figure.id} figure={figure} />
              ))}
            </div>
          ) : (
            <div className="space-y-2">
              {filteredAndSortedFigures.map(figure => (
                <FigureListItem key={figure.id} figure={figure} />
              ))}
            </div>
          )}
        </div>
      )}

      {/* Pagination */}
      {pagination.total > pagination.limit && (
        <div className="flex items-center justify-center gap-2">
          <Button
            variant="outline"
            disabled={pagination.offset === 0}
            onClick={() => setPagination(prev => ({ 
              ...prev, 
              offset: Math.max(0, prev.offset - prev.limit) 
            }))}
          >
            Previous
          </Button>
          <span className="text-sm text-muted-foreground">
            Page {Math.floor(pagination.offset / pagination.limit) + 1} of{' '}
            {Math.ceil(pagination.total / pagination.limit)}
          </span>
          <Button
            variant="outline"
            disabled={pagination.offset + pagination.limit >= pagination.total}
            onClick={() => setPagination(prev => ({ 
              ...prev, 
              offset: prev.offset + prev.limit 
            }))}
          >
            Next
          </Button>
        </div>
      )}
    </div>
  );
}