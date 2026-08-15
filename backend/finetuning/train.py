"""LoRA / QLoRA fine-tuning for the College AI Assistant.

Trains a small instruction-following model (Llama / Qwen / Mistral family)
on train.jsonl with validation.jsonl. Every hyperparameter is configurable
via CLI flags or environment variables (see .env.example / README).

Example (QLoRA 4-bit, Qwen2.5-1.5B):
    python finetuning/train.py \
        --model Qwen/Qwen2.5-1.5B-Instruct \
        --quant 4bit \
        --epochs 3 \
        --batch-size 1 --grad-accum 8 --lr 2e-4 --max-len 1024

Example (LoRA, no quantization, Office-of-memory-safe):
    python finetuning/train.py --model Qwen/Qwen2.5-0.5B-Instruct --no-quant

Adapters are saved to --output-dir; use --merge to also export a merged
model that can be converted to GGUF and imported into Ollama.
"""
import argparse
import json
import logging
import os
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("finetune")

FINETUNING_DIR = Path(__file__).resolve().parent
DEFAULT_TRAIN = FINETUNING_DIR / "train.jsonl"
DEFAULT_VALIDATION = FINETUNING_DIR / "validation.jsonl"

INSTRUCTION_TEMPLATE = (
    "You are a College AI Assistant. Answer using the supplied college "
    "knowledge context and never invent facts.\n\n"
    "### Instruction\n{instruction}\n"
    "{input}"
    "### Response\n{output}"
)

UNANSWERED_MARKER = "I could not find that information in the college knowledge base."


def env_default(name: str, default: str) -> str:
    return os.getenv(name, default)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="LoRA/QLoRA fine-tuning for College AI")
    parser.add_argument("--model", default=env_default("FINETUNE_MODEL", "Qwen/Qwen2.5-1.5B-Instruct"),
                        help="base model id (Llama/Qwen/Mistral family)")
    parser.add_argument("--train-file", default=str(DEFAULT_TRAIN))
    parser.add_argument("--validation-file", default=str(DEFAULT_VALIDATION))
    parser.add_argument("--output-dir", default=env_default("FINETUNE_OUTPUT_DIR", "finetuning/checkpoints"), help="adapter checkpoint dir")
    parser.add_argument("--batch-size", type=int, default=int(env_default("FINETUNE_BATCH_SIZE", "1")))
    parser.add_argument("--grad-accum", type=int, default=int(env_default("FINETUNE_GRAD_ACCUM", "8")))
    parser.add_argument("--lr", type=float, default=float(env_default("FINETUNE_LR", "2e-4")))
    parser.add_argument("--epochs", type=int, default=int(env_default("FINETUNE_EPOCHS", "3")))
    parser.add_argument("--max-len", type=int, default=int(env_default("FINETUNE_MAX_SEQ_LEN", "1024")))
    parser.add_argument("--lora-r", type=int, default=int(env_default("FINETUNE_LORA_R", "16")))
    parser.add_argument("--lora-alpha", type=int, default=int(env_default("FINETUNE_LORA_ALPHA", "32")))
    parser.add_argument("--lora-dropout", type=float, default=float(env_default("FINETUNE_LORA_DROPOUT", "0.05")))
    parser.add_argument("--target-modules", default=env_default("FINETUNE_TARGET_MODULES", ""),
                        help="comma-separated module names for LoRA (auto-detected when empty)")
    parser.add_argument("--quant", choices=("none", "4bit", "8bit"), default=env_default("FINETUNE_QUANT", "4bit"))
    parser.add_argument("--no-quant", action="store_true", help="shorthand for --quant none")
    parser.add_argument("--save-steps", type=int, default=int(env_default("FINETUNE_SAVE_STEPS", "250")))
    parser.add_argument("--eval-steps", type=int, default=int(env_default("FINETUNE_EVAL_STEPS", "250")))
    parser.add_argument("--num-ctx-chunks", type=int, default=int(env_default("FINETUNE_CTX_CHUNKS", "1")),
                        help="concatenate this many instructions per training chunk (for long-context)")
    parser.add_argument("--merge", action="store_true", help="export a merged full model after training")
    parser.add_argument("--seed", type=int, default=int(os.getenv("FINETUNE_SEED", "42")))
    parser.add_argument("--device", default=os.getenv("FINETUNE_DEVICE", "auto"))
    args = parser.parse_args()
    if args.no_quant:
        args.quant = "none"
    return args


def load_jsonl(path: str) -> list[dict]:
    rows = []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def build_text(row: dict) -> str:
    instruction = row.get("instruction", "")
    inp = row.get("input") or ""
    output = row.get("output") or UNANSWERED_MARKER
    if inp:
        inp = f"### Input\n{inp}\n"
    return INSTRUCTION_TEMPLATE.format(instruction=instruction, input=inp, output=output)


def main() -> None:
    args = parse_args()

    try:
        import torch  # noqa: F401
        import transformers
        import peft
    except ImportError as exc:  # pragma: no cover
        logger.error(
            "Training stack missing (%s). Install with: pip install torch transformers peft "
            "bitsandbytes accelerate datasets", exc
        )
        raise SystemExit(1) from exc

    logger.info("Loading datasets: train=%s validation=%s", args.train_file, args.validation_file)
    train_rows = load_jsonl(args.train_file)
    validation_rows = load_jsonl(args.validation_file)
    logger.info("train=%d validation=%d", len(train_rows), len(validation_rows))

    from datasets import Dataset

    train_ds = Dataset.from_list([{"text": build_text(r)} for r in train_rows])
    eval_ds = Dataset.from_list([{"text": build_text(r)} for r in validation_rows])

    tokenizer = transformers.AutoTokenizer.from_pretrained(args.model, trust_remote_code=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    def tokenize(examples):
        return tokenizer(examples["text"], truncation=True, max_length=args.max_len, padding=False)

    train_ds = train_ds.map(tokenize, batched=True, remove_columns=["text"])
    eval_ds = eval_ds.map(tokenize, batched=True, remove_columns=["text"])

    quant_config = None
    if args.quant == "4bit":
        try:
            from transformers import BitsAndBytesConfig
        except ImportError as exc:  # pragma: no cover
            raise SystemExit("bitsandbytes not installed; use --no-quant") from exc
        quant_config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_use_double_quant=True,
            bnb_4bit_compute_dtype=torch.float16,
        )
    elif args.quant == "8bit":
        from transformers import BitsAndBytesConfig

        quant_config = BitsAndBytesConfig(load_in_8bit=True)

    logger.info("Loading base model: %s (quant=%s)", args.model, args.quant)
    model = transformers.AutoModelForCausalLM.from_pretrained(
        args.model,
        trust_remote_code=True,
        quantization_config=quant_config,
        device_map=None if not torch.cuda.is_available() else ("auto" if args.device == "auto" else args.device),
        low_cpu_mem_usage=False,
    )
    model.config.use_cache = False

    from peft import LoraConfig, TaskType, get_peft_model, prepare_model_for_kbit_training

    if args.quant in ("4bit", "8bit"):
        model = prepare_model_for_kbit_training(model)

    target_modules = (
        [m.strip() for m in args.target_modules.split(",") if m.strip()]
        if args.target_modules
        else None
    )
    lora_config = LoraConfig(
        task_type=TaskType.CAUSAL_LM,
        r=args.lora_r,
        lora_alpha=args.lora_alpha,
        lora_dropout=args.lora_dropout,
        target_modules=target_modules,
        bias="none",
    )
    model = get_peft_model(model, lora_config)
    if target_modules:
        model.print_trainable_parameters()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    steps_per_epoch = max(1, len(train_ds) // (args.batch_size * args.grad_accum))
    total_steps = steps_per_epoch * args.epochs
    warmup_steps = max(1, int(0.05 * total_steps))

    training_args = transformers.TrainingArguments(
        output_dir=str(output_dir),
        num_train_epochs=args.epochs,
        per_device_train_batch_size=args.batch_size,
        per_device_eval_batch_size=max(1, args.batch_size),
        gradient_accumulation_steps=args.grad_accum,
        learning_rate=args.lr,
        warmup_steps=warmup_steps,
        lr_scheduler_type="cosine",
        fp16=torch.cuda.is_available() and args.quant != "8bit",
        bf16=False,
        logging_steps=10,
        log_level="info",
        eval_strategy="steps" if len(eval_ds) else "no",
        eval_steps=args.eval_steps,
        save_strategy="steps",
        save_steps=args.save_steps,
        save_total_limit=2,
        load_best_model_at_end=bool(len(eval_ds)),
        metric_for_best_model="eval_loss",
        report_to=[],
        seed=args.seed,
        remove_unused_columns=False,
        dataloader_pin_memory=False,
    )

    trainer = transformers.Trainer(
        model=model,
        args=training_args,
        train_dataset=train_ds,
        eval_dataset=eval_ds if len(eval_ds) else None,
        processing_class=tokenizer,
        data_collator=transformers.DataCollatorForLanguageModeling(
            tokenizer=tokenizer, mlm=False, pad_to_multiple_of=8
        ),
    )

    logger.info("Starting training: epochs=%d batch=%d grad_accum=%d lr=%s max_len=%d",
                args.epochs, args.batch_size, args.grad_accum, args.lr, args.max_len)
    trainer.train()
    trainer.save_model(str(output_dir))
    tokenizer.save_pretrained(str(output_dir))
    logger.info("Adapter saved to %s", output_dir)

    if args.merge:
        logger.info("Exporting merged full-precision model to %s/merged", output_dir)
        from peft import PeftModel

        merged = PeftModel.from_pretrained(model, str(output_dir))
        merged = merged.merge_and_unload()
        merged.save_pretrained(str(output_dir / "merged"))
        tokenizer.save_pretrained(str(output_dir / "merged"))
        logger.info("Merged model saved; convert to GGUF and `ollama create` to serve it.")


if __name__ == "__main__":
    main()