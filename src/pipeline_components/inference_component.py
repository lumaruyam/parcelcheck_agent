"""Session 3: the fine-tuned model writes a decision for every held-out test claim (greedy decoding)."""

from kfp import dsl
from kfp.dsl import Dataset, Input, Model, Output

BASE_IMAGE = "pytorch/pytorch:2.8.0-cuda12.9-cudnn9-devel"
PACKAGES = [
    "transformers==4.46.3",
    "peft==0.13.2",
    "accelerate==1.1.1",
    "pandas",
]


def run_inference(
    model: Input[Model],
    test_dataset: Input[Dataset],
    predictions: Output[Dataset],
    max_new_tokens: int = 256,
    max_samples: int = 0,
) -> None:
    """Write predictions.path as CSV: user_input, reference, extracted_response."""
    import json
    import logging
    import re
    from typing import Any

    import pandas as pd
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer

    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger("inference")

    def build_prompt(tokenizer: AutoTokenizer, sentence: str) -> str:
        """'<|user|>\\n{sentence}<|end|>\\n<|assistant|>\\n' via the tokenizer's chat template."""
        return tokenizer.apply_chat_template(
            [{"role": "user", "content": sentence}], tokenize=False, add_generation_prompt=True
        )

    def generate_response(model: Any, tokenizer: Any, prompt: str, **kwargs: Any) -> str:
        """Generate and decode, keeping special tokens so the response can be extracted."""
        inputs = tokenizer(prompt, add_special_tokens=False, return_tensors="pt").to(model.device)
        inputs.pop("token_type_ids", None)  # some tokenizers add it, generate() refuses it
        with torch.no_grad():
            output = model.generate(**inputs, eos_token_id=tokenizer.eos_token_id, **kwargs)
        return tokenizer.batch_decode(output, skip_special_tokens=False)[0]

    def extract_response(model_output: str) -> str:
        """Keep only what comes after <|assistant|> and before <|end|> / <|endoftext|>."""
        match = re.search(r"<\|assistant\|>(.*?)(?:<\|end\|>|<\|endoftext\|>|$)", model_output, re.DOTALL)
        return match.group(1).strip() if match else model_output.strip()

    # The model artifact is a directory with the LoRA adapters + tokenizer; with peft installed,
    # from_pretrained loads the base model and applies the adapters.
    logger.info(f"Loading model from {model.path}")
    tokenizer = AutoTokenizer.from_pretrained(model.path)
    llm = AutoModelForCausalLM.from_pretrained(model.path, torch_dtype=torch.float16, device_map="cuda:0")
    llm.eval()

    df = pd.read_csv(test_dataset.path)
    if max_samples > 0:
        df = df.head(max_samples)
    logger.info(f"Predicting {len(df)} test rows")

    rows = []
    for i, raw in enumerate(df["messages"]):
        messages = json.loads(raw)
        user_input = next(m["content"] for m in messages if m["role"] == "user")
        reference = next(m["content"] for m in messages if m["role"] == "assistant")
        output = generate_response(llm, tokenizer, build_prompt(tokenizer, user_input),
                                   max_new_tokens=max_new_tokens, do_sample=False)
        rows.append({"user_input": user_input, "reference": reference, "extracted_response": extract_response(output)})
        if i < 3:
            logger.info(f"reference={reference!r} -> {rows[-1]['extracted_response']!r}")

    pd.DataFrame(rows).to_csv(predictions.path, index=False)
    logger.info(f"Wrote {len(rows)} predictions to {predictions.path}")


inference_component = dsl.component(
    func=run_inference,
    base_image=BASE_IMAGE,
    packages_to_install=PACKAGES,
)
