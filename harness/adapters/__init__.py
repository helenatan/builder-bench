"""Model adapter registry + alias resolution.

A Builder-Bench `--model` value is a friendly *alias* (e.g. `opus-4.6`). The registry maps
it to a concrete model id and the adapter that drives it. This indirection lets the PRD's
intended lineup (Opus 4.6 / Haiku 4.5 / GPT-5.5 / Gemini 3.5 ...) be named stably even as
the concrete ids behind them change.

NOTE ON THIS MACHINE: the PRD targets `opus-4.6`, which does not exist in the current
environment. Anthropic aliases are mapped to the latest shipping ids available here
(Opus 4.8 / Sonnet 4.6 / Haiku 4.5). Pin these to the real PRD ids when running for record.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .base import ModelAdapter, SessionResult, StepResult  # re-export

# alias -> (provider, concrete_model_id)
ALIASES: dict[str, tuple[str, str]] = {
    # Anthropic flagship
    "opus-4.6": ("anthropic", "claude-opus-4-8"),  # PRD id unavailable here; mapped to current Opus
    "opus": ("anthropic", "claude-opus-4-8"),
    "opus-4.8": ("anthropic", "claude-opus-4-8"),
    "opus-5": ("anthropic", "claude-opus-5"),  # current-gen flagship
    # Anthropic mid
    "sonnet-4.6": ("anthropic", "claude-sonnet-4-6"),
    "sonnet": ("anthropic", "claude-sonnet-4-6"),
    "sonnet-5": ("anthropic", "claude-sonnet-5"),  # current-gen mid
    # Anthropic budget
    "haiku-4.5": ("anthropic", "claude-haiku-4-5-20251001"),
    "haiku": ("anthropic", "claude-haiku-4-5-20251001"),
    # Anthropic current-gen, no 4.x analog in the lineup
    "fable-5": ("anthropic", "claude-fable-5"),
}

_PROVIDERS = {"anthropic"}


def resolve_model(alias: str) -> tuple[str, str]:
    """Return (provider, model_id) for an alias, or pass an explicit id straight through."""
    if alias in ALIASES:
        return ALIASES[alias]
    if alias.startswith(("claude-", "us.anthropic.")):
        return "anthropic", alias
    raise ValueError(
        f"Unknown model alias '{alias}'. Known aliases: {sorted(ALIASES)}. "
        "In M0 only the 'anthropic' provider is implemented."
    )


def get_adapter(model: str, workdir: Path, **kwargs: Any) -> ModelAdapter:
    provider, model_id = resolve_model(model)
    if provider == "anthropic":
        from .anthropic import AnthropicAdapter

        return AnthropicAdapter(model=model, model_id=model_id, workdir=workdir, **kwargs)
    raise NotImplementedError(
        f"Provider '{provider}' has no adapter yet (M0 ships Anthropic only)."
    )


__all__ = [
    "ALIASES",
    "ModelAdapter",
    "SessionResult",
    "StepResult",
    "get_adapter",
    "resolve_model",
]
