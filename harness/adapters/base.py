"""Adapter contract shared by every model backend.

The whole point of Builder-Bench's harness is *neutrality*: every model runs through the
same scaffolding (the Claude Agent SDK in headless mode) so result differences reflect the
model, not the harness. An adapter's only job is to map our model alias to a concrete model
id and drive one multi-step session, returning a uniform `SessionResult`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class StepResult:
    """One prompt -> response turn within a single continuous session."""

    index: int
    prompt: str
    final_text: str = ""
    messages: list[dict[str, Any]] = field(default_factory=list)
    cost_usd: float = 0.0


@dataclass
class SessionResult:
    """The full trajectory + accounting for one attempt at a task."""

    model: str           # our alias, e.g. "opus-4.6"
    model_id: str        # the concrete id actually sent, e.g. "claude-opus-4-8"
    steps: list[StepResult] = field(default_factory=list)
    cost_usd: float = 0.0
    input_tokens: int = 0
    output_tokens: int = 0
    num_turns: int = 0
    session_id: str | None = None
    error: str | None = None

    @property
    def final_text(self) -> str:
        return self.steps[-1].final_text if self.steps else ""

    def transcript_steps(self) -> list[dict[str, Any]]:
        """Compact, grader-facing view of the trajectory."""
        return [
            {"step": s.index, "prompt": s.prompt, "final_text": s.final_text}
            for s in self.steps
        ]

    def to_dict(self) -> dict[str, Any]:
        return {
            "model": self.model,
            "model_id": self.model_id,
            "cost_usd": round(self.cost_usd, 6),
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "num_turns": self.num_turns,
            "session_id": self.session_id,
            "error": self.error,
            "steps": [
                {
                    "step": s.index,
                    "prompt": s.prompt,
                    "final_text": s.final_text,
                    "cost_usd": round(s.cost_usd, 6),
                    "messages": s.messages,
                }
                for s in self.steps
            ],
        }


class ModelAdapter:
    """Base class. Subclasses implement `run_session`."""

    name = "base"

    def __init__(
        self,
        model: str,
        model_id: str,
        workdir: Path,
        *,
        budget_usd: float | None = None,
        allowed_tools: list[str] | None = None,
        max_turns: int = 40,
        system_prompt: str | None = None,
    ) -> None:
        self.model = model
        self.model_id = model_id
        self.workdir = Path(workdir)
        self.budget_usd = budget_usd
        self.allowed_tools = allowed_tools or ["Read", "Write", "Edit", "Bash", "Glob", "Grep"]
        self.max_turns = max_turns
        self.system_prompt = system_prompt

    async def run_session(self, prompts: list[str]) -> SessionResult:
        raise NotImplementedError
