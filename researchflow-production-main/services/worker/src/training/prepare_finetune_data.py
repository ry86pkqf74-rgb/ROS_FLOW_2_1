"""Fine-tuning data preparation pipeline for medical AI models.

This module provides classes and utilities for preparing training data for
fine-tuning large language models on medical tasks such as manuscript
refinement, IRB reviews, and abstract writing. It includes:

- PHIRedactionPipeline: Redacts Protected Health Information
- FinetuneDataPreparator: Converts data to Alpaca format
- DatasetSplit: Represents train/val/test splits
- CLI: Command-line interface for running the pipeline
"""

import argparse
import json
import logging
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)


@dataclass
class DatasetSplit:
    """Represents train/validation/test splits of a dataset.
    
    Attributes:
        train: List of training examples
        validation: List of validation examples
        test: List of test examples
        train_ratio: Ratio of training data (default: 0.7)
        val_ratio: Ratio of validation data (default: 0.15)
        test_ratio: Ratio of test data (default: 0.15)
    """
    
    train: list[dict[str, Any]] = field(default_factory=list)
    validation: list[dict[str, Any]] = field(default_factory=list)
    test: list[dict[str, Any]] = field(default_factory=list)
    train_ratio: float = 0.7
    val_ratio: float = 0.15
    test_ratio: float = 0.15
    
    def __post_init__(self) -> None:
        """Validate ratios sum to 1.0."""
        total = self.train_ratio + self.val_ratio + self.test_ratio
        if not (0.99 < total < 1.01):  # Allow small floating point variance
            raise ValueError(
                f"Split ratios must sum to 1.0, got {total}"
            )
    
    @property
    def total_examples(self) -> int:
        """Return total number of examples across all splits."""
        return len(self.train) + len(self.validation) + len(self.test)
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return asdict(self)
    
    def save(self, path: Path) -> None:
        """Save splits to JSON file.
        
        Args:
            path: Path to save the JSON file
        """
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, 'w') as f:
            json.dump(self.to_dict(), f, indent=2)
        logger.info(f"Saved dataset splits to {path}")
    
    @classmethod
    def load(cls, path: Path) -> "DatasetSplit":
        """Load splits from JSON file.
        
        Args:
            path: Path to the JSON file
            
        Returns:
            DatasetSplit instance
        """
        with open(path, 'r') as f:
            data = json.load(f)
        return cls(**data)


class PHIRedactionPipeline:
    """Pipeline for redacting Protected Health Information from text.
    
    Redacts common PHI patterns including:
    - Patient names
    - Medical record numbers
    - Dates of birth
    - Phone numbers
    - Email addresses
    - Social Security numbers
    - Medical facility names
    """
    
    # Regex patterns for common PHI
    PHI_PATTERNS = {
        'mrn': r'\bMRN\s*[:\-]?\s*(\d{5,})\b',
        'ssn': r'\b\d{3}-\d{2}-\d{4}\b',
        'phone': r'\b(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b',
        'email': r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
        'dob': r'\b(?:DOB|Date of Birth|Birth Date)\s*[:\-]?\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
        'hospital': r'\b(?:Hospital|Medical Center|Clinic|Institute)\s+(?:of\s+)?[A-Z][A-Za-z\s&]+\b',
    }
    
    def __init__(self, additional_patterns: Optional[dict[str, str]] = None):
        """Initialize the PHI redaction pipeline.
        
        Args:
            additional_patterns: Optional dictionary of additional regex patterns
                                to redact beyond the default set
        """
        self.patterns = self.PHI_PATTERNS.copy()
        if additional_patterns:
            self.patterns.update(additional_patterns)
        
        self.redaction_count = 0
    
    def redact(self, text: str, redaction_token: str = "[REDACTED]") -> str:
        """Redact PHI from text.
        
        Args:
            text: Text to redact
            redaction_token: Token to replace PHI with (default: "[REDACTED]")
            
        Returns:
            Text with PHI redacted
        """
        redacted_text = text
        
        for pattern_name, pattern in self.patterns.items():
            matches = re.finditer(pattern, redacted_text, re.IGNORECASE)
            for match in matches:
                self.redaction_count += 1
                redacted_text = redacted_text.replace(match.group(0), redaction_token)
        
        return redacted_text
    
    def reset_count(self) -> None:
        """Reset the redaction counter."""
        self.redaction_count = 0


class FinetuneDataPreparator:
    """Prepares training data in Alpaca format for fine-tuning.
    
    Converts raw training examples to Alpaca instruction format:
    {
        "instruction": "Task description",
        "input": "Context or input text",
        "output": "Expected output/answer"
    }
    
    Supports tasks:
    - manuscript_refinement: Improve scientific manuscripts
    - irb_review: Review and comment on IRB applications
    - abstract_writing: Generate or improve abstracts
    """
    
    SUPPORTED_TASKS = {
        'manuscript_refinement',
        'irb_review',
        'abstract_writing',
    }
    
    TASK_INSTRUCTIONS = {
        'manuscript_refinement': (
            'You are an expert scientific editor. Improve the following manuscript '
            'section by enhancing clarity, fixing grammar, and strengthening arguments.'
        ),
        'irb_review': (
            'You are an Institutional Review Board (IRB) expert. Review the provided '
            'IRB application section and provide constructive feedback on compliance, '
            'ethics, and clarity.'
        ),
        'abstract_writing': (
            'You are an expert scientific writer. Generate or improve the following '
            'abstract to be concise, impactful, and highlight key contributions.'
        ),
    }
    
    def __init__(
        self,
        redaction_pipeline: Optional[PHIRedactionPipeline] = None,
        redact_phi: bool = True,
    ):
        """Initialize the fine-tuning data preparator.
        
        Args:
            redaction_pipeline: Optional custom PHI redaction pipeline
            redact_phi: Whether to redact PHI from training data (default: True)
        """
        self.redaction_pipeline = redaction_pipeline or PHIRedactionPipeline()
        self.redact_phi = redact_phi
    
    def prepare_example(
        self,
        task: str,
        input_text: str,
        output_text: str,
        custom_instruction: Optional[str] = None,
    ) -> dict[str, str]:
        """Prepare a single training example in Alpaca format.
        
        Args:
            task: Type of task (must be in SUPPORTED_TASKS)
            input_text: Input text for the example
            output_text: Expected output/response
            custom_instruction: Optional custom instruction to override task default
            
        Returns:
            Dictionary with 'instruction', 'input', and 'output' keys
            
        Raises:
            ValueError: If task is not supported
        """
        if task not in self.SUPPORTED_TASKS:
            raise ValueError(
                f"Unsupported task: {task}. "
                f"Supported tasks: {self.SUPPORTED_TASKS}"
            )
        
        instruction = custom_instruction or self.TASK_INSTRUCTIONS[task]
        
        # Redact PHI if enabled
        if self.redact_phi:
            input_text = self.redaction_pipeline.redact(input_text)
            output_text = self.redaction_pipeline.redact(output_text)
        
        return {
            'instruction': instruction,
            'input': input_text.strip(),
            'output': output_text.strip(),
        }
    
    def prepare_batch(
        self,
        examples: list[dict[str, Any]],
        task_field: str = 'task',
        input_field: str = 'input',
        output_field: str = 'output',
    ) -> list[dict[str, str]]:
        """Prepare a batch of examples.
        
        Args:
            examples: List of example dictionaries
            task_field: Field name containing the task type
            input_field: Field name containing the input text
            output_field: Field name containing the output text
            
        Returns:
            List of prepared examples in Alpaca format
        """
        prepared = []
        for example in examples:
            try:
                prepared_example = self.prepare_example(
                    task=example.get(task_field, 'manuscript_refinement'),
                    input_text=example.get(input_field, ''),
                    output_text=example.get(output_field, ''),
                )
                prepared.append(prepared_example)
            except ValueError as e:
                logger.warning(f"Skipped example: {e}")
                continue
        
        return prepared
    
    def split_dataset(
        self,
        examples: list[dict[str, str]],
        train_ratio: float = 0.7,
        val_ratio: float = 0.15,
        test_ratio: float = 0.15,
        seed: Optional[int] = None,
    ) -> DatasetSplit:
        """Split prepared examples into train/val/test sets.
        
        Args:
            examples: List of prepared examples
            train_ratio: Proportion for training set
            val_ratio: Proportion for validation set
            test_ratio: Proportion for test set
            seed: Random seed for reproducibility
            
        Returns:
            DatasetSplit object with train/val/test examples
        """
        import random
        
        if seed is not None:
            random.seed(seed)
        
        shuffled = examples.copy()
        random.shuffle(shuffled)
        
        n = len(shuffled)
        train_idx = int(n * train_ratio)
        val_idx = train_idx + int(n * val_ratio)
        
        return DatasetSplit(
            train=shuffled[:train_idx],
            validation=shuffled[train_idx:val_idx],
            test=shuffled[val_idx:],
            train_ratio=train_ratio,
            val_ratio=val_ratio,
            test_ratio=test_ratio,
        )
    
    def process_file(
        self,
        input_path: Path,
        output_path: Path,
        task_field: str = 'task',
        input_field: str = 'input',
        output_field: str = 'output',
    ) -> None:
        """Process a JSON file of examples and save prepared data.
        
        Args:
            input_path: Path to input JSON file
            output_path: Path to save prepared examples
            task_field: Field name containing task type
            input_field: Field name containing input text
            output_field: Field name containing output text
        """
        with open(input_path, 'r') as f:
            examples = json.load(f)
        
        prepared = self.prepare_batch(
            examples,
            task_field=task_field,
            input_field=input_field,
            output_field=output_field,
        )
        
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w') as f:
            json.dump(prepared, f, indent=2)
        
        logger.info(
            f"Processed {len(examples)} examples, saved {len(prepared)} to {output_path}"
        )


def main() -> None:
    """CLI interface for the fine-tuning data preparation pipeline."""
    parser = argparse.ArgumentParser(
        description="Prepare data for fine-tuning medical AI models"
    )
    parser.add_argument(
        '--input',
        type=Path,
        required=True,
        help='Path to input JSON file with examples',
    )
    parser.add_argument(
        '--output',
        type=Path,
        required=True,
        help='Path to save prepared examples',
    )
    parser.add_argument(
        '--split',
        type=Path,
        help='Path to save train/val/test splits (optional)',
    )
    parser.add_argument(
        '--no-redact',
        action='store_true',
        help='Disable PHI redaction',
    )
    parser.add_argument(
        '--task-field',
        default='task',
        help='Field name for task type (default: task)',
    )
    parser.add_argument(
        '--input-field',
        default='input',
        help='Field name for input text (default: input)',
    )
    parser.add_argument(
        '--output-field',
        default='output',
        help='Field name for output text (default: output)',
    )
    parser.add_argument(
        '--train-ratio',
        type=float,
        default=0.7,
        help='Training set ratio (default: 0.7)',
    )
    parser.add_argument(
        '--val-ratio',
        type=float,
        default=0.15,
        help='Validation set ratio (default: 0.15)',
    )
    parser.add_argument(
        '--seed',
        type=int,
        help='Random seed for reproducibility (optional)',
    )
    parser.add_argument(
        '--log-level',
        default='INFO',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        help='Logging level (default: INFO)',
    )
    
    args = parser.parse_args()
    
    # Setup logging
    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    )
    
    # Validate input file
    if not args.input.exists():
        logger.error(f"Input file not found: {args.input}")
        return
    
    # Create preparator and process file
    preparator = FinetuneDataPreparator(redact_phi=not args.no_redact)
    preparator.process_file(
        args.input,
        args.output,
        task_field=args.task_field,
        input_field=args.input_field,
        output_field=args.output_field,
    )
    
    # Create splits if requested
    if args.split:
        with open(args.output, 'r') as f:
            prepared_examples = json.load(f)
        
        test_ratio = 1.0 - args.train_ratio - args.val_ratio
        splits = preparator.split_dataset(
            prepared_examples,
            train_ratio=args.train_ratio,
            val_ratio=args.val_ratio,
            test_ratio=test_ratio,
            seed=args.seed,
        )
        splits.save(args.split)
        logger.info(
            f"Dataset splits: train={len(splits.train)}, "
            f"val={len(splits.validation)}, test={len(splits.test)}"
        )
    
    logger.info("Fine-tuning data preparation complete!")


if __name__ == '__main__':
    main()
