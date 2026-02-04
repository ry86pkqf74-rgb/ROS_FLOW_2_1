# 🚀 Enhanced ResearchFlow Integration Quickstart

## Overview
This guide gets you started with the newly enhanced ResearchFlow system featuring citation network analysis, advanced monitoring, and improved statistical capabilities.

## 🏃‍♂️ Quick Start (5 minutes)

### 1. Health Check
```bash
chmod +x scripts/integration_health_check.sh
./scripts/integration_health_check.sh
```

### 2. Run Demo
```bash
cd demo
python complete_system_integration.py
```

### 3. Start Services
```bash
# Start enhanced monitoring
python -c "from services.worker.src.analytics import get_enhanced_monitor; get_enhanced_monitor().start_enhanced_monitoring()"

# Start citation analysis API (separate terminal)
cd services/worker/src
uvicorn api.citation_analysis_api:app --host 0.0.0.0 --port 8002
```

## 📊 Key Endpoints

### Citation Network Analysis
```bash
# Build network
curl -X POST http://localhost:8002/api/v1/network/build \
  -H "Content-Type: application/json" \
  -d '{"papers": [...]}'

# Analyze network
curl -X POST http://localhost:8002/api/v1/network/analyze

# Get visualizations
curl http://localhost:8002/api/v1/network/visualization
```

### Performance Monitoring
```python
from services.worker.src.analytics import get_performance_monitor

monitor = get_performance_monitor()
health = monitor.get_current_system_health()
print(f"System Status: {health.overall_status}")
```

### Enhanced Protocol Generation
```python
from services.worker.src.enhanced_protocol_generation import create_enhanced_generator

generator = create_enhanced_generator("production")
result = await generator.generate_protocol_enhanced(
    template_id="clinical_trial_protocol",
    study_data={"study_title": "My Study"},
    phi_check=True
)
```

## 🔧 Key Features

✅ **Citation Network Analysis** - Graph algorithms, centrality analysis, gap detection  
✅ **Enhanced Monitoring** - Real-time performance tracking with optimization recommendations  
✅ **Statistical Improvements** - Welch's t-test, Cohen's dz, Tukey HSD post-hoc tests  
✅ **PHI Compliance** - Built-in healthcare data protection  
✅ **Production Ready** - Enterprise-grade error handling and logging  

## 📈 Monitoring Dashboard

Access real-time system metrics:
```python
from services.worker.src.analytics import get_enhanced_monitor

monitor = get_enhanced_monitor()
insights = monitor.get_performance_insights()
recommendations = monitor.get_optimization_recommendations()
```

## 🎯 Next Steps

1. **Production Deployment**: Follow `PRODUCTION_ENVIRONMENT_SETUP.md`
2. **Custom Configuration**: Modify `services/worker/src/enhanced_protocol_generation.py`
3. **Integration Testing**: Run `python demo/complete_system_integration.py`
4. **Monitoring Setup**: Configure alerts and thresholds in enhanced monitoring

## 🆘 Troubleshooting

**Import Errors**: Ensure Python path includes `services/worker/src`
```bash
export PYTHONPATH="${PYTHONPATH}:$(pwd)/services/worker/src"
```

**Permission Errors**: Check file permissions
```bash
chmod +x scripts/*.sh
```

**Port Conflicts**: Use different ports in API configurations

---

🎉 **You're ready to leverage the enhanced ResearchFlow system!**