/**
 * Visualization Components Index
 * Export chart builder and related components.
 */

// Chart Builders
export { InteractiveChartBuilder } from './InteractiveChartBuilder';
export type { ChartBuilderProps, ChartSuggestion, BuilderChartType } from './InteractiveChartBuilder';
export { default as ProductionChartGenerator } from './ProductionChartGenerator';
export { MercuryChartGenerator } from './MercuryChartGenerator';
export type { MercuryChartConfig, MercuryChartGeneratorProps } from './MercuryChartGenerator';

// Configuration and Styling
export { default as ChartConfigurationPanel } from './ChartConfigurationPanel';
export type { ChartConfiguration } from './ChartConfigurationPanel';
export { VariableDropZone } from './VariableDropZone';
export type { VariableDropZoneProps } from './VariableDropZone';
export { ChartStylePanel } from './ChartStylePanel';
export type { ChartStylePanelProps } from './ChartStylePanel';

// Figure Management
export { default as FigureLibraryBrowser } from './FigureLibraryBrowser';
export { default as FigurePreviewModal } from './FigurePreviewModal';

// Dashboard and Monitoring
export { default as VisualizationDashboard } from './VisualizationDashboard';
