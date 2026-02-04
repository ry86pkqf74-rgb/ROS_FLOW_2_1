# Quick Start Guide - Fine-Tuning Data Preparation

## One-Line Summary
Prepare research papers for LLM fine-tuning with HIPAA-compliant PHI redaction and Alpaca instruction format.

## Installation

```bash
# No additional installation needed - uses standard library + pandas
pip install pandas  # If not already installed
```

## Quick Examples

### 1. Prepare Abstract Summarization Data (Most Common)

```bash
python src/training/prepare_finetune_data.py \
  --input-dir data/research_papers \
  --output-dir models/abstract_finetuning \
  --task-type abstract
```

**Output**: 
- `models/abstract_finetuning/abstract/train.jsonl` - 80% of examples
- `models/abstract_finetuning/abstract/validation.jsonl` - 10% of examples
- `models/abstract_finetuning/abstract/test.jsonl` - 10% of examples

### 2. Prepare Manuscript Structure Data

```bash
python src/training/prepare_finetune_data.py \
  --input-dir data/published_manuscripts \
  --output-dir models/manuscript_finetuning \
  --task-type manuscript
```

### 3. Prepare IRB Protocol Data

```bash
python src/training/prepare_finetune_data.py \
  --input-dir data/irb_protocols \
  --output-dir models/irb_finetuning \
  --task-type irb
```

### 4. Disable PHI Redaction (Testing Only)

```bash
python src/training/prepare_finetune_data.py \
  --input-dir data/papers \
  --output-dir output \
  --task-type abstract \
  --no-redact-phi
```

### 5. Custom Split Ratios

```bash
python src/training/prepare_finetune_data.py \
  --input-dir data/papers \
  --output-dir output \
  --task-type manuscript \
  --train-ratio 0.85 \
  --validation-ratio 0.10 \
  --seed 2024
```

## Programmatic Usage

```python
from pathlib import Path
from training.prepare_finetune_data import FinetuneDataPreparator, TaskType

# One-liner approach
preparer = FinetuneDataPreparator(redact_phi=True)
split = preparer.prepare_dataset(Path("data/papers"), TaskType.ABSTRACT)
preparer.save_dataset(split, Path("output"), TaskType.ABSTRACT)

# Print statistics
print(f"Generated {preparer.stats['total_instructions_generated']} examples")
print(f"Redacted {preparer.stats['total_phi_redactions']} PHI instances")
```

## What Gets Generated?

### For Each Document:

**ABSTRACT Task:**
- 2 examples per section (>200 chars)
- Summarization + Information Extraction

**MANUSCRIPT Task:**
- 3 examples per document
- Section Identification + Completeness + Statistics

**IRB Task:**
- 4 examples per document
- Risk Assessment + Vulnerable Populations + PHI + Protocol

### Output Format (JSONL):

```json
{
  "instruction": "Summarize the following research paper section...",
  "input": "The study examined 500 patients with diabetes...",
  "output": "[Generated summary would synthesize key points...]",
  "task_type": "abstract",
  "phi_redacted": true,
  "source_document": "/data/paper1.txt",
  "metadata": {"section_index": 0, "subtask": "summarization"}
}
```

## File Support

**Supported Input Formats:**
- `.txt` - Plain text
- `.json` - JSON with 'text'/'content'/'abstract' fields
- `.csv` - CSV with 'text'/'content'/'abstract' columns

**Directory Structure**: Recursively loads all files in input directory

## PHI Redaction

**Automatically Redacts:**
- Names (Dr. Smith → [REDACTED_NAME])
- Emails (john@example.com → [REDACTED_EMAIL])
- Phone numbers (404-555-1234 → [REDACTED_PHONE])
- SSNs (123-45-6789 → [REDACTED_SSN])
- Medical record numbers → [REDACTED_MRN]
- Dates of birth → [REDACTED_DOB]
- Addresses → [REDACTED_ADDRESS]
- ZIP codes → [REDACTED_ZIP]
- IP addresses → [REDACTED_IP]
- And 6 more categories...

## Check Results

```bash
# View example records
head -5 models/abstract_finetuning/abstract/train.jsonl | jq .

# Count examples
wc -l models/abstract_finetuning/abstract/*.jsonl

# Check statistics
cat models/abstract_finetuning/abstract/split_stats.json | jq .
cat models/abstract_finetuning/abstract/preparation_stats.json | jq .
```

## Common Issues

### No files loaded?
- Check input directory path exists
- Ensure files end with .txt, .json, or .csv
- Verify encoding is UTF-8

### Few examples generated?
- Document sections may be too short (<50 chars for split, <200 for task)
- Check document content quality
- Ensure consistent formatting

### PHI redaction failing?
- Review confidence scores in preparation_stats.json
- Some patterns intentionally strict (e.g., ZIP codes)
- Can disable with `--no-redact-phi` for testing

## Performance Tips

For 100+ documents:
```bash
# Increase verbosity to monitor progress
export LOGLEVEL=DEBUG

# Process in batches by task type
python src/training/prepare_finetune_data.py \
  --input-dir data/batch1 \
  --output-dir output/batch1 \
  --task-type abstract
```

## Next Steps

1. Prepare input directory with research papers
2. Run one of the quick examples above
3. Check output JSONL files
4. Review statistics in split_stats.json and preparation_stats.json
5. Use train.jsonl with fine-tuning framework (e.g., Hugging Face)

## Fine-Tuning with Output

```python
# Using Hugging Face transformers
from datasets import load_dataset

# Load training data
train_dataset = load_dataset("json", data_files="models/abstract_finetuning/abstract/train.jsonl")

# Fine-tune your model...
```

## Help

```bash
python src/training/prepare_finetune_data.py --help
```

## Documentation

- Full details: `README.md`
- Implementation: `IMPLEMENTATION_SUMMARY.md`
- Code: `prepare_finetune_data.py`
