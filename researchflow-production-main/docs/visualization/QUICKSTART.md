# Data Visualization System - Quick Start Guide

Get up and running with ResearchFlow's data visualization system in minutes.

## 🚀 Quick Setup (5 minutes)

### 1. Prerequisites
```bash
# Check requirements
node --version    # >= 18
python --version  # >= 3.9
docker --version  # >= 24
```

### 2. Environment Setup
```bash
# Clone and navigate
git clone https://github.com/ry86pkqf74-rgb/researchflow-production.git
cd researchflow-production

# Set up environment
cp .env.example .env
# Edit .env and add your API keys:
# ANTHROPIC_API_KEY=your_key_here
# OPENAI_API_KEY=your_key_here (optional)
```

### 3. Start Services
```bash
# Option A: Docker (Recommended)
docker compose up -d

# Option B: Manual (Development)
# Terminal 1 - Database
docker compose up postgres redis -d

# Terminal 2 - Worker
cd services/worker
pip install -r requirements.txt
python -m uvicorn src.main:app --reload --port 8000

# Terminal 3 - Orchestrator  
cd services/orchestrator
npm install
npm run dev

# Terminal 4 - Frontend
cd services/web
npm install
npm run dev
```

### 4. Verify Setup
```bash
# Check service health
curl http://localhost:8000/api/visualization/health  # Worker
curl http://localhost:3001/api/visualization/health  # Orchestrator
open http://localhost:5173                           # Frontend
```

## 📊 Generate Your First Chart (2 minutes)

### Via Frontend
1. Navigate to http://localhost:5173
2. Create or select a research project
3. Go to **Visualization** tab
4. Select **Bar Chart**
5. Input sample data:
   ```json
   {
     "group": ["Control", "Treatment A", "Treatment B"],
     "value": [5.2, 6.8, 7.3],
     "error": [0.8, 1.1, 0.9]
   }
   ```
6. Set title: "Treatment Effectiveness"
7. Click **Generate Chart**
8. View and save your chart!

### Via API (cURL)
```bash
# Generate bar chart
curl -X POST http://localhost:8000/api/visualization/bar-chart \
  -H "Content-Type: application/json" \
  -d '{
    "data": {
      "group": ["Control", "Treatment A", "Treatment B"],
      "value": [5.2, 6.8, 7.3]
    },
    "title": "Treatment Effectiveness",
    "x_label": "Treatment Group",
    "y_label": "Pain Score (0-10)",
    "journal_style": "nature",
    "color_palette": "colorblind_safe",
    "dpi": 300
  }'
```

### Via Python
```python
import requests
import base64

# Generate chart
response = requests.post('http://localhost:8000/api/visualization/bar-chart', json={
    "data": {
        "group": ["Control", "Treatment A", "Treatment B"],
        "value": [5.2, 6.8, 7.3]
    },
    "title": "Treatment Effectiveness",
    "journal_style": "jama",
    "color_palette": "colorblind_safe"
})

# Save image
if response.ok:
    result = response.json()
    image_data = base64.b64decode(result['image_base64'])
    with open('my_chart.png', 'wb') as f:
        f.write(image_data)
    print(f"Chart saved! ID: {result['figure_id']}")
```

### Via JavaScript/React
```typescript
import { useVisualization } from '@/hooks/useVisualization';

function MyChart() {
  const { generateChart, loading, error } = useVisualization();
  
  const createChart = async () => {
    const result = await generateChart({
      chart_type: 'line_chart',
      data: {
        time: [0, 1, 2, 3, 4, 5],
        value: [10, 12, 11, 14, 13, 15]
      },
      config: {
        title: 'Recovery Timeline',
        x_label: 'Time (weeks)',
        y_label: 'Recovery Score',
        journal_style: 'nejm'
      }
    });
    
    console.log('Generated:', result.figure_id);
  };
  
  return (
    <button onClick={createChart} disabled={loading}>
      Generate Line Chart
    </button>
  );
}
```

## 🎨 Chart Types Available

### Basic Charts
```bash
# Bar Chart
POST /api/visualization/bar-chart
# - Groups, values, error bars
# - Horizontal/vertical orientation
# - Multiple series support

# Line Chart  
POST /api/visualization/line-chart
# - Time series, multiple lines
# - Confidence bands, markers
# - Smooth/stepped lines

# Scatter Plot
POST /api/visualization/scatter-plot
# - Correlation analysis
# - Trend lines, bubble sizes
# - Color-coded categories

# Box Plot
POST /api/visualization/box-plot
# - Distribution comparison
# - Outliers, means, medians
# - Grouped/stacked layouts
```

### Advanced Charts
```bash
# Forest Plot (Meta-analysis)
POST /api/visualization/forest-plot
# - Effect sizes, confidence intervals
# - Study weights, summary diamond
# - Fixed/random effects models

# Kaplan-Meier (Survival)
POST /api/visualization/kaplan-meier
# - Survival curves, risk tables
# - Censoring indicators
# - Log-rank test results

# CONSORT Flowchart
POST /api/visualization/flowchart
# - Study participant flow
# - Exclusion reasons
# - Randomization branches
```

## 🎯 Common Use Cases

### 1. Clinical Trial Results
```json
{
  "chart_type": "bar_chart",
  "data": {
    "group": ["Placebo", "Low Dose", "High Dose"],
    "primary_outcome": [45.2, 52.8, 61.3],
    "error_bars": [3.1, 2.9, 3.4]
  },
  "config": {
    "title": "Primary Outcome by Treatment Group",
    "y_label": "Efficacy Score (%)",
    "show_error_bars": true,
    "journal_style": "nejm",
    "color_palette": "colorblind_safe"
  }
}
```

### 2. Longitudinal Data
```json
{
  "chart_type": "line_chart",
  "data": {
    "time": [0, 4, 8, 12, 24, 48],
    "treatment": [0, 15, 35, 52, 68, 75],
    "control": [0, 8, 18, 25, 32, 38],
    "treatment_ci_lower": [0, 12, 30, 46, 61, 68],
    "treatment_ci_upper": [0, 18, 40, 58, 75, 82]
  },
  "config": {
    "title": "Recovery Over Time",
    "x_label": "Time (weeks)",
    "y_label": "Recovery Score",
    "show_confidence_bands": true,
    "journal_style": "jama"
  }
}
```

### 3. Meta-Analysis
```json
{
  "chart_type": "forest_plot",
  "data": {
    "study": ["Smith 2020", "Jones 2021", "Brown 2022"],
    "effect": [1.25, 1.18, 1.31],
    "ci_lower": [1.05, 0.98, 1.12],
    "ci_upper": [1.48, 1.42, 1.53],
    "weight": [0.35, 0.40, 0.25]
  },
  "config": {
    "title": "Meta-Analysis: Treatment vs Control",
    "effect_measure": "Risk Ratio",
    "show_summary": true,
    "journal_style": "bmj"
  }
}
```

## 🎨 Styling Options

### Journal Styles
```typescript
type JournalStyle = 
  | 'nature'    // High-impact, clean
  | 'jama'      // Medical, conservative
  | 'nejm'      // New England Journal
  | 'lancet'    // The Lancet style
  | 'bmj'       // British Medical Journal
  | 'plos'      // PLOS ONE format
  | 'apa';      // Psychology journals
```

### Color Palettes
```typescript
type ColorPalette = 
  | 'colorblind_safe'  // Accessible colors
  | 'grayscale'        // Black & white
  | 'viridis'          // Scientific standard
  | 'pastel'           // Soft colors
  | 'bold';            // High contrast
```

### Quality Options
```typescript
interface ChartConfig {
  dpi?: number;         // 72-600 (300 recommended)
  width?: number;       // Pixels
  height?: number;      // Pixels
  format?: 'png' | 'svg' | 'pdf';
  quality?: 'draft' | 'presentation' | 'publication';
}
```

## 🔍 Testing Your Implementation

### 1. Quick Health Check
```bash
# Test all services
npm test tests/integration/visualization.test.ts

# Or manually:
curl http://localhost:8000/api/visualization/health
curl http://localhost:3001/api/visualization/health
```

### 2. Generate Test Charts
```bash
# Run the test script
cd services/worker
python test_visualization_api.py
```

### 3. Frontend Testing
```bash
cd services/web
npm run test:e2e -- visualization-workflow.test.ts
```

## 🔧 Troubleshooting

### Common Issues

#### Worker Service Won't Start
```bash
# Check Python dependencies
cd services/worker
pip install -r requirements.txt

# Check if port is in use
lsof -i :8000

# Check logs
docker compose logs worker
```

#### Charts Not Generating
```bash
# Check worker health
curl http://localhost:8000/api/visualization/health

# Check dependencies
python -c "import matplotlib, seaborn, pandas; print('OK')"

# Check API key (if using AI features)
echo $ANTHROPIC_API_KEY
```

#### Database Connection Issues
```bash
# Check database is running
docker compose ps postgres

# Test connection
psql $DATABASE_URL -c "SELECT 1;"

# Check migrations
cd services/orchestrator
npm run migrate
```

#### Frontend Issues
```bash
# Clear cache and restart
cd services/web
rm -rf node_modules/.cache
npm run dev

# Check browser console for errors
# Check network tab for API calls
```

### Performance Issues

#### Slow Chart Generation
```bash
# Check DPI setting (lower = faster)
# Reduce data points for testing
# Monitor CPU/memory usage
htop
```

#### Database Growing Too Fast
```sql
-- Check figure sizes
SELECT 
  AVG(size_bytes/1024) as avg_kb,
  MAX(size_bytes/1024) as max_kb,
  COUNT(*) as total
FROM figures;

-- Archive old figures
UPDATE figures 
SET deleted_at = NOW() 
WHERE created_at < NOW() - INTERVAL '90 days';
```

## 🚀 Production Deployment

### Docker Production
```bash
# Build production images
docker compose -f docker-compose.prod.yml build

# Deploy
docker compose -f docker-compose.prod.yml up -d

# Check health
curl https://your-domain.com/api/visualization/health
```

### Environment Variables
```bash
# Required
DATABASE_URL=postgresql://user:pass@db:5432/researchflow
REDIS_URL=redis://redis:6379
WORKER_URL=http://worker:8000

# Optional
ANTHROPIC_API_KEY=your_key_here
OPENAI_API_KEY=your_key_here
VIZ_DEFAULT_DPI=300
VIZ_ENABLE_PHI_SCANNING=true
```

## 📚 Next Steps

1. **Explore Examples**: Check `services/worker/example_visualization_usage.py`
2. **Read Documentation**: See `docs/visualization/IMPLEMENTATION_COMPLETE.md`
3. **Customize Styles**: Modify journal templates in agent code
4. **Add Chart Types**: Extend visualization_types.py
5. **Integrate with Workflow**: Connect to your research pipeline

## 🆘 Getting Help

- **Documentation**: `/docs` folder
- **API Reference**: http://localhost:8000/docs (when worker running)
- **Health Checks**: `/api/visualization/health` endpoints
- **Logs**: `docker compose logs` or service-specific logs
- **Tests**: Run test suites for validation

## ✅ Success Checklist

- [ ] All services running (worker, orchestrator, frontend)
- [ ] Database connected and migrated
- [ ] Generated at least one chart successfully
- [ ] Charts saved to database (check figures table)
- [ ] Frontend visualization panel working
- [ ] API health checks passing
- [ ] Tests running successfully

**You're ready to start visualizing research data!** 🎉