# [ROS-100] LoRA Fine-Tuning Scripts - Phase 4.2

## Task Overview
Create scripts for LoRA (Low-Rank Adaptation) fine-tuning of language models for medical manuscript refinement.

## Location
Create files in: `scripts/training/`

## Required Files

### 1. `scripts/training/lora_config.py`
```python
# LoRA configuration for medical manuscript fine-tuning
# - Rank: 16 (balance between quality and memory)
# - Alpha: 32
# - Target modules: q_proj, v_proj, k_proj, o_proj
# - Dropout: 0.05
# - Base model: meta-llama/Llama-3.1-8B
```

### 2. `scripts/training/prepare_dataset.py`
- Load medical manuscript examples
- Format for instruction fine-tuning
- Split into train/validation sets (90/10)
- Save in JSONL format with fields: instruction, input, output

### 3. `scripts/training/train_lora.py`
- Load base model with 4-bit quantization (bitsandbytes)
- Apply LoRA adapters
- Training arguments:
  - batch_size: 4
  - gradient_accumulation_steps: 4
  - learning_rate: 2e-4
  - epochs: 3
  - warmup_ratio: 0.03
- Save adapter weights to `models/lora_adapters/`

### 4. `scripts/training/merge_adapter.py`
- Merge LoRA weights with base model
- Save merged model for deployment
- Export to GGUF format for Ollama

### 5. `scripts/training/requirements.txt`
```
transformers>=4.36.0
peft>=0.7.0
bitsandbytes>=0.41.0
accelerate>=0.25.0
datasets>=2.15.0
torch>=2.1.0
```

## Expected Output
- Working training pipeline for LoRA fine-tuning
- Configuration files for different model sizes
- Dataset preparation utilities
- Model merging and export scripts

## GitHub Repository
https://github.com/ry86pkqf74-rgb/researchflow-production
