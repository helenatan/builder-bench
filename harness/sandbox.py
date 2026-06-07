"""Sandboxing: build a task's fixed starting state in an isolated working directory.

The PRD mandates a Docker container per task. This module ships two backends behind one
interface so the harness runs end-to-end whether or not Docker is present:

  - DockerSandbox  — the spec-compliant path. Builds the fixed starting state by running
                     the task's `setup.sh` *inside* a pinned container image with the work
                     directory bind-mounted, so state construction is isolated and
                     reproducible. Selected automatically when Docker is available.
  - LocalSandbox   — a fallback that builds the same state in a throwaway temp directory on
                     the host. NOT a security boundary; use only for local development when
                     Docker is unavailable. Prints a loud warning.

Both expose the same surface: `.workdir` (where the agent works, cwd of the session) and
`setup()` / `teardown()`. The agent itself (driven by the Agent SDK on the host) operates
against `.workdir`. Running the agent's *tool calls* inside the container — full process
isolation, not just isolated state construction — is the production hardening tracked for
v1.x; M0 isolates state construction and confines the agent to a clean per-run workdir.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

# Pinned for reproducibility (PRD §9). Bump deliberately, not incidentally.
DEFAULT_IMAGE = "python:3.12-slim"


def docker_available() -> bool:
    if not shutil.which("docker"):
        return False
    try:
        return (
            subprocess.run(
                ["docker", "info"],
                capture_output=True,
                timeout=15,
            ).returncode
            == 0
        )
    except Exception:  # noqa: BLE001
        return False


class Sandbox:
    """Base: provisions `workdir` from a task's fixtures + setup.sh."""

    kind = "base"

    def __init__(self, task_dir: Path, run_dir: Path, *, image: str = DEFAULT_IMAGE) -> None:
        self.task_dir = Path(task_dir)
        self.run_dir = Path(run_dir)
        self.image = image
        self.workdir = self.run_dir / "workdir"

    # -- shared helpers -------------------------------------------------------
    def _provision_files(self) -> None:
        """Copy fixtures + setup.sh into a fresh workdir (the fixed starting state seed)."""
        if self.workdir.exists():
            shutil.rmtree(self.workdir)
        self.workdir.mkdir(parents=True)
        fixtures = self.task_dir / "fixtures"
        if fixtures.is_dir():
            shutil.copytree(fixtures, self.workdir / "fixtures")
        setup = self.task_dir / "setup.sh"
        if setup.is_file():
            shutil.copy2(setup, self.workdir / "setup.sh")

    def setup(self) -> Path:
        raise NotImplementedError

    def teardown(self) -> None:
        # Keep workdir by default — it holds the agent's artifacts for grading + audit.
        return None


class LocalSandbox(Sandbox):
    kind = "local"

    def setup(self) -> Path:
        print(
            "  [sandbox] WARNING: running LocalSandbox (no Docker). This is NOT an isolation "
            "boundary — the agent's Bash runs on the host, confined only to a temp workdir.",
            file=sys.stderr,
        )
        self._provision_files()
        setup = self.workdir / "setup.sh"
        if setup.is_file():
            proc = subprocess.run(
                ["bash", "setup.sh"],
                cwd=str(self.workdir),
                capture_output=True,
                text=True,
                timeout=300,
            )
            (self.run_dir / "setup.log").write_text(proc.stdout + proc.stderr)
            if proc.returncode != 0:
                raise RuntimeError(
                    f"setup.sh failed (exit {proc.returncode}):\n{proc.stdout}\n{proc.stderr}"
                )
        return self.workdir


class DockerSandbox(Sandbox):
    kind = "docker"

    def setup(self) -> Path:
        self._provision_files()
        setup = self.workdir / "setup.sh"
        if setup.is_file():
            # Build the fixed starting state inside an isolated, pinned container, with the
            # workdir bind-mounted so the resulting state is available to the host-side agent.
            cmd = [
                "docker", "run", "--rm",
                "--network", "none",
                "-v", f"{self.workdir.resolve()}:/work",
                "-w", "/work",
                self.image,
                "bash", "setup.sh",
            ]
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
            (self.run_dir / "setup.log").write_text(proc.stdout + proc.stderr)
            if proc.returncode != 0:
                raise RuntimeError(
                    f"setup.sh failed in container (exit {proc.returncode}):\n"
                    f"{proc.stdout}\n{proc.stderr}"
                )
        return self.workdir


def get_sandbox(kind: str, task_dir: Path, run_dir: Path, **kwargs) -> Sandbox:
    """kind in {'auto', 'docker', 'local'}."""
    if kind == "auto":
        kind = "docker" if docker_available() else "local"
    if kind == "docker":
        if not docker_available():
            raise RuntimeError(
                "Sandbox 'docker' requested but Docker is not available. "
                "Install/start Docker, or use --sandbox local (no isolation), or --sandbox auto."
            )
        return DockerSandbox(task_dir, run_dir, **kwargs)
    if kind == "local":
        return LocalSandbox(task_dir, run_dir, **kwargs)
    raise ValueError(f"Unknown sandbox kind: {kind!r}")
