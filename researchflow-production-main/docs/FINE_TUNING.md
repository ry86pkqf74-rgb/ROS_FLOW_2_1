# ResearchFlow: Fine-Tuning & Model Deployment Guide
## Phase 10: Custom Model Training & Ollama Integration

**Last Updated**: 2026-01-30
**Version**: 1.0
**Packages**: @researchflow/phi-engine, @researchflow/core

---

## Table of Contents

1. [Data Preparation Pipeline](#data-preparation-pipeline)
2. [PHI Redaction Requirements](#phi-redaction-requirements)
3. [LoRA Training Setup](#lora-training-setup)
4. [Model Deployment to Ollama](#model-deployment-to-ollama)
5. [Integration Examples](#integration-examples)

---

## Data Preparation Pipeline

### Step 1: Data Collection

Collect research paper data with proper metadata:

```typescript
interface TrainingExample {
  id: string;
  input: string;        // Instruction or prompt
  output: string;       // Expected completion
  metadata: {
    source: 'paper' | 'manifest' | 'guideline';
    domain: string;     // medical, biology, chemistry, etc.
    difficulty: 'easy' | 'medium' | 'hard';
    verified: boolean;
  };
}

const trainingData: TrainingExample[] = [
  {
    id: 'example-1',
    input: 'Extract the methodology section from this paper: [paper text]',
    output: 'The study employed a randomized controlled trial design...',
    metadata: {
      source: 'paper',
      domain: 'medical',
      difficulty: 'medium',
      verified: true
    }
  }
];
```

### Step 2: Data Validation

```typescript
async function validateTrainingData(examples: TrainingExample[]) {
  const errors: string[] = [];
  
  for (const ex of examples) {
    // Check required fields
    if (!ex.input || !ex.output) {
      errors.push(`${ex.id}: Missing input or output`);
    }
    
    // Check length constraints
    if (ex.input.length < 10 || ex.input.length > 50000) {
      errors.push(`${ex.id}: Input length out of bounds`);
    }
    
    // Check for PHI
    const phiFindings = phiScanner.scan(ex.output);
    if (phiFindings.length > 0) {
      errors.push(`${ex.id}: Contains PHI - must redact first`);
    }
  }
  
  return { valid: errors.length === 0, errors };
}
```

### Step 3: Data Splitting

```typescript
function splitTrainingData(
  data: TrainingExample[],
  trainRatio: number = 0.8,
  valRatio: number = 0.1
) {
  // Shuffle data
  const shuffled = [...data].sort(() => Math.random() - 0.5);
  
  const totalSize = shuffled.length;
  const trainSize = Math.floor(totalSize * trainRatio);
  const valSize = Math.floor(totalSize * valRatio);
  
  return {
    train: shuffled.slice(0, trainSize),
    val: shuffled.slice(trainSize, trainSize + valSize),
    test: shuffled.slice(trainSize + valSize)
  };
}
```

### Step 4: Format Conversion for Training

```typescript
// Convert to standard fine-tuning format
async function formatForOpenAI(examples: TrainingExample[]) {
  const jsonl = examples
    .map(ex => ({
      messages: [
        { role: 'system', content: 'You are a research analysis assistant.' },
        { role: 'user', content: ex.input },
        { role: 'assistant', content: ex.output }
      ]
    }))
    .map(obj => JSON.stringify(obj))
    .join('\n');
  
  // Save to file
  fs.writeFileSync('training_data.jsonl', jsonl);
  
  return jsonl;
}
```

---

## PHI Redaction Requirements

### Critical: HIPAA 18 Identifiers

PHI detection and redaction is mandatory for medical data:

**18 HIPAA Identifiers**:
1. **Names** - Patient, provider, emergency contact
2. **Medical Record Numbers (MRN)** - xxx-xxx-xxxx
3. **Social Security Numbers (SSN)** - xxx-xx-xxxx
4. **Dates** - Birth dates, admission dates (dates > 89 years are okay)
5. **Phone Numbers** - All 10-digit numbers
6. **Email Addresses** - All email formats
7. **Account Numbers** - Financial, health plan
8. **Health Plan Numbers** - Insurance identifiers
9. **Certificate/License Numbers** - Medical licenses, vehicle
10. **ZIP Codes** - Geographic data (last 3 digits are okay)
11. **IP Addresses** - Network identifiers
12. **URLs** - Web addresses
13. **Biometric Identifiers** - Fingerprints, retinal scans
14. **Facial Images** - Photos of faces
15. **Vehicle IDs** - License plates
16. **Device IDs** - Implant serial numbers
17. **Ages** - Over 89 years (coded as 89+)
18. **Any Unique Identifying Number** - Lab account, etc.

### PHI Scanning Pipeline

```typescript
import { RegexPhiScanner } from '@researchflow/phi-engine';

const phiScanner = new RegexPhiScanner();

async function redactPHIFromData(text: string): Promise<{
  redactedText: string;
  findings: PhiFinding[];
  riskLevel: 'none' | 'low' | 'medium' | 'high';
}> {
  // Scan for PHI
  const findings = phiScanner.scan(text);
  
  // Determine risk level
  let riskLevel: 'none' | 'low' | 'medium' | 'high' = 'none';
  
  if (findings.length === 0) {
    riskLevel = 'none';
  } else {
    const highConfidenceCount = findings.filter(f => f.confidence > 0.9).length;
    
    if (highConfidenceCount === 0) {
      riskLevel = 'low';
    } else if (highConfidenceCount <= 3) {
      riskLevel = 'medium';
    } else {
      riskLevel = 'high';
    }
  }
  
  // Redact
  const redactedText = phiScanner.redact(text);
  
  return { redactedText, findings, riskLevel };
}
```

### Redaction Verification

```typescript
async function verifyRedaction(originalText: string, redactedText: string) {
  const originalFindings = phiScanner.scan(originalText);
  const redactedFindings = phiScanner.scan(redactedText);
  
  console.log(`Original findings: ${originalFindings.length}`);
  console.log(`After redaction: ${redactedFindings.length}`);
  
  // Check for residual PHI (should be < 5% of original)
  const residualRate = redactedFindings.length / Math.max(originalFindings.length, 1);
  
  if (residualRate > 0.05) {
    console.warn('WARNING: Redaction incomplete, residual PHI detected');
    return false;
  }
  
  return true;
}

// Example usage
const example = 'Patient John Smith (DOB: 01/15/1965, SSN: 123-45-6789) presented...';
const { redactedText, findings, riskLevel } = await redactPHIFromData(example);

console.log(`Risk Level: ${riskLevel}`);
console.log(`Findings: ${JSON.stringify(findings)}`);
console.log(`Redacted: ${redactedText}`);
// Output: Redacted: Patient [REDACTED-NAME] (DOB: [REDACTED-DOB], SSN: [REDACTED-SSN])...
```

---

## LoRA Training Setup

### Installation & Dependencies

```bash
# Install PyTorch and LoRA libraries
pip install torch torchvision torchaudio
pip install peft transformers datasets evaluate

# For GPU acceleration (recommended)
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
```

### Training Configuration

```python
from peft import LoraConfig, get_peft_model
from transformers import AutoModelForCausalLM, AutoTokenizer, TrainingArguments, Trainer
from datasets import load_dataset

# Model selection
model_name = "meta-llama/Llama-2-7b-hf"  # Or any open-source model

# LoRA Configuration
lora_config = LoraConfig(
    r=8,                           # LoRA rank
    lora_alpha=16,                 # LoRA scaling
    target_modules=["q_proj", "v_proj"],  # Target attention layers
    lora_dropout=0.05,
    bias="none",
    task_type="CAUSAL_LM"
)

# Load model and tokenizer
model = AutoModelForCausalLM.from_pretrained(
    model_name,
    device_map="auto",
    load_in_8bit=True  # For memory efficiency
)
tokenizer = AutoTokenizer.from_pretrained(model_name)

# Apply LoRA
model = get_peft_model(model, lora_config)
print(model.print_trainable_parameters())
# Output: trainable params: 4,194,304 || all params: 6,738,415,616 || trainable%: 0.06
```

### Data Preparation for LoRA

```python
# Load and preprocess dataset
dataset = load_dataset("json", data_files="training_data.jsonl")

def preprocess_function(examples):
    inputs = examples["input"]
    targets = examples["output"]
    
    model_inputs = tokenizer(
        inputs,
        max_length=512,
        padding="max_length",
        truncation=True
    )
    
    labels = tokenizer(
        targets,
        max_length=512,
        padding="max_length",
        truncation=True
    )
    
    model_inputs["labels"] = labels["input_ids"]
    return model_inputs

tokenized_dataset = dataset.map(
    preprocess_function,
    batched=True,
    remove_columns=dataset["train"].column_names
)

train_dataset = tokenized_dataset["train"]
eval_dataset = tokenized_dataset.get("validation")
```

### Training Script

```python
# Training arguments
training_args = TrainingArguments(
    output_dir="./lora_checkpoints",
    learning_rate=1e-4,
    per_device_train_batch_size=4,
    per_device_eval_batch_size=4,
    num_train_epochs=3,
    weight_decay=0.01,
    eval_strategy="epoch",
    save_strategy="epoch",
    load_best_model_at_end=True,
    gradient_checkpointing=True,
    gradient_accumulation_steps=4,
    warmup_steps=100,
    logging_steps=10
)

# Create trainer
trainer = Trainer(
    model=model,
    args=training_args,
    train_dataset=train_dataset,
    eval_dataset=eval_dataset,
    tokenizer=tokenizer
)

# Train
trainer.train()

# Save LoRA weights
model.save_pretrained("./lora_final")
```

### Evaluation During Training

```python
import evaluate

# Load metrics
rouge = evaluate.load('rouge')
bleu = evaluate.load('bleu')

def compute_metrics(eval_preds):
    predictions, labels = eval_preds
    
    decoded_preds = tokenizer.batch_decode(predictions, skip_special_tokens=True)
    decoded_labels = tokenizer.batch_decode(labels, skip_special_tokens=True)
    
    rouge_result = rouge.compute(
        predictions=decoded_preds,
        references=decoded_labels
    )
    
    bleu_result = bleu.compute(
        predictions=decoded_preds,
        references=decoded_labels
    )
    
    return {
        'rouge1': rouge_result['rouge1'],
        'bleu': bleu_result['bleu']
    }

trainer = Trainer(
    model=model,
    args=training_args,
    train_dataset=train_dataset,
    eval_dataset=eval_dataset,
    compute_metrics=compute_metrics,
    tokenizer=tokenizer
)
```

---

## Model Deployment to Ollama

### Install Ollama

```bash
# macOS
brew install ollama

# Linux
curl https://ollama.ai/install.sh | sh

# Windows
# Download from https://ollama.ai
```

### Create Modelfile for Fine-Tuned Model

```dockerfile
# Modelfile
FROM llama2:7b

# Add system prompt
SYSTEM You are a helpful research analysis assistant.

# Set parameters for generation
PARAMETER temperature 0.3
PARAMETER top_p 0.9
PARAMETER top_k 40

# Optional: Quantization settings
PARAMETER num_predict 2048
```

### Integrate LoRA with Base Model

```python
import subprocess
import json

def create_ollama_model_with_lora(
    model_name: str,
    base_model: str,
    lora_weights_path: str
):
    """Create Ollama model with integrated LoRA weights"""
    
    # Create modelfile
    modelfile_content = f"""FROM {base_model}

# Set system prompt
SYSTEM You are a research analysis assistant specializing in extracting and analyzing academic papers.

# LoRA Integration
ADAPTER {lora_weights_path}

# Generation parameters
PARAMETER temperature 0.3
PARAMETER top_p 0.9
PARAMETER repeat_penalty 1.1
PARAMETER top_k 40
"""
    
    # Write modelfile
    with open("Modelfile", "w") as f:
        f.write(modelfile_content)
    
    # Create model in Ollama
    result = subprocess.run(
        ["ollama", "create", model_name, "-f", "Modelfile"],
        capture_output=True,
        text=True
    )
    
    if result.returncode != 0:
        raise Exception(f"Failed to create Ollama model: {result.stderr}")
    
    return True

# Usage
create_ollama_model_with_lora(
    model_name="research-analyzer",
    base_model="llama2:7b",
    lora_weights_path="./lora_final"
)
```

### Run Local Model with Ollama

```typescript
import axios from 'axios';

async function queryOllamaModel(prompt: string, modelName: string = "research-analyzer") {
  try {
    const response = await axios.post('http://localhost:11434/api/generate', {
      model: modelName,
      prompt: prompt,
      stream: false
    });
    
    return response.data.response;
  } catch (error) {
    console.error('Ollama request failed:', error);
    throw error;
  }
}

// Example usage
const result = await queryOllamaModel(
  'Extract the methodology from this paper: [paper text]'
);

console.log(result);
```

### Batch Inference with Ollama

```typescript
async function batchInferenceWithOllama(
  prompts: string[],
  modelName: string = "research-analyzer",
  concurrency: number = 3
) {
  const results: string[] = [];
  
  // Process in batches with concurrency control
  for (let i = 0; i < prompts.length; i += concurrency) {
    const batch = prompts.slice(i, i + concurrency);
    const batchResults = await Promise.all(
      batch.map(prompt => queryOllamaModel(prompt, modelName))
    );
    results.push(...batchResults);
  }
  
  return results;
}
```

---

## Integration Examples

### Example 1: End-to-End Training Pipeline

```typescript
async function completeTrainingPipeline() {
  // 1. Collect data
  const rawData = await collectTrainingExamples();
  
  // 2. Redact PHI
  const redactedData = await Promise.all(
    rawData.map(async (ex) => ({
      ...ex,
      output: (await redactPHIFromData(ex.output)).redactedText
    }))
  );
  
  // 3. Validate
  const { valid, errors } = await validateTrainingData(redactedData);
  if (!valid) {
    console.error('Validation errors:', errors);
    return;
  }
  
  // 4. Split
  const { train, val, test } = splitTrainingData(redactedData);
  console.log(`Train: ${train.length}, Val: ${val.length}, Test: ${test.length}`);
  
  // 5. Format
  await formatForOpenAI(train);
  
  // 6. Train with LoRA (external Python script)
  console.log('Running Python training script...');
  
  // 7. Create Ollama model
  await createOllamaModel('research-analyzer', 'llama2:7b', './lora_final');
  
  console.log('Training complete!');
}
```

### Example 2: Model Comparison

```typescript
async function compareModels(testPrompts: string[]) {
  const models = {
    'openai': async (prompt: string) => {
      return await callOpenAI(prompt, 'gpt-4o');
    },
    'ollama-base': async (prompt: string) => {
      return await queryOllamaModel(prompt, 'llama2:7b');
    },
    'ollama-finetuned': async (prompt: string) => {
      return await queryOllamaModel(prompt, 'research-analyzer');
    }
  };
  
  const results: Record<string, any> = {};
  
  for (const [modelName, modelFn] of Object.entries(models)) {
    const startTime = Date.now();
    const outputs = await Promise.all(
      testPrompts.map(p => modelFn(p))
    );
    const duration = Date.now() - startTime;
    
    results[modelName] = {
      outputs,
      totalTime: duration,
      avgTime: duration / testPrompts.length
    };
  }
  
  return results;
}
```

---

## Performance Optimization

### LoRA Configuration Tuning

```typescript
interface LoRAHyperparameters {
  rank: number;                 // 4-64, higher = more flexibility
  alpha: number;                // Usually 2x rank
  learningRate: number;         // 1e-4 to 1e-3
  epochs: number;               // 2-5 for fine-tuning
  batchSize: number;            // 4-32 depending on VRAM
  warmupSteps: number;          // 5-10% of total steps
}

// Conservative (faster, less VRAM)
const conservative: LoRAHyperparameters = {
  rank: 8,
  alpha: 16,
  learningRate: 1e-4,
  epochs: 2,
  batchSize: 4,
  warmupSteps: 100
};

// Balanced (recommended)
const balanced: LoRAHyperparameters = {
  rank: 16,
  alpha: 32,
  learningRate: 5e-4,
  epochs: 3,
  batchSize: 8,
  warmupSteps: 200
};

// Aggressive (slower, better results)
const aggressive: LoRAHyperparameters = {
  rank: 32,
  alpha: 64,
  learningRate: 1e-3,
  epochs: 5,
  batchSize: 16,
  warmupSteps: 500
};
```

---

*Documentation Version: 1.0 | Phase 10 Deliverable*
