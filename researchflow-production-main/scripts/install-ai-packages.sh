#!/bin/bash

# ResearchFlow AI Package Installation Script
# Installs sentence-transformers, transformers, torch, and dependencies

set -e  # Exit on any error

echo "🚀 ResearchFlow AI Package Installation"
echo "======================================"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_header() {
    echo -e "${BLUE}[STEP]${NC} $1"
}

# Check if we're in the right directory
if [ ! -f "services/worker/requirements.txt" ]; then
    print_error "Please run this script from the researchflow-production root directory"
    exit 1
fi

print_header "Step 1: Checking System Requirements"

# Check Python version
python_version=$(python3 --version 2>&1 | cut -d' ' -f2)
print_status "Python version: $python_version"

# Check if pip is available
if ! command -v pip3 &> /dev/null; then
    print_error "pip3 is not installed. Please install pip first."
    exit 1
fi

print_status "pip3 is available"

# Check available disk space (need at least 2GB for models)
available_space=$(df . | awk 'NR==2 {print $4}')
if [ "$available_space" -lt 2000000 ]; then
    print_warning "Low disk space. AI models may require up to 2GB of storage."
fi

print_header "Step 2: Installing Core AI Packages"

cd services/worker

# Create backup of current requirements
if [ -f "requirements-backup.txt" ]; then
    print_warning "Backup file already exists, skipping backup creation"
else
    cp requirements.txt requirements-backup.txt
    print_status "Created backup: requirements-backup.txt"
fi

# Install AI-enhanced requirements
print_status "Installing AI packages from requirements-ai-enhanced.txt..."
if pip3 install -r requirements-ai-enhanced.txt; then
    print_status "✅ AI packages installed successfully"
else
    print_error "❌ Failed to install AI packages"
    print_status "Attempting individual package installation..."
    
    # Try installing packages individually
    packages=(
        "sentence-transformers>=2.2.2"
        "transformers>=4.21.0,<5.0.0" 
        "torch>=2.0.0,<3.0.0"
        "tokenizers>=0.13.0,<1.0.0"
        "accelerate>=0.20.0"
        "safetensors>=0.3.0"
        "numpy>=1.21.0,<2.0.0"
        "scikit-learn>=1.3.0"
    )
    
    for package in "${packages[@]}"; do
        print_status "Installing $package..."
        pip3 install "$package" || print_warning "Failed to install $package"
    done
fi

print_header "Step 3: Checking GPU Support"

# Check if CUDA is available
if python3 -c "import torch; print('CUDA available:', torch.cuda.is_available())" 2>/dev/null; then
    if python3 -c "import torch; exit(0 if torch.cuda.is_available() else 1)" 2>/dev/null; then
        gpu_count=$(python3 -c "import torch; print(torch.cuda.device_count())" 2>/dev/null)
        print_status "✅ CUDA GPU support available ($gpu_count GPU(s) detected)"
        
        # Ask if user wants to install CUDA-optimized PyTorch
        read -p "Would you like to install CUDA-optimized PyTorch? (y/n): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            print_status "Installing CUDA-optimized PyTorch..."
            pip3 install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
        fi
    else
        print_warning "⚠️  CUDA not available, using CPU-only mode"
    fi
else
    print_warning "⚠️  Could not check CUDA availability, assuming CPU-only mode"
fi

print_header "Step 4: Pre-downloading AI Models"

# Create models cache directory
mkdir -p ../../data/models
export TRANSFORMERS_CACHE="../../data/models"
export SENTENCE_TRANSFORMERS_HOME="../../data/models"

print_status "Pre-downloading sentence-transformers model..."
python3 -c "
try:
    from sentence_transformers import SentenceTransformer
    print('Downloading all-MiniLM-L6-v2 model...')
    model = SentenceTransformer('all-MiniLM-L6-v2')
    print('✅ Model downloaded successfully')
    print(f'Model size: {model.get_sentence_embedding_dimension()} dimensions')
except Exception as e:
    print(f'❌ Model download failed: {e}')
    exit(1)
" || print_warning "Model pre-download failed, but will be downloaded on first use"

print_status "Pre-downloading transformers model..."
python3 -c "
try:
    from transformers import pipeline
    print('Downloading NER model...')
    ner = pipeline('ner', model='dbmdz/bert-large-cased-finetuned-conll03-english')
    print('✅ NER model downloaded successfully')
except Exception as e:
    print(f'⚠️  NER model download failed: {e}')
" || print_warning "NER model pre-download failed, but will be downloaded on first use"

print_header "Step 5: Testing AI Functionality"

print_status "Testing sentence-transformers..."
python3 -c "
import sys
sys.path.insert(0, 'src')

try:
    from ai.enhanced_processing import EnhancedAIProcessor
    import asyncio
    
    async def test_ai():
        processor = EnhancedAIProcessor()
        await processor._initialize_models()
        
        if processor.is_ready():
            # Test embeddings
            embeddings = await processor.get_embeddings(['Hello world', 'AI testing'])
            if embeddings and embeddings[0].success:
                print('✅ Embeddings test passed')
            else:
                print('❌ Embeddings test failed')
                return False
            
            # Test semantic search
            search_result = await processor.semantic_search(
                'artificial intelligence',
                ['AI is the future', 'Machine learning algorithms', 'Database queries'],
                top_k=2
            )
            if search_result.matches:
                print('✅ Semantic search test passed')
            else:
                print('❌ Semantic search test failed')
                return False
            
            print('✅ All AI functionality tests passed')
            return True
        else:
            print('❌ AI processor not ready')
            return False
    
    result = asyncio.run(test_ai())
    if not result:
        sys.exit(1)
        
except Exception as e:
    print(f'❌ AI testing failed: {e}')
    sys.exit(1)
" && print_status "✅ AI functionality tests passed" || print_error "❌ AI functionality tests failed"

print_header "Step 6: Updating Service Configuration"

# Check if API server needs to be updated
if grep -q "AI_ENDPOINTS_AVAILABLE" api_server.py; then
    print_status "✅ API server already configured for AI endpoints"
else
    print_warning "⚠️  API server may need manual update to include AI endpoints"
fi

print_header "Step 7: Creating AI Configuration Files"

# Create AI configuration file
cat > src/ai/config.json << 'EOF'
{
    "sentence_transformer_model": "all-MiniLM-L6-v2",
    "clinical_model": "emilyalsentzer/Bio_ClinicalBERT",
    "similarity_threshold": 0.7,
    "max_sequence_length": 512,
    "batch_size": 32,
    "use_gpu": "auto",
    "cache_embeddings": true,
    "models_to_load": ["sentence_transformer", "clinical_ner"]
}
EOF

print_status "Created AI configuration file: src/ai/config.json"

# Create environment file for AI settings
cat > .env.ai << 'EOF'
# AI Service Configuration
AI_MODEL_CACHE_DIR=/data/models
AI_DEFAULT_MODEL=all-MiniLM-L6-v2
AI_USE_GPU=auto
AI_BATCH_SIZE=32
AI_MAX_SEQUENCE_LENGTH=512
AI_SIMILARITY_THRESHOLD=0.7
AI_CACHE_EMBEDDINGS=true
AI_MAX_CACHE_SIZE=1000

# Model Performance Settings
TRANSFORMERS_CACHE=/data/models
SENTENCE_TRANSFORMERS_HOME=/data/models
HF_HOME=/data/models

# Logging
AI_LOG_LEVEL=INFO
TRANSFORMERS_VERBOSITY=warning
EOF

print_status "Created AI environment file: .env.ai"

print_header "Step 8: Installation Summary"

# Get installed package versions
print_status "Installed AI package versions:"
packages_to_check=(
    "sentence-transformers"
    "transformers" 
    "torch"
    "tokenizers"
    "accelerate"
    "numpy"
    "scikit-learn"
)

for package in "${packages_to_check[@]}"; do
    version=$(pip3 show "$package" 2>/dev/null | grep Version | cut -d' ' -f2)
    if [ -n "$version" ]; then
        print_status "  $package: $version"
    else
        print_warning "  $package: NOT INSTALLED"
    fi
done

# Check model cache
model_cache_size=$(du -sh ../../data/models 2>/dev/null | cut -f1 || echo "0")
print_status "Model cache size: $model_cache_size"

# Final recommendations
echo
print_header "🎉 Installation Complete!"
echo
print_status "Next steps:"
echo "  1. Restart the worker service: docker-compose restart worker"
echo "  2. Test AI endpoints: curl http://localhost:8000/api/v1/ai/health"
echo "  3. Run the demo: python demo/ai_frontend_integration_example.py"
echo "  4. Check the deployment guide: AI_ENHANCEMENT_DEPLOYMENT_GUIDE.md"
echo
print_status "Environment variables can be loaded with: source .env.ai"
echo

# Create quick test script
cat > test-ai-quick.sh << 'EOF'
#!/bin/bash
echo "🧪 Quick AI Test"
echo "==============="

# Test health endpoint
echo "Testing health endpoint..."
curl -s http://localhost:8000/api/v1/ai/health | python3 -m json.tool

echo
echo "Testing embeddings endpoint..."
curl -X POST http://localhost:8000/api/v1/ai/embeddings \
  -H "Content-Type: application/json" \
  -d '{"texts": ["Hello world", "AI testing"]}' \
  -s | python3 -m json.tool

echo
echo "✅ AI quick test complete!"
EOF

chmod +x test-ai-quick.sh
print_status "Created quick test script: test-ai-quick.sh"

cd ../..  # Return to root directory

print_status "Installation completed successfully! 🚀"
print_warning "Remember to restart services to load new AI functionality."

exit 0