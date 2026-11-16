"""Session 3: fine-tune Phi-3-mini on the refund decisions with LoRA (4-bit QLoRA on a T4).

Same structure as the course component. Changes for P4: the prompt holds the policy and the
claim (about 450 tokens), so max_seq_length is 768 and the batch is smaller; no packing, so
one example = one claim.
"""
from kfp import dsl
from kfp.dsl import Dataset, Input, Metrics, Model, Output

BASE_IMAGE = "pytorch/pytorch:2.8.0-cuda12.9-cudnn9-devel"
# Course warning: peft 0.13.2 + transformers 4.46.* so the Vertex AI pre-built serving image can load the model
PACKAGES = [
    "transformers==4.46.3",
    "peft==0.13.2",
    "trl==0.12.2",
    "accelerate==1.1.1",
    "bitsandbytes>=0.47.0",
    "datasets==3.1.0",
    "pandas",
    "tensorboard",
]


def fine_tune(
    train_dataset: Input[Dataset],
    model: Output[Model],
    metrics: Output[Metrics],
    base_model_id: str = "microsoft/Phi-3-mini-4k-instruct",
    num_train_epochs: int = 2,
    learning_rate: float = 2e-4,
    lora_r: int = 16,
    lora_alpha: int = 32,
    max_seq_length: int = 768,
    validation_size: float = 0.1,
    seed: int = 42,
) -> None:
    """Train LoRA adapters; save adapters + tokenizer to model.path; log metrics to Kubeflow."""
    import json
    import logging
    import os

    import pandas as pd
    import torch
    from datasets import Dataset as HFDataset
    from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
    from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
    from trl import SFTConfig, SFTTrainer

    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger("fine_tuning")

    hyperparameters = {
        "base_model_id": base_model_id,
        "num_train_epochs": num_train_epochs,
        "learning_rate": learning_rate,
        "lora_r": lora_r,
        "lora_alpha": lora_alpha,
        "lora_dropout": 0.05,
        "per_device_train_batch_size": 4,
        "gradient_accumulation_steps": 4,
        "max_seq_length": max_seq_length,
        "validation_size": validation_size,
        "seed": seed,
    }
    logger.info(f"Hyper-parameters: {hyperparameters}")

    df = pd.read_csv(train_dataset.path)
    df["messages"] = df["messages"].apply(json.loads)
    dataset = HFDataset.from_pandas(df[["messages"]])
    splits = dataset.train_test_split(test_size=validation_size, seed=seed)
    logger.info(f"Train {len(splits['train'])} rows, validation {len(splits['test'])} rows")

    bnb_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_use_double_quant=True,
        bnb_4bit_compute_dtype=torch.float32,
    )
    base = AutoModelForCausalLM.from_pretrained(base_model_id, device_map="cuda:0", quantization_config=bnb_config)
    base = prepare_model_for_kbit_training(base)
    lora_config = LoraConfig(
        r=lora_r,
        lora_alpha=lora_alpha,
        lora_dropout=hyperparameters["lora_dropout"],
        bias="none",
        task_type="CAUSAL_LM",
        target_modules=["o_proj", "qkv_proj", "gate_up_proj", "down_proj"],
    )
    peft_model = get_peft_model(base, lora_config)
    trainable, total = peft_model.get_nb_trainable_parameters()
    logger.info(f"Trainable parameters: {trainable:,} / {total:,} ({100 * trainable / total:.2f} %)")

    tokenizer = AutoTokenizer.from_pretrained(base_model_id)
    tokenizer.pad_token = tokenizer.unk_token
    tokenizer.pad_token_id = tokenizer.unk_token_id

    os.makedirs(metrics.path, exist_ok=True)
    sft_config = SFTConfig(
        output_dir="/tmp/phi3-parcelcheck",
        num_train_epochs=num_train_epochs,
        learning_rate=learning_rate,
        per_device_train_batch_size=hyperparameters["per_device_train_batch_size"],
        gradient_accumulation_steps=hyperparameters["gradient_accumulation_steps"],
        auto_find_batch_size=True,
        gradient_checkpointing=True,
        gradient_checkpointing_kwargs={"use_reentrant": False},
        max_seq_length=max_seq_length,
        packing=False,
        optim="paged_adamw_8bit",
        logging_steps=10,
        eval_strategy="epoch",
        save_strategy="no",
        report_to=["tensorboard"],
        logging_dir=metrics.path,
        seed=seed,
    )
    trainer = SFTTrainer(
        model=peft_model,
        processing_class=tokenizer,
        args=sft_config,
        train_dataset=splits["train"],
        eval_dataset=splits["test"],
    )
    train_result = trainer.train()
    eval_result = trainer.evaluate()

    trainer.save_model(model.path)
    tokenizer.save_pretrained(model.path)
    model.metadata.update({k: str(v) for k, v in hyperparameters.items()})

    metrics.log_metric("train_loss", float(train_result.training_loss))
    metrics.log_metric("eval_loss", float(eval_result["eval_loss"]))
    metrics.log_metric("trainable_parameters", int(trainable))
    for name, value in hyperparameters.items():
        if isinstance(value, (int, float)):
            metrics.log_metric(f"hp_{name}", value)
    logger.info(f"Saved model to {model.path}; train_loss={train_result.training_loss:.4f}, "
                f"eval_loss={eval_result['eval_loss']:.4f}")


fine_tuning_component = dsl.component(
    func=fine_tune,
    base_image=BASE_IMAGE,
    packages_to_install=PACKAGES,
)
