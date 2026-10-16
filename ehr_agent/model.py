"""Adapter around a local Hugging Face causal language model."""

from __future__ import annotations

import json
import os
from typing import Any


class LocalHFModel:
    """Generate JSON-controlled decisions with a local Transformers model."""

    def __init__(self, model_id: str, max_new_tokens: int = 800):
        from transformers import AutoModelForCausalLM, AutoTokenizer

        token = os.environ.get("HF_TOKEN") or None
        self.processor = None
        if "gemma-4" in model_id.lower():
            from transformers import AutoModelForMultimodalLM, AutoProcessor

            self.processor = AutoProcessor.from_pretrained(model_id, token=token)
            self.tokenizer = self.processor.tokenizer
            self.model = AutoModelForMultimodalLM.from_pretrained(
                model_id, device_map="auto", torch_dtype="auto", token=token
            )
        else:
            self.tokenizer = AutoTokenizer.from_pretrained(model_id, token=token)
            self.model = AutoModelForCausalLM.from_pretrained(
                model_id, device_map="auto", torch_dtype="auto", token=token
            )
        self.max_new_tokens = max_new_tokens

    def generate(self, messages: list[dict[str, str]]) -> str:
        prompt = self.tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        encoder = self.processor or self.tokenizer
        inputs = encoder(text=prompt, return_tensors="pt").to(self.model.device)
        output = self.model.generate(
            **inputs,
            max_new_tokens=self.max_new_tokens,
            do_sample=False,
            pad_token_id=self.tokenizer.eos_token_id,
        )
        generated = output[0][inputs["input_ids"].shape[-1] :]
        decoder = self.processor.batch_decode if self.processor else self.tokenizer.batch_decode
        return decoder(generated, skip_special_tokens=True)[0].strip()

    def generate_json(self, messages: list[dict[str, str]]) -> dict[str, Any]:
        text = self.generate(messages).strip()
        if text.startswith("```"):
            text = text.removeprefix("```").removeprefix("json").removesuffix("```").strip()
        try:
            return json.loads(text)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Local model returned invalid JSON: {text[:500]}") from exc
