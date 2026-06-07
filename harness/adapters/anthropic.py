"""Anthropic adapter — drives a headless Claude Agent SDK session.

This is the *neutral harness* implementation for Anthropic models. It runs a single
continuous `ClaudeSDKClient` session and feeds it the task's prompt steps one at a time,
accumulating the full trajectory (text + tool calls) and cost/usage accounting.

Other labs (OpenAI, Google) get their own adapter behind the same `ModelAdapter` contract
in later milestones; M0 ships Anthropic only.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .base import ModelAdapter, SessionResult, StepResult


def _safe(value: Any) -> Any:
    """Best-effort JSON-serializable coercion for logging arbitrary SDK objects."""
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, dict):
        return {str(k): _safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_safe(v) for v in value]
    for attr in ("model_dump", "to_dict", "_asdict"):
        fn = getattr(value, attr, None)
        if callable(fn):
            try:
                return _safe(fn())
            except Exception:  # noqa: BLE001
                pass
    if hasattr(value, "__dict__") and vars(value):
        return {str(k): _safe(v) for k, v in vars(value).items()}
    return repr(value)[:4000]


def _message_to_dict(msg: Any) -> dict[str, Any]:
    """Normalize an SDK message (any version) into a loggable dict."""
    out: dict[str, Any] = {"type": type(msg).__name__}
    content = getattr(msg, "content", None)
    if content is not None:
        blocks: list[dict[str, Any]] = []
        if isinstance(content, str):
            blocks.append({"block": "text", "text": content})
        else:
            for b in content:
                bt = type(b).__name__
                if hasattr(b, "text"):
                    blocks.append({"block": "text", "text": getattr(b, "text")})
                elif hasattr(b, "name") and hasattr(b, "input"):
                    blocks.append(
                        {
                            "block": "tool_use",
                            "name": getattr(b, "name", None),
                            "input": _safe(getattr(b, "input", None)),
                            "id": getattr(b, "id", None),
                        }
                    )
                elif hasattr(b, "tool_use_id"):
                    blocks.append(
                        {
                            "block": "tool_result",
                            "tool_use_id": getattr(b, "tool_use_id", None),
                            "content": _safe(getattr(b, "content", None)),
                            "is_error": getattr(b, "is_error", None),
                        }
                    )
                else:
                    blocks.append({"block": bt, "data": _safe(b)})
        out["content"] = blocks
    for attr in ("subtype", "total_cost_usd", "num_turns", "session_id", "is_error", "duration_ms"):
        v = getattr(msg, attr, None)
        if v is not None:
            out[attr] = _safe(v)
    usage = getattr(msg, "usage", None)
    if usage is not None:
        out["usage"] = _safe(usage)
    return out


def _usage_tokens(usage: Any) -> tuple[int, int]:
    """Extract (input_tokens, output_tokens) from a usage object/dict, tolerant of shape."""
    if usage is None:
        return 0, 0
    d = usage if isinstance(usage, dict) else _safe(usage)
    if not isinstance(d, dict):
        return 0, 0
    inp = int(d.get("input_tokens", 0) or 0)
    out = int(d.get("output_tokens", 0) or 0)
    return inp, out


class AnthropicAdapter(ModelAdapter):
    name = "anthropic"

    async def run_session(self, prompts: list[str]) -> SessionResult:
        # Imported lazily so the rest of the harness (scaffold, --help) works without the SDK.
        try:
            from claude_agent_sdk import ClaudeAgentOptions, ClaudeSDKClient
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError(
                "claude-agent-sdk is not installed. Run: pip install claude-agent-sdk"
            ) from exc

        result = SessionResult(model=self.model, model_id=self.model_id)

        options_kwargs: dict[str, Any] = dict(
            model=self.model_id,
            cwd=str(self.workdir),
            allowed_tools=self.allowed_tools,
            permission_mode="bypassPermissions",
            max_turns=self.max_turns,
            # Neutral harness: do NOT inherit the host machine's user/project/local
            # settings, so every model sees the same blank scaffolding.
            setting_sources=[],
        )
        if self.system_prompt:
            options_kwargs["system_prompt"] = self.system_prompt

        # Drop kwargs an older SDK build might not accept, rather than hard-failing.
        try:
            options = ClaudeAgentOptions(**options_kwargs)
        except TypeError:
            for k in ("setting_sources", "max_turns"):
                options_kwargs.pop(k, None)
            options = ClaudeAgentOptions(**options_kwargs)

        prev_total_cost = 0.0
        try:
            async with ClaudeSDKClient(options=options) as client:
                for i, prompt in enumerate(prompts, start=1):
                    step = StepResult(index=i, prompt=prompt)
                    texts: list[str] = []
                    await client.query(prompt)
                    async for msg in client.receive_response():
                        step.messages.append(_message_to_dict(msg))
                        if type(msg).__name__ == "AssistantMessage":
                            for b in getattr(msg, "content", []) or []:
                                if hasattr(b, "text"):
                                    texts.append(getattr(b, "text"))
                        if type(msg).__name__ == "ResultMessage":
                            total = getattr(msg, "total_cost_usd", None)
                            if total is not None:
                                step.cost_usd = max(0.0, float(total) - prev_total_cost)
                                prev_total_cost = float(total)
                                result.cost_usd = float(total)
                            result.num_turns = getattr(msg, "num_turns", result.num_turns)
                            result.session_id = getattr(msg, "session_id", result.session_id)
                            inp, out = _usage_tokens(getattr(msg, "usage", None))
                            result.input_tokens += inp
                            result.output_tokens += out
                            if getattr(msg, "is_error", False):
                                result.error = f"step {i}: {getattr(msg, 'subtype', 'error')}"
                    step.final_text = "\n".join(t for t in texts if t).strip()
                    result.steps.append(step)
                    if self.budget_usd is not None and result.cost_usd >= self.budget_usd:
                        result.error = (
                            f"budget cap ${self.budget_usd} reached after step {i}"
                            f" (spent ${result.cost_usd:.4f})"
                        )
                        break
        except Exception as exc:  # noqa: BLE001 — surface, don't crash the whole run
            result.error = f"{type(exc).__name__}: {exc}"

        return result
