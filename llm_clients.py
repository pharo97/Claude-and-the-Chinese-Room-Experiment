"""Unified LLM client wrapper for OpenAI and Anthropic.

Called by: experiments/run_experiment.py and individual experiment modules.
"""
from __future__ import annotations
import os
import time
from dataclasses import dataclass
from typing import Optional
from dotenv import load_dotenv

load_dotenv(override=True)


@dataclass
class LLMResponse:
    provider: str
    model: str
    text: str
    latency_s: float
    error: Optional[str] = None


class LLMClient:
    def __init__(self):
        self.openai_key = os.getenv("OPENAI_API_KEY")
        self.anthropic_key = os.getenv("ANTHROPIC_API_KEY")
        self.openai_model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        self.anthropic_model = os.getenv("ANTHROPIC_MODEL", "claude-haiku-4-5-20251001")
        self._openai = None
        self._anthropic = None

    def _openai_client(self):
        if self._openai is None:
            from openai import OpenAI
            self._openai = OpenAI(api_key=self.openai_key)
        return self._openai

    def _anthropic_client(self):
        if self._anthropic is None:
            from anthropic import Anthropic
            self._anthropic = Anthropic(api_key=self.anthropic_key)
        return self._anthropic

    def query_openai(self, prompt: str, system: str = "", max_tokens: int = 400) -> LLMResponse:
        t0 = time.time()
        try:
            msgs = []
            if system:
                msgs.append({"role": "system", "content": system})
            msgs.append({"role": "user", "content": prompt})
            resp = self._openai_client().chat.completions.create(
                model=self.openai_model, messages=msgs,
                max_tokens=max_tokens, temperature=0.0,
            )
            return LLMResponse("openai", self.openai_model,
                               (resp.choices[0].message.content or "").strip(),
                               time.time() - t0)
        except Exception as e:
            return LLMResponse("openai", self.openai_model, "", time.time() - t0, str(e))

    def query_anthropic(self, prompt: str, system: str = "", max_tokens: int = 400) -> LLMResponse:
        t0 = time.time()
        try:
            resp = self._anthropic_client().messages.create(
                model=self.anthropic_model, max_tokens=max_tokens,
                system=system or "You are a helpful assistant.",
                messages=[{"role": "user", "content": prompt}], temperature=0.0,
            )
            text = "".join(b.text for b in resp.content if hasattr(b, "text"))
            return LLMResponse("anthropic", self.anthropic_model, text.strip(), time.time() - t0)
        except Exception as e:
            return LLMResponse("anthropic", self.anthropic_model, "", time.time() - t0, str(e))

    def query_all(self, prompt: str, system: str = "") -> list[LLMResponse]:
        out = []
        if self.openai_key:
            out.append(self.query_openai(prompt, system))
        if self.anthropic_key:
            out.append(self.query_anthropic(prompt, system))
        return out
