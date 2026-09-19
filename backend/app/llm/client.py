"""Anthropic client wrapper: auth, retry, JSON coercion, and cost accounting."""

from __future__ import annotations

import asyncio
import json
import logging
import random
from dataclasses import dataclass, field
from typing import Any

import anthropic
from pydantic import BaseModel, ValidationError

from app.config import settings
from app.llm.auth import Credential, describe_credential, resolve_credential
from app.llm.json_salvage import salvage_truncated_json_object

logger = logging.getLogger(__name__)

# Indicative USD per million tokens, for the in-run cost meter only.
# Verify against current Anthropic pricing before relying on these figures.
_PRICING: dict[str, tuple[float, float]] = {
    "claude-opus-5": (15.0, 75.0),
    "claude-sonnet-5": (3.0, 15.0),
    "claude-haiku-4-5-20251001": (1.0, 5.0),
}


@dataclass
class UsageMeter:
    """Accumulates token usage and estimated cost across a run."""

    input_tokens: int = 0
    output_tokens: int = 0
    calls: int = 0
    by_model: dict[str, int] = field(default_factory=dict)

    def record(self, model: str, in_tok: int, out_tok: int) -> None:
        self.input_tokens += in_tok
        self.output_tokens += out_tok
        self.calls += 1
        self.by_model[model] = self.by_model.get(model, 0) + 1

    @property
    def estimated_cost_usd(self) -> float:
        # Approximate: attributes all tokens to whichever model made the calls,
        # weighted by call share. Good enough for a per-run meter.
        if not self.calls:
            return 0.0
        total = 0.0
        for model, n in self.by_model.items():
            share = n / self.calls
            in_rate, out_rate = _PRICING.get(model, (3.0, 15.0))
            total += (self.input_tokens * share / 1e6) * in_rate
            total += (self.output_tokens * share / 1e6) * out_rate
        return round(total, 4)

    def snapshot(self) -> dict[str, Any]:
        return {
            "calls": self.calls,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "estimated_cost_usd": self.estimated_cost_usd,
            "by_model": dict(self.by_model),
        }


class LLMError(RuntimeError):
    pass


class LLMClient:
    """Async Anthropic client with bounded concurrency and schema-checked JSON."""

    def __init__(self, credential: Credential | None = None) -> None:
        self.credential = credential or resolve_credential()
        self._client = anthropic.AsyncAnthropic(**self.credential.client_kwargs())
        self._semaphore = asyncio.Semaphore(settings.max_concurrency)
        self.usage = UsageMeter()
        logger.info("Anthropic auth: %s", describe_credential(self.credential))

    async def complete(
        self,
        *,
        system: str,
        user: str,
        model: str,
        max_tokens: int,
        temperature: float = 0.3,
        prefill: str | None = None,
    ) -> str:
        """One completion, with bounded concurrency and retry on transient errors."""
        messages: list[dict[str, Any]] = [{"role": "user", "content": user}]
        if prefill:
            messages.append({"role": "assistant", "content": prefill})

        last_exc: Exception | None = None
        for attempt in range(settings.max_retries):
            try:
                async with self._semaphore:
                    resp = await asyncio.wait_for(
                        self._client.messages.create(
                            model=model,
                            max_tokens=max_tokens,
                            temperature=temperature,
                            system=system,
                            messages=messages,
                        ),
                        timeout=settings.call_timeout_seconds,
                    )
                self.usage.record(model, resp.usage.input_tokens, resp.usage.output_tokens)
                text = "".join(b.text for b in resp.content if b.type == "text")
                return (prefill or "") + text

            except (anthropic.RateLimitError, anthropic.APIStatusError) as exc:
                status = getattr(exc, "status_code", None)
                if status is not None and 400 <= status < 500 and status != 429:
                    raise LLMError(f"{model}: non-retryable {status}: {exc}") from exc
                last_exc = exc
            except (TimeoutError, anthropic.APIConnectionError) as exc:
                last_exc = exc

            backoff = (2**attempt) + random.uniform(0, 0.5)
            logger.warning(
                "LLM call failed (attempt %d/%d), retrying in %.1fs: %s",
                attempt + 1,
                settings.max_retries,
                backoff,
                last_exc,
            )
            await asyncio.sleep(backoff)

        raise LLMError(f"{model}: exhausted {settings.max_retries} retries: {last_exc}")

    async def complete_json(
        self,
        *,
        system: str,
        user: str,
        model: str,
        max_tokens: int,
        schema: type[BaseModel],
        temperature: float = 0.3,
    ) -> BaseModel:
        """Completion coerced into a Pydantic model.

        Prefills ``{`` so the model starts emitting the object immediately, and
        salvages truncated output rather than losing the whole reaction.
        """
        raw = await self.complete(
            system=system,
            user=user,
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            prefill="{",
        )

        data = salvage_truncated_json_object(raw)
        if data is None:
            raise LLMError(f"{model}: no parseable JSON object in response")

        try:
            return schema.model_validate(data)
        except ValidationError as exc:
            raise LLMError(f"{model}: JSON did not match {schema.__name__}: {exc}") from exc

    async def aclose(self) -> None:
        await self._client.close()


def format_schema_for_prompt(schema: type[BaseModel]) -> str:
    """Render a JSON-schema hint compact enough to embed in a system prompt."""
    return json.dumps(schema.model_json_schema(), separators=(",", ":"))
