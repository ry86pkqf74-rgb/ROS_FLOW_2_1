#!/usr/bin/env python3
"""
Training Data Preparation for ResearchFlow Fine-Tuning

Prepares training data for LoRA fine-tuning of research-specific models.
Handles PHI redaction, format conversion, and quality filtering.

Usage:
    python scripts/prepare_training_data.py --input data/raw --output data/training --task manuscript

Linear Issue: ROS-82
"""

import argparse
import json
import logging
import os
import sys
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional, Iterator
import hashlib
import re

import httpx
from datasets import Dataset

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)


@dataclass
class TrainingExample:
    """A single training example for fine-tuning."""
    instruction: str
    input: str
    output: str
    task_type: str
    source: str
    quality_score: float
    metadata: Dict[str, Any]


@dataclass
class DatasetStats:
    """Statistics about the prepared dataset."""
    total_examples: int
    examples_by_task: Dict[str, int]
    avg_input_length: float
    avg_output_length: float
    phi_redacted: int
    quality_filtered: int


class TrainingDataPreparer:
    """Prepares training data with PHI scanning and quality filtering."""
    
    # Task-specific prompts for training
    TASK_PROMPTS = {
        "manuscript_refinement": {
            "instruction": "Refine the following manuscript section to improve clarity, scientific accuracy, and adherence to publication standards.",
            "system": "You are an expert scientific editor specializing in clinical research manuscripts."
        },
        "statistical_analysis": {
            "instruction": "Analyze the following data and provide appropriate statistical analysis with interpretation.",
            "system": "You are a biostatistician with expertise in clinical research methods."
        },
        "data_cleaning": {
            "instruction": "Review the following dataset description and provide data cleaning recommendations.",
            "system": "You are a data quality specialist for clinical research."
        },
        "irb_review": {
            "instruction": "Review the following protocol excerpt for IRB compliance issues.",
            "system": "You are an IRB compliance specialist familiar with 45 CFR 46 and HIPAA."
        },
        "citation_formatting": {
            "instruction": "Format the following references according to the specified citation style.",
            "system": "You are a scientific reference specialist."
        }
    }

    def __init__(
        self,
        orchestrator_url: str = "http://localhost:3001",
        min_quality_score: float = 0.7,
        max_examples: Optional[int] = None,
    ):
        self.orchestrator_url = orchestrator_url
        self.min_quality_score = min_quality_score
        self.max_examples = max_examples
        self.http_client = httpx.Client(timeout=30.0)
        
        self.stats = DatasetStats(
            total_examples=0,
            examples_by_task={},
            avg_input_length=0,
            avg_output_length=0,
            phi_redacted=0,
            quality_filtered=0,
        )

    def prepare_dataset(
        self,
        input_dir: Path,
        output_dir: Path,
        task_type: str,
    ) -> Dataset:
        """
        Prepare a HuggingFace Dataset from raw training data.
        
        Args:
            input_dir: Directory containing raw training files
            output_dir: Directory to save processed dataset
            task_type: Type of task (manuscript_refinement, statistical_analysis, etc.)
        
        Returns:
            HuggingFace Dataset ready for training
        """
        logger.info(f"Preparing {task_type} dataset from {input_dir}")
        
        examples = []
        input_lengths = []
        output_lengths = []
        
        for example in self._load_examples(input_dir, task_type):
            # PHI scan and redact
            redacted_example = self._scan_and_redact_phi(example)
            if redacted_example is None:
                continue
            
            # Quality filter
            if redacted_example.quality_score < self.min_quality_score:
                self.stats.quality_filtered += 1
                continue
            
            # Convert to training format
            training_item = self._to_training_format(redacted_example, task_type)
            examples.append(training_item)
            
            input_lengths.append(len(training_item["input"]))
            output_lengths.append(len(training_item["output"]))
            
            # Check max examples
            if self.max_examples and len(examples) >= self.max_examples:
                break
        
        # Update stats
        self.stats.total_examples = len(examples)
        self.stats.examples_by_task[task_type] = len(examples)
        self.stats.avg_input_length = sum(input_lengths) / len(input_lengths) if input_lengths else 0
        self.stats.avg_output_length = sum(output_lengths) / len(output_lengths) if output_lengths else 0
        
        # Create HuggingFace dataset
        dataset = Dataset.from_list(examples)
        
        # Save to disk
        output_dir.mkdir(parents=True, exist_ok=True)
        dataset.save_to_disk(str(output_dir / task_type))
        
        # Save stats
        with open(output_dir / f"{task_type}_stats.json", "w") as f:
            json.dump(asdict(self.stats), f, indent=2)
        
        logger.info(f"Prepared {len(examples)} examples for {task_type}")
        logger.info(f"Stats: {asdict(self.stats)}")
        
        return dataset

    def _load_examples(
        self,
        input_dir: Path,
        task_type: str,
    ) -> Iterator[TrainingExample]:
        """Load raw examples from input directory."""
        input_path = Path(input_dir)
        
        # Support multiple formats
        for file_path in input_path.glob("**/*.json"):
            try:
                with open(file_path) as f:
                    data = json.load(f)
                
                # Handle list or single example
                items = data if isinstance(data, list) else [data]
                
                for item in items:
                    yield TrainingExample(
                        instruction=item.get("instruction", ""),
                        input=item.get("input", ""),
                        output=item.get("output", ""),
                        task_type=item.get("task_type", task_type),
                        source=str(file_path),
                        quality_score=item.get("quality_score", 0.8),
                        metadata=item.get("metadata", {}),
                    )
            except Exception as e:
                logger.warning(f"Failed to load {file_path}: {e}")
        
        # Also support JSONL format
        for file_path in input_path.glob("**/*.jsonl"):
            try:
                with open(file_path) as f:
                    for line in f:
                        if line.strip():
                            item = json.loads(line)
                            yield TrainingExample(
                                instruction=item.get("instruction", ""),
                                input=item.get("input", ""),
                                output=item.get("output", ""),
                                task_type=item.get("task_type", task_type),
                                source=str(file_path),
                                quality_score=item.get("quality_score", 0.8),
                                metadata=item.get("metadata", {}),
                            )
            except Exception as e:
                logger.warning(f"Failed to load {file_path}: {e}")

    def _scan_and_redact_phi(self, example: TrainingExample) -> Optional[TrainingExample]:
        """Scan for PHI and redact if found."""
        try:
            # Combine all text for scanning
            full_text = f"{example.instruction}\n{example.input}\n{example.output}"
            
            # Call orchestrator PHI scan endpoint
            response = self.http_client.post(
                f"{self.orchestrator_url}/api/phi/scan",
                json={"text": full_text, "redact": True}
            )
            
            if response.status_code != 200:
                logger.warning(f"PHI scan failed: {response.status_code}")
                # Fail closed - skip this example
                return None
            
            result = response.json()
            
            if result.get("has_phi"):
                self.stats.phi_redacted += 1
                
                # Get redacted text and split back
                redacted = result.get("redacted_text", full_text)
                parts = redacted.split("\n", 2)
                
                return TrainingExample(
                    instruction=parts[0] if len(parts) > 0 else example.instruction,
                    input=parts[1] if len(parts) > 1 else example.input,
                    output=parts[2] if len(parts) > 2 else example.output,
                    task_type=example.task_type,
                    source=example.source,
                    quality_score=example.quality_score,
                    metadata={
                        **example.metadata,
                        "phi_redacted": True,
                        "phi_entities": result.get("entities", []),
                    },
                )
            
            return example
            
        except Exception as e:
            logger.warning(f"PHI scan error: {e}")
            # Fail closed
            return None

    def _to_training_format(
        self,
        example: TrainingExample,
        task_type: str,
    ) -> Dict[str, str]:
        """Convert example to training format (Alpaca-style)."""
        task_config = self.TASK_PROMPTS.get(task_type, {
            "instruction": "Complete the following task:",
            "system": "You are a helpful research assistant."
        })
        
        # Alpaca format with system prompt
        return {
            "instruction": task_config["instruction"],
            "input": example.input,
            "output": example.output,
            "system": task_config["system"],
            "task_type": task_type,
            "source_hash": hashlib.md5(example.source.encode()).hexdigest()[:8],
        }

    def close(self):
        """Clean up resources."""
        self.http_client.close()


def main():
    parser = argparse.ArgumentParser(
        description="Prepare training data for ResearchFlow fine-tuning"
    )
    parser.add_argument(
        "--input", "-i",
        type=Path,
        required=True,
        help="Input directory with raw training data"
    )
    parser.add_argument(
        "--output", "-o",
        type=Path,
        default=Path("data/training"),
        help="Output directory for processed dataset"
    )
    parser.add_argument(
        "--task", "-t",
        choices=list(TrainingDataPreparer.TASK_PROMPTS.keys()),
        required=True,
        help="Task type for training"
    )
    parser.add_argument(
        "--min-quality",
        type=float,
        default=0.7,
        help="Minimum quality score to include (0-1)"
    )
    parser.add_argument(
        "--max-examples",
        type=int,
        default=None,
        help="Maximum number of examples to include"
    )
    parser.add_argument(
        "--orchestrator-url",
        default=os.getenv("ORCHESTRATOR_URL", "http://localhost:3001"),
        help="Orchestrator URL for PHI scanning"
    )
    
    args = parser.parse_args()
    
    preparer = TrainingDataPreparer(
        orchestrator_url=args.orchestrator_url,
        min_quality_score=args.min_quality,
        max_examples=args.max_examples,
    )
    
    try:
        dataset = preparer.prepare_dataset(
            input_dir=args.input,
            output_dir=args.output,
            task_type=args.task,
        )
        
        print(f"\n✅ Dataset prepared successfully!")
        print(f"   Examples: {len(dataset)}")
        print(f"   Location: {args.output / args.task}")
        
    except Exception as e:
        logger.error(f"Failed to prepare dataset: {e}")
        sys.exit(1)
    finally:
        preparer.close()


if __name__ == "__main__":
    main()
