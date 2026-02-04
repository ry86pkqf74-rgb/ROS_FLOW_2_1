# Statistical Analysis Components - Stage 7

This document describes the frontend components implemented for Stage 7 of the ResearchFlow Statistical Analysis system.

## Overview

The Stage 7 frontend integration provides a complete user interface for configuring, executing, and visualizing statistical analyses. The components work together to create a seamless workflow from data input to results export.

## Components

### 1. StatisticalAnalysisForm.tsx

**Purpose**: Comprehensive form for configuring statistical analyses with guided test selection and variable assignment.

**Key Features**:
- Tabbed interface for step-by-step configuration
- Dynamic test type selection based on available data
- Real-time validation with helpful error messages
- Variable assignment with type checking
- Advanced options for each test type
- Progress tracking and completion indicators

**Usage**:
```tsx
import { StatisticalAnalysisForm } from '@/components/analysis';

<StatisticalAnalysisForm
  datasetMetadata={metadata}
  onSubmit={handleAnalysisSubmit}
  onValidationChange={handleValidationChange}
  disabled={isExecuting}
/>
```

**Props**:
- `datasetMetadata`: Dataset structure and column information
- `initialConfig`: Pre-filled configuration for editing
- `onSubmit`: Called when valid configuration is submitted
- `onValidationChange`: Called when validation state changes
- `disabled`: Disables form during analysis execution

### 2. StatisticalResults.tsx

**Purpose**: Comprehensive results display with tabbed interface for different aspects of statistical analysis.

**Key Features**:
- Tabbed organization (Summary, Descriptive, Inferential, Assumptions, Visualizations)
- Interactive results exploration
- APA-formatted text generation
- Assumption checking with interpretations
- Effect size display and interpretation
- Export functionality integration

**Usage**:
```tsx
import { StatisticalResults } from '@/components/analysis';

<StatisticalResults
  results={analysisResults}
  preferences={displayPreferences}
  onExport={handleExport}
  onCopy={handleCopy}
/>
```

**Props**:
- `results`: Complete statistical analysis results
- `preferences`: Display customization options
- `onExport`: Export handler function
- `onCopy`: Copy to clipboard handler

### 3. VisualizationRenderer.tsx

**Purpose**: Renders statistical visualizations including Q-Q plots, histograms, boxplots, and scatter plots.

**Key Features**:
- Support for multiple chart types
- Interactive visualizations with zoom/pan
- Grid and list view modes
- Type filtering and customization
- Export functionality for individual charts
- Responsive design

**Supported Visualizations**:
- Q-Q plots for normality checking
- Histograms with normal curve overlays
- Box plots for group comparisons
- Scatter plots with regression lines
- Bar plots for categorical data
- Forest plots for effect sizes

**Usage**:
```tsx
import { VisualizationRenderer } from '@/components/analysis';

<VisualizationRenderer
  visualizations={chartData}
  preferences={{ types: ['qq-plot', 'histogram'], gridCols: 2 }}
  onExport={handleChartExport}
/>
```

### 4. StatisticalExportPanel.tsx

**Purpose**: Specialized export functionality for statistical analysis results with multiple format support.

**Key Features**:
- Multiple export formats (PDF, DOCX, HTML, CSV, JSON)
- Customizable content sections
- Template selection for reports
- Quick export presets
- Progress tracking and download management
- Export tips and recommendations

**Export Formats**:
- **PDF**: Publication-ready formatted reports
- **DOCX**: Editable Microsoft Word documents
- **HTML**: Interactive web reports
- **CSV**: Raw data and statistics
- **JSON**: Complete machine-readable format

**Usage**:
```tsx
import { StatisticalExportPanel } from '@/components/analysis';

<StatisticalExportPanel
  results={analysisResults}
  onExport={handleExportRequest}
  isExporting={exportInProgress}
/>
```

### 5. StatisticalAnalysisIntegration.tsx

**Purpose**: Main orchestration component that manages the complete workflow from configuration to export.

**Key Features**:
- Workflow state management
- Progress tracking across all phases
- Error handling and recovery
- Component integration
- API communication

**Workflow Steps**:
1. **Loading**: Dataset metadata retrieval
2. **Configure**: Analysis setup using StatisticalAnalysisForm
3. **Executing**: Analysis execution with progress tracking
4. **Results**: Results display using StatisticalResults
5. **Export**: Export functionality using StatisticalExportPanel

**Usage**:
```tsx
import { StatisticalAnalysisIntegration } from '@/components/analysis';

<StatisticalAnalysisIntegration
  datasetId="dataset-123"
  researchId="research-456"
  onAnalysisComplete={handleComplete}
  onExport={handleExport}
  initialConfig={existingConfig}
/>
```

## Hooks

### useStatisticalAnalysis

**Purpose**: React hook for managing statistical analysis operations.

**Features**:
- Configuration validation
- Analysis execution
- Dataset metadata retrieval
- Results export
- Error handling
- Loading state management

**Usage**:
```tsx
import { useStatisticalAnalysis } from '@/hooks/use-statistical-analysis';

const {
  results,
  isLoading,
  error,
  validateConfig,
  executeAnalysis,
  exportAnalysis
} = useStatisticalAnalysis();
```

## Data Flow

```
Dataset Upload/Selection
        ↓
StatisticalAnalysisForm (Configuration)
        ↓
API Validation & Execution
        ↓
StatisticalResults (Display)
        ↓
VisualizationRenderer (Charts)
        ↓
StatisticalExportPanel (Export)
```

## API Integration

The components integrate with the following API endpoints:

- `POST /api/v1/statistical-analysis/validate` - Configuration validation
- `POST /api/v1/statistical-analysis/execute` - Analysis execution
- `GET /api/v1/statistical-analysis/datasets/{id}/metadata` - Dataset metadata
- `POST /api/v1/statistical-analysis/export` - Results export

## Error Handling

All components include comprehensive error handling:

- **Validation Errors**: Real-time feedback during configuration
- **Execution Errors**: Graceful handling of analysis failures
- **Network Errors**: Timeout and connectivity error handling
- **Data Errors**: Missing data and quality issue reporting

## Accessibility

Components are designed with accessibility in mind:

- **Keyboard Navigation**: Full keyboard support
- **Screen Readers**: Proper ARIA labels and descriptions
- **High Contrast**: Support for high contrast themes
- **Focus Management**: Logical focus flow

## Testing

Each component includes:

- **Unit Tests**: Component-level testing with mocked dependencies
- **Integration Tests**: Multi-component workflow testing
- **E2E Tests**: Complete user journey validation
- **Accessibility Tests**: WCAG compliance verification

## Performance Considerations

- **Lazy Loading**: Components load only when needed
- **Memoization**: Expensive calculations are memoized
- **Virtualization**: Large datasets use virtual scrolling
- **Debouncing**: API calls are debounced to prevent spam

## Future Enhancements

Planned improvements for future releases:

1. **Real-time Collaboration**: Multi-user analysis sessions
2. **Advanced Visualizations**: 3D plots and interactive diagrams
3. **Machine Learning Integration**: Automated test selection
4. **Custom Templates**: User-defined export templates
5. **Audit Trail**: Complete analysis history tracking

## Examples

### Basic T-test Analysis

```tsx
function TTestExample() {
  return (
    <StatisticalAnalysisIntegration
      datasetId="clinical-trial-001"
      researchId="study-123"
      onAnalysisComplete={(results) => {
        console.log('T-test completed:', results);
      }}
      showAdvanced={false}
    />
  );
}
```

### ANOVA with Custom Export

```tsx
function ANOVAExample() {
  const handleExport = async (filename, downloadUrl) => {
    // Custom export handling
    await fetch(downloadUrl)
      .then(response => response.blob())
      .then(blob => {
        // Save or process the exported file
      });
  };

  return (
    <StatisticalAnalysisIntegration
      datasetId="multi-group-study"
      researchId="anova-analysis"
      onExport={handleExport}
      initialConfig={{
        testType: 'anova-one-way',
        variables: [
          { name: 'outcome', type: 'continuous', role: 'dependent' },
          { name: 'group', type: 'categorical', role: 'grouping' }
        ],
        confidenceLevel: 0.95,
        alpha: 0.05
      }}
    />
  );
}
```

## Troubleshooting

### Common Issues

1. **Validation Errors**: Check dataset column types and missing values
2. **Analysis Failures**: Verify dataset quality and assumption requirements
3. **Export Problems**: Check network connectivity and file permissions
4. **Performance Issues**: Consider dataset size and complexity

### Debug Mode

Enable debug mode for detailed logging:

```tsx
<StatisticalAnalysisIntegration
  datasetId={id}
  researchId={researchId}
  debug={process.env.NODE_ENV === 'development'}
/>
```

## Support

For technical support:

- Check the component documentation
- Review error messages and suggestions
- Test with demo datasets
- Contact the development team

---

This documentation covers the main statistical analysis components implemented in Stage 7. For implementation details, see the individual component files and their inline documentation.