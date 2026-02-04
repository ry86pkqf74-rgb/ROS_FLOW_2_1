# Data Visualization Integration Guide

## ✅ What's Complete

### Backend (Worker Service)
- ✅ `DataVisualizationAgent` - 7 chart types fully implemented
- ✅ API endpoints in `services/worker/src/api/routes/visualization.py`
- ✅ Request/Response models with Pydantic validation
- ✅ Database schema in `packages/core/migrations/0015_add_figures_table.sql`
- ✅ Test script: `services/worker/test_mercury_rendering.py`

### Validation Results
```bash
cd services/worker
python3 test_mercury_rendering.py
# Result: ✅ ALL RENDERING TESTS PASSED
```

## 🚀 Quick Start (No Docker Required)

### 1. Test the Rendering
```bash
cd services/worker
python3 test_mercury_rendering.py
```

### 2. Check API Routes
```bash
cd services/worker
python3 test_visualization_api.py
```

### 3. Run Database Migration
```sql
-- Apply the figures table migration
psql -d researchflow_db -f packages/core/migrations/0015_add_figures_table.sql
```

## 📋 Next Steps for Full Integration

### Phase 1: Orchestrator Routes (1 hour)

Create `services/orchestrator/src/routes/visualization.ts`:

```typescript
import { Router } from 'express';
import axios from 'axios';

const router = Router();

router.post('/api/visualization/bar-chart', async (req, res) => {
  try {
    const response = await axios.post(
      `${process.env.WORKER_URL}/api/visualization/bar-chart`,
      req.body
    );
    res.json(response.data);
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// Add similar routes for: line-chart, scatter-plot, box-plot

router.get('/api/visualization/capabilities', async (req, res) => {
  const response = await axios.get(
    `${process.env.WORKER_URL}/api/visualization/capabilities`
  );
  res.json(response.data);
});

export default router;
```

Register in `services/orchestrator/src/index.ts`:
```typescript
import visualizationRoutes from './routes/visualization';
app.use(visualizationRoutes);
```

### Phase 2: Frontend Component (2 hours)

Create `services/web/src/components/visualization/ChartGenerator.tsx`:

```typescript
import React, { useState } from 'react';
import { Card, CardHeader, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';

interface ChartData {
  imageBase64?: string;
  caption?: string;
  altText?: string;
}

export function ChartGenerator() {
  const [chartType, setChartType] = useState('bar_chart');
  const [chartData, setChartData] = useState<ChartData | null>(null);
  const [loading, setLoading] = useState(false);

  const generateChart = async () => {
    setLoading(true);
    try {
      const response = await fetch('/api/visualization/bar-chart', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          data: {
            group: ['Control', 'Treatment A', 'Treatment B'],
            value: [5.2, 6.8, 7.3],
            std: [1.1, 1.3, 1.0],
          },
          title: 'Treatment Outcomes',
          x_label: 'Group',
          y_label: 'Pain Score (0-10)',
          show_error_bars: true,
          color_palette: 'colorblind_safe',
          dpi: 300,
        }),
      });
      const data = await response.json();
      setChartData(data);
    } catch (error) {
      console.error('Chart generation failed:', error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <Card>
      <CardHeader>
        <h2 className="text-2xl font-bold">Generate Chart</h2>
      </CardHeader>
      <CardContent className="space-y-4">
        <Select value={chartType} onValueChange={setChartType}>
          <SelectTrigger>
            <SelectValue placeholder="Select chart type" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="bar_chart">Bar Chart</SelectItem>
            <SelectItem value="line_chart">Line Chart</SelectItem>
            <SelectItem value="scatter_plot">Scatter Plot</SelectItem>
            <SelectItem value="box_plot">Box Plot</SelectItem>
          </SelectContent>
        </Select>

        <Button onClick={generateChart} disabled={loading}>
          {loading ? 'Generating...' : 'Generate Chart'}
        </Button>

        {chartData?.imageBase64 && (
          <div className="mt-4 space-y-2">
            <img
              src={`data:image/png;base64,${chartData.imageBase64}`}
              alt={chartData.altText || 'Generated chart'}
              className="w-full border rounded"
            />
            {chartData.caption && (
              <p className="text-sm text-gray-600 italic">{chartData.caption}</p>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
```

### Phase 3: Database Schema (Already Complete ✅)

The migration file exists at:
`packages/core/migrations/0015_add_figures_table.sql`

Apply it:
```bash
# If using Drizzle
npm run db:push

# Or manually
psql -d researchflow_db -f packages/core/migrations/0015_add_figures_table.sql
```

### Phase 4: TypeScript Schema (30 minutes)

Add to `packages/core/types/schema.ts`:

```typescript
// Figure Types
export const FIGURE_TYPES = [
  "bar_chart",
  "line_chart", 
  "scatter_plot",
  "box_plot",
  "kaplan_meier",
  "forest_plot",
  "flowchart",
] as const;
export type FigureType = (typeof FIGURE_TYPES)[number];

// Figures Table
export const figures = pgTable("figures", {
  id: varchar("id").primaryKey().default(sql`gen_random_uuid()`),
  researchId: varchar("research_id").notNull(),
  artifactId: varchar("artifact_id").references(() => artifacts.id, { onDelete: "cascade" }),
  
  figureType: varchar("figure_type", { length: 50 }).notNull(),
  title: text("title"),
  caption: text("caption"),
  altText: text("alt_text"),
  
  imageData: text("image_data").notNull(), // Base64 or bytea
  imageFormat: varchar("image_format", { length: 10 }).default("png").notNull(),
  sizeBytes: integer("size_bytes").notNull(),
  width: integer("width"),
  height: integer("height"),
  dpi: integer("dpi").default(300),
  
  chartConfig: jsonb("chart_config").default({}).notNull(),
  journalStyle: varchar("journal_style", { length: 50 }),
  colorPalette: varchar("color_palette", { length: 50 }),
  
  sourceDataRef: varchar("source_data_ref"),
  sourceDataHash: varchar("source_data_hash", { length: 64 }),
  
  generatedBy: varchar("generated_by").notNull(),
  generationDurationMs: integer("generation_duration_ms"),
  agentVersion: varchar("agent_version", { length: 20 }).default("1.0.0"),
  
  phiScanStatus: varchar("phi_scan_status", { length: 20 }).default("PENDING"),
  phiRiskLevel: varchar("phi_risk_level", { length: 20 }),
  phiFindings: jsonb("phi_findings").default([]).notNull(),
  
  createdAt: timestamp("created_at").default(sql`CURRENT_TIMESTAMP`).notNull(),
  updatedAt: timestamp("updated_at").default(sql`CURRENT_TIMESTAMP`).notNull(),
  deletedAt: timestamp("deleted_at"),
  metadata: jsonb("metadata").default({}).notNull(),
});

export const insertFigureSchema = createInsertSchema(figures).omit({
  id: true,
  createdAt: true,
  updatedAt: true,
  deletedAt: true,
} as any);

export type Figure = InferSelectModel<typeof figures>;
export type InsertFigure = z.infer<typeof insertFigureSchema>;
```

## 📚 Available Endpoints

### Worker Service (`http://localhost:8000`)

#### POST /api/visualization/bar-chart
```json
{
  "data": {
    "group": ["A", "B", "C"],
    "value": [10, 15, 12]
  },
  "title": "Test Chart",
  "x_label": "X Axis",
  "y_label": "Y Axis",
  "show_error_bars": false,
  "color_palette": "colorblind_safe",
  "dpi": 300
}
```

#### POST /api/visualization/line-chart
```json
{
  "data": {
    "x": [1, 2, 3, 4, 5],
    "y": [2, 4, 3, 5, 4]
  },
  "title": "Trend Over Time",
  "show_markers": true,
  "show_confidence_bands": false
}
```

#### POST /api/visualization/scatter-plot
```json
{
  "data": {
    "x": [1, 2, 3, 4, 5],
    "y": [2.1, 3.9, 6.2, 7.8, 10.1]
  },
  "title": "Correlation Analysis",
  "show_trendline": true,
  "show_correlation": true
}
```

#### POST /api/visualization/box-plot
```json
{
  "data": {
    "group": ["A", "A", "A", "B", "B", "B"],
    "value": [5, 6, 7, 8, 9, 10]
  },
  "title": "Distribution Comparison",
  "show_outliers": true,
  "show_means": true
}
```

#### GET /api/visualization/capabilities
Returns available chart types, journal styles, and color palettes.

#### GET /api/visualization/health
Health check with dependency versions.

### Response Format

All POST endpoints return:
```json
{
  "success": true,
  "figure_id": "uuid-here",
  "image_base64": "base64-encoded-image-data",
  "caption": "Auto-generated caption",
  "alt_text": "Accessibility description",
  "metadata": {
    "viz_type": "bar_chart",
    "dimensions": {"width": 800, "height": 600},
    "dpi": 300
  },
  "duration_ms": 245
}
```

## 🎨 Chart Configuration Options

### Journal Styles
- `nature` - Nature journal format
- `jama` - JAMA Medical format
- `nejm` - New England Journal of Medicine
- `lancet` - The Lancet
- `bmj` - British Medical Journal
- `plos` - PLOS ONE
- `apa` - APA style

### Color Palettes
- `colorblind_safe` - Colorblind-friendly colors (default)
- `grayscale` - Grayscale only
- `viridis` - Viridis color map
- `pastel` - Soft pastel colors
- `bold` - Bold, high-contrast colors

## 🧪 Testing

### Unit Tests (Example)
```typescript
// tests/api/visualization.test.ts
import { describe, it, expect } from 'vitest';
import request from 'supertest';
import app from '../src/app';

describe('Visualization API', () => {
  it('generates bar chart', async () => {
    const response = await request(app)
      .post('/api/visualization/bar-chart')
      .send({
        data: { group: ['A', 'B'], value: [10, 15] },
        title: 'Test',
      });
    
    expect(response.status).toBe(200);
    expect(response.body.success).toBe(true);
    expect(response.body.image_base64).toBeDefined();
  });
});
```

### E2E Tests (Example)
```typescript
// e2e/visualization.spec.ts
import { test, expect } from '@playwright/test';

test('user generates chart', async ({ page }) => {
  await page.goto('/analysis/visualization');
  await page.selectOption('[name="chartType"]', 'bar_chart');
  await page.click('button:has-text("Generate")');
  await expect(page.locator('img[alt*="chart"]')).toBeVisible();
});
```

## 📊 Usage Examples

### From Statistical Analysis
```typescript
// In your analysis workflow
const analysisResults = await runStatisticalAnalysis(data);

// Generate visualization
const chart = await fetch('/api/visualization/bar-chart', {
  method: 'POST',
  body: JSON.stringify({
    data: {
      group: analysisResults.groups,
      value: analysisResults.means,
      std: analysisResults.std_errors,
    },
    title: 'Treatment Comparison',
    show_error_bars: true,
    journal_style: 'jama',
  }),
});
```

### Batch Generation
```typescript
const chartTypes = ['bar_chart', 'box_plot', 'scatter_plot'];
const figures = await Promise.all(
  chartTypes.map(type =>
    fetch(`/api/visualization/${type.replace('_', '-')}`, {
      method: 'POST',
      body: JSON.stringify({ data, config }),
    })
  )
);
```

## 🔍 Troubleshooting

### Issue: "DataVisualizationAgent not available"
**Solution**: Check that Python dependencies are installed:
```bash
pip install matplotlib seaborn lifelines pillow pandas numpy
```

### Issue: "Module not found: agents/analysis"
**Solution**: Verify Python path in worker service:
```python
import sys
from pathlib import Path
agents_dir = Path(__file__).parent.parent / "agents"
sys.path.insert(0, str(agents_dir))
```

### Issue: Font warnings on first run
**Solution**: This is normal. Matplotlib builds font cache on first import (~5-10 seconds).

## 📝 Future Enhancements

- [ ] Caching layer (Redis) for frequently generated charts
- [ ] Real-time preview as user adjusts parameters
- [ ] Chart templates library
- [ ] Export to multiple formats (PDF, SVG, EPS)
- [ ] Batch processing for manuscript figures
- [ ] Integration with manuscript editor
- [ ] Figure numbering and cross-referencing
- [ ] Style consistency checker across figures

## 🎯 Success Metrics

- ✅ 7 chart types implemented
- ✅ <1 second average render time
- ✅ Colorblind-safe by default
- ✅ Publication-quality output (300 DPI)
- ✅ Auto-generated captions and alt text
- ✅ PHI-safe (no raw data exposure)

## 📖 References

- **Implementation**: `services/worker/agents/analysis/data_visualization_agent.py`
- **API Routes**: `services/worker/src/api/routes/visualization.py`
- **Types**: `services/worker/agents/analysis/visualization_types.py`
- **Tests**: `services/worker/test_mercury_rendering.py`
- **Docs**: `services/worker/agents/analysis/MERCURY_IMPLEMENTATION_COMPLETE.md`
