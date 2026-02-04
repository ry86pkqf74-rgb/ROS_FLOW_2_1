#!/usr/bin/env python3
"""
LoRA Fine-Tuning for ResearchFlow Models

Fine-tunes base models using LoRA (Low-Rank Adaptation) for research-specific tasks.
Supports Llama 3.1, Qwen 2.5, and Mistral base models.

Usage:
    python scripts/train_lora.py \
        --base-model meta-llama/Llama-3.1-8B \
        --dataset data/training/manuscript_refinement \
        --output models/research-refiner

Requirements:
    pip install transformers peft trl bitsandbytes accelerate datasets

Linear Issue: ROS-82
"""

import argparse
import json
import logging
import os
from pathlib import Path
from datetime import datetime

import torch
from datasets import load_from_disk
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    BitsAndBytesConfig,
    TrainingArguments,
)
from peft import (
    LoraConfig,
    get_peft_model,
    prepare_model_for_kbit_training,
    TaskType,
)
from trl import SFTTrainer

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)


# Default LoRA configuration optimized for research tasks
DEFAULT_LORA_CONFIG = {
    "r": 16,  # Rank
    "lora_alpha": 32,  # Alpha scaling
    "lora_dropout": 0.05,
    "target_modules": ["q_proj", "v_proj", "k_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
    "bias": "none",
    "task_type": TaskType.CAUSAL_LM,
}

# Training arguments optimized for research fine-tuning
DEFAULT_TRAINING_ARGS = {
    "num_train_epochs": 3,
    "per_device_train_batch_size": 4,
    "gradient_accumulation_steps": 4,
    "learning_rate": 2e-4,
    "weight_decay": 0.01,
    "warmup_ratio": 0.03,
    "lr_scheduler_type": "cosine",
    "logging_steps": 10,
    "save_steps": 100,
    "save_total_limit": 3,
    "bf16": True,  # Use bfloat16 if available
    "gradient_checkpointing": True,
    "optim": "paged_adamw_8bit",
}


def format_prompt(example: dict) -> str:
    """Format example into training prompt."""
    system = example.get("system", "You are a helpful research assistant.")
    instruction = example.get("instruction", "")
    input_text = example.get("input", "")
    output = example.get("output", "")
    
    # Llama 3.1 chat format
    prompt = f"""<|begin_of_text|><|start_header_id|>system<|end_header_id|>

{system}<|eot_id|><|start_header_id|>user<|end_header_id|>

{instruction}

{input_text}<|eot_id|><|start_header_id|>assistant<|end_header_id|>

{output}<|eot_id|>"""
    
    return prompt


def load_model_and_tokenizer(
    model_name: str,
    use_4bit: bool = True,
    use_8bit: bool = False,
):
    """Load base model with quantization."""
    logger.info(f"Loading model: {model_name}")
    
    # Quantization config
    if use_4bit:
        bnb_config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype=torch.bfloat16,
            bnb_4bit_use_double_quant=True,
        )
    elif use_8bit:
        bnb_config = BitsAndBytesConfig(load_in_8bit=True)
    else:
        bnb_config = None
    
    # Load tokenizer
    tokenizer = AutoTokenizer.from_pretrained(
        model_name,
        trust_remote_code=True,
    )
    
    # Set padding token if not set
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    
    # Load model
    model = AutoModelForCausalLM.from_pretrained(
        model_name,
        quantization_config=bnb_config,
        device_map="auto",
        trust_remote_code=True,
        torch_dtype=torch.bfloat16,
    )
    
    # Prepare for training
    if bnb_config:
        model = prepare_model_for_kbit_training(model)
    
    return model, tokenizer


def train_lora(
    base_model: str,
    dataset_path: Path,
    output_dir: Path,
    lora_config: dict = None,
    training_args: dict = None,
    max_seq_length: int = 2048,
):
    """
    Fine-tune a model using LoRA.
    
    Args:
        base_model: HuggingFace model ID or local path
        dataset_path: Path to prepared HuggingFace dataset
        output_dir: Directory to save fine-tuned model
        lora_config: LoRA configuration override
        training_args: Training arguments override
        max_seq_length: Maximum sequence length
    """
    # Merge configs
    lora_cfg = {**DEFAULT_LORA_CONFIG, **(lora_config or {})}
    train_cfg = {**DEFAULT_TRAINING_ARGS, **(training_args or {})}
    
    # Load model and tokenizer
    model, tokenizer = load_model_and_tokenizer(base_model)
    
    # Apply LoRA
    logger.info("Applying LoRA configuration")
    peft_config = LoraConfig(**lora_cfg)
    model = get_peft_model(model, peft_config)
    model.print_trainable_parameters()
    
    # Load dataset
    logger.info(f"Loading dataset from {dataset_path}")
    dataset = load_from_disk(str(dataset_path))
    
    # Format examples
    def formatting_func(examples):
        return [format_prompt(ex) for ex in [
            {k: examples[k][i] for k in examples.keys()}
            for i in range(len(examples["input"]))
        ]]
    
    # Setup training arguments
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    training_arguments = TrainingArguments(
        output_dir=str(output_dir),
        report_to="none",  # Disable wandb/tensorboard for now
        **train_cfg,
    )
    
    # Create trainer
    trainer = SFTTrainer(
        model=model,
        args=training_arguments,
        train_dataset=dataset,
        tokenizer=tokenizer,
        formatting_func=formatting_func,
        max_seq_length=max_seq_length,
        packing=False,
    )
    
    # Train
    logger.info("Starting training...")
    trainer.train()
    
    # Save final model
    logger.info(f"Saving model to {output_dir}")
    trainer.save_model(str(output_dir / "final"))
    tokenizer.save_pretrained(str(output_dir / "final"))
    
    # Save training metadata
    metadata = {
        "base_model": base_model,
        "dataset": str(dataset_path),
        "lora_config": lora_cfg,
        "training_args": train_cfg,
        "trained_at": datetime.utcnow().isoformat(),
        "trainable_params": model.get_nb_trainable_parameters(),
    }
    
    with open(output_dir / "training_metadata.json", "w") as f:
        json.dump(metadata, f, indent=2, default=str)
    
    logger.info("Training complete!")
    return output_dir / "final"


def main():
    parser = argparse.ArgumentParser(
        description="Fine-tune models with LoRA for ResearchFlow"
    )
    parser.add_argument(
        "--base-model", "-m",
        default="meta-llama/Llama-3.1-8B",
        help="Base model to fine-tune"
    )
    parser.add_argument(
        "--dataset", "-d",
        type=Path,
        required=True,
        help="Path to prepared training dataset"
    )
    parser.add_argument(
        "--output", "-o",
        type=Path,
        default=Path("models/research-refiner"),
        help="Output directory for fine-tuned model"
    )
    parser.add_argument(
        "--epochs",
        type=int,
        default=3,
        help="Number of training epochs"
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=4,
        help="Per-device batch size"
    )
    parser.add_argument(
        "--learning-rate",
        type=float,
        default=2e-4,
        help="Learning rate"
    )
    parser.add_argument(
        "--lora-r",
        type=int,
        default=16,
        help="LoRA rank"
    )
    parser.add_argument(
        "--lora-alpha",
        type=int,
        default=32,
        help="LoRA alpha"
    )
    parser.add_argument(
        "--max-seq-length",
        type=int,
        default=2048,
        help="Maximum sequence length"
    )
    parser.add_argument(
        "--no-4bit",
        action="store_true",
        help="Disable 4-bit quantization"
    )
    
    args = parser.parse_args()
    
    # Build configs from args
    lora_config = {
        "r": args.lora_r,
        "lora_alpha": args.lora_alpha,
    }
    
    training_args = {
        "num_train_epochs": args.epochs,
        "per_device_train_batch_size": args.batch_size,
        "learning_rate": args.learning_rate,
    }
    
    # Run training
    model_path = train_lora(
        base_model=args.base_model,
        dataset_path=args.dataset,
        output_dir=args.output,
        lora_config=lora_config,
        training_args=training_args,
        max_seq_length=args.max_seq_length,
    )
    
    print(f"\n✅ Model saved to: {model_path}")
    print(f"\nNext steps:")
    print(f"  1. Export to GGUF: python scripts/export_to_ollama.sh {model_path}")
    print(f"  2. Import to Ollama: ollama create research-refiner -f {model_path}/Modelfile")


if __name__ == "__main__":
    main()
