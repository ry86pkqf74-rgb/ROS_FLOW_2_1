"""Training module for fine-tuning medical AI models.

This module provides utilities for preparing, processing, and managing
training data for fine-tuning large language models on medical tasks
such as manuscript refinement, IRB reviews, and abstract writing.

Exports:
    PHIRedactionPipeline: Pipeline for redacting Protected Health Information
    FinetuneDataPreparator: Converter for training data to Alpaca format
    DatasetSplit: Dataclass representing train/val/test splits
"""

from training.prepare_finetune_data import (
    DatasetSplit,
    FinetuneDataPreparator,
    PHIRedactionPipeline,
)

__all__ = [
    "PHIRedactionPipeline",
    "FinetuneDataPreparator",
    "DatasetSplit",
]

__version__ = "0.1.0"
