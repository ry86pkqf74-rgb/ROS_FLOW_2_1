#!/bin/bash
set -e

# ResearchFlow AI Package Installation Script
# Installs comprehensive AI functionality including sentence-transformers, transformers, and torch

echo "🚀 Installing ResearchFlow AI Enhanced Packages..."
echo "=================================================="

# Check Python version
PYTHON_VERSION=$(python3 --version 2>&1 | cut -d' ' -f2 | cut -d'.' -f1,2)
echo "📍 Python version: $PYTHON_VERSION"

if [[ $(echo "$PYTHON_VERSION < 3.8" | bc -l 2>/dev/null || echo "0") == "1" ]]; then
    echo "❌ Python 3.8+ required. Current version: $PYTHON_VERSION"
    exit 1
fi

# Check if we're in the worker directory
if [[ ! -f "requirements-ai-enhanced.txt" ]]; then
    echo "❌ Please run this script from the services/worker directory"
    echo "   Current directory: $(pwd)"
    exit 1
fi

# Check available disk space (need ~3GB for models)
AVAILABLE_SPACE=$(df -BG . | tail -1 | awk '{print $4}' | sed 's/G//')
if [[ $AVAILABLE_SPACE -lt 5 ]]; then
    echo "⚠️  Warning: Low disk space ($AVAILABLE_SPACE GB available). AI models need ~3GB."
    read -p "Continue anyway? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Create models cache directory
echo "📁 Creating model cache directory..."
mkdir -p /tmp/models /data/models
export TRANSFORMERS_CACHE=/data/models
export SENTENCE_TRANSFORMERS_HOME=/data/models

# Check for CUDA support
echo "🔍 Checking for GPU support..."
if command -v nvidia-smi &> /dev/null; then
    echo "✅ NVIDIA GPU detected"
    GPU_SUPPORT=true
    # Install PyTorch with CUDA support
    echo "📦 Installing PyTorch with CUDA support..."
    pip3 install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
else
    echo "ℹ️  No NVIDIA GPU detected, using CPU-only PyTorch"
    GPU_SUPPORT=false
fi

# Install AI packages
echo "📦 Installing AI enhanced requirements..."
pip3 install -r requirements-ai-enhanced.txt

# Install additional NLP resources
echo "📦 Installing additional NLP resources..."
python3 -m nltk.downloader punkt stopwords wordnet averaged_perceptron_tagger

# Optional: Download spaCy models
echo "📦 Installing spaCy language models..."
pip3 install spacy
python3 -m spacy download en_core_web_sm

# Test installation
echo "🧪 Testing AI package installation..."
python3 -c "
try:
    import sentence_transformers
    import transformers
    import torch
    import sklearn
    import nltk
    
    print('✅ Core AI packages: OK')
    print(f'   - sentence-transformers: {sentence_transformers.__version__}')
    print(f'   - transformers: {transformers.__version__}')
    print(f'   - torch: {torch.__version__}')
    
    # Test CUDA if available
    if torch.cuda.is_available():
        print(f'   - CUDA: Available ({torch.cuda.device_count()} GPUs)')
    else:
        print('   - CUDA: Not available (CPU mode)')
    
    print('✅ Installation successful!')
    
except ImportError as e:
    print(f'❌ Import failed: {e}')
    exit(1)
"

# Pre-download essential models
echo "📥 Pre-downloading essential AI models..."
python3 -c "
from sentence_transformers import SentenceTransformer
import os

# Set cache directory
os.environ['TRANSFORMERS_CACHE'] = '/data/models'
os.environ['SENTENCE_TRANSFORMERS_HOME'] = '/data/models'

print('Downloading all-MiniLM-L6-v2 (lightweight, fast)...')
model1 = SentenceTransformer('all-MiniLM-L6-v2')
print(f'✅ Model downloaded to: {model1.cache_folder}')

print('Downloading all-mpnet-base-v2 (higher quality)...')
model2 = SentenceTransformer('all-mpnet-base-v2') 
print(f'✅ Model downloaded to: {model2.cache_folder}')

print('🎯 Essential models ready!')
"

# Test AI processor
echo "🧪 Testing enhanced AI processor..."
python3 -c "
import sys
sys.path.insert(0, 'src')

try:
    from ai.enhanced_processing import get_ai_processor, get_text_embeddings
    import asyncio
    
    async def test():
        processor = get_ai_processor()
        if processor.is_ready():
            print('✅ Enhanced AI processor: Ready')
            
            # Test embedding generation
            results = await get_text_embeddings(['Clinical trial for heart disease', 'Machine learning research'])
            if all(r.success for r in results):
                print('✅ Embedding generation: Working')
                print(f'   - Generated {len(results)} embeddings')
                print(f'   - Embedding dimension: {results[0].embedding.shape[0]}')
            else:
                print('❌ Embedding generation: Failed')
        else:
            print('❌ Enhanced AI processor: Not ready')
            
    asyncio.run(test())
    
except Exception as e:
    print(f'❌ AI processor test failed: {e}')
"

echo ""
echo "🎉 AI Package Installation Complete!"
echo "===================================="
echo ""
echo "✅ Installed packages:"
echo "   - sentence-transformers (semantic search)"
echo "   - transformers (NLP models)" 
echo "   - torch (deep learning)"
echo "   - scikit-learn (ML utilities)"
echo "   - nltk, spacy (text processing)"
echo ""
echo "✅ Pre-downloaded models:"
echo "   - all-MiniLM-L6-v2 (lightweight)"
echo "   - all-mpnet-base-v2 (high quality)"
echo ""
echo "🚀 Next steps:"
echo "   1. Start the worker API: python3 src/main.py"
echo "   2. Test health check: curl http://localhost:8000/api/v1/ai/health"
echo "   3. Test embeddings: curl -X POST http://localhost:8000/api/v1/ai/embeddings -H 'Content-Type: application/json' -d '{\"texts\": [\"test\"]}'"
echo ""
if [[ $GPU_SUPPORT == true ]]; then
    echo "🎯 GPU acceleration enabled - models will run faster!"
else
    echo "ℹ️  Running in CPU mode - consider GPU setup for better performance"
fi
echo ""
echo "📚 For more examples, check demo/ai_frontend_integration_example.py"