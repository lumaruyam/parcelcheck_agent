"""Custom handler for the Hugging Face pre-built inference container on Vertex AI.

The container copies the model artifacts from GCS to MODEL_DIR, imports this file
(it must be called handler.py, at the root of the artifacts folder) and calls
EndpointHandler(model_dir)(request_body) for every prediction request.

This file must stay standalone: inside the container there is no src/ package,
only this file next to the model weights.
"""

import re
from typing import Any

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

MODEL_DIR = "/opt/huggingface/model"  # where the container puts the GCS artifacts
BASE_MODEL_ID = "microsoft/Phi-3-mini-4k-instruct"
DEFAULT_PARAMETERS: dict[str, Any] = {"max_new_tokens": 256, "do_sample": False}  # a decision is short JSON; greedy = reproducible


def pick_device() -> tuple[str, torch.dtype]:
    """GPU on Vertex AI (T4 -> float16); CPU locally (float32, slow but safe)."""
    if torch.cuda.is_available():
        return "cuda:0", torch.float16
    return "cpu", torch.float32


def extract_response(generated_text: str) -> str:
    """Keep only what comes after <|assistant|> and before <|end|> / <|endoftext|>."""
    match = re.search(
        r"<\|assistant\|>(.*?)(?:<\|end\|>|<\|endoftext\|>|$)", generated_text, re.DOTALL
    )
    return match.group(1).strip() if match else generated_text.strip()


class EndpointHandler:
    """Handler for processing inference requests using a Hugging Face model."""

    def __init__(self, model_dir: str = MODEL_DIR) -> None:
        """Load tokenizer and model from the specified directory."""
        try:
            self.tokenizer = AutoTokenizer.from_pretrained(model_dir)
        except (OSError, ValueError):
            # the artifacts only contain the LoRA adapters -> use the base model's tokenizer
            self.tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL_ID)

        device_map, dtype = pick_device()
        # model_dir holds the LoRA adapters (adapter_config.json): with peft installed,
        # from_pretrained downloads the base Phi-3 and applies the adapters on top.
        self.model = AutoModelForCausalLM.from_pretrained(
            model_dir, torch_dtype=dtype, device_map=device_map
        ).eval()

    def build_prompt(self, instance: dict[str, Any] | str) -> str:
        """Accept either a ready prompt {"input": ...} or a raw {"message": ...}."""
        if isinstance(instance, str):
            instance = {"message": instance}
        if "input" in instance:  # chat template already applied by the client
            return instance["input"]
        return self.tokenizer.apply_chat_template(
            [{"role": "user", "content": instance["message"]}],
            tokenize=False,
            add_generation_prompt=True,
        )

    def __call__(self, data: dict[str, Any]) -> dict[str, list[Any]]:
        """Vertex AI format: {"instances": [...], "parameters": {...}} -> {"predictions": [...]}."""
        parameters = {**DEFAULT_PARAMETERS, **(data.get("parameters") or {})}
        predictions = []
        for instance in data.get("instances", []):
            prompt = self.build_prompt(instance)
            inputs = self.tokenizer(prompt, add_special_tokens=False, return_tensors="pt").to(
                self.model.device
            )
            inputs.pop("token_type_ids", None)
            with torch.no_grad():
                output = self.model.generate(
                    **inputs,
                    eos_token_id=self.tokenizer.eos_token_id,
                    pad_token_id=self.tokenizer.pad_token_id or self.tokenizer.eos_token_id,
                    **parameters,
                )
            generated_text = self.tokenizer.batch_decode(output, skip_special_tokens=False)[0]
            predictions.append(
                {"response": extract_response(generated_text), "generated_text": generated_text}
            )
        return {"predictions": predictions}
