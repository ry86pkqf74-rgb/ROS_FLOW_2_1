#!/usr/bin/env python3
"""
ResearchFlow - LoRA Fine-Tuning Script for Medical Manuscript Refinement
=========================================================================
Phase 4.2: Train LoRA adapters for medical manuscript writing
Linear Issue: ROS-100

This script fine-tunes LLaMA 3.1 8B with LoRA adapters for:
- Medical terminology accuracy
- Scientific writing style
- Citation formatting
- Methods section generation
"""

import os
import json
import logging
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from pathlib import Path

import torch
from datasets import load_dataset, Dataset
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    TrainingArguments,
    Trainer,
    DataCollatorForLanguageModeling,
    BitsAndBytesConfig,
)
from peft import (
    LoraConfig,
    get_peft_model,
    prepare_model_for_kbit_training,
    TaskType,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class ModelConfig:
    """Configuration for the base model."""
    model_name: str = "meta-llama/Meta-Llama-3.1-8B"
    use_4bit: bool = True
    bnb_4bit_compute_dtype: str = "float16"
    bnb_4bit_quant_type: str = "nf4"
    use_nested_quant: bool = False


@dataclass
class LoRAConfig:
    """Configuration for LoRA fine-tuning."""
    lora_r: int = 64
    lora_alpha: int = 16
    lora_dropout: float = 0.1
    bias: str = "none"
    task_type: str = "CAUSAL_LM"
    target_modules: List[str] = field(default_factory=lambda: [
        "q_proj", "k_proj", "v_proj", "o_proj",
        "gate_proj", "up_proj", "down_proj"
    ])


@dataclass
class TrainConfig:
    """Configuration for training."""
    output_dir: str = "./outputs/manuscript-lora"
    num_train_epochs: int = 3
    per_device_train_batch_size: int = 4
    per_device_eval_batch_size: int = 4
    gradient_accumulation_steps: int = 4
    learning_rate: float = 2e-4
    weight_decay: float = 0.001
    warmup_ratio: float = 0.03
    max_seq_length: int = 2048
    logging_steps: int = 10
    save_steps: int = 100
    eval_steps: int = 100
    fp16: bool = True
    optim: str = "paged_adamw_32bit"
    lr_scheduler_type: str = "cosine"
    gradient_checkpointing: bool = True


class ManuscriptDataProcessor:
    """Process medical manuscript data for training."""

    def __init__(self, tokenizer, max_length: int = 2048):
        self.tokenizer = tokenizer
        self.max_length = max_length

    def format_instruction(self, example: Dict[str, Any]) -> str:
        """Format a single example into instruction format."""
        instruction = example.get("instruction", "")
        input_text = example.get("input", "")
        output = example.get("output", "")

        if input_text:
            prompt = f"""### Instruction:
{instruction}

### Input:
{input_text}

### Response:
{output}"""
        else:
            prompt = f"""### Instruction:
{instruction}

### Response:
{output}"""

        return prompt

    def tokenize(self, example: Dict[str, Any]) -> Dict[str, torch.Tensor]:
        """Tokenize a single example."""
        text = self.format_instruction(example)

        result = self.tokenizer(
            text,
            truncation=True,
            max_length=self.max_length,
            padding="max_length",
            return_tensors=None,
        )

        result["labels"] = result["input_ids"].copy()
        return result


def load_quantized_model(config: ModelConfig):
    """Load model with 4-bit quantization."""
    logger.info(f"Loading model: {config.model_name}")

    compute_dtype = getattr(torch, config.bnb_4bit_compute_dtype)

    bnb_config = BitsAndBytesConfig(
        load_in_4bit=config.use_4bit,
        bnb_4bit_quant_type=config.bnb_4bit_quant_type,
        bnb_4bit_compute_dtype=compute_dtype,
        bnb_4bit_use_double_quant=config.use_nested_quant,
    )

    model = AutoModelForCausalLM.from_pretrained(
        config.model_name,
        quantization_config=bnb_config,
        device_map="auto",
        trust_remote_code=True,
    )

    model = prepare_model_for_kbit_training(model)
    logger.info("Model loaded with 4-bit quantization")

    return model


def setup_lora(model, config: LoRAConfig):
    """Configure and apply LoRA to the model."""
    logger.info("Setting up LoRA configuration")

    peft_config = LoraConfig(
        r=config.lora_r,
        lora_alpha=config.lora_alpha,
        lora_dropout=config.lora_dropout,
        bias=config.bias,
        task_type=TaskType.CAUSAL_LM,
        target_modules=config.target_modules,
    )

    model = get_peft_model(model, peft_config)
    model.print_trainable_parameters()

    return model


def load_training_data(data_path: str, tokenizer, max_length: int) -> Dataset:
    """Load and preprocess training data."""
    logger.info(f"Loading training data from: {data_path}")

    # Load dataset (supports JSONL format)
    if data_path.endswith('.jsonl'):
        dataset = load_dataset('json', data_files=data_path, split='train')
    else:
        dataset = load_dataset(data_path, split='train')

    processor = ManuscriptDataProcessor(tokenizer, max_length)

    # Tokenize dataset
    dataset = dataset.map(
        processor.tokenize,
        remove_columns=dataset.column_names,
        num_proc=4,
        desc="Tokenizing",
    )

    logger.info(f"Loaded {len(dataset)} training examples")
    return dataset


def train(
    model_config: ModelConfig,
    lora_config: LoRAConfig,
    train_config: TrainConfig,
    data_path: str,
    eval_data_path: Optional[str] = None,
):
    """Main training function."""
    logger.info("Starting LoRA fine-tuning for medical manuscript generation")

    # Load tokenizer
    tokenizer = AutoTokenizer.from_pretrained(
        model_config.model_name,
        trust_remote_code=True,
    )
    tokenizer.pad_token = tokenizer.eos_token
    tokenizer.padding_side = "right"

    # Load model with quantization
    model = load_quantized_model(model_config)

    # Apply LoRA
    model = setup_lora(model, lora_config)

    # Load data
    train_dataset = load_training_data(
        data_path, tokenizer, train_config.max_seq_length
    )

    eval_dataset = None
    if eval_data_path:
        eval_dataset = load_training_data(
            eval_data_path, tokenizer, train_config.max_seq_length
        )

    # Training arguments
    training_args = TrainingArguments(
        output_dir=train_config.output_dir,
        num_train_epochs=train_config.num_train_epochs,
        per_device_train_batch_size=train_config.per_device_train_batch_size,
        per_device_eval_batch_size=train_config.per_device_eval_batch_size,
        gradient_accumulation_steps=train_config.gradient_accumulation_steps,
        learning_rate=train_config.learning_rate,
        weight_decay=train_config.weight_decay,
        warmup_ratio=train_config.warmup_ratio,
        logging_steps=train_config.logging_steps,
        save_steps=train_config.save_steps,
        eval_steps=train_config.eval_steps if eval_dataset else None,
        evaluation_strategy="steps" if eval_dataset else "no",
        fp16=train_config.fp16,
        optim=train_config.optim,
        lr_scheduler_type=train_config.lr_scheduler_type,
        gradient_checkpointing=train_config.gradient_checkpointing,
        report_to="tensorboard",
        save_total_limit=3,
        load_best_model_at_end=True if eval_dataset else False,
    )

    # Data collator
    data_collator = DataCollatorForLanguageModeling(
        tokenizer=tokenizer,
        mlm=False,
    )

    # Initialize trainer
    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=train_dataset,
        eval_dataset=eval_dataset,
        data_collator=data_collator,
    )

    # Train
    logger.info("Starting training...")
    trainer.train()

    # Save final model
    final_output_dir = os.path.join(train_config.output_dir, "final")
    trainer.save_model(final_output_dir)
    tokenizer.save_pretrained(final_output_dir)

    logger.info(f"Training complete! Model saved to: {final_output_dir}")

    return trainer


def main():
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Train LoRA adapters for medical manuscript generation"
    )
    parser.add_argument(
        "--data", required=True, help="Path to training data (JSONL format)"
    )
    parser.add_argument(
        "--eval-data", help="Path to evaluation data (optional)"
    )
    parser.add_argument(
        "--output", default="./outputs/manuscript-lora",
        help="Output directory for checkpoints"
    )
    parser.add_argument(
        "--epochs", type=int, default=3, help="Number of training epochs"
    )
    parser.add_argument(
        "--batch-size", type=int, default=4, help="Training batch size"
    )
    parser.add_argument(
        "--learning-rate", type=float, default=2e-4, help="Learning rate"
    )
    parser.add_argument(
        "--lora-r", type=int, default=64, help="LoRA rank"
    )
    parser.add_argument(
        "--max-length", type=int, default=2048, help="Maximum sequence length"
    )

    args = parser.parse_args()

    # Configure
    model_config = ModelConfig()
    lora_config = LoRAConfig(lora_r=args.lora_r)
    train_config = TrainConfig(
        output_dir=args.output,
        num_train_epochs=args.epochs,
        per_device_train_batch_size=args.batch_size,
        learning_rate=args.learning_rate,
        max_seq_length=args.max_length,
    )

    # Train
    train(
        model_config=model_config,
        lora_config=lora_config,
        train_config=train_config,
        data_path=args.data,
        eval_data_path=args.eval_data,
    )


if __name__ == "__main__":
    main()
