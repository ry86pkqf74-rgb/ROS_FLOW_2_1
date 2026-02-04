# Training Module

Fine-tuning data preparation pipeline for medical AI models.

## Overview

The training module provides utilities for preparing, processing, and managing training data for fine-tuning large language models on medical tasks. It includes:

- **PHIRedactionPipeline**: Automatically redacts Protected Health Information from training data
- **FinetuneDataPreparator**: Converts raw examples to Alpaca instruction format
- **DatasetSplit**: Manages train/validation/test splits
- **CLI Interface**: Command-line tools for batch processing

## Features

### Supported Tasks

- **manuscript_refinement**: Improve clarity, grammar, and argumentation in scientific manuscripts
- **irb_review**: Review and provide feedback on Institutional Review Board applications
- **abstract_writing**: Generate or refine scientific abstracts

### PHI Redaction

Automatically detects and redacts:
- Patient names
- Medical record numbers (MRN)
- Social Security numbers (SSN)
- Phone numbers
- Email addresses
- Dates of birth
- Medical facility names

### Data Format

Training data is converted to Alpaca instruction format:

```json
{
  "instruction": "You are an expert scientific editor...",
  "input": "Scientific manuscript text to improve...",
  "output": "Improved manuscript text..."
}
```

## Installation

The module requires Python 3.11+ with no external dependencies beyond the standard library.

```bash
pip install -r requirements.txt  # if using a requirements file
```

## Usage

### Python API

#### Basic Example

```python
from training import FinetuneDataPreparator, PHIRedactionPipeline, DatasetSplit

# Create a preparator with PHI redaction
preparator = FinetuneDataPreparator(redact_phi=True)

# Prepare a single example
example = preparator.prepare_example(
    task='manuscript_refinement',
    input_text='The results shows that the treatment was effective.',
    output_text='The results show that the treatment was effective.'
)

# Output:
# {
#     "instruction": "You are an expert scientific editor...",
#     "input": "The results shows that the treatment was effective.",
#     "output": "The results show that the treatment was effective."
# }
```

#### Processing Batch Data

```python
# Prepare multiple examples
examples = [
    {
        'task': 'manuscript_refinement',
        'input': 'Raw manuscript text...',
        'output': 'Improved manuscript text...'
    },
    # ... more examples
]

prepared = preparator.prepare_batch(examples)
```

#### Creating Dataset Splits

```python
# Split into train/val/test
splits = preparator.split_dataset(
    prepared,
    train_ratio=0.7,
    val_ratio=0.15,
    test_ratio=0.15,
    seed=42
)

# Save splits
splits.save('output/splits.json')
```

#### Processing Files

```python
from pathlib import Path

# Process JSON file with raw examples
preparator.process_file(
    input_path=Path('data/raw_examples.json'),
    output_path=Path('data/prepared_examples.json'),
    task_field='task',
    input_field='manuscript_text',
    output_field='refined_text'
)
```

#### Custom PHI Redaction

```python
# Create custom redaction pipeline
phi_pipeline = PHIRedactionPipeline(
    additional_patterns={
        'patient_id': r'\bPID\s*[:\-]?\s*(\d+)\b',
        'hospital_name': r'\b(?:Johns|Stanford|Mayo)\s+\w+\b'
    }
)

preparator = FinetuneDataPreparator(
    redaction_pipeline=phi_pipeline,
    redact_phi=True
)
```

### Command Line Interface

#### Basic Usage

```bash
python -m training.prepare_finetune_data \
  --input data/raw_examples.json \
  --output data/prepared_examples.json
```

#### With Dataset Splits

```bash
python -m training.prepare_finetune_data \
  --input data/raw_examples.json \
  --output data/prepared_examples.json \
  --split data/splits.json \
  --train-ratio 0.8 \
  --val-ratio 0.1 \
  --test-ratio 0.1
```

#### Disable PHI Redaction

```bash
python -m training.prepare_finetune_data \
  --input data/raw_examples.json \
  --output data/prepared_examples.json \
  --no-redact
```

#### Custom Field Mapping

```bash
python -m training.prepare_finetune_data \
  --input data/examples.json \
  --output data/prepared.json \
  --task-field task_type \
  --input-field source_text \
  --output-field target_text
```

#### Full Options

```bash
python -m training.prepare_finetune_data --help
```

Available options:
- `--input PATH`: Input JSON file (required)
- `--output PATH`: Output JSON file (required)
- `--split PATH`: Path to save dataset splits (optional)
- `--no-redact`: Disable PHI redaction
- `--task-field FIELD`: Field name for task type (default: task)
- `--input-field FIELD`: Field name for input text (default: input)
- `--output-field FIELD`: Field name for output text (default: output)
- `--train-ratio RATIO`: Training set proportion (default: 0.7)
- `--val-ratio RATIO`: Validation set proportion (default: 0.15)
- `--seed SEED`: Random seed for reproducibility
- `--log-level LEVEL`: Logging level (DEBUG, INFO, WARNING, ERROR)

## Input Data Format

Raw training data should be JSON with examples containing task, input, and output fields:

```json
[
  {
    "task": "manuscript_refinement",
    "input": "The studies shows significant results.",
    "output": "The studies show significant results."
  },
  {
    "task": "irb_review",
    "input": "IRB application section describing research protocol...",
    "output": "This section needs clarification on consent procedures..."
  },
  {
    "task": "abstract_writing",
    "input": "Key points: findings, implications, methods",
    "output": "We conducted a study on X, finding Y, with implications for Z."
  }
]
```

## Output Data Format

Prepared training data in Alpaca format:

```json
[
  {
    "instruction": "You are an expert scientific editor. Improve the following manuscript section...",
    "input": "The studies shows significant results.",
    "output": "The studies show significant results."
  },
  {
    "instruction": "You are an Institutional Review Board (IRB) expert...",
    "input": "IRB application section describing research protocol...",
    "output": "This section needs clarification on consent procedures..."
  }
]
```

### Dataset Splits Output

When using `--split`, a JSON file is created with train/val/test splits:

```json
{
  "train": [...100 examples...],
  "validation": [...20 examples...],
  "test": [...20 examples...],
  "train_ratio": 0.7,
  "val_ratio": 0.15,
  "test_ratio": 0.15
}
```

## Module Structure

```
training/
├── __init__.py                 # Module initialization with exports
├── prepare_finetune_data.py    # Main implementation
│   ├── DatasetSplit           # Dataclass for train/val/test splits
│   ├── PHIRedactionPipeline   # PHI redaction pipeline
│   ├── FinetuneDataPreparator # Data preparation and formatting
│   └── main()                 # CLI entry point
└── README.md                   # This file
```

## Classes

### DatasetSplit

Dataclass representing train/validation/test splits.

**Attributes:**
- `train`: List of training examples
- `validation`: List of validation examples
- `test`: List of test examples
- `train_ratio`: Training set proportion
- `val_ratio`: Validation set proportion
- `test_ratio`: Test set proportion

**Methods:**
- `total_examples`: Property returning total count
- `to_dict()`: Convert to dictionary
- `save(path)`: Save to JSON file
- `load(path)`: Load from JSON file

### PHIRedactionPipeline

Detects and redacts Protected Health Information.

**Default patterns:**
- MRN (Medical Record Number)
- SSN (Social Security Number)
- Phone numbers
- Email addresses
- Dates of birth
- Hospital/facility names

**Methods:**
- `redact(text, redaction_token)`: Redact PHI from text
- `reset_count()`: Reset redaction counter

### FinetuneDataPreparator

Converts raw examples to Alpaca format.

**Supported tasks:**
- `manuscript_refinement`
- `irb_review`
- `abstract_writing`

**Methods:**
- `prepare_example(task, input_text, output_text)`: Prepare single example
- `prepare_batch(examples)`: Prepare multiple examples
- `split_dataset(examples, ratios)`: Create train/val/test splits
- `process_file(input_path, output_path)`: Process JSON file

## Error Handling

The module logs warnings for invalid examples and skips them without stopping:

```
WARNING: Skipped example: Unsupported task: invalid_task
```

Use `--log-level DEBUG` for detailed debugging information.

## Examples

### Example 1: Basic Manuscript Refinement

Input:
```json
[
  {
    "task": "manuscript_refinement",
    "input": "The data indicates that the hypothesis are correct.",
    "output": "The data indicate that the hypotheses are correct."
  }
]
```

Output:
```json
[
  {
    "instruction": "You are an expert scientific editor. Improve the following manuscript section...",
    "input": "The data indicates that the hypothesis are correct.",
    "output": "The data indicate that the hypotheses are correct."
  }
]
```

### Example 2: IRB Review with PHI Redaction

Input:
```json
[
  {
    "task": "irb_review",
    "input": "Study participants: Dr. Smith, 50-year-old male, SSN 123-45-6789",
    "output": "The IRB notes: Remove participant identifiers per 45 CFR 46."
  }
]
```

Output (with `--no-redact` flag):
```json
[
  {
    "instruction": "You are an Institutional Review Board expert...",
    "input": "Study participants: Dr. Smith, 50-year-old male, SSN [REDACTED]",
    "output": "The IRB notes: Remove participant identifiers per 45 CFR 46."
  }
]
```

## Performance Notes

- Redaction with regex patterns adds minimal overhead (~1-5ms per example)
- Batch processing scales linearly with dataset size
- Dataset splitting uses in-memory operations (optimized for datasets <1M examples)

## Best Practices

1. **Always redact PHI** before using data for training or sharing
2. **Validate field names** match your data structure using CLI flags
3. **Test with small datasets** first to verify output format
4. **Use fixed seeds** for reproducible splits: `--seed 42`
5. **Monitor logs** for skipped examples that may indicate data issues
6. **Version control** your prepared datasets with metadata

## Troubleshooting

### Issue: "Unsupported task" warnings

**Solution**: Verify `task` field values match one of:
- `manuscript_refinement`
- `irb_review`
- `abstract_writing`

### Issue: PHI not being redacted

**Solution**: Enable redaction (default is enabled). Check:
```bash
python -m training.prepare_finetune_data \
  --input data.json \
  --output out.json \
  --log-level DEBUG
```

### Issue: File not found errors

**Solution**: Use absolute paths or verify relative paths from working directory:
```bash
python -m training.prepare_finetune_data \
  --input $(pwd)/data/examples.json \
  --output $(pwd)/data/prepared.json
```

## License

[Specify your license here]

## Contributing

[Specify contribution guidelines here]
