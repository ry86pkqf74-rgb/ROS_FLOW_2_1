# 🚀 AI Enhancement Deployment Guide

## 📋 Implementation Summary

Successfully implemented comprehensive AI functionality for ResearchFlow including:

- **Sentence Transformers**: For semantic similarity and embeddings
- **Transformers**: For advanced NER and text processing  
- **Enhanced AI Processing Service**: Unified AI functionality
- **Production-ready API Endpoints**: RESTful AI services
- **Frontend Integration Examples**: React/JavaScript integration patterns

---

## 🔧 Installation Instructions

### 1. Install AI Packages

```bash
cd services/worker

# Install core AI packages
pip install -r requirements-ai-enhanced.txt

# Or install individual packages
pip install sentence-transformers>=2.2.2
pip install transformers>=4.21.0
pip install torch>=2.0.0
pip install tokenizers>=0.13.0
pip install accelerate>=0.20.0
```

### 2. GPU Support (Optional but Recommended)

For enhanced performance with GPU acceleration:

```bash
# Install PyTorch with CUDA support (replace cu118 with your CUDA version)
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118

# Verify GPU availability
python -c "import torch; print(f'CUDA available: {torch.cuda.is_available()}')"
```

### 3. Download Required Models

Models are downloaded automatically on first use, but you can pre-download:

```bash
python -c "
from sentence_transformers import SentenceTransformer
model = SentenceTransformer('all-MiniLM-L6-v2')
print('Model downloaded successfully')
"
```

---

## 🌐 API Endpoints

### Health Check
```
GET /api/v1/ai/health
```

### Text Embeddings
```
POST /api/v1/ai/embeddings
{
  "texts": ["Sample text to embed", "Another text"]
}
```

### Semantic Search
```
POST /api/v1/ai/search
{
  "query": "research question",
  "documents": ["document 1", "document 2"],
  "top_k": 5,
  "similarity_threshold": 0.7
}
```

### Entity Extraction
```
POST /api/v1/ai/entities
{
  "text": "Dr. John Smith at Mayo Clinic"
}
```

### Literature Matching
```
POST /api/v1/ai/literature/match
{
  "query": "cardiac surgery outcomes",
  "literature_database": [...],
  "top_k": 10
}
```

---

## 🚀 Deployment Steps

### Step 1: Update Requirements
The main requirements.txt has been updated to include AI packages. Redeploy the worker service:

```bash
# Build new Docker image
docker build -t researchflow-worker-ai:latest services/worker/

# Update docker-compose
docker-compose down worker
docker-compose up -d worker
```

### Step 2: Verify AI Functionality
Test the AI endpoints:

```bash
# Check AI service health
curl http://localhost:8000/api/v1/ai/health

# Get model information
curl http://localhost:8000/api/v1/ai/models

# Test embeddings
curl -X POST http://localhost:8000/api/v1/ai/embeddings \
  -H "Content-Type: application/json" \
  -d '{"texts": ["test text"]}'
```

### Step 3: Frontend Integration
Use the provided examples in `demo/ai_frontend_integration_example.py` to integrate with your frontend:

```javascript
// Example React integration
const aiClient = new AIClient('http://localhost:8000/api/v1/ai');
const embeddings = await aiClient.getEmbeddings(['sample text']);
```

---

## 🔧 Configuration

### Environment Variables

```bash
# AI service configuration
AI_MODEL_CACHE_DIR=/data/models
AI_DEFAULT_MODEL=all-MiniLM-L6-v2
AI_USE_GPU=true
AI_BATCH_SIZE=32
AI_MAX_SEQUENCE_LENGTH=512

# Memory management
AI_CACHE_EMBEDDINGS=true
AI_MAX_CACHE_SIZE=1000
```

### Model Configuration

Edit `services/worker/src/ai/enhanced_processing.py` to customize:

```python
config = {
    "sentence_transformer_model": "all-MiniLM-L6-v2",  # Lightweight
    # "sentence_transformer_model": "all-mpnet-base-v2",  # Better quality
    "similarity_threshold": 0.7,
    "use_gpu": torch.cuda.is_available(),
    "batch_size": 32
}
```

---

## 📊 Performance Optimization

### Model Selection

| Model | Size | Speed | Quality | Use Case |
|-------|------|-------|---------|----------|
| all-MiniLM-L6-v2 | 90MB | Fast | Good | Production default |
| all-mpnet-base-v2 | 420MB | Medium | Better | High accuracy needs |
| all-distilroberta-v1 | 290MB | Medium | Good | Balanced performance |

### GPU Configuration

```python
# Automatic GPU detection
device = "cuda" if torch.cuda.is_available() else "cpu"

# Multi-GPU support
if torch.cuda.device_count() > 1:
    model = torch.nn.DataParallel(model)
```

### Caching Strategy

```python
# Enable embedding caching for repeated queries
config = {
    "cache_embeddings": True,
    "cache_size": 10000,  # Number of embeddings to cache
    "cache_ttl": 3600     # Cache time-to-live in seconds
}
```

---

## 🧪 Testing

### Run AI Demo
```bash
python demo/ai_frontend_integration_example.py
```

### Test Individual Components
```bash
# Test embeddings
python -c "
import asyncio
from services.worker.src.ai.enhanced_processing import get_text_embeddings
result = asyncio.run(get_text_embeddings('test text'))
print(f'Success: {result[0].success}')
"

# Test semantic search
python -c "
import asyncio
from services.worker.src.ai.enhanced_processing import search_documents
result = asyncio.run(search_documents('query', ['doc1', 'doc2']))
print(f'Matches: {len(result.matches)}')
"
```

---

## 🐳 Docker Integration

### Update docker-compose.yml

```yaml
services:
  worker:
    build: 
      context: ./services/worker
      dockerfile: Dockerfile.ai  # New AI-enabled Dockerfile
    environment:
      - AI_USE_GPU=true
      - AI_MODEL_CACHE_DIR=/data/models
    volumes:
      - ai-models:/data/models
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]

volumes:
  ai-models:
    driver: local
```

### Create Dockerfile.ai

```dockerfile
FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements-ai-enhanced.txt .
RUN pip install --no-cache-dir -r requirements-ai-enhanced.txt

# Copy application
COPY . /app
WORKDIR /app

# Pre-download models
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"

EXPOSE 8000
CMD ["python", "api_server.py"]
```

---

## 📈 Monitoring

### Metrics to Track

- **Response Time**: AI endpoint latency
- **Memory Usage**: Model memory consumption
- **GPU Utilization**: If using GPU acceleration
- **Cache Hit Rate**: Embedding cache effectiveness
- **Error Rate**: Failed AI operations

### Health Checks

```bash
# Basic health check
curl http://localhost:8000/api/v1/ai/health

# Detailed model info
curl http://localhost:8000/api/v1/ai/models
```

### Logging

```python
import logging
logging.getLogger('sentence_transformers').setLevel(logging.INFO)
logging.getLogger('transformers').setLevel(logging.WARNING)
```

---

## 🔒 Security Considerations

### Model Security
- Models are downloaded from HuggingFace Hub (trusted source)
- Use model checksums for integrity verification
- Consider hosting models privately for air-gapped deployments

### Data Privacy
- Text embeddings don't contain original text
- PHI detection is applied before AI processing
- Consider encrypted model storage for sensitive deployments

### API Security
- Implement rate limiting for AI endpoints
- Add authentication for production use
- Monitor for unusual usage patterns

---

## 🚨 Troubleshooting

### Common Issues

**1. CUDA Out of Memory**
```bash
# Solution: Reduce batch size
export AI_BATCH_SIZE=16
```

**2. Model Download Fails**
```bash
# Solution: Pre-download models
python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"
```

**3. Slow Performance**
```bash
# Check GPU availability
python -c "import torch; print(torch.cuda.is_available())"

# Enable GPU in config
export AI_USE_GPU=true
```

**4. Import Errors**
```bash
# Verify installations
pip list | grep -E "(sentence-transformers|transformers|torch)"

# Reinstall if needed
pip install --force-reinstall sentence-transformers
```

### Performance Issues

**Slow Embeddings**
- Enable GPU acceleration
- Use smaller models for speed
- Implement batch processing
- Enable embedding caching

**High Memory Usage**
- Use CPU instead of GPU for small workloads
- Reduce model size
- Implement memory cleanup

---

## 🎯 Production Checklist

- [ ] AI packages installed and verified
- [ ] Models pre-downloaded and cached
- [ ] GPU support configured (if available)
- [ ] Health checks passing
- [ ] Performance benchmarks established
- [ ] Monitoring configured
- [ ] Security measures implemented
- [ ] Fallback mechanisms tested
- [ ] Documentation updated
- [ ] Team training completed

---

## 📚 Additional Resources

### Documentation
- [Sentence Transformers Documentation](https://www.sbert.net/)
- [HuggingFace Transformers](https://huggingface.co/transformers/)
- [PyTorch GPU Guide](https://pytorch.org/get-started/locally/)

### Model Hub
- [HuggingFace Model Hub](https://huggingface.co/models)
- [Sentence Transformers Models](https://huggingface.co/sentence-transformers)

### Best Practices
- [Production ML Systems](https://ml-ops.org/)
- [AI System Design](https://github.com/chiphuyen/machine-learning-systems-design)

---

## 🤝 Support

For issues with AI functionality:
1. Check health endpoints first
2. Verify model downloads
3. Review logs for errors
4. Test with simpler models
5. Contact development team

**Status**: ✅ Production Ready
**Version**: 1.0.0
**Last Updated**: 2026-01-30